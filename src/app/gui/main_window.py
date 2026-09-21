from __future__ import annotations
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QSplitter,
    QStackedWidget, QPushButton, QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont

from src.app.app_controller import AppController
from src.app.gui.video_widget import VideoWidget
from src.app.gui.control_panel import ControlPanel
from src.app.gui.telemetry_panel import TelemetryPanel
from src.app.gui.config_panel import ConfigPanel
from src.app.gui.view_3d import View3DWidget
from src.app.gui.evaluation_panel import EvaluationPanel
from src.app.gui.results_panel import ResultsPanel

# Minimal Dark Theme QSS
DARK_THEME_QSS = """
QMainWindow {
    background-color: #1e1e1e;
    color: #e0e0e0;
}
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Inter, Roboto, sans-serif;
}
QFrame#Sidebar {
    background-color: #252526;
    border-right: 1px solid #333333;
}
QPushButton.SidebarButton {
    background-color: transparent;
    color: #cccccc;
    text-align: left;
    padding: 10px 20px;
    border: none;
    font-size: 14px;
    font-weight: 500;
}
QPushButton.SidebarButton:hover {
    background-color: #2a2d2e;
    color: #ffffff;
}
QPushButton.SidebarButton:checked {
    background-color: #37373d;
    color: #ffffff;
    border-left: 3px solid #007acc;
}
QGroupBox {
    border: 1px solid #444444;
    border-radius: 4px;
    margin-top: 1ex;
    font-weight: bold;
    color: #007acc;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
}
QTabWidget::pane {
    border: 1px solid #444444;
    background-color: #252526;
}
QTabBar::tab {
    background-color: #2d2d30;
    color: #cccccc;
    padding: 8px 12px;
    border: 1px solid #444444;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #ffffff;
    border-bottom: 1px solid #1e1e1e;
}
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    padding: 4px;
    border-radius: 2px;
}
QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: none;
    padding: 6px 12px;
    border-radius: 2px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #1177bb;
}
QPushButton:disabled {
    background-color: #4d4d4d;
    color: #888888;
}
"""

class MainWindow(QMainWindow):
    def __init__(self, app_controller: AppController):
        super().__init__()
        self.app = app_controller
        self.setWindowTitle("LumiTrack — Virtual Camera Tracking & Algorithm Evaluation Platform")
        self.resize(1440, 900)
        
        self.setStyleSheet(DARK_THEME_QSS)
        
        # Central Layout: Sidebar + Stacked Widget
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self._build_sidebar()
        self._build_stacked_widget()
        
    def _build_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 0)
        sidebar_layout.setSpacing(5)
        
        # Logo / Title
        title = QLabel(" LumiTrack")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #007acc; padding-bottom: 20px;")
        sidebar_layout.addWidget(title)
        
        # Navigation Buttons
        self.btn_nav_dev = self._create_nav_button("🔧 Developer Workflow")
        self.btn_nav_eval = self._create_nav_button("📊 Evaluator Workflow")
        self.btn_nav_results = self._create_nav_button("📈 Results & Analysis")
        
        self.btn_nav_dev.setChecked(True)
        
        sidebar_layout.addWidget(self.btn_nav_dev)
        sidebar_layout.addWidget(self.btn_nav_eval)
        sidebar_layout.addWidget(self.btn_nav_results)
        sidebar_layout.addStretch()
        
        self.main_layout.addWidget(self.sidebar)
        
        # Connections
        self.btn_nav_dev.clicked.connect(lambda: self._switch_page(0, self.btn_nav_dev))
        self.btn_nav_eval.clicked.connect(lambda: self._switch_page(1, self.btn_nav_eval))
        self.btn_nav_results.clicked.connect(lambda: self._switch_page(2, self.btn_nav_results))
        
    def _create_nav_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "SidebarButton")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        return btn
        
    def _switch_page(self, index: int, active_btn: QPushButton):
        self.stacked_widget.setCurrentIndex(index)
        for btn in [self.btn_nav_dev, self.btn_nav_eval, self.btn_nav_results]:
            btn.setChecked(btn == active_btn)

    def _build_stacked_widget(self):
        self.stacked_widget = QStackedWidget()
        
        # Page 0: Developer Workflow (Interactive Simulation)
        self.page_dev = QWidget()
        self._build_developer_page()
        self.stacked_widget.addWidget(self.page_dev)
        
        # Page 1: Evaluator Workflow (Benchmark Matrix)
        self.page_eval = EvaluationPanel(self.app, self)
        self.stacked_widget.addWidget(self.page_eval)
        
        # Page 2: Results & Analysis
        self.page_results = ResultsPanel(self.app, self)
        self.stacked_widget.addWidget(self.page_results)
        
        self.main_layout.addWidget(self.stacked_widget)
        
    def _build_developer_page(self):
        dev_layout = QHBoxLayout(self.page_dev)
        dev_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left Panel (Controls and Config)
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.control_panel = ControlPanel(self.app, self)
        self.left_layout.addWidget(self.control_panel)
        
        self.config_panel = ConfigPanel(self.app)
        self.config_panel.config_changed.connect(self._on_config_changed)
        self.left_layout.addWidget(self.config_panel)
        
        dev_layout.addWidget(self.left_panel, stretch=1)
        
        # Right Panel (Visualization Tabs and Telemetry)
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        # View Tabs: 2D View, 3D Scene
        self.view_tabs = QTabWidget()
        self.video_widget = VideoWidget(self.app)
        self.view_tabs.addTab(self.video_widget, "2D Camera View")
        
        self.view_3d_widget = View3DWidget()
        self.view_tabs.addTab(self.view_3d_widget, "3D Geometric Scene")
        
        self.right_layout.addWidget(self.view_tabs, stretch=1)
        
        # Telemetry Panel
        self.telemetry_panel = TelemetryPanel(self.app)
        self.video_widget.state_updated.connect(self.telemetry_panel.update_state)
        self.video_widget.state_updated.connect(self.view_3d_widget.update_state)
        self.right_layout.addWidget(self.telemetry_panel, stretch=0)
        
        dev_layout.addWidget(self.right_panel, stretch=3)

    def _on_config_changed(self):
        # Only apply live tuning if running in Simulation mode
        if self.app.is_running and self.app.config_manager.config.simulation.mode == "SIMULATION":
            self.config_panel.apply_to_config(self.app.config_manager.config)
            # Push changes to TargetManager and DisturbanceEngine for live tuning
            if self.app.target_manager:
                self.app.target_manager._target_cfg = self.app.config_manager.config.target
                self.app.target_manager._motion_cfg = self.app.config_manager.config.motion
            if self.app.disturbance_engine:
                self.app.disturbance_engine._atmos_cfg = self.app.config_manager.config.atmospheric
                self.app.disturbance_engine._noise_cfg = self.app.config_manager.config.noise
                self.app.disturbance_engine._jitter_cfg = self.app.config_manager.config.jitter
                self.app.disturbance_engine._platform_cfg = self.app.config_manager.config.platform_motion

    def closeEvent(self, event):
        self.video_widget.stop_timer()
        self.app.stop()
        event.accept()
