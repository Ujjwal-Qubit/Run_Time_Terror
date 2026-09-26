"""
SIH 2026 — FSOC Virtual Camera Tracking System
Application Entry Point

Usage:
    python -m src.main                     # Run with defaults
    python -m src.main --scenario <name>   # Load scenario
    python -m src.main --mp4 <path>        # MP4 mode
    python -m src.main --validate          # Validate foundation
"""

from __future__ import annotations

import argparse
import os
import sys

from src.app.app_controller import AppController
from src.config.config_manager import ConfigManager
from src.evaluation.benchmark_manager import BenchmarkManager


def parse_args(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SIH 2026 — FSOC Virtual Camera Tracking System"
    )
    parser.add_argument(
        "--scenario", type=str, default=None,
        help="Load a named scenario from the scenarios directory",
    )
    parser.add_argument(
        "--mp4", type=str, default=None,
        help="Path to MP4 file for Benchmark-2 mode",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Launch the standalone GUI for evaluator demonstration",
    )
    parser.add_argument(
        "--web", action="store_true",
        help="Launch the modern Web API server and frontend interface",
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Port for Web API server (default: 8000)",
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate foundation (config, contracts, interfaces) and exit",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to a JSON configuration file",
    )
    parser.add_argument(
        "--eval-scenarios", type=str, default=None,
        help="Batch evaluate all JSON scenario files in the given directory",
    )
    parser.add_argument(
        "--eval-mp4s", type=str, default=None,
        help="Batch evaluate all MP4/video files in the given directory",
    )
    parser.add_argument(
        "--reference-csv", type=str, default=None,
        help="Path to evaluator reference CSV (or directory) for Benchmark-2 centroid error comparison",
    )
    parser.add_argument(
        "--algorithm", type=str, default="baseline_tracker",
        help="Target tracking algorithm plugin under test (default: 'baseline_tracker')",
    )
    parser.add_argument(
        "--matrix", type=str, default=None,
        choices=["SMOKE", "CORE", "DISTURBANCE", "FULL"],
        help="Execute a Standard Benchmark Matrix subset (SMOKE, CORE, DISTURBANCE, FULL)",
    )
    parser.add_argument(
        "--ai-scenario", type=str, default=None,
        help="Natural language description for AI-assisted scenario generation and evaluation",
    )
    parser.add_argument(
        "--output-dir", type=str, default="output",
        help="Output destination directory for reports and telemetry (default: 'output')",
    )
    parser.add_argument(
        "--plugins-dir", type=str, default=None,
        help="Path to custom algorithm plugins directory",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Deterministic random seed for simulation reproducibility (default: 42)",
    )
    parser.add_argument(
        "--max-frames", type=int, default=None,
        help="Maximum frames to process per scenario",
    )
    return parser.parse_args(args=args)



def validate_foundation() -> bool:
    """
    Validate that all Phase 5.1 foundation components import and
    initialize correctly. Used for early testing.
    """
    print("=" * 60)
    print("SIH 2026 — Phase 5.1 Foundation Validation")
    print("=" * 60)

    errors = []

    # 1. Data contracts
    print("\n[1] Importing data contracts...", end=" ")
    try:
        from src.frame.data_contracts import (
            FramePacket, GroundTruth, CandidateRegion, ScoredCandidate,
            CentroidResult, TrackResult, StateDecision, PTZCommand,
            ROI, TrackerOutput, TelemetryRecord, MetricsSummary,
            TrackingState, MotionType, AtmosphericCondition, NoiseType,
            FrameSource, PlatformMotionType,
        )
        # Verify all enums
        assert len(TrackingState) == 5, "Expected 5 tracking states"
        assert len(MotionType) == 7, "Expected 7 motion types"
        assert len(AtmosphericCondition) == 5, "Expected 5 atmos conditions"
        assert len(NoiseType) == 3, "Expected 3 noise types"
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"Data contracts: {e}")

    # 2. Strategy interfaces
    print("[2] Importing strategy interfaces...", end=" ")
    try:
        from src.interfaces.strategy_interfaces import (
            IPreprocessor, ICandidateGenerator, IDetector,
            IBeaconIdentifier, ICentroidEstimator, ITracker,
            IPTZController, IFrameProvider,
        )
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"Strategy interfaces: {e}")

    # 3. Defaults classification
    print("[3] Importing defaults...", end=" ")
    try:
        from src.config import defaults

        # Verify PS_REQUIRED limits exist
        assert defaults.SCENE_MIN_WIDTH == 2000
        assert defaults.PERFORMANCE_MIN_FPS == 20
        assert defaults.PERFORMANCE_MAX_ACQUISITION_TIME_S == 2.0
        assert defaults.PERFORMANCE_MAX_TRACKING_ERROR_PX == 10.0
        assert defaults.PERFORMANCE_MAX_TARGET_LOSS_PCT == 5.0
        assert defaults.PERFORMANCE_MAX_REACQUISITION_TIME_S == 1.0
        assert defaults.PTZ_MAX_PAN_SPEED_DEG_S == 10.0
        assert defaults.JITTER_MAX_PX_PER_FRAME == 20.0
        assert defaults.TARGET_MIN_SIZE == 5
        assert defaults.TARGET_MAX_SIZE == 20

        # Verify PS_DEFAULT values
        assert defaults.CAMERA_DEFAULT_WIDTH == 640
        assert defaults.CAMERA_DEFAULT_HEIGHT == 480
        assert defaults.CAMERA_DEFAULT_FOV_H_DEG == 4.0
        assert defaults.TARGET_DEFAULT_SIZE == 10
        assert defaults.PTZ_DEFAULT_PAN_SPEED_DEG_S == 5.0

        # Verify disturbance ordering from Architecture v1.2 §7.1
        assert defaults.DISTURBANCE_ORDER[0] == "platform_motion"
        assert defaults.DISTURBANCE_ORDER[1] == "camera_jitter"
        assert defaults.DISTURBANCE_ORDER[-1] == "salt_and_pepper_noise"

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"Defaults: {e}")

    # 4. ConfigManager
    print("[4] Testing ConfigManager...", end=" ")
    try:
        from src.config.config_manager import ConfigManager, SystemConfig
        cm = ConfigManager()
        cfg = cm.config

        # Verify default values propagated correctly
        assert cfg.camera.width == 640
        assert cfg.camera.height == 480
        assert cfg.target.size == 10
        assert cfg.scene.width == 2000

        # Validate should pass with defaults
        validation_errors = cm.validate()
        assert len(validation_errors) == 0, (
            f"Default config has validation errors: {validation_errors}"
        )

        # Test snapshot
        snapshot = cm.get_snapshot()
        assert snapshot.camera.width == cfg.camera.width
        snapshot.camera.width = 1280
        assert cfg.camera.width == 640  # original unchanged

        # Test section update
        cm.update_section("target", size=15)
        assert cm.config.target.size == 15
        cm.reset_to_defaults()
        assert cm.config.target.size == 10

        # Test serialization roundtrip
        d = cm.config.to_dict()
        restored = SystemConfig.from_dict(d)
        assert restored.camera.width == 640

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"ConfigManager: {e}")

    # 5. ScenarioManager
    print("[5] Testing ScenarioManager...", end=" ")
    try:
        from src.config.scenario_manager import ScenarioManager
        import tempfile
        import shutil

        tmpdir = tempfile.mkdtemp()
        sm = ScenarioManager(scenario_dir=tmpdir)
        cm = ConfigManager()

        # Save and reload
        sm.save_scenario("test_scenario", cm)
        scenarios = sm.list_scenarios()
        assert "test_scenario" in scenarios

        cm.update_section("target", size=15)
        sm.load_scenario("test_scenario", cm)
        assert cm.config.target.size == 10  # restored from file

        shutil.rmtree(tmpdir)
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"ScenarioManager: {e}")

    # 6. LoggingEngine
    print("[6] Testing LoggingEngine...", end=" ")
    try:
        from src.metrics.logging_engine import LoggingEngine
        from src.frame.data_contracts import TelemetryRecord, MetricsSummary
        import tempfile
        import shutil
        import os

        tmpdir = tempfile.mkdtemp()
        le = LoggingEngine(output_dir=tmpdir, run_id="test_run")
        le.initialize()

        # Log a frame
        record = TelemetryRecord(
            run_id="test_run",
            frame_number=0,
            timestamp=0.0,
            source="SIMULATION",
            state="SEARCHING",
            estimated_centroid_x=320.5,
            estimated_centroid_y=240.3,
        )
        le.log_frame(record)
        assert le.get_buffer_size() == 1

        le.flush()
        assert le.get_buffer_size() == 0

        # Write summary
        summary = MetricsSummary(run_id="test_run", total_frames=1)
        le.write_summary(summary)

        le.finalize()

        # Verify files exist
        assert os.path.isfile(
            os.path.join(tmpdir, "test_run_telemetry.csv")
        )
        assert os.path.isfile(
            os.path.join(tmpdir, "test_run_summary.json")
        )

        shutil.rmtree(tmpdir)
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"LoggingEngine: {e}")

    # 7. AppController skeleton
    print("[7] Testing AppController skeleton...", end=" ")
    try:
        from src.app.app_controller import AppController
        app = AppController()
        assert app.config_manager is not None
        assert app.scenario_manager is not None
        assert app.logging_engine is not None
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"AppController: {e}")

    # 8. Data contract instantiation
    print("[8] Testing data contract instantiation...", end=" ")
    try:
        from src.frame.data_contracts import (
            FramePacket, GroundTruth, CandidateRegion, ScoredCandidate,
            CentroidResult, TrackResult, StateDecision, PTZCommand,
            ROI, TrackerOutput, TelemetryRecord, MetricsSummary,
            TrackingState,
        )

        # Verify all contracts instantiate with defaults
        fp = FramePacket(frame_number=0, timestamp=0.0, image=None,
                         width=640, height=480)
        gt = GroundTruth(frame_number=0, timestamp=0.0,
                         target_world_x=100.0, target_world_y=100.0)
        cr = CandidateRegion(bbox_x=10, bbox_y=10, bbox_w=10, bbox_h=10,
                             peak_intensity=200, mean_intensity=180, area=100)
        sc = ScoredCandidate(candidate=cr, score=0.9)
        cent = CentroidResult(x=15.5, y=15.3)
        tr = TrackResult(estimated_x=15.5, estimated_y=15.3)
        sd = StateDecision(is_valid=True, confidence_level=0.8)
        ptz = PTZCommand(delta_pan_deg=0.1, delta_tilt_deg=-0.05)
        roi = ROI(x=0, y=0, width=640, height=480)
        to = TrackerOutput(
            frame_number=0, timestamp=0.0,
            state=TrackingState.SEARCHING,
            previous_state=TrackingState.SEARCHING,
            transition_reason="",
            centroid=None, track=None,
            detection_valid=False, candidate_count=0,
            confidence=0.0, roi=roi,
        )

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(f"Data contract instantiation: {e}")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"FOUNDATION VALIDATION: {len(errors)} FAILURE(S)")
        for err in errors:
            print(f"  [X] {err}")
        return False
    else:
        print("FOUNDATION VALIDATION: ALL PASSED (8/8)")
        return True


def main(argv=None) -> None:
    args = parse_args(args=argv)

    if args.validate:
        success = validate_foundation()
        sys.exit(0 if success else 1)

    # Batch evaluation workflows (Phase 5.9 / Module 17)
    if args.eval_scenarios:
        bm = BenchmarkManager()
        grand_summary = bm.evaluate_batch_scenarios(
            scenario_dir=args.eval_scenarios,
            base_config_path=args.config,
        )
        sys.exit(0 if grand_summary.failed_runs == 0 else 1)

    if args.eval_mp4s:
        bm = BenchmarkManager()
        grand_summary = bm.evaluate_batch_mp4s(
            mp4_dir=args.eval_mp4s,
            base_config_path=args.config,
            reference_csv=args.reference_csv,
        )
        sys.exit(0 if grand_summary.failed_runs == 0 else 1)

    # Benchmark Matrix workflow (Phase 6.6 / Module 17 — DEF-02 Fix)
    if args.matrix:
        app = AppController(plugins_dir=args.plugins_dir) if args.plugins_dir else None
        bm = BenchmarkManager(app)
        algo = args.algorithm or "baseline_tracker"
        print("=" * 60)
        print(f"LumiTrack Benchmark Matrix Execution: {args.matrix.upper()}")
        print(f"Algorithm: {algo} | Seed: {args.seed} | Max Frames: {args.max_frames or 'Default'}")
        print("=" * 60 + "\n")

        try:
            matrix_results = bm.run_benchmark_matrix(
                subset=args.matrix,
                algorithms=[algo],
                random_seed=args.seed,
                max_frames=args.max_frames,
                output_dir=args.output_dir,
            )

            # Generate comprehensive reports (JSON, CSV, Markdown)
            json_p, csv_p, md_p = bm.generate_comprehensive_report(
                matrix_results=matrix_results,
                output_dir=args.output_dir,
                report_title=f"LumiTrack Benchmark Matrix — {args.matrix.upper()}",
            )

            print("\nBenchmark Matrix Complete:")
            print(f"  Total Runs: {matrix_results.total_runs} (Success: {matrix_results.successful_runs}, Failed: {matrix_results.failed_runs}, Crashed: {matrix_results.crashed_runs})")
            print(f"  Mean Algorithm FPS: {matrix_results.mean_algorithm_fps:.1f}")
            rmse_str = f"{matrix_results.mean_rmse_centroid:.3f} px" if matrix_results.mean_rmse_centroid is not None else "N/A"
            print(f"  Mean Centroid RMSE: {rmse_str}")
            print(f"  SIH PS 26169 Threshold Verdict: {'PASS' if matrix_results.passed_sih_spec else 'FAIL'}")
            print(f"\nReports generated in '{args.output_dir}':")
            print(f"  JSON:     {json_p}")
            print(f"  CSV:      {csv_p}")
            print(f"  Markdown: {md_p}")
            sys.exit(0 if matrix_results.passed_sih_spec else 1)
        except Exception as e:
            print(f"\n[ERROR] Benchmark Matrix execution failed: {e}")
            sys.exit(1)

    # AI-Assisted Scenario Workflow (Phase 6.7 / Module 17 — DEF-02 Fix)
    if args.ai_scenario:
        app = AppController(plugins_dir=args.plugins_dir) if args.plugins_dir else None
        bm = BenchmarkManager(app)
        algo = args.algorithm or "baseline_tracker"
        print("=" * 60)
        print("LumiTrack AI-Assisted Scenario Generation & Evaluation")
        print(f"Prompt: \"{args.ai_scenario}\"")
        print(f"Algorithm: {algo} | Seed: {args.seed} | Max Frames: {args.max_frames or 60}")
        print("=" * 60 + "\n")

        try:
            ai_out_dir = os.path.join(args.output_dir, "ai_scenarios")
            success, spec, res, errors = bm.run_ai_scenario(
                prompt=args.ai_scenario,
                algorithm_name=algo,
                seed=args.seed,
                max_frames=args.max_frames or 60,
                output_dir=ai_out_dir,
            )

            if not success or spec is None:
                print("[ERROR] AI Scenario rejected by validator:")
                for err in errors:
                    print(f"  [X] {err}")
                sys.exit(1)

            print(f"Scenario Validated and Generated: '{spec.scenario_id}'")
            print(f"  Trajectory: {spec.trajectory_type} | Speed: {spec.target_speed} px/s")
            print(f"  Atmospheric: {spec.atmospheric_condition}")
            if res:
                print(f"\nEvaluation Results:")
                print(f"  Outcome: {res.outcome.value}")
                print(f"  Total Frames: {res.total_frames}")
                print(f"  Algorithm FPS: {res.algorithm_fps:.1f}")
                rmse_str = f"{res.centroid_rmse:.3f} px" if res.centroid_rmse is not None else "N/A"
                print(f"  Centroid RMSE: {rmse_str}")
                print(f"  Target Loss Rate: {res.target_loss_rate:.1f}%")
                if res.json_report_path:
                    print(f"  Report: {res.json_report_path}")
                sys.exit(0 if res.outcome.value == "SUCCESS" else 1)
            else:
                sys.exit(0)
        except Exception as e:
            print(f"\n[ERROR] AI Scenario execution failed: {e}")
            sys.exit(1)

    # Normal single-run application startup
    app = AppController(plugins_dir=args.plugins_dir) if args.plugins_dir else AppController()

    if args.config:
        app.config_manager.load_from_file(args.config)

    if args.scenario:
        app.scenario_manager.load_scenario(
            args.scenario, app.config_manager
        )

    if args.mp4:
        app.config_manager.update_section(
            "simulation", mode="MP4", mp4_path=args.mp4
        )

    app.initialize()

    if args.algorithm and args.algorithm != "baseline_tracker":
        app.select_algorithm(args.algorithm)

    if args.mp4 and not args.gui and args.reference_csv:
        bm = BenchmarkManager(app)
        summary = bm.run_benchmark(reference_csv=args.reference_csv)
        print(f"\n[BM2 Evaluator Summary] Total Frames: {summary.total_frames}, Speed: {summary.mean_fps:.1f} FPS")
        print(f"  Centroid RMSE: {summary.rmse_centroid:.3f} px (Coverage: {summary.reference_frame_coverage_pct:.1f}%)")
        print(f"  Mean Centroid Error: {summary.mean_centroid_error:.3f} px, Max: {summary.max_centroid_error:.3f} px")
        sys.exit(0)

    if args.web:
        import uvicorn
        print(f"\n[LumiTrack Web] Starting Modern Web API & Frontend on http://127.0.0.1:{args.port}")
        uvicorn.run("src.api.server:app", host="127.0.0.1", port=args.port, reload=False)
    elif args.gui:
        from src.app.gui import launch_gui
        launch_gui(app)
    else:
        app.run()


if __name__ == "__main__":
    main()
