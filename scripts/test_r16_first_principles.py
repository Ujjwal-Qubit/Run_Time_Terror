"""
First-principles revalidation of R16 Camera-Only Autonomous Acquisition.
Evaluates:
  1. In-FOV positions
  2. Near-FOV boundary positions
  3. Mid-field uncertainty zone positions (R <= 450 px)
  4. Far-field scene corner / edge positions (R > 600 px up to canvas edge)

Measures:
  - Metric A: Time from simulation start to TRACKING lock (t_sim_start -> lock)
  - Metric B: Time from first optical visibility to TRACKING lock (t_first_vis -> lock)
  - Theoretical minimum time based on PTZ rate limits (10 deg/s = 1600 px/s)
"""

import sys
import os
import math
import json
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from src.app.app_controller import AppController
from src.config.config_manager import ConfigManager
from src.frame.data_contracts import TrackingState

def run_r16_acquisition_test():
    print("=" * 80)
    print("R16 ACQUISITION BENCHMARK - FIRST PRINCIPLES AUDIT")
    print("=" * 80)

    # Initial camera: center at (1000, 1000), FOV 4°x3° => Viewport size 640x480
    # Visible box initially: X in [680, 1320], Y in [760, 1240]
    # Max PTZ speed = 10°/s. At 160 px/deg, max PTZ speed = 1600 px/s.
    # Canvas is 2000 x 2000.

    test_points = [
        # (category, name, tx, ty)
        # Category 1: Inside initial FOV
        ("IN_FOV", "Center", 1000.0, 1000.0),
        ("IN_FOV", "Near-Center Offset (+80, +60)", 1080.0, 1060.0),
        ("IN_FOV", "In-FOV Edge (+280, +180)", 1280.0, 1180.0),
        ("IN_FOV", "In-FOV Edge (-280, -180)", 720.0, 820.0),
        
        # Category 2: Near FOV Boundary (just out of view)
        ("NEAR_BOUNDARY", "Right Margin (+360, 0)", 1360.0, 1000.0),
        ("NEAR_BOUNDARY", "Left Margin (-360, 0)", 640.0, 1000.0),
        ("NEAR_BOUNDARY", "Top Margin (0, +280)", 1000.0, 1280.0),
        ("NEAR_BOUNDARY", "Bottom Margin (0, -280)", 1000.0, 720.0),

        # Category 3: Mid-Field / Coarse Acquisition Zone (dist <= 450 px from center)
        ("MID_FIELD_UNCERTAINTY", "Quadrant 1 (+380, +260)", 1380.0, 1260.0),
        ("MID_FIELD_UNCERTAINTY", "Quadrant 2 (-380, +260)", 620.0, 1260.0),
        ("MID_FIELD_UNCERTAINTY", "Quadrant 3 (-380, -260)", 620.0, 740.0),
        ("MID_FIELD_UNCERTAINTY", "Quadrant 4 (+380, -260)", 1380.0, 740.0),
        ("MID_FIELD_UNCERTAINTY", "Mid East (+450, 0)", 1450.0, 1000.0),
        ("MID_FIELD_UNCERTAINTY", "Mid North (0, +400)", 1000.0, 1400.0),

        # Category 4: Far-Field / Extreme Scene Corners & Edges (dist 600 - 1200 px)
        ("FAR_FIELD_EXTREME", "Corner Q1 Far (+750, +750)", 1750.0, 1750.0),
        ("FAR_FIELD_EXTREME", "Corner Q2 Far (-750, +750)", 250.0, 1750.0),
        ("FAR_FIELD_EXTREME", "Corner Q3 Far (-750, -750)", 250.0, 250.0),
        ("FAR_FIELD_EXTREME", "Corner Q4 Far (+750, -750)", 1750.0, 250.0),
        ("FAR_FIELD_EXTREME", "Edge East Far (+850, 0)", 1850.0, 1000.0),
        ("FAR_FIELD_EXTREME", "Edge South Far (0, -850)", 1000.0, 150.0),
    ]

    results = []
    dt = 1.0 / 30.0
    max_frames = 240  # 8.0 seconds of simulation

    for cat, name, tx, ty in test_points:
        dist_from_center = math.hypot(tx - 1000.0, ty - 1000.0)
        
        cm = ConfigManager()
        cfg = cm.config
        cfg.camera.initial_x = 1000.0
        cfg.camera.initial_y = 1000.0
        cfg.camera.fov_h_deg = 4.0
        cfg.camera.fov_v_deg = 3.0
        cfg.target.initial_x = tx
        cfg.target.initial_y = ty
        cfg.target.initial_position = "custom"
        cfg.target.speed = 0.0
        cfg.ptz.max_pan_speed_deg_s = 10.0
        cfg.ptz.max_tilt_speed_deg_s = 10.0
        cfg.ptz.search_scan_enabled = True

        app = AppController()
        app.initialize(cfg)

        first_vis_time = None
        lock_time = None
        vis_frame = None
        lock_frame = None

        for f in range(max_frames):
            pkt = app.get_next_frame()
            if pkt is None:
                break
            
            # Check optical visibility on the rendered image
            # A target is visible if its rendered centroid falls within viewport bounds
            # In simulation, we can inspect ground truth provider strictly for evaluation timing
            gt = app.ground_truth_provider.get_truth(pkt.frame_number)
            if gt.target_visible and first_vis_time is None:
                first_vis_time = pkt.timestamp
                vis_frame = pkt.frame_number

            pub, lat, trk, st, cent, det = app.step_algorithm(pkt)
            cmd = app.ptz_controller.compute(
                trk, st.state, pkt.width, pkt.height, dt=dt,
                projection_model=app.camera_model.projection_model
            )
            if cmd.valid:
                app.camera_model.apply_pan_tilt(cmd.delta_pan_deg, cmd.delta_tilt_deg)

            if st.state == TrackingState.TRACKING and lock_time is None:
                lock_time = pkt.timestamp
                lock_frame = pkt.frame_number
                break

        metric_a = lock_time if lock_time is not None else float("inf")
        metric_b = (lock_time - first_vis_time) if (lock_time is not None and first_vis_time is not None) else float("inf")

        # Theoretical minimal time if PTZ moved directly to target in straight line at 10 deg/s
        # 1 deg = 160 px, so 10 deg/s = 1600 px/s
        direct_ptz_time = dist_from_center / 1600.0

        r_item = {
            "category": cat,
            "name": name,
            "target_pos": (tx, ty),
            "dist_from_center_px": dist_from_center,
            "direct_ptz_time_s": direct_ptz_time,
            "metric_a_sim_to_lock_s": metric_a,
            "metric_b_vis_to_lock_s": metric_b,
            "lock_acquired": lock_time is not None,
            "metric_a_pass": metric_a <= 2.0,
            "metric_b_pass": metric_b <= 2.0,
        }
        results.append(r_item)

        print(f"[{cat:21s}] {name:32s} | d={dist_from_center:6.1f}px | "
              f"Metric A={metric_a:5.2f}s (<=2s: {str(r_item['metric_a_pass']):5s}) | "
              f"Metric B={metric_b:5.2f}s (<=2s: {str(r_item['metric_b_pass']):5s}) | "
              f"DirectLimit={direct_ptz_time:4.2f}s")

    out_file = "output/phase3_validation/r16_acquisition_results.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print("CATEGORY SUMMARY:")
    print("=" * 80)
    for cat in ["IN_FOV", "NEAR_BOUNDARY", "MID_FIELD_UNCERTAINTY", "FAR_FIELD_EXTREME"]:
        cat_items = [r for r in results if r["category"] == cat]
        pass_a = sum(1 for r in cat_items if r["metric_a_pass"])
        pass_b = sum(1 for r in cat_items if r["metric_b_pass"])
        mean_a = np.mean([r["metric_a_sim_to_lock_s"] for r in cat_items if r["lock_acquired"]])
        mean_b = np.mean([r["metric_b_vis_to_lock_s"] for r in cat_items if r["lock_acquired"]])
        print(f"{cat:22s} | N={len(cat_items):2d} | "
              f"Metric A Pass (<=2.0s): {pass_a}/{len(cat_items)} (Mean: {mean_a:.2f}s) | "
              f"Metric B Pass (<=2.0s): {pass_b}/{len(cat_items)} (Mean: {mean_b:.2f}s)")

    return results

if __name__ == "__main__":
    results = run_r16_acquisition_test()
    in_fov_items = [r for r in results if r["category"] == "IN_FOV"]
    in_fov_passed = sum(1 for r in in_fov_items if r["metric_b_pass"])
    if in_fov_passed < len(in_fov_items):
        print(f"\n[FAIL] In-FOV acquisition failed ({in_fov_passed}/{len(in_fov_items)} passed Metric B <= 2.0s)!")
        sys.exit(1)
    print(f"\n[SUCCESS] R16 first principles acquisition benchmark passed ({in_fov_passed}/{len(in_fov_items)} In-FOV passed).")
    sys.exit(0)
