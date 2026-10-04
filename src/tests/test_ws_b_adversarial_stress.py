"""
Adversarial Kinematics & Continuous Deadband Stress Testing Suite for Workstream B.
Created by Challenger 1 (critic, specialist) to empirically falsify:
  1. DEF-19: C0 Continuity and Boundary Smoothness in PTZController deadband law.
  2. DEF-15: Motion Type Enum, Dotted String, Alias Mutation & Invalid String Fallback.
  3. Multi-Beacon Kinematic Trajectory Integrity over 2,000 steps across all patterns.

Empirical Invariant: If a bug cannot be reproduced empirically, it does not count.
"""

import math
from typing import List, Tuple, Any, Optional
import numpy as np
import pytest

from src.frame.data_contracts import (
    MotionType,
    TrackingState,
    TrackResult,
)
from src.config.config_manager import (
    PTZConfig,
    TargetConfig,
    MotionConfig,
    BeaconConfig,
)
from src.config import defaults
from src.control.ptz_controller import PTZController
from src.simulation.target_manager import (
    TargetManager,
    MultiBeaconManager,
    _SecondaryBeaconKinematics,
)


def _create_track_result(x: float, y: float) -> TrackResult:
    return TrackResult(
        estimated_x=x,
        estimated_y=y,
        velocity_x=0.0,
        velocity_y=0.0,
        confidence=1.0,
        track_age=10,
        predicted_x=x,
        predicted_y=y,
        frame_number=1,
        timestamp=0.04,
        measurement_valid=True,
    )


# =============================================================================
# STRESS TEST 1: C0 Continuity Falsification (DEF-19)
# =============================================================================

class TestDEF19DeadbandC0ContinuityFalsification:
    """Empirical falsification harness for PTZ continuous deadband control."""

    def test_continuous_deadband_sweep_and_boundary_c0_continuity(self) -> None:
        """
        Stress Test 1A: C0 Continuity Across Deadband Boundary.
        Sweeps error from 1.0 to 3.0 in steps of 0.001 with deadband = 2.0.
        Asserts:
          - Velocity command is strictly 0.0 deg/s when |err| <= deadband.
          - Delta omega across the boundary step (2.000 -> 2.001) is < 0.05 deg/s.
          - Maximum step across the entire sweep is < 0.05 deg/s.
        """
        ptz_cfg = PTZConfig(deadband_px=2.0, proportional_gain=50.0, integral_gain=0.0)
        ctrl = PTZController(ptz_config=ptz_cfg)

        frame_w = 640
        frame_h = 480
        cx = frame_w / 2.0
        cy = frame_h / 2.0

        errors = np.arange(1.0, 3.0001, 0.001)
        omegas = []

        for err in errors:
            track = _create_track_result(cx + err, cy)
            cmd = ctrl.compute(track, TrackingState.TRACKING, frame_w, frame_h, 0.04)
            omegas.append(cmd.pan_velocity_deg_s)

        omegas = np.array(omegas)

        # 1. Inside deadband: strictly 0.0 deg/s
        inside_mask = errors <= 2.0
        assert np.all(omegas[inside_mask] == 0.0), (
            f"Non-zero velocity detected inside deadband: {omegas[inside_mask]}"
        )

        # 2. Boundary step: between 2.000 and 2.001
        idx_boundary = np.where(np.isclose(errors, 2.0, atol=1e-5))[0][0]
        step_omega = omegas[idx_boundary + 1] - omegas[idx_boundary]

        # Empirical expectation: kp * (0.001 * 4.0 / 640) = 50 * 6.25e-6 = 0.0003125 deg/s
        assert step_omega < 0.05, (
            f"Boundary step Delta omega = {step_omega:.6f} deg/s exceeds threshold 0.05 deg/s!"
        )

        # 3. Maximum step across the entire sweep
        max_delta = float(np.max(np.abs(np.diff(omegas))))
        assert max_delta < 0.05, (
            f"Maximum step Delta omega = {max_delta:.6f} deg/s exceeds threshold 0.05 deg/s!"
        )

    def test_legacy_discontinuous_law_contrast(self) -> None:
        """
        Stress Test 1B: Contrast against legacy discontinuous control law.
        Proves that the legacy law produced a step impulse of ~0.3125 deg/s
        (or ~0.625 deg/s for deadband=2.0), which would violate Delta omega < 0.05 deg/s.
        """
        deadband = 1.0  # Default deadband
        kp = 50.0
        deg_per_px = 4.0 / 640.0  # 0.00625 deg/px

        # Legacy law computation at deadband and deadband + 0.001
        err_inside = 1.0
        err_outside = 1.001

        legacy_omega_inside = 0.0
        legacy_omega_outside = kp * err_outside * deg_per_px  # No subtraction of deadband

        legacy_delta_omega = legacy_omega_outside - legacy_omega_inside

        # Verify legacy law step impulse is ~0.3128 deg/s
        assert abs(legacy_delta_omega - 0.3128125) < 1e-4
        assert legacy_delta_omega > 0.05, (
            "Legacy law unexpectedly met the C0 threshold — check test formulation."
        )

    def test_continuous_deadband_negative_and_tilt_axes(self) -> None:
        """
        Stress Test 1C: Symmetry verification on negative pan and tilt axes.
        Verifies smooth linear ramp transition on negative errors and y-axis.
        """
        ptz_cfg = PTZConfig(deadband_px=1.5, proportional_gain=50.0, integral_gain=0.0)
        ctrl = PTZController(ptz_config=ptz_cfg)

        cx, cy = 320.0, 240.0

        # Negative pan axis
        track_in = _create_track_result(cx - 1.5, cy)
        cmd_in = ctrl.compute(track_in, TrackingState.TRACKING, 640, 480, 0.04)
        assert cmd_in.pan_velocity_deg_s == 0.0

        track_out = _create_track_result(cx - 1.501, cy)
        cmd_out = ctrl.compute(track_out, TrackingState.TRACKING, 640, 480, 0.04)
        assert cmd_out.pan_velocity_deg_s < 0.0
        assert abs(cmd_out.pan_velocity_deg_s) < 0.05

        # Tilt axis
        track_tilt_in = _create_track_result(cx, cy + 1.5)
        cmd_tilt_in = ctrl.compute(track_tilt_in, TrackingState.TRACKING, 640, 480, 0.04)
        assert cmd_tilt_in.tilt_velocity_deg_s == 0.0

        track_tilt_out = _create_track_result(cx, cy + 1.501)
        cmd_tilt_out = ctrl.compute(track_tilt_out, TrackingState.TRACKING, 640, 480, 0.04)
        assert cmd_tilt_out.tilt_velocity_deg_s > 0.0
        assert abs(cmd_tilt_out.tilt_velocity_deg_s) < 0.05


# =============================================================================
# STRESS TEST 2: Motion Type Enum / Alias Mutation Stress (DEF-15)
# =============================================================================

class TestDEF15MotionTypeEnumAliasMutationStress:
    """Adversarial stress testing of motion type normalization and kinematics."""

    VALID_MUTATION_CASES = [
        # Enums
        ("Enum STRAIGHT_LINE", MotionType.STRAIGHT_LINE, False),
        ("Enum CIRCULAR", MotionType.CIRCULAR, False),
        ("Enum FIGURE_8", MotionType.FIGURE_8, False),
        ("Enum RANDOM", MotionType.RANDOM, True),
        # Dotted strings
        ("Dotted MotionType.FIGURE_8", "MotionType.FIGURE_8", False),
        ("Dotted MotionType.CIRCULAR", "MotionType.CIRCULAR", False),
        ("Dotted MotionType.STRAIGHT_LINE", "MotionType.STRAIGHT_LINE", False),
        ("Dotted MotionType.RANDOM", "MotionType.RANDOM", True),
        # Lowercase aliases
        ("Alias linear", "linear", False),
        ("Alias straight", "straight", False),
        ("Alias figure8", "figure8", False),
        ("Alias brownian", "brownian", True),
        ("Alias random", "random", True),
        # None
        ("None fallback", None, False),
    ]

    @pytest.mark.parametrize("label,m_input,is_brownian", VALID_MUTATION_CASES)
    def test_valid_motion_mutations_1000_frames(self, label: str, m_input: Any, is_brownian: bool) -> None:
        """
        Stress Test 2A: 1,000 frames under each valid motion type representation.
        Asserts:
          - Zero AttributeError across TargetManager and MultiBeaconManager.
          - Zero unexpected Brownian fallbacks.
          - Deterministic continuous trajectories for deterministic patterns.
          - Coordinates remain strictly bounded within 2000x2000 canvas.
        """
        # 1. TargetManager stress
        tm = TargetManager(
            target_config=TargetConfig(speed=50.0),
            motion_config=MotionConfig(motion_type=m_input),
            scene_width=2000,
            scene_height=2000,
            seed=42,
        )
        for _ in range(1000):
            st = tm.step(0.04)
            assert 0.0 <= st.world_x <= 2000.0, f"TargetManager breached X bound: {st.world_x}"
            assert 0.0 <= st.world_y <= 2000.0, f"TargetManager breached Y bound: {st.world_y}"

        # 2. MultiBeaconManager stress
        prim = BeaconConfig(role="primary", motion_type=m_input, speed=50.0)
        sec = BeaconConfig(role="secondary", motion_type=m_input, speed=40.0)
        mbm = MultiBeaconManager(
            beacon_configs=[prim, sec],
            motion_config=MotionConfig(motion_type=m_input),
            scene_width=2000,
            scene_height=2000,
            seed=42,
        )

        sec_kin = mbm._secondaries[0]
        sec_vxs = []

        for _ in range(1000):
            mbm.step(0.04)
            states = mbm.get_all_beacon_states()
            for x, y, _ in states:
                assert 0.0 <= x <= 2000.0, f"MultiBeaconManager breached bounds: x={x}"
                assert 0.0 <= y <= 2000.0, f"MultiBeaconManager breached bounds: y={y}"
            sec_vxs.append(sec_kin.state.vx)

        # Check Brownian behavior
        if not is_brownian and sec_kin._motion_type not in ("CIRCULAR", "FIGURE_8"):
            # Straight-line motion must have constant vx except for boundary bounces
            unique_vxs = len(set(round(v, 4) for v in sec_vxs))
            # At most 2 velocities (+v, -v) for straight line
            assert unique_vxs <= 2, (
                f"Unexpected velocity variation in deterministic motion: {unique_vxs} unique vx values"
            )

    def test_invalid_string_mutation_falsification(self) -> None:
        """
        Stress Test 2B: Invalid Motion String Fallback Falsification.
        Falsifies the claim that invalid strings safely fall back to STRAIGHT_LINE.
        Demonstrates that:
          1. TargetManager._normalize_motion_type("foobar") returns "FOOBAR", not "STRAIGHT_LINE".
          2. TargetManager.step() with an invalid string lacks boundary reflection,
             drifting out of the 2000x2000 canvas.
          3. _SecondaryBeaconKinematics falls back to RANDOM (Brownian motion)
             instead of STRAIGHT_LINE.
        """
        invalid_str = "invalid_drift_pattern"

        # 1. Normalization check: should normalize to STRAIGHT_LINE, but currently returns raw string
        normalized = TargetManager._normalize_motion_type(invalid_str)

        # 2. TargetManager boundary containment check
        tm = TargetManager(
            target_config=TargetConfig(speed=50.0),
            motion_config=MotionConfig(motion_type=invalid_str),
            scene_width=2000,
            scene_height=2000,
            seed=42,
        )
        for _ in range(1000):
            tm.step(0.04)

        tm_escaped = not (0.0 <= tm.world_position[0] <= 2000.0)

        # 3. Secondary beacon Brownian fallback check
        mbm = MultiBeaconManager(
            beacon_configs=[
                BeaconConfig(role="primary", motion_type=invalid_str, speed=50.0),
                BeaconConfig(role="secondary", motion_type=invalid_str, speed=40.0),
            ],
            motion_config=MotionConfig(motion_type=invalid_str),
            scene_width=2000,
            scene_height=2000,
            seed=42,
        )
        sec_kin = mbm._secondaries[0]
        sec_vxs = []
        for _ in range(1000):
            mbm.step(0.04)
            sec_vxs.append(sec_kin.state.vx)

        unique_sec_vxs = len(set(round(v, 4) for v in sec_vxs))
        unexpected_brownian = unique_sec_vxs > 10

        # Empirical findings recorded
        print(f"\n[DEF-15 Falsification Report]")
        print(f"  Input: {invalid_str!r}")
        print(f"  Normalized string: {normalized!r} (expected 'STRAIGHT_LINE')")
        print(f"  Primary Target Final X: {tm.world_position[0]:.2f} (Canvas limit: 2000.0, Escaped: {tm_escaped})")
        print(f"  Secondary Beacon Unique Vx: {unique_sec_vxs} (Unexpected Brownian: {unexpected_brownian})")

        # Verification check: implementation successfully guarantees safe STRAIGHT_LINE fallback
        is_safe_straight_line = (
            normalized == "STRAIGHT_LINE"
            and not tm_escaped
            and not unexpected_brownian
        )
        assert is_safe_straight_line, (
            "Implementation failed to safely fallback to STRAIGHT_LINE for invalid motion strings."
        )


# =============================================================================
# STRESS TEST 3: Multi-Beacon Kinematic Trajectory Integrity (2,000 steps)
# =============================================================================

class TestMultiBeaconKinematicIntegrity2000Steps:
    """Stress testing multi-beacon trajectory integrity over extended horizons."""

    @pytest.mark.parametrize("pattern", ["STRAIGHT_LINE", "CIRCULAR", "FIGURE_8"])
    def test_multi_beacon_2000_steps_trajectory_bounds_and_continuity(self, pattern: str) -> None:
        """
        Stress Test 3A: 2,000 steps across canonical patterns.
        Asserts:
          - Zero coordinate breach beyond the 2000x2000 canvas bounds.
          - Zero discontinuous jumps (|Delta pos| <= max_step_bound).
        """
        speed = 50.0
        dt = 0.04
        mbm = MultiBeaconManager(
            beacon_configs=[
                BeaconConfig(role="primary", motion_type=pattern, speed=speed),
                BeaconConfig(role="secondary", motion_type=pattern, speed=speed * 0.8),
            ],
            motion_config=MotionConfig(motion_type=pattern),
            scene_width=2000,
            scene_height=2000,
            seed=42,
        )

        prev_states = None
        max_jump = 0.0
        max_allowed_jump = speed * dt * 2.0 + 1.0  # conservative boundary for bounce/accel

        for step in range(2000):
            mbm.step(dt)
            states = mbm.get_all_beacon_states()
            assert len(states) == 2, f"Expected 2 beacon states, got {len(states)}"

            for idx, (x, y, _) in enumerate(states):
                assert 0.0 <= x <= 2000.0, (
                    f"Pattern {pattern} breached X bound at step {step}: x={x}"
                )
                assert 0.0 <= y <= 2000.0, (
                    f"Pattern {pattern} breached Y bound at step {step}: y={y}"
                )

                if prev_states is not None:
                    px, py, _ = prev_states[idx]
                    jump = math.hypot(x - px, y - py)
                    if jump > max_jump:
                        max_jump = jump
                    assert jump <= max_allowed_jump, (
                        f"Discontinuity jump {jump:.3f} px > {max_allowed_jump:.3f} px at step {step}"
                    )

            prev_states = states

        print(f"\n[Pattern {pattern}] 2000 steps: Max single-frame jump = {max_jump:.4f} px (Allowed: {max_allowed_jump:.4f} px)")

    def test_multi_beacon_multi_speed_multi_seed_stress(self) -> None:
        """
        Stress Test 3B: Cross-combination stress testing across multiple seeds and speeds.
        """
        seeds = [7, 42, 999]
        speeds = [15.0, 60.0, 100.0]

        for seed in seeds:
            for speed in speeds:
                for pattern in ["STRAIGHT_LINE", "CIRCULAR", "FIGURE_8"]:
                    mbm = MultiBeaconManager(
                        beacon_configs=[
                            BeaconConfig(role="primary", motion_type=pattern, speed=speed),
                            BeaconConfig(role="secondary", motion_type=pattern, speed=speed * 0.75),
                        ],
                        motion_config=MotionConfig(motion_type=pattern),
                        scene_width=2000,
                        scene_height=2000,
                        seed=seed,
                    )
                    dt = 0.033
                    for _ in range(500):
                        mbm.step(dt)
                        states = mbm.get_all_beacon_states()
                        for x, y, _ in states:
                            assert 0.0 <= x <= 2000.0
                            assert 0.0 <= y <= 2000.0
