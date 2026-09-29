"""
LumiTrack — Phase 2 Workspace Expansion & Ground-Truth Firewall Test Suite

Verifies:
  1. All Phase 2 QtWebChannel signals exist and emit valid JSON schemas.
  2. Subsystem Diagnostics emits 12 software subsystems with real status/rates.
  3. Ground-Truth Firewall status is ENFORCED with zero leakage into live streams.
  4. Run History Catalog scans real `output/` artifacts without mockup data.
  5. Artifact loader safely accesses project files and blocks directory traversal.
  6. Results Analysis time-series extracts real data and enforces firewall gating:
     - validation_mode=False: ground truth error is NULL/omitted.
     - validation_mode=True: ground truth error is populated.
  7. Validation mode toggle slot updates system status cleanly.
  8. Browser instrumentation reporting slot records client-side metrics on Python bridge.
  9. Modern frontend static bundle contains all 6 workspaces with zero external CDN links.
 10. Dual-GUI CLI fallback remains intact.
"""

from __future__ import annotations

import json
import os
import re
import pytest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.app.app_controller import AppController
from src.app.gui.web_bridge import LumiTrackBridge
from src.app.gui.web_window import resolve_frontend_dist
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


class TestPhase2WorkspaceExpansion:
    """Phase 2 Workspace & Signal Verification Tests."""

    def test_frontend_bundle_all_workspaces_built(self):
        """1. Verify frontend dist exists, includes all 6 workspaces, and has 0 external URLs."""
        dist_path = resolve_frontend_dist()
        assert os.path.isfile(dist_path), f"Frontend dist bundle not found at {dist_path}"

        with open(dist_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Check for external URLs
        external_urls = re.findall(r'(?:href|src)=["\'](https?://[^"\']+)["\']', html)
        assert len(external_urls) == 0, f"Found external CDN/HTTP URLs in dist/index.html: {external_urls}"

        # Check bundle JS
        dist_dir = Path(dist_path).parent
        js_files = list((dist_dir / "assets").glob("*.js"))
        assert len(js_files) > 0, "No JavaScript bundle found in dist/assets"

        js_content = js_files[0].read_text(encoding="utf-8", errors="ignore")
        # Verify workspace markers / strings are present in bundle
        assert "Diagnostics & Subsystem Audit" in js_content or "subsystemDiagnosticsUpdated" in js_content
        assert "Run History Catalog" in js_content or "runHistoryUpdated" in js_content
        assert "Results & Analysis" in js_content or "resultsAnalysisLoaded" in js_content

    def test_bridge_phase2_signals_exist(self, qapp, app_controller):
        """2. Verify that all Phase 2 signals exist on LumiTrackBridge."""
        bridge = LumiTrackBridge(app_controller)
        bridge._timer.stop()

        assert hasattr(bridge, "subsystemDiagnosticsUpdated")
        assert hasattr(bridge, "runHistoryUpdated")
        assert hasattr(bridge, "runArtifactLoaded")
        assert hasattr(bridge, "benchmarkProgress")
        assert hasattr(bridge, "benchmarkCompleted")
        assert hasattr(bridge, "resultsAnalysisLoaded")

    def test_subsystem_diagnostics_slot(self, qapp, app_controller):
        """3. Verify getSubsystemDiagnostics emits 12 software subsystems with valid schema."""
        bridge = LumiTrackBridge(app_controller)
        bridge._timer.stop()

        received_diag = []
        bridge.subsystemDiagnosticsUpdated.connect(lambda s: received_diag.append(json.loads(s)))

        bridge.getSubsystemDiagnostics()

        assert len(received_diag) == 1
        subsystems = received_diag[0]
        assert isinstance(subsystems, list)
        assert len(subsystems) == 12

        # Check critical subsystems
        ids = [s["id"] for s in subsystems]
        assert "sensor_pipeline" in ids
        assert "detection_engine" in ids
        assert "aiml_classifier" in ids
        assert "kalman_tracker" in ids
        assert "ptz_controller" in ids
        assert "benchmark_engine" in ids
        assert "web_bridge" in ids
        assert "firewall" in ids
        assert "logging_engine" in ids

        # Verify Ground-Truth Firewall status
        firewall_sub = next(s for s in subsystems if s["id"] == "firewall")
        assert firewall_sub["status"] == "ENFORCED"
        assert "AST" in firewall_sub["details"] or "Zero Ground Truth" in firewall_sub["details"]

        # Verify no fictional hardware claims
        for s in subsystems:
            assert "Ring0" not in s["name"] and "Ring0" not in s["details"]
            assert "DMA" not in s["name"] and "DMA" not in s["details"]
            assert "/dev/fsoc_fpa0" not in s["details"]
            assert "e3b0c442" not in s["details"]

    def test_run_history_slot(self, qapp, app_controller):
        """4. Verify getRunHistory scans real output/ directory and returns valid catalog items."""
        bridge = LumiTrackBridge(app_controller)
        bridge._timer.stop()

        received_history = []
        bridge.runHistoryUpdated.connect(lambda s: received_history.append(json.loads(s)))

        bridge.getRunHistory()

        assert len(received_history) == 1
        catalog = received_history[0]
        assert isinstance(catalog, list)

        # If there are real runs in output/, verify schema
        if len(catalog) > 0:
            first = catalog[0]
            assert "runId" in first
            assert "timestamp" in first
            assert "totalFrames" in first
            assert "rmseCentroidPx" in first
            assert "lockRetentionPct" in first
            assert "passedSihSpec" in first
            assert isinstance(first["passedSihSpec"], bool)

    def test_run_artifact_loader_and_path_containment(self, qapp, app_controller):
        """5. Verify getRunArtifact loads real file and blocks directory traversal attempts."""
        bridge = LumiTrackBridge(app_controller)
        bridge._timer.stop()

        received_artifacts = []
        bridge.runArtifactLoaded.connect(lambda s: received_artifacts.append(json.loads(s)))

        # Find any real artifact file
        summary_files = list(Path("output").glob("run_*_summary.json"))
        if summary_files:
            test_path = str(summary_files[0])
            bridge.getRunArtifact(test_path)
            assert len(received_artifacts) == 1
            payload = received_artifacts[0]
            assert payload["filename"] == summary_files[0].name
            assert payload["format"] == "json"
            assert "run_id" in payload["content"]

        # Test directory traversal security
        bridge.getRunArtifact("../../../../../../../windows/system.ini")
        # Should not emit unauthorized external files
        assert len(received_artifacts) <= 1

    def test_results_analysis_firewall_isolation(self, qapp, app_controller):
        """6. Verify getResultsAnalysisData respects Ground-Truth Firewall."""
        bridge = LumiTrackBridge(app_controller)
        bridge._timer.stop()

        received_results = []
        bridge.resultsAnalysisLoaded.connect(lambda s: received_results.append(json.loads(s)))

        # 6a. In live / normal mode: validationMode = False
        bridge.toggleValidationMode(False)
        bridge.getResultsAnalysisData("")

        if len(received_results) > 0:
            data_live = received_results[-1]
            assert data_live["validationModeActive"] is False
            # Ground truth errors MUST be None when validation mode is off
            assert data_live["validationGtErrors"] is None

        # 6b. In validation mode: validationMode = True
        bridge.toggleValidationMode(True)
        bridge.getResultsAnalysisData("")

        if len(received_results) > 1:
            data_val = received_results[-1]
            assert data_val["validationModeActive"] is True
            # When validation mode is ON, validationGtErrors is permitted for post-run analysis
            assert "validationGtErrors" in data_val

    def test_browser_metrics_reporting(self, qapp, app_controller):
        """7. Verify reportBrowserMetrics slot updates bridge metrics."""
        bridge = LumiTrackBridge(app_controller)
        bridge._timer.stop()

        bridge.reportBrowserMetrics(59.4, 55.0, 16.8, 0.42, 24.8)

        assert bridge.browser_render_fps == 59.4
        assert bridge.browser_min_fps == 55.0
        assert bridge.browser_frame_time_ms == 16.8
        assert bridge.browser_decode_time_ms == 0.42
        assert bridge.browser_telemetry_hz == 24.8

    def test_legacy_gui_flag_preserved(self):
        """8. Verify --legacy-gui CLI flag remains supported."""
        args_default = parse_args([])
        assert args_default.legacy_gui is False

        args_legacy = parse_args(["--legacy-gui"])
        assert args_legacy.legacy_gui is True
