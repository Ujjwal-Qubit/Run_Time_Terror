from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, 
    QRadioButton, QButtonGroup, QFileDialog, QLineEdit, QLabel, QMessageBox
)
from src.app.app_controller import AppController

class ControlPanel(QWidget):
    def __init__(self, app_controller: AppController, main_window):
        super().__init__()
        self.app = app_controller
        self.main_window = main_window
        self.layout = QVBoxLayout(self)
        
        # Mode Selection
        mode_group = QGroupBox("Operation Mode")
        mode_layout = QVBoxLayout(mode_group)
        self.mode_btn_group = QButtonGroup()
        
        self.radio_sim = QRadioButton("Simulation (Benchmark 1)")
        self.radio_mp4 = QRadioButton("MP4 Video (Benchmark 2)")
        self.radio_sim.setChecked(True)
        self.mode_btn_group.addButton(self.radio_sim, 0)
        self.mode_btn_group.addButton(self.radio_mp4, 1)
        
        mode_layout.addWidget(self.radio_sim)
        self.scenario_layout = QHBoxLayout()
        self.scenario_path = QLineEdit()
        self.scenario_path.setPlaceholderText("Current Config (or select JSON)")
        self.scenario_btn = QPushButton("Browse")
        self.scenario_btn.clicked.connect(self._browse_scenario)
        self.scenario_layout.addWidget(QLabel("Scenario:"))
        self.scenario_layout.addWidget(self.scenario_path)
        self.scenario_layout.addWidget(self.scenario_btn)
        mode_layout.addLayout(self.scenario_layout)

        mode_layout.addWidget(self.radio_mp4)
        
        self.mp4_layout = QHBoxLayout()
        self.mp4_path = QLineEdit()
        self.mp4_btn = QPushButton("Browse")
        self.mp4_btn.clicked.connect(self._browse_mp4)
        self.mp4_layout.addWidget(QLabel("MP4 File:"))
        self.mp4_layout.addWidget(self.mp4_path)
        self.mp4_layout.addWidget(self.mp4_btn)
        mode_layout.addLayout(self.mp4_layout)
        self.layout.addWidget(mode_group)
        
        self.mode_btn_group.idToggled.connect(self._on_mode_change)
        self._on_mode_change(0, self.radio_sim.isChecked())
        
        # Controls
        ctrl_group = QGroupBox("Playback")
        ctrl_layout = QVBoxLayout(ctrl_group)
        
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_pause = QPushButton("Pause")
        self.btn_resume = QPushButton("Resume")
        self.btn_reset = QPushButton("Reset")
        
        self.btn_start.clicked.connect(self._on_start)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_pause.clicked.connect(self._on_pause)
        self.btn_resume.clicked.connect(self._on_resume)
        self.btn_reset.clicked.connect(self._on_reset)
        
        self.btn_stop.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)
        
        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_stop)
        
        pause_layout = QHBoxLayout()
        pause_layout.addWidget(self.btn_pause)
        pause_layout.addWidget(self.btn_resume)
        ctrl_layout.addLayout(pause_layout)
        
        ctrl_layout.addWidget(self.btn_reset)
        self.layout.addWidget(ctrl_group)
        
        # Benchmark Integration
        bench_group = QGroupBox("Benchmark & Reporting")
        bench_layout = QVBoxLayout(bench_group)
        self.btn_batch = QPushButton("Run Batch Scenarios")
        self.btn_report = QPushButton("Generate Report")
        self.btn_batch.clicked.connect(self._on_batch)
        self.btn_report.clicked.connect(self._on_report)
        bench_layout.addWidget(self.btn_batch)
        bench_layout.addWidget(self.btn_report)
        self.layout.addWidget(bench_group)
        
        self.layout.addStretch()
        
    def _on_mode_change(self, id, checked):
        if not checked: return
        is_mp4 = (id == 1)
        self.mp4_path.setEnabled(is_mp4)
        self.mp4_btn.setEnabled(is_mp4)
        self.scenario_path.setEnabled(not is_mp4)
        self.scenario_btn.setEnabled(not is_mp4)
        if hasattr(self.main_window, 'config_panel'):
            self.main_window.config_panel.setEnabled(not is_mp4)

    def _browse_scenario(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Scenario JSON", "scenarios", "JSON files (*.json);;All files (*.*)")
        if filename:
            self.scenario_path.setText(filename)
            self.app.config_manager.load_from_file(filename)
            if hasattr(self.main_window, 'config_panel'):
                cfg = self.app.config_manager.config
                cp = self.main_window.config_panel
                cp.cam_w.setValue(cfg.camera.width)
                cp.cam_h.setValue(cfg.camera.height)
                cp.cam_fov.setValue(cfg.camera.fov_h_deg)
                cp.cam_fps.setValue(int(cfg.camera.update_rate_hz))
                cp.tgt_size.setValue(cfg.target.size)
                idx = cp.tgt_motion.findText(cfg.motion.motion_type)
                if idx >= 0: cp.tgt_motion.setCurrentIndex(idx)
                idx = cp.dist_atmos.findText(cfg.atmospheric.condition)
                if idx >= 0: cp.dist_atmos.setCurrentIndex(idx)
            
    def _browse_mp4(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select MP4 Video", "", "MP4 files (*.mp4);;All files (*.*)")
        if filename:
            self.mp4_path.setText(filename)
            
    def _update_config(self):
        cfg = self.app.config_manager.config
        if self.radio_mp4.isChecked():
            cfg.simulation.mode = "MP4"
            cfg.simulation.mp4_path = self.mp4_path.text()
            if not cfg.simulation.mp4_path:
                raise ValueError("MP4 path not specified.")
        else:
            s_file = self.scenario_path.text().strip()
            if s_file and os.path.isfile(s_file):
                self.app.config_manager.load_from_file(s_file)
                # Fix A: Refresh cfg reference after loading from file, which creates a new object
                cfg = self.app.config_manager.config
            
            cfg.simulation.mode = "SIMULATION"
            if hasattr(self.main_window, 'config_panel'):
                self.main_window.config_panel.apply_to_config(cfg)
                
    def _on_start(self):
        try:
            self._update_config()
            
            # Fix 4: Interactive simulation should run indefinitely until user stops
            self.app.config_manager.config.simulation.duration_s = None
            
            self.app.initialize()
            
            # Reset
            if self.app.tracking_engine: self.app.tracking_engine.reset()
            if self.app.tracking_state_manager: self.app.tracking_state_manager.reset()
            if self.app.ptz_controller: self.app.ptz_controller.reset()
            
            self.app.start_background_loop()
            
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", str(e))
            
    def _on_stop(self):
        self.app.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)
        
    def _on_pause(self):
        self.app.pause()
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(True)
        
    def _on_resume(self):
        self.app.resume()
        self.btn_pause.setEnabled(True)
        self.btn_resume.setEnabled(False)
        
    def _on_reset(self):
        self.app.reset()
        if hasattr(self.main_window, 'video_widget'):
            self.main_window.video_widget.reset()
        if hasattr(self.main_window, 'telemetry_panel'):
            self.main_window.telemetry_panel.reset()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)

    def _on_batch(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Scenario Directory")
        if directory:
            QMessageBox.information(self, "Batch Run", "Batch scenarios run started (see console).")
            # Usually we'd run this in a thread too to not block GUI
            self.app.benchmark_manager.evaluate_batch_scenarios(directory)
            QMessageBox.information(self, "Batch Run", "Batch scenarios completed.")
            
    def _on_report(self):
        try:
            if self.app.metrics_engine:
                summary = self.app.metrics_engine.finalize()
                json_path = self.app.logging_engine.write_summary(summary)
                md_path = self.app.logging_engine.write_performance_report(summary)
                self.app.logging_engine.finalize()
                QMessageBox.information(
                    self,
                    "Report Generated",
                    f"Performance Reports Generated Successfully:\n\nJSON:\n{json_path}\n\nMarkdown:\n{md_path}"
                )
            else:
                QMessageBox.warning(self, "Report Warning", "Metrics engine not initialized.")
        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Failed to generate report: {str(e)}")
