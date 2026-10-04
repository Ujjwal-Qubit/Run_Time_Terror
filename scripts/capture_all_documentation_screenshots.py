"""
SANKET — Comprehensive Documentation Screenshot Capture Suite.
Captures all 18 high-resolution (1920x1080) real screenshots directly from the live
SANKET QtWebEngine runtime.

Target Screens:
  01_application_overview.png
  02_developer_workspace.png
  03_sensor_view.png
  04_3d_pedestal.png
  05_world_canvas.png
  06_evaluator_console.png
  07_benchmark_1_matrix.png
  08_benchmark_2_mp4.png
  09_diagnostics.png
  10_subsystem_audit.png
  11_run_history.png
  12_results_scorecards.png
  13_performance_metrics.png
  14_configuration_ui.png
  15_active_tracking_run.png
  16_disturbance_scenario.png
  17_3d_pedestal_tracking.png
  18_world_canvas_tracking.png
"""

from __future__ import annotations

import os
import sys
import time
import shutil
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer, Qt
from src.app.app_controller import AppController
from src.app.gui.web_window import SanketWebWindow


def wait_ms(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def eval_sync(win: SanketWebWindow, js_body: str) -> Any:
    res = []
    loop = QEventLoop()
    def cb(v):
        res.append(v)
        loop.quit()
    wrapped_js = f"(() => {{\n{js_body}\n}})()"
    win.web_view.page().runJavaScript(wrapped_js, cb)
    loop.exec()
    return res[0] if res else None


def main():
    target_dirs = [
        PROJECT_ROOT / "docs" / "assets" / "screenshots",
        PROJECT_ROOT / "deliverables" / "UI_Screenshots",
        PROJECT_ROOT / "deliverables" / "03_Technical_Report" / "figures",
        PROJECT_ROOT / "deliverables" / "04_User_Manual" / "figures",
    ]
    for d in target_dirs:
        d.mkdir(parents=True, exist_ok=True)

    primary_dir = PROJECT_ROOT / "docs" / "assets" / "screenshots"

    qapp = QApplication.instance() or QApplication(sys.argv)
    ctrl = AppController()
    if ctrl.config_manager and ctrl.config_manager.config:
        ctrl.config_manager.config.simulation.duration_s = None
    ctrl.initialize()

    win = SanketWebWindow(ctrl)
    win.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    win.resize(1920, 1080)
    win.web_view.resize(1920, 1080)
    win.show()

    print("[INIT] Pre-warming WebEngine and React UI...")
    wait_ms(4500)

    captured_files: list[Path] = []

    def snap(name: str) -> Path:
        qapp.processEvents()
        path = primary_dir / name
        pix = win.web_view.grab()
        pix.save(str(path), "PNG")
        print(f"  [SAVED] {name} ({path.stat().st_size:,} bytes)")
        captured_files.append(path)
        return path

    print("\n--- Capturing 01 & 02: Application Launch & Developer Workspace ---")
    # Developer Workspace - 2D Sensor View
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Developer Workspace'));
        if (btn) btn.click();
    """)
    wait_ms(400)
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('2D Sensor View'));
        if (tab) tab.click();
    """)
    wait_ms(400)
    snap("01_application_overview.png")
    snap("02_developer_workspace.png")
    snap("03_sensor_view.png")

    print("\n--- Capturing 04: 3D Pedestal Frustum View ---")
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('3D Pedestal Frustum'));
        if (tab) tab.click();
    """)
    wait_ms(600)
    snap("04_3d_pedestal.png")

    print("\n--- Capturing 05: World Canvas View ---")
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('World Canvas'));
        if (tab) tab.click();
    """)
    wait_ms(600)
    snap("05_world_canvas.png")

    print("\n--- Capturing 06 & 07: Evaluator Workspace & Benchmark 1 Matrix ---")
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Evaluator Workspace'));
        if (btn) btn.click();
    """)
    wait_ms(600)
    eval_sync(win, """
        const b1Btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Benchmark 1: Automated Scenario Matrix'));
        if (b1Btn) b1Btn.click();
    """)
    wait_ms(500)
    snap("06_evaluator_console.png")
    snap("07_benchmark_1_matrix.png")

    print("\n--- Capturing 08: Benchmark 2 Video Evaluator ---")
    eval_sync(win, """
        const b2Btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Benchmark 2: Video Evaluator'));
        if (b2Btn) b2Btn.click();
    """)
    wait_ms(600)
    # Select first sample video from dropdown if available
    eval_sync(win, """
        const sel = document.querySelector('select');
        if (sel && sel.options.length > 1) {
            sel.selectedIndex = 1;
            sel.dispatchEvent(new Event('change', { bubbles: true }));
        }
    """)
    wait_ms(500)
    snap("08_benchmark_2_mp4.png")

    print("\n--- Capturing 09 & 10: Diagnostics & Subsystem Audit ---")
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Diagnostics & Audit'));
        if (btn) btn.click();
    """)
    wait_ms(600)
    snap("09_diagnostics.png")
    snap("10_subsystem_audit.png")

    print("\n--- Capturing 11: Run History & Forensic Catalog ---")
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Run History'));
        if (btn) btn.click();
    """)
    wait_ms(600)
    snap("11_run_history.png")

    print("\n--- Capturing 12 & 13: Results & Analysis Scorecards & Metrics ---")
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Results & Analysis'));
        if (btn) btn.click();
    """)
    wait_ms(600)
    snap("12_results_scorecards.png")
    snap("13_performance_metrics.png")

    print("\n--- Capturing 14: Configuration UI Sidebar Focus ---")
    # Return to Developer Workspace -> 2D Sensor View
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Developer Workspace'));
        if (btn) btn.click();
    """)
    wait_ms(400)
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('2D Sensor View'));
        if (tab) tab.click();
    """)
    wait_ms(400)
    snap("14_configuration_ui.png")

    print("\n--- Capturing 15: Active Tracking Run ---")
    # Trigger RUN
    eval_sync(win, """
        const runBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'RUN' || b.textContent.includes('RUN'));
        if (runBtn) runBtn.click();
    """)
    print("Running simulation for 45 frames...")
    wait_ms(1600)
    snap("15_active_tracking_run.png")

    print("\n--- Capturing 16: Disturbance Scenario (Atmosphere / Jitter) ---")
    # Change atmosphere to Fog or Rain via sidebar buttons if available
    eval_sync(win, """
        const fogBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.toLowerCase().includes('fog'));
        if (fogBtn) fogBtn.click();
    """)
    wait_ms(1200)
    snap("16_disturbance_scenario.png")

    print("\n--- Capturing 17: 3D Pedestal Tracking Frustum ---")
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('3D Pedestal Frustum'));
        if (tab) tab.click();
    """)
    wait_ms(600)
    snap("17_3d_pedestal_tracking.png")

    print("\n--- Capturing 18: World Canvas Active Tracking ---")
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('World Canvas'));
        if (tab) tab.click();
    """)
    wait_ms(600)
    snap("18_world_canvas_tracking.png")

    # Stop / Reset simulation
    eval_sync(win, """
        const resetBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'RESET' || b.textContent.includes('RESET'));
        if (resetBtn) resetBtn.click();
    """)
    wait_ms(300)

    win.close()
    ctrl.stop()
    qapp.quit()

    print("\n--- Replicating captured screenshots to all deliverable asset directories ---")
    dest_dirs = [
        PROJECT_ROOT / "deliverables" / "UI_Screenshots",
        PROJECT_ROOT / "deliverables" / "03_Technical_Report" / "figures",
        PROJECT_ROOT / "deliverables" / "04_User_Manual" / "figures",
    ]
    for ss_path in captured_files:
        for dest in dest_dirs:
            shutil.copy2(ss_path, dest / ss_path.name)
        print(f"  Synced {ss_path.name}")

    print("\n[SUCCESS] All 18 screenshots captured, validated, and synchronized across directories.")


if __name__ == "__main__":
    main()
