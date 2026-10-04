"""
SANKET — QWebEngine Host Window (Phase 1 POC)

Embeds the production React/TypeScript/Vite static bundle inside a native PySide6
desktop window via QWebEngineView and connects it to the Python core engine via QtWebChannel.
"""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QMainWindow, QApplication, QMessageBox, QWidget, QVBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import QUrl, Qt
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PySide6.QtWebChannel import QWebChannel

from src.app.app_controller import AppController
from src.app.gui.web_bridge import SanketBridge

logger = logging.getLogger(__name__)


def resolve_frontend_dist() -> str:
    """
    Locates the compiled production frontend dist/index.html.
    Supports PyInstaller bundle (sys._MEIPASS), development workspace, and installed paths.
    """
    candidates = []

    # 1. PyInstaller bundled path
    if hasattr(sys, "_MEIPASS"):
        meipass = getattr(sys, "_MEIPASS")
        candidates.append(os.path.join(meipass, "frontend", "dist", "index.html"))
        candidates.append(os.path.join(meipass, "src", "gui", "web", "dist", "index.html"))
        candidates.append(os.path.join(meipass, "dist", "index.html"))

    # 2. Relative to application executable
    if hasattr(sys, "executable"):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(os.path.join(exe_dir, "frontend", "dist", "index.html"))
        candidates.append(os.path.join(exe_dir, "frontend", "index.html"))
        candidates.append(os.path.join(exe_dir, "_internal", "frontend", "dist", "index.html"))

    # 3. Development workspace paths
    project_root = Path(__file__).resolve().parents[3]
    candidates.append(str(project_root / "frontend" / "dist" / "index.html"))
    candidates.append(os.path.join(os.getcwd(), "frontend", "dist", "index.html"))

    for path in candidates:
        if os.path.isfile(path):
            logger.info(f"[SanketWebWindow] Found frontend bundle at: {path}")
            return os.path.abspath(path)

    return ""


class SanketWebWindow(QMainWindow):
    """Native desktop host window containing embedded QWebEngineView and QtWebChannel."""

    def __init__(self, app_controller: AppController, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.app = app_controller

        self.setWindowTitle("SANKET — Virtual Camera Tracking Workstation [SIH PS 26169]")
        self.resize(1440, 900)
        self.setMinimumSize(1024, 700)

        # Set SANKET application icon from final logo assets
        icon_candidates = [
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "App_Logo_Assets_Final", "app_icon_256.png"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "App_Logo_Assets_Final", "favicon.ico"),
            os.path.join(getattr(sys, "_MEIPASS", ""), "App_Logo_Assets_Final", "app_icon_256.png"),
            os.path.join(getattr(sys, "_MEIPASS", ""), "App_Logo_Assets_Final", "favicon.ico"),
        ]
        for icon_path in icon_candidates:
            if icon_path and os.path.isfile(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                break

        # Main container
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 1. Initialize WebEngine View
        self.web_view = QWebEngineView(self)
        self.layout.addWidget(self.web_view)

        # Configure Security & WebEngine Settings
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        # 2. Setup QtWebChannel Bridge
        self.channel = QWebChannel(self.web_view.page())
        self.bridge = SanketBridge(self.app, self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # Wire up native file download handling for standalone desktop WebEngine
        try:
            self.web_view.page().profile().downloadRequested.connect(self._on_download_requested)
        except Exception as e:
            logger.warning(f"[SanketWebWindow] Failed to connect downloadRequested: {e}")

        # 3. Locate & Load Frontend
        dist_path = resolve_frontend_dist()
        if not dist_path:
            error_msg = (
                "SANKET production frontend bundle was not found!\n\n"
                "Expected location: frontend/dist/index.html\n"
                "Please run 'npm run build' inside the frontend directory, "
                "or launch with --legacy-gui for the native PySide6 UI."
            )
            logger.error(error_msg)
            QMessageBox.critical(self, "Frontend Bundle Missing", error_msg)
            return

        file_url = QUrl.fromLocalFile(dist_path)
        logger.info(f"[SanketWebWindow] Loading URL: {file_url.toString()}")
        self.web_view.load(file_url)

    def _on_download_requested(self, download_item) -> None:
        """Handle browser file downloads (CSV, MD, JSON) inside desktop QWebEngineView."""
        try:
            suggested_filename = download_item.suggestedFileName() or "sanket_artifact"
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.isdir(downloads_dir):
                downloads_dir = os.path.abspath("output")
                os.makedirs(downloads_dir, exist_ok=True)
            target_path = os.path.join(downloads_dir, suggested_filename)
            download_item.setDownloadDirectory(downloads_dir)
            download_item.setDownloadFileName(suggested_filename)
            download_item.accept()
            logger.info(f"[SanketWebWindow] Desktop download accepted and saved to: {target_path}")
        except Exception as e:
            logger.error(f"[SanketWebWindow] Error handling downloadRequested: {e}")

    def closeEvent(self, event) -> None:
        """Ensure clean shutdown of simulation and WebEngine on window close."""
        logger.info("[SanketWebWindow] Closing window; stopping simulation...")
        if hasattr(self, "bridge") and self.bridge:
            self.bridge._timer.stop()
        self.app.stop()
        event.accept()


def launch_web_gui(app: AppController) -> None:
    """Entry point for the modern React/WebEngine standalone UI."""
    qt_app = QApplication.instance()
    if not qt_app:
        qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("SANKET - FSOC Virtual Camera Tracker")
    icon_candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "App_Logo_Assets_Final", "app_icon_256.png"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "App_Logo_Assets_Final", "favicon.ico"),
    ]
    for icon_path in icon_candidates:
        if icon_path and os.path.isfile(icon_path):
            qt_app.setWindowIcon(QIcon(icon_path))
            break

    window = SanketWebWindow(app)
    window.show()
    sys.exit(qt_app.exec())

