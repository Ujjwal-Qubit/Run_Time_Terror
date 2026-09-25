from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QProgressBar, QTextEdit, QMessageBox, QInputDialog
)
from src.app.app_controller import AppController

class EvaluationPanel(QWidget):
    """
    Dedicated workflow page for the Evaluator.
    Executes standard Benchmark Matrix and AI Scenarios.
    """
    def __init__(self, app_controller: AppController, main_window):
        super().__init__()
        self.app = app_controller
        self.main_window = main_window
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Evaluator Workflow — Benchmark & AI Generation")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #007acc;")
        self.layout.addWidget(title)
        
        # Benchmark Matrix
        matrix_group = QGroupBox("1. Standard Evaluation (Benchmark Matrix)")
        matrix_layout = QVBoxLayout(matrix_group)
        self.lbl_matrix_info = QLabel(
            "Execute the SMOKE subset of standard benchmarks against the active algorithm.\n"
            "Evaluates FPS, Tracking Error (RMSE), and Loss Rate."
        )
        matrix_layout.addWidget(self.lbl_matrix_info)
        
        self.btn_run_matrix = QPushButton("Run Benchmark Matrix")
        self.btn_run_matrix.clicked.connect(self._on_run_matrix)
        matrix_layout.addWidget(self.btn_run_matrix)
        self.layout.addWidget(matrix_group)
        
        # AI Scenarios
        ai_group = QGroupBox("2. AI-Assisted Evaluation (Generative Scenarios)")
        ai_layout = QVBoxLayout(ai_group)
        self.lbl_ai_info = QLabel(
            "Generate novel deterministic test scenarios using Natural Language Prompts."
        )
        ai_layout.addWidget(self.lbl_ai_info)
        
        self.btn_run_ai = QPushButton("Generate & Run AI Scenario")
        self.btn_run_ai.clicked.connect(self._on_run_ai)
        ai_layout.addWidget(self.btn_run_ai)
        self.layout.addWidget(ai_group)
        
        # Output Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background-color: #1e1e1e; font-family: monospace;")
        self.layout.addWidget(QLabel("Evaluation Logs:"))
        self.layout.addWidget(self.console)
        
    def _log(self, text: str):
        self.console.append(text)
        
    def _on_run_matrix(self):
        active_algo = self.app.active_algorithm_name or "baseline_tracker"
        self._log(f"Starting Benchmark Matrix for '{active_algo}'...")
        try:
            from src.evaluation.benchmark_manager import BenchmarkManager
            bm = BenchmarkManager(self.app)
            matrix_res = bm.run_benchmark_matrix(
                subset="SMOKE",
                algorithms=[active_algo],
                max_frames=40,
                output_dir="output/matrix",
            )
            j_p, c_p, m_p = bm.generate_comprehensive_report(
                matrix_res,
                output_dir="output/matrix",
            )
            status_str = "PASSED (PS 26169 Compliant)" if matrix_res.passed_sih_spec else "FAILED CRITERIA"
            self._log(f"Verdict: {status_str} | Mean FPS: {matrix_res.mean_algorithm_fps:.1f}")
            self._log(f"Report exported to: {m_p}")
            
            # Pass results to ResultsPanel and switch
            if hasattr(self.main_window, "page_results"):
                self.main_window.page_results.load_results(matrix_res, m_p)
                self.main_window._switch_page(2, self.main_window.btn_nav_results)
                
            QMessageBox.information(self, "Evaluation Complete", f"Scorecard generated for {active_algo}.")
        except Exception as e:
            self._log(f"ERROR: {str(e)}")
            
    def _on_run_ai(self):
        prompt, accepted = QInputDialog.getMultiLineText(
            self,
            "AI-Assisted Scenario",
            "Describe the scenario to generate and evaluate:",
        )
        prompt = prompt.strip()
        if not accepted or not prompt:
            return

        active_algo = self.app.active_algorithm_name or "baseline_tracker"
        self._log(f"Generating an AI scenario for '{active_algo}'...")
        self.btn_run_ai.setEnabled(False)
        try:
            from src.evaluation.benchmark_manager import BenchmarkManager

            benchmark = BenchmarkManager(self.app)
            success, spec, result, errors = benchmark.run_ai_scenario(
                prompt=prompt,
                algorithm_name=active_algo,
                seed=42,
                max_frames=60,
                output_dir="output/ai_scenarios",
            )
            if not success or spec is None:
                details = "\n".join(f"• {error}" for error in errors)
                self._log(f"AI scenario rejected: {details or 'validation failed'}")
                QMessageBox.warning(
                    self,
                    "Scenario Not Accepted",
                    details or "The generated scenario did not pass validation.",
                )
                return

            self._log(
                f"Validated '{spec.scenario_id}' "
                f"({spec.trajectory_type}, {spec.target_speed:g} px/s)."
            )
            if result is None:
                self._log("Scenario generated; no evaluation result was returned.")
                QMessageBox.information(
                    self, "Scenario Generated", f"Generated {spec.scenario_id}."
                )
                return

            rmse = (
                f"{result.centroid_rmse:.3f} px"
                if result.centroid_rmse is not None
                else "N/A (no reference truth)"
            )
            self._log(
                f"Outcome: {result.outcome.value} | "
                f"Frames: {result.total_frames} | "
                f"FPS: {result.algorithm_fps:.1f} | "
                f"Centroid RMSE: {rmse} | "
                f"Target loss: {result.target_loss_rate:.2f}%"
            )
            if result.md_report_path:
                self._log(f"Report exported to: {result.md_report_path}")
            QMessageBox.information(
                self,
                "AI Scenario Evaluation Complete",
                f"Scenario: {spec.scenario_id}\n"
                f"Outcome: {result.outcome.value}\n"
                f"Algorithm FPS: {result.algorithm_fps:.1f}\n"
                f"Centroid RMSE: {rmse}\n"
                f"Target loss: {result.target_loss_rate:.2f}%",
            )
        except Exception as exc:
            self._log(f"AI scenario evaluation failed: {exc}")
            QMessageBox.critical(self, "AI Scenario Error", str(exc))
        finally:
            self.btn_run_ai.setEnabled(True)
