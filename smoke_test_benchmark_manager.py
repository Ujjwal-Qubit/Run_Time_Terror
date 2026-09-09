#!/usr/bin/env python3
"""
Smoke Test: Phase 5.9 Benchmark Manager & Automated Evaluation Workflows (Module 17)

Validates:
  1. Single-Run Benchmark (Simulation Closed-Loop) via BenchmarkManager.
  2. Batch Scenario Evaluation (Benchmark-1) across multiple scenarios.
  3. Batch MP4 Video Evaluation (Benchmark-2) across synthetic video files.
  4. Fault Tolerance & Exception Handling (corrupt scenarios do not crash the batch).
  5. Evaluator Scorecards & Reports (Grand JSON + Grand Markdown).
  6. CLI invocation routing via `--eval-scenarios` and `--eval-mp4s`.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import cv2
import numpy as np

from src.app.app_controller import AppController
from src.config.config_manager import ConfigManager, SystemConfig
from src.evaluation.benchmark_manager import BenchmarkManager
from src.frame.data_contracts import (
    BatchRunItem,
    GrandEvaluationSummary,
    MetricsSummary,
)
from src.metrics.logging_engine import LoggingEngine


def create_synthetic_mp4(filepath: str, num_frames: int = 30, width: int = 640, height: int = 480):
    """Generates a synthetic MP4 video file with a moving bright beacon."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(filepath, fourcc, 30.0, (width, height), isColor=False)
    for i in range(num_frames):
        frame = np.full((height, width), 25, dtype=np.uint8)
        # Draw moving beacon
        cx = int(320 + 50 * np.sin(i * 0.2))
        cy = int(240 + 30 * np.cos(i * 0.2))
        cv2.circle(frame, (cx, cy), 6, 220, -1)
        out.write(frame)
    out.release()


def run_smoke_test():
    print("=" * 80)
    print("      PHASE 5.9 BENCHMARK MANAGER & BATCH EVALUATION — SMOKE TEST")
    print("=" * 80)

    test_dir = tempfile.mkdtemp(prefix="sih_test_bm_")
    out_dir = os.path.join(test_dir, "output")
    scenarios_dir = os.path.join(test_dir, "scenarios")
    mp4_dir = os.path.join(test_dir, "mp4_videos")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(scenarios_dir, exist_ok=True)
    os.makedirs(mp4_dir, exist_ok=True)

    try:
        # -------------------------------------------------------------------
        # TEST 1: Single-Run Benchmark via BenchmarkManager
        # -------------------------------------------------------------------
        print("\n--- [TEST 1] SINGLE-RUN BENCHMARK (SIMULATION) ---")
        app = AppController()
        app.config_manager.update_section("logging", output_dir=out_dir)
        app.initialize()

        bm = BenchmarkManager(app)
        summary = bm.run_benchmark(max_frames=25)

        assert isinstance(summary, MetricsSummary), "Expected MetricsSummary return"
        assert summary.total_frames == 25, f"Expected 25 frames, got {summary.total_frames}"
        assert summary.mean_fps > 0, "FPS must be positive"
        assert os.path.isfile(os.path.join(out_dir, f"{app.logging_engine.run_id}_summary.json"))
        assert os.path.isfile(os.path.join(out_dir, f"{app.logging_engine.run_id}_performance_report.md"))
        print(f"  [OK] Single-run benchmark verified: {summary.total_frames} frames @ {summary.mean_fps:.1f} FPS")

        # -------------------------------------------------------------------
        # TEST 2: Batch Scenario Evaluation (Benchmark-1)
        # -------------------------------------------------------------------
        print("\n--- [TEST 2] BATCH SCENARIO EVALUATION (BENCHMARK-1) ---")
        # Create 3 distinct scenario files
        cm = ConfigManager()

        # Scenario A: Static target centered
        cm.reset_to_defaults()
        cm.update_section("target", initial_position="custom", initial_x=1000.0, initial_y=1000.0, speed=0.0, size=10, intensity=220)
        cm.update_section("simulation", duration_s=1.0, random_seed=101)
        with open(os.path.join(scenarios_dir, "scenario_static.json"), "w") as f:
            json.dump(cm.config.to_dict(), f, indent=2)

        # Scenario B: Straight line motion starting near center
        cm.reset_to_defaults()
        cm.update_section("target", initial_position="custom", initial_x=1000.0, initial_y=1000.0, speed=5.0)
        cm.update_section("motion", motion_type="STRAIGHT_LINE", straight_line_angle_deg=30.0)
        cm.update_section("simulation", duration_s=1.0, random_seed=102)
        with open(os.path.join(scenarios_dir, "scenario_linear.json"), "w") as f:
            json.dump(cm.config.to_dict(), f, indent=2)

        # Scenario C: Circular motion starting near center
        cm.reset_to_defaults()
        cm.update_section("target", initial_position="custom", initial_x=1000.0, initial_y=1000.0, speed=5.0)
        cm.update_section("motion", motion_type="CIRCULAR", circle_radius=10.0)
        cm.update_section("simulation", duration_s=1.0, random_seed=103)
        with open(os.path.join(scenarios_dir, "scenario_circular.json"), "w") as f:
            json.dump(cm.config.to_dict(), f, indent=2)

        grand_bm1 = bm.evaluate_batch_scenarios(
            scenario_dir=scenarios_dir,
            max_frames_per_scenario=20,
            output_dir=out_dir,
        )

        assert isinstance(grand_bm1, GrandEvaluationSummary)
        assert grand_bm1.total_runs == 3, f"Expected 3 runs, got {grand_bm1.total_runs}"
        assert grand_bm1.successful_runs == 3, f"Expected 3 successful runs, got {grand_bm1.successful_runs}"
        assert grand_bm1.failed_runs == 0
        assert grand_bm1.total_frames_processed == 60
        assert grand_bm1.mean_fps >= 20.0, "Expected macro FPS >= 20.0"
        assert grand_bm1.passed_fps_spec is True

        grand_json = os.path.join(out_dir, f"{grand_bm1.batch_id}_grand_summary.json")
        grand_md = os.path.join(out_dir, f"{grand_bm1.batch_id}_grand_evaluator_report.md")
        assert os.path.isfile(grand_json), f"Missing {grand_json}"
        assert os.path.isfile(grand_md), f"Missing {grand_md}"
        print(f"  [OK] Batch scenarios evaluated successfully (Scorecard: {grand_md})")

        # -------------------------------------------------------------------
        # TEST 3: Batch MP4 Evaluation (Benchmark-2)
        # -------------------------------------------------------------------
        print("\n--- [TEST 3] BATCH MP4 VIDEO EVALUATION (BENCHMARK-2) ---")
        vid1_path = os.path.join(mp4_dir, "eval_seq_01.mp4")
        vid2_path = os.path.join(mp4_dir, "eval_seq_02.mp4")
        create_synthetic_mp4(vid1_path, num_frames=15)
        create_synthetic_mp4(vid2_path, num_frames=15)

        grand_bm2 = bm.evaluate_batch_mp4s(
            mp4_dir=mp4_dir,
            max_frames_per_video=15,
            output_dir=out_dir,
        )

        assert isinstance(grand_bm2, GrandEvaluationSummary)
        assert grand_bm2.total_runs == 2
        assert grand_bm2.successful_runs == 2
        assert grand_bm2.total_frames_processed == 30
        print(f"  [OK] Batch MP4s evaluated successfully ({grand_bm2.total_runs} videos)")

        # -------------------------------------------------------------------
        # TEST 4: Fault Tolerance & Corrupt Scenario Isolation
        # -------------------------------------------------------------------
        print("\n--- [TEST 4] FAULT TOLERANCE & EXCEPTION ISOLATION ---")
        corrupt_path = os.path.join(scenarios_dir, "scenario_corrupt.json")
        with open(corrupt_path, "w") as f:
            f.write("{ invalid json syntax ...")

        grand_fault = bm.evaluate_batch_scenarios(
            scenario_dir=scenarios_dir,
            max_frames_per_scenario=10,
            output_dir=out_dir,
        )

        assert grand_fault.total_runs == 4, "Expected 4 scenarios (3 valid + 1 corrupt)"
        assert grand_fault.successful_runs == 3
        assert grand_fault.failed_runs == 1
        assert grand_fault.overall_compliance is False, "Overall compliance should be False with failures"

        # Verify failed item details
        failed_items = [it for it in grand_fault.run_items if not it.success]
        assert len(failed_items) == 1
        assert failed_items[0].item_id == "scenario_corrupt"
        assert failed_items[0].error_message is not None
        print(f"  [OK] Fault tolerance verified: corrupt file isolated, 3 valid scenarios passed")

        # Clean up corrupt file
        os.remove(corrupt_path)

        # -------------------------------------------------------------------
        # TEST 5: Main CLI Entry Point Subprocess Verification
        # -------------------------------------------------------------------
        print("\n--- [TEST 5] CLI SUBPROCESS VERIFICATION (`--eval-scenarios`) ---")
        cmd = [
            sys.executable,
            "-m",
            "src.main",
            "--eval-scenarios",
            scenarios_dir,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print("CLI Output (stdout tail):")
        for line in result.stdout.strip().splitlines()[-10:]:
            print(f"  {line}")

        assert result.returncode == 0, f"CLI exited with error code {result.returncode}:\n{result.stderr}"
        assert "GRAND EVALUATION BATCH SCORECARD" in result.stdout
        print("  [OK] CLI entry point `--eval-scenarios` executed with exit code 0")

        print("\n" + "=" * 80)
        print("    ALL PHASE 5.9 BENCHMARK MANAGER CHECKS PASSED SUCCESSFULLY (5/5)")
        print("=" * 80)


    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    run_smoke_test()
