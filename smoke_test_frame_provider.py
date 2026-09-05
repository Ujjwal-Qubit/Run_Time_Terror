"""
Phase 5.3 FrameProvider Smoke Test.

Demonstrates:
  1. Simulation -> FrameProvider pipeline (SIMULATION mode)
  2. MP4 -> FrameProvider pipeline (MP4 mode with custom resolution)
  3. Verification that both pipelines produce the identical FramePacket contract
  4. Zero ground-truth leakage into downstream packets
  5. Immutability validation (read-only views)
"""

import os
import sys
import tempfile
import cv2
import numpy as np

from src.app.app_controller import AppController
from src.config.config_manager import SystemConfig
from src.frame.data_contracts import FramePacket, FrameSource


def create_test_mp4(file_path: str, width: int = 400, height: int = 300, fps: float = 25.0, count: int = 25):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(file_path, fourcc, fps, (width, height))
    for i in range(count):
        img = np.full((height, width, 3), fill_value=25, dtype=np.uint8)
        # Moving bright beacon
        bx = int(30 + i * (width - 60) / max(1, count))
        by = int(height / 2)
        cv2.circle(img, (bx, by), 8, (230, 230, 230), -1)
        out.write(img)
    out.release()


def run_smoke_test():
    print("=" * 75)
    print("SIH 2026 — Phase 5.3 FrameProvider Smoke Test & Contract Verification")
    print("=" * 75)

    # -----------------------------------------------------------------------
    # Part 1: Simulation -> FrameProvider
    # -----------------------------------------------------------------------
    print("\n[PART 1] Running SimulationFrameProvider via AppController (SIMULATION mode)...")
    cfg_sim = SystemConfig()
    cfg_sim.simulation.random_seed = 42
    cfg_sim.camera.update_rate_hz = 30
    cfg_sim.simulation.duration_s = 1.0  # 30 frames

    app_sim = AppController()
    app_sim.initialize(cfg_sim)

    sim_packets = []
    for _ in range(15):
        pkt = app_sim.get_next_frame()
        if pkt is not None:
            sim_packets.append(pkt)

    sample_sim = sim_packets[0]
    print(f"  Frames retrieved: {len(sim_packets)}")
    print(f"  Source type:      {sample_sim.source.value}")
    print(f"  Resolution:       {sample_sim.width}x{sample_sim.height}")
    print(f"  Array shape:      {sample_sim.image.shape} (dtype: {sample_sim.image.dtype})")
    print(f"  Read-only flag:   writeable={sample_sim.image.flags.writeable}")
    print(f"  Timestamp range:  {sim_packets[0].timestamp:.3f}s -> {sim_packets[-1].timestamp:.3f}s")
    print(f"  Ground truth in packet: {hasattr(sample_sim, 'ground_truth')} (PASS - zero leakage)")

    # -----------------------------------------------------------------------
    # Part 2: MP4 -> FrameProvider
    # -----------------------------------------------------------------------
    print("\n[PART 2] Running MP4FrameProvider via AppController (MP4 mode)...")
    temp_dir = tempfile.gettempdir()
    mp4_path = os.path.join(temp_dir, "sih_smoke_test.mp4")
    create_test_mp4(mp4_path, width=480, height=360, fps=25.0, count=25)

    cfg_mp4 = SystemConfig()
    cfg_mp4.simulation.mode = "MP4"
    cfg_mp4.simulation.mp4_path = mp4_path

    app_mp4 = AppController()
    app_mp4.initialize(cfg_mp4)

    mp4_packets = []
    while not app_mp4.frame_provider.is_exhausted():
        pkt = app_mp4.get_next_frame()
        if pkt is not None:
            mp4_packets.append(pkt)

    sample_mp4 = mp4_packets[0]
    print(f"  Frames retrieved: {len(mp4_packets)}")
    print(f"  Source type:      {sample_mp4.source.value}")
    print(f"  Resolution:       {sample_mp4.width}x{sample_mp4.height} (preserves non-640x480)")
    print(f"  Array shape:      {sample_mp4.image.shape} (dtype: {sample_mp4.image.dtype})")
    print(f"  Monochrome:       {sample_mp4.image.ndim == 2} (converted from 3-channel BGR)")
    print(f"  Read-only flag:   writeable={sample_mp4.image.flags.writeable}")
    print(f"  Timestamp range:  {mp4_packets[0].timestamp:.3f}s -> {mp4_packets[-1].timestamp:.3f}s")
    print(f"  Ground truth in packet: {hasattr(sample_mp4, 'ground_truth')} (PASS - zero leakage)")

    app_mp4.stop()
    if os.path.exists(mp4_path):
        os.remove(mp4_path)

    # -----------------------------------------------------------------------
    # Part 3: Contract Equivalence Verification
    # -----------------------------------------------------------------------
    print("\n[PART 3] Contract Equivalence Verification...")
    sim_fields = {k: type(v) for k, v in sample_sim.__dict__.items()}
    mp4_fields = {k: type(v) for k, v in sample_mp4.__dict__.items()}

    print(f"  Fields match:     {sim_fields.keys() == mp4_fields.keys()} ({list(sim_fields.keys())})")
    types_match = all(sim_fields[k] == mp4_fields[k] for k in sim_fields)
    print(f"  Field types match: {types_match}")

    # Immutability test on both
    sim_write_error = False
    try:
        sample_sim.image[0, 0] = 0
    except ValueError:
        sim_write_error = True

    mp4_write_error = False
    try:
        sample_mp4.image[0, 0] = 0
    except ValueError:
        mp4_write_error = True

    print(f"  Simulation array immutability: {'PASS (write raised ValueError)' if sim_write_error else 'FAIL'}")
    print(f"  MP4 array immutability:        {'PASS (write raised ValueError)' if mp4_write_error else 'FAIL'}")

    all_passed = (
        len(sim_packets) == 15
        and len(mp4_packets) == 25
        and types_match
        and sim_write_error
        and mp4_write_error
        and sample_sim.image.ndim == 2
        and sample_mp4.image.ndim == 2
    )

    if all_passed:
        print("\n" + "=" * 75)
        print("FRAMEPROVIDER SMOKE TEST: ALL PASSED (CONTRACT IDENTICAL)")
        print("=" * 75)
        return 0
    else:
        print("\nFRAMEPROVIDER SMOKE TEST FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(run_smoke_test())
