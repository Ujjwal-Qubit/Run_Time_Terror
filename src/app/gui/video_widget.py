from __future__ import annotations
import cv2
import numpy as np
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap

from src.app.app_controller import AppController
from src.app.visualization_engine import VisualizationEngine

class VideoWidget(QWidget):
    state_updated = Signal(object)  # Emits VisualizationState

    def __init__(self, app_controller: AppController):
        super().__init__()
        self.app = app_controller
        self.viz_engine = VisualizationEngine()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        self.layout.addWidget(self.image_label)
        
        # Polling timer for ~20 FPS (50 ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(50)

    def update_frame(self):
        state = self.app.get_latest_visualization_state()
        if state is None:
            return
            
        # Emit state to other panels
        self.state_updated.emit(state)
        
        # Render overlays
        bgr_img = self.viz_engine.render(state)
        
        # Convert to QPixmap
        h, w, ch = bgr_img.shape
        bytes_per_line = ch * w
        # Convert BGR to RGB
        rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        
        q_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        # Scale to label size
        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
    def stop_timer(self):
        self.timer.stop()

    def reset(self):
        """Clear the video display to synchronize with backend reset."""
        self.image_label.clear()
        self.image_label.setText("Simulation Reset")
