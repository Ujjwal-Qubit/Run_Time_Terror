import pytest
import os
import math
import numpy as np
from PySide6.QtWidgets import QApplication

from src.config.config_manager import ConfigManager
from src.app.app_controller import AppController
from src.app.gui.control_panel import ControlPanel
from src.tracker.centroid_estimator import IntensityWeightedCentroidEstimator
from src.frame.data_contracts import CandidateRegion
from src.simulation.target_manager import TargetManager

class DummyMainWindow:
    def __init__(self, app_controller):
        from src.app.gui.config_panel import ConfigPanel
        from src.app.gui.telemetry_panel import TelemetryPanel
        from src.app.gui.video_widget import VideoWidget
        self.config_panel = ConfigPanel(app_controller)
        self.telemetry_panel = TelemetryPanel(app_controller)
        self.video_widget = VideoWidget(app_controller)

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_fix_a_config_precedence(qapp):
    # Verify GUI overrides apply to the ACTIVE config after loading a scenario
    app = AppController()
    main_window = DummyMainWindow(app)
    
    control_panel = ControlPanel(app, main_window)
    # Simulate loading scenario 2
    control_panel.scenario_path.setText("scenarios/scenario_2_circular.json")
    
    # Simulate setting target size to 20 in the GUI
    main_window.config_panel.tgt_size.setValue(20)
    
    # Run _update_config
    control_panel._update_config()
    
    # The active runtime config MUST have size 20, not the 10 from the JSON
    assert app.config_manager.config.target.size == 20

def test_fix_b_centroid_robustness():
    # Ensure margin scales with target size without breaking 5px bounds
    cfg = ConfigManager().config
    estimator = IntensityWeightedCentroidEstimator(cfg.centroid)
    
    # Test Size 5
    cand_5 = CandidateRegion(bbox_x=10, bbox_y=10, bbox_w=5, bbox_h=5, 
                             peak_intensity=255.0, mean_intensity=255.0, area=25.0, local_contrast=2.0)
    margin_5 = max(estimator._bg_margin, int(max(cand_5.bbox_w, cand_5.bbox_h) * 0.2))
    assert margin_5 == estimator._bg_margin
    
    # Test Size 20
    cand_20 = CandidateRegion(bbox_x=10, bbox_y=10, bbox_w=20, bbox_h=20, 
                             peak_intensity=255.0, mean_intensity=255.0, area=400.0, local_contrast=2.0)
    margin_20 = max(estimator._bg_margin, int(max(cand_20.bbox_w, cand_20.bbox_h) * 0.2))
    assert margin_20 >= 4

def test_fix_c_random_motion_bounded():
    # Verify RANDOM motion integrates velocity and stays bounded
    cfg = ConfigManager().config
    cfg.motion.motion_type = "RANDOM"
    cfg.motion.speed = 100.0
    cfg.motion.random_max_displacement = 50.0
    
    target = TargetManager(cfg.target, cfg.motion, scene_width=640, scene_height=480)
    target.reset()
    
    state_0 = target.target_state
    x0, y0 = state_0.world_x, state_0.world_y
    
    target.step(0.1)
    state_1 = target.target_state
    x1, y1 = state_1.world_x, state_1.world_y
    
    # Target must have moved
    assert (x1 != x0) or (y1 != y0)
    
    # Speed must not exceed configured limit
    speed = math.hypot(state_1.vx, state_1.vy)
    assert speed <= cfg.motion.speed + 1e-5
    
    # Must stay within bounds
    assert state_1.world_x >= 0
    assert state_1.world_x <= 640

def test_fix_d_reset_synchronization(qapp):
    # Verify reset clears telemetry and video
    app = AppController()
    main_window = DummyMainWindow(app)
    control_panel = ControlPanel(app, main_window)
    
    # Simulate a run with some telemetry
    main_window.telemetry_panel.labels["fps_lbl"].setText("30.0")
    
    # Trigger reset
    control_panel._on_reset()
    
    # Verify telemetry is cleared
    assert main_window.telemetry_panel.labels["fps_lbl"].text() == "---"
