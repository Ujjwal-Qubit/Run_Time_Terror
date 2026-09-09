"""
Tests for Module 14 — PTZ Controller (src/control/ptz_controller.py).

Verifies:
  1. Functional: Interface adherence, centered target, four-quadrant sign convention,
     deadband thresholds, independent axis deadband, proportional scaling, rate limiting.
  2. State-Dependent: SEARCHING, ACQUIRING, TRACKING, REACQUIRING, LOST.
  3. Geometry: Resolution/FOV independence, non-square pixels, ProjectionModel consumption.
  4. Robustness: None track, NaN/Inf coordinates, zero/negative dt, invalid frame dimensions.
  5. Architecture & Firewall: Single actuation ownership, zero GroundTruth/simulation imports.
  6. Performance: Latency measurement as engineering benchmark (not a hard failure gate).
"""

from __future__ import annotations

import ast
import inspect
import math
import time
import pytest

from src.interfaces.strategy_interfaces import IPTZController
from src.control.ptz_controller import ProportionalDeadbandPTZController, PTZController
from src.frame.data_contracts import PTZCommand, TrackResult, TrackingState
from src.config.config_manager import PTZConfig, CameraConfig, SystemConfig
from src.simulation.camera_model import CameraModel, ProjectionModel
from src.frame.simulation_provider import SimulationFrameProvider
from src.tracker.detection_engine import P0ThresholdDetector
from src.tracker.centroid_estimator import IntensityWeightedCentroidEstimator
from src.tracker.candidate_identifier import CandidateIdentifier
from src.tracker.temporal_tracker import ConstantVelocityKalmanTracker
from src.tracker.state_manager import TrackingStateManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_track(
    x: float = 320.0,
    y: float = 240.0,
    valid: bool = True,
    coasting: bool = False,
    confidence: float = 0.9,
    frame: int = 1,
    ts: float = 0.033,
) -> TrackResult:
    return TrackResult(
        estimated_x=x,
        estimated_y=y,
        velocity_x=0.0,
        velocity_y=0.0,
        confidence=confidence,
        track_age=frame,
        predicted_x=x,
        predicted_y=y,
        frame_number=frame,
        timestamp=ts,
        measurement_valid=valid,
        measurement_accepted=valid,
        is_coasting=coasting,
        status="TRACKING" if not coasting else "COASTING",
    )


# ---------------------------------------------------------------------------
# 1. Functional & Control Law Tests
# ---------------------------------------------------------------------------

class TestPTZControllerFunctional:
    def test_implements_interface(self):
        controller = ProportionalDeadbandPTZController()
        assert isinstance(controller, IPTZController)
        assert controller.get_name() == "ProportionalDeadbandPTZController"

    def test_centered_target_produces_zero_command(self):
        """Target exactly at optical axis center (320, 240) in a 640x480 frame."""
        controller = ProportionalDeadbandPTZController()
        track = make_track(320.0, 240.0)

        cmd = controller.compute(
            track_result=track,
            tracking_state=TrackingState.TRACKING,
            frame_width=640,
            frame_height=480,
            dt=0.0333,
        )

        assert cmd.valid is True
        assert cmd.in_deadband is True
        assert cmd.is_saturated is False
        assert cmd.pan_velocity_deg_s == 0.0
        assert cmd.tilt_velocity_deg_s == 0.0
        assert cmd.delta_pan_deg == 0.0
        assert cmd.delta_tilt_deg == 0.0
        assert cmd.error_x_px == 0.0
        assert cmd.error_y_px == 0.0

    def test_four_quadrant_sign_correctness(self):
        """
        Verify sign convention across all 4 quadrants:
          1. Right of center (x > 320): camera pans right (+pan).
          2. Left of center  (x < 320): camera pans left  (-pan).
          3. Below center    (y > 240): camera tilts down (+tilt).
          4. Above center    (y < 240): camera tilts up   (-tilt).
        """
        controller = ProportionalDeadbandPTZController()
        w, h = 640, 480
        dt = 0.0333

        # 1. Target right of center (+20 px offset)
        cmd_right = controller.compute(make_track(340.0, 240.0), TrackingState.TRACKING, w, h, dt)
        assert cmd_right.error_x_px == 20.0
        assert cmd_right.pan_velocity_deg_s > 0.0
        assert cmd_right.delta_pan_deg > 0.0
        assert cmd_right.tilt_velocity_deg_s == 0.0

        # 2. Target left of center (-20 px offset)
        cmd_left = controller.compute(make_track(300.0, 240.0), TrackingState.TRACKING, w, h, dt)
        assert cmd_left.error_x_px == -20.0
        assert cmd_left.pan_velocity_deg_s < 0.0
        assert cmd_left.delta_pan_deg < 0.0
        assert cmd_left.tilt_velocity_deg_s == 0.0

        # 3. Target below center (+20 px offset)
        cmd_down = controller.compute(make_track(320.0, 260.0), TrackingState.TRACKING, w, h, dt)
        assert cmd_down.error_y_px == 20.0
        assert cmd_down.tilt_velocity_deg_s > 0.0
        assert cmd_down.delta_tilt_deg > 0.0
        assert cmd_down.pan_velocity_deg_s == 0.0

        # 4. Target above center (-20 px offset)
        cmd_up = controller.compute(make_track(320.0, 220.0), TrackingState.TRACKING, w, h, dt)
        assert cmd_up.error_y_px == -20.0
        assert cmd_up.tilt_velocity_deg_s < 0.0
        assert cmd_up.delta_tilt_deg < 0.0
        assert cmd_up.pan_velocity_deg_s == 0.0

    def test_deadband_below_threshold_produces_zero(self):
        """Error below deadband (4 px < 5 px) must produce zero command."""
        cfg = PTZConfig(deadband_px=5.0)
        controller = ProportionalDeadbandPTZController(ptz_config=cfg)

        cmd = controller.compute(make_track(324.0, 243.0), TrackingState.TRACKING, 640, 480, 0.0333)
        assert cmd.in_deadband is True
        assert cmd.pan_velocity_deg_s == 0.0
        assert cmd.tilt_velocity_deg_s == 0.0
        assert cmd.delta_pan_deg == 0.0
        assert cmd.delta_tilt_deg == 0.0

    def test_deadband_exact_boundary_produces_zero(self):
        """Error exactly at deadband (5 px == 5 px) must produce zero command."""
        cfg = PTZConfig(deadband_px=5.0)
        controller = ProportionalDeadbandPTZController(ptz_config=cfg)

        cmd = controller.compute(make_track(325.0, 245.0), TrackingState.TRACKING, 640, 480, 0.0333)
        assert cmd.in_deadband is True
        assert cmd.pan_velocity_deg_s == 0.0
        assert cmd.tilt_velocity_deg_s == 0.0

    def test_deadband_above_threshold_produces_command(self):
        """Error strictly above deadband (5.1 px > 5.0 px) must produce nonzero command."""
        cfg = PTZConfig(deadband_px=5.0)
        controller = ProportionalDeadbandPTZController(ptz_config=cfg)

        cmd = controller.compute(make_track(325.1, 240.0), TrackingState.TRACKING, 640, 480, 0.0333)
        assert cmd.in_deadband is False
        assert cmd.pan_velocity_deg_s > 0.0
        assert cmd.delta_pan_deg > 0.0

    def test_independent_axis_deadband(self):
        """
        Verify independent per-axis deadbanding:
          error_x = 2 px (<= 5 px deadband) -> pan = 0
          error_y = 20 px (> 5 px deadband) -> tilt != 0
          in_deadband must be False (composite flag requires both axes in deadband).
        """
        cfg = PTZConfig(deadband_px=5.0)
        controller = ProportionalDeadbandPTZController(ptz_config=cfg)

        cmd = controller.compute(make_track(322.0, 260.0), TrackingState.TRACKING, 640, 480, 0.0333)
        assert cmd.in_deadband is False
        assert cmd.pan_velocity_deg_s == 0.0
        assert cmd.delta_pan_deg == 0.0
        assert cmd.tilt_velocity_deg_s > 0.0
        assert cmd.delta_tilt_deg > 0.0

    def test_proportional_scaling_below_saturation(self):
        """Below rate limits, doubling error must double commanded angular velocity."""
        cfg = PTZConfig(proportional_gain=0.5, deadband_px=0.0, max_pan_speed_deg_s=20.0)
        controller = ProportionalDeadbandPTZController(ptz_config=cfg)

        cmd1 = controller.compute(make_track(330.0, 240.0), TrackingState.TRACKING, 640, 480, 0.0333)
        cmd2 = controller.compute(make_track(340.0, 240.0), TrackingState.TRACKING, 640, 480, 0.0333)

        assert cmd2.pan_velocity_deg_s == pytest.approx(2.0 * cmd1.pan_velocity_deg_s, rel=1e-3)
        assert cmd2.delta_pan_deg == pytest.approx(2.0 * cmd1.delta_pan_deg, rel=1e-3)

    def test_rate_saturation_clamps_at_max_speed(self):
        """Large error or high gain must saturate velocity at configured max speed."""
        cfg = PTZConfig(max_pan_speed_deg_s=5.0, max_tilt_speed_deg_s=5.0, proportional_gain=10.0)
        controller = ProportionalDeadbandPTZController(ptz_config=cfg)

        # Huge error (+200 px offset -> 1.25 deg -> requested 12.5 deg/s > 5.0 deg/s)
        cmd = controller.compute(make_track(520.0, 440.0), TrackingState.TRACKING, 640, 480, 0.0333)

        assert cmd.is_saturated is True
        assert cmd.pan_velocity_deg_s == 5.0
        assert cmd.tilt_velocity_deg_s == 5.0
        # Integrated displacement = max_speed * dt
        assert cmd.delta_pan_deg == pytest.approx(5.0 * 0.0333, rel=1e-3)
        assert cmd.delta_tilt_deg == pytest.approx(5.0 * 0.0333, rel=1e-3)

    def test_asymmetric_rate_limits(self):
        """Pan and tilt can have different maximum speeds."""
        cfg = PTZConfig(max_pan_speed_deg_s=4.0, max_tilt_speed_deg_s=8.0, proportional_gain=10.0)
        controller = ProportionalDeadbandPTZController(ptz_config=cfg)

        cmd = controller.compute(make_track(520.0, 440.0), TrackingState.TRACKING, 640, 480, 0.0333)
        assert cmd.is_saturated is True
        assert cmd.pan_velocity_deg_s == 4.0
        assert cmd.tilt_velocity_deg_s == 8.0


# ---------------------------------------------------------------------------
# 2. Tracking State Behavior Tests
# ---------------------------------------------------------------------------

class TestPTZControllerStates:
    def test_searching_state_produces_zero_command(self):
        controller = ProportionalDeadbandPTZController()
        track = make_track(400.0, 300.0)

        cmd = controller.compute(track, TrackingState.SEARCHING, 640, 480, 0.0333)
        assert cmd.valid is False
        assert cmd.pan_velocity_deg_s == 0.0
        assert cmd.tilt_velocity_deg_s == 0.0
        assert cmd.delta_pan_deg == 0.0
        assert cmd.delta_tilt_deg == 0.0

    def test_acquiring_state_produces_zero_command(self):
        """Per P0 specification, ACQUIRING issues zero command (no premature actuation)."""
        controller = ProportionalDeadbandPTZController()
        track = make_track(400.0, 300.0)

        cmd = controller.compute(track, TrackingState.ACQUIRING, 640, 480, 0.0333)
        assert cmd.valid is False
        assert cmd.pan_velocity_deg_s == 0.0
        assert cmd.tilt_velocity_deg_s == 0.0
        assert cmd.delta_pan_deg == 0.0
        assert cmd.delta_tilt_deg == 0.0

    def test_tracking_state_produces_active_command(self):
        controller = ProportionalDeadbandPTZController()
        track = make_track(400.0, 300.0)

        cmd = controller.compute(track, TrackingState.TRACKING, 640, 480, 0.0333)
        assert cmd.valid is True
        assert cmd.pan_velocity_deg_s > 0.0
        assert cmd.tilt_velocity_deg_s > 0.0

    def test_reacquiring_state_bounded_control_with_valid_estimate(self):
        """REACQUIRING uses the valid coasted tracker estimate to maintain corrective motion."""
        controller = ProportionalDeadbandPTZController()
        coasted_track = make_track(350.0, 240.0, valid=False, coasting=True, confidence=0.5)

        cmd = controller.compute(coasted_track, TrackingState.REACQUIRING, 640, 480, 0.0333)
        assert cmd.valid is True
        assert cmd.pan_velocity_deg_s > 0.0

    def test_reacquiring_state_zero_when_estimate_invalid(self):
        """If tracker has no valid estimate during REACQUIRING, command is zero."""
        controller = ProportionalDeadbandPTZController()
        cmd = controller.compute(None, TrackingState.REACQUIRING, 640, 480, 0.0333)
        assert cmd.valid is False
        assert cmd.pan_velocity_deg_s == 0.0
        assert cmd.delta_pan_deg == 0.0

    def test_lost_state_produces_zero_command(self):
        controller = ProportionalDeadbandPTZController()
        track = make_track(400.0, 300.0)

        cmd = controller.compute(track, TrackingState.LOST, 640, 480, 0.0333)
        assert cmd.valid is False
        assert cmd.pan_velocity_deg_s == 0.0
        assert cmd.tilt_velocity_deg_s == 0.0
        assert cmd.delta_pan_deg == 0.0
        assert cmd.delta_tilt_deg == 0.0


# ---------------------------------------------------------------------------
# 3. Geometry & FOV/Resolution Independence
# ---------------------------------------------------------------------------

class TestPTZControllerGeometry:
    def test_default_resolution_and_fov(self):
        """640x480 resolution with 4°x3° FOV: scale is 4/640 = 0.00625 deg/px."""
        cam_cfg = CameraConfig(width=640, height=480, fov_h_deg=4.0, fov_v_deg=3.0)
        ptz_cfg = PTZConfig(proportional_gain=1.0, deadband_px=0.0)
        controller = ProportionalDeadbandPTZController(ptz_cfg, cam_cfg)

        cmd = controller.compute(make_track(340.0, 240.0), TrackingState.TRACKING, 640, 480, 0.0333)
        # Offset = 20 px -> Angular error = 20 * (4 / 640) = 0.125 deg
        assert cmd.error_pan_deg == pytest.approx(0.125, rel=1e-3)
        assert cmd.pan_velocity_deg_s == pytest.approx(0.125, rel=1e-3)

    def test_hd_resolution_and_fov(self):
        """1280x720 resolution with 8°x4.5° FOV: scale is 8/1280 = 0.00625 deg/px."""
        cam_cfg = CameraConfig(width=1280, height=720, fov_h_deg=8.0, fov_v_deg=4.5)
        ptz_cfg = PTZConfig(proportional_gain=1.0, deadband_px=0.0)
        controller = ProportionalDeadbandPTZController(ptz_cfg, cam_cfg)

        cmd = controller.compute(make_track(680.0, 360.0), TrackingState.TRACKING, 1280, 720, 0.0333)
        # Center is (640, 360). Offset = 40 px -> Angular error = 40 * (8 / 1280) = 0.25 deg
        assert cmd.error_pan_deg == pytest.approx(0.25, rel=1e-3)
        assert cmd.pan_velocity_deg_s == pytest.approx(0.25, rel=1e-3)

    def test_non_square_pixels_and_fov(self):
        """800x600 resolution with 5°x5° square FOV (non-square pixel aspect ratio)."""
        cam_cfg = CameraConfig(width=800, height=600, fov_h_deg=5.0, fov_v_deg=5.0)
        ptz_cfg = PTZConfig(proportional_gain=1.0, deadband_px=0.0)
        controller = ProportionalDeadbandPTZController(ptz_cfg, cam_cfg)

        cmd = controller.compute(make_track(450.0, 350.0), TrackingState.TRACKING, 800, 600, 0.0333)
        # Center is (400, 300).
        # Offset x = 50 px -> 50 * (5/800) = 0.3125 deg
        # Offset y = 50 px -> 50 * (5/600) = 0.41667 deg
        assert cmd.error_pan_deg == pytest.approx(0.3125, rel=1e-3)
        assert cmd.error_tilt_deg == pytest.approx(0.41667, rel=1e-3)

    def test_projection_model_consumed_directly(self):
        """Verify controller directly consumes ProjectionModel.image_to_angles()."""
        pm = ProjectionModel(width=640, height=480, fov_h_deg=4.0, fov_v_deg=3.0)
        ptz_cfg = PTZConfig(proportional_gain=1.0, deadband_px=0.0)
        controller = ProportionalDeadbandPTZController(ptz_cfg, projection_model=pm)

        cmd = controller.compute(
            track_result=make_track(340.0, 260.0),
            tracking_state=TrackingState.TRACKING,
            frame_width=640,
            frame_height=480,
            dt=0.0333,
            projection_model=pm,
        )
        expected_pan, expected_tilt = pm.image_to_angles(340.0, 260.0)
        assert cmd.error_pan_deg == pytest.approx(expected_pan, rel=1e-4)
        assert cmd.error_tilt_deg == pytest.approx(expected_tilt, rel=1e-4)


# ---------------------------------------------------------------------------
# 4. Robustness & Edge Cases
# ---------------------------------------------------------------------------

class TestPTZControllerRobustness:
    def test_none_track_result_safe(self):
        controller = ProportionalDeadbandPTZController()
        cmd = controller.compute(None, TrackingState.TRACKING, 640, 480, 0.0333)
        assert cmd.valid is False
        assert cmd.delta_pan_deg == 0.0
        assert cmd.delta_tilt_deg == 0.0

    def test_nan_coordinates_safe(self):
        controller = ProportionalDeadbandPTZController()
        track = make_track(float("nan"), 240.0)
        cmd = controller.compute(track, TrackingState.TRACKING, 640, 480, 0.0333)
        assert cmd.valid is False
        assert cmd.delta_pan_deg == 0.0

    def test_inf_coordinates_safe(self):
        controller = ProportionalDeadbandPTZController()
        track = make_track(320.0, float("inf"))
        cmd = controller.compute(track, TrackingState.TRACKING, 640, 480, 0.0333)
        assert cmd.valid is False
        assert cmd.delta_tilt_deg == 0.0

    def test_zero_or_negative_dt_safe(self):
        controller = ProportionalDeadbandPTZController()
        track = make_track(350.0, 240.0)

        # dt = 0.0 -> displacement must be 0.0
        cmd0 = controller.compute(track, TrackingState.TRACKING, 640, 480, 0.0)
        assert cmd0.delta_pan_deg == 0.0

        # dt < 0.0 -> clamped to 0.0 displacement
        cmd_neg = controller.compute(track, TrackingState.TRACKING, 640, 480, -0.05)
        assert cmd_neg.delta_pan_deg == 0.0

    def test_invalid_dimensions_safe(self):
        controller = ProportionalDeadbandPTZController()
        track = make_track(350.0, 240.0)
        cmd = controller.compute(track, TrackingState.TRACKING, 0, 0, 0.0333)
        assert cmd.valid is False

    def test_reset_clears_diagnostics(self):
        controller = ProportionalDeadbandPTZController()
        controller.compute(make_track(350.0, 240.0), TrackingState.TRACKING, 640, 480, 0.0333)
        assert controller.total_commands == 1
        assert controller.last_command is not None

        controller.reset()
        assert controller.total_commands == 0
        assert controller.last_command is None


# ---------------------------------------------------------------------------
# 5. Architecture & Ground-Truth Firewall Tests
# ---------------------------------------------------------------------------

class TestPTZControllerFirewall:
    def test_firewall_zero_ground_truth_ast(self):
        """Verify Module 14 has zero imports of GroundTruth or src.simulation."""
        import src.control.ptz_controller as mod
        source_file = inspect.getfile(mod)
        with open(source_file, "r") as f:
            tree = ast.parse(f.read(), filename=source_file)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod_name = getattr(node, "module", "") or ""
                assert "GroundTruth" not in mod_name, f"GroundTruth imported in {mod_name}"
                assert "src.simulation" not in mod_name, f"src.simulation imported in {mod_name}"

    def test_single_actuation_ownership(self):
        """
        Verify PTZController only generates PTZCommand and does NOT actuate CameraModel.
        Actuation is strictly owned by the simulation loop / AppController.
        """
        cam = CameraModel()
        init_pan, init_tilt = cam.pan_deg, cam.tilt_deg
        init_x, init_y = cam.world_position

        controller = ProportionalDeadbandPTZController()
        track = make_track(400.0, 300.0)

        # Compute command
        cmd = controller.compute(track, TrackingState.TRACKING, 640, 480, 0.0333)
        assert cmd.valid is True
        assert cmd.delta_pan_deg > 0.0

        # CameraModel must be unchanged
        assert cam.pan_deg == init_pan
        assert cam.tilt_deg == init_tilt
        assert cam.world_position == (init_x, init_y)

        # Only when explicitly applied by application loop does camera pose change
        cam.apply_pan_tilt(cmd.delta_pan_deg, cmd.delta_tilt_deg)
        assert cam.pan_deg > init_pan
        assert cam.tilt_deg > init_tilt


# ---------------------------------------------------------------------------
# 6. Performance Benchmark (Not a Hard Failure Gate)
# ---------------------------------------------------------------------------

class TestPTZControllerPerformance:
    def test_controller_latency_benchmark(self):
        """Measure PTZ compute execution latency over 1000 iterations."""
        controller = ProportionalDeadbandPTZController()
        track = make_track(350.0, 260.0)

        latencies_ms = []
        for _ in range(1000):
            t0 = time.perf_counter()
            controller.compute(track, TrackingState.TRACKING, 640, 480, 0.0333)
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        mean_lat = sum(latencies_ms) / len(latencies_ms)
        max_lat = max(latencies_ms)

        # Print latency as engineering benchmark
        print(f"\n[PTZ Benchmark] Mean Latency: {mean_lat:.4f} ms, Max Latency: {max_lat:.4f} ms")
        assert mean_lat >= 0.0


# ---------------------------------------------------------------------------
# 7. Closed-Loop Simulation Integration Test
# ---------------------------------------------------------------------------

class TestPTZControllerClosedLoopIntegration:
    def test_closed_loop_target_centering(self):
        """
        Closed-loop integration test:
          FrameProvider -> Detector -> Centroid -> Identifier -> Tracker -> State -> PTZ -> CameraModel.apply_pan_tilt.
        Verifies:
          1. Initial error is recorded.
          2. Final error is lower than initial error.
          3. Target reaches/enters deadband.
          4. Commands never exceed rate limits.
          5. Camera pose updates remain bounded.
        """
        cfg = SystemConfig()
        cfg.simulation.random_seed = 42
        cfg.camera.width = 640
        cfg.camera.height = 480
        cfg.camera.fov_h_deg = 4.0
        cfg.camera.fov_v_deg = 3.0
        # Camera starts at (1000, 1000). Target placed off-center at (1030, 1020) and stationary.
        cfg.target.initial_position = "custom"
        cfg.target.initial_x = 1030.0
        cfg.target.initial_y = 1020.0
        cfg.target.speed = 0.0
        cfg.target.size = 12
        cfg.target.intensity = 220
        cfg.scene.background_intensity = 30
        cfg.ptz.proportional_gain = 1.0
        cfg.ptz.deadband_px = 5.0
        cfg.ptz.max_pan_speed_deg_s = 5.0
        cfg.ptz.max_tilt_speed_deg_s = 5.0

        sim_provider = SimulationFrameProvider.from_config(cfg)
        detector = P0ThresholdDetector(cfg.detector)
        identifier = CandidateIdentifier(cfg.identifier)
        centroid_estimator = IntensityWeightedCentroidEstimator(cfg.centroid)
        tracker = ConstantVelocityKalmanTracker(cfg.tracker)
        state_mgr = TrackingStateManager(cfg.state)
        ptz_ctrl = ProportionalDeadbandPTZController(cfg.ptz, cfg.camera)

        dt = 1.0 / 30.0
        errors = []
        commands = []
        deadband_reached_frame = None

        # Run 60 frames of closed-loop tracking and actuation
        for f in range(60):
            packet = sim_provider.get_next_frame()
            assert packet is not None

            # 1. Detection
            det_res = detector.detect(packet)

            # 2. Identification
            pred_pos = tracker.predict() if tracker.is_initialized else None
            ident_res = identifier.identify(
                det_res.candidates,
                predicted_position=pred_pos,
                current_state=state_mgr.current_state,
                frame_number=f,
                timestamp=packet.timestamp,
            )

            # 3. Centroiding
            cent_res = None
            if ident_res.valid and ident_res.selected_candidate is not None:
                cent_res = centroid_estimator.estimate(packet, ident_res.selected_candidate)

            # 4. Temporal Tracking
            track_res = tracker.update(cent_res, dt=dt, frame_number=f, timestamp=packet.timestamp)

            # 5. State Management
            state_res = state_mgr.update(track_res, timestamp=packet.timestamp)

            # 6. PTZ Control
            cmd = ptz_ctrl.compute(
                track_res,
                state_res.state,
                packet.width,
                packet.height,
                dt=dt,
                projection_model=sim_provider._camera_model.projection_model,
            )
            commands.append(cmd)

            # Record tracking error relative to image center (320, 240)
            if cent_res and cent_res.valid:
                err = math.hypot(cent_res.x - 320.0, cent_res.y - 240.0)
                errors.append(err)
                if cmd.in_deadband and deadband_reached_frame is None:
                    deadband_reached_frame = f

            # 7. Actuation (Benchmark-1 application loop owns camera actuation)
            if cmd.valid:
                # Assert rate limit strictly respected
                assert abs(cmd.pan_velocity_deg_s) <= cfg.ptz.max_pan_speed_deg_s + 1e-6
                assert abs(cmd.tilt_velocity_deg_s) <= cfg.ptz.max_tilt_speed_deg_s + 1e-6
                sim_provider._camera_model.apply_pan_tilt(cmd.delta_pan_deg, cmd.delta_tilt_deg)

        # 1. Initial error recorded
        assert len(errors) > 0
        initial_error = errors[0]
        final_error = errors[-1]

        # 2. Final error is lower than initial error
        assert final_error < initial_error

        # 3. System demonstrates convergence into deadband
        assert deadband_reached_frame is not None, f"Target did not enter deadband: final_error={final_error:.2f}px"

        # 4. Camera pose updates remain bounded
        cam_x, cam_y = sim_provider._camera_model.world_position
        assert 990.0 <= cam_x <= 1050.0
        assert 990.0 <= cam_y <= 1050.0

# ---------------------------------------------------------------------------
# 8. Type Safety Regression Test
# ---------------------------------------------------------------------------

class TestPTZControllerTypeSafety:
    def test_type_mismatch_raises_error(self):
        """Passing StateDecision instead of TrackingState must raise TypeError."""
        from src.frame.data_contracts import StateDecision
        
        controller = ProportionalDeadbandPTZController()
        track = make_track(400.0, 300.0)
        
        invalid_state = StateDecision(
            state=TrackingState.SEARCHING,
            previous_state=TrackingState.SEARCHING,
            transition_reason="init"
        )
        
        with pytest.raises(TypeError, match="tracking_state must be a TrackingState enum"):
            controller.compute(track, invalid_state, 640, 480, 0.0333) # type: ignore
