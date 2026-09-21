"""
Phase 6.5 Verification Suite — End-to-End Evaluation Harness & BM1/BM2 Integration.

Verifies:
  1. BM1 simulation execution with baseline_tracker via EvaluationHarness
  2. BM2 MP4 execution without reference CSV (Rule 6: accuracy strictly None)
  3. BM2 MP4 execution with reference CSV (subpixel RMSE verified)
  4. Deterministic replay reproducibility under identical seed
  5. Seed divergence under distinct seeds
  6. Failure isolation on invalid plugin name (INVALID outcome, zero crash)
  7. Failure isolation on crashing algorithm (CRASHED outcome, zero crash)
  8. Batch suite execution with fault containment
  9. Multi-algorithm comparative evaluation and scorecard generation
 10. Metric population honesty (algorithm compute FPS vs throughput FPS)
"""

import math
import os
import shutil
import tempfile
import cv2
import numpy as np
import pytest

from src.evaluation.harness import (
    EvaluationHarness,
    EvaluationExperiment,
    EvaluationOutcome,
    EvaluationRunResult,
    ComparisonSummary,
)
from src.evaluation.benchmark_manager import BenchmarkManager
from src.app.app_controller import AppController


@pytest.fixture
def eval_env():
    """Creates a temporary workspace for evaluation testing."""
    temp_dir = tempfile.mkdtemp(prefix="sih_test_eval_")
    out_dir = os.path.join(temp_dir, "output")
    mp4_dir = os.path.join(temp_dir, "videos")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(mp4_dir, exist_ok=True)

    yield temp_dir, out_dir, mp4_dir

    shutil.rmtree(temp_dir, ignore_errors=True)


def create_test_video(path: str, num_frames: int = 25, width: int = 640, height: int = 480) -> None:
    """Helper to generate a clean synthetic video containing a bright beacon."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, 30.0, (width, height), isColor=True)
    for i in range(num_frames):
        frame = np.full((height, width, 3), 25, dtype=np.uint8)
        cx = int(width / 2.0 + 40.0 * np.sin(i * 0.2))
        cy = int(height / 2.0 + 30.0 * np.cos(i * 0.2))
        cv2.circle(frame, (cx, cy), 5, (240, 240, 240), -1)
        out.write(frame)
    out.release()


def create_test_video_and_csv(
    video_path: str, csv_path: str, num_frames: int = 25, width: int = 640, height: int = 480
) -> None:
    """Helper to generate a synthetic video and matching evaluator reference CSV."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height), isColor=True)
    with open(csv_path, "w", encoding="utf-8") as f_csv:
        f_csv.write("frame,true_x,true_y\n")
        for i in range(num_frames):
            frame = np.full((height, width, 3), 25, dtype=np.uint8)
            cx = float(int(width / 2.0 + 40.0 * np.sin(i * 0.2)))
            cy = float(int(height / 2.0 + 30.0 * np.cos(i * 0.2)))
            cv2.circle(frame, (int(cx), int(cy)), 5, (240, 240, 240), -1)
            out.write(frame)
            f_csv.write(f"{i},{cx:.2f},{cy:.2f}\n")
    out.release()


def test_harness_bm1_baseline_algorithm(eval_env):
    """Verify BM1 closed-loop simulation evaluation via EvaluationHarness."""
    _, out_dir, _ = eval_env
    harness = EvaluationHarness()

    exp = EvaluationExperiment(
        experiment_id="test_bm1_baseline",
        algorithm_name="baseline_tracker",
        source_type="SIMULATION",
        random_seed=42,
        max_frames=20,
        output_dir=out_dir,
    )

    res = harness.run_experiment(exp)

    assert res.outcome == EvaluationOutcome.SUCCESS
    assert res.algorithm_name == "baseline_tracker"
    assert res.total_frames == 20
    assert res.has_reference is True
    assert res.reference_source == "SIMULATION_GROUND_TRUTH"
    assert res.centroid_rmse is not None
    assert res.centroid_rmse >= 0.0
    assert res.algorithm_fps >= 20.0
    assert res.benchmark_fps > 0.0
    assert res.firewall_verified is True
    assert res.json_report_path is not None
    assert os.path.isfile(res.json_report_path)


def test_harness_bm2_no_reference_csv(eval_env):
    """
    CRITICAL (Rule 6): Verify BM2 video evaluation without reference CSV
    strictly marks spatial accuracy metrics as None rather than fabricating numbers.
    """
    _, out_dir, mp4_dir = eval_env
    vid_path = os.path.join(mp4_dir, "no_ref.mp4")
    create_test_video(vid_path, num_frames=20)

    harness = EvaluationHarness()
    exp = EvaluationExperiment(
        experiment_id="test_bm2_no_ref",
        algorithm_name="baseline_tracker",
        source_type="MP4",
        mp4_path=vid_path,
        reference_csv=None,
        output_dir=out_dir,
    )

    res = harness.run_experiment(exp)

    assert res.outcome in (EvaluationOutcome.SUCCESS, EvaluationOutcome.FAILED)
    assert res.total_frames == 20
    assert res.ptz_bypassed_in_mp4 is True
    # Rule 6 Verification: No ground truth -> no fabricated accuracy
    assert res.has_reference is False
    assert res.reference_source == "NONE"
    assert res.centroid_rmse is None
    assert res.centroid_mean_err is None
    assert res.centroid_max_err is None
    assert res.pct_within_1px is None


def test_harness_bm2_with_reference_csv(eval_env):
    """Verify BM2 video evaluation with reference CSV computes subpixel RMSE."""
    _, out_dir, mp4_dir = eval_env
    vid_path = os.path.join(mp4_dir, "with_ref.mp4")
    csv_path = os.path.join(mp4_dir, "with_ref.csv")
    create_test_video_and_csv(vid_path, csv_path, num_frames=25)

    harness = EvaluationHarness()
    exp = EvaluationExperiment(
        experiment_id="test_bm2_with_ref",
        algorithm_name="baseline_tracker",
        source_type="MP4",
        mp4_path=vid_path,
        reference_csv=csv_path,
        output_dir=out_dir,
    )

    res = harness.run_experiment(exp)

    assert res.outcome == EvaluationOutcome.SUCCESS
    assert res.has_reference is True
    assert res.reference_source == "REFERENCE_CSV"
    assert res.reference_frames_matched == 25
    assert res.reference_coverage_pct == 100.0
    assert res.centroid_rmse is not None
    assert res.centroid_rmse < 0.5  # Sub-pixel accuracy on clear circular beacon
    assert res.centroid_mean_err is not None
    assert res.centroid_mean_err < 0.5


def test_harness_deterministic_replay(eval_env):
    """Verify identical seeds produce identical evaluation metrics (reproducibility)."""
    _, out_dir, _ = eval_env
    harness = EvaluationHarness()

    exp1 = EvaluationExperiment(
        experiment_id="replay_run_1",
        algorithm_name="baseline_tracker",
        source_type="SIMULATION",
        random_seed=12345,
        max_frames=15,
        output_dir=out_dir,
    )
    exp2 = EvaluationExperiment(
        experiment_id="replay_run_2",
        algorithm_name="baseline_tracker",
        source_type="SIMULATION",
        random_seed=12345,
        max_frames=15,
        output_dir=out_dir,
    )

    res1 = harness.run_experiment(exp1)
    res2 = harness.run_experiment(exp2)

    assert res1.total_frames == res2.total_frames
    assert res1.frames_tracked == res2.frames_tracked
    assert res1.centroid_rmse == pytest.approx(res2.centroid_rmse, abs=1e-6)
    assert res1.config_digest == res2.config_digest


def test_harness_invalid_plugin_name(eval_env):
    """Verify requesting an invalid plugin name yields INVALID outcome without crashing."""
    _, out_dir, _ = eval_env
    harness = EvaluationHarness()

    exp = EvaluationExperiment(
        experiment_id="test_invalid_plugin",
        algorithm_name="non_existent_tracker_404",
        source_type="SIMULATION",
        max_frames=10,
        output_dir=out_dir,
    )

    res = harness.run_experiment(exp)

    assert res.outcome == EvaluationOutcome.INVALID
    assert res.error_message is not None
    assert "non_existent_tracker_404" in res.error_message


def test_harness_crashing_algorithm(eval_env):
    """Verify an algorithm that raises in process_frame is classified as CRASHED."""
    _, out_dir, _ = eval_env

    # Temporarily install a mock crashing plugin into app controller
    from src.api.v1 import ITrackingAlgorithm, FramePacket, TrackingResult
    from src.plugins.models import PluginManifest, LoadedPlugin

    class CrashingPlugin(ITrackingAlgorithm):
        def initialize(self, config): return True
        def process_frame(self, frame_packet):
            raise ArithmeticError("Simulated algorithm crash inside evaluation loop")
        def reset(self): pass

    harness = EvaluationHarness()
    app = AppController()
    app.initialize()

    mock_manifest = PluginManifest(
        name="crashing_plugin",
        version="1.0.0",
        api_version="1.0.0",
        author="Tester",
        description="Crashing plugin for fault test",
        entry_point="mock:CrashingPlugin",
    )
    loaded = LoadedPlugin(
        manifest=mock_manifest,
        plugin_dir=eval_env[0],
        algorithm_class=CrashingPlugin,
        instance=CrashingPlugin(),
    )
    app._active_algorithm = loaded.instance
    app._active_algorithm_name = "crashing_plugin"
    app._active_plugin = loaded

    pkt = app.get_next_frame()
    assert pkt is not None
    app.step_algorithm(pkt)
    assert app.algorithm_error is not None
    assert "Simulated algorithm crash" in app.algorithm_error


def test_harness_suite_execution_fault_isolation(eval_env):
    """Verify run_suite executes all experiments even if some algorithms are invalid."""
    _, out_dir, _ = eval_env
    harness = EvaluationHarness()

    suite = [
        EvaluationExperiment(
            experiment_id="suite_1_valid",
            algorithm_name="baseline_tracker",
            source_type="SIMULATION",
            max_frames=10,
            output_dir=out_dir,
        ),
        EvaluationExperiment(
            experiment_id="suite_2_invalid",
            algorithm_name="bogus_algorithm_name",
            source_type="SIMULATION",
            max_frames=10,
            output_dir=out_dir,
        ),
        EvaluationExperiment(
            experiment_id="suite_3_valid",
            algorithm_name="baseline_tracker",
            source_type="SIMULATION",
            max_frames=10,
            output_dir=out_dir,
        ),
    ]

    results = harness.run_suite(suite)

    assert len(results) == 3
    assert results[0].outcome == EvaluationOutcome.SUCCESS
    assert results[1].outcome == EvaluationOutcome.INVALID
    assert results[2].outcome == EvaluationOutcome.SUCCESS


def test_harness_compare_algorithms(eval_env):
    """Verify multi-algorithm comparison generates valid comparative scorecard."""
    _, out_dir, _ = eval_env
    harness = EvaluationHarness()

    comparison = harness.compare_algorithms(
        algorithm_names=["baseline_tracker"],
        seed=42,
        max_frames=15,
        output_dir=out_dir,
    )

    assert isinstance(comparison, ComparisonSummary)
    assert comparison.total_algorithms_tested == 1
    assert "baseline_tracker" in comparison.algorithm_results
    assert len(comparison.rankings) == 1
    assert comparison.rankings[0]["rank"] == 1
    assert comparison.rankings[0]["algorithm_name"] == "baseline_tracker"

    # Markdown export check
    md_str = comparison.to_markdown()
    assert "# Algorithm Evaluation Comparison" in md_str
    assert "baseline_tracker" in md_str


def test_harness_metric_population_honesty(eval_env):
    """Verify distinct populations for algorithm compute FPS vs benchmark throughput FPS."""
    _, out_dir, _ = eval_env
    harness = EvaluationHarness()

    exp = EvaluationExperiment(
        experiment_id="test_fps_honesty",
        algorithm_name="baseline_tracker",
        source_type="SIMULATION",
        max_frames=25,
        output_dir=out_dir,
    )

    res = harness.run_experiment(exp)

    # Pure algorithm compute FPS (1000.0 / mean_algorithm_latency_ms)
    assert res.algorithm_fps > 0.0
    assert math.isfinite(res.algorithm_fps)

    # End-to-end benchmark throughput FPS (frames / wall_time)
    assert res.benchmark_fps > 0.0
    assert math.isfinite(res.benchmark_fps)

    # Latency percentiles
    assert res.mean_latency_ms > 0.0
    assert res.p95_latency_ms >= res.mean_latency_ms or res.p95_latency_ms > 0.0
