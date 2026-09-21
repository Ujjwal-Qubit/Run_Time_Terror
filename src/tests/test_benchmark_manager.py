"""
Tests for BenchmarkManager (Module 17) — BM1 and BM2 Workflows.
Verifies:
  1. Deterministic seed reproducibility (identical seeds produce identical metrics).
  2. Batch scenario execution across multiple scenarios.
  3. Grand Evaluation scorecard generation (JSON and Markdown reports).
  4. Fault isolation (corrupt scenario does not crash the entire batch).
"""

import json
import os
import shutil
import tempfile
import pytest

from src.app.app_controller import AppController
from src.evaluation.benchmark_manager import BenchmarkManager
from src.metrics.logging_engine import LoggingEngine


@pytest.fixture
def temp_eval_dir():
    d = tempfile.mkdtemp(prefix="sih_test_bm_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_bm1_deterministic_seed_reproducibility(temp_eval_dir):
    """Verifies that running the same scenario with the same seed yields exact identical results."""
    scenario_path = "scenarios/scenario_1_static.json"
    assert os.path.isfile(scenario_path), "Base scenario 1 must exist"

    # Run 1
    app1 = AppController()
    app1.config_manager.load_from_file(scenario_path)
    app1.config_manager.config.simulation.duration_s = 2.0  # 60 frames
    app1.config_manager.config.simulation.random_seed = 42
    app1.config_manager.config.logging.output_dir = os.path.join(temp_eval_dir, "run1")
    app1.initialize()
    bm1 = BenchmarkManager(app1)
    summary1 = bm1.run_benchmark()
    app1.stop()

    # Run 2 with identical seed
    app2 = AppController()
    app2.config_manager.load_from_file(scenario_path)
    app2.config_manager.config.simulation.duration_s = 2.0
    app2.config_manager.config.simulation.random_seed = 42
    app2.config_manager.config.logging.output_dir = os.path.join(temp_eval_dir, "run2")
    app2.initialize()
    bm2 = BenchmarkManager(app2)
    summary2 = bm2.run_benchmark()
    app2.stop()

    assert summary1.total_frames == summary2.total_frames
    assert summary1.frames_tracked_count == summary2.frames_tracked_count
    assert abs(summary1.mean_tracking_error - summary2.mean_tracking_error) < 1e-4
    assert abs(summary1.rmse_centroid - summary2.rmse_centroid) < 1e-4
    assert summary1.lock_retention_rate == summary2.lock_retention_rate


def test_bm1_batch_scenario_evaluation(temp_eval_dir):
    """Verifies evaluate_batch_scenarios executes multiple scenarios and produces reports."""
    scenarios_dir = os.path.join(temp_eval_dir, "scenarios")
    out_dir = os.path.join(temp_eval_dir, "output")
    os.makedirs(scenarios_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # Copy 2 scenarios into temp scenarios dir with short duration
    for s_name in ("scenario_1_static.json", "scenario_2_circular.json"):
        src_path = os.path.join("scenarios", s_name)
        with open(src_path, "r") as f:
            data = json.load(f)
        data["simulation"]["duration_s"] = 3.0  # 90 frames for steady-state convergence
        with open(os.path.join(scenarios_dir, s_name), "w") as f:
            json.dump(data, f)

    bm = BenchmarkManager()
    grand_summary = bm.evaluate_batch_scenarios(
        scenario_dir=scenarios_dir,
        output_dir=out_dir,
    )

    assert grand_summary.total_runs == 2
    assert grand_summary.successful_runs == 2
    assert grand_summary.failed_runs == 0
    assert grand_summary.total_frames_processed == 180
    assert grand_summary.mean_tracking_error <= 10.0
    assert grand_summary.overall_compliance is True

    # Check that Grand JSON and Markdown reports were written
    reports = os.listdir(out_dir)
    assert any(r.endswith("_grand_summary.json") for r in reports)
    assert any(r.endswith("_grand_evaluator_report.md") for r in reports)


def test_bm1_batch_fault_tolerance(temp_eval_dir):
    """Verifies that a malformed scenario does not crash the entire batch run."""
    scenarios_dir = os.path.join(temp_eval_dir, "scenarios")
    out_dir = os.path.join(temp_eval_dir, "output")
    os.makedirs(scenarios_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # Valid scenario
    src_path = os.path.join("scenarios", "scenario_1_static.json")
    with open(src_path, "r") as f:
        data = json.load(f)
    data["simulation"]["duration_s"] = 0.5
    with open(os.path.join(scenarios_dir, "valid.json"), "w") as f:
        json.dump(data, f)

    # Corrupted scenario
    with open(os.path.join(scenarios_dir, "corrupt.json"), "w") as f:
        f.write("{ invalid json content ]]]")

    bm = BenchmarkManager()
    grand_summary = bm.evaluate_batch_scenarios(
        scenario_dir=scenarios_dir,
        output_dir=out_dir,
    )

    assert grand_summary.total_runs == 2
    assert grand_summary.successful_runs == 1
    assert grand_summary.failed_runs == 1
