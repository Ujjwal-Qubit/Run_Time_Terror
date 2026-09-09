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


class ProportionalDeadbandPTZController(IPTZController):
    """
    P0 Baseline PTZ Controller.

    Control Pipeline:
      1. Image-plane error relative to optical axis center:
         Delta_x = x_target - x_center,  Delta_y = y_target - y_center
      2. Component-wise deadband filtering:
         Delta_x' = 0 if |Delta_x| <= deadband else Delta_x
         Delta_y' = 0 if |Delta_y| <= deadband else Delta_y
      3. Angular error conversion via ProjectionModel:
         theta_pan, theta_tilt = projection_model.image_to_angles(x_center + Delta_x', y_center + Delta_y')
      4. Proportional control law:
         omega_pan_req = K_p * theta_pan
         omega_tilt_req = K_p * theta_tilt
      5. Hard rate limiting (PS Rows 13-14):
         omega_pan_lim = clamp(omega_pan_req, -max_pan_speed, max_pan_speed)
         omega_tilt_lim = clamp(omega_tilt_req, -max_tilt_speed, max_tilt_speed)
      6. Timestep integration to angular displacement:
         Delta_pan = omega_pan_lim * dt
         Delta_tilt = omega_tilt_lim * dt
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
        self._ptz_cfg = ptz_config or PTZConfig()
        self._camera_cfg = camera_config or CameraConfig()
        self._projection_model = projection_model

        # Telemetry and diagnostics counters
        self._total_commands: int = 0
        self._saturated_commands: int = 0
        self._deadband_commands: int = 0
        self._last_command: Optional[PTZCommand] = None

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

    def get_name(self) -> str:
        return "ProportionalDeadbandPTZController"

    def reset(self) -> None:
        """Reset internal diagnostics and state counters."""
        self._total_commands = 0
        self._saturated_commands = 0
        self._deadband_commands = 0
        self._last_command = None

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
        # 1. State-Dependent Gating (Zero Gain Scheduling)
        # -------------------------------------------------------------------
        # SEARCHING, ACQUIRING, and LOST command zero actuation.
        if tracking_state in (
            TrackingState.SEARCHING,
            TrackingState.ACQUIRING,
            TrackingState.LOST,
        ):
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

        # Commands are independently deadbanded on each axis
        err_x_db = 0.0 if abs(err_x) <= deadband else err_x
        err_y_db = 0.0 if abs(err_y) <= deadband else err_y

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
        # 6. Proportional Control Law
        # -------------------------------------------------------------------
        kp = float(self._ptz_cfg.proportional_gain)
        omega_pan_req = kp * theta_pan
        omega_tilt_req = kp * theta_tilt

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
