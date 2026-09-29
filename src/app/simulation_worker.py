"""
Simulation Worker Thread — Component extracted from AppController (F-ARCH-01).

Responsibilities:
  - Executes the continuous tracking simulation loop in a background daemon thread for GUI/interactive modes.
  - Coordinates frame acquisition, tracking step, PTZ actuation, metrics updates, and telemetry publishing.
  - Enforces loop timing and frame pacing matching camera update rates.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Optional, TYPE_CHECKING

from src.frame.data_contracts import (
    FrameSource,
    ROI,
    VisualizationState,
    PTZCommand,
)
from src.app.visualization_state import VisualizationStateManager

if TYPE_CHECKING:
    from src.app.app_controller import AppController


class SimulationWorkerThread:
    """Manages the background simulation thread and loop execution."""

    def __init__(
        self,
        app: "AppController",
        viz_manager: VisualizationStateManager,
    ) -> None:
        self._app = app
        self._viz_manager = viz_manager
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._paused: bool = False

    @property
    def thread(self) -> Optional[threading.Thread]:
        return self._thread

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        """Starts the internal simulation loop in a background thread."""
        if self._thread and self._thread.is_alive():
            print("[AppController] Simulation is already running.")
            return

        self._running = True
        self._paused = False
        self._viz_manager.clear()

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self, timeout: float = 1.0) -> None:
        """Stops the background simulation thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _run_loop(self) -> None:
        """Internal worker thread executing the tracker pipeline."""
        print("[AppController] Background simulation loop started.")
        app = self._app
        while self._running:
            if self._paused:
                time.sleep(0.01)
                continue

            loop_t0 = time.perf_counter()

            packet = app.get_next_frame()
            if packet is None:
                # EOF
                self._running = False
                app._running = False
                break

            # Execute active algorithm via public API
            (
                public_res,
                t_elapsed_ms,
                track_res,
                state_res,
                centroid_res,
                detection_res,
            ) = app.step_algorithm(packet)

            # Control (PTZ) — only active in SIMULATION mode
            ptz_cmd = None
            if app.ptz_controller and packet.source == FrameSource.SIMULATION:
                if app._ptz_enabled:
                    dt = 1.0 / app.config_manager.config.camera.update_rate_hz
                    pm = app.camera_model.projection_model if app.camera_model else None
                    ptz_cmd = app.ptz_controller.compute(
                        track_res,
                        state_res.state,
                        packet.width,
                        packet.height,
                        dt=dt,
                        projection_model=pm,
                    )
                    if app.camera_model and ptz_cmd.valid:
                        app.camera_model.apply_pan_tilt(ptz_cmd.delta_pan_deg, ptz_cmd.delta_tilt_deg)
                else:
                    app.ptz_controller.reset()
                    ptz_cmd = PTZCommand(
                        delta_pan_deg=0.0,
                        delta_tilt_deg=0.0,
                        pan_velocity_deg_s=0.0,
                        tilt_velocity_deg_s=0.0,
                        valid=False,
                        timestamp=packet.timestamp,
                        frame_number=packet.frame_number,
                    )

            # Telemetry/Metrics update
            gt = None
            if app.ground_truth_provider:
                gt = app.ground_truth_provider.get_truth(packet.frame_number)

            cam_pan = app.camera_model.pan_deg if app.camera_model else 0.0
            cam_tilt = app.camera_model.tilt_deg if app.camera_model else 0.0

            if app.metrics_engine and state_res:
                telemetry = app.metrics_engine.update(
                    frame_packet=packet,
                    track_result=track_res,
                    state_result=state_res,
                    centroid_result=centroid_res,
                    detection_result=detection_res,
                    ptz_command=ptz_cmd,
                    ground_truth=gt,
                    camera_pan_deg=cam_pan,
                    camera_tilt_deg=cam_tilt,
                    processing_time_ms=t_elapsed_ms,
                )
                app.logging_engine.log_frame(telemetry)

            # Build VisualizationState for frontend
            cam_fov = app.config_manager.config.camera.fov_h_deg

            roi_contract = None
            if public_res.roi:
                roi_contract = ROI(
                    x=public_res.roi[0],
                    y=public_res.roi[1],
                    width=public_res.roi[2],
                    height=public_res.roi[3],
                )

            tgt_spd = (
                app._config_manager.config.target.speed
                if (app._config_manager and app._config_manager.config and app._config_manager.config.target)
                else None
            )

            viz_state = VisualizationState(
                frame_number=packet.frame_number,
                timestamp=packet.timestamp,
                pan_angle_deg=cam_pan,
                tilt_angle_deg=cam_tilt,
                camera_fov=cam_fov,
                display_image=packet.image,
                camera_fov_v=app.config_manager.config.camera.fov_v_deg,
                camera_width=packet.width,
                camera_height=packet.height,
                estimated_centroid_x=centroid_res.x if centroid_res and centroid_res.valid else None,
                estimated_centroid_y=centroid_res.y if centroid_res and centroid_res.valid else None,
                tracking_state=state_res.state.name,
                tracking_error_px=None,
                roi=roi_contract,
                processing_latency_ms=t_elapsed_ms,
                fps=1000.0 / t_elapsed_ms if t_elapsed_ms > 0 else 0.0,
                ground_truth_x=gt.ideal_projected_x if gt else None,
                ground_truth_y=gt.ideal_projected_y if gt else None,
                target_speed_px_s=tgt_spd,
                ptz_enabled=app._ptz_enabled,
            )

            # Push to visualization queue with backpressure handling
            self._viz_manager.push_state(viz_state)

            # Pace simulation loop to match camera update rate in real time
            target_fps = (
                float(app.config_manager.config.camera.update_rate_hz)
                if (app.config_manager and app.config_manager.config and app.config_manager.config.camera)
                else 30.0
            )
            target_period = 1.0 / max(1.0, min(120.0, target_fps))
            loop_duration = time.perf_counter() - loop_t0
            sleep_time = max(0.001, target_period - loop_duration)
            time.sleep(sleep_time)
