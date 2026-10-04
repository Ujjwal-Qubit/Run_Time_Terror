"""
SANKET — Consolidated Submission Screenshot Capture Script.
Generates pristine, high-resolution (1920x1080) screenshots directly from
the live application runtime for:
  - deliverables/UI_Screenshots/
  - docs/assets/screenshots/
  - deliverables/03_Technical_Report/figures/
  - deliverables/04_User_Manual/figures/
"""

from __future__ import annotations

import os
import sys
import time
import shutil
from pathlib import Path
from typing import Dict, Any, List

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
    base_ss = PROJECT_ROOT / "deliverables" / "UI_Screenshots"
    dev_dir = base_ss / "developer"
    eval_dir = base_ss / "evaluator"
    diag_dir = base_ss / "diagnostics"
    hist_dir = base_ss / "history"
    res_dir = base_ss / "results"
    ctrl_dir = base_ss / "controls"
    state_dir = base_ss / "states"
    over_dir = base_ss / "overview"

    for d in [dev_dir, eval_dir, diag_dir, hist_dir, res_dir, ctrl_dir, state_dir, over_dir]:
        d.mkdir(parents=True, exist_ok=True)

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

    def snap(path: Path):
        qapp.processEvents()
        pix = win.web_view.grab()
        pix.save(str(path), "PNG")
        print(f"  [SAVED] {path.relative_to(PROJECT_ROOT)} ({path.stat().st_size:,} bytes)")

    # 1. Developer Workspace - 2D Sensor View (Default / Idle)
    print("\n--- Capturing Developer Views (Idle) ---")
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
    snap(dev_dir / "2d_sensor.png")
    snap(over_dir / "full_workspace_overview.png")

    # 2. Developer Workspace - 3D Pedestal Frustum Sub-View
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('3D Pedestal Frustum'));
        if (tab) tab.click();
    """)
    wait_ms(500)
    snap(dev_dir / "3d_pedestal.png")

    # 3. Developer Workspace - 2000x2000 World Canvas Sub-View
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('World Canvas'));
        if (tab) tab.click();
    """)
    wait_ms(500)
    snap(dev_dir / "world_canvas.png")

    # 4. Evaluator Workspace
    print("\n--- Capturing Evaluator, Diagnostics, History, Results ---")
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Evaluator Workspace'));
        if (btn) btn.click();
    """)
    wait_ms(500)
    snap(eval_dir / "evaluator_main.png")

    # 5. Diagnostics & Subsystem Audit
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Diagnostics & Audit'));
        if (btn) btn.click();
    """)
    wait_ms(500)
    snap(diag_dir / "diagnostics_main.png")

    # 6. Run History & Artifact Catalog
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Run History'));
        if (btn) btn.click();
    """)
    wait_ms(500)
    snap(hist_dir / "run_history.png")

    # 7. Results & Analysis
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Results & Analysis'));
        if (btn) btn.click();
    """)
    wait_ms(500)
    snap(res_dir / "results_analysis.png")

    # 8. Active Tracking States & Controls
    print("\n--- Capturing Active Simulation States ---")
    # Return to Developer Workspace -> 2D Sensor View
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Developer Workspace'));
        if (btn) btn.click();
    """)
    wait_ms(300)
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('2D Sensor View'));
        if (tab) tab.click();
    """)
    wait_ms(300)

    # Trigger RUN
    eval_sync(win, """
        const runBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'RUN' || b.textContent.includes('RUN'));
        if (runBtn) runBtn.click();
    """)
    # Wait for simulation to run ~40 frames
    print("Running simulation for active tracking capture...")
    wait_ms(1500)

    snap(state_dir / "tracking_active.png")
    snap(ctrl_dir / "transport_controls.png")

    # Pause simulation
    eval_sync(win, """
        const pauseBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'PAUSE' || b.textContent.includes('PAUSE'));
        if (pauseBtn) pauseBtn.click();
    """)
    wait_ms(300)
    snap(state_dir / "tracking_paused.png")

    # Capture 3D and World Canvas in tracking state
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('3D Pedestal Frustum'));
        if (tab) tab.click();
    """)
    wait_ms(500)
    snap(state_dir / "3d_pedestal_tracking.png")

    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('World Canvas'));
        if (tab) tab.click();
    """)
    wait_ms(500)
    snap(state_dir / "world_canvas_tracking.png")

    # Stop / Reset
    eval_sync(win, """
        const resetBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'RESET' || b.textContent.includes('RESET'));
        if (resetBtn) resetBtn.click();
    """)
    wait_ms(300)

    win.close()
    ctrl.stop()
    qapp.quit()

    # Mirroring key screenshots to docs/assets/screenshots and report figure folders
    print("\n--- Mirroring screenshots for Documentation and Technical Report ---")
    doc_ss = PROJECT_ROOT / "docs" / "assets" / "screenshots"
    tr_fig = PROJECT_ROOT / "deliverables" / "03_Technical_Report" / "figures"
    um_fig = PROJECT_ROOT / "deliverables" / "04_User_Manual" / "figures"

    for d in [doc_ss, tr_fig, um_fig]:
        d.mkdir(parents=True, exist_ok=True)

    mappings = [
        (dev_dir / "2d_sensor.png", "01_developer_2d_sensor.png"),
        (dev_dir / "3d_pedestal.png", "02_developer_3d_pedestal.png"),
        (dev_dir / "world_canvas.png", "03_developer_world_canvas.png"),
        (eval_dir / "evaluator_main.png", "04_evaluator_workspace.png"),
        (diag_dir / "diagnostics_main.png", "05_diagnostics_audit.png"),
        (hist_dir / "run_history.png", "06_run_history_catalog.png"),
        (res_dir / "results_analysis.png", "07_results_analysis.png"),
        (state_dir / "tracking_active.png", "08_tracking_active.png"),
        (state_dir / "3d_pedestal_tracking.png", "09_3d_tracking_frustum.png"),
        (state_dir / "world_canvas_tracking.png", "10_world_canvas_tracking.png"),
    ]

    for src_file, dst_name in mappings:
        if src_file.exists():
            for target_dir in [doc_ss, tr_fig, um_fig]:
                shutil.copy2(src_file, target_dir / dst_name)
            print(f"  Copied {src_file.name} -> {dst_name}")

    print("\n[SUCCESS] Consolidated screenshot library populated successfully.")


if __name__ == "__main__":
    main()
