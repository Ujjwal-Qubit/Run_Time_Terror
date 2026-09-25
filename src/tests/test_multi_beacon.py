"""
Unit and integration tests for Multi-Beacon Optical Target Simulation & Tracking.

Tests:
  1. BeaconConfig dataclass instantiation and fields.
  2. Multi-beacon intensity constraint validation (secondary < primary - margin).
  3. MultiBeaconManager multi-target dynamics and primary-at-index-0 invariant.
  4. SceneManager.render_beacons compositing multiple beacon patches.
  5. SimulationFrameProvider multi-beacon integration and Ground Truth Firewall enforcement.
  6. CandidateIdentifier hysteresis: threshold margin prevents instant track switching.
  7. CandidateIdentifier hysteresis: confirmation frames requirement before switching.
  8. CandidateIdentifier reset clears hysteresis state.
"""

from __future__ import annotations
import numpy as np
import pytest

from src.config.config_manager import (
    SystemConfig,
    BeaconConfig,
    TargetConfig,
    MotionConfig,
    SceneConfig,
    CameraConfig,
    ConfigManager,
)
from src.simulation.target_manager import TargetManager, MultiBeaconManager
from src.simulation.scene_manager import SceneManager
from src.simulation.camera_model import CameraModel
from src.simulation.disturbance_engine import DisturbanceEngine
from src.simulation.ground_truth_provider import GroundTruthProvider
from src.frame.simulation_provider import SimulationFrameProvider
from src.tracker.candidate_identifier import CandidateIdentifier
from src.frame.data_contracts import CandidateRegion, TrackingState, TrackingStateResult


class TestMultiBeaconConfigAndValidation:
    def test_beacon_config_defaults(self):
        b = BeaconConfig(beacon_id="b1", role="primary", size=12, intensity=240)
        assert b.beacon_id == "b1"
        assert b.role == "primary"
        assert b.size == 12
        assert b.intensity == 240

    def test_secondary_beacon_intensity_validation(self):
        """Secondary beacon intensity must be strictly less than primary intensity - margin."""
        cm = ConfigManager()
        cfg = cm.config
        # Create primary with intensity 200, secondary with 198 (margin is default 5)
        cfg.beacons = [
            BeaconConfig(beacon_id="p", role="primary", intensity=200),
            BeaconConfig(beacon_id="s", role="secondary", intensity=198),
        ]
        errors = cm.validate()
        assert any("Secondary beacon" in err and "intensity" in err for err in errors)

    def test_valid_multi_beacon_configuration(self):
        """Valid configuration passes validation without errors."""
        cm = ConfigManager()
        cfg = cm.config
        cfg.beacons = [
            BeaconConfig(beacon_id="p", role="primary", intensity=230),
            BeaconConfig(beacon_id="s1", role="secondary", intensity=150),
            BeaconConfig(beacon_id="s2", role="secondary", intensity=120),
        ]
        errors = cm.validate()
        assert not any("Secondary beacon" in err for err in errors)


class TestMultiBeaconManagerAndScene:
    def test_multi_beacon_manager_stepping(self):
        b1 = BeaconConfig(beacon_id="p", role="primary", size=10, intensity=220, speed=20.0)
        b2 = BeaconConfig(beacon_id="s", role="secondary", size=8, intensity=160, speed=30.0)
        mgr = MultiBeaconManager(
            beacon_configs=[b1, b2],
            motion_config=MotionConfig(),
            scene_width=2000,
            scene_height=2000,
            seed=42,
        )

        assert mgr.primary_manager is not None
        assert len(mgr.managers) == 2

        states = mgr.get_all_beacon_states()
        assert len(states) == 2
        # Primary is index 0
        assert states[0][0] is not None
        assert states[1][0] is not None
        
        # Step advances simulation
        p_state = mgr.step(0.1)
        assert p_state.world_x is not None

    def test_scene_manager_render_beacons(self):
        scene_mgr = SceneManager(SceneConfig(width=2000, height=2000, background_intensity=10))
        patch1 = np.full((10, 10), 220, dtype=np.uint8)
        patch2 = np.full((10, 10), 160, dtype=np.uint8)

        canvas = scene_mgr.render_beacons([
            (500.0, 500.0, patch1),
            (800.0, 800.0, patch2),
        ])

        assert canvas.shape == (2000, 2000)
        # Check that both locations have intensities corresponding to patches
        assert canvas[500, 500] == 220
        assert canvas[800, 800] == 160


class TestSimulationMultiBeaconFirewall:
    def test_ground_truth_tracks_only_primary(self):
        """SimulationFrameProvider composites all beacons, but ground truth ONLY tracks primary."""
        scene_cfg = SceneConfig(width=2000, height=2000, background_intensity=10)
        cam_cfg = CameraConfig(width=640, height=480, update_rate_hz=30)
        scene_mgr = SceneManager(scene_cfg)
        cam_model = CameraModel(cam_cfg, scene_width=2000, scene_height=2000)
        cam_model.set_position(1000.0, 1000.0)

        b1 = BeaconConfig(beacon_id="p", role="primary", x=1000.0, y=1000.0, size=10, intensity=220)
        b2 = BeaconConfig(beacon_id="s", role="secondary", x=1020.0, y=1020.0, size=10, intensity=160)
        mb_mgr = MultiBeaconManager(
            beacon_configs=[b1, b2],
            motion_config=MotionConfig(),
            scene_width=2000,
            scene_height=2000,
            seed=42,
        )

        gt_provider = GroundTruthProvider(background_intensity=10)
        dist_engine = DisturbanceEngine()

        provider = SimulationFrameProvider(
            scene_manager=scene_mgr,
            target_manager=mb_mgr.primary_manager,
            camera_model=cam_model,
            disturbance_engine=dist_engine,
            ground_truth_provider=gt_provider,
            fps=30,
            multi_beacon_manager=mb_mgr,
        )

        frame = provider.get_next_frame()
        assert frame is not None
        assert frame.image.shape == (480, 640)

        gt = gt_provider.get_truth(frame.frame_number)
        assert gt is not None
        # Ground truth world position must match primary beacon's initial position
        p_state = mb_mgr.primary_state
        assert gt.target_world_x == pytest.approx(p_state.world_x, abs=1e-3)
        assert gt.target_world_y == pytest.approx(p_state.world_y, abs=1e-3)


class TestCandidateIdentifierHysteresis:
    def test_hysteresis_prevents_premature_switching(self):
        """A distractor beacon with a slightly higher score cannot usurp track without beating margin."""
        identifier = CandidateIdentifier()
        identifier._switch_margin = 0.20
        identifier._switch_confirm_frames = 3

        # Simulate frame 1: current track establishes score
        cand_track = CandidateRegion(
            candidate_id="track_1",
            bbox_x=50, bbox_y=50, bbox_w=10, bbox_h=10,
            peak_intensity=200, mean_intensity=180, area=100,
            raw_centroid_x=55.0, raw_centroid_y=55.0,
            detection_score=0.60,
        )
        res1 = identifier.identify(
            [cand_track],
            current_state=TrackingState.SEARCHING,
        )
        assert res1.valid is True
        assert res1.selected_candidate_id == "track_1"

        # Simulate frame 2: In TRACKING state, a distractor appears with slight score advantage (< margin 0.20)
        cand_distractor = CandidateRegion(
            candidate_id="distractor_2",
            bbox_x=80, bbox_y=80, bbox_w=10, bbox_h=10,
            peak_intensity=210, mean_intensity=190, area=100,
            raw_centroid_x=85.0, raw_centroid_y=85.0,
            detection_score=0.65,
        )
        # Both candidates present
        res2 = identifier.identify(
            [cand_track, cand_distractor],
            current_state=TrackingState.TRACKING,
        )
        # Hysteresis must keep the current track ("track_1"), not switch to distractor
        assert res2.selected_candidate_id == "track_1"

    def test_hysteresis_switches_after_confirmed_frames(self):
        """Challenger exceeding score margin switches only after N confirmation frames."""
        identifier = CandidateIdentifier()
        identifier._switch_margin = 0.15
        identifier._switch_confirm_frames = 2

        # Initial track
        cand_track = CandidateRegion(
            candidate_id="track_1",
            bbox_x=50, bbox_y=50, bbox_w=10, bbox_h=10,
            peak_intensity=120, mean_intensity=100, area=100,
            raw_centroid_x=55.0, raw_centroid_y=55.0,
            detection_score=0.35,
        )
        identifier.identify([cand_track], current_state=TrackingState.SEARCHING)

        # Challenger candidate with much higher score (beats 0.15 margin)
        cand_challenger = CandidateRegion(
            candidate_id="challenger_9",
            bbox_x=100, bbox_y=100, bbox_w=10, bbox_h=10,
            peak_intensity=255, mean_intensity=240, area=100,
            raw_centroid_x=105.0, raw_centroid_y=105.0,
            detection_score=0.95,
        )

        # Frame 1: challenger beats margin, but confirmation count is 1 < 2 -> retains current track
        res_f1 = identifier.identify(
            [cand_track, cand_challenger],
            current_state=TrackingState.TRACKING,
            frame_number=1,
        )
        assert res_f1.selected_candidate_id == "track_1"

        # Frame 2: challenger beats margin for second consecutive frame -> switches track!
        res_f2 = identifier.identify(
            [cand_track, cand_challenger],
            current_state=TrackingState.TRACKING,
            frame_number=2,
        )
        assert res_f2.selected_candidate_id == "challenger_9"

    def test_hysteresis_reset(self):
        identifier = CandidateIdentifier()
        identifier._current_track_score = 0.99
        identifier._challenger_frames = 2
        identifier.reset()
        assert identifier._current_track_score == 0.0
        assert identifier._challenger_frames == 0

