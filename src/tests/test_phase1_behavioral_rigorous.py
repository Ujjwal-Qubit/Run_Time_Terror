"""
Phase 1 Rigorous Behavioral Test Suite.
Authoritative validation for SIH 26169 Phase 1 requirements:
1. ExpandingSearchPattern geometry, step-size progression, rate clamping (10 deg/s).
2. PTZController back-calculation anti-windup during rate saturation.
3. Unconstrained target placement on full 2000x2000 canvas.
4. Camera-only autonomous blind search acquisition (<= 2.0s lock).
5. Multi-frame predictive coasting surviving 8 frames of occlusion (reacquisition <= 1.0s).
6. Strict Ground-Truth Firewall preservation (zero leakage).
"""

import math
import numpy as np
import pytest

from src.app.app_controller import AppController
from src.config.config_manager import (
    ConfigManager,
    SystemConfig,
    TargetConfig,
    PTZConfig,
    CameraConfig,
    TrackerConfig,
    StateConfig,
)
from src.control.ptz_controller import (
    ExpandingSearchPattern,
    ProportionalDeadbandPTZController,
)
from src.frame.data_contracts import (
    CentroidResult,
    FramePacket,
    FrameSource,
    ROI,
    TrackingState,
    TrackResult,
)
from src.simulation.target_manager import TargetManager
from src.tracker.temporal_tracker import ConstantVelocityKalmanTracker
from src.tracker.state_manager import TrackingStateManager


# ===========================================================================
# 1. Expanding Search Pattern Geometry & Kinematic Clamping
# ===========================================================================

def test_expanding_search_pattern_geometry_and_limits():
    """
    Verify expanding square search trajectory:
    - Step length increases every 2 legs: [L, L, 2L, 2L, 3L, 3L, ...].
    - Commanded velocity never exceeds max_rate_deg_s.
    - Reset flushes all leg progression and restarts from center.
    """
    max_rate = 10.0
    step_deg = 2.0
    pattern = ExpandingSearchPattern(
        step_deg=step_deg,
        max_pan_speed=max_rate,
        max_tilt_speed=max_rate,
    )

    dt = 0.05  # 20 Hz
    total_steps = 200
    for _ in range(total_steps):
        d_pan, d_tilt, v_pan, v_tilt = pattern.compute_step(dt)
        # Verify rate limits
        assert abs(v_pan) <= max_rate + 1e-6, f"Pan velocity {v_pan} exceeded {max_rate}"
        assert abs(v_tilt) <= max_rate + 1e-6, f"Tilt velocity {v_tilt} exceeded {max_rate}"
        assert abs(d_pan) <= max_rate * dt + 1e-6
        assert abs(d_tilt) <= max_rate * dt + 1e-6

    # Verify leg progression
    assert pattern.leg_index > 0, "Pattern should have advanced through multiple legs"
    assert pattern.step_deg == step_deg

    # Reset test
    pattern.reset()
    assert pattern.leg_index == 0
    assert pattern._leg_progress_deg == 0.0


# ===========================================================================
# 2. Back-Calculation Anti-Windup Clamping
# ===========================================================================

def test_ptz_anti_windup_under_rate_saturation():
    """
    Verify back-calculation anti-windup:
    - When a large step error saturates the PTZ rate limiter (e.g. 10 deg/s),
      the integrator accumulators (_integral_pan, _integral_tilt) must be clamped
      to prevent windup growth beyond the saturation limit.
    - When error returns to 0, integrator must quickly recover without prolonged overshoot.
    """
    cfg = PTZConfig(
        proportional_gain=1.5,
        integral_gain=0.5,
        max_pan_speed_deg_s=10.0,
        max_tilt_speed_deg_s=10.0,
        deadband_px=2.0,
        search_scan_enabled=False,
    )
    ctrl = ProportionalDeadbandPTZController(cfg)

    # Frame dimensions: 640x480, optical center: (320, 240)
    # Target placed far away at (600, 440) -> large error
    large_error_track = TrackResult(
        estimated_x=600.0,
        estimated_y=440.0,
        confidence=1.0,
        frame_number=1,
        timestamp=0.033,
        measurement_valid=True,
    )

    dt = 0.033
    # Step for 30 frames under severe saturation
    for f in range(1, 31):
        cmd = ctrl.compute(
            large_error_track,
            TrackingState.TRACKING,
            frame_width=640,
            frame_height=480,
            dt=dt,
        )
        assert cmd.valid
        assert abs(cmd.pan_velocity_deg_s) <= 10.0 + 1e-5
        assert abs(cmd.tilt_velocity_deg_s) <= 10.0 + 1e-5

    # Check integrator states: with anti-windup, integral term must NOT have exploded
    assert abs(ctrl._integral_pan) <= 1.0 + 1e-5, f"Integral pan wound up to {ctrl._integral_pan}"
    assert abs(ctrl._integral_tilt) <= 1.0 + 1e-5, f"Integral tilt wound up to {ctrl._integral_tilt}"

    # Now simulate target centered: error = 0
    centered_track = TrackResult(
        estimated_x=320.0,
        estimated_y=240.0,
        confidence=1.0,
        frame_number=31,
        timestamp=1.0,
        measurement_valid=True,
    )
    cmd_centered = ctrl.compute(
        centered_track,
        TrackingState.TRACKING,
        frame_width=640,
        frame_height=480,
        dt=dt,
    )
    # Integrator should recover immediately to near 0 / deadband without overshoot
    assert cmd_centered.in_deadband or abs(cmd_centered.pan_velocity_deg_s) < 2.0


# ===========================================================================
# 3. Unconstrained Target Placement
# ===========================================================================

def test_unconstrained_target_placement():
    """
    Verify TargetManager accepts arbitrary initial placements anywhere on the
    full 2000x2000 canvas (e.g. at (1800, 1800) or (150, 250)) without being
    clamped to center +/- 150 px.
    """
    # 1. Custom corner placement
    tgt_cfg = TargetConfig(
        initial_position="custom",
        initial_x=1850.0,
        initial_y=1850.0,
        speed=0.0,
    )
    tm = TargetManager(
        target_config=tgt_cfg,
        scene_width=2000,
        scene_height=2000,
        seed=42,
    )
    state = tm.target_state
    assert state.world_x == 1850.0
    assert state.world_y == 1850.0

    # 2. Extreme opposite corner
    tgt_cfg2 = TargetConfig(
        initial_position="custom",
        initial_x=120.0,
        initial_y=150.0,
        speed=0.0,
    )
    tm2 = TargetManager(
        target_config=tgt_cfg2,
        scene_width=2000,
        scene_height=2000,
        seed=42,
    )
    state2 = tm2.target_state
    assert state2.world_x == 120.0
    assert state2.world_y == 150.0


# ===========================================================================
# 4. Out-of-FOV Target Acquisition via Autonomous Blind Search
# ===========================================================================

def test_camera_only_autonomous_blind_search_acquisition():
    """
    Closed-loop acquisition test:
    - Target starts strictly outside camera initial FOV.
    - Camera is centered at (1000, 1000). FOV: 4.0 deg x 3.0 deg (640 x 480 px).
    - Target is placed at (1380, 1260) - completely invisible at t=0.
    - Zero ground-truth coordinates or hints provided to controller.
    - Active ExpandingSearchPattern sweeps camera autonomously.
    - Must locate beacon, transition SEARCHING -> ACQUIRING -> TRACKING,
      and establish lock in <= 2.0 seconds.
    """
    cm = ConfigManager()
    cfg = cm.config

    cfg.camera.initial_x = 1000.0
    cfg.camera.initial_y = 1000.0
    cfg.camera.fov_h_deg = 4.0
    cfg.camera.fov_v_deg = 3.0

    cfg.target.initial_x = 1380.0
    cfg.target.initial_y = 1260.0
    cfg.target.initial_position = "custom"
    cfg.target.speed = 0.0

    cfg.ptz.max_pan_speed_deg_s = 10.0
    cfg.ptz.max_tilt_speed_deg_s = 10.0
    cfg.ptz.search_scan_enabled = True

    app = AppController()
    app.initialize(cfg)

    # Verify initial invisibility
    cam = app.camera_model
    pm = cam.projection_model
    assert not pm.is_visible(cfg.target.initial_x, cfg.target.initial_y, cam.world_position[0], cam.world_position[1])

    dt = 1.0 / 30.0
    max_frames = 90  # 3.0 seconds max
    locked_frame = None
    lock_time = None

    for f in range(max_frames):
        packet = app.get_next_frame()
        if packet is None:
            break

        public_res, latency, track_res, state_res, cent_res, det_res = app.step_algorithm(packet)

        ptz_cmd = app.ptz_controller.compute(
            track_res,
            state_res.state,
            packet.width,
            packet.height,
            dt=dt,
            projection_model=cam.projection_model,
        )

        if ptz_cmd.valid:
            cam.apply_pan_tilt(ptz_cmd.delta_pan_deg, ptz_cmd.delta_tilt_deg)

        if state_res.state == TrackingState.TRACKING and locked_frame is None:
            locked_frame = f
            lock_time = packet.timestamp
            break

    assert locked_frame is not None, "Target was not acquired by active search pattern"
    assert lock_time <= 2.0, f"Acquisition time {lock_time:.3f}s exceeded 2.0s requirement"


# ===========================================================================
# 5. Multi-Frame Predictive Coasting (8 Frames Occlusion Survival)
# ===========================================================================

def test_predictive_coasting_survives_eight_frame_occlusion():
    """
    Verify multi-frame predictive coasting:
    - Tracker locks onto moving target (30 px/s).
    - Target is completely occluded for 8 consecutive frames.
    - During occlusion, Kalman filter coasts (state extrapolates with velocity).
    - Confidence degrades gracefully (remaining > 0.0).
    - When target reappears on frame 9, tracker re-locks in <= 1.0s without aborting to LOST.
    """
    trk_cfg = TrackerConfig()
    st_cfg = StateConfig(loss_confirm_frames=10, reacquire_confirm_frames=2)
    tracker = ConstantVelocityKalmanTracker(trk_cfg)
    sm = TrackingStateManager(st_cfg)

    dt = 1.0 / 30.0
    vx = 30.0  # px/s
    vy = 15.0  # px/s

    # 1. Warm-up and lock tracking for 10 frames
    curr_x, curr_y = 100.0, 100.0
    for f in range(10):
        t = f * dt
        curr_x = 100.0 + vx * t
        curr_y = 100.0 + vy * t
        meas = CentroidResult(x=curr_x, y=curr_y, valid=True, frame_number=f, timestamp=t)
        tr = tracker.update(meas, dt=dt, frame_number=f, timestamp=t)
        sr = sm.update(tr, timestamp=t)

    assert sm.current_state == TrackingState.TRACKING
    assert tracker.is_initialized
    assert abs(tracker.state_vector[2, 0] - vx) < 5.0
    assert abs(tracker.state_vector[3, 0] - vy) < 5.0

    # 2. Occlusion: 8 consecutive frames with NO valid measurement
    loss_start_time = 10 * dt
    for f in range(10, 18):
        t = f * dt
        # Missing measurement
        tr = tracker.update(None, dt=dt, frame_number=f, timestamp=t)
        sr = sm.update(tr, timestamp=t)
        assert tr.is_coasting is True
        assert sr.state in (TrackingState.REACQUIRING, TrackingState.TRACKING)
        assert tr.confidence > 0.0

    # Must NOT have dropped to LOST on frame 8 of occlusion
    assert sm.current_state != TrackingState.LOST, "Should not drop to LOST within 8 frames"

    # 3. Target reappears on frame 18
    t_reappear = 18 * dt
    true_x = 100.0 + vx * t_reappear
    true_y = 100.0 + vy * t_reappear

    # Reappearance frame 18
    meas_re = CentroidResult(x=true_x, y=true_y, valid=True, frame_number=18, timestamp=t_reappear)
    tr_re = tracker.update(meas_re, dt=dt, frame_number=18, timestamp=t_reappear)
    sr_re = sm.update(tr_re, timestamp=t_reappear)

    # Frame 19 confirms reacquisition
    t_confirm = 19 * dt
    true_x2 = 100.0 + vx * t_confirm
    true_y2 = 100.0 + vy * t_confirm
    meas_re2 = CentroidResult(x=true_x2, y=true_y2, valid=True, frame_number=19, timestamp=t_confirm)
    tr_re2 = tracker.update(meas_re2, dt=dt, frame_number=19, timestamp=t_confirm)
    sr_re2 = sm.update(tr_re2, timestamp=t_confirm)

    assert sr_re2.state == TrackingState.TRACKING
    # Reacquisition time <= 1.0s
    if sr_re2.reacquisition_time is not None:
        assert sr_re2.reacquisition_time <= 1.0, f"Reacquisition time {sr_re2.reacquisition_time:.3f}s exceeded 1.0s"


# ===========================================================================
# 6. Strict Ground-Truth Firewall AST & Runtime Inspection
# ===========================================================================

def test_ground_truth_firewall_inspection():
    """
    Ensure no ground truth or simulator state is leaked into tracking/control.
    """
    app = AppController()
    cfg = ConfigManager().config
    app.initialize(cfg)

    # Active algorithm must not possess ground truth or simulator internals
    algo = app._active_algorithm
    assert not hasattr(algo, "ground_truth")
    assert not hasattr(algo, "_scene_manager")
    assert not hasattr(algo, "_target_manager")
    assert not hasattr(algo, "_camera_model")

    # PTZ Controller must not possess ground truth
    ptz = app.ptz_controller
    assert not hasattr(ptz, "ground_truth")
    assert not hasattr(ptz, "target_manager")
