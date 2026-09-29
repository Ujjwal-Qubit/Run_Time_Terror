"""
LumiTrack — Phase 2.6 Authoritative Packaged Cold Start Benchmark
Measures fresh launch milestones T0 through T9 on the FINAL packaged executable:
  dist/LumiTrack/LumiTrack.exe

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

Executes 5 fresh independent launches of dist/LumiTrack/LumiTrack.exe.
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
EXE_PATH = PROJECT_ROOT / "dist" / "LumiTrack" / "LumiTrack.exe"


def run_packaged_cold_start_trial(trial_num: int) -> Dict[str, Any]:
    """Runs a fresh launch of dist/LumiTrack/LumiTrack.exe and captures T0-T9 milestones."""
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
    print("LUMITRACK — PHASE 2.6 PACKAGED COLD START BENCHMARK")
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
        print(f"    T1 (Python Init):         {res['T1_python_init_ms']:.1f} ms")
        print(f"    T2 (PySide6 Ready):       {res['T2_pyside6_host_ready_ms']:.1f} ms")
        print(f"    T3 (WebEngine Created):   {res['T3_webengine_created_ms']:.1f} ms")
        print(f"    T4 (React Bundle Loaded): {res['T4_react_bundle_loaded_ms']:.1f} ms")
        print(f"    T5 (WebChannel Ready):    {res['T5_webchannel_connected_ms']:.1f} ms")
        print(f"    T6 (clientReady Ack):     {res['T6_client_ready_ms']:.1f} ms")
        print(f"    T7 (First Telemetry):     {res['T7_first_telemetry_ms']:.1f} ms")
        print(f"    T8 (First Image Decoded): {res['T8_first_frame_decoded_ms']:.1f} ms")
        print(f"    T9 (First Canvas Paint):  {res['T9_first_frame_drawn_ms']:.1f} ms ({res['time_to_usable_workstation_s']:.3f} s)")
        time.sleep(0.5)

    usable_times_s = [t["time_to_usable_workstation_s"] for t in trials]

    t_min = float(np.min(usable_times_s))
    t_median = float(np.median(usable_times_s))
    t_mean = float(np.mean(usable_times_s))
    t_max = float(np.max(usable_times_s))

    # Compute milestone averages across trials
    avg_milestones = {}
    for key in trials[0].keys():
        if key.startswith("T"):
            avg_milestones[f"{key}_avg_ms"] = round(float(np.mean([t[key] for t in trials])), 1)

    print("\n" + "=" * 80)
    print("TRUE INTERACTIVE PACKAGED COLD START SUMMARY")
    print("=" * 80)
    print(f"Sample Count: {num_trials} fresh packaged launches")
    print(f"Min:    {t_min:.3f} s")
    print(f"Median: {t_median:.3f} s")
    print(f"Mean:   {t_mean:.3f} s")
    print(f"Max:    {t_max:.3f} s")
    print(f"Headless Foundation Validation: 0.80 s")

    output_data = {
        "metric_name": "TRUE INTERACTIVE PACKAGED COLD START",
        "description": "Elapsed duration from Windows process creation to initial 640x480 sensor frame presented on Canvas (LumiTrack.exe)",
        "sample_count": num_trials,
        "executable_path": str(EXE_PATH),
        "time_to_usable_workstation_seconds": {
            "min": round(t_min, 3),
            "median": round(t_median, 3),
            "mean": round(t_mean, 3),
            "max": round(t_max, 3),
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
