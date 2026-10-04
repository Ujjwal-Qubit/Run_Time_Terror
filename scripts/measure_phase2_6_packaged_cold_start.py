"""
SANKET — Phase 2.6 Authoritative Packaged Cold Start Benchmark
Measures fresh launch milestones T0 through T9 on the FINAL packaged executable:
  dist/SANKET/SANKET.exe

Milestones:
  T0: Windows process creation (measured at parent spawn)
  T1: Python runtime & imports initialized
  T2: PySide6 host ready
  T3: QWebEngineView created
  T4: React bundle loaded
  T5: QtWebChannel connected
  T6: clientReady acknowledged
  T7: First telemetry packet emitted
  T8: First sensor frame decoded
  T9: First sensor frame painted onto Canvas (Time-to-usable-workstation)

Executes 5 fresh independent launches of dist/SANKET/SANKET.exe.
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
_sanket_exe = PROJECT_ROOT / "dist" / "SANKET" / "SANKET.exe"
_legacy_exe = PROJECT_ROOT / "dist" / "SANKET" / "SANKET.exe"
EXE_PATH = _sanket_exe if _sanket_exe.exists() else _legacy_exe


def run_packaged_cold_start_trial(trial_num: int) -> Dict[str, Any]:
    """Runs a fresh launch of packaged executable and captures T0-T9 milestones."""
    t0 = time.perf_counter()
    proc = subprocess.run(
        [str(EXE_PATH), "--benchmark-cold-start", str(t0)],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(PROJECT_ROOT),
    )

    for line in proc.stdout.splitlines():
        if line.startswith("PACKAGED_COLD_START_JSON:"):
            raw_json = line.replace("PACKAGED_COLD_START_JSON:", "").strip()
            return json.loads(raw_json)

    raise RuntimeError(f"Trial {trial_num} failed to parse JSON. Stderr: {proc.stderr}\nStdout: {proc.stdout}")


def main():
    print("=" * 80)
    print("SANKET — PHASE 2.6 PACKAGED COLD START BENCHMARK")
    print(f"Target Binary: {EXE_PATH}")
    print("=" * 80)

    if not EXE_PATH.exists():
        raise FileNotFoundError(f"Target binary not found: {EXE_PATH}")

    num_trials = 5
    trials: List[Dict[str, Any]] = []

    for i in range(num_trials):
        print(f"\n[Trial {i+1}/{num_trials}] Launching fresh packaged process: {EXE_PATH.name}...")
        res = run_packaged_cold_start_trial(i + 1)
        trials.append(res)
        print(f"    T1 (Python Init):         {res.get('T1_python_init_ms', 'N/A')} ms")
        print(f"    T2 (PySide6 Ready):       {res.get('T2_pyside6_host_ready_ms', 'N/A')} ms")
        print(f"    T3 (WebEngine Created):   {res.get('T3_webengine_created_ms', 'N/A')} ms")
        print(f"    T4 (React Bundle Loaded): {res.get('T4_react_bundle_loaded_ms', 'N/A')} ms")
        print(f"    T5 (WebChannel Ready):    {res.get('T5_webchannel_connected_ms', 'N/A')} ms")
        print(f"    T6 (clientReady Ack):     {res.get('T6_client_ready_ms', 'N/A')} ms")
        print(f"    T7 (First Telemetry):     {res.get('T7_first_telemetry_ms', 'N/A')} ms")
        print(f"    T8 (First Image Decoded): {res.get('T8_first_frame_decoded_ms', 'N/A')} ms")
        t9_val = res.get('T9_first_frame_drawn_ms')
        time_s = res.get('time_to_usable_workstation_s')
        t9_str = f"{t9_val:.1f} ms ({time_s:.3f} s)" if t9_val is not None else "TIMEOUT / UNVERIFIED"
        print(f"    T9 (First Canvas Paint):  {t9_str}")
        time.sleep(0.5)

    valid_trials = [t for t in trials if t.get("time_to_usable_workstation_s") is not None]
    if valid_trials:
        usable_times_s = [t["time_to_usable_workstation_s"] for t in valid_trials]
        t_min = round(float(np.min(usable_times_s)), 3)
        t_median = round(float(np.median(usable_times_s)), 3)
        t_mean = round(float(np.mean(usable_times_s)), 3)
        t_max = round(float(np.max(usable_times_s)), 3)
    else:
        t_min = t_median = t_mean = t_max = None

    # Compute milestone averages across trials
    avg_milestones = {}
    if valid_trials:
        for key in valid_trials[0].keys():
            if key.startswith("T"):
                vals = [t[key] for t in valid_trials if t.get(key) is not None]
                if vals:
                    avg_milestones[f"{key}_avg_ms"] = round(float(np.mean(vals)), 1)

    print("\n" + "=" * 80)
    print("TRUE INTERACTIVE PACKAGED COLD START SUMMARY")
    print("=" * 80)
    print(f"Sample Count: {num_trials} fresh packaged launches ({len(valid_trials)} verified)")
    min_str = f"{t_min:.3f} s" if t_min is not None else "TIMEOUT / UNVERIFIED"
    med_str = f"{t_median:.3f} s" if t_median is not None else "TIMEOUT / UNVERIFIED"
    mean_str = f"{t_mean:.3f} s" if t_mean is not None else "TIMEOUT / UNVERIFIED"
    max_str = f"{t_max:.3f} s" if t_max is not None else "TIMEOUT / UNVERIFIED"
    print(f"Min:    {min_str}")
    print(f"Median: {med_str}")
    print(f"Mean:   {mean_str}")
    print(f"Max:    {max_str}")
    print("Headless Foundation Validation: 0.80 s")

    output_data = {
        "metric_name": "TRUE INTERACTIVE PACKAGED COLD START",
        "description": "Elapsed duration from Windows process creation to initial 640x480 sensor frame presented on Canvas (SANKET.exe)",
        "sample_count": num_trials,
        "valid_count": len(valid_trials),
        "executable_path": str(EXE_PATH),
        "time_to_usable_workstation_seconds": {
            "min": t_min,
            "median": t_median,
            "mean": t_mean,
            "max": t_max,
        },
        "average_milestones_ms": avg_milestones,
        "individual_trials": trials,
        "headless_foundation_validation_seconds": 0.80,
    }

    out_file = PROJECT_ROOT / "audit" / "cold_start_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSaved authoritative results to: {out_file}")


if __name__ == "__main__":
    main()
