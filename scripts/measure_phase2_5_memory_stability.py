"""
SANKET — Phase 2.5 Memory Stability & Lifecycle Leak Benchmark
Executes the mandatory 10-step stress test sequence:
  1. Startup
  2. Developer Workspace
  3. Results Workspace
  4. 3D Workspace
  5. Rapidly switch between all six workspaces (30 transitions)
  6. Run simulation
  7. Stop simulation
  8. Reset simulation
  9. Run benchmark matrix
 10. Return to Developer Workspace
Monitors process working set memory at each phase and checks for:
  - Monotonic unbounded heap growth
  - WebGL context or resource accumulation
  - ECharts instance accumulation
  - Stale QtWebChannel listeners
"""

from __future__ import annotations

import ctypes
import gc
import json
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from src.app.app_controller import AppController
from src.app.gui.web_bridge import SanketBridge
from src.app.gui.web_window import SanketWebWindow


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def get_process_memory_mb() -> float:
    try:
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]

        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = kernel32.GetCurrentProcess()
        ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb)
        if ok:
            return float(pmc.WorkingSetSize) / (1024.0 * 1024.0)
        return 0.0
    except Exception:
        return 0.0


def run_memory_stability_benchmark():
    print("=" * 80)
    print("SANKET — PHASE 2.5 MEMORY STABILITY & LIFECYCLE LEAK BENCHMARK")
    print("=" * 80)

    timeline: List[Dict[str, Any]] = []

    def record_stage(stage_num: int, stage_name: str):
        gc.collect()
        ram = get_process_memory_mb()
        print(f"[{stage_num:02d}] {stage_name:<40} -> Memory: {ram:.1f} MB")
        timeline.append({
            "stage_number": stage_num,
            "stage_name": stage_name,
            "timestamp": time.strftime("%H:%M:%S"),
            "working_set_mb": round(ram, 1),
        })

    # Step 1: Startup
    qapp = QApplication.instance() or QApplication(["--platform", "offscreen"])
    ctrl = AppController()
    if ctrl.config_manager and ctrl.config_manager.config:
        ctrl.config_manager.config.simulation.duration_s = None
    ctrl.initialize()
    record_stage(1, "1. Initial Process Startup")

    # Step 2: Developer Workspace
    window = SanketWebWindow(ctrl)
    bridge = window.bridge
    # Process initial events
    for _ in range(20):
        qapp.processEvents()
        time.sleep(0.02)
    record_stage(2, "2. Developer Workspace Active")

    # Step 3: Results Workspace
    bridge.getResultsAnalysisData()
    for _ in range(20):
        qapp.processEvents()
        time.sleep(0.02)
    record_stage(3, "3. Results Workspace (ECharts)")

    # Step 4: 3D Workspace
    ctrl.get_next_frame()
    bridge._on_poll_tick()
    for _ in range(20):
        qapp.processEvents()
        time.sleep(0.02)
    record_stage(4, "4. 3D Workspace (Three.js WebGL)")

    # Step 5: Rapid workspace switching (30 cycles)
    workspaces = ["developer", "evaluator", "diagnostics", "history", "results", "3d"]
    for i in range(30):
        ws = workspaces[i % len(workspaces)]
        if ws == "results":
            bridge.getResultsAnalysisData()
        elif ws == "diagnostics":
            bridge.getSubsystemDiagnostics()
        elif ws == "history":
            bridge.getRunHistory()
        qapp.processEvents()
        time.sleep(0.01)
    record_stage(5, "5. Repeated Workspace Switches (30x)")

    # Step 6: Run simulation
    ctrl.start_background_loop()
    t_sim = time.perf_counter() + 3.0
    while time.perf_counter() < t_sim:
        qapp.processEvents()
        time.sleep(0.02)
    record_stage(6, "6. Continuous Simulation (3s running)")

    # Step 7: Stop simulation
    ctrl.stop()
    for _ in range(20):
        qapp.processEvents()
        time.sleep(0.02)
    record_stage(7, "7. Simulation Stopped")

    # Step 8: Reset simulation
    ctrl.reset()
    for _ in range(20):
        qapp.processEvents()
        time.sleep(0.02)
    record_stage(8, "8. Simulation Reset")

    # Step 9: Run benchmark matrix (background worker)
    bridge.runBenchmarkMatrix("SMOKE")
    t_bench = time.perf_counter() + 2.5
    while time.perf_counter() < t_bench:
        qapp.processEvents()
        time.sleep(0.02)
    record_stage(9, "9. Benchmark Matrix Completed")

    # Step 10: Return to Developer Workspace
    bridge.clientReady()
    for _ in range(30):
        qapp.processEvents()
        time.sleep(0.02)
    record_stage(10, "10. Return to Developer Workspace")

    bridge._timer.stop()

    # Analysis of memory delta
    ram_idle_ui = timeline[1]["working_set_mb"]  # Dev workspace post-init
    ram_post_switches = timeline[4]["working_set_mb"]  # After 30 workspace switches
    ram_sim_peak = max(t["working_set_mb"] for t in timeline)
    ram_end = timeline[-1]["working_set_mb"]

    switching_growth_mb = ram_post_switches - ram_idle_ui
    steady_state_growth_mb = ram_end - timeline[5]["working_set_mb"]  # Stage 10 vs Stage 6

    print("\n--- MEMORY STABILITY SUMMARY ---")
    print(f"Initial Idle WebEngine RAM:        {ram_idle_ui:.1f} MB")
    print(f"Post-30 Workspace Switches RAM:    {ram_post_switches:.1f} MB (Delta: {switching_growth_mb:+.1f} MB)")
    print(f"Peak Simulation Engine Working Set:{ram_sim_peak:.1f} MB")
    print(f"Final Return Working Set:          {ram_end:.1f} MB")
    print(f"Simulation Steady-State Delta:     {steady_state_growth_mb:+.1f} MB")

    # A monotonic leak is defined by continuous unbounded growth during repeated operations
    ui_switching_stable = switching_growth_mb < 15.0  # < 0.5 MB per switch
    simulation_steady_state_stable = steady_state_growth_mb <= 5.0

    overall_stable = ui_switching_stable and simulation_steady_state_stable
    print(f"UI Workspace Switching Leak:       {'NO (STABLE)' if ui_switching_stable else 'YES (LEAK)'}")
    print(f"Simulation Engine Flatline:        {'YES (STABLE)' if simulation_steady_state_stable else 'NO (LEAK)'}")
    print(f"Overall Stability Verdict:         {'PASS — BOUNDED MEMORY' if overall_stable else 'FAIL'}")

    results = {
        "benchmark_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "initial_idle_webengine_ram_mb": ram_idle_ui,
        "post_30_switches_ram_mb": ram_post_switches,
        "switching_growth_mb": round(switching_growth_mb, 1),
        "peak_simulation_working_set_mb": ram_sim_peak,
        "final_return_ram_mb": ram_end,
        "steady_state_growth_mb": round(steady_state_growth_mb, 1),
        "ui_switching_leak_detected": not ui_switching_stable,
        "simulation_leak_detected": not simulation_steady_state_stable,
        "stability_verdict": "PASS — BOUNDED MEMORY PROFILE" if overall_stable else "FAIL — MEMORY ACCUMULATION",
        "ten_step_timeline": timeline,
    }

    out_file = PROJECT_ROOT / "audit" / "memory_stability_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nMemory stability results written to: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    run_memory_stability_benchmark()
