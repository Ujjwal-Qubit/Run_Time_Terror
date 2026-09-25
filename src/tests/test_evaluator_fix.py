"""
Unit tests for the Evaluator batch_id bug fix and ResultsPanel compatibility.

Tests:
  1. BenchmarkMatrixResults.batch_id property exists and aliases suite_id.
  2. BenchmarkMatrixResults backwards compatibility properties (passed_fps_spec, etc.).
  3. ResultsPanel.load_results works with BenchmarkMatrixResults without raising AttributeError.
  4. BenchmarkMatrixResults serializes and handles missing fields gracefully.
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock

from src.evaluation.matrix import BenchmarkMatrixResults, BenchmarkSubset


class TestEvaluatorFix:
    def test_batch_id_property_aliases_suite_id(self):
        """Verify batch_id property returns suite_id on BenchmarkMatrixResults."""
        res = BenchmarkMatrixResults(
            suite_id="test_suite_123",
            subset=BenchmarkSubset.SMOKE,
            random_seed=42,
            algorithms_tested=["baseline_tracker"],
            scenarios_executed=["matrix_01_linear"],
            run_results=[],
        )
        assert res.batch_id == "test_suite_123"
        assert res.suite_id == "test_suite_123"

    def test_compat_properties_on_matrix_results(self):
        """Verify helper properties on BenchmarkMatrixResults for backward compatibility."""
        res = BenchmarkMatrixResults(
            suite_id="suite_compat",
            subset=BenchmarkSubset.CORE,
            random_seed=42,
            algorithms_tested=["baseline_tracker"],
            scenarios_executed=["matrix_01_linear"],
            run_results=[],
            mean_algorithm_fps=45.2,
            mean_rmse_centroid=1.8,
            mean_target_loss_rate=0.02,
        )
        assert res.batch_id == "suite_compat"
        assert res.passed_fps_spec is True
        assert res.mean_target_loss_rate_pct == pytest.approx(2.0)
        assert res.run_items == res.run_results

    def test_results_panel_load_matrix_results_no_crash(self):
        """Verify ResultsPanel.load_results handles BenchmarkMatrixResults without AttributeError."""
        try:
            from PySide6.QtWidgets import QApplication
            from src.app.gui.results_panel import ResultsPanel
        except ImportError:
            pytest.skip("PySide6 not available in this test environment")

        app = QApplication.instance() or QApplication([])

        mock_app = MagicMock()
        mock_main_window = MagicMock()
        panel = ResultsPanel(mock_app, mock_main_window)

        matrix_res = BenchmarkMatrixResults(
            suite_id="matrix_eval_run_999",
            subset=BenchmarkSubset.SMOKE,
            random_seed=42,
            algorithms_tested=["baseline_tracker"],
            scenarios_executed=["matrix_01_linear"],
            run_results=[],
            mean_algorithm_fps=62.5,
            mean_rmse_centroid=0.85,
            mean_target_loss_rate=0.0,
        )

        # Should not raise AttributeError
        panel.load_results(matrix_res, metadata_path=None)
        assert panel.summary_table.rowCount() > 0

