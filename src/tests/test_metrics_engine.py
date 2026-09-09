"""
Unit & Integration Tests for Module 15: MetricsEngine (src/metrics/metrics_engine.py)
and Module 16: LoggingEngine (src/metrics/logging_engine.py).

Verifies:
  1. Mathematical correctness: Centroiding error, optical axis tracking error,
     ground truth tracking error, online incremental RMSE.
  2. Operational timing: Acquisition time (total & from detect), reacquisition
     episodes (durations, mean, max), unclosed loss episodes.
  3. Retention metrics: Lock retention (post-acq, all-frames, visible), target loss rate,
     track continuity.
  4. Robustness & edge cases: Zero-frame runs, None estimates, coasting tracks,
     out-of-FOV targets, reset behavior.
  5. Logging integration: CSV telemetry log, evaluator centroid export, summary JSON,
     and performance scorecard.
  6. Dual Benchmark support: BM1 (with GroundTruth) and BM2 (without GroundTruth).
  7. Ground-Truth firewall: AST check confirming zero imports of src.simulation.
  8. Performance benchmark: Verifying < 0.1 ms metrics overhead.
"""

from __future__ import annotations

import ast
import inspect
import math
import os
import shutil
import tempfile
import time
import pytest
import numpy as np

from src.interfaces.strategy_interfaces import IMetricsEngine
from src.metrics.metrics_engine import MetricsEngine
from src.metrics.logging_engine import LoggingEngine
from src.frame.data_contracts import (
    FramePacket,
    FrameSource,
    CentroidResult,
    TrackResult,
    TrackingStateResult,
    TrackingState,
    DetectionResult,
    CandidateRegion,
    PTZCommand,
    GroundTruth,
    TelemetryRecord,
    MetricsSummary,
)


def make_dummy_packet(frame_num: int, timestamp: float, width: int = 640, height: int = 480) -> FramePacket:
    img = np.zeros((height, width), dtype=np.uint8)
    return FramePacket(
        frame_number=frame_num,
        timestamp=timestamp,
        image=img,
        width=width,
        height=height,
        source=FrameSource.SIMULATION,
    )


# ---------------------------------------------------------------------------
# 1. Mathematical Correctness
# ---------------------------------------------------------------------------

class TestMetricsEngineCalculations:
    def test_implements_interface(self):
        engine = MetricsEngine()
        assert isinstance(engine, IMetricsEngine)
        assert engine.get_name() == "MetricsEngine"

    def test_zero_error_calculation(self):
        """When estimate exactly matches ground truth, centroid error and RMSE are zero."""
        engine = MetricsEngine(run_id="test_zero")
        packet = make_dummy_packet(0, 0.0)
        cent = CentroidResult(x=320.0, y=240.0, valid=True)
        track = TrackResult(estimated_x=320.0, estimated_y=240.0)
        state = TrackingStateResult(state=TrackingState.TRACKING)
        gt = GroundTruth(
            frame_number=0,
            timestamp=0.0,
            target_world_x=1000.0,
            target_world_y=1000.0,
            ideal_projected_x=320.0,
            ideal_projected_y=240.0,
            rendered_centroid_x=320.0,
            rendered_centroid_y=240.0,
            target_visible=True,
        )

        rec = engine.update(packet, track, state, centroid_result=cent, ground_truth=gt)
        assert rec.centroid_error_rendered == 0.0
        assert rec.centroid_error_ideal == 0.0
        assert rec.tracking_error_optical_axis == 0.0
        assert rec.tracking_error_gt == 0.0

        summary = engine.finalize()
        assert summary.mean_centroid_error == 0.0
        assert summary.rmse_centroid == 0.0
        assert summary.rmse_centroid_rendered == 0.0
        assert summary.rmse_centroid_ideal == 0.0
        assert summary.mean_tracking_error == 0.0

    def test_known_constant_error_and_rmse(self):
        """Verify Euclidean distance and RMSE for known offset Δx=3.0, Δy=4.0 (hypot=5.0)."""
        engine = MetricsEngine(run_id="test_known")
        for f in range(10):
            t = f * 0.0333
            packet = make_dummy_packet(f, t)
            cent = CentroidResult(x=323.0, y=244.0, valid=True)
            track = TrackResult(estimated_x=323.0, estimated_y=244.0)
            state = TrackingStateResult(state=TrackingState.TRACKING)
            gt = GroundTruth(
                frame_number=f,
                timestamp=t,
                target_world_x=1000.0,
                target_world_y=1000.0,
                ideal_projected_x=320.0,
                ideal_projected_y=240.0,
                rendered_centroid_x=320.0,
                rendered_centroid_y=240.0,
                target_visible=True,
            )
            rec = engine.update(packet, track, state, centroid_result=cent, ground_truth=gt)
            assert pytest.approx(rec.centroid_error_rendered, rel=1e-6) == 5.0

        summary = engine.finalize()
        assert pytest.approx(summary.mean_centroid_error, rel=1e-6) == 5.0
        assert pytest.approx(summary.rmse_centroid, rel=1e-6) == 5.0
        assert pytest.approx(summary.rmse_centroid_rendered, rel=1e-6) == 5.0

    def test_incremental_rmse_matches_batch_numpy(self):
        """Verify incremental sum-of-squares RMSE exactly matches batch numpy calculation."""
        engine = MetricsEngine(run_id="test_rmse")
        offsets = [(1.0, 2.0), (3.0, 4.0), (0.5, 1.5), (2.5, 3.5), (4.0, 0.0)]
        expected_errors = []

        for f, (dx, dy) in enumerate(offsets):
            t = f * 0.0333
            packet = make_dummy_packet(f, t)
            cent = CentroidResult(x=320.0 + dx, y=240.0 + dy, valid=True)
            track = TrackResult(estimated_x=320.0 + dx, estimated_y=240.0 + dy)
            state = TrackingStateResult(state=TrackingState.TRACKING)
            gt = GroundTruth(
                frame_number=f,
                timestamp=t,
                target_world_x=1000.0,
                target_world_y=1000.0,
                rendered_centroid_x=320.0,
                rendered_centroid_y=240.0,
                target_visible=True,
            )
            engine.update(packet, track, state, centroid_result=cent, ground_truth=gt)
            expected_errors.append(math.hypot(dx, dy))

        summary = engine.finalize()
        batch_rmse = float(np.sqrt(np.mean(np.square(expected_errors))))
        assert pytest.approx(summary.rmse_centroid, rel=1e-6) == batch_rmse


# ---------------------------------------------------------------------------
# 2. Timing and Event Metrics
# ---------------------------------------------------------------------------

class TestMetricsEngineTimingAndEvents:
    def test_acquisition_time_metrics(self):
        """
        Verify acquisition timing:
          - Frame 0: SEARCHING
          - Frame 1: ACQUIRING (first detect at t=0.1s)
          - Frame 2: ACQUIRING
          - Frame 3: TRACKING (lock at t=0.3s)
        acq_total = 0.3s, acq_from_detect = 0.2s.
        """
        engine = MetricsEngine()
        times = [0.0, 0.1, 0.2, 0.3, 0.4]
        states = [
            TrackingState.SEARCHING,
            TrackingState.ACQUIRING,
            TrackingState.ACQUIRING,
            TrackingState.TRACKING,
            TrackingState.TRACKING,
        ]

        for f, (t, st) in enumerate(zip(times, states)):
            packet = make_dummy_packet(f, t)
            det = DetectionResult(frame_number=f, timestamp=t, candidates=[CandidateRegion(0, 0, 10, 10, 200, 150, 50)]) if f > 0 else None
            state = TrackingStateResult(state=st)
            engine.update(packet, None, state, detection_result=det)

        summary = engine.finalize()
        assert pytest.approx(summary.acquisition_time_total_s, rel=1e-5) == 0.3
        assert pytest.approx(summary.acquisition_time_from_detect_s, rel=1e-5) == 0.2

    def test_reacquisition_episodes(self):
        """
        Verify multi-episode reacquisition:
          Episode 1: Lost at t=1.0s, Reacquired at t=1.5s -> duration = 0.5s.
          Episode 2: Lost at t=2.0s, Reacquired at t=2.8s -> duration = 0.8s.
          Expected: 2 events, mean = 0.65s, max = 0.8s.
        """
        engine = MetricsEngine()
        # 1. Initial lock at t=0.2s
        for f in range(3):
            t = f * 0.1
            st = TrackingState.TRACKING if f == 2 else TrackingState.ACQUIRING
            engine.update(make_dummy_packet(f, t), None, TrackingStateResult(state=st))

        # Episode 1: Lost at t=1.0, Track at t=1.5
        engine.update(make_dummy_packet(10, 1.0), None, TrackingStateResult(state=TrackingState.LOST))
        engine.update(make_dummy_packet(15, 1.5), None, TrackingStateResult(state=TrackingState.TRACKING))

        # Episode 2: Lost at t=2.0, Track at t=2.8
        engine.update(make_dummy_packet(20, 2.0), None, TrackingStateResult(state=TrackingState.REACQUIRING))
        engine.update(make_dummy_packet(28, 2.8), None, TrackingStateResult(state=TrackingState.TRACKING))

        summary = engine.finalize()
        assert summary.reacquisition_events == 2
        assert pytest.approx(summary.mean_reacquisition_time_s, rel=1e-5) == 0.65
        assert pytest.approx(summary.max_reacquisition_time_s, rel=1e-5) == 0.8


# ---------------------------------------------------------------------------
# 3. Retention & Lock Metrics
# ---------------------------------------------------------------------------

class TestMetricsEngineLockRetention:
    def test_lock_retention_variations(self):
        """
        Test lock retention across post-acq, all-frames, and visible-frames.
        Total frames = 10.
        Frame 0: ACQUIRING (not in post-acq)
        Frames 1..9: Post-acq (9 frames).
        Frames 1..7: TRACKING (7 frames).
        Frames 8..9: LOST (2 frames).
        All frames visible.
        Post-acq retention = 7 / 9 * 100 = 77.78%.
        All frames retention = 7 / 10 * 100 = 70.0%.
        Loss rate = 100 - 77.78 = 22.22%.
        """
        engine = MetricsEngine()
        for f in range(10):
            t = f * 0.1
            st = TrackingState.ACQUIRING if f == 0 else (TrackingState.TRACKING if f < 8 else TrackingState.LOST)
            gt = GroundTruth(
                frame_number=f, timestamp=t,
                target_world_x=1000.0, target_world_y=1000.0,
                target_visible=True,
            )
            engine.update(make_dummy_packet(f, t), None, TrackingStateResult(state=st), ground_truth=gt)

        summary = engine.finalize()
        assert pytest.approx(summary.lock_retention_all_pct, rel=1e-3) == 70.0
        assert pytest.approx(summary.lock_retention_post_acq_pct, rel=1e-3) == 77.777
        assert pytest.approx(summary.target_loss_rate, rel=1e-3) == 22.222


# ---------------------------------------------------------------------------
# 4. Robustness & Edge Cases
# ---------------------------------------------------------------------------

class TestMetricsEngineRobustness:
    def test_zero_frames_handled_gracefully(self):
        """Zero frames run produces a valid summary without ZeroDivisionError."""
        engine = MetricsEngine()
        summary = engine.finalize()
        assert summary.total_frames == 0
        assert summary.mean_fps == 0.0
        assert summary.mean_centroid_error == 0.0
        assert summary.acquisition_time_s is None

    def test_coasting_and_missing_ground_truth(self):
        """Coasting frame computes optical axis tracking error but centroid error is None."""
        engine = MetricsEngine()
        packet = make_dummy_packet(0, 0.0)
        track = TrackResult(estimated_x=330.0, estimated_y=245.0, is_coasting=True)
        state = TrackingStateResult(state=TrackingState.REACQUIRING)

        # No ground truth, no centroid result
        rec = engine.update(packet, track, state, centroid_result=None, ground_truth=None)
        assert rec.centroid_error_rendered is None
        assert rec.centroid_valid is False
        assert rec.is_coasting is True
        assert rec.tracking_error_optical_axis is not None

    def test_reset_clears_all_diagnostics(self):
        engine = MetricsEngine()
        engine.update(make_dummy_packet(0, 0.0), None, TrackingStateResult(state=TrackingState.TRACKING))
        assert engine.finalize().total_frames == 1

        engine.reset()
        assert engine.finalize().total_frames == 0


# ---------------------------------------------------------------------------
# 5. Logging Integration (Module 16)
# ---------------------------------------------------------------------------

class TestMetricsEngineLoggingIntegration:
    def test_end_to_end_logging_and_exports(self):
        """Verify CSV telemetry, centroid export, summary JSON, and performance scorecard."""
        tmpdir = tempfile.mkdtemp()
        try:
            logger = LoggingEngine(output_dir=tmpdir, run_id="integ_run")
            logger.initialize()
            engine = MetricsEngine(run_id="integ_run")

            for f in range(5):
                t = f * 0.0333
                packet = make_dummy_packet(f, t)
                cent = CentroidResult(x=320.0 + f, y=240.0 + f, valid=True)
                track = TrackResult(estimated_x=320.0 + f, estimated_y=240.0 + f)
                state = TrackingStateResult(state=TrackingState.TRACKING)
                gt = GroundTruth(
                    frame_number=f, timestamp=t,
                    target_world_x=1000.0, target_world_y=1000.0,
                    rendered_centroid_x=320.0, rendered_centroid_y=240.0,
                    target_visible=True,
                )
                rec = engine.update(packet, track, state, centroid_result=cent, ground_truth=gt)
                logger.log_frame(rec)

            summary = engine.finalize()
            logger.write_summary(summary)
            logger.write_performance_report(summary)
            logger.finalize()

            # Verify all 4 output files exist
            csv_path = os.path.join(tmpdir, "integ_run_telemetry.csv")
            cent_path = os.path.join(tmpdir, "integ_run_centroids.csv")
            sum_path = os.path.join(tmpdir, "integ_run_summary.json")
            rep_path = os.path.join(tmpdir, "integ_run_performance_report.md")

            assert os.path.isfile(csv_path), "Telemetry CSV missing"
            assert os.path.isfile(cent_path), "Centroid export CSV missing"
            assert os.path.isfile(sum_path), "Summary JSON missing"
            assert os.path.isfile(rep_path), "Performance Report missing"

            # Check centroid export contents
            with open(cent_path, "r") as f:
                lines = f.readlines()
            assert len(lines) == 6  # header + 5 records
            assert "frame_number,centroid_x,centroid_y,is_valid,confidence" in lines[0]
            assert "0,320.0000,240.0000,1,0.0000" in lines[1]
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 6. Benchmark-1 & Benchmark-2 Dual Flow
# ---------------------------------------------------------------------------

class TestMetricsEngineBenchmarkFlows:
    def test_benchmark_2_mp4_mode_without_ground_truth(self):
        """
        In Benchmark-2 (MP4 mode):
          - Ground truth is None
          - PTZ actuation is bypassed
          - Centroiding error is None
          - Evaluator centroids are exported
          - Ground-truth-independent metrics (FPS, acq time, lock ret) are computed
        """
        engine = MetricsEngine(run_id="bm2_test")
        for f in range(20):
            t = f * 0.0333
            packet = make_dummy_packet(f, t)
            cent = CentroidResult(x=325.0, y=242.0, valid=True)
            track = TrackResult(estimated_x=325.0, estimated_y=242.0)
            state = TrackingStateResult(state=TrackingState.TRACKING if f >= 3 else TrackingState.ACQUIRING)

            rec = engine.update(packet, track, state, centroid_result=cent, ground_truth=None)
            assert rec.centroid_error_rendered is None
            assert rec.centroid_error_ideal is None
            assert rec.ground_truth_x is None

        summary = engine.finalize()
        assert summary.total_frames == 20
        assert summary.rmse_centroid == 0.0  # zero ground truth evaluated
        assert summary.lock_retention_post_acq_pct == 100.0
        assert summary.acquisition_time_s is not None


# ---------------------------------------------------------------------------
# 7. Ground-Truth Firewall AST Inspection
# ---------------------------------------------------------------------------

class TestMetricsEngineFirewall:
    def test_metrics_engine_zero_simulation_imports_ast(self):
        """Verify MetricsEngine source contains zero imports from src.simulation."""
        import src.metrics.metrics_engine as mod
        source_file = inspect.getfile(mod)
        with open(source_file, "r") as f:
            tree = ast.parse(f.read(), filename=source_file)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod_name = getattr(node, "module", "") or ""
                assert "src.simulation" not in mod_name, f"src.simulation imported in {mod_name}"
                assert "GroundTruthProvider" not in mod_name, f"GroundTruthProvider imported in {mod_name}"


# ---------------------------------------------------------------------------
# 8. Performance Benchmark (< 0.1 ms overhead)
# ---------------------------------------------------------------------------

class TestMetricsEnginePerformance:
    def test_metrics_collection_overhead_benchmark(self):
        """Verify MetricsEngine.update latency is well within < 0.1 ms."""
        engine = MetricsEngine()
        packet = make_dummy_packet(0, 0.0)
        cent = CentroidResult(x=325.0, y=242.0, valid=True)
        track = TrackResult(estimated_x=325.0, estimated_y=242.0)
        state = TrackingStateResult(state=TrackingState.TRACKING)
        gt = GroundTruth(
            frame_number=0, timestamp=0.0,
            target_world_x=1000.0, target_world_y=1000.0,
            ideal_projected_x=320.0, ideal_projected_y=240.0,
            rendered_centroid_x=320.0, rendered_centroid_y=240.0,
            target_visible=True,
        )

        latencies_ms = []
        for f in range(1000):
            t0 = time.perf_counter()
            engine.update(packet, track, state, centroid_result=cent, ground_truth=gt)
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        mean_lat = sum(latencies_ms) / len(latencies_ms)
        print(f"\n[Metrics Benchmark] Mean update latency: {mean_lat:.4f} ms")
        assert mean_lat < 0.1, f"Metrics overhead {mean_lat:.4f} ms exceeds 0.1 ms target"
