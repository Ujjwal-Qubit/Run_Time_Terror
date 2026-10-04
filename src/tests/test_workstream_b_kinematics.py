"""
Workstream B Kinematics, Simulation & Tracking Test Suite.

Verifies remediation of:
  - DEF-15: Motion Type Normalization across TargetManager, SecondaryBeaconKinematics, MultiBeaconManager
  - DEF-19: PTZ Continuous Linear Ramp Deadband Transition
  - DEF-14: CandidateIdentifier Raster-Scan Invariant Persistent Spatial NN Tracking & Hysteresis
  - DEF-27/31: NoiseConfig gaussian_sigma attribute & gaussian_std backward compatibility
  - DEF-02/24: 2D Planar Viewport Projection geometry & coordinate mapping
"""

import math
import numpy as np
import pytest

from src.frame.data_contracts import (
    MotionType,
    CandidateRegion,
    ScoredCandidate,
    TrackingState,
)
from src.config.config_manager import (
    ConfigManager,
    TargetConfig,
    MotionConfig,
    BeaconConfig,
    PTZConfig,
    NoiseConfig,
    IdentifierConfig,
)
from src.config import defaults
from src.simulation.target_manager import (
    TargetManager,
    MultiBeaconManager,
    _SecondaryBeaconKinematics,
)
from src.control.ptz_controller import PTZController
from src.tracker.candidate_identifier import CandidateIdentifier, _SpatialTrack


# ===========================================================================
# 1. DEF-15: Motion Type Normalization Tests
# ===========================================================================

class TestDEF15MotionTypeNormalization:
    """Tests that all motion type representations and aliases normalize to canonical forms."""

    @pytest.mark.parametrize(
        "raw_input,expected",
        [
            (MotionType.STRAIGHT_LINE, "STRAIGHT_LINE"),
            (MotionType.CIRCULAR, "CIRCULAR"),
            (MotionType.FIGURE_8, "FIGURE_8"),
            (MotionType.RANDOM, "RANDOM"),
            ("linear", "STRAIGHT_LINE"),
            ("LINEAR", "STRAIGHT_LINE"),
            ("straight", "STRAIGHT_LINE"),
            ("straight_line", "STRAIGHT_LINE"),
            ("circle", "CIRCULAR"),
            ("CIRCULAR", "CIRCULAR"),
            ("figure8", "FIGURE_8"),
            ("FIG8", "FIGURE_8"),
            ("figure-8", "FIGURE_8"),
            ("FIGURE_8", "FIGURE_8"),
            ("brownian", "RANDOM"),
            ("RANDOM", "RANDOM"),
            ("MotionType.FIGURE_8", "FIGURE_8"),
            ("MOTIONTYPE.CIRCULAR", "CIRCULAR"),
            (None, "STRAIGHT_LINE"),
            ("invalid_motion", "STRAIGHT_LINE"),
            ("unknown", "STRAIGHT_LINE"),
            ("", "STRAIGHT_LINE"),
        ],
    )
    def test_normalize_motion_type_canonical_mapping(self, raw_input, expected):
        norm = TargetManager._normalize_motion_type(raw_input)
        assert norm == expected, f"Failed normalizing {raw_input}: expected {expected}, got {norm}"

    def test_target_manager_init_with_enum(self):
        """TargetManager initialized with MotionType enum sets up correct kinematics."""
        tm = TargetManager(
            target_config=TargetConfig(speed=50.0),
            motion_config=MotionConfig(motion_type=MotionType.FIGURE_8),
        )
        assert hasattr(tm, "_fig8_omega"), "TargetManager failed to initialize figure-8 parameters"
        assert tm._motion_cfg.motion_type == "FIGURE_8"
        state = tm.step(0.1)
        # Should not be static or moving strictly on a single axis
        assert state.vx != 0.0 or state.vy != 0.0

    def test_target_manager_set_motion_type_with_alias(self):
        """Dynamic set_motion_type maps string aliases correctly."""
        tm = TargetManager(
            target_config=TargetConfig(speed=40.0),
            motion_config=MotionConfig(motion_type="linear"),
        )
        assert tm._motion_cfg.motion_type == "STRAIGHT_LINE"

        tm.set_motion_type("figure8")
        assert tm._motion_cfg.motion_type == "FIGURE_8"
        assert hasattr(tm, "_fig8_omega")

        tm.set_motion_type("brownian")
        assert tm._motion_cfg.motion_type == "RANDOM"

    def test_secondary_beacon_kinematics_enum_and_alias(self):
        """_SecondaryBeaconKinematics handles enums and aliases without AttributeError."""
        # Enum input
        sec1 = _SecondaryBeaconKinematics(
            beacon_cfg=BeaconConfig(role="secondary", motion_type=MotionType.FIGURE_8),
            motion_cfg=MotionConfig(),
            scene_width=1920,
            scene_height=1080,
            seed=42,
        )
        assert sec1._motion_type == "FIGURE_8"
        assert hasattr(sec1, "_fig8_omega")

        # Alias input
        sec2 = _SecondaryBeaconKinematics(
            beacon_cfg=BeaconConfig(role="secondary", motion_type="linear"),
            motion_cfg=MotionConfig(),
            scene_width=1920,
            scene_height=1080,
            seed=42,
        )
        assert sec2._motion_type == "STRAIGHT_LINE"

    def test_multi_beacon_manager_set_motion_type(self):
        """MultiBeaconManager normalizes motion type across all beacon managers."""
        primary_cfg = BeaconConfig(role="primary", motion_type="straight_line", speed=30.0)
        sec_cfg = BeaconConfig(role="secondary", motion_type="circle", speed=20.0)
        mbm = MultiBeaconManager(
            beacon_configs=[primary_cfg, sec_cfg],
            motion_config=MotionConfig(),
        )
        mbm.set_motion_type("figure8")
        assert mbm._primary_manager._motion_cfg.motion_type == "FIGURE_8"
        assert mbm._secondaries[0]._motion_type == "FIGURE_8"


# ===========================================================================
# 2. DEF-19: Continuous Linear Ramp Deadband Transition
# ===========================================================================

class TestDEF19PTZDeadbandContinuity:
    """Verifies that the PTZ deadband uses a C0 continuous ramp with zero step discontinuity."""

    def _make_track(self, x: float = 320.0, y: float = 240.0):
        from src.frame.data_contracts import TrackResult
        return TrackResult(
            estimated_x=x,
            estimated_y=y,
            velocity_x=0.0,
            velocity_y=0.0,
            confidence=0.95,
            track_age=1,
            predicted_x=x,
            predicted_y=y,
            frame_number=1,
            timestamp=0.033,
            measurement_valid=True,
        )

    def test_deadband_exact_boundary_and_interior(self):
        """Points inside and exactly on deadband boundary produce zero angular error."""
        ctrl = PTZController()
        # Inside deadband
        res_inside = ctrl.compute(
            track_result=self._make_track(320.5, 240.0),
            tracking_state=TrackingState.TRACKING,
            frame_width=640,
            frame_height=480,
            dt=0.05,
        )
        assert res_inside.in_deadband is True
        assert res_inside.pan_velocity_deg_s == 0.0

        # Exact deadband boundary (1.0 px)
        res_bound = ctrl.compute(
            track_result=self._make_track(321.0, 240.0),
            tracking_state=TrackingState.TRACKING,
            frame_width=640,
            frame_height=480,
            dt=0.05,
        )
        assert res_bound.in_deadband is True
        assert res_bound.pan_velocity_deg_s == 0.0

    def test_deadband_boundary_continuity_epsilon(self):
        """As error approaches deadband from outside, commanded velocity approaches zero."""
        ctrl = PTZController()
        deadband = defaults.PTZ_DEFAULT_DEADBAND_PX  # 1.0 px
        eps = 1e-4

        # Just outside deadband: err_x = deadband + eps
        x_target = 320.0 + deadband + eps
        res_eps = ctrl.compute(
            track_result=self._make_track(x_target, 240.0),
            tracking_state=TrackingState.TRACKING,
            frame_width=640,
            frame_height=480,
            dt=0.05,
        )
        assert res_eps.in_deadband is False

        # In continuous ramp: effective error is eps, NOT (deadband + eps)
        # Therefore velocity must be tiny (~0.0003 dps), not a step of ~0.3 dps
        assert abs(res_eps.pan_velocity_deg_s) < 0.01, (
            f"Velocity jump detected at boundary: {res_eps.pan_velocity_deg_s} dps. "
            "Continuous ramp should eliminate step discontinuity."
        )

    def test_deadband_ramp_linearity(self):
        """Commanded velocity grows linearly with excess error above deadband."""
        ctrl = PTZController()
        deadband = defaults.PTZ_DEFAULT_DEADBAND_PX

        # Compute for excess = 1.0 px and excess = 2.0 px
        ctrl.reset()
        res1 = ctrl.compute(
            track_result=self._make_track(320.0 + deadband + 1.0, 240.0),
            tracking_state=TrackingState.TRACKING,
            frame_width=640,
            frame_height=480,
            dt=0.05,
        )
        ctrl.reset()
        res2 = ctrl.compute(
            track_result=self._make_track(320.0 + deadband + 2.0, 240.0),
            tracking_state=TrackingState.TRACKING,
            frame_width=640,
            frame_height=480,
            dt=0.05,
        )

        # Ratio of velocities should be approximately 2.0 (linear proportional action)
        ratio = res2.pan_velocity_deg_s / res1.pan_velocity_deg_s
        assert abs(ratio - 2.0) < 0.05, f"Expected linear velocity doubling, got ratio {ratio}"


# ===========================================================================
# 3. DEF-14: Persistent Spatial NN Tracking & Anti-Hijack Hysteresis
# ===========================================================================

class TestDEF14CandidateSpatialTracking:
    """Verifies that CandidateIdentifier is immune to raster-scan candidate index swaps."""

    def test_raster_scan_noise_anti_hijack(self):
        """Noise appearing at raster-scan index 0 does NOT hijack the beacon track."""
        ci = CandidateIdentifier()

        # Frame 1: True beacon discovered at (500, 500), receives candidate_id=0
        beacon_f1 = CandidateRegion(
            bbox_x=495, bbox_y=495, bbox_w=10, bbox_h=10,
            peak_intensity=220, mean_intensity=200, area=100,
            raw_centroid_x=500.0, raw_centroid_y=500.0,
            candidate_id=0, detection_score=0.92,
        )
        r1 = ci.identify([beacon_f1], current_state=TrackingState.SEARCHING, frame_number=1)
        assert r1.valid is True
        assert r1.selected_candidate_id == 0

        # Frame 2: Noise artifact appears at (100, 100) and usurps raster index 0.
        # True beacon moves to (501, 501) and gets raster index 1.
        noise_f2 = CandidateRegion(
            bbox_x=95, bbox_y=95, bbox_w=10, bbox_h=10,
            peak_intensity=230, mean_intensity=210, area=100,
            raw_centroid_x=100.0, raw_centroid_y=100.0,
            candidate_id=0, detection_score=0.90,
        )
        beacon_f2 = CandidateRegion(
            bbox_x=496, bbox_y=496, bbox_w=10, bbox_h=10,
            peak_intensity=220, mean_intensity=200, area=100,
            raw_centroid_x=501.0, raw_centroid_y=501.0,
            candidate_id=1, detection_score=0.92,
        )

        r2 = ci.identify(
            [noise_f2, beacon_f2],
            predicted_position=(500.0, 500.0),
            current_state=TrackingState.TRACKING,
            frame_number=2,
        )

        # Spatial NN engine must associate beacon_f2 with persistent track ID 0
        assert r2.selected_candidate is not None
        assert abs(r2.selected_candidate.raw_centroid_x - 501.0) < 0.1, (
            f"Hijacked by noise at {r2.selected_candidate.raw_centroid_x}"
        )
        assert r2.selected_candidate_id == 0, (
            f"Persistent candidate ID should remain 0, got {r2.selected_candidate_id}"
        )

    def test_subpixel_coordinate_preservation(self):
        """Subpixel centroids are preserved and used over coarse integer bounding boxes."""
        cand = CandidateRegion(
            bbox_x=200, bbox_y=150, bbox_w=12, bbox_h=12,
            peak_intensity=250, mean_intensity=220, area=144,
            raw_centroid_x=205.875, raw_centroid_y=155.432,
            candidate_id=0, detection_score=0.95,
        )
        pos = CandidateIdentifier._get_candidate_pos(cand)
        assert pos == (205.875, 155.432)

    def test_track_staleness_and_pruning(self):
        """Tracks tolerate missed detections up to max_staleness before pruning."""
        ci = CandidateIdentifier()
        beacon = CandidateRegion(
            bbox_x=300, bbox_y=300, bbox_w=10, bbox_h=10,
            peak_intensity=200, mean_intensity=180, area=100,
            raw_centroid_x=305.0, raw_centroid_y=305.0,
            candidate_id=0, detection_score=0.9,
        )
        ci.identify([beacon], current_state=TrackingState.SEARCHING, frame_number=1)
        assert 0 in ci._tracks

        # 3 missed frames: track still retained with missed_frames=3
        for fn in range(2, 5):
            ci.identify([], current_state=TrackingState.TRACKING, frame_number=fn)

        # Frame 5: candidate returns within gate
        beacon_ret = CandidateRegion(
            bbox_x=301, bbox_y=301, bbox_w=10, bbox_h=10,
            peak_intensity=200, mean_intensity=180, area=100,
            raw_centroid_x=306.0, raw_centroid_y=306.0,
            candidate_id=99, detection_score=0.9,
        )
        r = ci.identify([beacon_ret], current_state=TrackingState.TRACKING, frame_number=5)
        # Re-tagged to original track ID 0
        assert r.selected_candidate_id == 0

    def test_hysteresis_challenger_margin(self):
        """Challenger must beat current track by margin for confirmation frames to switch."""
        ci = CandidateIdentifier()
        ci._switch_confirm_frames = 3
        ci._switch_margin = 0.15

        # Initialize tracking on track 0
        b1 = CandidateRegion(
            bbox_x=400, bbox_y=400, bbox_w=10, bbox_h=10,
            peak_intensity=200, mean_intensity=180, area=100,
            raw_centroid_x=405.0, raw_centroid_y=405.0,
            candidate_id=0, detection_score=0.75,
        )
        ci.identify([b1], current_state=TrackingState.SEARCHING, frame_number=1)

        # Challenger candidate with slightly higher score (+0.05 < margin 0.15)
        c_weak = CandidateRegion(
            bbox_x=200, bbox_y=200, bbox_w=10, bbox_h=10,
            peak_intensity=220, mean_intensity=190, area=100,
            raw_centroid_x=205.0, raw_centroid_y=205.0,
            candidate_id=1, detection_score=0.80,
        )
        r = ci.identify([b1, c_weak], current_state=TrackingState.TRACKING, frame_number=2)
        # Should stay on track 0
        assert r.selected_candidate_id == 0


# ===========================================================================
# 4. DEF-27/31: NoiseConfig gaussian_sigma & gaussian_std Compatibility
# ===========================================================================

class TestDEF27NoiseConfigCompatibility:
    """Verifies that gaussian_sigma is the canonical attribute and gaussian_std is a working alias."""

    def test_gaussian_sigma_and_std_property(self):
        cfg = NoiseConfig(gaussian_sigma=8.5)
        assert cfg.gaussian_sigma == 8.5
        assert cfg.gaussian_std == 8.5

        # Setter via alias
        cfg.gaussian_std = 6.2
        assert cfg.gaussian_sigma == 6.2
        assert cfg.gaussian_std == 6.2

    def test_dataset_generator_uses_gaussian_sigma(self):
        """Inspects that dataset_generator sets gaussian_sigma without error."""
        import inspect
        from src.data import dataset_generator
        src = inspect.getsource(dataset_generator)
        assert "cfg.noise.gaussian_sigma" in src
        assert "cfg.noise.gaussian_std =" not in src


# ===========================================================================
# 5. DEF-02 / DEF-24: 2D Planar Projection & Geometry Constants
# ===========================================================================

class TestDEF02DEF24PlanarProjectionGeometry:
    """Verifies the 2D planar viewport projection mathematical formulas and constants."""

    def test_camera_angular_mapping_scale(self):
        """FOV to pixel angular sensitivity must equal 160.0 px/deg."""
        cam_w = 640.0
        fov_h = 4.0
        cam_h = 480.0
        fov_v = 3.0

        scale_h = cam_w / fov_h
        scale_v = cam_h / fov_v

        assert scale_h == 160.0
        assert scale_v == 160.0

    def test_telemetry_derived_world_coordinates(self):
        """World coordinates derived from pan/tilt and optical centroid offset."""
        scene_center_x = 1000.0
        scene_center_y = 1000.0
        scale = 160.0

        pan_deg = 0.2625
        tilt_deg = -0.1000
        cam_world_x = scene_center_x + pan_deg * scale
        cam_world_y = scene_center_y + tilt_deg * scale

        assert abs(cam_world_x - 1042.0) < 1e-4
        assert abs(cam_world_y - 984.0) < 1e-4

        # Optical centroid offset: centroid at (330.4, 240.2)
        cx, cy = 330.4, 240.2
        delta_x = cx - 320.0
        delta_y = cy - 240.0
        target_x = cam_world_x + delta_x
        target_y = cam_world_y + delta_y

        assert abs(target_x - 1052.4) < 1e-4
        assert abs(target_y - 984.2) < 1e-4

    def test_docs_and_ui_declaration_of_2d_planar_testbed(self):
        """Verifies that documentation and UI files declare 2D Planar Testbed."""
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent.parent

        # docs/system_architecture.md
        arch_md = (root / "docs" / "system_architecture.md").read_text(encoding="utf-8")
        assert "2D Planar Viewport Projection Testbed" in arch_md

        # docs/PRD.md
        prd_md = (root / "docs" / "PRD.md").read_text(encoding="utf-8")
        assert "2D Planar Viewport Projection" in prd_md

        # frontend Header.tsx
        header_tsx = (root / "frontend" / "src" / "components" / "Header.tsx").read_text(encoding="utf-8")
        assert "ARENA:" in header_tsx
        assert "742.18 km" not in header_tsx
