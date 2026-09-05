"""
Benchmark Manager — Module 17 per Architecture v1.2 §17.

Orchestrates Benchmark-1 (Scenario) and Benchmark-2 (MP4) execution.
Executes the main tracking loop and delegates to MetricsEngine and LoggingEngine.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.app.app_controller import AppController

from src.frame.data_contracts import TrackerOutput, ROI, TelemetryRecord, FrameSource


class BenchmarkManager:
    """
    Manages execution of benchmarks.
    """

    def __init__(self, app: AppController) -> None:
        self.app = app
        self._is_running = False

    def run_benchmark(self, max_frames: Optional[int] = None) -> None:
        """
        Executes the main pipeline loop until FrameProvider is exhausted
        or max_frames is reached.
        """
        self._is_running = True
        frame_count = 0

        # Reset components if needed
        if self.app.tracking_engine:
            self.app.tracking_engine.reset()
        if self.app.tracking_state_manager:
            self.app.tracking_state_manager.reset()
        if self.app.ptz_controller:
            self.app.ptz_controller.reset()

        while self._is_running:
            # 1. Get Next Frame
            packet = self.app.get_next_frame()
            if packet is None:
                print("[BenchmarkManager] Source exhausted.")
                break

            # Measure frame processing latency
            t_start = time.perf_counter()

            # 2. Tracking Domain
            # Query tracker for ROI
            roi = self.app.tracking_engine.get_roi(packet.width, packet.height) if self.app.tracking_engine else ROI()

            # Detection
            detection_res = self.app.detection_engine.detect(packet, roi=roi)
            
            # Identification
            ident_res = self.app.candidate_identifier.identify(detection_res.candidates)

            # Centroid Estimation
            centroid_res = None
            if ident_res.valid and ident_res.selected_candidate is not None:
                centroid_res = self.app.centroid_estimator.estimate(packet, ident_res.selected_candidate)

            # Temporal Tracking
            track_res = self.app.tracking_engine.update(centroid_res, frame_number=packet.frame_number, timestamp=packet.timestamp)

            # State Management
            state_res = self.app.tracking_state_manager.update(track_res)

            # 3. Control Domain (PTZ) - only active in SIMULATION
            ptz_cmd = None
            if self.app.ptz_controller and packet.source == FrameSource.SIMULATION:
                dt = 1.0 / self.app.config_manager.config.camera.update_rate_hz
                ptz_cmd = self.app.ptz_controller.compute(track_res, state_res, packet.width, packet.height, dt)
                if self.app.camera_model and ptz_cmd.valid:
                    # Apply PTZ command to camera model
                    self.app.camera_model.apply_pan_tilt(ptz_cmd.delta_pan_deg, ptz_cmd.delta_tilt_deg)

            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

            # Package output
            tracker_output = TrackerOutput(
                frame_number=packet.frame_number,
                timestamp=packet.timestamp,
                state=state_res.state,
                previous_state=state_res.previous_state,
                transition_reason=state_res.transition_reason,
                centroid=centroid_res,
                track=track_res,
                detection_valid=ident_res.valid,
                candidate_count=len(detection_res.candidates),
                confidence=state_res.confidence_level,
                roi=roi,
                processing_time_ms=t_elapsed_ms
            )

            # 4. Metrics Domain
            ground_truth = None
            if self.app.ground_truth_provider:
                # We fetch the ground truth corresponding to the frame we just processed
                ground_truth = self.app.ground_truth_provider.get_truth(packet.frame_number)

            if self.app._metrics_engine:
                self.app._metrics_engine.update(
                    tracker_output,
                    ground_truth,
                    camera_width=packet.width,
                    camera_height=packet.height
                )

            # 5. Logging Domain
            telemetry = TelemetryRecord(
                run_id=self.app.logging_engine.run_id,
                frame_number=packet.frame_number,
                timestamp=packet.timestamp,
                source=packet.source.name,
                state=state_res.state.name,
                previous_state=state_res.previous_state.name,
                transition_reason=state_res.transition_reason,
                target_present=ground_truth.target_visible if ground_truth else False,
                ground_truth_x=ground_truth.target_world_x if ground_truth else None,
                ground_truth_y=ground_truth.target_world_y if ground_truth else None,
                ideal_projected_x=ground_truth.ideal_projected_x if ground_truth else None,
                ideal_projected_y=ground_truth.ideal_projected_y if ground_truth else None,
                rendered_centroid_x=ground_truth.rendered_centroid_x if ground_truth else None,
                rendered_centroid_y=ground_truth.rendered_centroid_y if ground_truth else None,
                estimated_centroid_x=centroid_res.x if centroid_res and centroid_res.valid else None,
                estimated_centroid_y=centroid_res.y if centroid_res and centroid_res.valid else None,
                detection_confidence=ident_res.confidence,
                candidate_count=len(detection_res.candidates),
                detection_valid=ident_res.valid,
                pan_angle=self.app.camera_model.pan_deg if self.app.camera_model else 0.0,
                tilt_angle=self.app.camera_model.tilt_deg if self.app.camera_model else 0.0,
                pan_command=ptz_cmd.pan_velocity_deg_s if ptz_cmd else 0.0,
                tilt_command=ptz_cmd.tilt_velocity_deg_s if ptz_cmd else 0.0,
                processing_time_ms=t_elapsed_ms,
                fps=(1000.0 / t_elapsed_ms) if t_elapsed_ms > 0 else 0.0
            )

            # Optional: metrics engine can provide current centroid errors for telemetry here
            
            self.app.logging_engine.log_frame(telemetry)

            frame_count += 1
            if max_frames and frame_count >= max_frames:
                print(f"[BenchmarkManager] Max frames ({max_frames}) reached.")
                break

        # Finalize benchmark
        self.stop_benchmark()

    def stop_benchmark(self) -> None:
        """Stops the benchmark loop and finalizes logs."""
        self._is_running = False
        
        if self.app._metrics_engine:
            summary = self.app._metrics_engine.get_summary()
            self.app.logging_engine.write_summary(summary)
            print("[BenchmarkManager] Benchmark complete. Summary:")
            print(f"  Frames Processed: {summary.total_frames}")
            print(f"  Average FPS: {summary.mean_fps:.2f}")
            print(f"  RMSE Centroid Error: {summary.rmse_centroid:.4f} px")
            print(f"  Lock Retention Rate: {summary.lock_retention_rate:.2f}%")
            if summary.acquisition_time_s is not None:
                print(f"  Acquisition Time: {summary.acquisition_time_s:.2f} s")
            else:
                print("  Acquisition Time: N/A")

        self.app.logging_engine.finalize()
