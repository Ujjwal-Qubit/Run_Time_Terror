from __future__ import annotations
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget

from src.app.app_controller import AppController
from src.app.gui.video_widget import VideoWidget
from src.app.gui.control_panel import ControlPanel
from src.app.gui.telemetry_panel import TelemetryPanel
from src.app.gui.config_panel import ConfigPanel

class MainWindow(QMainWindow):
    def __init__(self, app_controller: AppController):
        super().__init__()
        self.app = app_controller
        self.setWindowTitle("LumiTrack 2D Frontend")
        self.resize(1280, 720)
        
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        self.main_layout = QHBoxLayout(self.main_widget)
        
        # Left Panel (Controls and Config)
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.control_panel = ControlPanel(self.app, self)
        self.left_layout.addWidget(self.control_panel)
        
        self.config_panel = ConfigPanel(self.app)
        self.left_layout.addWidget(self.config_panel)
        
        self.main_layout.addWidget(self.left_panel, stretch=1)
        
        # Center/Right Panel (Video and Telemetry)
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_widget = VideoWidget(self.app)
        self.right_layout.addWidget(self.video_widget, stretch=1)
        
        self.telemetry_panel = TelemetryPanel(self.app)
        # Connect video widget's frame received signal to telemetry panel
        self.video_widget.state_updated.connect(self.telemetry_panel.update_state)
        self.right_layout.addWidget(self.telemetry_panel, stretch=0)
        
        self.main_layout.addWidget(self.right_panel, stretch=3)
        
    def closeEvent(self, event):
        self.video_widget.stop_timer()
        self.app.stop()
        event.accept()
