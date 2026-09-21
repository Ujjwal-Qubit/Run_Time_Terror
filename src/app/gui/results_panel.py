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
        
    def load_results(self, matrix_res, report_path: str):
        self.current_report_path = report_path
        
        # Populate table
        self.table.setRowCount(0)
        
        metrics = [
            ("Algorithm", matrix_res.batch_id, "INFO"),
            ("Verdict", "PASSED" if matrix_res.passed_sih_spec else "FAILED", "PASS" if matrix_res.passed_sih_spec else "FAIL"),
            ("Mean FPS", f"{matrix_res.mean_algorithm_fps:.1f}", "PASS" if matrix_res.passed_fps_spec else "FAIL"),
            ("Centroid RMSE", f"{matrix_res.mean_rmse_centroid:.3f} px" if matrix_res.mean_rmse_centroid is not None else "N/A", "PASS" if matrix_res.passed_tracking_error_spec else "FAIL"),
            ("Target Loss Rate", f"{matrix_res.mean_target_loss_rate_pct:.1f}%", "PASS" if matrix_res.passed_loss_rate_spec else "FAIL"),
        ]
        
        for i, (metric, value, status) in enumerate(metrics):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(metric))
            self.table.setItem(i, 1, QTableWidgetItem(value))
            
            status_item = QTableWidgetItem(status)
            if status == "PASS":
                status_item.setForeground(Qt.green)
            elif status == "FAIL":
                status_item.setForeground(Qt.red)
            self.table.setItem(i, 2, status_item)
            
        # Display failure analysis if available
        if matrix_res.failed_runs > 0:
            failed_str = f"{matrix_res.failed_runs} runs failed out of {matrix_res.total_runs}.\n"
            for item in matrix_res.run_items:
                if not item.success:
                    failed_str += f"- {item.item_id}: {item.error_message}\n"
            self.txt_fail.setText(failed_str)
        else:
            self.txt_fail.setText("All runs succeeded successfully. No failures detected.")

