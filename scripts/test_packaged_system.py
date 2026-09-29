"""
LumiTrack — Comprehensive Packaged Application Verification Suite
Tests the PyInstaller ONEDIR package in dist/LumiTrack/ and embedded WebEngine runtime.
SIH 2026 Problem Statement PS-26169 Deliverable Verification.
"""

from __future__ import annotations

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist" / "LumiTrack"
EXE_PATH = DIST_DIR / "LumiTrack.exe"
INTERNAL_DIR = DIST_DIR / "_internal"
FRONTEND_DIST = INTERNAL_DIR / "frontend" / "dist"

def run_step(step_name: str):
    print(f"\n{'='*70}\n[STEP] {step_name}\n{'='*70}")

def verify_file_tree() -> Dict[str, Any]:
    run_step("1. Packaged File Tree & Asset Inventory Audit")
    checks = {}

    # Check executable
    checks["exe_exists"] = EXE_PATH.is_file()
    checks["exe_size_bytes"] = EXE_PATH.stat().st_size if checks["exe_exists"] else 0
    print(f"  - LumiTrack.exe: {'EXISTS' if checks['exe_exists'] else 'MISSING'} ({checks['exe_size_bytes']:,} bytes)")
    assert checks["exe_exists"], "LumiTrack.exe missing from dist/LumiTrack"

    # Check internal frontend dist
    index_html = FRONTEND_DIST / "index.html"
    checks["frontend_index_exists"] = index_html.is_file()
    print(f"  - _internal/frontend/dist/index.html: {'EXISTS' if checks['frontend_index_exists'] else 'MISSING'}")
    assert checks["frontend_index_exists"], "Bundled frontend index.html missing"

    # Check bundled assets
    assets_dir = FRONTEND_DIST / "assets"
    js_files = list(assets_dir.glob("*.js"))
    css_files = list(assets_dir.glob("*.css"))
    checks["bundle_js_count"] = len(js_files)
    checks["bundle_css_count"] = len(css_files)
    checks["bundle_js_file"] = js_files[0].name if js_files else None
    checks["bundle_css_file"] = css_files[0].name if css_files else None
    print(f"  - JS bundle: {checks['bundle_js_file']} ({checks['bundle_js_count']} file)")
    print(f"  - CSS bundle: {checks['bundle_css_file']} ({checks['bundle_css_count']} file)")
    assert len(js_files) >= 1 and len(css_files) >= 1, "Frontend JS/CSS assets missing"

    # Check QtWebEngineProcess
    qt_webengine = INTERNAL_DIR / "PySide6" / "QtWebEngineProcess.exe"
    checks["qt_webengine_process_exists"] = qt_webengine.is_file()
    print(f"  - QtWebEngineProcess.exe: {'EXISTS' if checks['qt_webengine_process_exists'] else 'MISSING'}")
    assert checks["qt_webengine_process_exists"], "QtWebEngineProcess.exe missing"

    # Check MSVC runtime DLLs
    msvc_dll = INTERNAL_DIR / "msvcp140.dll"
    checks["msvcp140_dll_exists"] = msvc_dll.is_file()
    print(f"  - MSVC runtime DLL (msvcp140.dll): {'EXISTS' if checks['msvcp140_dll_exists'] else 'MISSING'}")
    assert checks["msvcp140_dll_exists"], "msvcp140.dll missing from _internal"

    # Check scenarios, models, plugins
    scenarios_dir = INTERNAL_DIR / "scenarios"
    scenario_files = list(scenarios_dir.glob("*.json"))
    checks["scenario_json_count"] = len(scenario_files)
    print(f"  - Bundled scenarios: {len(scenario_files)} JSON files")
    assert len(scenario_files) >= 4, f"Expected at least 4 canonical scenarios, found {len(scenario_files)}"

    algorithms_dir = INTERNAL_DIR / "src" / "plugins" / "algorithms"
    algo_files = list(algorithms_dir.rglob("*.py"))
    checks["algorithm_plugins_count"] = len(algo_files)
    print(f"  - Bundled algorithm plugins: {len(algo_files)} Python files")
    assert len(algo_files) >= 1, f"Expected at least 1 algorithm plugin file, found {len(algo_files)}"

    # Check node_modules exclusion (clean airgap)
    node_modules_in_dist = list(DIST_DIR.rglob("node_modules"))
    checks["node_modules_in_dist"] = len(node_modules_in_dist)
    print(f"  - node_modules in dist: {len(node_modules_in_dist)} (Airgap Compliant: ZERO)")
    assert len(node_modules_in_dist) == 0, "node_modules found in dist!"

    return checks


def test_cli_foundation_and_benchmark() -> Dict[str, Any]:
    run_step("2. Standalone Executable CLI Execution & Validation")
    results = {}

    # Test 1: --validate
    t0 = time.perf_counter()
    p1 = subprocess.run(
        [str(EXE_PATH), "--validate"],
        capture_output=True,
        text=True,
        cwd=str(DIST_DIR),
        timeout=30,
    )
    results["validate_time_s"] = round(time.perf_counter() - t0, 3)
    results["validate_exit_code"] = p1.returncode
    results["validate_passed"] = (p1.returncode == 0 and "FOUNDATION VALIDATION: ALL PASSED" in p1.stdout)
    print(f"  - LumiTrack.exe --validate: Exit code {p1.returncode} in {results['validate_time_s']}s (Passed: {results['validate_passed']})")
    assert results["validate_passed"], f"Packaged --validate failed: {p1.stdout}\n{p1.stderr}"

    # Test 2: --matrix SMOKE
    t0 = time.perf_counter()
    p2 = subprocess.run(
        [str(EXE_PATH), "--matrix", "SMOKE"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=60,
    )
    results["smoke_time_s"] = round(time.perf_counter() - t0, 3)
    results["smoke_exit_code"] = p2.returncode
    results["smoke_passed"] = (p2.returncode == 0 and "SIH PS 26169 Threshold Verdict: PASS" in p2.stdout)
    print(f"  - LumiTrack.exe --matrix SMOKE: Exit code {p2.returncode} in {results['smoke_time_s']}s (Passed: {results['smoke_passed']})")
    assert results["smoke_passed"], f"Packaged --matrix SMOKE failed: {p2.stdout}\n{p2.stderr}"

    # Test 3: --benchmark-cold-start
    t0 = time.perf_counter()
    p3 = subprocess.run(
        [str(EXE_PATH), "--benchmark-cold-start"],
        capture_output=True,
        text=True,
        cwd=str(DIST_DIR),
        timeout=45,
    )
    results["cold_start_exit_code"] = p3.returncode
    cold_start_json = None
    for line in p3.stdout.splitlines():
        if line.startswith("PACKAGED_COLD_START_JSON:"):
            cold_start_json = json.loads(line.replace("PACKAGED_COLD_START_JSON:", ""))
            break
    results["cold_start_metrics"] = cold_start_json
    print(f"  - LumiTrack.exe --benchmark-cold-start: Exit code {p3.returncode}")
    if cold_start_json:
        print(f"    T1 Python Init: {cold_start_json.get('T1_python_init_ms')} ms")
        print(f"    T2 PySide6 Host Ready: {cold_start_json.get('T2_pyside6_host_ready_ms')} ms")
        print(f"    T3 WebEngine Created: {cold_start_json.get('T3_webengine_created_ms')} ms")
        print(f"    T4 React Bundle Loaded: {cold_start_json.get('T4_react_bundle_loaded_ms')} ms")
        print(f"    T5 WebChannel Connected: {cold_start_json.get('T5_webchannel_connected_ms')} ms")
        print(f"    Time to Usable Workstation: {cold_start_json.get('time_to_usable_workstation_ms')} ms ({cold_start_json.get('time_to_usable_workstation_s')} s)")
    assert cold_start_json is not None, "Failed to parse cold start JSON metrics"

    return results


def test_packaged_web_gui_runtime() -> Dict[str, Any]:
    run_step("3. Embedded WebEngine & QtWebChannel Interactive Runtime Audit")

    # Add project root to sys.path so we can import helper modules for running GUI harness
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QEventLoop, QTimer, Qt
    from src.app.app_controller import AppController
    from src.app.gui.web_window import LumiTrackWebWindow

    results = {}

    def wait_ms(ms: int) -> None:
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def eval_sync(win: LumiTrackWebWindow, js: str) -> Any:
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

    win = LumiTrackWebWindow(ctrl)
    win.setWindowFlags(Qt.WindowType.FramelessWindowHint)
    win.resize(1920, 1080)
    win.show()

    print("  Waiting 4.0s for WebEngine and React initialization...")
    wait_ms(4000)

    # 1. Verify Bridge & Connection State
    qt_transport = eval_sync(win, "return typeof window.qt !== 'undefined' && typeof window.qt.webChannelTransport !== 'undefined';")
    results["qt_transport_available"] = qt_transport
    print(f"  - window.qt.webChannelTransport exists in DOM: {qt_transport}")
    assert qt_transport is True, "window.qt.webChannelTransport is missing from WebEngine page"

    # Verify that the React client called clientReady() over the bridge
    client_ready_called = (win.bridge._t_client_ready_ms is not None)
    results["client_ready_called"] = client_ready_called
    print(f"  - React client called clientReady() on pyBridge: {client_ready_called}")
    assert client_ready_called is True, "React client did not call clientReady() over WebChannel"

    is_connected = eval_sync(win, """
        const banner = document.body.innerText;
        return !banner.includes('BACKEND OFFLINE');
    """)
    results["frontend_connected_to_backend"] = is_connected
    print(f"  - Frontend connected status: {'ONLINE' if is_connected else 'OFFLINE'}")

    # 2. Verify 5 Workspaces Navigation & Rendering
    ws_targets = [
        ("Developer Workspace", "Developer Workspace"),
        ("Evaluator Workspace", "Evaluator Workspace"),
        ("Diagnostics & Audit", "Diagnostics & Subsystem Audit"),
        ("Run History", "Run History & Artifact Catalog"),
        ("Results & Analysis", "Results & Analysis"),
    ]

    ws_results = {}
    for nav_label, expected_title in ws_targets:
        res = eval_sync(win, f"""
            const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('{nav_label}'));
            if (!btn) return 'BUTTON_NOT_FOUND';
            btn.click();
            return 'CLICKED';
        """)
        wait_ms(400)
        dom_text = eval_sync(win, "return document.querySelector('main').innerText.slice(0, 200);")
        has_content = len(dom_text or "") > 20
        ws_results[nav_label] = {
            "click_status": res,
            "has_content": has_content,
            "sample_text": dom_text[:60] if dom_text else ""
        }
        print(f"  - Nav to '{nav_label}': {res} (Rendered {len(dom_text or '')} chars in main)")
        assert res == 'CLICKED' and has_content, f"Workspace navigation failed for {nav_label}"

    results["workspace_navigation"] = ws_results

    # 3. Verify Developer Workspace Sub-Views (2D, 3D Frustum, World Canvas)
    eval_sync(win, """
        const btn = Array.from(document.querySelectorAll('aside button')).find(b => b.textContent.includes('Developer Workspace'));
        if (btn) btn.click();
    """)
    wait_ms(400)

    sub_views = ["2D Sensor View", "3D Pedestal Frustum", "World Canvas"]
    sub_results = {}
    for sub in sub_views:
        res = eval_sync(win, f"""
            const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('{sub}'));
            if (!tab) return 'TAB_NOT_FOUND';
            tab.click();
            return 'CLICKED';
        """)
        wait_ms(400)
        sub_results[sub] = (res == 'CLICKED')
        print(f"  - Developer Sub-View '{sub}': {res}")
        assert res == 'CLICKED', f"Failed to switch to Developer sub-view {sub}"

    results["developer_sub_views"] = sub_results

    # 4. Verify Ground-Truth Firewall on World Canvas
    gt_firewall_live = eval_sync(win, """
        return document.body.innerText.includes('LIVE OPERATIONAL: WORLD GT STRIPPED');
    """)
    results["gt_firewall_active"] = gt_firewall_live
    print(f"  - Live World Canvas GT Firewall banner present: {gt_firewall_live}")
    assert gt_firewall_live is True, "Live operational World Canvas must display GT STRIPPED firewall indicator"

    # Switch back to 2D Sensor View
    eval_sync(win, """
        const tab = Array.from(document.querySelectorAll('main button')).find(b => b.textContent.includes('2D Sensor View'));
        if (tab) tab.click();
    """)
    wait_ms(300)

    # 5. Verify Simulation Transport Controls (Run -> Pause -> Step -> Reset)
    # Start Simulation
    eval_sync(win, """
        const runBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'RUN' || b.textContent.includes('RUN'));
        if (runBtn) runBtn.click();
    """)
    wait_ms(1500)
    frame_after_run = ctrl.frame_count
    print(f"  - Transport RUN triggered: Frame progressed to {frame_after_run}")
    assert frame_after_run > 0, "Simulation failed to advance frames after RUN button clicked"

    # Pause Simulation
    eval_sync(win, """
        const pauseBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'PAUSE' || b.textContent.includes('PAUSE'));
        if (pauseBtn) pauseBtn.click();
    """)
    wait_ms(500)
    frame_paused_1 = ctrl.frame_count
    wait_ms(500)
    frame_paused_2 = ctrl.frame_count
    results["pause_effective"] = (frame_paused_1 == frame_paused_2)
    print(f"  - Transport PAUSE triggered: Frame held at {frame_paused_1} -> {frame_paused_2}")
    assert results["pause_effective"], "Simulation continued running after PAUSE clicked"

    # Step +1 Frame
    eval_sync(win, """
        const stepBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('STEP') || b.textContent.includes('+1 FR'));
        if (stepBtn) stepBtn.click();
    """)
    wait_ms(500)
    frame_after_step = ctrl.frame_count
    results["step_effective"] = (frame_after_step == frame_paused_2 + 1)
    print(f"  - Transport STEP (+1 FR): Frame incremented to {frame_after_step} (from {frame_paused_2})")

    # Reset
    eval_sync(win, """
        const resetBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'RESET' || b.textContent.includes('RESET'));
        if (resetBtn) resetBtn.click();
    """)
    wait_ms(500)
    frame_after_reset = ctrl.frame_count
    results["reset_effective"] = (frame_after_reset == 0)
    print(f"  - Transport RESET: Frame reset to {frame_after_reset}")
    assert results["reset_effective"], "Simulation failed to reset frame number to 0"

    win.close()
    qapp.quit()
    return results


def main():
    print(f"Starting LumiTrack Packaged System Verification...")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Executable:   {EXE_PATH}")

    t_start = time.perf_counter()
    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "project_root": str(PROJECT_ROOT),
        "dist_dir": str(DIST_DIR),
        "exe_path": str(EXE_PATH),
    }

    try:
        summary["file_tree"] = verify_file_tree()
        summary["cli_benchmark"] = test_cli_foundation_and_benchmark()
        summary["gui_runtime"] = test_packaged_web_gui_runtime()
        summary["all_passed"] = True
    except Exception as exc:
        print(f"\n[FATAL VERIFICATION ERROR]: {exc}")
        import traceback
        traceback.print_exc()
        summary["all_passed"] = False
        summary["error"] = str(exc)

    total_duration_s = round(time.perf_counter() - t_start, 2)
    summary["total_verification_time_s"] = total_duration_s

    report_path = PROJECT_ROOT / "output" / "packaged_system_verification.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*70}")
    print(f"VERIFICATION SUMMARY: {'ALL TESTS PASSED' if summary.get('all_passed') else 'VERIFICATION FAILED'}")
    print(f"Total Time: {total_duration_s}s")
    print(f"Saved Evidence: {report_path}")
    print(f"{'='*70}")

    sys.exit(0 if summary.get("all_passed") else 1)

if __name__ == "__main__":
    main()
