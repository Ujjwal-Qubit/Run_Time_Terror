from __future__ import annotations
import sys
import logging
from PySide6.QtWidgets import QApplication

from src.app.app_controller import AppController
from src.app.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


def launch_gui(app: AppController) -> None:
    """Entry point for the legacy native PySide6 UI."""
    qt_app = QApplication.instance()
    if not qt_app:
        qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("SIH 2026 - FSOC Virtual Camera Tracker (Legacy)")
    window = MainWindow(app)
    window.show()
    sys.exit(qt_app.exec())


def launch_web_gui(app: AppController) -> None:
    """Entry point for the modern React / WebEngine UI with automatic fallback."""
    try:
        from src.app.gui.web_window import LumiTrackWebWindow, resolve_frontend_dist
        dist = resolve_frontend_dist()
        if not dist:
            logger.warning("[GUI] Modern frontend dist not found. Falling back to native PySide6 GUI.")
            launch_gui(app)
            return

        qt_app = QApplication.instance()
        if not qt_app:
            qt_app = QApplication(sys.argv)
        qt_app.setApplicationName("LumiTrack - FSOC Virtual Camera Tracker")
        window = LumiTrackWebWindow(app)
        window.show()
        sys.exit(qt_app.exec())
    except Exception as e:
        logger.error(f"[GUI] Failed to launch modern WebEngine UI ({e}). Falling back to native PySide6 GUI.")
        launch_gui(app)
