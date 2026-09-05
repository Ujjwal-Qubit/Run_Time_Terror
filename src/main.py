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
import sys

from src.app.app_controller import AppController
from src.config.config_manager import ConfigManager


def parse_args() -> argparse.Namespace:
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
        "--validate", action="store_true",
        help="Validate foundation (config, contracts, interfaces) and exit",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to a JSON configuration file",
    )
    return parser.parse_args()


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
            print(f"  ✗ {err}")
        return False
    else:
        print("FOUNDATION VALIDATION: ALL PASSED (8/8)")
        return True


def main() -> None:
    args = parse_args()

    if args.validate:
        success = validate_foundation()
        sys.exit(0 if success else 1)

    # Normal application startup
    app = AppController()

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
    
    if args.gui:
        from src.app.gui_controller import launch_gui
        launch_gui(app)
    else:
        app.run()


if __name__ == "__main__":
    main()
