"""
Phase 5.5 Centroid Estimator Smoke Test & Performance Check.

Measures:
  - Frames processed
  - Average / min / max centroid estimation time per frame (ms)
  - Effective throughput (FPS)
  - Valid centroid percentage (%)
  - Sub-pixel coordinate precision
  - Integration with SimulationFrameProvider and MP4FrameProvider
"""

import os
import sys
import tempfile
import time
import cv2
import numpy as np

from src.config.config_manager import SystemConfig
from src.tracker.detection_engine import P0ThresholdDetector
from src.tracker.centroid_estimator import IntensityWeightedCentroidEstimator
from src.frame.simulation_provider import SimulationFrameProvider
from src.frame.mp4_provider import MP4FrameProvider
from src.tests.test_frame_provider import create_synthetic_mp4


def run_benchmark():
    print("=" * 75)
    print("SIH 2026 — Phase 5.5 Centroid Estimator Smoke Test & Performance Check")
    print("=" * 75)

    detector = P0ThresholdDetector()
    centroid_estimator = IntensityWeightedCentroidEstimator()

    # -----------------------------------------------------------------------
    # 1. Simulation Stream Benchmark (100 frames at 640x480 with disturbances)
    # -----------------------------------------------------------------------
    print("\n[PART 1] Running Centroid Estimation on Disturbed Simulation Stream (640x480)...")
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
    cfg.atmospheric.condition = "HAZE"
    cfg.noise.gaussian_enabled = True
    cfg.noise.gaussian_sigma = 6.0
    cfg.noise.sp_enabled = True
    cfg.noise.sp_density = 0.02

    sim_provider = SimulationFrameProvider.from_config(cfg)

    frame_times = []
    valid_centroids = 0
    total_candidates_processed = 0
    total_frames = 100

    sample_coords = []

    for i in range(total_frames):
        packet = sim_provider.get_next_frame()
        if packet is None:
            break

        # Detect candidates
        det_result = detector.detect(packet)
        if not det_result.candidates:
            continue

        best_cand = det_result.candidates[0]
        total_candidates_processed += 1

        t0 = time.perf_counter()
        cent_result = centroid_estimator.estimate(packet, best_cand)
        t1 = time.perf_counter()

        frame_times.append((t1 - t0) * 1000.0)

        if cent_result.valid:
            valid_centroids += 1
            if i % 25 == 0 or i == total_frames - 1:
                sample_coords.append((packet.frame_number, cent_result.x, cent_result.y, cent_result.quality))
                print(
                    f"  Frame {packet.frame_number:02d} | Time: {frame_times[-1]:.3f}ms | "
                    f"Centroid: ({cent_result.x:.2f}, {cent_result.y:.2f}) | "
                    f"Signal: {cent_result.total_signal:.1f} | BG: {cent_result.estimated_bg:.1f} | "
                    f"Quality: {cent_result.quality:.2f}"
                )

    avg_time_ms = float(np.mean(frame_times)) if frame_times else 0.0
    min_time_ms = float(np.min(frame_times)) if frame_times else 0.0
    max_time_ms = float(np.max(frame_times)) if frame_times else 0.0
    effective_fps = 1000.0 / avg_time_ms if avg_time_ms > 0 else 0.0
    valid_rate = (valid_centroids / total_candidates_processed * 100.0) if total_candidates_processed > 0 else 0.0

    print(f"\n  Simulation Centroid Performance Summary:")
    print(f"    Frames evaluated:        {len(frame_times)}")
    print(f"    Avg estimation latency:  {avg_time_ms:.3f} ms / candidate (budget: <2.0 ms)")
    print(f"    Min / Max latency:       {min_time_ms:.3f} ms / {max_time_ms:.3f} ms")
    print(f"    Effective throughput:    {effective_fps:.1f} FPS (isolated centroiding)")
    print(f"    Valid centroid rate:     {valid_rate:.1f}% ({valid_centroids}/{total_candidates_processed})")

    # -----------------------------------------------------------------------
    # 2. MP4 Video Stream Benchmark (50 frames at 800x600)
    # -----------------------------------------------------------------------
    print("\n[PART 2] Running Centroid Estimation on Arbitrary-Resolution MP4 Stream (800x600)...")
    temp_dir = tempfile.gettempdir()
    mp4_path = os.path.join(temp_dir, "centroid_perf_test.mp4")
    create_synthetic_mp4(mp4_path, width=800, height=600, fps=30.0, num_frames=50)

    mp4_times = []
    mp4_valid = 0
    mp4_cands = 0

    with MP4FrameProvider(mp4_path) as mp4_prov:
        while not mp4_prov.is_exhausted():
            pkt = mp4_prov.get_next_frame()
            if pkt is None:
                break
            det = detector.detect(pkt)
            if not det.candidates:
                continue

            best_cand = det.candidates[0]
            mp4_cands += 1

            t0 = time.perf_counter()
            res = centroid_estimator.estimate(pkt, best_cand)
            t1 = time.perf_counter()

            mp4_times.append((t1 - t0) * 1000.0)
            if res.valid:
                mp4_valid += 1

    if os.path.exists(mp4_path):
        os.remove(mp4_path)

    mp4_avg_ms = float(np.mean(mp4_times)) if mp4_times else 0.0
    mp4_fps = 1000.0 / mp4_avg_ms if mp4_avg_ms > 0 else 0.0

    print(f"    Frames evaluated:        {len(mp4_times)}")
    print(f"    Resolution:              800x600")
    print(f"    Avg estimation latency:  {mp4_avg_ms:.3f} ms / candidate")
    print(f"    Effective throughput:    {mp4_fps:.1f} FPS")
    print(f"    Valid centroid rate:     {(mp4_valid / mp4_cands * 100.0) if mp4_cands > 0 else 0.0:.1f}%")

    print("\n" + "=" * 75)
    print("NOTE ON METRICS & PS COMPLIANCE:")
    print("These measurements indicate standalone centroid estimator execution speed on this host.")
    print("Per Stage 5 guidelines, they do NOT constitute formal end-to-end benchmark")
    print("compliance certification, which will be evaluated in the full benchmark harness.")
    print("=" * 75)

    return 0


if __name__ == "__main__":
    sys.exit(run_benchmark())
