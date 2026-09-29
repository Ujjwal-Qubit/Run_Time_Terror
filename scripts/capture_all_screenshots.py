"""
LumiTrack — Multi-Resolution Production Screenshot Capture Script
Captures all five workspaces across four target viewports:
  - 1920×1080 (FHD / Primary)
  - 1600×900 (Workstation)
  - 1366×768 (Laptop)
  - 1280×720 (HD)

Includes Developer Workspace integrated sub-views:
  - 2D Sensor View
  - 3D Pedestal Frustum
  - 2000×2000 World Canvas
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer, Qt
from src.app.app_controller import AppController
from src.app.gui.web_window import LumiTrackWebWindow

VIEWPORTS = [
    (1920, 1080, "1920x1080"),
    (1600, 900, "1600x900"),
    (1366, 768, "1366x768"),
    (1280, 720, "1280x720"),
]

SCREENS = [
    {
        "id": "developer_2d",
        "name": "Developer Workspace (2D Sensor View)",
        "nav_type": "dev_tab",
        "tab_label": "2D Sensor View",
    },
    {
        "id": "developer_3d",
        "name": "Developer Workspace (3D Pedestal Frustum Sub-View)",
        "nav_type": "dev_tab",
        "tab_label": "3D Pedestal Frustum",
    },
    {
        "id": "developer_world",
        "name": "Developer Workspace (World Canvas Sub-View)",
        "nav_type": "dev_tab",
        "tab_label": "World Canvas",
    },
    {
        "id": "evaluator",
        "name": "Evaluator Workspace",
        "nav_type": "workspace",
        "aside_label": "Evaluator Workspace",
    },
    {
        "id": "diagnostics",
        "name": "Diagnostics & Subsystem Audit",
        "nav_type": "workspace",
        "aside_label": "Diagnostics & Audit",
    },
    {
        "id": "history",
        "name": "Run History & Artifact Catalog",
        "nav_type": "workspace",
        "aside_label": "Run History",
    },
    {
        "id": "results",
        "name": "Results & Analysis",
        "nav_type": "workspace",
        "aside_label": "Results & Analysis",
    },
]


def wait_ms(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def eval_sync(win: LumiTrackWebWindow, js_body: str) -> Any:
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
    out_dir = PROJECT_ROOT / "audit" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    qapp = QApplication.instance() or QApplication(sys.argv)
    ctrl = AppController()
    if ctrl.config_manager and ctrl.config_manager.config:
        ctrl.config_manager.config.simulation.duration_s = None
    ctrl.initialize()

    win = LumiTrackWebWindow(ctrl)
    win.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    win.resize(1920, 1080)
    win.show()

    # Initial warm-up for WebEngine and React to boot
    print("Pre-warming WebEngine and React app...")
    wait_ms(4000)

    results_manifest: List[Dict[str, Any]] = []

    for width, height, res_tag in VIEWPORTS:
        print(f"\n==========================================")
        print(f"Setting Viewport: {res_tag} ({width}x{height})")
        print(f"==========================================")
        win.resize(width, height)
        win.web_view.resize(width, height)
        qapp.processEvents()
        wait_ms(400)

        for screen in SCREENS:
            sid = screen["id"]
            sname = screen["name"]
            ntype = screen["nav_type"]
            print(f"  Capturing: {sid} @ {res_tag}...")

            if ntype == "dev_tab":
                tab_label = screen["tab_label"]
                # 1. Ensure Developer Workspace is active
                res1 = eval_sync(win, """
                    const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Developer Workspace'));
                    if (btn) { btn.click(); return 'dev_clicked'; }
                    return 'dev_not_found';
                """)
                wait_ms(250)
                # 2. Select sub-view tab inside Developer Workspace
                js_tab = f"""
                    const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('{tab_label}'));
                    if (tab) {{ tab.click(); return 'tab_clicked'; }}
                    return 'tab_not_found';
                """
                res2 = eval_sync(win, js_tab)
                wait_ms(400)
            else:
                aside_label = screen["aside_label"]
                js_ws = f"""
                    const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('{aside_label}'));
                    if (btn) {{ btn.click(); return 'ws_clicked'; }}
                    return 'ws_not_found';
                """
                res_ws = eval_sync(win, js_ws)
                wait_ms(500)

            # Grab and save
            filename = f"{sid}_{res_tag}.png"
            filepath = out_dir / filename
            pix = win.web_view.grab()
            pix.save(str(filepath), "PNG")

            size_bytes = filepath.stat().st_size
            results_manifest.append({
                "screen_id": sid,
                "screen_name": sname,
                "viewport": res_tag,
                "width": width,
                "height": height,
                "filename": filename,
                "filepath": str(filepath),
                "size_bytes": size_bytes,
            })
            print(f"    Saved: {filename} ({size_bytes:,} bytes)")

    win.close()
    qapp.quit()
    print("\nAll 28 production screenshots captured successfully!")
    print(f"Total screenshots generated: {len(results_manifest)}")


if __name__ == "__main__":
    main()
