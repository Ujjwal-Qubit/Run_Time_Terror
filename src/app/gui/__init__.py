from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication

from src.app.app_controller import AppController
from src.app.gui.main_window import MainWindow


def launch_gui(app: AppController) -> None:
    """Entry point for the PySide6 standalone UI."""
    # Ensure a QApplication exists
    qt_app = QApplication.instance()
    if not qt_app:
        qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("SIH 2026 - FSOC Virtual Camera Tracker")
    window = MainWindow(app)
    window.show()
    # In case we want to return and continue
    sys.exit(qt_app.exec())
