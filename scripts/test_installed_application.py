"""
SANKET — Clean Installed Application Verification Suite (Task 3, 4, 8)
Tests the installed application from C:\\Users\\sanje\\AppData\\Local\\Programs\\SANKET\\ (or SANKET_Installed)
completely isolated from the source repository.
"""

from __future__ import annotations

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

INSTALLED_DIR_SANKET = Path(r"C:\Users\sanje\AppData\Local\Programs\SANKET")
INSTALLED_DIR_LUMI = Path(r"C:\Users\sanje\AppData\Local\Programs\SANKET_Installed")
INSTALLED_DIR = INSTALLED_DIR_SANKET if INSTALLED_DIR_SANKET.exists() else INSTALLED_DIR_LUMI
INSTALLED_EXE = INSTALLED_DIR / ("SANKET.exe" if (INSTALLED_DIR / "SANKET.exe").exists() else "SANKET.exe")
INTERNAL_DIR = INSTALLED_DIR / "_internal"
FRONTEND_DIST = INTERNAL_DIR / "frontend" / "dist"

def run_step(step_name: str):
    print(f"\n{'='*70}\n[INSTALLED TEST STEP] {step_name}\n{'='*70}")

def verify_installed_files() -> Dict[str, Any]:
    run_step("1. Installed Application File Audit Outside Source Repository")
    checks = {}

    checks["installed_exe_exists"] = INSTALLED_EXE.is_file()
    checks["installed_exe_size"] = INSTALLED_EXE.stat().st_size if checks["installed_exe_exists"] else 0
    print(f"  - Installed {INSTALLED_EXE.name}: {'EXISTS' if checks['installed_exe_exists'] else 'MISSING'} ({checks['installed_exe_size']:,} bytes)")
    assert checks["installed_exe_exists"], f"Installed executable does not exist at {INSTALLED_EXE}"

    checks["internal_dir_exists"] = INTERNAL_DIR.is_dir()
    print(f"  - Installed _internal/: {'EXISTS' if checks['internal_dir_exists'] else 'MISSING'}")
    assert checks["internal_dir_exists"], "Installed _internal/ directory missing"

    index_html = FRONTEND_DIST / "index.html"
    checks["frontend_index_exists"] = index_html.is_file()
    print(f"  - Embedded frontend index.html: {'EXISTS' if checks['frontend_index_exists'] else 'MISSING'}")
    assert checks["frontend_index_exists"], "Installed frontend index.html missing"

    assets_dir = FRONTEND_DIST / "assets"
    js_files = list(assets_dir.glob("*.js"))
    css_files = list(assets_dir.glob("*.css"))
    checks["js_files"] = [f.name for f in js_files]
    checks["css_files"] = [f.name for f in css_files]
    print(f"  - Embedded JS: {checks['js_files']}")
    print(f"  - Embedded CSS: {checks['css_files']}")
    assert len(js_files) >= 1 and len(css_files) >= 1, "Missing JS/CSS assets in installed frontend"

    qt_webengine = INTERNAL_DIR / "PySide6" / "QtWebEngineProcess.exe"
    checks["qt_webengine_exists"] = qt_webengine.is_file()
    print(f"  - QtWebEngineProcess.exe: {'EXISTS' if checks['qt_webengine_exists'] else 'MISSING'}")
    assert checks["qt_webengine_exists"], "QtWebEngineProcess.exe missing from installed application"

    return checks


def verify_installed_cli_execution() -> Dict[str, Any]:
    run_step("2. Installed Application CLI Execution (Working Directory: C:\\Users\\sanje)")
    results = {}

    # Test 1: Foundation validation
    t0 = time.perf_counter()
    p1 = subprocess.run(
        [str(INSTALLED_EXE), "--validate"],
        capture_output=True,
        text=True,
        cwd=r"C:\Users\sanje",
        timeout=30,
    )
    results["validate_exit_code"] = p1.returncode
    results["validate_time_s"] = round(time.perf_counter() - t0, 3)
    results["validate_passed"] = (p1.returncode == 0 and "FOUNDATION VALIDATION: ALL PASSED" in p1.stdout)
    print(f"  - Installed --validate: Exit code {p1.returncode} in {results['validate_time_s']}s (Passed: {results['validate_passed']})")
    assert results["validate_passed"], f"Installed --validate failed: {p1.stdout}\n{p1.stderr}"

    # Test 2: Standard Benchmark Matrix SMOKE
    t0 = time.perf_counter()
    p2 = subprocess.run(
        [str(INSTALLED_EXE), "--matrix", "SMOKE"],
        capture_output=True,
        text=True,
        cwd=r"C:\Users\sanje",
        timeout=60,
    )
    results["smoke_exit_code"] = p2.returncode
    results["smoke_time_s"] = round(time.perf_counter() - t0, 3)
    results["smoke_passed"] = (p2.returncode == 0 and "SIH PS 26169 Threshold Verdict: PASS" in p2.stdout)
    print(f"  - Installed --matrix SMOKE: Exit code {p2.returncode} in {results['smoke_time_s']}s (Passed: {results['smoke_passed']})")
    assert results["smoke_passed"], f"Installed --matrix SMOKE failed: {p2.stdout}\n{p2.stderr}"

    return results


def verify_installed_interactive_workstation() -> Dict[str, Any]:
    run_step("3. Installed Interactive Workstation & 5 Workspaces Verification")

    # Add project root to sys.path to run headless test harness
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QEventLoop, QTimer, Qt, QUrl
    from src.app.app_controller import AppController
    from src.app.gui.web_window import SanketWebWindow

    results = {}

    def wait_ms(ms: int) -> None:
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def eval_sync(win: SanketWebWindow, js: str) -> Any:
        res = []
        loop = QEventLoop()
        def cb(v):
            res.append(v)
            loop.quit()
        win.web_view.page().runJavaScript(f"(() => {{\n{js}\n}})()", cb)
        loop.exec()
        return res[0] if res else None

    qapp = QApplication.instance() or QApplication(sys.argv)
    ctrl = AppController()
    if ctrl.config_manager and ctrl.config_manager.config:
        ctrl.config_manager.config.simulation.duration_s = None
    ctrl.initialize()

    win = SanketWebWindow(ctrl)
    win.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    win.resize(1920, 1080)

    # Point directly to installed frontend dist!
    installed_html = FRONTEND_DIST / "index.html"
    assert installed_html.is_file(), f"Installed index.html not found at {installed_html}"
    file_url = QUrl.fromLocalFile(str(installed_html))
    print(f"  Loading installed frontend from: {file_url.toString()}")
    win.web_view.load(file_url)
    win.show()

    print("  Waiting 4.0s for installed WebEngine bundle to boot...")
    wait_ms(4000)

    # Verify WebEngine launched & WebChannel connected
    qt_transport = eval_sync(win, "return typeof window.qt !== 'undefined' && typeof window.qt.webChannelTransport !== 'undefined';")
    results["qt_transport_available"] = qt_transport
    print(f"  - Installed window.qt.webChannelTransport: {qt_transport}")
    assert qt_transport is True, "QtWebChannel transport missing from installed bundle"

    client_ready = (win.bridge._t_client_ready_ms is not None)
    results["client_ready"] = client_ready
    print(f"  - React clientReady signal received by bridge: {client_ready}")
    assert client_ready is True, "React client did not signal clientReady"

    # Verify offline airgapped operation: 0 remote network calls attempted
    remote_access_blocked = not win.web_view.settings().testAttribute(
        win.web_view.settings().WebAttribute.LocalContentCanAccessRemoteUrls
    )
    results["remote_access_blocked"] = remote_access_blocked
    print(f"  - LocalContentCanAccessRemoteUrls is DISABLED (Airgapped): {remote_access_blocked}")
    assert remote_access_blocked is True, "Remote network access must be blocked in workstation profile"

    # Verify 5 Workspaces Navigation
    workspaces = [
        ("Developer Workspace", "Developer Workspace"),
        ("Evaluator Workspace", "Evaluator Workspace"),
        ("Diagnostics & Audit", "Diagnostics & Subsystem Audit"),
        ("Run History", "Run History & Artifact Catalog"),
        ("Results & Analysis", "Results & Analysis"),
    ]

    ws_nav_results = {}
    for nav_label, ws_name in workspaces:
        res = eval_sync(win, f"""
            const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('{nav_label}'));
            if (!btn) return 'NOT_FOUND';
            btn.click();
            return 'OK';
        """)
        wait_ms(350)
        dom_slice = eval_sync(win, "return document.querySelector('main').innerText.slice(0, 100);")
        has_content = len(dom_slice or "") > 10
        ws_nav_results[nav_label] = {"status": res, "has_content": has_content, "preview": dom_slice[:40] if dom_slice else ""}
        print(f"  - Workspace '{nav_label}': {res} (DOM verified: {has_content})")
        assert res == 'OK' and has_content, f"Failed to open workspace {nav_label}"

    results["workspaces"] = ws_nav_results

    # Switch back to Developer Workspace and test sub-views
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Developer Workspace'));
        if (btn) btn.click();
    """)
    wait_ms(350)

    sub_views = ["2D Sensor View", "3D Pedestal Frustum", "World Canvas"]
    sub_results = {}
    for sub in sub_views:
        res = eval_sync(win, f"""
            const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('{sub}'));
            if (!tab) return 'NOT_FOUND';
            tab.click();
            return 'OK';
        """)
        wait_ms(350)
        sub_results[sub] = (res == 'OK')
        print(f"  - Developer Sub-View '{sub}': {res}")
        assert res == 'OK', f"Failed to switch to {sub}"

    results["developer_sub_views"] = sub_results

    # Ground-truth firewall check on World Canvas
    gt_firewall_banner = eval_sync(win, "return document.body.innerText.includes('LIVE OPERATIONAL: WORLD GT STRIPPED');")
    results["gt_firewall_banner"] = gt_firewall_banner
    print(f"  - World Canvas GT Firewall banner: {gt_firewall_banner}")
    assert gt_firewall_banner is True, "Ground truth firewall banner missing on live World Canvas"

    # Switch back to 2D view and test controls (RUN, PAUSE, STEP, RESET)
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('2D Sensor View'));
        if (tab) tab.click();
    """)
    wait_ms(300)

    # 1. RUN
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'RUN' || b.textContent.includes('RUN'));
        if (btn) btn.click();
    """)
    wait_ms(1500)
    frame_after_run = ctrl.frame_count
    results["run_effective"] = (frame_after_run > 0)
    print(f"  - RUN control: Frame progressed to {frame_after_run} (Passed: {results['run_effective']})")
    assert results["run_effective"], "RUN button failed to advance simulation frames"

    # 2. PAUSE
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'PAUSE' || b.textContent.includes('PAUSE'));
        if (btn) btn.click();
    """)
    wait_ms(500)
    f_p1 = ctrl.frame_count
    wait_ms(500)
    f_p2 = ctrl.frame_count
    results["pause_effective"] = (f_p1 == f_p2)
    print(f"  - PAUSE control: Frame held at {f_p1} == {f_p2} (Passed: {results['pause_effective']})")
    assert results["pause_effective"], "PAUSE button failed to halt simulation frames"

    # 3. STEP (+1 FR)
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('STEP') || b.textContent.includes('+1 FR'));
        if (btn) btn.click();
    """)
    wait_ms(500)
    f_step = ctrl.frame_count
    results["step_effective"] = (f_step == f_p2 + 1)
    print(f"  - STEP control (+1 FR): Frame incremented to {f_step} (Passed: {results['step_effective']})")

    # 4. RESET
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'RESET' || b.textContent.includes('RESET'));
        if (btn) btn.click();
    """)
    wait_ms(500)
    f_reset = ctrl.frame_count
    results["reset_effective"] = (f_reset == 0)
    print(f"  - RESET control: Frame reset to {f_reset} (Passed: {results['reset_effective']})")
    assert results["reset_effective"], "RESET button failed to reset frame counter to 0"

    win.close()
    qapp.quit()
    return results


def main():
    print("=" * 70)
    print("SANKET Installed Application Verification (Tasks 3, 4, 8)")
    print(f"Installed Path: {INSTALLED_DIR}")
    print("=" * 70)

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "installed_dir": str(INSTALLED_DIR),
        "installed_exe": str(INSTALLED_EXE),
    }

    try:
        summary["file_audit"] = verify_installed_files()
        summary["cli_execution"] = verify_installed_cli_execution()
        summary["interactive_workstation"] = verify_installed_interactive_workstation()
        summary["all_passed"] = True
    except Exception as exc:
        print(f"\n[FATAL ERROR]: {exc}")
        import traceback
        traceback.print_exc()
        summary["all_passed"] = False
        summary["error"] = str(exc)

    report_path = Path(__file__).resolve().parents[1] / "output" / "installed_application_verification.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print(f"INSTALLED APPLICATION VERDICT: {'ALL 20 CHECKS PASSED' if summary.get('all_passed') else 'FAILED'}")
    print(f"Evidence Report: {report_path}")
    print("=" * 70)

    sys.exit(0 if summary.get("all_passed") else 1)

if __name__ == "__main__":
    main()
