"""
Unit tests for developer single-run comprehensive reporting (P2).

Tests:
  1. ComprehensiveReportGenerator.generate_single_run_report produces Markdown, JSON, and CSV files.
  2. Generated JSON report contains correct metric values from MetricsSummary.
  3. Generated Markdown report contains human-readable summary tables.
  4. Generated CSV report contains correct column headers and row data.
  5. BenchmarkManager.generate_single_run_report integration.
"""

from __future__ import annotations
import csv
import json
import os
import shutil
import tempfile
import pytest

from src.frame.data_contracts import MetricsSummary
from src.evaluation.reporting import ComprehensiveReportGenerator
from src.evaluation.benchmark_manager import BenchmarkManager


@pytest.fixture
def temp_report_dir():
    d = tempfile.mkdtemp(prefix="test_single_run_report_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestSingleRunReport:
    def _create_sample_summary(self) -> MetricsSummary:
        summary = MetricsSummary(run_id="run_test_42")
        summary.total_frames = 100
        summary.rmse_centroid = 1.25
        summary.mae_centroid = 0.95
        summary.max_error_centroid = 3.5
        summary.tracking_loss_rate = 0.02
        summary.lost_track_count = 1
        summary.mean_tracking_latency_ms = 8.5
        summary.fps_achieved = 55.0
        summary.passed_accuracy_spec = True
        summary.passed_fps_spec = True
        summary.passed_robustness_spec = True
        summary.passed_overall = True
        return summary

    def test_generate_single_run_report_files_created(self, temp_report_dir):
        summary = self._create_sample_summary()

        json_path, csv_path, md_path = ComprehensiveReportGenerator.generate_single_run_report(
            summary=summary,
            output_dir=temp_report_dir,
            report_title="Test Developer Run",
        )

        assert os.path.isfile(json_path)
        assert os.path.isfile(csv_path)
        assert os.path.isfile(md_path)

    def test_single_run_json_content(self, temp_report_dir):
        summary = self._create_sample_summary()

        json_path, _, _ = ComprehensiveReportGenerator.generate_single_run_report(
            summary=summary,
            output_dir=temp_report_dir,
            report_title="JSON Validation Run",
        )

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "total_frames" in data
        assert "mean_fps" in data
        assert data["total_frames"] == 100
        assert data["mean_fps"] == pytest.approx(55.0)

    def test_single_run_markdown_content(self, temp_report_dir):
        summary = self._create_sample_summary()

        _, _, md_path = ComprehensiveReportGenerator.generate_single_run_report(
            summary=summary,
            output_dir=temp_report_dir,
            report_title="Developer Verification Report",
        )

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Developer Verification Report" in content or "Single-Run Report" in content
        assert "1.25" in content or "RMSE" in content

    def test_single_run_csv_content(self, temp_report_dir):
        summary = self._create_sample_summary()

        _, csv_path, _ = ComprehensiveReportGenerator.generate_single_run_report(
            summary=summary,
            output_dir=temp_report_dir,
        )

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) >= 2  # Header + at least 1 data row
        header = [h.lower() for h in rows[0]]
        assert "metric" in header and "value" in header
        metric_names = [r[0].lower() for r in rows[1:]]
        assert any("fps" in m or "latency" in m or "rmse" in m for m in metric_names)

    def test_benchmark_manager_generate_single_run_report(self, temp_report_dir):
        bm = BenchmarkManager()
        summary = self._create_sample_summary()

        json_p, csv_p, md_p = bm.generate_single_run_report(
            summary=summary,
            output_dir=temp_report_dir,
            scenario_label="scenario_alpha",
        )

        assert os.path.exists(json_p)
        assert os.path.exists(csv_p)
        assert os.path.exists(md_p)
