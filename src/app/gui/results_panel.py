from __future__ import annotations

import os
import json
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QTextEdit, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from src.app.app_controller import AppController


class ResultsPanel(QWidget):
    """
    Dedicated workflow page for the Researcher.
    Views scorecards, failure analysis, and exports.
    """

    def __init__(self, app_controller: AppController, main_window):
        super().__init__()
        self.app = app_controller
        self.main_window = main_window
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Results & Analysis (Researcher Workflow)")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #007acc;")
        self.layout.addWidget(title)

        # Breakdown Table
        table_group = QGroupBox("Latest Evaluation Scorecard")
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Metric", "Value", "Status"])
        # Backward-compatible name used by earlier results-page integrations.
        self.summary_table = self.table
        table_layout.addWidget(self.table)
        self.layout.addWidget(table_group, stretch=2)

        # Failure Analysis
        fail_group = QGroupBox("Failure Analysis")
        fail_layout = QVBoxLayout(fail_group)
        self.txt_fail = QTextEdit()
        self.txt_fail.setReadOnly(True)
        self.txt_fail.setStyleSheet("background-color: #2d2d30;")
        fail_layout.addWidget(self.txt_fail)
        self.layout.addWidget(fail_group, stretch=1)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh Results")
        self.btn_export = QPushButton("Export to PDF/Markdown")
        self.btn_refresh.clicked.connect(self._on_refresh)
        self.btn_export.clicked.connect(self._on_export)
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_export)
        self.layout.addLayout(btn_layout)

        self.current_report_path: str | None = None

    def load_results(
        self,
        matrix_res,
        report_path: str | None = None,
        *,
        metadata_path: str | None = None,
    ):
        self.current_report_path = report_path if report_path is not None else metadata_path

        # Populate table
        self.table.setRowCount(0)

        if isinstance(matrix_res, dict):
            summary = matrix_res.get("overall_summary", matrix_res)
            passed = summary.get("passed_sih_spec", False)
            mean_fps = float(summary.get("mean_algorithm_fps", 0.0))
            rmse_val = summary.get("mean_rmse_centroid")
            if rmse_val is not None:
                rmse_val = float(rmse_val)
            loss_rate = float(summary.get("mean_target_loss_rate", 0.0))
            succ_runs = int(summary.get("successful_runs", 0))
            total_runs = int(summary.get("total_runs", 0))
            suite_id = matrix_res.get("suite_id", "N/A")
            failed_runs = int(summary.get("failed_runs", 0))
            crashed_runs = int(summary.get("crashed_runs", 0))
            fail_analysis = matrix_res.get("failure_analysis", {})
            run_results = matrix_res.get("runs", [])
        else:
            passed = getattr(matrix_res, "passed_sih_spec", False)
            mean_fps = getattr(matrix_res, "mean_algorithm_fps", 0.0)
            rmse_val = getattr(matrix_res, "mean_rmse_centroid", None)
            loss_rate = getattr(matrix_res, "mean_target_loss_rate", 0.0)
            succ_runs = getattr(matrix_res, "successful_runs", 0)
            total_runs = getattr(matrix_res, "total_runs", 0)
            suite_id = getattr(matrix_res, "suite_id", "N/A")
            failed_runs = getattr(matrix_res, "failed_runs", 0)
            crashed_runs = getattr(matrix_res, "crashed_runs", 0)
            fail_analysis = getattr(matrix_res, "failure_analysis", {})
            run_results = getattr(matrix_res, "run_results", [])

        fps_ok = mean_fps >= 20.0 and succ_runs > 0
        rmse_ok = (rmse_val is None or rmse_val <= 10.0) and succ_runs > 0
        loss_ok = loss_rate < 5.0 and succ_runs > 0

        rmse_display = (
            f"{rmse_val:.3f} px" if rmse_val is not None else "N/A (no reference)"
        )
        loss_display = f"{loss_rate:.2f}%"

        metrics = [
            ("Suite ID", str(suite_id), "INFO"),
            ("Verdict", "PASSED" if passed else "FAILED", "PASS" if passed else "FAIL"),
            ("Mean Algo FPS", f"{mean_fps:.1f}", "PASS" if fps_ok else "FAIL"),
            ("Centroid RMSE", rmse_display, "PASS" if rmse_ok else ("N/A" if rmse_val is None else "FAIL")),
            ("Target Loss Rate", loss_display, "PASS" if loss_ok else "FAIL"),
            ("Successful Runs", f"{succ_runs}/{total_runs}", "INFO"),
        ]

        for i, (metric, value, status) in enumerate(metrics):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(metric))
            self.table.setItem(i, 1, QTableWidgetItem(str(value)))

            status_item = QTableWidgetItem(status)
            if status == "PASS":
                status_item.setForeground(Qt.green)
            elif status == "FAIL":
                status_item.setForeground(Qt.red)
            self.table.setItem(i, 2, status_item)

        # Display failure analysis if available
        if failed_runs > 0 or crashed_runs > 0:
            failed_str = f"{failed_runs} failed, {crashed_runs} crashed out of {total_runs} runs.\n"
            if isinstance(fail_analysis, dict):
                for ep in fail_analysis.get("episodes", []):
                    failed_str += f"  - {ep.get('scenario_id', '?')}: {ep.get('details', '')}\n"
            elif run_results:
                from src.evaluation.harness import EvaluationOutcome
                for r in run_results:
                    if getattr(r, "outcome", None) not in (None, EvaluationOutcome.SUCCESS):
                        failed_str += (
                            f"  - {getattr(r, 'experiment_id', '?')}: "
                            f"{getattr(r, 'error_message', 'unknown error')}\n"
                        )
            self.txt_fail.setText(failed_str)
        else:
            self.txt_fail.setText("All runs succeeded. No failures detected.")

    def _on_refresh(self) -> None:
        """Scans output/ directory for the latest benchmark results and reloads."""
        output_dir = Path("output")
        if not output_dir.exists():
            self.txt_fail.setText("No output directory found. Run a benchmark first.")
            return

        json_files = list(output_dir.glob("**/*_report.json")) + list(output_dir.glob("**/*_summary.json"))
        if not json_files:
            self.txt_fail.setText("No report files found in output/. Run a benchmark evaluation first.")
            return

        latest_file = max(json_files, key=os.path.getmtime)
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            md_path = str(latest_file.with_suffix(".md"))
            self.load_results(data, report_path=md_path if os.path.exists(md_path) else str(latest_file))
        except Exception as e:
            self.txt_fail.setText(f"Error loading report {latest_file.name}: {e}")

    def _on_export(self) -> None:
        """Exports current report to destination chosen by user."""
        if not self.current_report_path or not os.path.exists(self.current_report_path):
            QMessageBox.warning(self, "Export Failed", "No report file is currently loaded. Click 'Refresh Results' first.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            os.path.basename(self.current_report_path),
            "Markdown Files (*.md);;JSON Files (*.json);;All Files (*)"
        )
        if save_path:
            try:
                shutil.copyfile(self.current_report_path, save_path)
                QMessageBox.information(self, "Export Successful", f"Report saved to:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save report: {e}")
