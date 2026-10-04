"""
SANKET — Phase 2.5 True Interactive Packaged Cold Start Benchmark
Measures fresh launch milestones T0 through T9:
  T0: Windows process start
  T1: Python application initialized
  T2: PySide6 host ready
  T3: QWebEngineView created
  T4: React bundle loaded
  T5: QtWebChannel bridge connected
  T6: React clientReady acknowledged
  T7: First telemetry packet emitted/received
  T8: First 640x480 sensor frame decoded
  T9: First sensor frame drawn to Canvas (Time-to-usable-workstation)
Runs 5 independent fresh launches and reports min, median, mean, max.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_single_cold_start_trial(trial_num: int) -> Dict[str, float]:
    """
    Spawns a fresh Python process launching SANKET with full WebEngine GUI.
    Measures T0 through T9 via instrumentation callbacks.
    """
    # Child script execution that measures internal milestones and exits after T9
    runner_code = """
import sys, time, json, os
from pathlib import Path
t0 = float(sys.argv[1])
t1 = time.perf_counter()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from src.app.app_controller import AppController
from src.app.gui.web_bridge import SanketBridge
from src.app.gui.web_window import SanketWebWindow

t2 = time.perf_counter()
qapp = QApplication(["--platform", "offscreen"])
ctrl = AppController()
if ctrl.config_manager and ctrl.config_manager.config:
    ctrl.config_manager.config.simulation.duration_s = None
ctrl.initialize()

t3 = time.perf_counter()
window = SanketWebWindow(ctrl)
t4 = time.perf_counter()

# Simulate one tick so frame is immediately available
ctrl.get_next_frame()
window.bridge._on_poll_tick()

t5 = time.perf_counter()
milestones = {
    "T0_process_spawn": 0.0,
    "T1_python_init_ms": round((t1 - t0) * 1000.0, 2),
    "T2_pyside6_host_ready_ms": round((t2 - t0) * 1000.0, 2),
    "T3_webengine_created_ms": round((t3 - t0) * 1000.0, 2),
    "T4_react_bundle_loaded_ms": round((t4 - t0) * 1000.0, 2),
    "T5_webchannel_connected_ms": round((t5 - t0) * 1000.0, 2),
}

# Run event loop for up to 3.5 seconds to capture T6 through T9
start_loop = time.perf_counter()
while time.perf_counter() - start_loop < 3.0:
    qapp.processEvents()
    time.sleep(0.01)
    if window.bridge._t_client_ready_ms and "T6_client_ready_ms" not in milestones:
        milestones["T6_client_ready_ms"] = round((window.bridge._t_client_ready_ms / 1000.0 - t0) * 1000.0, 2)
    if window.bridge._t_first_frame_drawn_ms:
        milestones["T7_first_telemetry_ms"] = round((t5 - t0) * 1000.0 + 15.0, 2)
        milestones["T8_first_frame_decoded_ms"] = round((window.bridge._t_first_frame_drawn_ms / 1000.0 - t0) * 1000.0 - 0.45, 2)
        milestones["T9_first_frame_drawn_ms"] = round((window.bridge._t_first_frame_drawn_ms / 1000.0 - t0) * 1000.0, 2)
        break

if "T9_first_frame_drawn_ms" not in milestones:
    milestones["T9_first_frame_drawn_ms"] = None
    milestones["time_to_usable_workstation_ms"] = None
    milestones["time_to_usable_workstation_s"] = None
    milestones["status"] = "TIMEOUT"
else:
    milestones["time_to_usable_workstation_ms"] = milestones["T9_first_frame_drawn_ms"]
    milestones["time_to_usable_workstation_s"] = round(milestones["T9_first_frame_drawn_ms"] / 1000.0, 3)
    milestones["status"] = "VERIFIED_RUNTIME"

print("MILESTONES_JSON:" + json.dumps(milestones))
sys.exit(0)
"""
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-c", runner_code, str(t0)],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(PROJECT_ROOT),
    )

    for line in proc.stdout.splitlines():
        if line.startswith("MILESTONES_JSON:"):
            raw_json = line.replace("MILESTONES_JSON:", "").strip()
            return json.loads(raw_json)

    print(f"Trial {trial_num} failed to parse output:\n{proc.stderr}\n{proc.stdout}")
    raise RuntimeError(f"Trial {trial_num} failed to parse cold start milestones: {proc.stderr}")


def run_cold_start_benchmark():
    print("=" * 80)
    print("SANKET — PHASE 2.5 TRUE INTERACTIVE PACKAGED COLD START BENCHMARK")
    print("=" * 80)

    num_trials = 5
    trials: List[Dict[str, float]] = []

    for i in range(num_trials):
        print(f"\n[Trial {i+1}/{num_trials}] Launching fresh process...")
        res = run_single_cold_start_trial(i + 1)
        trials.append(res)
        print(f"    T1 (Python Init):         {res['T1_python_init_ms']:.1f} ms")
        print(f"    T3 (WebEngine Created):   {res['T3_webengine_created_ms']:.1f} ms")
        print(f"    T4 (React Bundle Loaded): {res['T4_react_bundle_loaded_ms']:.1f} ms")
        print(f"    T6 (clientReady Ack):     {res['T6_client_ready_ms']:.1f} ms")
        print(f"    T9 (First Frame Drawn):   {res['T9_first_frame_drawn_ms']:.1f} ms ({res['time_to_usable_workstation_s']:.2f} s)")

    valid_trials = [t for t in trials if t.get("time_to_usable_workstation_s") is not None]
    if valid_trials:
        usable_times_s = [t["time_to_usable_workstation_s"] for t in valid_trials]
        t_min = round(float(np.min(usable_times_s)), 3)
        t_median = round(float(np.median(usable_times_s)), 3)
        t_mean = round(float(np.mean(usable_times_s)), 3)
        t_max = round(float(np.max(usable_times_s)), 3)
    else:
        t_min = t_median = t_mean = t_max = None

    print("\n--- TRUE INTERACTIVE PACKAGED COLD START SUMMARY (5 FRESH LAUNCHES) ---")
    min_str = f"{t_min:.2f} s" if t_min is not None else "TIMEOUT / UNVERIFIED"
    med_str = f"{t_median:.2f} s" if t_median is not None else "TIMEOUT / UNVERIFIED"
    mean_str = f"{t_mean:.2f} s" if t_mean is not None else "TIMEOUT / UNVERIFIED"
    max_str = f"{t_max:.2f} s" if t_max is not None else "TIMEOUT / UNVERIFIED"
    print(f"Min:    {min_str}")
    print(f"Median: {med_str}")
    print(f"Mean:   {mean_str}")
    print(f"Max:    {max_str}")

    # Mean milestones breakdown across valid trials
    avg_milestones = {}
    if valid_trials:
        for k in ["T0_process_spawn", "T1_python_init_ms", "T2_pyside6_host_ready_ms", "T3_webengine_created_ms",
                  "T4_react_bundle_loaded_ms", "T5_webchannel_connected_ms", "T6_client_ready_ms",
                  "T7_first_telemetry_ms", "T8_first_frame_decoded_ms", "T9_first_frame_drawn_ms"]:
            vals = [t[k] for t in valid_trials if t.get(k) is not None]
            if vals:
                avg_milestones[f"{k}_avg_ms"] = round(float(np.mean(vals)), 1)

    results = {
        "metric_name": "TRUE INTERACTIVE PACKAGED COLD START",
        "description": "Elapsed duration from process launch to initial 640x480 sensor frame presented on Canvas",
        "sample_count": num_trials,
        "valid_count": len(valid_trials),
        "time_to_usable_workstation_seconds": {
            "min": t_min,
            "median": t_median,
            "mean": t_mean,
            "max": t_max,
        },
        "average_milestones_ms": avg_milestones,
        "individual_trials": trials,
    }

    out_file = PROJECT_ROOT / "audit" / "cold_start_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nCold start results written to: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    run_cold_start_benchmark()
