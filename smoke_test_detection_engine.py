"""
Phase 5.4 Detection Engine Smoke Test & Performance Check.

Measures:
  - Frames processed
  - Average / min / max processing time per frame (ms)
  - Effective throughput (FPS)
  - Candidate count per frame
  - Target detection rate on disturbed synthetic frames and video stream
"""

import os
import sys
import tempfile
import time
import cv2
import numpy as np

from src.app.app_controller import AppController
from src.config.config_manager import SystemConfig
from src.tracker.detection_engine import P0ThresholdDetector
from src.frame.simulation_provider import SimulationFrameProvider
from src.frame.mp4_provider import MP4FrameProvider
from src.tests.test_frame_provider import create_synthetic_mp4


def run_benchmark():
    print("=" * 75)
    print("SIH 2026 — Phase 5.4 Detection Engine Smoke Test & Performance Check")
    print("=" * 75)

    detector = P0ThresholdDetector()

    # -----------------------------------------------------------------------
    # 1. Simulation Stream Benchmark (100 frames at 640x480 with disturbances)
    # -----------------------------------------------------------------------
    print("\n[PART 1] Running Detection on Disturbed Simulation Stream (640x480)...")
    cfg = SystemConfig()
    cfg.simulation.random_seed = 42
    cfg.camera.update_rate_hz = 30
    cfg.simulation.duration_s = 3.33  # ~100 frames
    cfg.target.initial_position = "custom"
    cfg.target.initial_x = 1000.0
    cfg.target.initial_y = 1000.0
    cfg.target.size = 10
    cfg.target.intensity = 220
    # Enable disturbances
    cfg.platform_motion.enabled = True
    cfg.jitter.enabled = True
    cfg.atmospheric.condition = "FOG"
    cfg.noise.gaussian_enabled = True
    cfg.noise.gaussian_sigma = 8.0
    cfg.noise.sp_enabled = True
    cfg.noise.sp_density = 0.05

    sim_provider = SimulationFrameProvider.from_config(cfg)

    frame_times = []
    candidate_counts = []
    detected_count = 0
    total_frames = 100

    for i in range(total_frames):
        packet = sim_provider.get_next_frame()
        if packet is None:
            break

        t0 = time.perf_counter()
        result = detector.detect(packet)
        t1 = time.perf_counter()

        frame_times.append((t1 - t0) * 1000.0)
        candidate_counts.append(len(result.candidates))

        if len(result.candidates) >= 1:
            detected_count += 1

        if i % 25 == 0 or i == total_frames - 1:
            top_cand = result.candidates[0] if result.candidates else None
            score_str = f"{top_cand.detection_score:.2f}" if top_cand else "N/A"
            area_str = f"{top_cand.area}" if top_cand else "N/A"
            print(
                f"  Frame {packet.frame_number:02d} | Time: {frame_times[-1]:.2f}ms | "
                f"Candidates: {len(result.candidates)} | Top Area: {area_str} | Score: {score_str}"
            )

    avg_time_ms = float(np.mean(frame_times))
    min_time_ms = float(np.min(frame_times))
    max_time_ms = float(np.max(frame_times))
    effective_fps = 1000.0 / avg_time_ms if avg_time_ms > 0 else 0.0
    avg_candidates = float(np.mean(candidate_counts))

    print(f"\n  Simulation Performance Summary:")
    print(f"    Frames processed:        {len(frame_times)}")
    print(f"    Avg processing time:     {avg_time_ms:.2f} ms / frame (latency budget: <8ms)")
    print(f"    Min / Max time:          {min_time_ms:.2f} ms / {max_time_ms:.2f} ms")
    print(f"    Effective throughput:    {effective_fps:.1f} FPS")
    print(f"    Avg candidates / frame:  {avg_candidates:.2f}")
    print(f"    Detection success rate:  {detected_count / len(frame_times) * 100:.1f}%")

    # -----------------------------------------------------------------------
    # 2. MP4 Video Stream Benchmark (50 frames at 800x600)
    # -----------------------------------------------------------------------
    print("\n[PART 2] Running Detection on Arbitrary-Resolution MP4 Stream (800x600)...")
    temp_dir = tempfile.gettempdir()
    mp4_path = os.path.join(temp_dir, "detector_perf_test.mp4")
    create_synthetic_mp4(mp4_path, width=800, height=600, fps=30.0, num_frames=50)

    mp4_times = []
    mp4_cand_counts = []
    with MP4FrameProvider(mp4_path) as mp4_prov:
        while not mp4_prov.is_exhausted():
            pkt = mp4_prov.get_next_frame()
            if pkt is None:
                break
            t0 = time.perf_counter()
            res = detector.detect(pkt)
            t1 = time.perf_counter()
            mp4_times.append((t1 - t0) * 1000.0)
            mp4_cand_counts.append(len(res.candidates))

    if os.path.exists(mp4_path):
        os.remove(mp4_path)

    mp4_avg_ms = float(np.mean(mp4_times))
    mp4_fps = 1000.0 / mp4_avg_ms if mp4_avg_ms > 0 else 0.0

    print(f"    Frames processed:        {len(mp4_times)}")
    print(f"    Resolution:              800x600")
    print(f"    Avg processing time:     {mp4_avg_ms:.2f} ms / frame")
    print(f"    Effective throughput:    {mp4_fps:.1f} FPS")
    print(f"    Avg candidates / frame:  {np.mean(mp4_cand_counts):.2f}")

    print("\n" + "=" * 75)
    print("NOTE ON METRICS & PS COMPLIANCE:")
    print("These measurements indicate standalone detector execution speed on this host.")
    print("Per Stage 5 guidelines, they do NOT constitute formal end-to-end benchmark")
    print("compliance certification, which will be evaluated in the full benchmark harness.")
    print("=" * 75)

    return 0


if __name__ == "__main__":
    sys.exit(run_benchmark())
