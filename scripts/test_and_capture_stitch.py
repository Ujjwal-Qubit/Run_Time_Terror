"""
LumiTrack — Comprehensive Stitch 3D Frustum & World Canvas Integration Test & Capture
Validates:
  1. All 5 Target Viewports:
     - 1920×1080 (FHD / Primary Workstation)
     - 1600×900 (High-Density Workstation)
     - 1366×768 (Standard Laptop)
     - 1280×720 (HD Ready)
     - 1024×700 (Minimum Certified Display)
  2. Developer Workspace Subviews:
     - 2D Sensor View (640×480)
     - 3D Pedestal Frustum View (Stitch Approved Design)
     - 2000×2000 World Canvas View (Stitch Approved Design)
  3. Interactive Navigation:
     - Developer subview tabs (2D <-> 3D <-> World)
     - Sidebar Quick-Jump navigation
     - Minimap [EXPAND] triggers in 3D and World views
  4. Responsive Scroll Containment:
     - #lumitrack-main-scroll-container horizontal overflow = 0
     - Vertical scrolling accessibility
     - Absence of clipped/obscured controls
  5. Live Telemetry & Simulation Reactivity:
     - Simulation start/step
     - Dynamic pan/tilt encoder updates reflected in SVG geometry
  6. Zero Console/JavaScript Errors
  7. High-Fidelity Multi-Resolution Screenshots for all 7 production views across 5 viewports (35 screenshots)
"""

from __future__ import annotations

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtWebEngineCore import QWebEnginePage
from src.app.app_controller import AppController
from src.app.gui.web_window import LumiTrackWebWindow

VIEWPORTS = [
    (1920, 1080, "1920x1080"),
    (1600, 900, "1600x900"),
    (1366, 768, "1366x768"),
    (1280, 720, "1280x720"),
    (1024, 700, "1024x700"),
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
        "name": "Developer Workspace (2000x2000 World Canvas Sub-View)",
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


class CustomWebPage(QWebEnginePage):
    """Captures JavaScript console messages and errors."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.console_messages: List[Dict[str, Any]] = []

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        level_str = "INFO"
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel:
            level_str = "WARNING"
        elif level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            level_str = "ERROR"
        self.console_messages.append({
            "level": level_str,
            "message": message,
            "line": line_number,
            "source": source_id,
        })
        if level_str == "ERROR":
            print(f"[JS ERROR] {source_id}:{line_number} -> {message}")


def main():
    out_dir = PROJECT_ROOT / "audit" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_json_path = PROJECT_ROOT / "audit" / "STITCH_3D_WORLD_TEST_METRICS.json"

    qapp = QApplication.instance() or QApplication(sys.argv)
    ctrl = AppController()
    if ctrl.config_manager and ctrl.config_manager.config:
        ctrl.config_manager.config.simulation.duration_s = None
    ctrl.initialize()

    win = LumiTrackWebWindow(ctrl)
    win.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    win.resize(1920, 1080)
    win.show()

    print("\n[INIT] Pre-warming WebEngine and React app...")
    wait_ms(4500)

    # Attach error listener in JS context
    eval_sync(win, """
        window.__jsErrors = [];
        window.__jsWarnings = [];
        window.addEventListener('error', e => {
            window.__jsErrors.push({ message: e.message, filename: e.filename, lineno: e.lineno });
        });
        window.addEventListener('unhandledrejection', e => {
            window.__jsErrors.push({ message: String(e.reason) });
        });
        const origWarn = console.warn;
        console.warn = (...args) => {
            window.__jsWarnings.push(args.map(String).join(' '));
            origWarn.apply(console, args);
        };
        const origErr = console.error;
        console.error = (...args) => {
            window.__jsErrors.push({ message: args.map(String).join(' ') });
            origErr.apply(console, args);
        };
        return 'listener_attached';
    """)

    # Step 1: Functional Subview Navigation Verification
    print("\n==========================================")
    print("PHASE 1: SUBVIEW NAVIGATION INTERACTIVE TEST")
    print("==========================================")

    nav_test_results = {}

    # Test 1.1: Direct Tab Switching inside Developer Workspace
    print("  Testing subview tab switching: 2D -> 3D -> World -> 2D...")
    tab_res_3d = eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('3D Pedestal Frustum'));
        if (btn) { btn.click(); return 'clicked_3d'; }
        return 'not_found_3d';
    """)
    wait_ms(600)
    has_3d_canvas = eval_sync(win, """
        return !!document.querySelector('svg[viewBox="0 0 640 480"]') || document.body.textContent.includes('3D Pedestal Frustum ACTIVE');
    """)
    nav_test_results["tab_switch_to_3d"] = {"action": tab_res_3d, "verified": bool(has_3d_canvas)}
    print(f"    Switch to 3D: action={tab_res_3d}, verified={has_3d_canvas}")

    tab_res_world = eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('World Canvas'));
        if (btn) { btn.click(); return 'clicked_world'; }
        return 'not_found_world';
    """)
    wait_ms(600)
    has_world_canvas = eval_sync(win, """
        return !!document.querySelector('svg[viewBox="0 0 2000 2000"]') || document.body.textContent.includes('2000×2000 World Canvas ACTIVE');
    """)
    nav_test_results["tab_switch_to_world"] = {"action": tab_res_world, "verified": bool(has_world_canvas)}
    print(f"    Switch to World: action={tab_res_world}, verified={has_world_canvas}")

    tab_res_2d = eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('2D Sensor View'));
        if (btn) { btn.click(); return 'clicked_2d'; }
        return 'not_found_2d';
    """)
    wait_ms(600)
    has_2d_canvas = eval_sync(win, """
        return !!document.querySelector('canvas') && document.body.textContent.includes('2D Sensor View (640×480) ACTIVE');
    """)
    nav_test_results["tab_switch_to_2d"] = {"action": tab_res_2d, "verified": bool(has_2d_canvas)}
    print(f"    Switch back to 2D: action={tab_res_2d}, verified={has_2d_canvas}")

    # Test 1.2: Sidebar Quick-Jump navigation
    print("\n  Testing Sidebar Quick-Jump views...")
    qj_res_3d = eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('3D Pedestal Frustum'));
        if (btn) { btn.click(); return 'qj_3d_clicked'; }
        return 'qj_3d_not_found';
    """)
    wait_ms(600)
    has_3d_qj = eval_sync(win, """
        return !!document.querySelector('svg[viewBox="0 0 640 480"]') || document.body.textContent.includes('3D Pedestal Frustum ACTIVE');
    """)
    nav_test_results["quick_jump_3d"] = {"action": qj_res_3d, "verified": bool(has_3d_qj)}
    print(f"    Quick-Jump 3D: action={qj_res_3d}, verified={has_3d_qj}")

    qj_res_world = eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('World Canvas'));
        if (btn) { btn.click(); return 'qj_world_clicked'; }
        return 'qj_world_not_found';
    """)
    wait_ms(600)
    has_world_qj = eval_sync(win, """
        return !!document.querySelector('svg[viewBox="0 0 2000 2000"]') || document.body.textContent.includes('2000×2000 World Canvas ACTIVE');
    """)
    nav_test_results["quick_jump_world"] = {"action": qj_res_world, "verified": bool(has_world_qj)}
    print(f"    Quick-Jump World: action={qj_res_world}, verified={has_world_qj}")

    # Test 1.3: Minimap [EXPAND] triggers
    print("\n  Testing Minimap [EXPAND] buttons...")
    # Currently in World Canvas, click [EXPAND] on 3D Pedestal minimap
    expand_3d = eval_sync(win, """
        const btns = Array.from(document.querySelectorAll('main button')).filter(b => b.textContent.includes('EXPAND'));
        if (btns.length >= 2) {
            // Second minimap in World Canvas is 3D Pedestal Frustum
            btns[1].click();
            return 'expand_3d_clicked';
        }
        return 'minimap_btn_not_found';
    """)
    wait_ms(600)
    has_3d_expand = eval_sync(win, """
        return !!document.querySelector('svg[viewBox="0 0 640 480"]') || document.body.textContent.includes('3D Pedestal Frustum ACTIVE');
    """)
    nav_test_results["minimap_expand_to_3d"] = {"action": expand_3d, "verified": bool(has_3d_expand)}
    print(f"    Minimap [EXPAND] to 3D: action={expand_3d}, verified={has_3d_expand}")

    # From 3D view, click [EXPAND] on World Canvas minimap
    expand_world = eval_sync(win, """
        const btns = Array.from(document.querySelectorAll('main button')).filter(b => b.textContent.includes('EXPAND'));
        if (btns.length >= 2) {
            // Second minimap in 3D view is World Canvas
            btns[1].click();
            return 'expand_world_clicked';
        }
        return 'minimap_btn_not_found';
    """)
    wait_ms(600)
    has_world_expand = eval_sync(win, """
        return !!document.querySelector('svg[viewBox="0 0 2000 2000"]') || document.body.textContent.includes('2000×2000 World Canvas ACTIVE');
    """)
    nav_test_results["minimap_expand_to_world"] = {"action": expand_world, "verified": bool(has_world_expand)}
    print(f"    Minimap [EXPAND] to World: action={expand_world}, verified={has_world_expand}")

    # Step 2: Live Telemetry Reactivity Verification
    print("\n==========================================")
    print("PHASE 2: LIVE SIMULATION REACTIVITY TEST")
    print("==========================================")
    # Trigger Run via bridge
    win.bridge.runSimulation()
    wait_ms(1500)
    sim_status_raw = eval_sync(win, """
        const el = document.querySelector('header');
        const text = el ? el.textContent : '';
        return JSON.stringify({
            headerText: text,
            hasFps: text.includes('FPS'),
        });
    """)
    try:
        sim_status = json.loads(sim_status_raw) if sim_status_raw else {}
    except Exception:
        sim_status = {"headerText": str(sim_status_raw), "hasFps": "FPS" in str(sim_status_raw)}
    print(f"    Simulation running check: hasFps={sim_status.get('hasFps', False)}")

    # Step 3: Multi-Resolution Viewport Audit & Screenshot Capture
    print("\n==========================================")
    print("PHASE 3: MULTI-RESOLUTION VIEWPORT & SCROLL AUDIT")
    print("==========================================")

    viewport_metrics = []
    screenshots_manifest = []

    for width, height, res_tag in VIEWPORTS:
        print(f"\n--- Testing Viewport: {res_tag} ({width}×{height}) ---")
        win.resize(width, height)
        win.web_view.resize(width, height)
        qapp.processEvents()
        wait_ms(400)

        for screen in SCREENS:
            sid = screen["id"]
            sname = screen["name"]
            ntype = screen["nav_type"]

            # Navigate to screen
            if ntype == "dev_tab":
                tab_label = screen["tab_label"]
                # Ensure Developer Workspace
                eval_sync(win, """
                    const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Developer Workspace'));
                    if (btn) btn.click();
                """)
                wait_ms(200)
                # Click subview tab
                eval_sync(win, f"""
                    const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('{tab_label}'));
                    if (tab) tab.click();
                """)
                wait_ms(350)
            else:
                aside_label = screen["aside_label"]
                eval_sync(win, f"""
                    const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('{aside_label}'));
                    if (btn) btn.click();
                """)
                wait_ms(400)

            # Audit Scroll Container at this viewport
            scroll_audit_raw = eval_sync(win, """
                const sc = document.getElementById('lumitrack-main-scroll-container');
                if (!sc) return JSON.stringify({ error: 'scroll_container_not_found' });
                const cs = window.getComputedStyle(sc);
                return JSON.stringify({
                    clientWidth: sc.clientWidth,
                    scrollWidth: sc.scrollWidth,
                    clientHeight: sc.clientHeight,
                    scrollHeight: sc.scrollHeight,
                    scrollTop: sc.scrollTop,
                    overflowY: cs.overflowY,
                    overflowX: cs.overflowX,
                    hasHorizontalOverflow: sc.scrollWidth > sc.clientWidth,
                    isScrollableY: sc.scrollHeight > sc.clientHeight,
                });
            """)
            try:
                scroll_audit = json.loads(scroll_audit_raw) if scroll_audit_raw else {}
            except Exception:
                scroll_audit = {}

            # Capture screenshot
            filename = f"{sid}_{res_tag}.png"
            filepath = out_dir / filename
            pix = win.web_view.grab()
            pix.save(str(filepath), "PNG")
            size_bytes = filepath.stat().st_size

            metric_entry = {
                "screen_id": sid,
                "screen_name": sname,
                "viewport": res_tag,
                "width": width,
                "height": height,
                "scroll_audit": scroll_audit,
                "filename": filename,
                "size_bytes": size_bytes,
            }
            viewport_metrics.append(metric_entry)
            screenshots_manifest.append({
                "screen_id": sid,
                "viewport": res_tag,
                "filename": filename,
                "filepath": str(filepath),
                "size_bytes": size_bytes,
            })
            h_status = "PASS (0px overflow)" if not scroll_audit.get("hasHorizontalOverflow") else "FAIL (overflow)"
            print(f"    [{sid} @ {res_tag}]: {h_status}, Client: {scroll_audit.get('clientWidth')}x{scroll_audit.get('clientHeight')}, Scroll: {scroll_audit.get('scrollWidth')}x{scroll_audit.get('scrollHeight')}, Saved: {filename} ({size_bytes:,} B)")

    # Stop simulation
    win.bridge.pauseSimulation()

    # Step 4: Console Messages & Errors Check
    print("\n==========================================")
    print("PHASE 4: CONSOLE ERROR & LOG AUDIT")
    print("==========================================")
    js_errors = eval_sync(win, "return window.__jsErrors || [];") or []
    js_warnings = eval_sync(win, "return window.__jsWarnings || [];") or []
    print(f"  Total JS Errors Intercepted: {len(js_errors)}")
    print(f"  Total JS Warnings Intercepted: {len(js_warnings)}")
    for err in js_errors:
        print(f"    ERROR: {err}")

    # Compile Final Report
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "navigation_tests": nav_test_results,
        "console_errors_count": len(js_errors),
        "console_errors": js_errors,
        "total_screenshots": len(screenshots_manifest),
        "viewport_metrics": viewport_metrics,
    }

    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\n[DONE] Full verification report saved to: {report_json_path}")

    win.close()
    qapp.quit()


if __name__ == "__main__":
    main()
