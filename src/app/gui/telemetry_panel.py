from __future__ import annotations
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGridLayout, QGroupBox
from PySide6.QtCore import Qt
from src.app.app_controller import AppController

class TelemetryPanel(QWidget):
    def __init__(self, app_controller: AppController):
        super().__init__()
        self.app = app_controller
        
        self.layout = QVBoxLayout(self)
        
        group = QGroupBox("Real-time Telemetry Dashboard")
        self.layout.addWidget(group)
        
        grid = QGridLayout(group)
        
        self.labels = {}
        
        metrics = [
            ("Algorithm", "algo_lbl", "baseline_tracker"),
            ("Frame", "frame_lbl", "---"),
            ("State", "state_lbl", "IDLE"),
            ("Lock Status", "lock_lbl", "UNLOCKED"),
            ("Tracking Error (px)", "err_lbl", "---"),
            ("Centroid X", "cx_lbl", "---"),
            ("Centroid Y", "cy_lbl", "---"),
            ("Pan Angle (deg)", "pan_lbl", "0.00"),
            ("Tilt Angle (deg)", "tilt_lbl", "0.00"),
            ("FPS", "fps_lbl", "---"),
            ("Latency (ms)", "lat_lbl", "---")
        ]
        
        for i, (text, key, val) in enumerate(metrics):
            grid.addWidget(QLabel(f"<b>{text}:</b>"), i // 2, (i % 2) * 2)
            lbl = QLabel(val)
            if key == "lock_lbl":
                lbl.setStyleSheet("color: #cc0000; font-weight: bold;")
            elif key == "state_lbl":
                lbl.setStyleSheet("font-weight: bold;")
            elif key == "algo_lbl":
                lbl.setStyleSheet("color: #0055aa; font-weight: bold;")
            self.labels[key] = lbl
            grid.addWidget(lbl, i // 2, (i % 2) * 2 + 1)
            
    def set_algorithm(self, name: str):
        if "algo_lbl" in self.labels:
            self.labels["algo_lbl"].setText(name or "---")

    def update_state(self, state):
        if hasattr(state, "algorithm_name") and state.algorithm_name:
            self.labels["algo_lbl"].setText(state.algorithm_name)
        elif self.app.active_algorithm_name:
            self.labels["algo_lbl"].setText(self.app.active_algorithm_name)

        self.labels["frame_lbl"].setText(str(state.frame_number))
        self.labels["state_lbl"].setText(state.tracking_state)
        
        # Lock status indicator
        if state.tracking_state == "TRACKING":
            self.labels["lock_lbl"].setText("LOCKED")
            self.labels["lock_lbl"].setStyleSheet("color: #00aa00; font-weight: bold;")
            self.labels["state_lbl"].setStyleSheet("color: #00aa00; font-weight: bold;")
        elif state.tracking_state in ("ACQUIRING", "REACQUIRING"):
            self.labels["lock_lbl"].setText("ACQUIRING")
            self.labels["lock_lbl"].setStyleSheet("color: #d4aa00; font-weight: bold;")
            self.labels["state_lbl"].setStyleSheet("color: #d4aa00; font-weight: bold;")
        else:
            self.labels["lock_lbl"].setText("UNLOCKED")
            self.labels["lock_lbl"].setStyleSheet("color: #cc0000; font-weight: bold;")
            self.labels["state_lbl"].setStyleSheet("color: #cc0000; font-weight: bold;")
        
        cx = state.estimated_centroid_x
        cy = state.estimated_centroid_y
        
        if cx is not None and cy is not None:
            self.labels["cx_lbl"].setText(f"{cx:.2f}")
            self.labels["cy_lbl"].setText(f"{cy:.2f}")
            
            cfg = self.app.config_manager.config
            center_x = cfg.camera.width / 2.0
            center_y = cfg.camera.height / 2.0
            err = ((cx - center_x)**2 + (cy - center_y)**2)**0.5
            self.labels["err_lbl"].setText(f"{err:.2f}")
        else:
            self.labels["cx_lbl"].setText("---")
            self.labels["cy_lbl"].setText("---")
            self.labels["err_lbl"].setText("---")
            
        self.labels["pan_lbl"].setText(f"{state.pan_angle_deg:.2f}")
        self.labels["tilt_lbl"].setText(f"{state.tilt_angle_deg:.2f}")
        self.labels["fps_lbl"].setText(f"{state.fps:.1f}")
        self.labels["lat_lbl"].setText(f"{state.processing_latency_ms:.1f}")

    def reset(self):
        """Clear telemetry labels to synchronize with backend reset."""
        for key in self.labels:
            if key == "algo_lbl":
                self.labels[key].setText(self.app.active_algorithm_name or "---")
            elif key == "state_lbl":
                self.labels[key].setText("IDLE")
                self.labels[key].setStyleSheet("font-weight: bold;")
            elif key == "lock_lbl":
                self.labels[key].setText("UNLOCKED")
                self.labels[key].setStyleSheet("color: #cc0000; font-weight: bold;")
            elif key in ("pan_lbl", "tilt_lbl"):
                self.labels[key].setText("0.00")
            else:
                self.labels[key].setText("---")

