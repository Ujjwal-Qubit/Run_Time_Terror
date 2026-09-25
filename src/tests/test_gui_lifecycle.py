"""
GUI Lifecycle and Component Integration Tests.
Tests MainWindow, ControlPanel, ConfigPanel, TelemetryPanel, and VisualizationEngine
in offscreen mode to ensure complete UI stability and lifecycle verification.
"""

import os
import math
import pytest
import numpy as np

# Ensure Qt runs offscreen for automated headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, QEvent
from src.app.app_controller import AppController
from src.app.gui.main_window import MainWindow
from src.app.visualization_engine import VisualizationEngine
from src.frame.data_contracts import VisualizationState, ROI, TrackingState


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def cleanup_top_level_widgets(qapp):
    """Close each test's windows/workers before Qt tears down at process exit."""
    yield
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()


def test_telemetry_panel_initial_state(qapp):
    ctrl = AppController()
    win = MainWindow(ctrl)
    tp = win.telemetry_panel

    # Check uninitialized state
    assert tp.labels["state_lbl"].text() == "IDLE"
    assert tp.labels["lock_lbl"].text() == "UNLOCKED"
    assert tp.labels["frame_lbl"].text() == "---"
    assert tp.labels["err_lbl"].text() == "---"
    assert tp.labels["cx_lbl"].text() == "---"
    assert tp.labels["cy_lbl"].text() == "---"
    assert tp.labels["fps_lbl"].text() == "---"
    assert tp.labels["lat_lbl"].text() == "---"


def test_telemetry_panel_state_updates(qapp):
    ctrl = AppController()
    win = MainWindow(ctrl)
    tp = win.telemetry_panel

    dummy_img = np.zeros((480, 640), dtype=np.uint8)
    state = VisualizationState(
        frame_number=42,
        timestamp=1.4,
        pan_angle_deg=1.5,
        tilt_angle_deg=-0.8,
        camera_fov=4.0,
        display_image=dummy_img,
        tracking_state="TRACKING",
        estimated_centroid_x=325.0,
        estimated_centroid_y=245.0,
        fps=30.0,
        processing_latency_ms=12.5,
    )

    tp.update_state(state)
    assert tp.labels["frame_lbl"].text() == "42"
    assert tp.labels["state_lbl"].text() == "TRACKING"
    assert tp.labels["lock_lbl"].text() == "LOCKED"
    assert tp.labels["cx_lbl"].text() == "325.00"
    assert tp.labels["cy_lbl"].text() == "245.00"
    assert tp.labels["pan_lbl"].text() == "1.50"
    assert tp.labels["tilt_lbl"].text() == "-0.80"
    assert tp.labels["fps_lbl"].text() == "30.0"
    assert tp.labels["lat_lbl"].text() == "12.5"

    # Reset
    tp.reset()
    assert tp.labels["state_lbl"].text() == "IDLE"
    assert tp.labels["lock_lbl"].text() == "UNLOCKED"
    assert tp.labels["err_lbl"].text() == "---"


def test_config_panel_sync_and_apply(qapp):
    ctrl = AppController()
    win = MainWindow(ctrl)
    cp = win.config_panel

    # Change some values
    cp.cam_w.setValue(800)
    cp.cam_h.setValue(600)
    cp.cam_fov.setValue(6.0)
    cp.cam_fps.setValue(60)
    cp.tgt_size.setValue(15)
    cp.tgt_speed.setValue(85.0)
    cp.dist_jitter_enable.setChecked(True)
    cp.dist_jitter_amp.setValue(3.5)
    cp.aiml_classifier_enable.setChecked(True)
    cp.aiml_model_dir.setText("models/test_classifier/v2")
    cp.aiml_temporal_enable.setChecked(True)
    cp.aiml_temporal_model_dir.setText("models/test_temporal/v2")

    cfg = ctrl.config_manager.config
    cp.apply_to_config(cfg)

    assert cfg.camera.width == 800
    assert cfg.camera.height == 600
    assert cfg.camera.fov_h_deg == 6.0
    assert cfg.camera.update_rate_hz == 60.0
    assert cfg.target.size == 15
    assert cfg.target.speed == 85.0
    assert cfg.jitter.enabled is True
    assert cfg.jitter.max_px_per_frame == 3.5
    assert cfg.aiml.candidate_classifier_enabled is True
    assert cfg.aiml.candidate_model_dir == "models/test_classifier/v2"
    assert cfg.aiml.temporal_predictor_enabled is True
    assert cfg.aiml.temporal_model_dir == "models/test_temporal/v2"


def test_control_panel_lifecycle(qapp):
    ctrl = AppController()
    win = MainWindow(ctrl)
    cp = win.control_panel

    # Initial state
    assert cp.btn_start.isEnabled() is True
    assert cp.btn_stop.isEnabled() is False
    assert cp.btn_pause.isEnabled() is False
    assert cp.btn_resume.isEnabled() is False

    # Start simulation
    cp._on_start()
    assert cp.btn_start.isEnabled() is False
    assert cp.btn_stop.isEnabled() is True
    assert cp.btn_pause.isEnabled() is True
    assert cp.btn_resume.isEnabled() is False

    # Pause
    cp._on_pause()
    assert cp.btn_pause.isEnabled() is False
    assert cp.btn_resume.isEnabled() is True

    # Resume
    cp._on_resume()
    assert cp.btn_pause.isEnabled() is True
    assert cp.btn_resume.isEnabled() is False

    # Stop
    cp._on_stop()
    assert cp.btn_start.isEnabled() is True
    assert cp.btn_stop.isEnabled() is False
    assert cp.btn_pause.isEnabled() is False
    assert cp.btn_resume.isEnabled() is False

    # Reset
    cp._on_reset()
    assert cp.btn_start.isEnabled() is True
    assert win.telemetry_panel.labels["state_lbl"].text() == "IDLE"


def test_visualization_engine_hud():
    engine = VisualizationEngine()
    dummy_img = np.zeros((480, 640), dtype=np.uint8)
    state = VisualizationState(
        frame_number=10,
        timestamp=0.33,
        pan_angle_deg=2.45,
        tilt_angle_deg=-1.12,
        camera_fov=4.0,
        display_image=dummy_img,
        tracking_state="TRACKING",
        estimated_centroid_x=320.0,
        estimated_centroid_y=240.0,
        ground_truth_x=321.0,
        ground_truth_y=239.0,
        roi=ROI(x=300, y=220, width=40, height=40),
        fps=29.8,
        processing_latency_ms=15.2,
    )

    rendered = engine.render(state)
    assert rendered.shape == (480, 640, 3)
    assert rendered.dtype == np.uint8
    # Assert rendered has non-zero pixels (HUD and crosshairs were drawn)
    assert np.any(rendered > 0)


def test_view_3d_widget_lifecycle(qapp):
    from src.app.gui.view_3d import View3DWidget

    w3d = View3DWidget()
    w3d.resize(600, 400)
    assert len(w3d._trajectory_history) == 0

    dummy_img = np.zeros((480, 640), dtype=np.uint8)
    state = VisualizationState(
        frame_number=1,
        timestamp=0.033,
        pan_angle_deg=3.5,
        tilt_angle_deg=-1.2,
        camera_fov=4.0,
        display_image=dummy_img,
        tracking_state="TRACKING",
        ground_truth_x=325.0,
        ground_truth_y=242.0,
    )

    w3d.update_state(state)
    assert len(w3d._trajectory_history) == 1
    pt = w3d._project_point(w3d._trajectory_history[0], 600, 400)
    assert pt is not None
    assert 0 <= pt.x() <= 600
    assert 0 <= pt.y() <= 400

    # Test reset view
    w3d.reset_view()
    assert len(w3d._trajectory_history) == 0
    assert w3d._cam_azimuth_deg == 35.0


def test_video_widget_frame_scale_keeps_full_frame_visible(qapp):
    from PySide6.QtGui import QPixmap
    from src.app.gui.video_widget import VideoWidget

    widget = VideoWidget(AppController())
    widget.resize(640, 480)
    widget._source_pixmap = QPixmap(800, 600)
    widget.show()
    qapp.processEvents()

    widget.frame_scale_slider.setValue(60)
    qapp.processEvents()
    displayed = widget.image_label.pixmap()
    area = widget.image_label.contentsRect()

    assert displayed is not None
    assert displayed.width() <= area.width()
    assert displayed.height() <= area.height()
    assert widget.frame_scale_label.text() == "60%"
    widget.stop_timer()


def test_3d_target_uses_tracker_estimate_and_frame_geometry(qapp):
    from src.app.gui.view_3d import View3DWidget

    widget = View3DWidget()
    state = VisualizationState(
        frame_number=1,
        timestamp=0.033,
        pan_angle_deg=0.0,
        tilt_angle_deg=0.0,
        camera_fov=8.0,
        camera_fov_v=6.0,
        camera_width=800,
        camera_height=600,
        display_image=np.zeros((600, 800), dtype=np.uint8),
        tracking_state="TRACKING",
        estimated_centroid_x=500.0,
        estimated_centroid_y=300.0,
        ground_truth_x=400.0,
        ground_truth_y=300.0,
    )

    widget.update_state(state)
    target = widget._trajectory_history[-1]
    expected_pan = math.radians((500.0 - 400.0) * 8.0 / 800.0)
    assert target[0] / target[2] == pytest.approx(math.tan(expected_pan), abs=1e-5)

    # An extreme tracked direction remains inside the overview's 3D viewport.
    state.frame_number = 2
    state.pan_angle_deg = 150.0
    state.tilt_angle_deg = 60.0
    state.estimated_centroid_x = 0.0
    state.estimated_centroid_y = 0.0
    widget.update_state(state)
    projected = widget._project_point(widget._trajectory_history[-1], 600, 400)
    assert projected is not None
    assert 0 <= projected.x() <= 600
    assert 0 <= projected.y() <= 400

