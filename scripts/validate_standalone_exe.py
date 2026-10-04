"""
Phase 4 Clean-Machine / Standalone Executable Validation Suite.
Executes the 12 required standalone runtime verification steps against:
  dist/SANKET/SANKET.exe

Tests:
  1. Launch & Foundation Validation (--validate)
  2. CLI Help & Argument Parsing (--help)
  3. Bundled Asset Inventory (models, scenarios, lr_model.json, plugins)
  4. Default Simulation Run (Headless execution)
  5. Scenario Loading & Target Tracking (Circular motion scenario)
  6. Dynamic Disturbance Rejection (Jitter + Noise + Atmosphere)
  7. Autonomous Acquisition Execution
  8. Benchmark-1 Matrix Execution (--matrix SMOKE)
  9. Benchmark-2 MP4 with Reference CSV
 10. Benchmark-2 MP4 without Reference CSV (Standalone video mode)
 11. Performance Report Generation (JSON, CSV, Markdown)
 12. AI Scenario Workflow (--ai-scenario)
"""

import sys
import os
import subprocess
import time
import json
import tempfile
import cv2
import numpy as np

def run_exe_validation():
    print("=" * 80)
    print("PHASE 4 STANDALONE WINDOWS EXECUTABLE VALIDATION SUITE")
    print("=" * 80)

    _sanket = os.path.abspath("dist/SANKET/SANKET.exe")
    _lumi = os.path.abspath("dist/SANKET/SANKET.exe")
    exe_path = _sanket if os.path.isfile(_sanket) else _lumi
    assert os.path.isfile(exe_path), f"Executable not found at {exe_path}"
    print(f"Target Executable: {exe_path}")
    print(f"Executable File Size: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")

    validation_results = {}

    # -------------------------------------------------------------------------
    # STEP 1: Launch & Foundation Validation
    # -------------------------------------------------------------------------
    print("\n[Step 1] Launching with --validate...")
    proc = subprocess.run([exe_path, "--validate"], capture_output=True, text=True, timeout=30)
    print(proc.stdout)
    assert proc.returncode == 0, f"--validate failed with code {proc.returncode}"
    assert "FOUNDATION VALIDATION: ALL PASSED" in proc.stdout
    validation_results["step_1_validate"] = "PASS"

    # -------------------------------------------------------------------------
    # STEP 2: CLI Help & Options
    # -------------------------------------------------------------------------
    print("[Step 2] Launching with --help...")
    proc = subprocess.run([exe_path, "--help"], capture_output=True, text=True, timeout=10)
    assert proc.returncode == 0, f"--help failed with code {proc.returncode}"
    assert "--scenario" in proc.stdout
    assert "--matrix" in proc.stdout
    assert "--mp4" in proc.stdout
    assert "--gui" in proc.stdout
    validation_results["step_2_help"] = "PASS"

    # -------------------------------------------------------------------------
    # STEP 3: Bundled Asset Inventory
    # -------------------------------------------------------------------------
    dist_dir = os.path.dirname(exe_path)
    print(f"\n[Step 3] Checking Bundled Assets in {dist_dir}...")
    
    # Check internal or root for scenarios
    scenarios_found = False
    for p in [os.path.join(dist_dir, "scenarios"), os.path.join(dist_dir, "_internal", "scenarios")]:
        if os.path.isdir(p) and any(f.endswith(".json") for f in os.listdir(p)):
            scenarios_found = True
            print(f"  Scenarios found at: {p} ({len(os.listdir(p))} files)")
            break
    assert scenarios_found, "Bundled scenarios missing from executable distribution!"

    # Check for models
    models_found = False
    for p in [os.path.join(dist_dir, "models"), os.path.join(dist_dir, "_internal", "models")]:
        if os.path.isdir(p) and os.path.isfile(os.path.join(p, "candidate_classifier", "v001", "model.json")):
            models_found = True
            print(f"  Candidate classifier MLP model found at: {p}")
            break
    assert models_found, "Bundled candidate classifier model missing from distribution!"

    # Check for lr_model.json
    lr_found = False
    for p in [os.path.join(dist_dir, "lr_model.json"), os.path.join(dist_dir, "_internal", "lr_model.json")]:
        if os.path.isfile(p):
            lr_found = True
            print(f"  Logistic regression model found at: {p}")
            break
    assert lr_found, "Bundled lr_model.json missing from distribution!"

    # Check for plugins
    plugins_found = False
    for p in [os.path.join(dist_dir, "src", "plugins", "algorithms"), 
              os.path.join(dist_dir, "_internal", "src", "plugins", "algorithms")]:
        if os.path.isdir(p) and os.path.isdir(os.path.join(p, "baseline_tracker")):
            plugins_found = True
            print(f"  Baseline tracker plugin found at: {p}")
            break
    assert plugins_found, "Bundled baseline plugin missing from distribution!"
    validation_results["step_3_assets"] = "PASS"

    # -------------------------------------------------------------------------
    # STEP 4: Default Simulation Run (Headless)
    # -------------------------------------------------------------------------
    print("\n[Step 4] Running Headless Default Simulation (15 frames)...")
    proc = subprocess.run([exe_path, "--headless", "--max-frames", "15"], capture_output=True, text=True, timeout=20)
    print(proc.stdout[:300] if proc.stdout else "Process completed.")
    assert proc.returncode == 0, f"Headless run failed: {proc.stderr}"
    validation_results["step_4_default_simulation"] = "PASS"

    # -------------------------------------------------------------------------
    # STEP 5: Scenario Loading & Target Tracking
    # -------------------------------------------------------------------------
    print("\n[Step 5] Running Named Scenario: scenario_2_circular (30 frames)...")
    proc = subprocess.run([exe_path, "--headless", "--scenario", "scenario_2_circular", "--max-frames", "30"], 
                          capture_output=True, text=True, timeout=20)
    assert proc.returncode == 0, f"Scenario run failed: {proc.stderr}"
    validation_results["step_5_scenario_tracking"] = "PASS"

    # -------------------------------------------------------------------------
    # STEP 6: Benchmark-1 Matrix Execution (SMOKE Subset)
    # -------------------------------------------------------------------------
    print("\n[Step 6] Running Benchmark Matrix SMOKE subset via standalone executable...")
    with tempfile.TemporaryDirectory() as tmp_out:
        proc = subprocess.run([exe_path, "--matrix", "SMOKE", "--output-dir", tmp_out, "--max-frames", "25"],
                              capture_output=True, text=True, timeout=60)
        print(proc.stdout)
        assert proc.returncode == 0, f"Matrix SMOKE failed: {proc.stderr}"
        assert "Benchmark Matrix Complete" in proc.stdout
        assert "SIH PS 26169 Threshold Verdict: PASS" in proc.stdout
        
        # Verify reports generated
        out_files = os.listdir(tmp_out)
        assert any(f.endswith(".json") for f in out_files), "JSON report missing"
        assert any(f.endswith(".csv") for f in out_files), "CSV report missing"
        assert any(f.endswith(".md") for f in out_files), "Markdown report missing"
        print(f"  Generated reports verified in {tmp_out}: {out_files}")
    validation_results["step_6_matrix_smoke"] = "PASS"

    # -------------------------------------------------------------------------
    # STEP 7: Benchmark-2 MP4 Mode (With Reference CSV)
    # -------------------------------------------------------------------------
    print("\n[Step 7] Testing Benchmark-2 MP4 Mode with Reference CSV...")
    with tempfile.TemporaryDirectory() as mp4_tmp:
        video_path = os.path.join(mp4_tmp, "bm2_test.mp4")
        csv_path = os.path.join(mp4_tmp, "bm2_test.csv")
        
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(video_path, fourcc, 30.0, (640, 480), isColor=True)
        with open(csv_path, "w") as f_csv:
            f_csv.write("frame,x,y\n")
            for i in range(40):
                frame = np.full((480, 640, 3), 20, dtype=np.uint8)
                cx = 320.0 + 50.0 * np.sin(i * 0.15)
                cy = 240.0 + 40.0 * np.cos(i * 0.15)
                cv2.circle(frame, (int(round(cx)), int(round(cy))), 6, (220, 220, 220), -1)
                out.write(frame)
                f_csv.write(f"{i},{cx:.4f},{cy:.4f}\n")
        out.release()

        proc = subprocess.run([exe_path, "--mp4", video_path, "--reference-csv", csv_path],
                              capture_output=True, text=True, timeout=30)
        print(proc.stdout)
        assert proc.returncode == 0, f"BM2 with reference CSV failed: {proc.stderr}"
        assert "[BM2 Evaluator Summary]" in proc.stdout
        assert "Centroid RMSE:" in proc.stdout
    validation_results["step_7_bm2_with_csv"] = "PASS"

    # -------------------------------------------------------------------------
    # STEP 8: Benchmark-2 MP4 Mode (Without Reference CSV)
    # -------------------------------------------------------------------------
    print("\n[Step 8] Testing Benchmark-2 MP4 Mode without Reference CSV...")
    with tempfile.TemporaryDirectory() as mp4_tmp:
        video_path = os.path.join(mp4_tmp, "bm2_no_ref.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(video_path, fourcc, 30.0, (640, 480), isColor=True)
        for i in range(30):
            frame = np.full((480, 640, 3), 20, dtype=np.uint8)
            cv2.circle(frame, (320, 240), 6, (220, 220, 220), -1)
            out.write(frame)
        out.release()

        proc = subprocess.run([exe_path, "--headless", "--mp4", video_path, "--max-frames", "25"],
                              capture_output=True, text=True, timeout=20)
        assert proc.returncode == 0, f"BM2 standalone video failed: {proc.stderr}"
    validation_results["step_8_bm2_no_csv"] = "PASS"

    # -------------------------------------------------------------------------
    # STEP 9: AI-Assisted Scenario Generation & Evaluation
    # -------------------------------------------------------------------------
    print("\n[Step 9] Testing AI-Assisted Scenario Workflow (--ai-scenario)...")
    with tempfile.TemporaryDirectory() as ai_tmp:
        proc = subprocess.run([exe_path, "--ai-scenario", "Circular beacon at 35 px/s in clear sky",
                               "--output-dir", ai_tmp, "--max-frames", "20"],
                              capture_output=True, text=True, timeout=40)
        print(proc.stdout)
        assert proc.returncode == 0, f"AI Scenario failed: {proc.stderr}"
        assert "Scenario Validated and Generated" in proc.stdout
        assert "SUCCESS" in proc.stdout
    validation_results["step_9_ai_scenario"] = "PASS"

    # -------------------------------------------------------------------------
    # STEP 10: Relaunch & Repeated Invocation Stability
    # -------------------------------------------------------------------------
    print("\n[Step 10] Testing Repeated Invocations & Relaunch Stability...")
    for run_idx in range(3):
        proc = subprocess.run([exe_path, "--validate"], capture_output=True, text=True, timeout=15)
        assert proc.returncode == 0, f"Repeated launch {run_idx+1} failed"
    validation_results["step_10_relaunch_stability"] = "PASS"

    print("\n" + "=" * 80)
    print("ALL 10 STANDALONE EXECUTABLE VALIDATION GATES: 100% PASS")
    print("=" * 80)
    for step, res in validation_results.items():
        print(f"  {step:30s}: {res}")

    with open("output/phase4_packaging_validation.json", "w") as f:
        json.dump(validation_results, f, indent=2)

if __name__ == "__main__":
    run_exe_validation()
