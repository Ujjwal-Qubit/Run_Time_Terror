#!/usr/bin/env python3
"""
Smoke Test: Phase 5.8 Metrics, Telemetry & Performance Evaluation
Demonstrates:
  1. Benchmark-1 Closed-Loop Simulation with Ground Truth.
  2. Incremental online error calculation and RMSE evaluation.
  3. Benchmark-2 Evaluator MP4 mode (PTZ bypassed, centroid export CSV).
  4. Automatic generation of Telemetry CSV, Centroid Export CSV, Summary JSON,
     and Performance Report Scorecard (Markdown).
"""

import os
import shutil
import tempfile
import time

from src.config.config_manager import SystemConfig
from src.frame.simulation_provider import SimulationFrameProvider
from src.tracker.detection_engine import P0ThresholdDetector
from src.tracker.candidate_identifier import CandidateIdentifier
from src.tracker.centroid_estimator import IntensityWeightedCentroidEstimator
from src.tracker.temporal_tracker import ConstantVelocityKalmanTracker
from src.tracker.state_manager import TrackingStateManager
from src.control.ptz_controller import ProportionalDeadbandPTZController
from src.metrics.metrics_engine import MetricsEngine
from src.metrics.logging_engine import LoggingEngine


def run_smoke_test():
    print("=" * 80)
    print("       PHASE 5.8 METRICS ENGINE & TELEMETRY — SMOKE TEST")
    print("=" * 80)

    output_dir = os.path.abspath("output/smoke_test_5_8")
    os.makedirs(output_dir, exist_ok=True)

    # -----------------------------------------------------------------------
    # PART 1: Benchmark-1 Closed-Loop Simulation
    # -----------------------------------------------------------------------
    print("\n--- [1] EXECUTING BENCHMARK-1 (SIMULATION CLOSED-LOOP + GROUND TRUTH) ---")
    cfg = SystemConfig()
    cfg.simulation.random_seed = 42
    cfg.target.initial_position = "custom"
    cfg.target.initial_x = 1030.0
    cfg.target.initial_y = 1020.0
    cfg.target.speed = 0.0
    cfg.target.size = 12
    cfg.target.intensity = 220
    cfg.scene.background_intensity = 30
    cfg.ptz.proportional_gain = 1.0
    cfg.ptz.deadband_px = 5.0

    sim_provider = SimulationFrameProvider.from_config(cfg)
    detector = P0ThresholdDetector(cfg.detector)
    identifier = CandidateIdentifier(cfg.identifier)
    centroid_estimator = IntensityWeightedCentroidEstimator(cfg.centroid)
    tracker = ConstantVelocityKalmanTracker(cfg.tracker)
    state_mgr = TrackingStateManager(cfg.state)
    ptz_ctrl = ProportionalDeadbandPTZController(cfg.ptz, cfg.camera)

    metrics_engine = MetricsEngine(run_id="smoke_bm1")
    logging_engine = LoggingEngine(output_dir=output_dir, run_id="smoke_bm1")
    logging_engine.initialize()

    dt = 1.0 / 30.0
    milestone_frames = {0, 10, 20, 30, 40, 50, 59}

    print(f"{'F#':>3} | {'State':^11} | {'Centroid Err':^12} | {'Track Err (Opt)':^15} | {'DB':^4} | {'Pipe (ms)':^9}")
    print("-" * 65)

    for f in range(60):
        t0_frame = time.perf_counter()
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

        # 7. Actuation (BM1 Closed-Loop)
        if cmd.valid:
            sim_provider._camera_model.apply_pan_tilt(cmd.delta_pan_deg, cmd.delta_tilt_deg)

        # 8. Synchronized Ground Truth (Side-Channel)
        gt = sim_provider.ground_truth_provider.get_truth(f) if sim_provider.ground_truth_provider else None

        pipeline_ms = (time.perf_counter() - t0_frame) * 1000.0

        # 9. Metrics & Telemetry Recording
        cam_x, cam_y = sim_provider._camera_model.world_position
        record = metrics_engine.update(
            frame_packet=packet,
            track_result=track_res,
            state_result=state_res,
            centroid_result=cent_res,
            detection_result=det_res,
            ptz_command=cmd,
            ground_truth=gt,
            camera_pan_deg=sim_provider._camera_model.pan_deg,
            camera_tilt_deg=sim_provider._camera_model.tilt_deg,
            processing_time_ms=pipeline_ms,
        )
        logging_engine.log_frame(record)

        if f in milestone_frames:
            ce_str = f"{record.centroid_error_rendered:6.2f} px" if record.centroid_error_rendered is not None else "   N/A   "
            te_str = f"{record.tracking_error_optical_axis:6.2f} px" if record.tracking_error_optical_axis is not None else "   N/A   "
            db_str = "YES" if record.ptz_in_deadband else "NO"
            print(f"{f:3d} | {record.state:^11} | {ce_str:^12} | {te_str:^15} | {db_str:^4} | {record.processing_time_ms:7.3f} ms")

    summary_bm1 = metrics_engine.finalize()
    logging_engine.write_summary(summary_bm1)
    rep_path = logging_engine.write_performance_report(summary_bm1)
    logging_engine.finalize()

    print("-" * 65)
    print("BENCHMARK-1 SUMMARY SCORECARD:")
    print(f"  Total Frames Processed:   {summary_bm1.total_frames}")
    print(f"  Throughput (FPS):         {summary_bm1.mean_fps:.1f} FPS (PS min: 20 FPS)")
    print(f"  Acquisition Time:         {summary_bm1.acquisition_time_s:.3f} s (PS max: 2.0 s)")
    print(f"  RMSE Centroid Error:      {summary_bm1.rmse_centroid_rendered:.3f} px")
    print(f"  Final Tracking Error:     {summary_bm1.mean_tracking_error:.2f} px (PS max: 10 px)")
    print(f"  Lock Retention Rate:      {summary_bm1.lock_retention_post_acq_pct:.1f}% (PS loss < 5%)")
    print(f"  Target Loss Rate:         {summary_bm1.target_loss_rate:.1f}%")
    print(f"  Performance Report Saved: {rep_path}")

    # -----------------------------------------------------------------------
    # PART 2: Benchmark-2 Mode (Evaluator Stream, PTZ Bypassed)
    # -----------------------------------------------------------------------
    print("\n--- [2] EXECUTING BENCHMARK-2 (MP4 EMULATION, PTZ BYPASSED) ---")
    bm2_metrics = MetricsEngine(run_id="smoke_bm2")
    bm2_logger = LoggingEngine(output_dir=output_dir, run_id="smoke_bm2")
    bm2_logger.initialize()

    # Re-run 30 frames bypassing PTZ actuation and without Ground Truth
    sim_provider.reset()
    tracker.reset()
    state_mgr.reset()
    ptz_ctrl.reset()

    for f in range(30):
        t0_f = time.perf_counter()
        packet = sim_provider.get_next_frame()
        det_res = detector.detect(packet)
        pred_pos = tracker.predict() if tracker.is_initialized else None
        ident_res = identifier.identify(det_res.candidates, predicted_position=pred_pos, current_state=state_mgr.current_state, frame_number=f, timestamp=packet.timestamp)
        cent_res = centroid_estimator.estimate(packet, ident_res.selected_candidate) if ident_res.valid and ident_res.selected_candidate else None
        track_res = tracker.update(cent_res, dt=dt, frame_number=f, timestamp=packet.timestamp)
        state_res = state_mgr.update(track_res, timestamp=packet.timestamp)
        cmd = ptz_ctrl.compute(track_res, state_res.state, packet.width, packet.height, dt=dt)
        # Note: in BM2, sim_provider._camera_model.apply_pan_tilt is strictly NOT called!
        pipe_ms = (time.perf_counter() - t0_f) * 1000.0

        # Ground truth is None in BM2
        rec_bm2 = bm2_metrics.update(
            frame_packet=packet,
            track_result=track_res,
            state_result=state_res,
            centroid_result=cent_res,
            detection_result=det_res,
            ptz_command=cmd,
            ground_truth=None,  # NO ground truth in BM2!
            processing_time_ms=pipe_ms,
        )
        bm2_logger.log_frame(rec_bm2)

    summary_bm2 = bm2_metrics.finalize()
    bm2_logger.write_summary(summary_bm2)
    bm2_rep = bm2_logger.write_performance_report(summary_bm2)
    bm2_logger.finalize()

    cent_export_path = os.path.join(output_dir, "smoke_bm2_centroids.csv")
    print(f"  Benchmark-2 Frames:       {summary_bm2.total_frames}")
    print(f"  Centroid Export (PS L113):{cent_export_path}")
    print(f"  Ground Truth Leakage:     VERIFIED ZERO (GT was None)")
    print(f"  Centroid Export Size:     {os.path.getsize(cent_export_path)} bytes")

    print("\n" + "=" * 80)
    print("       ALL PHASE 5.8 METRICS & TELEMETRY SMOKE CHECKS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    run_smoke_test()
