"""
SANKET — Phase 1 Frontend POC Test Suite

Verifies:
  1. Frontend static bundle exists and has zero CDN/external network dependencies.
  2. QWebChannel bridge initialization.
  3. Telemetry serialization and schema contract validation.
  4. Ground-Truth Firewall enforcement at the IPC boundary.
  5. Sensor frame JPEG compression and Base64 transport serialization.
  6. Simulation control commands (RUN, PAUSE, RESUME, STOP, STEP, RESET).
  7. Algorithm and scenario selection slots.
  8. Invalid command handling and failure isolation.
  9. Dual-GUI CLI arguments (--legacy-gui and default modern GUI).
 10. WebWindow and Legacy MainWindow instantiation in offscreen mode.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import numpy as np
import pytest
import cv2

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

from src.app.app_controller import AppController
from src.app.gui.web_bridge import SanketBridge
from src.app.gui.web_window import SanketWebWindow, resolve_frontend_dist
from src.app.gui.main_window import MainWindow
from src.frame.data_contracts import VisualizationState, ROI, TrackingState
from src.main import parse_args


@pytest.fixture(scope="module")
def qapp():
    """Ensure a QApplication instance exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    yield app


@pytest.fixture
def app_controller():
    """Create and initialize a standard AppController instance."""
    ctrl = AppController()
    ctrl.initialize()
    yield ctrl
    ctrl.stop()
    ctrl.reset()


class TestPhase1FrontendPOC:
    """Phase 1 Verification Tests."""

    def test_frontend_bundle_built_and_offline(self):
        """1. Verify frontend dist exists, contains no external CDN references, and has CSP."""
        dist_path = resolve_frontend_dist()
        assert os.path.isfile(dist_path), f"Frontend dist bundle not found at {dist_path}"

        with open(dist_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify no external CDN/HTTP script or stylesheet references
        external_urls = re.findall(r'(?:href|src)=["\'](https?://[^"\']+)["\']', content)
        assert len(external_urls) == 0, f"Found external URL references in dist/index.html: {external_urls}"

        # Verify Content-Security-Policy is present
        assert "Content-Security-Policy" in content, "Missing Content-Security-Policy meta tag in index.html"

    def test_bridge_initialization(self, qapp, app_controller):
        """2. Verify SanketBridge initializes with correct signals and timer."""
        bridge = SanketBridge(app_controller)
        assert bridge is not None
        assert bridge._timer.isActive()
        assert bridge._timer.interval() == 40  # 25 Hz
        bridge._timer.stop()

    def test_telemetry_serialization_and_firewall(self, qapp, app_controller):
        """3 & 4. Verify telemetry serialization and STRICT Ground-Truth Firewall enforcement."""
        bridge = SanketBridge(app_controller)
        bridge._timer.stop()

        received_telemetry = []
        bridge.telemetryUpdated.connect(lambda s: received_telemetry.append(json.loads(s)))

        # Create a mock VisualizationState containing potential ground-truth coordinates
        mock_state = VisualizationState(
            frame_number=42,
            timestamp=1.4,
            pan_angle_deg=1.234,
            tilt_angle_deg=-0.567,
            camera_fov=4.0,
            display_image=np.zeros((480, 640), dtype=np.uint8),
            camera_fov_v=3.0,
            camera_width=640,
            camera_height=480,
            estimated_centroid_x=325.4,
            estimated_centroid_y=241.8,
            tracking_state="TRACKING",
            roi=ROI(x=310, y=230, width=30, height=30),
            processing_latency_ms=12.5,
            fps=80.0,
            ground_truth_x=999.9,  # SENSITIVE: Ground truth world/ideal coordinate
            ground_truth_y=888.8,  # SENSITIVE: Ground truth world/ideal coordinate
        )

        app_controller.visualization_manager.push_state(mock_state)
        bridge._on_poll_tick()

        assert len(received_telemetry) == 1
        telem = received_telemetry[0]

        # Verify public telemetry fields
        assert telem["frameNumber"] == 42
        assert telem["trackingState"] == "TRACKING"
        assert telem["centroid"]["x"] == pytest.approx(325.4)
        assert telem["centroid"]["y"] == pytest.approx(241.8)
        assert telem["panAngleDeg"] == pytest.approx(1.234)
        assert telem["tiltAngleDeg"] == pytest.approx(-0.567)
        assert telem["processingLatencyMs"] == pytest.approx(12.5)

        # STRICT GROUND-TRUTH FIREWALL ASSERTIONS:
        assert "ground_truth_x" not in telem, "Firewall Violation: ground_truth_x leaked in telemetry!"
        assert "ground_truth_y" not in telem, "Firewall Violation: ground_truth_y leaked in telemetry!"
        assert "groundTruthX" not in telem, "Firewall Violation: groundTruthX leaked in telemetry!"
        assert "groundTruthY" not in telem, "Firewall Violation: groundTruthY leaked in telemetry!"
        assert telem["trackingErrorPx"] is None, "Firewall Violation: live tracking error must be None!"

    def test_system_status_serialization(self, qapp, app_controller):
        """5. Verify SystemStatus serialization contract."""
        bridge = SanketBridge(app_controller)
        bridge._timer.stop()

        received_status = []
        bridge.systemStatusChanged.connect(lambda s: received_status.append(json.loads(s)))

        bridge._emit_system_status()
        assert len(received_status) == 1
        st = received_status[0]

        assert st["mode"] in ("SIMULATION", "MP4")
        assert isinstance(st["isRunning"], bool)
        assert isinstance(st["isPaused"], bool)
        assert "baseline_tracker" in st["availableAlgorithms"]
        assert len(st["availableScenarios"]) > 0
        assert isinstance(st["ptzEnabled"], bool)

    def test_sensor_frame_serialization(self, qapp, app_controller):
        """6. Verify sensor frame JPEG encoding and Base64 payload reconstruction."""
        bridge = SanketBridge(app_controller)
        bridge._timer.stop()

        received_frames = []
        bridge.sensorFrameReady.connect(lambda s: received_frames.append(json.loads(s)))

        # Create a test frame with synthetic bright spot
        test_img = np.zeros((480, 640), dtype=np.uint8)
        cv2.circle(test_img, (320, 240), 10, 255, -1)

        mock_state = VisualizationState(
            frame_number=1,
            timestamp=0.033,
            pan_angle_deg=0.0,
            tilt_angle_deg=0.0,
            camera_fov=4.0,
            display_image=test_img,
            camera_fov_v=3.0,
            camera_width=640,
            camera_height=480,
            tracking_state="SEARCHING",
        )

        app_controller.visualization_manager.push_state(mock_state)
        bridge._on_poll_tick()

        assert len(received_frames) == 1
        frame_payload = received_frames[0]

        assert frame_payload["frameNumber"] == 1
        assert frame_payload["width"] == 640
        assert frame_payload["height"] == 480
        assert frame_payload["format"] == "jpeg"
        assert frame_payload["data"].startswith("data:image/jpeg;base64,")

        # Decode base64 data and verify reconstruction
        b64_data = frame_payload["data"].split(",")[1]
        raw_bytes = base64.b64decode(b64_data)
        decoded_img = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)

        assert decoded_img is not None
        assert decoded_img.shape == (480, 640)
        # Spot in the center should be bright
        assert decoded_img[240, 320] > 200

    def test_command_dispatch_lifecycle(self, qapp, app_controller):
        """7. Verify RUN, PAUSE, RESUME, STEP, STOP, RESET lifecycle via bridge slots."""
        bridge = SanketBridge(app_controller)
        bridge._timer.stop()

        # Step once (processes frame 0)
        bridge.stepSimulation()
        assert bridge._last_frame_number == 0

        # Step second time (processes frame 1)
        bridge.stepSimulation()
        assert bridge._last_frame_number == 1
        assert app_controller._frame_count == 1

        # Run
        bridge.runSimulation()
        assert app_controller._running is True

        # Pause
        bridge.pauseSimulation()
        assert app_controller._paused is True

        # Resume
        bridge.resumeSimulation()
        assert app_controller._paused is False

        # Stop
        bridge.stopSimulation()
        assert app_controller._running is False

        # Reset
        bridge.resetSimulation()
        assert app_controller._frame_count == 0
        assert app_controller._running is False

    def test_algorithm_and_scenario_selection(self, qapp, app_controller):
        """8. Verify selectAlgorithm and selectScenario bridge slots."""
        bridge = SanketBridge(app_controller)
        bridge._timer.stop()

        # Select algorithm
        bridge.selectAlgorithm("baseline_tracker")
        assert app_controller.active_algorithm_name == "baseline_tracker"

        # Select invalid algorithm (should not crash)
        bridge.selectAlgorithm("invalid_algorithm_name_xyz")
        assert app_controller.active_algorithm_name == "baseline_tracker"

        # Select scenario
        scenarios = app_controller.scenario_manager.list_scenarios()
        if scenarios:
            bridge.selectScenario(scenarios[0])
            assert getattr(app_controller.config_manager, "scenario_name", None) == scenarios[0]

        # PTZ Toggle
        bridge.setPtzEnabled(False)
        assert app_controller._ptz_enabled is False
        bridge.setPtzEnabled(True)
        assert app_controller._ptz_enabled is True

    def test_dual_gui_cli_seam(self):
        """9. Verify command-line argument parsing for default vs legacy GUI."""
        args_default = parse_args([])
        assert args_default.legacy_gui is False
        assert args_default.gui is False

        args_gui = parse_args(["--gui"])
        assert args_gui.gui is True
        assert args_gui.legacy_gui is False

        args_legacy = parse_args(["--legacy-gui"])
        assert args_legacy.legacy_gui is True

    def test_web_window_and_legacy_window_instantiation(self, qapp, app_controller):
        """10. Verify both modern WebWindow and legacy MainWindow instantiate cleanly."""
        # 1. Test Modern WebWindow
        web_win = SanketWebWindow(app_controller)
        assert web_win is not None
        assert web_win.web_view is not None
        assert web_win.bridge is not None
        web_win.close()

        # 2. Test Legacy MainWindow
        legacy_win = MainWindow(app_controller)
        assert legacy_win is not None
        assert legacy_win.video_widget is not None
        assert legacy_win.control_panel is not None
        legacy_win.close()

    def test_pyinstaller_spec_packaging_compatibility(self):
        """11. Verify spec includes frontend bundle and WebEngine hidden imports."""
        spec_path = "sanket.spec"
        assert os.path.isfile(spec_path), f"PyInstaller spec file {spec_path} missing!"

        with open(spec_path, "r", encoding="utf-8") as f:
            spec_content = f.read()

        assert "frontend/dist" in spec_content, f"Missing frontend/dist in added_files of {spec_path}"
        assert "PySide6.QtWebEngineWidgets" in spec_content, "Missing PySide6.QtWebEngineWidgets in hidden_imports"
        assert "PySide6.QtWebChannel" in spec_content, "Missing PySide6.QtWebChannel in hidden_imports"

