"""
Phase 5.1 Foundation Tests

Tests cover:
  - Data contract enums and dataclasses
  - Strategy interface definitions
  - Defaults classification and values
  - ConfigManager CRUD and validation
  - ScenarioManager save/load
  - LoggingEngine buffering and file I/O
  - AppController skeleton
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

class TestDataContracts:
    """Test all data contract enums and dataclasses."""

    def test_tracking_state_enum(self):
        from src.frame.data_contracts import TrackingState
        assert len(TrackingState) == 5
        assert TrackingState.SEARCHING.value == "SEARCHING"
        assert TrackingState.ACQUIRING.value == "ACQUIRING"
        assert TrackingState.TRACKING.value == "TRACKING"
        assert TrackingState.LOST.value == "LOST"
        assert TrackingState.REACQUIRING.value == "REACQUIRING"

    def test_motion_type_enum(self):
        from src.frame.data_contracts import MotionType
        mandatory = {
            MotionType.STRAIGHT_LINE, MotionType.CIRCULAR,
            MotionType.FIGURE_8, MotionType.RANDOM
        }
        assert len(mandatory) == 4

    def test_atmospheric_condition_enum(self):
        from src.frame.data_contracts import AtmosphericCondition
        assert len(AtmosphericCondition) == 5

    def test_noise_type_enum(self):
        from src.frame.data_contracts import NoiseType
        assert len(NoiseType) == 3

    def test_frame_packet_creation(self):
        from src.frame.data_contracts import FramePacket, FrameSource
        fp = FramePacket(
            frame_number=0, timestamp=0.0,
            image=None, width=640, height=480
        )
        assert fp.frame_number == 0
        assert fp.width == 640
        assert fp.height == 480
        assert fp.source == FrameSource.SIMULATION

    def test_ground_truth_isolation(self):
        """Ground truth has world, ideal, and rendered positions."""
        from src.frame.data_contracts import GroundTruth
        gt = GroundTruth(
            frame_number=0, timestamp=0.0,
            target_world_x=1000, target_world_y=1000,
            ideal_projected_x=320, ideal_projected_y=240,
            rendered_centroid_x=320.3, rendered_centroid_y=240.1,
        )
        assert gt.target_world_x == 1000
        assert gt.ideal_projected_x == 320
        assert gt.rendered_centroid_x == 320.3

    def test_centroid_result_subpixel(self):
        """CentroidResult must preserve sub-pixel coordinates."""
        from src.frame.data_contracts import CentroidResult
        c = CentroidResult(x=320.7654, y=240.1234)
        assert isinstance(c.x, float)
        assert c.x == 320.7654
        assert c.y == 240.1234

    def test_candidate_region(self):
        from src.frame.data_contracts import CandidateRegion
        cr = CandidateRegion(
            bbox_x=100, bbox_y=200, bbox_w=10, bbox_h=10,
            peak_intensity=220, mean_intensity=200, area=100
        )
        assert cr.area == 100
        assert cr.peak_intensity == 220

    def test_scored_candidate(self):
        from src.frame.data_contracts import CandidateRegion, ScoredCandidate
        cr = CandidateRegion(
            bbox_x=0, bbox_y=0, bbox_w=10, bbox_h=10,
            peak_intensity=200, mean_intensity=180, area=100,
        )
        sc = ScoredCandidate(candidate=cr, score=0.95, is_beacon=True)
        assert sc.score == 0.95
        assert sc.is_beacon is True

    def test_track_result(self):
        from src.frame.data_contracts import TrackResult
        tr = TrackResult(
            estimated_x=320.5, estimated_y=240.3,
            velocity_x=1.2, velocity_y=-0.5,
            confidence=0.85, track_age=10,
            predicted_x=321.7, predicted_y=239.8,
        )
        assert tr.confidence == 0.85
        assert tr.predicted_x == 321.7

    def test_ptz_command(self):
        from src.frame.data_contracts import PTZCommand
        cmd = PTZCommand(delta_pan_deg=0.1, delta_tilt_deg=-0.05)
        assert cmd.delta_pan_deg == 0.1

    def test_telemetry_record_fields(self):
        """Verify all required telemetry fields exist."""
        from src.frame.data_contracts import TelemetryRecord
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(TelemetryRecord)}
        required = {
            "run_id", "frame_number", "timestamp", "source", "state",
            "previous_state", "transition_reason", "target_present",
            "ground_truth_x", "ground_truth_y",
            "ideal_projected_x", "ideal_projected_y",
            "rendered_centroid_x", "rendered_centroid_y",
            "estimated_centroid_x", "estimated_centroid_y",
            "centroid_error_ideal", "centroid_error_rendered",
            "tracking_error", "detection_confidence", "candidate_count",
            "detection_valid",
            "pan_angle", "tilt_angle", "pan_command", "tilt_command",
            "processing_time_ms", "fps",
        }
        missing = required - field_names
        assert not missing, f"Missing telemetry fields: {missing}"


# ---------------------------------------------------------------------------
# Strategy interfaces
# ---------------------------------------------------------------------------

class TestStrategyInterfaces:
    """Verify all strategy interfaces are abstract and importable."""

    def test_interfaces_are_abstract(self):
        from src.interfaces.strategy_interfaces import (
            IPreprocessor, ICandidateGenerator, IDetector,
            IBeaconIdentifier, ICentroidEstimator, ITracker,
            IPTZController, IFrameProvider,
        )
        import abc

        for cls in [
            IPreprocessor, ICandidateGenerator, IDetector,
            IBeaconIdentifier, ICentroidEstimator, ITracker,
            IPTZController, IFrameProvider,
        ]:
            assert issubclass(cls, abc.ABC), (
                f"{cls.__name__} must be abstract"
            )
            # Should not be directly instantiable
            with pytest.raises(TypeError):
                cls()

    def test_interface_method_count(self):
        """Each interface should have the expected abstract methods."""
        from src.interfaces.strategy_interfaces import (
            IPreprocessor, ICandidateGenerator, IDetector,
            IBeaconIdentifier, ICentroidEstimator, ITracker,
            IPTZController, IFrameProvider,
        )
        # Minimum expected abstract method count
        assert len(IPreprocessor.__abstractmethods__) >= 2
        assert len(ICandidateGenerator.__abstractmethods__) >= 2
        assert len(IDetector.__abstractmethods__) >= 2
        assert len(IBeaconIdentifier.__abstractmethods__) >= 2
        assert len(ICentroidEstimator.__abstractmethods__) >= 2
        assert len(ITracker.__abstractmethods__) >= 4
        assert len(IPTZController.__abstractmethods__) >= 3
        assert len(IFrameProvider.__abstractmethods__) >= 4


# ---------------------------------------------------------------------------
# Defaults classification
# ---------------------------------------------------------------------------

class TestDefaults:
    """Verify defaults are correctly classified and valued."""

    def test_ps_required_limits(self):
        from src.config import defaults
        # These are hard PS requirements — must not change
        assert defaults.SCENE_MIN_WIDTH == 2000
        assert defaults.SCENE_MIN_HEIGHT == 2000
        assert defaults.TARGET_MIN_SIZE == 5
        assert defaults.TARGET_MAX_SIZE == 20
        assert defaults.CAMERA_MIN_UPDATE_RATE_HZ == 30
        assert defaults.PTZ_MIN_UPDATE_RATE_HZ == 20
        assert defaults.PTZ_MAX_PAN_SPEED_DEG_S == 10.0
        assert defaults.PTZ_MAX_TILT_SPEED_DEG_S == 10.0
        assert defaults.JITTER_MAX_PX_PER_FRAME == 20.0
        assert defaults.PLATFORM_MOTION_MAX_PX_PER_FRAME == 20.0
        assert defaults.PERFORMANCE_MIN_FPS == 20
        assert defaults.PERFORMANCE_MAX_ACQUISITION_TIME_S == 2.0
        assert defaults.PERFORMANCE_MAX_TRACKING_ERROR_PX == 10.0
        assert defaults.PERFORMANCE_MAX_TARGET_LOSS_PCT == 5.0
        assert defaults.PERFORMANCE_MAX_REACQUISITION_TIME_S == 1.0

    def test_ps_defaults(self):
        from src.config import defaults
        assert defaults.CAMERA_DEFAULT_WIDTH == 640
        assert defaults.CAMERA_DEFAULT_HEIGHT == 480
        assert defaults.CAMERA_DEFAULT_FOV_H_DEG == 4.0
        assert defaults.CAMERA_DEFAULT_FOV_V_DEG == 3.0
        assert defaults.TARGET_DEFAULT_SIZE == 10
        assert defaults.TARGET_DEFAULT_SHAPE == "square"
        assert defaults.PTZ_DEFAULT_PAN_SPEED_DEG_S == 5.0
        assert defaults.PTZ_DEFAULT_TILT_SPEED_DEG_S == 5.0
        assert defaults.NOISE_SP_DEFAULT_DENSITY == 0.10

    def test_disturbance_order_matches_architecture(self):
        """Verify order matches Architecture v1.2 §7.1."""
        from src.config import defaults
        order = defaults.DISTURBANCE_ORDER
        assert order[0] == "platform_motion"
        assert order[1] == "camera_jitter"
        assert order[2] == "atmospheric"
        assert order[3] == "poisson_noise"
        assert order[4] == "gaussian_noise"
        assert order[5] == "salt_and_pepper_noise"

    def test_engineering_defaults_are_not_ps_values(self):
        """Engineering defaults should be separate from PS values."""
        from src.config import defaults
        # Background intensity is engineering default, not PS
        assert defaults.SCENE_BACKGROUND_INTENSITY == 30
        # Target intensity is engineering default
        assert defaults.TARGET_DEFAULT_INTENSITY == 220
        # Kalman parameters are engineering defaults
        assert defaults.KALMAN_PROCESS_NOISE_POS == 1.0
        # PTZ gain and deadband are engineering defaults
        assert defaults.PTZ_DEFAULT_PROPORTIONAL_GAIN == 0.5
        assert defaults.PTZ_DEFAULT_DEADBAND_PX == 5.0

    def test_mandatory_motion_types(self):
        from src.config import defaults
        mandatory = defaults.MOTION_MANDATORY_TYPES
        assert "STRAIGHT_LINE" in mandatory
        assert "CIRCULAR" in mandatory
        assert "FIGURE_8" in mandatory
        assert "RANDOM" in mandatory
        assert len(mandatory) == 4


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

class TestConfigManager:
    """Test ConfigManager CRUD, validation, and serialization."""

    def test_default_config_valid(self):
        from src.config.config_manager import ConfigManager
        cm = ConfigManager()
        errors = cm.validate()
        assert errors == [], f"Default config invalid: {errors}"

    def test_update_section(self):
        from src.config.config_manager import ConfigManager
        cm = ConfigManager()
        cm.update_section("target", size=15)
        assert cm.config.target.size == 15

    def test_update_unknown_section_raises(self):
        from src.config.config_manager import ConfigManager
        cm = ConfigManager()
        with pytest.raises(ValueError):
            cm.update_section("nonexistent", foo=1)

    def test_update_unknown_param_raises(self):
        from src.config.config_manager import ConfigManager
        cm = ConfigManager()
        with pytest.raises(ValueError):
            cm.update_section("target", nonexistent_param=42)

    def test_snapshot_isolation(self):
        from src.config.config_manager import ConfigManager
        cm = ConfigManager()
        snap = cm.get_snapshot()
        snap.target.size = 20
        assert cm.config.target.size == 10  # unchanged

    def test_reset_to_defaults(self):
        from src.config.config_manager import ConfigManager
        cm = ConfigManager()
        cm.update_section("target", size=15)
        cm.reset_to_defaults()
        assert cm.config.target.size == 10

    def test_serialization_roundtrip(self):
        from src.config.config_manager import ConfigManager, SystemConfig
        cm = ConfigManager()
        cm.update_section("target", size=15)
        d = cm.config.to_dict()
        restored = SystemConfig.from_dict(d)
        assert restored.target.size == 15
        assert restored.camera.width == 640

    def test_validation_catches_bad_scene_size(self):
        from src.config.config_manager import ConfigManager
        cm = ConfigManager()
        cm.update_section("scene", width=100)
        errors = cm.validate()
        assert any("Scene width" in e for e in errors)

    def test_validation_catches_bad_target_size(self):
        from src.config.config_manager import ConfigManager
        cm = ConfigManager()
        cm.update_section("target", size=50)
        errors = cm.validate()
        assert any("Target size" in e for e in errors)

    def test_validation_catches_bad_ptz_speed(self):
        from src.config.config_manager import ConfigManager
        cm = ConfigManager()
        cm.update_section("ptz", max_pan_speed_deg_s=20.0)
        errors = cm.validate()
        assert any("Pan speed" in e for e in errors)

    def test_file_save_load(self):
        from src.config.config_manager import ConfigManager
        cm = ConfigManager()
        cm.update_section("target", size=15)

        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "test_config.json")
        try:
            cm.save_to_file(path)
            assert os.path.isfile(path)

            cm2 = ConfigManager()
            cm2.load_from_file(path)
            assert cm2.config.target.size == 15
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# ScenarioManager
# ---------------------------------------------------------------------------

class TestScenarioManager:
    def test_save_and_load(self):
        from src.config.scenario_manager import ScenarioManager
        from src.config.config_manager import ConfigManager

        tmpdir = tempfile.mkdtemp()
        try:
            sm = ScenarioManager(scenario_dir=tmpdir)
            cm = ConfigManager()
            cm.update_section("target", size=15)

            sm.save_scenario("test_s", cm)
            assert "test_s" in sm.list_scenarios()

            cm.reset_to_defaults()
            assert cm.config.target.size == 10

            sm.load_scenario("test_s", cm)
            assert cm.config.target.size == 15
        finally:
            shutil.rmtree(tmpdir)

    def test_load_nonexistent_raises(self):
        from src.config.scenario_manager import ScenarioManager
        from src.config.config_manager import ConfigManager

        tmpdir = tempfile.mkdtemp()
        try:
            sm = ScenarioManager(scenario_dir=tmpdir)
            cm = ConfigManager()
            with pytest.raises(FileNotFoundError):
                sm.load_scenario("nonexistent", cm)
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# LoggingEngine
# ---------------------------------------------------------------------------

class TestLoggingEngine:
    def test_buffer_and_flush(self):
        from src.metrics.logging_engine import LoggingEngine
        from src.frame.data_contracts import TelemetryRecord

        tmpdir = tempfile.mkdtemp()
        try:
            le = LoggingEngine(output_dir=tmpdir, run_id="test")
            le.initialize()

            for i in range(5):
                le.log_frame(TelemetryRecord(frame_number=i))
            assert le.get_buffer_size() == 5

            le.flush()
            assert le.get_buffer_size() == 0

            le.finalize()

            csv_path = os.path.join(tmpdir, "test_telemetry.csv")
            assert os.path.isfile(csv_path)

            # Verify CSV has header + 5 rows
            with open(csv_path) as f:
                lines = f.readlines()
            assert len(lines) == 6  # header + 5 data rows
        finally:
            shutil.rmtree(tmpdir)

    def test_summary_json(self):
        from src.metrics.logging_engine import LoggingEngine
        from src.frame.data_contracts import MetricsSummary

        tmpdir = tempfile.mkdtemp()
        try:
            le = LoggingEngine(output_dir=tmpdir, run_id="test")
            le.initialize()

            summary = MetricsSummary(
                run_id="test", total_frames=100, mean_fps=30.5
            )
            le.write_summary(summary)
            le.finalize()

            json_path = os.path.join(tmpdir, "test_summary.json")
            assert os.path.isfile(json_path)

            with open(json_path) as f:
                data = json.load(f)
            assert data["total_frames"] == 100
            assert data["mean_fps"] == 30.5
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# AppController skeleton
# ---------------------------------------------------------------------------

class TestAppController:
    def test_creation(self):
        from src.app.app_controller import AppController
        app = AppController()
        assert app.config_manager is not None
        assert app.scenario_manager is not None
        assert app.logging_engine is not None

    def test_module_slots_exist(self):
        """All 19 module slots should be declared."""
        from src.app.app_controller import AppController
        app = AppController()
        # Production module slots
        assert hasattr(app, '_scene_manager')
        assert hasattr(app, '_target_manager')
        assert hasattr(app, '_camera_model')
        assert hasattr(app, '_disturbance_engine')
        assert hasattr(app, '_frame_provider')
        assert hasattr(app, '_detection_engine')
        assert hasattr(app, '_centroid_estimator')
        assert hasattr(app, '_tracking_engine')
        assert hasattr(app, '_tracking_state_manager')
        assert hasattr(app, '_ptz_controller')
        assert hasattr(app, '_ground_truth_provider')
        assert hasattr(app, '_metrics_engine')
        assert hasattr(app, '_benchmark_manager')
        assert hasattr(app, '_visualization_engine')
        assert hasattr(app, '_gui_controller')
