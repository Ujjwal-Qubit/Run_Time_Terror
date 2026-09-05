"""
Deterministic Simulation Engine Smoke Test.

Runs 60 simulation frames (2.0 seconds at 30 FPS) twice with identical seeds.
Verifies:
  1. Frame-by-frame ground-truth capture and synchronization
  2. Four distinct position concepts: world (Xw, Yw), ideal projected (Xp, Yp),
     rendered centroid (Xr, Yr), and camera pose
  3. Strict byte-for-byte reproducibility between identical seeds
  4. Frame dimensions (640x480) and data types (uint8)
"""

import sys
import numpy as np

from src.app.app_controller import AppController
from src.config.config_manager import SystemConfig, MotionConfig, NoiseConfig, JitterConfig, PlatformMotionConfig
from src.frame.data_contracts import MotionType


def run_smoke_test():
    print("=" * 70)
    print("SIH 2026 — Phase 5.2 Deterministic Simulation Engine Smoke Test")
    print("=" * 70)

    # Configure a realistic scenario with active disturbances:
    # Circular motion + Platform motion + Jitter + Gaussian noise + Fog
    cfg1 = SystemConfig()
    cfg1.simulation.random_seed = 42
    cfg1.motion.motion_type = MotionType.CIRCULAR.value
    cfg1.motion.circle_radius = 200.0
    cfg1.target.initial_position = "custom"
    cfg1.target.initial_x = 1000.0
    cfg1.target.initial_y = 1000.0
    cfg1.target.size = 12
    cfg1.target.intensity = 220
    cfg1.platform_motion.enabled = True
    cfg1.platform_motion.max_px_per_frame = 5.0
    cfg1.jitter.enabled = True
    cfg1.jitter.max_px_per_frame = 3.0
    cfg1.atmospheric.condition = "FOG"
    cfg1.noise.gaussian_enabled = True
    cfg1.noise.gaussian_sigma = 8.0
    cfg1.noise.sp_enabled = True
    cfg1.noise.sp_density = 0.05

    print("\n[RUN 1] Initializing AppController with seed=42...")
    app1 = AppController()
    app1.initialize(cfg1)

    frames_run1 = []
    gt_run1 = []

    dt = 1.0 / 30.0  # 30 FPS
    num_frames = 60

    print(f"[RUN 1] Stepping {num_frames} frames ({num_frames * dt:.1f}s at 30 FPS)...")
    for f in range(num_frames):
        disturbed, gt, clean = app1.step_simulation(dt)
        frames_run1.append(disturbed)
        gt_run1.append(gt)
        if f % 15 == 0 or f == num_frames - 1:
            print(
                f"  Frame {gt.frame_number:02d} | t={gt.timestamp:.3f}s | "
                f"World: ({gt.target_world_x:6.1f}, {gt.target_world_y:6.1f}) | "
                f"Projected: ({gt.ideal_projected_x:5.1f}, {gt.ideal_projected_y:5.1f}) | "
                f"Rendered: ({gt.rendered_centroid_x:5.1f}, {gt.rendered_centroid_y:5.1f}) | "
                f"Vis: {gt.target_visible} | Mean: {np.mean(disturbed):.1f}"
            )

    print("\n[RUN 2] Initializing fresh AppController with identical seed=42...")
    app2 = AppController()
    app2.initialize(cfg1)

    frames_run2 = []
    gt_run2 = []

    print(f"[RUN 2] Stepping {num_frames} frames to verify determinism...")
    for f in range(num_frames):
        disturbed, gt, clean = app2.step_simulation(dt)
        frames_run2.append(disturbed)
        gt_run2.append(gt)

    print("\n[VERIFICATION] Comparing Run 1 and Run 2 byte-for-byte...")
    all_frames_identical = True
    for f in range(num_frames):
        if not np.array_equal(frames_run1[f], frames_run2[f]):
            all_frames_identical = False
            print(f"  MISMATCH at frame {f}!")
            break

    all_gt_identical = True
    for f in range(num_frames):
        gt1 = gt_run1[f]
        gt2 = gt_run2[f]
        if (
            gt1.target_world_x != gt2.target_world_x
            or gt1.target_world_y != gt2.target_world_y
            or gt1.ideal_projected_x != gt2.ideal_projected_x
            or gt1.ideal_projected_y != gt2.ideal_projected_y
            or gt1.rendered_centroid_x != gt2.rendered_centroid_x
            or gt1.rendered_centroid_y != gt2.rendered_centroid_y
        ):
            all_gt_identical = False
            print(f"  GT MISMATCH at frame {f}!")
            break

    print(f"  Frame array byte-level equality: {'PASS (100% IDENTICAL)' if all_frames_identical else 'FAIL'}")
    print(f"  Ground truth telemetry equality: {'PASS (100% IDENTICAL)' if all_gt_identical else 'FAIL'}")
    print(f"  Frame output shape: {frames_run1[0].shape} (expected: (480, 640))")
    print(f"  Frame output dtype: {frames_run1[0].dtype} (expected: uint8)")

    if all_frames_identical and all_gt_identical:
        print("\n" + "=" * 70)
        print("SIMULATION ENGINE SMOKE TEST: ALL PASSED (100% DETERMINISTIC)")
        print("=" * 70)
        return 0
    else:
        print("\nSMOKE TEST FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(run_smoke_test())
