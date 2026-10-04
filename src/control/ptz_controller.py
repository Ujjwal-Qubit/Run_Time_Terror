"""
PTZ Controller — Module 14 per Architecture v1.2 §4, §11, §18.2.

Responsibility:
  Convert tracked beacon image-plane errors into rate-limited pan/tilt angular
  velocity (deg/s) and displacement (deg) commands to center the beacon on the
  virtual camera's optical axis.

Key Architectural Guarantees:
  1. P0 Control Law: Dead-band proportional control + hard rate limiting.
  2. Single Ownership: Controller only generates PTZCommand; virtual camera pose
     actuation is owned exclusively by the simulation/application loop.
  3. Ground-Truth Firewall: Zero dependency on GroundTruth, GroundTruthProvider,
     or simulator internals.
  4. Benchmark-2 Compatibility: In MP4 mode, PTZ actuation is bypassed entirely.
  5. Geometric Soundness: Consumes ProjectionModel / CameraConfig for pixel-to-angle
     transformations without duplicating projection equations.
"""

from __future__ import annotations

import math
import time
from typing import Any, Optional, Tuple

from src.config.config_manager import CameraConfig, PTZConfig
from src.frame.data_contracts import PTZCommand, TrackResult, TrackingState
from src.interfaces.strategy_interfaces import IPTZController


class ExpandingSearchPattern:
    """
    Kinematically constrained Expanding Square Search (ESS) generator.
    Standard aeronautical / maritime search pattern adapted for 2-DOF optical gimbal.
    
    Generates rate-limited pan/tilt angular velocity commands (<= max_speed)
    expanding outwards from the current camera orientation in concentric squares
    with 25% track overlap (step_size = 0.75 * FOV_minor) to guarantee zero blind spots.
    """

    def __init__(
        self,
        step_deg: float = 2.25,
        max_pan_speed: float = 10.0,
        max_tilt_speed: float = 10.0,
        max_expansion_deg: float = 12.5,
    ) -> None:
        self.step_deg = max(0.1, float(step_deg))
        self.max_pan_speed = max(0.1, float(max_pan_speed))
        self.max_tilt_speed = max(0.1, float(max_tilt_speed))
        self.max_expansion_deg = max(1.0, float(max_expansion_deg))
        self.reset()

    def reset(self) -> None:
        """Reset search state to origin."""
        self._leg_index: int = 0
        self._leg_progress_deg: float = 0.0
        self._total_search_time: float = 0.0

    @property
    def leg_index(self) -> int:
        return self._leg_index

    @property
    def total_search_time(self) -> float:
        return self._total_search_time

    def compute_step(self, dt: float) -> Tuple[float, float, float, float]:
        """
        Compute rate-limited pan/tilt velocities and displacements for the current timestep.

        Returns:
            Tuple of (delta_pan_deg, delta_tilt_deg, pan_velocity_deg_s, tilt_velocity_deg_s)
        """
        eff_dt = max(0.0, float(dt))
        if eff_dt == 0.0:
            return (0.0, 0.0, 0.0, 0.0)

        # Leg length in expanding square: L_i = (i // 2 + 1) * step_deg
        multiplier = (self._leg_index // 2) + 1
        leg_length = multiplier * self.step_deg

        # If expansion exceeds maximum boundary, cycle back to initial step
        if leg_length > self.max_expansion_deg:
            self._leg_index = 0
            self._leg_progress_deg = 0.0
            leg_length = self.step_deg

        # Direction pattern: 0: +Pan, 1: +Tilt, 2: -Pan, 3: -Tilt
        direction_mode = self._leg_index % 4

        if direction_mode == 0:
            pan_vel = self.max_pan_speed
            tilt_vel = 0.0
            dist_remaining = leg_length - self._leg_progress_deg
            step_dist = pan_vel * eff_dt
            if step_dist >= dist_remaining:
                actual_dist = dist_remaining
                self._leg_index += 1
                self._leg_progress_deg = 0.0
            else:
                actual_dist = step_dist
                self._leg_progress_deg += step_dist
            d_pan = actual_dist
            d_tilt = 0.0

        elif direction_mode == 1:
            pan_vel = 0.0
            tilt_vel = self.max_tilt_speed
            dist_remaining = leg_length - self._leg_progress_deg
            step_dist = tilt_vel * eff_dt
            if step_dist >= dist_remaining:
                actual_dist = dist_remaining
                self._leg_index += 1
                self._leg_progress_deg = 0.0
            else:
                actual_dist = step_dist
                self._leg_progress_deg += step_dist
            d_pan = 0.0
            d_tilt = actual_dist

        elif direction_mode == 2:
            pan_vel = -self.max_pan_speed
            tilt_vel = 0.0
            dist_remaining = leg_length - self._leg_progress_deg
            step_dist = abs(pan_vel) * eff_dt
            if step_dist >= dist_remaining:
                actual_dist = dist_remaining
                self._leg_index += 1
                self._leg_progress_deg = 0.0
            else:
                actual_dist = step_dist
                self._leg_progress_deg += step_dist
            d_pan = -actual_dist
            d_tilt = 0.0

        else: # direction_mode == 3
            pan_vel = 0.0
            tilt_vel = -self.max_tilt_speed
            dist_remaining = leg_length - self._leg_progress_deg
            step_dist = abs(tilt_vel) * eff_dt
            if step_dist >= dist_remaining:
                actual_dist = dist_remaining
                self._leg_index += 1
                self._leg_progress_deg = 0.0
            else:
                actual_dist = step_dist
                self._leg_progress_deg += step_dist
            d_pan = 0.0
            d_tilt = -actual_dist

        self._total_search_time += eff_dt
        return (d_pan, d_tilt, pan_vel, tilt_vel)


class ProportionalDeadbandPTZController(IPTZController):
    """
    P0 Baseline & Active Search PTZ Controller.

    Control Pipeline:
      1. Image-plane error relative to optical axis center:
         Delta_x = x_target - x_center,  Delta_y = y_target - y_center
      2. Component-wise deadband filtering:
         Delta_x' = 0 if |Delta_x| <= deadband else Delta_x
         Delta_y' = 0 if |Delta_y| <= deadband else Delta_y
      3. Angular error conversion via ProjectionModel:
         theta_pan, theta_tilt = projection_model.image_to_angles(x_center + Delta_x', y_center + Delta_y')
      4. Proportional-Integral control law with back-calculation anti-windup:
         omega_pan_req = K_p * theta_pan + K_i * I_pan
         omega_tilt_req = K_p * theta_tilt + K_i * I_tilt
      5. Hard rate limiting (PS Rows 13-14):
         omega_pan_lim = clamp(omega_pan_req, -max_pan_speed, max_pan_speed)
         omega_tilt_lim = clamp(omega_tilt_req, -max_tilt_speed, max_tilt_speed)
      6. Timestep integration to angular displacement:
         Delta_pan = omega_pan_lim * dt
         Delta_tilt = omega_tilt_lim * dt
      7. Autonomous active expanding search during SEARCHING state when enabled.
    """

    def __init__(
        self,
        ptz_config: Optional[PTZConfig] = None,
        camera_config: Optional[CameraConfig] = None,
        projection_model: Optional[Any] = None,
    ) -> None:
        """
        Initialize the PTZ controller.

        Args:
            ptz_config: Controller tuning parameters (speeds, gain, deadband).
            camera_config: Camera geometry parameters (resolution, FOV).
            projection_model: Optional authoritative ProjectionModel instance.
        """
        if hasattr(ptz_config, "ptz"):
            self._ptz_cfg = ptz_config.ptz
        else:
            self._ptz_cfg = ptz_config or PTZConfig()

        if hasattr(camera_config, "camera"):
            self._camera_cfg = camera_config.camera
        elif hasattr(ptz_config, "camera") and camera_config is None:
            self._camera_cfg = ptz_config.camera
        else:
            self._camera_cfg = camera_config or CameraConfig()

        self._projection_model = projection_model

        # Telemetry and diagnostics counters
        self._total_commands: int = 0
        self._saturated_commands: int = 0
        self._deadband_commands: int = 0
        self._last_command: Optional[PTZCommand] = None

        # Integral control accumulators for steady-state lag elimination
        self._integral_pan: float = 0.0
        self._integral_tilt: float = 0.0

        # Step increment for search: 0.75 * min(fov_h, fov_v)
        fov_minor = min(self._camera_cfg.fov_h_deg, self._camera_cfg.fov_v_deg)
        step_deg = 0.75 * fov_minor
        self._search_pattern = ExpandingSearchPattern(
            step_deg=step_deg,
            max_pan_speed=float(self._ptz_cfg.max_pan_speed_deg_s),
            max_tilt_speed=float(self._ptz_cfg.max_tilt_speed_deg_s),
        )

    @property
    def config(self) -> PTZConfig:
        return self._ptz_cfg

    @property
    def total_commands(self) -> int:
        return self._total_commands

    @property
    def saturated_commands(self) -> int:
        return self._saturated_commands

    @property
    def deadband_commands(self) -> int:
        return self._deadband_commands

    @property
    def last_command(self) -> Optional[PTZCommand]:
        return self._last_command

    @property
    def search_pattern(self) -> ExpandingSearchPattern:
        return self._search_pattern

    def get_name(self) -> str:
        return "ProportionalDeadbandPTZController"

    def reset(self) -> None:
        """Reset internal diagnostics, state counters, and integral accumulators."""
        self._total_commands = 0
        self._saturated_commands = 0
        self._deadband_commands = 0
        self._last_command = None
        self._integral_pan = 0.0
        self._integral_tilt = 0.0
        self._search_pattern.reset()

    def _convert_pixels_to_angles(
        self,
        img_x: float,
        img_y: float,
        frame_width: int,
        frame_height: int,
        projection_model: Optional[Any] = None,
    ) -> Tuple[float, float]:
        """
        Convert pixel coordinates to angular offset relative to the optical axis center.

        Uses the passed projection_model or internally configured projection model.
        If no projection model instance is provided, computes linear angular offset
        using camera configuration parameters.
        """
        pm = projection_model or self._projection_model
        if pm is not None and hasattr(pm, "image_to_angles"):
            return pm.image_to_angles(img_x, img_y)

        # Fallback using camera configuration without importing simulator internals
        deg_per_px_h = self._camera_cfg.fov_h_deg / float(frame_width)
        deg_per_px_v = self._camera_cfg.fov_v_deg / float(frame_height)
        d_pan = (img_x - frame_width / 2.0) * deg_per_px_h
        d_tilt = (img_y - frame_height / 2.0) * deg_per_px_v
        return (d_pan, d_tilt)

    def compute(
        self,
        track_result: Optional[TrackResult],
        tracking_state: TrackingState,
        frame_width: int,
        frame_height: int,
        dt: float,
        projection_model: Optional[Any] = None,
    ) -> PTZCommand:
        """
        Compute rate-limited pan/tilt velocity and displacement commands.

        Args:
            track_result: Current TrackResult from temporal tracker (None if no track).
            tracking_state: Current tracking lifecycle state.
            frame_width: Image width for optical axis calculation.
            frame_height: Image height for optical axis calculation.
            dt: Control update interval in seconds.
            projection_model: Optional authoritative ProjectionModel instance.

        Returns:
            PTZCommand containing angular velocities, displacements, and telemetry.
        """
        t0 = time.perf_counter()
        frame_num = track_result.frame_number if track_result else 0
        timestamp = track_result.timestamp if track_result else 0.0

        if not isinstance(tracking_state, TrackingState):
            raise TypeError(f"tracking_state must be a TrackingState enum, got {type(tracking_state).__name__}")

        # Defensive checks on frame dimensions
        if frame_width <= 0 or frame_height <= 0:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return PTZCommand(
                valid=False,
                frame_number=frame_num,
                timestamp=timestamp,
                processing_time_ms=elapsed_ms,
            )

        # -------------------------------------------------------------------
        # 1. State-Dependent Gating & Active Autonomous Search
        # -------------------------------------------------------------------
        eff_dt = max(0.0, float(dt))

        if tracking_state == TrackingState.SEARCHING:
            self._integral_pan = 0.0
            self._integral_tilt = 0.0
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            search_enabled = getattr(self._ptz_cfg, "search_scan_enabled", False)
            if search_enabled:
                d_pan, d_tilt, pan_vel, tilt_vel = self._search_pattern.compute_step(eff_dt)
                self._total_commands += 1
                cmd = PTZCommand(
                    delta_pan_deg=d_pan,
                    delta_tilt_deg=d_tilt,
                    pan_velocity_deg_s=pan_vel,
                    tilt_velocity_deg_s=tilt_vel,
                    valid=True,
                    timestamp=timestamp,
                    frame_number=frame_num,
                    processing_time_ms=elapsed_ms,
                )
                self._last_command = cmd
                return cmd
            else:
                cmd = PTZCommand(
                    delta_pan_deg=0.0,
                    delta_tilt_deg=0.0,
                    pan_velocity_deg_s=0.0,
                    tilt_velocity_deg_s=0.0,
                    valid=False,
                    timestamp=timestamp,
                    frame_number=frame_num,
                    processing_time_ms=elapsed_ms,
                )
                self._total_commands += 1
                self._last_command = cmd
                return cmd

        # Not searching: reset search pattern generator
        self._search_pattern.reset()

        if tracking_state in (TrackingState.ACQUIRING, TrackingState.LOST):
            self._integral_pan = 0.0
            self._integral_tilt = 0.0
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            cmd = PTZCommand(
                delta_pan_deg=0.0,
                delta_tilt_deg=0.0,
                pan_velocity_deg_s=0.0,
                tilt_velocity_deg_s=0.0,
                valid=False,
                timestamp=timestamp,
                frame_number=frame_num,
                processing_time_ms=elapsed_ms,
            )
            self._total_commands += 1
            self._last_command = cmd
            return cmd

        # -------------------------------------------------------------------
        # 2. Track Validity & Target Extraction
        # -------------------------------------------------------------------
        if track_result is None:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            cmd = PTZCommand(
                delta_pan_deg=0.0,
                delta_tilt_deg=0.0,
                pan_velocity_deg_s=0.0,
                tilt_velocity_deg_s=0.0,
                valid=False,
                timestamp=timestamp,
                frame_number=frame_num,
                processing_time_ms=elapsed_ms,
            )
            self._total_commands += 1
            self._last_command = cmd
            return cmd

        # For REACQUIRING: only actuate if tracker has an active valid estimate
        if tracking_state == TrackingState.REACQUIRING:
            if not track_result.is_coasting and not track_result.measurement_valid:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                cmd = PTZCommand(
                    delta_pan_deg=0.0,
                    delta_tilt_deg=0.0,
                    pan_velocity_deg_s=0.0,
                    tilt_velocity_deg_s=0.0,
                    valid=False,
                    timestamp=timestamp,
                    frame_number=frame_num,
                    processing_time_ms=elapsed_ms,
                )
                self._total_commands += 1
                self._last_command = cmd
                return cmd

        x_target = track_result.estimated_x
        y_target = track_result.estimated_y

        # Safety against NaN / Inf
        if not (math.isfinite(x_target) and math.isfinite(y_target)):
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            cmd = PTZCommand(
                delta_pan_deg=0.0,
                delta_tilt_deg=0.0,
                pan_velocity_deg_s=0.0,
                tilt_velocity_deg_s=0.0,
                valid=False,
                timestamp=timestamp,
                frame_number=frame_num,
                processing_time_ms=elapsed_ms,
            )
            self._total_commands += 1
            self._last_command = cmd
            return cmd

        # -------------------------------------------------------------------
        # 3. Optical Axis Center & Image-Plane Error
        # -------------------------------------------------------------------
        x_center = frame_width / 2.0
        y_center = frame_height / 2.0

        # Displacement of target from optical center:
        # err_x > 0: target is to the right of center -> camera must pan right (+pan)
        # err_x < 0: target is to the left of center  -> camera must pan left (-pan)
        # err_y > 0: target is below center           -> camera must tilt down (+tilt)
        # err_y < 0: target is above center           -> camera must tilt up (-tilt)
        err_x = float(x_target - x_center)
        err_y = float(y_target - y_center)

        # -------------------------------------------------------------------
        # 4. Component-Wise Deadband Filtering
        # -------------------------------------------------------------------
        deadband = float(self._ptz_cfg.deadband_px)

        # in_deadband is True ONLY when BOTH axes are within deadband
        in_deadband = bool(abs(err_x) <= deadband and abs(err_y) <= deadband)

        # Continuous linear deadband transition: e_db = sign(e) * (|e| - deadband)
        # Eliminates step torque impulses when crossing the deadband boundary (DEF-19)
        err_x_db = 0.0 if abs(err_x) <= deadband else math.copysign(abs(err_x) - deadband, err_x)
        err_y_db = 0.0 if abs(err_y) <= deadband else math.copysign(abs(err_y) - deadband, err_y)

        # -------------------------------------------------------------------
        # 5. Angular Error Conversion via ProjectionModel
        # -------------------------------------------------------------------
        # Pass deadbanded coordinates relative to center
        theta_pan, theta_tilt = self._convert_pixels_to_angles(
            x_center + err_x_db,
            y_center + err_y_db,
            frame_width,
            frame_height,
            projection_model,
        )

        # Also calculate raw un-deadbanded angular error for telemetry
        raw_theta_pan, raw_theta_tilt = self._convert_pixels_to_angles(
            x_target,
            y_target,
            frame_width,
            frame_height,
            projection_model,
        )

        # -------------------------------------------------------------------
        # 6. Proportional-Integral (PI) Control Law with Back-Calculation Anti-Windup
        # -------------------------------------------------------------------
        eff_dt = max(0.0, float(dt))
        kp = float(self._ptz_cfg.proportional_gain)
        ki = float(getattr(self._ptz_cfg, "integral_gain", 0.0))
        max_pan = float(self._ptz_cfg.max_pan_speed_deg_s)
        max_tilt = float(self._ptz_cfg.max_tilt_speed_deg_s)
        max_int = 1.0  # Anti-windup ceiling (degrees)

        if ki > 0.0:
            if not in_deadband:
                self._integral_pan += theta_pan * eff_dt
                self._integral_tilt += theta_tilt * eff_dt

                # Back-calculation anti-windup: if tentative request exceeds limits,
                # shed excess integration to prevent runaway accumulation
                omega_pan_tentative = kp * theta_pan + ki * self._integral_pan
                omega_tilt_tentative = kp * theta_tilt + ki * self._integral_tilt

                if abs(omega_pan_tentative) > max_pan and kp > 0.0:
                    omega_pan_sat = max(-max_pan, min(max_pan, omega_pan_tentative))
                    excess_pan = omega_pan_tentative - omega_pan_sat
                    self._integral_pan -= (excess_pan / kp) * eff_dt

                if abs(omega_tilt_tentative) > max_tilt and kp > 0.0:
                    omega_tilt_sat = max(-max_tilt, min(max_tilt, omega_tilt_tentative))
                    excess_tilt = omega_tilt_tentative - omega_tilt_sat
                    self._integral_tilt -= (excess_tilt / kp) * eff_dt

                self._integral_pan = max(-max_int, min(max_int, self._integral_pan))
                self._integral_tilt = max(-max_int, min(max_int, self._integral_tilt))
            else:
                # Exponential decay in deadband to prevent steady-state limit cycling
                self._integral_pan *= 0.95
                self._integral_tilt *= 0.95

        omega_pan_req = kp * theta_pan + ki * self._integral_pan
        omega_tilt_req = kp * theta_tilt + ki * self._integral_tilt

        # -------------------------------------------------------------------
        # 7. Hard Rate Limiting (PS Rows 13–14)
        # -------------------------------------------------------------------
        max_pan = float(self._ptz_cfg.max_pan_speed_deg_s)
        max_tilt = float(self._ptz_cfg.max_tilt_speed_deg_s)

        omega_pan_lim = max(-max_pan, min(max_pan, omega_pan_req))
        omega_tilt_lim = max(-max_tilt, min(max_tilt, omega_tilt_req))

        is_saturated = bool(
            abs(omega_pan_req) > max_pan or abs(omega_tilt_req) > max_tilt
        )

        # -------------------------------------------------------------------
        # 8. Timestep Integration to Angular Displacement
        # -------------------------------------------------------------------
        eff_dt = max(0.0, float(dt))
        delta_pan = omega_pan_lim * eff_dt
        delta_tilt = omega_tilt_lim * eff_dt

        # Diagnostics counters
        self._total_commands += 1
        if in_deadband:
            self._deadband_commands += 1
        if is_saturated:
            self._saturated_commands += 1

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        cmd = PTZCommand(
            delta_pan_deg=delta_pan,
            delta_tilt_deg=delta_tilt,
            pan_velocity_deg_s=omega_pan_lim,
            tilt_velocity_deg_s=omega_tilt_lim,
            error_x_px=err_x,
            error_y_px=err_y,
            error_pan_deg=raw_theta_pan,
            error_tilt_deg=raw_theta_tilt,
            in_deadband=in_deadband,
            is_saturated=is_saturated,
            valid=True,
            timestamp=timestamp,
            frame_number=frame_num,
            processing_time_ms=elapsed_ms,
        )
        self._last_command = cmd
        return cmd


# Production aliases per Architecture v1.2
PTZController = ProportionalDeadbandPTZController
PIDeadbandPTZController = ProportionalDeadbandPTZController
