"""
Phase 5.6 Tracking Pipeline Tests (Modules 11, 12, 13).

Comprehensive unit, precision, edge-case, robustness, firewall, and integration tests for:
  - Module 11: Candidate Identification (CandidateIdentifier)
  - Module 12: Temporal Tracker (ConstantVelocityKalmanTracker)
  - Module 13: Tracking State Manager (TrackingStateManager)
"""

from __future__ import annotations

import ast
import inspect
import math
import numpy as np
import pytest

from src.interfaces.strategy_interfaces import (
    IBeaconIdentifier,
    ITracker,
    ITrackingStateManager,
)
from src.frame.data_contracts import (
    CandidateRegion,
    ScoredCandidate,
    CentroidResult,
    TrackResult,
    TrackingState,
    TrackingStateResult,
    IdentificationResult,
    FramePacket,
    FrameSource,
)
from src.config.config_manager import (
    IdentifierConfig,
    TrackerConfig,
    StateConfig,
    SystemConfig,
)
from src.tracker.candidate_identifier import CandidateIdentifier, BeaconIdentifier
from src.tracker.temporal_tracker import ConstantVelocityKalmanTracker, TemporalTracker
from src.tracker.state_manager import TrackingStateManager, StateManager
from src.tracker.detection_engine import P0ThresholdDetector
from src.tracker.centroid_estimator import IntensityWeightedCentroidEstimator
from src.frame.simulation_provider import SimulationFrameProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_candidate(
    bx: int = 100,
    by: int = 100,
    bw: int = 10,
    bh: int = 10,
    peak: float = 220.0,
    mean: float = 180.0,
    contrast: float = 2.5,
    cid: int = 1,
    score: float = 0.9,
) -> CandidateRegion:
    return CandidateRegion(
        bbox_x=bx,
        bbox_y=by,
        bbox_w=bw,
        bbox_h=bh,
        peak_intensity=peak,
        mean_intensity=mean,
        area=bw * bh,
        local_contrast=contrast,
        candidate_id=cid,
        detection_score=score,
    )


# ---------------------------------------------------------------------------
# 1. Module 11: Candidate Identification Tests
# ---------------------------------------------------------------------------

class TestCandidateIdentifier:
    """Verifies candidate ranking, scoring, and beacon selection."""

    def test_implements_interface(self):
        ident = CandidateIdentifier()
        assert isinstance(ident, IBeaconIdentifier)
        assert ident.get_name() == "CandidateIdentifier"
        assert BeaconIdentifier is CandidateIdentifier

    def test_no_candidate_returns_invalid(self):
        ident = CandidateIdentifier()
        res = ident.identify([])
        assert isinstance(res, IdentificationResult)
        assert res.valid is False
        assert res.selected_candidate is None
        assert res.confidence == 0.0

    def test_single_candidate_selection(self):
        ident = CandidateIdentifier()
        c = make_candidate(peak=230.0, bw=10, bh=10)
        res = ident.identify([c])
        assert res.valid is True
        assert res.selected_candidate is not None
        assert res.selected_candidate.candidate_id == c.candidate_id
        assert res.confidence > 0.5
        # Duck typing for ScoredCandidate
        assert res.candidate is res.selected_candidate
        assert res.is_beacon is True

    def test_multiple_candidates_observation_ranking(self):
        """In SEARCHING state, brighter, well-sized target beats faint distractor."""
        ident = CandidateIdentifier()
        bright_good = make_candidate(bx=100, by=100, bw=10, bh=10, peak=240.0, contrast=3.0, cid=10)
        faint_distractor = make_candidate(bx=300, by=300, bw=25, bh=25, peak=80.0, contrast=1.1, cid=20)

        res = ident.identify([faint_distractor, bright_good], current_state=TrackingState.SEARCHING)
        assert res.valid is True
        assert res.selected_candidate_id == 10
        assert res.all_scored_candidates[0].candidate.candidate_id == 10
        assert res.all_scored_candidates[1].candidate.candidate_id == 20

    def test_temporal_proximity_preference_during_tracking(self):
        """When tracking, candidate closer to predicted position is preferred even if slightly dimmer."""
        ident = CandidateIdentifier()
        pred_pos = (150.0, 150.0)

        # Distractor is slightly brighter but far away at (400, 400)
        far_distractor = make_candidate(bx=395, by=395, bw=10, bh=10, peak=255.0, cid=1)
        # Real beacon is at (152, 148), very close to predicted position (150, 150)
        near_beacon = make_candidate(bx=147, by=143, bw=10, bh=10, peak=210.0, cid=2)

        res = ident.identify(
            [far_distractor, near_beacon],
            predicted_position=pred_pos,
            current_state=TrackingState.TRACKING,
        )
        assert res.valid is True
        assert res.selected_candidate_id == 2  # Near beacon chosen due to temporal proximity

    def test_ambiguous_candidates_proximity_breaks_tie(self):
        ident = CandidateIdentifier()
        pred_pos = (200.0, 200.0)

        cand_near = make_candidate(bx=195, by=195, peak=200.0, cid=1)
        cand_far = make_candidate(bx=280, by=280, peak=200.0, cid=2)

        res = ident.identify([cand_far, cand_near], predicted_position=pred_pos, current_state=TrackingState.TRACKING)
        assert res.valid is True
        assert res.selected_candidate_id == 1

    def test_firewall_zero_ground_truth_ast(self):
        """Inspect candidate_identifier.py AST to ensure no GroundTruth references exist."""
        import src.tracker.candidate_identifier as mod
        source_file = inspect.getfile(mod)
        with open(source_file, "r") as f:
            tree = ast.parse(f.read(), filename=source_file)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "GroundTruth" not in alias.name
                    assert "ground_truth" not in alias.name
                    assert "src.simulation" not in alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert "GroundTruth" not in module
                assert "ground_truth" not in module
                assert "src.simulation" not in module


# ---------------------------------------------------------------------------
# 2. Module 12: Constant-Velocity Kalman Tracker Tests
# ---------------------------------------------------------------------------

class TestConstantVelocityKalmanTracker:
    """Verifies Kalman initialization, state propagation, gating, and coasting."""

    def test_implements_interface(self):
        tracker = ConstantVelocityKalmanTracker()
        assert isinstance(tracker, ITracker)
        assert tracker.get_name() == "ConstantVelocityKalmanTracker"
        assert TemporalTracker is ConstantVelocityKalmanTracker

    def test_initialization_on_first_measurement(self):
        tracker = ConstantVelocityKalmanTracker()
        assert not tracker.is_initialized

        c = CentroidResult(x=120.45, y=230.78, valid=True, frame_number=0, timestamp=0.0)
        res = tracker.update(c, dt=0.0333)

        assert tracker.is_initialized
        assert tracker.track_age == 1
        assert res.measurement_valid is True
        assert res.measurement_accepted is True
        assert abs(res.estimated_x - 120.45) < 1e-4
        assert abs(res.estimated_y - 230.78) < 1e-4
        assert res.velocity_x == 0.0
        assert res.velocity_y == 0.0

    def test_constant_position_sequence(self):
        """Stationary target should yield steady position and near-zero velocity."""
        tracker = ConstantVelocityKalmanTracker()
        fixed_x, fixed_y = 300.25, 200.75

        res = None
        for i in range(20):
            c = CentroidResult(x=fixed_x, y=fixed_y, valid=True, frame_number=i, timestamp=i * 0.0333)
            res = tracker.update(c, dt=0.0333)

        assert res is not None
        assert abs(res.estimated_x - fixed_x) < 0.1
        assert abs(res.estimated_y - fixed_y) < 0.1
        assert abs(res.velocity_x) < 0.5
        assert abs(res.velocity_y) < 0.5

    def test_constant_velocity_sequence(self):
        """Target moving at 30 px/s in X, 15 px/s in Y should have velocity accurately tracked."""
        tracker = ConstantVelocityKalmanTracker()
        dt = 1.0 / 30.0
        vx_true = 30.0
        vy_true = 15.0
        x0, y0 = 100.0, 100.0

        res = None
        for i in range(30):
            meas_x = x0 + vx_true * (i * dt)
            meas_y = y0 + vy_true * (i * dt)
            c = CentroidResult(x=meas_x, y=meas_y, valid=True, frame_number=i, timestamp=i * dt)
            res = tracker.update(c, dt=dt)

        assert res is not None
        assert abs(res.estimated_x - (x0 + vx_true * 29 * dt)) < 0.5
        assert abs(res.velocity_x - vx_true) < 2.0
        assert abs(res.velocity_y - vy_true) < 2.0

    def test_sub_pixel_precision_preservation(self):
        tracker = ConstantVelocityKalmanTracker()
        c = CentroidResult(x=319.42, y=239.71, valid=True, frame_number=1, timestamp=0.0333)
        res = tracker.update(c)

        assert isinstance(res.estimated_x, float)
        assert isinstance(res.estimated_y, float)
        assert abs(res.estimated_x - round(res.estimated_x)) > 0.1
        assert abs(res.estimated_y - round(res.estimated_y)) > 0.1

    def test_missing_measurements_coasting(self):
        """When measurements cease, tracker must coast forward on velocity prediction with is_coasting=True."""
        tracker = ConstantVelocityKalmanTracker()
        dt = 0.0333
        # Initialize and establish velocity
        for i in range(5):
            c = CentroidResult(x=100.0 + i * 2.0, y=200.0 + i * 1.0, valid=True, frame_number=i, timestamp=i * dt)
            tracker.update(c, dt=dt)

        last_x = tracker.state_vector[0, 0]
        last_y = tracker.state_vector[1, 0]
        vx = tracker.state_vector[2, 0]

        # Supply None for missing frame
        res_coast = tracker.update(None, dt=dt, frame_number=5, timestamp=5 * dt)
        assert res_coast.measurement_valid is False
        assert res_coast.measurement_accepted is False
        assert res_coast.is_coasting is True
        # Forward position predicted along velocity
        assert res_coast.estimated_x > last_x

    def test_innovation_gating_rejects_outlier(self):
        """Outlier far away from prediction must be rejected, preserving track state."""
        tracker = ConstantVelocityKalmanTracker()
        dt = 0.0333

        # Track at (200, 200)
        for i in range(5):
            c = CentroidResult(x=200.0, y=200.0, valid=True, frame_number=i, timestamp=i * dt)
            tracker.update(c, dt=dt)

        # Inject wild outlier at (600, 450)
        outlier = CentroidResult(x=600.0, y=450.0, valid=True, frame_number=5, timestamp=5 * dt)
        res = tracker.update(outlier, dt=dt)

        assert res.measurement_valid is True
        assert res.measurement_accepted is False  # Rejected by innovation gate!
        assert res.is_coasting is True
        # State must remain near 200, not corrupted to 600
        assert abs(res.estimated_x - 200.0) < 5.0

    def test_timestamp_derived_dt(self):
        tracker = ConstantVelocityKalmanTracker()
        c0 = CentroidResult(x=100.0, y=100.0, valid=True, timestamp=1.0)
        tracker.update(c0)

        # Step with timestamp 1.05 -> dt = 0.05
        c1 = CentroidResult(x=102.0, y=101.0, valid=True, timestamp=1.05)
        res = tracker.update(c1)
        assert res.measurement_accepted is True

    def test_repeated_timestamps_gracefully_handled(self):
        tracker = ConstantVelocityKalmanTracker()
        c0 = CentroidResult(x=100.0, y=100.0, valid=True, timestamp=1.0)
        tracker.update(c0)

        # Repeated timestamp
        c1 = CentroidResult(x=100.0, y=100.0, valid=True, timestamp=1.0)
        res = tracker.update(c1)
        assert res.measurement_accepted is True
        assert not math.isnan(res.estimated_x)

    def test_large_dt_clamping(self):
        tracker = ConstantVelocityKalmanTracker()
        c0 = CentroidResult(x=100.0, y=100.0, valid=True, timestamp=0.0)
        tracker.update(c0)

        # 10 second jump
        c1 = CentroidResult(x=105.0, y=105.0, valid=True, timestamp=10.0)
        res = tracker.update(c1)
        assert res.measurement_accepted is True
        assert not math.isnan(res.estimated_x)

    def test_adaptive_roi_bounds(self):
        tracker = ConstantVelocityKalmanTracker()
        c = CentroidResult(x=320.0, y=240.0, valid=True)
        tracker.update(c)

        roi = tracker.get_roi(frame_width=640, frame_height=480)
        assert roi.width >= tracker.config.roi_min_size
        assert roi.height >= tracker.config.roi_min_size
        assert 0 <= roi.x < 640
        assert 0 <= roi.y < 480

    def test_firewall_zero_ground_truth_ast(self):
        import src.tracker.temporal_tracker as mod
        source_file = inspect.getfile(mod)
        with open(source_file, "r") as f:
            tree = ast.parse(f.read(), filename=source_file)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod_name = getattr(node, "module", "") or ""
                assert "GroundTruth" not in mod_name
                assert "src.simulation" not in mod_name


# ---------------------------------------------------------------------------
# 3. Module 13: Tracking State Manager Tests
# ---------------------------------------------------------------------------

class TestTrackingStateManager:
    """Verifies state machine transitions, confirmation counters, and hysteresis."""

    def test_implements_interface(self):
        sm = TrackingStateManager()
        assert isinstance(sm, ITrackingStateManager)
        assert sm.get_name() == "TrackingStateManager"
        assert StateManager is TrackingStateManager

    def test_initial_state_is_searching(self):
        sm = TrackingStateManager()
        assert sm.current_state == TrackingState.SEARCHING
        assert sm.is_locked is False

    def test_acquisition_and_lock_transition(self):
        """
        SEARCHING --(1 valid)--> ACQUIRING --(lock_confirm_frames valid)--> TRACKING
        """
        cfg = StateConfig(lock_confirm_frames=3)
        sm = TrackingStateManager(cfg)

        t_res_valid = TrackResult(
            estimated_x=100.0, estimated_y=100.0,
            confidence=0.9, track_age=1,
            measurement_valid=True, measurement_accepted=True,
        )

        # Frame 1: SEARCHING -> ACQUIRING
        st1 = sm.update(t_res_valid, timestamp=0.033)
        assert st1.state == TrackingState.ACQUIRING
        assert st1.is_locked is False
        assert st1.acquisition_frames == 1

        # Frame 2: Still ACQUIRING
        st2 = sm.update(t_res_valid, timestamp=0.066)
        assert st2.state == TrackingState.ACQUIRING
        assert st2.is_locked is False
        assert st2.acquisition_frames == 2

        # Frame 3: Lock confirmed -> TRACKING
        st3 = sm.update(t_res_valid, timestamp=0.100)
        assert st3.state == TrackingState.TRACKING
        assert st3.is_locked is True

    def test_acquisition_aborted_on_missed_frame(self):
        """If measurement drops during ACQUIRING, reverts immediately to SEARCHING."""
        cfg = StateConfig(lock_confirm_frames=3)
        sm = TrackingStateManager(cfg)

        valid_res = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_accepted=True)
        miss_res = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_accepted=False)

        sm.update(valid_res, timestamp=0.033)
        assert sm.current_state == TrackingState.ACQUIRING

        st = sm.update(miss_res, timestamp=0.066)
        assert st.state == TrackingState.SEARCHING
        assert st.is_locked is False

    def test_loss_and_reacquisition_lifecycle(self):
        """
        TRACKING --(miss)--> REACQUIRING --(recover)--> TRACKING
        """
        cfg = StateConfig(lock_confirm_frames=2, loss_confirm_frames=4, reacquire_confirm_frames=2)
        sm = TrackingStateManager(cfg)

        valid_res = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_accepted=True)
        miss_res = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_accepted=False)

        # Lock onto target
        sm.update(valid_res, timestamp=0.033)
        sm.update(valid_res, timestamp=0.066)
        assert sm.current_state == TrackingState.TRACKING
        assert sm.is_locked is True

        # Drop 1 frame: TRACKING -> REACQUIRING
        st_reacq = sm.update(miss_res, timestamp=0.100)
        assert st_reacq.state == TrackingState.REACQUIRING
        assert st_reacq.is_locked is False

        # Recover measurement frame 1: still REACQUIRING
        sm.update(valid_res, timestamp=0.133)
        assert sm.current_state == TrackingState.REACQUIRING

        # Recover measurement frame 2: confirmed reacquisition -> TRACKING
        st_relock = sm.update(valid_res, timestamp=0.166)
        assert st_relock.state == TrackingState.TRACKING
        assert st_relock.is_locked is True

    def test_loss_confirmation_to_lost_state(self):
        """
        REACQUIRING --(loss_confirm_frames misses)--> LOST
        """
        cfg = StateConfig(lock_confirm_frames=1, loss_confirm_frames=3)
        sm = TrackingStateManager(cfg)

        valid_res = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_accepted=True)
        miss_res = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_accepted=False)

        # Immediate lock
        sm.update(valid_res, timestamp=0.033)
        assert sm.current_state == TrackingState.TRACKING

        # Miss 1: REACQUIRING (loss_frames=1)
        sm.update(miss_res, timestamp=0.066)
        assert sm.current_state == TrackingState.REACQUIRING

        # Miss 2: REACQUIRING (loss_frames=2)
        sm.update(miss_res, timestamp=0.100)
        assert sm.current_state == TrackingState.REACQUIRING

        # Miss 3: LOST confirmed
        st_lost = sm.update(miss_res, timestamp=0.133)
        assert st_lost.state == TrackingState.LOST
        assert st_lost.should_trigger_loss is True

    def test_explicit_acquisition_time_metric(self):
        """
        Confirm Acquisition time = t(TRACKING entry) - t(first observation considered).
        For 3 confirm frames at 30 FPS: t=0.000, t=0.033, t=0.067 -> acq_time = 0.067s.
        """
        cfg = StateConfig(lock_confirm_frames=3)
        sm = TrackingStateManager(cfg)
        valid_res = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_accepted=True)

        res0 = sm.update(valid_res, timestamp=0.000)
        assert res0.state == TrackingState.ACQUIRING
        assert res0.acquisition_timestamp == 0.000
        assert res0.acquisition_time is None

        res1 = sm.update(valid_res, timestamp=0.0333)
        assert res1.state == TrackingState.ACQUIRING
        assert res1.acquisition_time is None

        res2 = sm.update(valid_res, timestamp=0.0667)
        assert res2.state == TrackingState.TRACKING
        assert res2.is_locked is True
        assert res2.lock_timestamp == 0.0667
        assert res2.acquisition_time == pytest.approx(0.0667, abs=1e-4)
        assert sm.acquisition_time == pytest.approx(0.0667, abs=1e-4)

    def test_reacquisition_time_metric_from_loss_episode(self):
        """
        Confirm Reacquisition time = t(TRACKING return) - t(loss episode entry).
        """
        cfg = StateConfig(lock_confirm_frames=1, loss_confirm_frames=5, reacquire_confirm_frames=2)
        sm = TrackingStateManager(cfg)
        valid_res = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_accepted=True)
        miss_res = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_accepted=False)

        # Immediate lock at t=1.000
        sm.update(valid_res, timestamp=1.000)
        assert sm.current_state == TrackingState.TRACKING

        # Loss episode begins at t=1.333
        sm.update(miss_res, timestamp=1.333)
        assert sm.current_state == TrackingState.REACQUIRING

        # Reacquire frame 1 at t=1.367 (not yet locked)
        sm.update(valid_res, timestamp=1.367)
        assert sm.current_state == TrackingState.REACQUIRING
        assert sm.is_locked is False

        # Reacquire frame 2 confirmed at t=1.400 -> TRACKING
        res_relock = sm.update(valid_res, timestamp=1.400)
        assert res_relock.state == TrackingState.TRACKING
        assert res_relock.is_locked is True
        # Reacquisition time: 1.400 - 1.333 = 0.067s
        assert res_relock.reacquisition_time == pytest.approx(0.067, abs=1e-3)
        assert sm.reacquisition_time == pytest.approx(0.067, abs=1e-3)

    def test_gate_rejected_outlier_does_not_advance_acquisition_or_reacquisition(self):
        """
        Outlier rejected by Euclidean innovation gate (measurement_accepted=False)
        must NOT advance acquisition frames or reacquisition frames.
        """
        cfg = StateConfig(lock_confirm_frames=3, reacquire_confirm_frames=3)
        sm = TrackingStateManager(cfg)
        valid_res = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_valid=True, measurement_accepted=True)
        gated_outlier = TrackResult(estimated_x=100.0, estimated_y=100.0, measurement_valid=True, measurement_accepted=False, is_coasting=True)

        # 1. In SEARCHING/ACQUIRING: gated outlier does not confirm lock
        sm.update(valid_res, timestamp=0.000)  # ACQUIRING (1/3)
        assert sm.current_state == TrackingState.ACQUIRING
        assert sm.is_locked is False

        res_gated = sm.update(gated_outlier, timestamp=0.033)  # Gated outlier dropped -> aborts to SEARCHING
        assert res_gated.state == TrackingState.SEARCHING
        assert res_gated.is_locked is False
        assert sm.is_locked is False

        # 2. In REACQUIRING: gated outlier does not count as reacquired frame
        sm.update(valid_res, timestamp=0.066)
        sm.update(valid_res, timestamp=0.100)
        sm.update(valid_res, timestamp=0.133)
        assert sm.current_state == TrackingState.TRACKING

        # Measurement drops -> REACQUIRING
        sm.update(gated_outlier, timestamp=0.166)
        assert sm.current_state == TrackingState.REACQUIRING

        # Gated outlier in REACQUIRING resets reacquisition counter and increments loss frames
        res_reacq_gated = sm.update(gated_outlier, timestamp=0.200)
        assert res_reacq_gated.state == TrackingState.REACQUIRING
        assert res_reacq_gated.reacquisition_frames == 0
        assert res_reacq_gated.loss_frames == 2
        assert res_reacq_gated.is_locked is False

    def test_subpixel_dataflow_exact_float_preservation(self):
        """
        Confirm Module 10's floating-point centroid passes to Module 12 without
        truncation, integer casting, or rounding.
        """
        tracker = ConstantVelocityKalmanTracker()
        subpix_x, subpix_y = 123.456789, 234.567890
        cent = CentroidResult(
            x=subpix_x,
            y=subpix_y,
            valid=True,
            quality=0.95,
        )

        res = tracker.update(cent, dt=0.0333)
        assert isinstance(res.estimated_x, float)
        assert isinstance(res.estimated_y, float)
        assert isinstance(res.predicted_x, float)
        assert isinstance(res.predicted_y, float)
        # Verify first update exactly preserves sub-pixel position
        assert res.estimated_x == pytest.approx(subpix_x, abs=1e-5)
        assert res.estimated_y == pytest.approx(subpix_y, abs=1e-5)
        # Ensure no integer rounding occurred
        assert res.estimated_x != float(int(subpix_x))
        assert res.estimated_y != float(int(subpix_y))

    def test_firewall_zero_ground_truth_ast(self):
        import src.tracker.state_manager as mod
        source_file = inspect.getfile(mod)
        with open(source_file, "r") as f:
            tree = ast.parse(f.read(), filename=source_file)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod_name = getattr(node, "module", "") or ""
                assert "GroundTruth" not in mod_name
                assert "src.simulation" not in mod_name


# ---------------------------------------------------------------------------
# 4. End-to-End Tracking Pipeline Integration Test
# ---------------------------------------------------------------------------

class TestFullTrackingPipelineIntegration:
    """
    Verifies full integration:
      SimulationFrameProvider
        -> DetectionEngine (M9)
        -> CandidateIdentifier (M11)
        -> CentroidEstimator (M10)
        -> TemporalTracker (M12)
        -> TrackingStateManager (M13)
    """

    def test_full_pipeline_multi_frame_lock(self):
        cfg = SystemConfig()
        cfg.simulation.random_seed = 42
        cfg.camera.width = 640
        cfg.camera.height = 480
        cfg.target.initial_position = "custom"
        cfg.target.initial_x = 1000.0
        cfg.target.initial_y = 1000.0
        cfg.target.size = 12
        cfg.target.intensity = 220
        cfg.scene.background_intensity = 30

        sim_provider = SimulationFrameProvider.from_config(cfg)
        detector = P0ThresholdDetector(cfg.detector)
        identifier = CandidateIdentifier(cfg.identifier)
        centroid_estimator = IntensityWeightedCentroidEstimator(cfg.centroid)
        tracker = ConstantVelocityKalmanTracker(cfg.tracker)
        state_mgr = TrackingStateManager(cfg.state)

        states_observed = []

        # Run 10 consecutive frames
        for f in range(10):
            packet = sim_provider.get_next_frame()
            assert packet is not None

            # 1. Detection
            det_result = detector.detect(packet)
            assert det_result.frame_number == f

            # 2. Identification
            pred_pos = tracker.predict() if tracker.is_initialized else None
            ident_result = identifier.identify(
                det_result.candidates,
                predicted_position=pred_pos,
                current_state=state_mgr.current_state,
                frame_number=f,
                timestamp=packet.timestamp,
            )

            # 3. Centroid Estimation on selected candidate
            if ident_result.valid and ident_result.selected_candidate is not None:
                cent_result = centroid_estimator.estimate(packet, ident_result.selected_candidate)
            else:
                cent_result = None

            # 4. Temporal Tracking update
            track_result = tracker.update(cent_result, dt=0.0333, frame_number=f, timestamp=packet.timestamp)
            assert isinstance(track_result.estimated_x, float)
            assert isinstance(track_result.estimated_y, float)

            # 5. Tracking State Manager update
            state_result = state_mgr.update(track_result, timestamp=packet.timestamp)
            states_observed.append(state_result.state)

        # Verify pipeline established lock: SEARCHING -> ACQUIRING -> TRACKING
        assert TrackingState.ACQUIRING in states_observed
        assert TrackingState.TRACKING in states_observed
        assert state_mgr.is_locked is True
