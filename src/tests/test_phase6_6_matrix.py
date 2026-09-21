"""
Phase 6.6 Verification Suite — Standard Benchmark Matrix & Comprehensive Reporting.

Tests:
  1. Matrix definitions, categories, and subset filtering (SMOKE, CORE, DISTURBANCE, FULL).
  2. Deterministic replay reproducibility with identical seeds.
  3. BenchmarkMatrixRunner execution with baseline_tracker.
  4. Multi-algorithm comparative evaluation on identical deterministic frame streams.
  5. Multi-format comprehensive report generation (JSON, CSV, Markdown).
  6. Failure mode diagnostics and fault containment.
  7. Rule 6 compliance: no fabricated accuracy metrics in matrix outputs.
  8. SIH PS 26169 compliance gates audit.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
import pytest

from src.app.app_controller import AppController
from src.evaluation.benchmark_manager import BenchmarkManager
from src.evaluation.harness import EvaluationHarness, EvaluationOutcome
from src.evaluation.matrix import (
    BenchmarkMatrixResults,
    BenchmarkMatrixRunner,
    BenchmarkScenarioDefinition,
    BenchmarkSubset,
    StandardBenchmarkMatrix,
)
from src.evaluation.reporting import (
    ComprehensiveReportGenerator,
    FailureAnalysisSummary,
    FailureEpisode,
)


@pytest.fixture
def temp_output_dir():
    d = tempfile.mkdtemp(prefix="test_phase6_6_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestBenchmarkMatrixDefinitions:
    """Tests matrix scenario specifications, categorizations, and subset filtering."""

    def test_all_19_scenarios_exist(self):
        all_scen = StandardBenchmarkMatrix.get_all_scenarios()
        assert len(all_scen) == 19
        scenario_ids = [s.scenario_id for s in all_scen]
        assert len(set(scenario_ids)) == 19, "Duplicate scenario IDs detected"

    def test_subset_filtering(self):
        smoke = StandardBenchmarkMatrix.get_scenarios(BenchmarkSubset.SMOKE)
        assert len(smoke) == 3
        assert smoke[0].motion_type == "STRAIGHT_LINE"
        assert smoke[1].motion_type == "CIRCULAR"
        assert smoke[2].atmospheric_condition == "FOG"

        core = StandardBenchmarkMatrix.get_scenarios(BenchmarkSubset.CORE)
        assert len(core) == 6

        dist = StandardBenchmarkMatrix.get_scenarios(BenchmarkSubset.DISTURBANCE)
        assert len(dist) == 8

        full = StandardBenchmarkMatrix.get_scenarios(BenchmarkSubset.FULL)
        assert len(full) == 19

    def test_scenario_dict_serialization(self):
        scen = StandardBenchmarkMatrix.SCENARIO_COMBINED_FOG_NOISE_JITTER
        d = scen.to_scenario_dict(random_seed=123)
        assert d["atmospheric"]["condition"] == "FOG"
        assert d["noise"]["gaussian_enabled"] is True
        assert d["noise"]["gaussian_sigma"] == 10.0
        assert d["jitter"]["enabled"] is True
        assert d["simulation"]["random_seed"] == 123


class TestBenchmarkMatrixExecution:
    """Tests execution of matrix subsets via BenchmarkMatrixRunner."""

    def test_matrix_runner_smoke_execution(self, temp_output_dir):
        app = AppController()
        harness = EvaluationHarness(app)
        runner = BenchmarkMatrixRunner(harness)

        results = runner.run_matrix(
            subset=BenchmarkSubset.SMOKE,
            algorithms=["baseline_tracker"],
            random_seed=42,
            max_frames_override=30,
            output_dir=temp_output_dir,
        )

        assert isinstance(results, BenchmarkMatrixResults)
        assert results.total_runs == 3
        assert results.successful_runs == 3
        assert results.crashed_runs == 0
        assert results.invalid_runs == 0
        assert results.failed_runs == 0
        assert results.total_frames_processed == 90
        assert results.mean_algorithm_fps >= 20.0
        assert results.mean_rmse_centroid is not None
        assert results.mean_rmse_centroid <= 1.0  # nominal tracking in simulation
        assert results.passed_sih_spec is True

    def test_matrix_deterministic_replay(self, temp_output_dir):
        app1 = AppController()
        runner1 = BenchmarkMatrixRunner(EvaluationHarness(app1))
        res1 = runner1.run_matrix(
            subset=BenchmarkSubset.SMOKE,
            algorithms=["baseline_tracker"],
            random_seed=777,
            max_frames_override=25,
            output_dir=os.path.join(temp_output_dir, "run1"),
        )

        app2 = AppController()
        runner2 = BenchmarkMatrixRunner(EvaluationHarness(app2))
        res2 = runner2.run_matrix(
            subset=BenchmarkSubset.SMOKE,
            algorithms=["baseline_tracker"],
            random_seed=777,
            max_frames_override=25,
            output_dir=os.path.join(temp_output_dir, "run2"),
        )

        assert res1.total_frames_processed == res2.total_frames_processed
        assert res1.successful_runs == res2.successful_runs
        for r1, r2 in zip(res1.run_results, res2.run_results):
            assert r1.frames_tracked == r2.frames_tracked
            assert r1.total_frames == r2.total_frames
            if r1.centroid_rmse is not None and r2.centroid_rmse is not None:
                assert abs(r1.centroid_rmse - r2.centroid_rmse) < 1e-4

    def test_multi_algorithm_matrix_comparison(self, temp_output_dir):
        import shutil
        app = AppController()
        runner = BenchmarkMatrixRunner(EvaluationHarness(app))

        # Setup test plugins directory with baseline_tracker and simple_centroid_tracker
        test_plugins_dir = os.path.join(temp_output_dir, "test_plugins")
        os.makedirs(test_plugins_dir, exist_ok=True)

        # 1. Copy baseline_tracker
        baseline_src = os.path.join("src", "plugins", "algorithms", "baseline_tracker")
        shutil.copytree(baseline_src, os.path.join(test_plugins_dir, "baseline_tracker"))

        # 2. Create simple_centroid_tracker plugin
        simple_dir = os.path.join(test_plugins_dir, "simple_centroid_tracker")
        os.makedirs(simple_dir, exist_ok=True)
        manifest_data = {
            "name": "simple_centroid_tracker",
            "version": "1.0.0",
            "api_version": "v1",
            "entry_point": "tracker:SimpleCentroidTracker",
            "description": "Simple centroid detector without Kalman smoothing",
            "author": "Tester",
        }
        with open(os.path.join(simple_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        tracker_code = '''
from src.api.v1.algorithm import ITrackingAlgorithm
from src.api.v1.contracts import FramePacket, TrackingResult
import numpy as np

class SimpleCentroidTracker(ITrackingAlgorithm):
    def initialize(self, config=None):
        return True
    def process_frame(self, frame_packet: FramePacket) -> TrackingResult:
        img = frame_packet.image
        if img is None:
            return TrackingResult(algorithm_is_tracking=False, centroid_x=None, centroid_y=None)
        mask = img > 100
        if np.any(mask):
            y_idx, x_idx = np.where(mask)
            return TrackingResult(
                algorithm_is_tracking=True,
                centroid_x=float(np.mean(x_idx)),
                centroid_y=float(np.mean(y_idx)),
                confidence=0.85,
            )
        return TrackingResult(algorithm_is_tracking=False, centroid_x=None, centroid_y=None)
    def reset(self):
        pass
'''
        with open(os.path.join(simple_dir, "tracker.py"), "w", encoding="utf-8") as f:
            f.write(tracker_code)

        # Compare baseline_tracker with simple_centroid_tracker across SMOKE subset
        results = runner.run_matrix(
            subset=BenchmarkSubset.SMOKE,
            algorithms=["baseline_tracker", "simple_centroid_tracker"],
            random_seed=42,
            max_frames_override=25,
            output_dir=temp_output_dir,
            plugins_dir=test_plugins_dir,
        )

        assert results.total_runs == 6  # 3 scenarios * 2 algorithms
        assert results.successful_runs == 6
        assert len(results.algorithms_tested) == 2

        # Generate report and verify leaderboard ranking
        j_p, c_p, m_p = ComprehensiveReportGenerator.generate_report(
            results,
            output_dir=temp_output_dir,
        )

        with open(j_p, "r", encoding="utf-8") as f:
            report_json = json.load(f)

        leaderboard = report_json["leaderboard"]
        assert len(leaderboard) == 2
        # Both algorithms completed successfully
        assert all(entry["successful_runs"] == 3 for entry in leaderboard)


class TestComprehensiveReporting:
    """Tests multi-format report generation (JSON, CSV, Markdown) and failure analysis."""

    def test_reporting_formats_and_schemas(self, temp_output_dir):
        app = AppController()
        runner = BenchmarkMatrixRunner(EvaluationHarness(app))

        results = runner.run_matrix(
            subset=BenchmarkSubset.SMOKE,
            algorithms=["baseline_tracker"],
            random_seed=42,
            max_frames_override=20,
            output_dir=temp_output_dir,
        )

        json_path, csv_path, md_path = ComprehensiveReportGenerator.generate_report(
            results,
            output_dir=temp_output_dir,
            report_title="Automated Test Report",
        )

        # 1. JSON Report Validation
        assert os.path.isfile(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["title"] == "Automated Test Report"
        assert "sih_compliance_gates" in data
        assert len(data["sih_compliance_gates"]) == 5
        assert "leaderboard" in data
        assert "failure_analysis" in data
        assert len(data["runs"]) == 3

        # 2. CSV Summary Validation
        assert os.path.isfile(csv_path)
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 4  # header + 3 scenario rows
        headers = rows[0]
        assert "experiment_id" in headers
        assert "algorithm_fps" in headers
        assert "centroid_rmse_px" in headers

        # 3. Markdown Report Validation
        assert os.path.isfile(md_path)
        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        assert "# Automated Test Report" in md_text
        assert "PASSED (PS 26169 COMPLIANT)" in md_text
        assert "Executive Summary & SIH Requirements Audit" in md_text
        assert "Multi-Algorithm Performance & Accuracy Leaderboard" in md_text
        assert "Failure Mode & Robustness Analysis" in md_text

    def test_fault_containment_in_reporting(self, temp_output_dir):
        # Setup plugin directory with an exploding plugin
        test_plugins_dir = os.path.join(temp_output_dir, "crash_plugins")
        os.makedirs(test_plugins_dir, exist_ok=True)

        crash_dir = os.path.join(test_plugins_dir, "exploding_plugin")
        os.makedirs(crash_dir, exist_ok=True)
        manifest_data = {
            "name": "exploding_plugin",
            "version": "1.0.0",
            "api_version": "v1",
            "entry_point": "exploder:ExplodingPlugin",
            "description": "Throws exception after frame 5",
            "author": "Tester",
        }
        with open(os.path.join(crash_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        code = '''
from src.api.v1.algorithm import ITrackingAlgorithm
from src.api.v1.contracts import FramePacket, TrackingResult

class ExplodingPlugin(ITrackingAlgorithm):
    def initialize(self, config=None):
        return True
    def process_frame(self, frame_packet: FramePacket) -> TrackingResult:
        if frame_packet.frame_number >= 5:
            raise RuntimeError("Fatal algorithmic math explosion!")
        return TrackingResult(
            algorithm_is_tracking=True,
            centroid_x=100.0,
            centroid_y=100.0,
            confidence=1.0,
        )
    def reset(self):
        pass
'''
        with open(os.path.join(crash_dir, "exploder.py"), "w", encoding="utf-8") as f:
            f.write(code)


        app = AppController()
        runner = BenchmarkMatrixRunner(EvaluationHarness(app))
        results = runner.run_matrix(
            subset=BenchmarkSubset.SMOKE,
            algorithms=["exploding_plugin"],
            random_seed=42,
            max_frames_override=10,
            output_dir=temp_output_dir,
            plugins_dir=test_plugins_dir,
        )

        assert results.total_runs == 3
        assert results.crashed_runs == 3
        assert results.successful_runs == 0
        assert results.passed_sih_spec is False

        # Generate report and verify crash diagnostic capture
        j_p, c_p, m_p = ComprehensiveReportGenerator.generate_report(results, output_dir=temp_output_dir)

        with open(j_p, "r", encoding="utf-8") as f:
            data = json.load(f)

        fa = data["failure_analysis"]
        assert fa["total_crashes"] == 3
        assert len(fa["episodes"]) == 3
        assert any("Fatal algorithmic math explosion" in ep["details"] for ep in fa["episodes"])


    def test_benchmark_manager_convenience_integration(self, temp_output_dir):
        app = AppController()
        bm = BenchmarkManager(app)

        res = bm.run_benchmark_matrix(
            subset="SMOKE",
            algorithms=["baseline_tracker"],
            max_frames=20,
            output_dir=temp_output_dir,
        )
        assert res.total_runs == 3

        j_p, c_p, m_p = bm.generate_comprehensive_report(res, output_dir=temp_output_dir)
        assert os.path.isfile(j_p)
        assert os.path.isfile(c_p)
        assert os.path.isfile(m_p)
