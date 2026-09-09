"""
Benchmark Manager — Module 17 per Architecture v1.2 §17.

Orchestrates Benchmark-1 (Scenario Closed-Loop Simulation) and Benchmark-2
(MP4 Evaluator Verification) execution, both as single-run benchmarks and as
batch automated evaluation workflows with Grand Evaluation scorecards.
"""

from __future__ import annotations

import glob
import os
import sys
import time
import traceback
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from src.app.app_controller import AppController

from src.frame.data_contracts import (
    BatchRunItem,
    FramePacket,
    FrameSource,
    GrandEvaluationSummary,
    MetricsSummary,
    ROI,
    TelemetryRecord,
    TrackerOutput,
    TrackingState,
)
from src.metrics.logging_engine import LoggingEngine


class BenchmarkManager:
    """
    Benchmark Manager — Module 17.

    Responsibilities:
      - Coordinate single-run Benchmark-1 (Simulation) and Benchmark-2 (MP4) execution
      - Orchestrate batch evaluations across multiple scenario JSONs or MP4 files
      - Calculate macro-level aggregated performance metrics across benchmark suites
      - Generate Grand Evaluator reports and scorecards (JSON + Markdown)
    """

    def __init__(self, app: Optional[AppController] = None) -> None:
        self.app = app
        self._is_running = False

    def run_benchmark(self, max_frames: Optional[int] = None) -> MetricsSummary:
        """
        Executes the main pipeline loop until FrameProvider is exhausted
        or max_frames is reached. Returns the completed MetricsSummary.
        """
        if self.app is None:
            raise RuntimeError("BenchmarkManager requires an AppController instance to run.")

        self._is_running = True
        frame_count = 0

        # Reset components
        if self.app.tracking_engine:
            self.app.tracking_engine.reset()
        if self.app.tracking_state_manager:
            self.app.tracking_state_manager.reset()
        if self.app.ptz_controller:
            self.app.ptz_controller.reset()
        if self.app._metrics_engine:
            self.app._metrics_engine.reset()

        dt = 1.0 / self.app.config_manager.config.camera.update_rate_hz

        while self._is_running:
            # 1. Get Next Frame from Firewall Provider
            packet = self.app.get_next_frame()
            if packet is None:
                break

            t_start = time.perf_counter()

            # 2. Tracking Domain
            # (a) Adaptive ROI
            roi = (
                self.app.tracking_engine.get_roi(packet.width, packet.height)
                if self.app.tracking_engine
                else ROI()
            )

            # (b) Detection
            detection_res = None
            if self.app.detection_engine:
                detection_res = self.app.detection_engine.detect(packet, roi=roi)

            # (c) Candidate Identification
            ident_res = None
            if self.app.candidate_identifier and detection_res:
                pred_pos = (
                    self.app.tracking_engine.predict()
                    if (self.app.tracking_engine and getattr(self.app.tracking_engine, "is_initialized", False))
                    else None
                )
                curr_state = (
                    getattr(self.app.tracking_state_manager, "current_state", TrackingState.SEARCHING)
                    if self.app.tracking_state_manager
                    else TrackingState.SEARCHING
                )
                ident_res = self.app.candidate_identifier.identify(
                    detection_res.candidates,
                    predicted_position=pred_pos,
                    current_state=curr_state,
                    frame_number=packet.frame_number,
                    timestamp=packet.timestamp,
                )

            # (d) Sub-pixel Centroid Estimation
            centroid_res = None
            if (
                self.app.centroid_estimator
                and ident_res
                and ident_res.valid
                and ident_res.selected_candidate is not None
            ):
                centroid_res = self.app.centroid_estimator.estimate(packet, ident_res.selected_candidate)

            # (e) Temporal Tracking (Kalman Filter)
            track_res = None
            if self.app.tracking_engine:
                track_res = self.app.tracking_engine.update(
                    centroid_res,
                    dt=dt,
                    frame_number=packet.frame_number,
                    timestamp=packet.timestamp,
                )

            # (f) Tracking State Management
            state_res = None
            if self.app.tracking_state_manager:
                state_res = self.app.tracking_state_manager.update(
                    track_res,
                    timestamp=packet.timestamp,
                )

            # 3. Control Domain (PTZ) - only active in SIMULATION mode
            ptz_cmd = None
            if self.app.ptz_controller and state_res:
                pm = self.app.camera_model.projection_model if self.app.camera_model else None
                ptz_cmd = self.app.ptz_controller.compute(
                    track_res,
                    state_res.state,
                    packet.width,
                    packet.height,
                    dt=dt,
                    projection_model=pm,
                )
                if (
                    self.app.camera_model
                    and ptz_cmd.valid
                    and packet.source == FrameSource.SIMULATION
                ):
                    self.app.camera_model.apply_pan_tilt(ptz_cmd.delta_pan_deg, ptz_cmd.delta_tilt_deg)

            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

            # 4. Ground Truth (Side-channel ingestion for metrics only)
            ground_truth = None
            if self.app.ground_truth_provider:
                ground_truth = self.app.ground_truth_provider.get_truth(packet.frame_number)

            # 5. Metrics & Telemetry Recording
            cam_pan = self.app.camera_model.pan_deg if self.app.camera_model else 0.0
            cam_tilt = self.app.camera_model.tilt_deg if self.app.camera_model else 0.0

            if self.app._metrics_engine and state_res:
                telemetry = self.app._metrics_engine.update(
                    frame_packet=packet,
                    track_result=track_res,
                    state_result=state_res,
                    centroid_result=centroid_res,
                    detection_result=detection_res,
                    ptz_command=ptz_cmd,
                    ground_truth=ground_truth,
                    camera_pan_deg=cam_pan,
                    camera_tilt_deg=cam_tilt,
                    processing_time_ms=t_elapsed_ms,
                )
                self.app.logging_engine.log_frame(telemetry)

            frame_count += 1
            if max_frames and frame_count >= max_frames:
                break

        # Finalize benchmark and return summary
        return self.stop_benchmark()

    def stop_benchmark(self) -> MetricsSummary:
        """Stops the benchmark loop and finalizes logs."""
        self._is_running = False
        summary = MetricsSummary()

        if self.app and self.app._metrics_engine:
            summary = self.app._metrics_engine.finalize()
            self.app.logging_engine.write_summary(summary)
            self.app.logging_engine.write_performance_report(summary)

        if self.app:
            self.app.logging_engine.finalize()

        return summary

    def evaluate_batch_scenarios(
        self,
        scenario_dir: str,
        base_config_path: Optional[str] = None,
        max_frames_per_scenario: Optional[int] = None,
        output_dir: Optional[str] = None,
    ) -> GrandEvaluationSummary:
        """
        Executes an automated evaluation batch over all scenario JSON files in scenario_dir.
        Aggregates results and produces a Grand Evaluation scorecard.
        """
        from src.app.app_controller import AppController

        batch_id = f"batch_scenarios_{int(time.time())}"
        target_out_dir = output_dir or "output"

        # Discover scenario files
        scenario_files = sorted(glob.glob(os.path.join(scenario_dir, "*.json")))
        if not scenario_files:
            raise FileNotFoundError(f"No scenario JSON files found in '{scenario_dir}'.")

        print("=" * 80)
        print(f"       STARTING BATCH SCENARIO EVALUATION: {len(scenario_files)} SCENARIO(S)")
        print(f"       Directory: {scenario_dir}")
        print("=" * 80)

        run_items: List[BatchRunItem] = []

        for idx, s_path in enumerate(scenario_files, start=1):
            s_name = os.path.splitext(os.path.basename(s_path))[0]
            print(f"\n[{idx}/{len(scenario_files)}] Executing Scenario: '{s_name}'...")

            run_app = AppController()
            try:
                if base_config_path and os.path.isfile(base_config_path):
                    run_app.config_manager.load_from_file(base_config_path)

                run_app.config_manager.load_from_file(s_path)
                run_app.config_manager.update_section("logging", output_dir=target_out_dir)

                run_app.initialize()
                run_bm = BenchmarkManager(run_app)
                summary = run_bm.run_benchmark(max_frames=max_frames_per_scenario)

                run_items.append(
                    BatchRunItem(
                        item_id=s_name,
                        source_path=s_path,
                        success=True,
                        summary=summary,
                    )
                )
                print(
                    f"  [OK] Scenario '{s_name}' completed successfully: "
                    f"{summary.total_frames} frames, {summary.mean_fps:.1f} FPS, "
                    f"RMSE: {summary.rmse_centroid_rendered:.3f} px"
                )
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                print(f"  [FAIL] Scenario '{s_name}' FAILED: {err_msg}")
                traceback.print_exc()
                run_items.append(
                    BatchRunItem(
                        item_id=s_name,
                        source_path=s_path,
                        success=False,
                        error_message=err_msg,
                    )
                )
            finally:
                try:
                    run_app.stop()
                except Exception:
                    pass

        # Aggregate Grand Evaluation Summary
        grand_summary = self._aggregate_grand_summary(
            batch_id=batch_id,
            batch_type="SCENARIOS",
            run_items=run_items,
        )

        # Write output reports
        json_path, md_path = LoggingEngine.write_grand_summary(grand_summary, output_dir=target_out_dir)

        self._print_grand_summary(grand_summary, json_path, md_path)
        return grand_summary

    def evaluate_batch_mp4s(
        self,
        mp4_dir: str,
        base_config_path: Optional[str] = None,
        max_frames_per_video: Optional[int] = None,
        output_dir: Optional[str] = None,
    ) -> GrandEvaluationSummary:
        """
        Executes an automated evaluation batch over all MP4/video files in mp4_dir.
        Aggregates results and produces a Grand Evaluation scorecard.
        """
        from src.app.app_controller import AppController

        batch_id = f"batch_mp4_{int(time.time())}"
        target_out_dir = output_dir or "output"

        # Discover video files
        video_exts = ("*.mp4", "*.avi", "*.mov", "*.mkv")
        video_files: List[str] = []
        for ext in video_exts:
            video_files.extend(glob.glob(os.path.join(mp4_dir, ext)))
        video_files = sorted(video_files)

        if not video_files:
            raise FileNotFoundError(f"No video files found in '{mp4_dir}'.")

        print("=" * 80)
        print(f"       STARTING BATCH MP4 EVALUATION: {len(video_files)} VIDEO(S)")
        print(f"       Directory: {mp4_dir}")
        print("=" * 80)

        run_items: List[BatchRunItem] = []

        for idx, v_path in enumerate(video_files, start=1):
            v_name = os.path.splitext(os.path.basename(v_path))[0]
            print(f"\n[{idx}/{len(video_files)}] Executing Video: '{v_name}'...")

            run_app = AppController()
            try:
                if base_config_path and os.path.isfile(base_config_path):
                    run_app.config_manager.load_from_file(base_config_path)

                run_app.config_manager.update_section(
                    "simulation",
                    mode="MP4",
                    mp4_path=os.path.abspath(v_path),
                )
                run_app.config_manager.update_section("logging", output_dir=target_out_dir)

                run_app.initialize()
                run_bm = BenchmarkManager(run_app)
                summary = run_bm.run_benchmark(max_frames=max_frames_per_video)

                run_items.append(
                    BatchRunItem(
                        item_id=v_name,
                        source_path=v_path,
                        success=True,
                        summary=summary,
                    )
                )
                print(
                    f"  [OK] Video '{v_name}' completed successfully: "
                    f"{summary.total_frames} frames, {summary.mean_fps:.1f} FPS"
                )
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                print(f"  [FAIL] Video '{v_name}' FAILED: {err_msg}")
                traceback.print_exc()
                run_items.append(
                    BatchRunItem(
                        item_id=v_name,
                        source_path=v_path,
                        success=False,
                        error_message=err_msg,
                    )
                )
            finally:
                try:
                    run_app.stop()
                except Exception:
                    pass

        # Aggregate Grand Evaluation Summary
        grand_summary = self._aggregate_grand_summary(
            batch_id=batch_id,
            batch_type="MP4",
            run_items=run_items,
        )

        # Write output reports
        json_path, md_path = LoggingEngine.write_grand_summary(grand_summary, output_dir=target_out_dir)

        self._print_grand_summary(grand_summary, json_path, md_path)
        return grand_summary

    def _aggregate_grand_summary(
        self,
        batch_id: str,
        batch_type: str,
        run_items: List[BatchRunItem],
    ) -> GrandEvaluationSummary:
        """Helper to compute macro-averaged metrics across successful runs."""
        successful = [it for it in run_items if it.success and it.summary is not None]
        failed = [it for it in run_items if not it.success]

        total_runs = len(run_items)
        successful_runs = len(successful)
        failed_runs = len(failed)

        if successful_runs > 0:
            mean_fps = sum(it.summary.mean_fps for it in successful) / successful_runs
            mean_lat = sum(it.summary.mean_latency_ms for it in successful) / successful_runs
            p95_lat = sum(it.summary.p95_latency_ms for it in successful) / successful_runs

            acq_times = [
                it.summary.acquisition_time_s
                for it in successful
                if it.summary.acquisition_time_s is not None
            ]
            mean_acq = (sum(acq_times) / len(acq_times)) if acq_times else None

            mean_rmse_ce = sum(it.summary.rmse_centroid for it in successful) / successful_runs
            mean_rmse_ce_rend = (
                sum(it.summary.rmse_centroid_rendered for it in successful) / successful_runs
            )
            mean_te = sum(it.summary.mean_tracking_error for it in successful) / successful_runs
            mean_lock = (
                sum(it.summary.lock_retention_post_acq_pct for it in successful) / successful_runs
            )
            mean_loss = sum(it.summary.target_loss_rate for it in successful) / successful_runs
            total_frames = sum(it.summary.total_frames for it in successful)
            total_dur = sum(it.summary.duration_seconds for it in successful)
        else:
            mean_fps = 0.0
            mean_lat = 0.0
            p95_lat = 0.0
            mean_acq = None
            mean_rmse_ce = 0.0
            mean_rmse_ce_rend = 0.0
            mean_te = 0.0
            mean_lock = 0.0
            mean_loss = 0.0
            total_frames = 0
            total_dur = 0.0

        # Compliance checks against SIH PS 26169 thresholds
        passed_fps = bool(mean_fps >= 20.0 and successful_runs > 0)
        passed_acq = bool((mean_acq is None or mean_acq <= 2.0) and successful_runs > 0)
        passed_te = bool(mean_te <= 10.0 and successful_runs > 0)
        passed_loss = bool(mean_loss < 5.0 and successful_runs > 0)
        overall = bool(
            passed_fps
            and passed_acq
            and passed_te
            and passed_loss
            and failed_runs == 0
            and successful_runs > 0
        )

        return GrandEvaluationSummary(
            batch_id=batch_id,
            batch_type=batch_type,
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            run_items=run_items,
            mean_fps=mean_fps,
            mean_latency_ms=mean_lat,
            p95_latency_ms=p95_lat,
            mean_acquisition_time_s=mean_acq,
            mean_rmse_centroid=mean_rmse_ce,
            mean_rmse_centroid_rendered=mean_rmse_ce_rend,
            mean_tracking_error=mean_te,
            mean_lock_retention_pct=mean_lock,
            mean_target_loss_rate_pct=mean_loss,
            total_frames_processed=total_frames,
            total_duration_s=total_dur,
            passed_fps_spec=passed_fps,
            passed_acquisition_spec=passed_acq,
            passed_tracking_error_spec=passed_te,
            passed_loss_rate_spec=passed_loss,
            overall_compliance=overall,
            timestamp=time.time(),
        )

    def _print_grand_summary(
        self,
        summary: GrandEvaluationSummary,
        json_path: str,
        md_path: str,
    ) -> None:
        """Prints a clean CLI grand evaluation summary table."""
        print("\n" + "=" * 80)
        print("          GRAND EVALUATION BATCH SCORECARD (MODULE 17)")
        print("=" * 80)
        print(f"  Batch ID:                {summary.batch_id}")
        print(f"  Evaluation Type:         {summary.batch_type}")
        print(f"  Total Runs:              {summary.total_runs} (Success: {summary.successful_runs}, Failed: {summary.failed_runs})")
        print(f"  Total Frames Processed:  {summary.total_frames_processed}")
        print(f"  Total Duration:          {summary.total_duration_s:.2f} s")
        print("-" * 80)
        print(f"  Mean Processing Speed:   {summary.mean_fps:.1f} FPS (PS min: 20.0 FPS) -> {'PASS' if summary.passed_fps_spec else 'FAIL'}")
        acq_str = f"{summary.mean_acquisition_time_s:.2f} s" if summary.mean_acquisition_time_s is not None else "N/A"
        print(f"  Mean Acquisition Time:   {acq_str} (PS max: 2.00 s) -> {'PASS' if summary.passed_acquisition_spec else 'FAIL'}")
        print(f"  Mean Tracking Error:     {summary.mean_tracking_error:.2f} px (PS max: 10.0 px) -> {'PASS' if summary.passed_tracking_error_spec else 'FAIL'}")
        print(f"  Mean Target Loss Rate:   {summary.mean_target_loss_rate_pct:.2f}% (PS max: <5.0%) -> {'PASS' if summary.passed_loss_rate_spec else 'FAIL'}")
        print(f"  Mean Centroid RMSE (GT): {summary.mean_rmse_centroid_rendered:.3f} px")
        print(f"  Mean End-to-End Latency: {summary.mean_latency_ms:.2f} ms (P95: {summary.p95_latency_ms:.2f} ms)")
        print("-" * 80)
        status_str = "PASSED ALL CRITERIA" if summary.overall_compliance else "FAILED CRITERIA"
        print(f"  OVERALL PS COMPLIANCE:   {status_str}")
        print(f"  Grand JSON Report:       {json_path}")
        print(f"  Grand Markdown Report:   {md_path}")
        print("=" * 80 + "\n")
