"""
Rigorous Loop Latency and Rate Benchmark for R15 Compliance.
Measures continuous end-to-end loop latency across 500 frames:
  1. Frame ingestion / packet unpacking
  2. Perception & Candidate Identification (adaptive thresholding, connected components)
  3. Feature extraction & MLP candidate classification
  4. Kalman tracking association, gating, update & coasting
  5. PTZ control command calculation
Computes:
  - Latency percentiles: Mean, Median, P90, P95, P99, Max, Min (in milliseconds)
  - Sustained Loop Rate (Frames Per Second)
  - Latency breakdown by subsystem
"""

import sys
import os
import time
import json
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from src.app.app_controller import AppController
from src.config.config_manager import ConfigManager
from src.frame.data_contracts import TrackingState

def benchmark_loop_latency():
    print("=" * 80)
    print("R15 END-TO-END CONTINUOUS LOOP LATENCY & FPS BENCHMARK")
    print("=" * 80)

    cm = ConfigManager()
    cfg = cm.config
    cfg.target.initial_x = 1000.0
    cfg.target.initial_y = 1000.0
    cfg.target.speed = 35.0
    cfg.motion.motion_type = "CIRCULAR"
    cfg.motion.circular_radius = 120.0
    cfg.atmospheric.condition = "HAZE"
    cfg.noise.gaussian_enabled = True
    cfg.noise.gaussian_sigma = 8.0

    app = AppController()
    app.initialize(cfg)

    num_frames = 500
    dt = 1.0 / 30.0

    # Latency storage in milliseconds
    loop_latencies_ms = []
    breakdown_ingest_ms = []
    breakdown_algo_ms = []
    breakdown_ptz_ms = []

    # Warmup 10 frames
    for _ in range(10):
        pkt = app.get_next_frame()
        pub, lat, trk, st, cent, det = app.step_algorithm(pkt)
        app.ptz_controller.compute(trk, st.state, pkt.width, pkt.height, dt=dt)

    t_start_total = time.perf_counter()

    for i in range(num_frames):
        t0 = time.perf_counter()
        
        # 1. Ingestion
        pkt = app.get_next_frame()
        t1 = time.perf_counter()

        # 2. Algorithm (detection, MLP classification, Kalman tracking)
        pub, lat, trk, st, cent, det = app.step_algorithm(pkt)
        t2 = time.perf_counter()

        # 3. PTZ Command Generation
        cmd = app.ptz_controller.compute(
            trk, st.state, pkt.width, pkt.height, dt=dt,
            projection_model=app.camera_model.projection_model
        )
        if cmd.valid:
            app.camera_model.apply_pan_tilt(cmd.delta_pan_deg, cmd.delta_tilt_deg)
        t3 = time.perf_counter()

        total_loop_ms = (t3 - t0) * 1000.0
        loop_latencies_ms.append(total_loop_ms)
        breakdown_ingest_ms.append((t1 - t0) * 1000.0)
        breakdown_algo_ms.append((t2 - t1) * 1000.0)
        breakdown_ptz_ms.append((t3 - t2) * 1000.0)

    t_end_total = time.perf_counter()
    total_wall_time = t_end_total - t_start_total
    sustained_fps = num_frames / total_wall_time

    # Compute percentiles
    loop_arr = np.array(loop_latencies_ms)
    algo_arr = np.array(breakdown_algo_ms)
    ptz_arr = np.array(breakdown_ptz_ms)
    ingest_arr = np.array(breakdown_ingest_ms)

    mean_ms = np.mean(loop_arr)
    std_ms = np.std(loop_arr)
    median_ms = np.median(loop_arr)
    p90_ms = np.percentile(loop_arr, 90)
    p95_ms = np.percentile(loop_arr, 95)
    p99_ms = np.percentile(loop_arr, 99)
    max_ms = np.max(loop_arr)
    min_ms = np.min(loop_arr)

    print(f"Frames Benchmarked: {num_frames}")
    print(f"Total Wall Time:    {total_wall_time:.3f} s")
    print(f"Sustained Loop FPS: {sustained_fps:.1f} FPS (Requirement >= 30.0 FPS)")
    print(f"Pass/Fail Verdict:  {'PASS' if sustained_fps >= 30.0 else 'FAIL'}")
    print("\nEnd-to-End Latency Statistics (ms):")
    print(f"  Mean:   {mean_ms:.3f} ms (+/- {std_ms:.3f})")
    print(f"  Median: {median_ms:.3f} ms")
    print(f"  P90:    {p90_ms:.3f} ms")
    print(f"  P95:    {p95_ms:.3f} ms")
    print(f"  P99:    {p99_ms:.3f} ms")
    print(f"  Max:    {max_ms:.3f} ms")
    print(f"  Min:    {min_ms:.3f} ms")

    print("\nSubsystem Timing Breakdown (Mean ms):")
    print(f"  Frame Ingestion:      {np.mean(ingest_arr):.3f} ms ({np.mean(ingest_arr)/mean_ms*100:.1f}%)")
    print(f"  Perception & Tracker: {np.mean(algo_arr):.3f} ms ({np.mean(algo_arr)/mean_ms*100:.1f}%)")
    print(f"  PTZ Control Command:  {np.mean(ptz_arr):.3f} ms ({np.mean(ptz_arr)/mean_ms*100:.1f}%)")

    latency_data = {
        "num_frames": num_frames,
        "total_wall_time_s": total_wall_time,
        "sustained_fps": sustained_fps,
        "mean_ms": mean_ms,
        "std_ms": std_ms,
        "median_ms": median_ms,
        "p90_ms": p90_ms,
        "p95_ms": p95_ms,
        "p99_ms": p99_ms,
        "max_ms": max_ms,
        "min_ms": min_ms,
        "subsystem_mean_ms": {
            "ingestion": float(np.mean(ingest_arr)),
            "perception_tracking": float(np.mean(algo_arr)),
            "ptz_control": float(np.mean(ptz_arr)),
        }
    }

    out_file = "output/phase3_validation/loop_latency_results.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(latency_data, f, indent=2)

    return latency_data

if __name__ == "__main__":
    benchmark_loop_latency()
