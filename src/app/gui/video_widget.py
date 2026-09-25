from __future__ import annotations
import cv2
import numpy as np
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSlider
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
        self.layout.setSpacing(4)

        # The displayed image is always fitted inside the available viewport;
        # this slider lets the operator reduce its on-screen footprint without
        # cropping the sensor frame or changing acquisition resolution.
        toolbar = QHBoxLayout()
        self.title_label = QLabel("2D Optical Sensor Focal Plane (HUD Viewport)")
        self.title_label.setStyleSheet("color: #19bfff; font-weight: 600; padding-left: 8px;")
        toolbar.addWidget(self.title_label)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel("Frame size"))
        self.frame_scale_slider = QSlider(Qt.Horizontal)
        self.frame_scale_slider.setRange(40, 100)
        self.frame_scale_slider.setValue(100)
        self.frame_scale_slider.setFixedWidth(140)
        self.frame_scale_slider.setToolTip("Scale the displayed frame within the viewport; the complete frame always remains visible.")
        self.frame_scale_label = QLabel("100%")
        self.frame_scale_label.setMinimumWidth(38)
        toolbar.addWidget(self.frame_scale_slider)
        toolbar.addWidget(self.frame_scale_label)
        self.layout.addLayout(toolbar)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        self.image_label.setMinimumSize(1, 1)
        self.layout.addWidget(self.image_label)
        self._source_pixmap = QPixmap()
        self.frame_scale_slider.valueChanged.connect(self._on_frame_scale_changed)
        
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
        self._source_pixmap = QPixmap.fromImage(q_img)
        self._fit_frame_to_viewport()

    def _on_frame_scale_changed(self, value: int) -> None:
        self.frame_scale_label.setText(f"{value}%")
        self._fit_frame_to_viewport()

    def _fit_frame_to_viewport(self) -> None:
        """Fit the entire source frame into the image area, preserving aspect ratio."""
        if self._source_pixmap.isNull():
            return

        area = self.image_label.contentsRect()
        if area.width() <= 0 or area.height() <= 0:
            return

        fit_scale = min(
            area.width() / self._source_pixmap.width(),
            area.height() / self._source_pixmap.height(),
        )
        display_scale = fit_scale * self.frame_scale_slider.value() / 100.0
        target_size = self._source_pixmap.size() * display_scale
        self.image_label.setPixmap(
            self._source_pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_frame_to_viewport()

        
    def stop_timer(self):
        self.timer.stop()

    def reset(self):
        """Clear the video display to synchronize with backend reset."""
        self.viz_engine.reset()
        self._source_pixmap = QPixmap()
        self.image_label.clear()
        self.image_label.setText("Simulation Reset")
