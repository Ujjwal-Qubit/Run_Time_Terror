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
            ("Frame", "frame_lbl", "0"),
            ("State", "state_lbl", "IDLE"),
            ("Tracking Error (px)", "err_lbl", "0.0"),
            ("Centroid X", "cx_lbl", "0.0"),
            ("Centroid Y", "cy_lbl", "0.0"),
            ("Pan Angle (deg)", "pan_lbl", "0.0"),
            ("Tilt Angle (deg)", "tilt_lbl", "0.0"),
            ("FPS", "fps_lbl", "0.0"),
            ("Latency (ms)", "lat_lbl", "0.0")
        ]
        
        for i, (text, key, val) in enumerate(metrics):
            grid.addWidget(QLabel(f"<b>{text}:</b>"), i // 3, (i % 3) * 2)
            lbl = QLabel(val)
            self.labels[key] = lbl
            grid.addWidget(lbl, i // 3, (i % 3) * 2 + 1)
            
    def update_state(self, state):
        self.labels["frame_lbl"].setText(str(state.frame_number))
        self.labels["state_lbl"].setText(state.tracking_state)
        
        cx = state.estimated_centroid_x
        cy = state.estimated_centroid_y
        
        if cx is not None and cy is not None:
            self.labels["cx_lbl"].setText(f"{cx:.2f}")
            self.labels["cy_lbl"].setText(f"{cy:.2f}")
            
            # Rough tracking error from center (assumes 640x480 for now)
            # Actually, we should get scene width from config
            cfg = self.app.config_manager.config
            center_x = cfg.camera.width / 2.0
            center_y = cfg.camera.height / 2.0
            err = ((cx - center_x)**2 + (cy - center_y)**2)**0.5
            self.labels["err_lbl"].setText(f"{err:.2f}")
        else:
            self.labels["cx_lbl"].setText("-")
            self.labels["cy_lbl"].setText("-")
            self.labels["err_lbl"].setText("-")
            
        self.labels["pan_lbl"].setText(f"{state.pan_angle_deg:.2f}")
        self.labels["tilt_lbl"].setText(f"{state.tilt_angle_deg:.2f}")
        self.labels["fps_lbl"].setText(f"{state.fps:.1f}")
        self.labels["lat_lbl"].setText(f"{state.processing_latency_ms:.1f}")

    def reset(self):
        """Clear telemetry labels to synchronize with backend reset."""
        for key in self.labels:
            self.labels[key].setText("---")
