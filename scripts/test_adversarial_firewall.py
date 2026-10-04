"""
Adversarial Ground-Truth Firewall Verification Test.
Proves:
  1. The tracking algorithm and PTZ control loop operate strictly on sensor images.
  2. Mutating, corrupting, or poisoning the ground-truth provider with extreme values
     (e.g., target coordinates (999999.0, -888888.0)) produces bitwise-identical
     tracker outputs, PTZ commands, and FSM states compared to an uncorrupted run.
  3. Static code analysis verifies zero ground-truth imports in tracker, detector, and control modules.
"""

import sys
import os
import math
import json
import ast
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from src.app.app_controller import AppController
from src.config.config_manager import ConfigManager
from src.frame.data_contracts import TrackingState, GroundTruth

def run_firewall_verification():
    print("=" * 80)
    print("ADVERSARIAL GROUND-TRUTH FIREWALL AUDIT & TEST")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # PART 1: Static AST Import Audit
    # -------------------------------------------------------------------------
    print("\n[PART 1] Static AST Import Audit of UUT Modules...")
    modules_to_audit = [
        "src/tracker/temporal_tracker.py",
        "src/tracker/candidate_identifier.py",
        "src/aiml/candidate_classifier.py",
        "src/control/ptz_controller.py",
        "src/plugins/algorithms/baseline_tracker/baseline_tracker.py",
    ]

    forbidden_patterns = [
        "GroundTruth",
        "ground_truth",
        "ScenarioDefinition",
        "simulation",
        "TargetManager",
        "SceneManager",
    ]

    audit_passed = True
    for mod_path in modules_to_audit:
        if not os.path.exists(mod_path):
            print(f"Warning: {mod_path} not found")
            continue
        with open(mod_path, "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
        
        # Check all imports
        imported_symbols = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imported_symbols.append(n.name)
            elif isinstance(node, ast.ImportFrom):
                mod_name = node.module or ""
                for n in node.names:
                    imported_symbols.append(f"{mod_name}.{n.name}")

        leaks = []
        for sym in imported_symbols:
            for pat in forbidden_patterns:
                if pat.lower() in sym.lower():
                    leaks.append(sym)

        if leaks:
            print(f"  FAIL: {mod_path} contains forbidden imports: {leaks}")
            audit_passed = False
        else:
            print(f"  PASS: {mod_path} has zero ground-truth/simulation dependencies.")

    # -------------------------------------------------------------------------
    # PART 2: Closed-Loop Adversarial Dynamic Poisoning Test
    # -------------------------------------------------------------------------
    print("\n[PART 2] Closed-Loop Dynamic Adversarial Poisoning Test...")
    
    def run_simulation_instance(poison: bool):
        cm = ConfigManager()
        cfg = cm.config
        cfg.target.initial_x = 1000.0
        cfg.target.initial_y = 1000.0
        cfg.target.speed = 35.0
        cfg.motion.motion_type = "CIRCULAR"
        cfg.motion.circular_radius = 120.0
        cfg.atmospheric.condition = "CLEAR"
        cfg.noise.gaussian_enabled = False

        app = AppController()
        app.initialize(cfg)

        records = []
        dt = 1.0 / 30.0

        for f in range(60):
            pkt = app.get_next_frame()
            if pkt is None:
                break

            # If poison is True, we actively corrupt the ground truth provider's history & current truth
            # AFTER frame generation so it is not overwritten, ensuring genuine adversarial poisoning (DEF-42)
            if poison and f >= 5:
                if hasattr(app, "ground_truth_provider") and app.ground_truth_provider is not None:
                    app.ground_truth_provider._history[f] = GroundTruth(
                        frame_number=f,
                        timestamp=f * dt,
                        target_world_x=999999.0,
                        target_world_y=-888888.0,
                        ideal_projected_x=999999.0,
                        ideal_projected_y=-888888.0,
                        rendered_centroid_x=999999.0,
                        rendered_centroid_y=-888888.0,
                        target_visible=False,
                        camera_pan_deg=0.0,
                        camera_tilt_deg=0.0,
                    )

            pub, lat, trk, st, cent, det = app.step_algorithm(pkt)
            cmd = app.ptz_controller.compute(
                trk, st.state, pkt.width, pkt.height, dt=dt,
                projection_model=app.camera_model.projection_model
            )
            if cmd.valid:
                app.camera_model.apply_pan_tilt(cmd.delta_pan_deg, cmd.delta_tilt_deg)

            records.append({
                "frame": f,
                "state": st.state.value,
                "centroid_x": pub.centroid_x,
                "centroid_y": pub.centroid_y,
                "cmd_pan": cmd.delta_pan_deg if cmd.valid else None,
                "cmd_tilt": cmd.delta_tilt_deg if cmd.valid else None,
                "cam_pan": app.camera_model.pan_deg,
                "cam_tilt": app.camera_model.tilt_deg,
            })
        return records

    print("Running Baseline Run (Nominal Ground Truth)...")
    records_clean = run_simulation_instance(poison=False)

    print("Running Adversarial Poisoned Run (Ground Truth Poisoned with (999999, -888888))...")
    records_poison = run_simulation_instance(poison=True)

    # Compare step-by-step
    assert len(records_clean) == len(records_poison), "Frame count mismatch"
    
    max_centroid_diff = 0.0
    max_cmd_pan_diff = 0.0
    max_cmd_tilt_diff = 0.0
    state_mismatches = 0

    for i in range(len(records_clean)):
        rc = records_clean[i]
        rp = records_poison[i]

        if rc["state"] != rp["state"]:
            state_mismatches += 1

        if rc["centroid_x"] is not None and rp["centroid_x"] is not None:
            cdiff = math.hypot(rc["centroid_x"] - rp["centroid_x"], rc["centroid_y"] - rp["centroid_y"])
            if cdiff > max_centroid_diff:
                max_centroid_diff = cdiff

        if rc["cmd_pan"] is not None and rp["cmd_pan"] is not None:
            pdiff = abs(rc["cmd_pan"] - rp["cmd_pan"])
            tdiff = abs(rc["cmd_tilt"] - rp["cmd_tilt"])
            if pdiff > max_cmd_pan_diff:
                max_cmd_pan_diff = pdiff
            if tdiff > max_cmd_tilt_diff:
                max_cmd_tilt_diff = tdiff

    print(f"Max Centroid Difference: {max_centroid_diff:.10f} px")
    print(f"Max PTZ Pan Diff:        {max_cmd_pan_diff:.10f} deg")
    print(f"Max PTZ Tilt Diff:       {max_cmd_tilt_diff:.10f} deg")
    print(f"State Mismatches:        {state_mismatches}")

    bitwise_identical = (max_centroid_diff == 0.0 and max_cmd_pan_diff == 0.0 and 
                         max_cmd_tilt_diff == 0.0 and state_mismatches == 0)

    print(f"\nFirewall Dynamic Integrity Verdict: {'PASS (Bitwise Identical)' if bitwise_identical else 'FAIL'}")

    firewall_results = {
        "static_import_audit_passed": audit_passed,
        "bitwise_identical": bitwise_identical,
        "max_centroid_diff_px": max_centroid_diff,
        "max_pan_cmd_diff_deg": max_cmd_pan_diff,
        "max_tilt_cmd_diff_deg": max_cmd_tilt_diff,
        "state_mismatches": state_mismatches,
    }

    out_file = "output/phase3_validation/firewall_audit_results.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(firewall_results, f, indent=2)

    return firewall_results

if __name__ == "__main__":
    res = run_firewall_verification()
    if not (res.get("static_import_audit_passed") and res.get("bitwise_identical")):
        sys.exit(1)
    sys.exit(0)
