from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QTextEdit, QTableWidget, QTableWidgetItem
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
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_export)
        self.layout.addLayout(btn_layout)
        
        self.current_report_path = None
        
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

        # Derive per-spec pass/fail from BenchmarkMatrixResults fields
        # (BenchmarkMatrixResults has aggregate metrics, not individual spec flags)
        fps_ok = matrix_res.mean_algorithm_fps >= 20.0 and matrix_res.successful_runs > 0
        rmse_val = matrix_res.mean_rmse_centroid
        rmse_ok = (rmse_val is None or rmse_val <= 10.0) and matrix_res.successful_runs > 0
        loss_ok = matrix_res.mean_target_loss_rate < 5.0 and matrix_res.successful_runs > 0

        # Use suite_id as the identifier (batch_id is a compat alias)
        algo_display = getattr(matrix_res, "suite_id", "N/A")

        rmse_display = (
            f"{rmse_val:.3f} px" if rmse_val is not None else "N/A (no reference)"
        )
        loss_display = f"{matrix_res.mean_target_loss_rate:.2f}%"

        metrics = [
            ("Suite ID", algo_display, "INFO"),
            ("Verdict", "PASSED" if matrix_res.passed_sih_spec else "FAILED",
             "PASS" if matrix_res.passed_sih_spec else "FAIL"),
            ("Mean Algo FPS", f"{matrix_res.mean_algorithm_fps:.1f}",
             "PASS" if fps_ok else "FAIL"),
            ("Centroid RMSE", rmse_display,
             "PASS" if rmse_ok else ("N/A" if rmse_val is None else "FAIL")),
            ("Target Loss Rate", loss_display, "PASS" if loss_ok else "FAIL"),
            ("Successful Runs", f"{matrix_res.successful_runs}/{matrix_res.total_runs}", "INFO"),
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
        # BenchmarkMatrixResults uses run_results (list of EvaluationRunResult)
        run_results = getattr(matrix_res, "run_results", [])
        if matrix_res.failed_runs > 0 or matrix_res.crashed_runs > 0:
            failed_str = (
                f"{matrix_res.failed_runs} failed, {matrix_res.crashed_runs} crashed "
                f"out of {matrix_res.total_runs} runs.\n"
            )
            from src.evaluation.harness import EvaluationOutcome
            for r in run_results:
                if getattr(r, "outcome", None) not in (
                    None, EvaluationOutcome.SUCCESS
                ):
                    failed_str += (
                        f"  - {getattr(r, 'experiment_id', '?')}: "
                        f"{getattr(r, 'error_message', 'unknown error')}\n"
                    )
            self.txt_fail.setText(failed_str)
        else:
            self.txt_fail.setText("All runs succeeded. No failures detected.")



