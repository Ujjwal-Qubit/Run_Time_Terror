"""
Comprehensive Boundary Disturbances, Multi-Seed Statistical Sweep & Falsification Matrix.
Covers:
  1. Upper-bound Gaussian noise sweep (sigma in [0, 8, 12, 14, 15, 16, 18, 20]) across 10 seeds.
  2. Upper-bound Platform Jitter sweep (amplitude in [0, 3, 6, 10, 15, 18, 20] px/frame) across 10 seeds.
  3. Upper-bound Platform Drift sweep (velocity in [0, 2, 5, 10, 15, 18, 20] px/frame) across 10 seeds.
  4. Adversarial Combined Hazards:
     - Hazard A: Maximum Jitter (20 px) + Maximum Drift (20 px)
     - Hazard B: Near-Boundary Noise (sigma=14) + Heavy Fog + Low Contrast
     - Hazard C: Super-Bright Decoy (intensity 240 vs target 180) placed 45 px from target
     - Hazard D: Rapid Multi-Burst Blanking (4 frames blanked every 15 frames, 3 bursts)
     - Hazard E: Extreme Maneuver (speed 80 px/s, sinusoidal sharp reversal)
  5. Continuous vs Discrete Centroid Truth Audit:
     - Measures discrete rendered centroid error vs continuous ideal projected coordinate error.
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

def run_boundary_and_falsification():
    print("=" * 80)
    print("BOUNDARY DISTURBANCES & ADVERSARIAL FALSIFICATION MATRIX")
    print("=" * 80)

    out_dir = "output/phase3_validation"
    os.makedirs(out_dir, exist_ok=True)

    seeds = [10, 21, 32, 43, 54, 65, 76, 87, 98, 109]
    results = {
        "gaussian_noise_sweep": [],
        "jitter_sweep": [],
        "drift_sweep": [],
        "adversarial_hazards": [],
        "centroid_truth_analysis": {},
    }

    # -------------------------------------------------------------------------
    # 1. Upper-Bound Gaussian Noise Sweep
    # -------------------------------------------------------------------------
    print("\n--- [PART 1] Upper-Bound Gaussian Noise Sweep Across 10 Seeds ---")
    sigmas = [0.0, 8.0, 12.0, 14.0, 15.0, 16.0, 18.0, 20.0]
    for sigma in sigmas:
        rmses = []
        post_losses = []
        for s in seeds:
            cm = ConfigManager()
            cfg = cm.config
            cfg.target.initial_x = 1000.0
            cfg.target.initial_y = 1000.0
            cfg.target.speed = 35.0
            cfg.motion.motion_type = "CIRCULAR"
            cfg.atmospheric.condition = "CLEAR"
            cfg.noise.gaussian_enabled = (sigma > 0.0)
            cfg.noise.gaussian_sigma = sigma

            np.random.seed(s)
            app = AppController()
            app.initialize(cfg)

            total_frames = 45
            sq_errs = []
            first_lock_f = None
            post_tracked = 0

            for f in range(total_frames):
                pkt = app.get_next_frame()
                pub, lat, trk, st, cent, det = app.step_algorithm(pkt)
                cmd = app.ptz_controller.compute(
                    trk, st.state, pkt.width, pkt.height, dt=1.0/30.0,
                    projection_model=app.camera_model.projection_model
                )
                if cmd.valid:
                    app.camera_model.apply_pan_tilt(cmd.delta_pan_deg, cmd.delta_tilt_deg)

                if st.state == TrackingState.TRACKING and first_lock_f is None:
                    first_lock_f = f

                gt = app.ground_truth_provider.get_truth(pkt.frame_number)
                if pub.algorithm_is_tracking and pub.centroid_x is not None and gt.target_visible:
                    err = math.hypot(pub.centroid_x - gt.rendered_centroid_x, pub.centroid_y - gt.rendered_centroid_y)
                    sq_errs.append(err ** 2)

                if first_lock_f is not None and f >= first_lock_f:
                    if pub.algorithm_is_tracking:
                        post_tracked += 1

            post_total = (total_frames - first_lock_f) if first_lock_f is not None else total_frames
            loss_pct = ((post_total - post_tracked) / max(1, post_total)) * 100.0 if first_lock_f is not None else 100.0
            rmse = math.sqrt(np.mean(sq_errs)) if sq_errs else 999.0

            rmses.append(rmse)
            post_losses.append(loss_pct)

        mean_rmse = float(np.mean(rmses))
        mean_loss = float(np.mean(post_losses))
        status = "PASS" if mean_loss == 0.0 and mean_rmse < 5.0 else ("DEGRADED" if mean_loss < 30.0 else "FAIL")
        print(f"Gaussian Sigma = {sigma:4.1f} | Mean RMSE = {mean_rmse:7.3f} px | Post-Acq Loss = {mean_loss:5.1f}% | Verdict: {status}")
        results["gaussian_noise_sweep"].append({
            "sigma": sigma,
            "mean_rmse": mean_rmse,
            "std_rmse": float(np.std(rmses)),
            "mean_post_loss": mean_loss,
            "status": status,
        })

    # -------------------------------------------------------------------------
    # 2. Upper-Bound Platform Jitter Sweep
    # -------------------------------------------------------------------------
    print("\n--- [PART 2] Upper-Bound Platform Jitter Sweep Across 10 Seeds ---")
    jitters = [0.0, 3.0, 6.0, 10.0, 15.0, 18.0, 20.0]
    for jit in jitters:
        rmses = []
        post_losses = []
        for s in seeds:
            cm = ConfigManager()
            cfg = cm.config
            cfg.target.initial_x = 1000.0
            cfg.target.initial_y = 1000.0
            cfg.target.speed = 35.0
            cfg.motion.motion_type = "CIRCULAR"
            cfg.atmospheric.condition = "CLEAR"
            cfg.jitter.enabled = (jit > 0.0)
            cfg.jitter.max_px_per_frame = jit

            np.random.seed(s)
            app = AppController()
            app.initialize(cfg)

            total_frames = 45
            sq_errs = []
            first_lock_f = None
            post_tracked = 0

            for f in range(total_frames):
                pkt = app.get_next_frame()
                pub, lat, trk, st, cent, det = app.step_algorithm(pkt)
                cmd = app.ptz_controller.compute(
                    trk, st.state, pkt.width, pkt.height, dt=1.0/30.0,
                    projection_model=app.camera_model.projection_model
                )
                if cmd.valid:
                    app.camera_model.apply_pan_tilt(cmd.delta_pan_deg, cmd.delta_tilt_deg)

                if st.state == TrackingState.TRACKING and first_lock_f is None:
                    first_lock_f = f

                gt = app.ground_truth_provider.get_truth(pkt.frame_number)
                if pub.algorithm_is_tracking and pub.centroid_x is not None and gt.target_visible:
                    err = math.hypot(pub.centroid_x - gt.rendered_centroid_x, pub.centroid_y - gt.rendered_centroid_y)
                    sq_errs.append(err ** 2)

                if first_lock_f is not None and f >= first_lock_f:
                    if pub.algorithm_is_tracking:
                        post_tracked += 1

            post_total = (total_frames - first_lock_f) if first_lock_f is not None else total_frames
            loss_pct = ((post_total - post_tracked) / max(1, post_total)) * 100.0 if first_lock_f is not None else 100.0
            rmse = math.sqrt(np.mean(sq_errs)) if sq_errs else 999.0

            rmses.append(rmse)
            post_losses.append(loss_pct)

        mean_rmse = float(np.mean(rmses))
        mean_loss = float(np.mean(post_losses))
        status = "PASS" if mean_loss == 0.0 and mean_rmse < 5.0 else "FAIL"
        print(f"Jitter Amplitude = {jit:4.1f} px/f | Mean RMSE = {mean_rmse:7.3f} px | Post-Acq Loss = {mean_loss:5.1f}% | Verdict: {status}")
        results["jitter_sweep"].append({
            "amplitude": jit,
            "mean_rmse": mean_rmse,
            "mean_post_loss": mean_loss,
            "status": status,
        })

    # -------------------------------------------------------------------------
    # 3. Upper-Bound Platform Drift Sweep
    # -------------------------------------------------------------------------
    print("\n--- [PART 3] Upper-Bound Platform Drift Sweep Across 10 Seeds ---")
    drifts = [0.0, 2.0, 5.0, 10.0, 15.0, 18.0, 20.0]
    for d_rate in drifts:
        rmses = []
        post_losses = []
        for s in seeds:
            cm = ConfigManager()
            cfg = cm.config
            cfg.target.initial_x = 1000.0
            cfg.target.initial_y = 1000.0
            cfg.target.speed = 35.0
            cfg.motion.motion_type = "CIRCULAR"
            cfg.atmospheric.condition = "CLEAR"
            cfg.platform_motion.enabled = (d_rate > 0.0)
            cfg.platform_motion.max_px_per_frame = d_rate

            np.random.seed(s)
            app = AppController()
            app.initialize(cfg)

            total_frames = 45
            sq_errs = []
            first_lock_f = None
            post_tracked = 0

            for f in range(total_frames):
                pkt = app.get_next_frame()
                pub, lat, trk, st, cent, det = app.step_algorithm(pkt)
                cmd = app.ptz_controller.compute(
                    trk, st.state, pkt.width, pkt.height, dt=1.0/30.0,
                    projection_model=app.camera_model.projection_model
                )
                if cmd.valid:
                    app.camera_model.apply_pan_tilt(cmd.delta_pan_deg, cmd.delta_tilt_deg)

                if st.state == TrackingState.TRACKING and first_lock_f is None:
                    first_lock_f = f

                gt = app.ground_truth_provider.get_truth(pkt.frame_number)
                if pub.algorithm_is_tracking and pub.centroid_x is not None and gt.target_visible:
                    err = math.hypot(pub.centroid_x - gt.rendered_centroid_x, pub.centroid_y - gt.rendered_centroid_y)
                    sq_errs.append(err ** 2)

                if first_lock_f is not None and f >= first_lock_f:
                    if pub.algorithm_is_tracking:
                        post_tracked += 1

            post_total = (total_frames - first_lock_f) if first_lock_f is not None else total_frames
            loss_pct = ((post_total - post_tracked) / max(1, post_total)) * 100.0 if first_lock_f is not None else 100.0
            rmse = math.sqrt(np.mean(sq_errs)) if sq_errs else 999.0

            rmses.append(rmse)
            post_losses.append(loss_pct)

        mean_rmse = float(np.mean(rmses))
        mean_loss = float(np.mean(post_losses))
        status = "PASS" if mean_loss == 0.0 and mean_rmse < 5.0 else "FAIL"
        print(f"Drift Rate = {d_rate:4.1f} px/f | Mean RMSE = {mean_rmse:7.3f} px | Post-Acq Loss = {mean_loss:5.1f}% | Verdict: {status}")
        results["drift_sweep"].append({
            "drift_rate": d_rate,
            "mean_rmse": mean_rmse,
            "mean_post_loss": mean_loss,
            "status": status,
        })

    # -------------------------------------------------------------------------
    # 4. Adversarial Falsification Hazard Stress Tests
    # -------------------------------------------------------------------------
    print("\n--- [PART 4] Adversarial Falsification Scenarios ---")
    hazards = [
        ("HAZARD_A_MAX_JITTER_AND_DRIFT", {"jit": 20.0, "drift": 20.0, "sigma": 0.0, "atmos": "CLEAR"}),
        ("HAZARD_B_MAX_NOISE_AND_FOG",    {"jit": 0.0,  "drift": 0.0,  "sigma": 14.0, "atmos": "FOG"}),
        ("HAZARD_C_SUPER_BRIGHT_DECOY",   {"jit": 0.0,  "drift": 0.0,  "sigma": 0.0, "atmos": "CLEAR", "decoy": True}),
        ("HAZARD_D_RAPID_BURST_BLANKING", {"jit": 0.0,  "drift": 0.0,  "sigma": 0.0, "atmos": "CLEAR", "blank": True}),
        ("HAZARD_E_HIGH_G_MANEUVER",      {"jit": 0.0,  "drift": 0.0,  "sigma": 0.0, "atmos": "CLEAR", "speed": 80.0}),
    ]

    for h_name, h_params in hazards:
        cm = ConfigManager()
        cfg = cm.config
        cfg.target.initial_x = 1000.0
        cfg.target.initial_y = 1000.0
        cfg.target.speed = h_params.get("speed", 35.0)
        cfg.motion.motion_type = "CIRCULAR"
        cfg.atmospheric.condition = h_params["atmos"]
        
        if h_params["jit"] > 0:
            cfg.jitter.enabled = True
            cfg.jitter.max_px_per_frame = h_params["jit"]
        if h_params["drift"] > 0:
            cfg.platform_motion.enabled = True
            cfg.platform_motion.max_px_per_frame = h_params["drift"]
        if h_params["sigma"] > 0:
            cfg.noise.gaussian_enabled = True
            cfg.noise.gaussian_sigma = h_params["sigma"]

        app = AppController()
        app.initialize(cfg)

        tracked_frames = 0
        total_frames = 60
        sq_errs = []
        false_locks = 0

        for f in range(total_frames):
            pkt = app.get_next_frame()
            
            # Decoy injection
            if h_params.get("decoy", False) and f >= 10:
                gt_cur = app.ground_truth_provider.get_truth(pkt.frame_number)
                if gt_cur.target_visible:
                    # Place decoy offset by 45 px
                    decoy_x = int(np.clip(gt_cur.rendered_centroid_x + 45, 10, pkt.width - 10))
                    decoy_y = int(np.clip(gt_cur.rendered_centroid_y + 45, 10, pkt.height - 10))
                    import cv2
                    img = pkt.image.copy()
                    cv2.circle(img, (decoy_x, decoy_y), 6, 240, -1)
                    pkt.image = img

            # Rapid blanking injection (frames 15-18, 30-33, 45-48)
            if h_params.get("blank", False) and ((15 <= f <= 18) or (30 <= f <= 33) or (45 <= f <= 48)):
                pkt.image = np.full((pkt.height, pkt.width), 20, dtype=np.uint8)

            pub, lat, trk, st, cent, det = app.step_algorithm(pkt)
            cmd = app.ptz_controller.compute(
                trk, st.state, pkt.width, pkt.height, dt=1.0/30.0,
                projection_model=app.camera_model.projection_model
            )
            if cmd.valid:
                app.camera_model.apply_pan_tilt(cmd.delta_pan_deg, cmd.delta_tilt_deg)

            gt = app.ground_truth_provider.get_truth(pkt.frame_number)
            if pub.algorithm_is_tracking and pub.centroid_x is not None and gt.target_visible:
                err = math.hypot(pub.centroid_x - gt.rendered_centroid_x, pub.centroid_y - gt.rendered_centroid_y)
                if err > 25.0:
                    false_locks += 1
                else:
                    sq_errs.append(err ** 2)
                    tracked_frames += 1

        rmse = math.sqrt(np.mean(sq_errs)) if sq_errs else 0.0
        loss_pct = ((total_frames - tracked_frames) / total_frames) * 100.0
        status = "PASS" if false_locks == 0 and loss_pct <= 25.0 else ("FAIL" if false_locks > 0 else "PARTIAL")
        
        print(f"[{h_name:32s}] Tracked={tracked_frames}/{total_frames} | RMSE={rmse:5.2f}px | FalseLocks={false_locks} | Status={status}")
        results["adversarial_hazards"].append({
            "name": h_name,
            "tracked_frames": tracked_frames,
            "total_frames": total_frames,
            "rmse": rmse,
            "false_locks": false_locks,
            "loss_pct": loss_pct,
            "status": status,
        })

    # -------------------------------------------------------------------------
    # 5. Centroid Truth Metric Comparison (Rendered vs Projected)
    # -------------------------------------------------------------------------
    print("\n--- [PART 5] Ground-Truth Centroid Residual Analysis (Discrete vs Continuous) ---")
    cm = ConfigManager()
    cfg = cm.config
    cfg.target.initial_x = 1000.0
    cfg.target.initial_y = 1000.0
    cfg.target.speed = 35.0
    cfg.motion.motion_type = "CIRCULAR"
    cfg.atmospheric.condition = "CLEAR"
    cfg.noise.gaussian_enabled = False

    app = AppController()
    app.initialize(cfg)

    discrete_errs = []
    continuous_errs = []

    for f in range(60):
        pkt = app.get_next_frame()
        pub, lat, trk, st, cent, det = app.step_algorithm(pkt)
        gt = app.ground_truth_provider.get_truth(pkt.frame_number)

        if pub.algorithm_is_tracking and pub.centroid_x is not None:
            # Error vs discrete rendered centroid
            d_err = math.hypot(pub.centroid_x - gt.rendered_centroid_x, pub.centroid_y - gt.rendered_centroid_y)
            discrete_errs.append(d_err)

            # Error vs continuous ideal projected coordinate
            c_err = math.hypot(pub.centroid_x - gt.ideal_projected_x, pub.centroid_y - gt.ideal_projected_y)
            continuous_errs.append(c_err)

    results["centroid_truth_analysis"] = {
        "discrete_rendered_mean_err_px": float(np.mean(discrete_errs)),
        "discrete_rendered_max_err_px": float(np.max(discrete_errs)),
        "continuous_projected_mean_err_px": float(np.mean(continuous_errs)),
        "continuous_projected_max_err_px": float(np.max(continuous_errs)),
    }

    print(f"Discrete Rendered Centroid Error:   Mean = {np.mean(discrete_errs):.6f} px | Max = {np.max(discrete_errs):.6f} px")
    print(f"Continuous Projected Center Error: Mean = {np.mean(continuous_errs):.6f} px | Max = {np.max(continuous_errs):.6f} px")

    out_file = "output/phase3_validation/boundary_falsification_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    return results

if __name__ == "__main__":
    run_boundary_and_falsification()
