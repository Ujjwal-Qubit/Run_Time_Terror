"""
Phase 6.4 Verification Suite — AppController Algorithm Injection & Plugin Integration.

Tests cover:
  1. Plugin discovery via AppController
  2. Default algorithm selection (baseline_tracker)
  3. Explicit algorithm selection
  4. Invalid algorithm selection error handling
  5. Custom algorithm plugin loading & injection
  6. Ground-truth firewall enforcement in PublicFramePacket
  7. Process_frame exception containment (no platform crash)
  8. Malformed result containment (no platform crash)
  9. BM1 simulation execution with baseline algorithm plugin
 10. BM1 simulation execution with custom mock algorithm plugin
 11. BenchmarkManager algorithm injection & batch run
 12. AppController reset lifecycle with active algorithm
"""

import os
import pytest
import numpy as np
from typing import Dict, Any, Optional

from src.app.app_controller import AppController
from src.api.v1 import (
    ITrackingAlgorithm,
    FramePacket as PublicFramePacket,
    TrackingResult as PublicTrackingResult,
)
from src.frame.data_contracts import TrackingState
from src.plugins.models import PluginManifest, LoadedPlugin


class MockCustomAlgorithm(ITrackingAlgorithm):
    """A mock algorithm plugin to test dynamic injection of non-baseline algorithms."""

    def __init__(self) -> None:
        self.initialized = False
        self.reset_called = False
        self.frame_count = 0
        self.fixed_x = 320.0
        self.fixed_y = 240.0
        self.should_raise = False
        self.return_invalid = False

    def initialize(self, config: Dict[str, Any]) -> bool:
        self.initialized = True
        return True

    def process_frame(self, frame_packet: PublicFramePacket) -> PublicTrackingResult:
        if self.should_raise:
            raise RuntimeError("Simulated algorithm crash inside process_frame!")
        if self.return_invalid:
            return None  # type: ignore

        self.frame_count += 1
        return PublicTrackingResult(
            algorithm_is_tracking=True,
            centroid_x=self.fixed_x,
            centroid_y=self.fixed_y,
            confidence=0.95,
            roi=(int(self.fixed_x - 10), int(self.fixed_y - 10), 20, 20),
        )

    def reset(self) -> None:
        self.reset_called = True
        self.frame_count = 0


def test_plugin_discovery_via_app():
    """Verify AppController discovers algorithm plugins via PluginLoader."""
    app = AppController()
    discovered = app.discover_algorithms()
    assert isinstance(discovered, dict)
    assert "baseline_tracker" in discovered

    avail = app.get_available_algorithms()
    assert isinstance(avail, list)
    assert "baseline_tracker" in avail
    assert avail == sorted(avail)


def test_default_algorithm_selection():
    """Verify AppController.initialize() defaults to baseline_tracker."""
    app = AppController()
    app.initialize()
    assert app.active_algorithm_name == "baseline_tracker"
    assert app.active_algorithm is not None
    assert isinstance(app.active_algorithm, ITrackingAlgorithm)
    assert app.active_plugin is not None
    assert app.active_plugin.manifest.name == "baseline_tracker"
    assert app.algorithm_error is None


def test_explicit_algorithm_selection():
    """Verify selecting an algorithm by name initializes it correctly."""
    app = AppController()
    app.initialize()
    success = app.select_algorithm("baseline_tracker")
    assert success is True
    assert app.active_algorithm_name == "baseline_tracker"
    assert app.active_algorithm is not None
    assert app.algorithm_error is None


def test_select_algorithm_invalid():
    """Verify selecting an invalid algorithm returns False and records error."""
    app = AppController()
    app.initialize()
    success = app.select_algorithm("non_existent_algorithm_xyz")
    assert success is False
    assert app.algorithm_error is not None
    assert "non_existent_algorithm_xyz" in app.algorithm_error


def test_custom_algorithm_injection():
    """Verify AppController can run an injected custom algorithm plugin."""
    app = AppController()
    app.initialize()

    mock_algo = MockCustomAlgorithm()
    manifest = PluginManifest(
        name="mock_tracker",
        version="1.0.0",
        api_version="1.0.0",
        author="Tester",
        description="Mock tracker for testing",
        entry_point="mock:MockCustomAlgorithm",
    )
    from pathlib import Path
    loaded_plugin = LoadedPlugin(
        manifest=manifest,
        plugin_dir=Path("."),
        algorithm_class=MockCustomAlgorithm,
        instance=mock_algo,
    )

    # Manually activate custom plugin in app
    app._active_algorithm = mock_algo
    app._active_algorithm_name = "mock_tracker"
    app._active_plugin = loaded_plugin
    mock_algo.initialize({})

    packet = app.get_next_frame()
    assert packet is not None

    pub_res, lat_ms, track_res, state_res, cent_res, det_res = app.step_algorithm(packet)
    assert pub_res.algorithm_is_tracking is True
    assert pub_res.centroid_x == 320.0
    assert pub_res.centroid_y == 240.0
    assert mock_algo.frame_count == 1
    assert track_res is not None
    assert track_res.estimated_x == 320.0
    assert track_res.estimated_y == 240.0
    assert state_res.state == TrackingState.TRACKING


def test_ground_truth_firewall_in_step_algorithm():
    """Verify PublicFramePacket passed to algorithm has no ground truth."""
    app = AppController()
    app.initialize()

    packet = app.get_next_frame()
    assert packet is not None

    captured_packets = []

    class FirewallAuditAlgorithm(MockCustomAlgorithm):
        def process_frame(self, frame_packet: PublicFramePacket) -> PublicTrackingResult:
            captured_packets.append(frame_packet)
            return super().process_frame(frame_packet)

    audit_algo = FirewallAuditAlgorithm()
    app._active_algorithm = audit_algo
    app._active_algorithm_name = "firewall_audit"

    app.step_algorithm(packet)
    assert len(captured_packets) == 1
    cp = captured_packets[0]

    assert isinstance(cp, PublicFramePacket)
    assert not hasattr(cp, "target_truth")
    assert not hasattr(cp, "ground_truth")
    assert not hasattr(cp, "camera_truth")
    assert not hasattr(cp, "disturbance_state")
    assert cp.image is not None
    assert cp.image.shape == (packet.height, packet.width)


def test_step_algorithm_exception_containment():
    """Verify algorithm exception inside process_frame() does not crash platform."""
    app = AppController()
    app.initialize()

    crashing_algo = MockCustomAlgorithm()
    crashing_algo.should_raise = True
    app._active_algorithm = crashing_algo
    app._active_algorithm_name = "crashing_algo"

    packet = app.get_next_frame()
    assert packet is not None

    # step_algorithm should not raise, but catch and return fallback
    pub_res, lat_ms, track_res, state_res, cent_res, det_res = app.step_algorithm(packet)
    assert pub_res.algorithm_is_tracking is False
    assert state_res.state == TrackingState.SEARCHING
    assert app.algorithm_error is not None
    assert "Simulated algorithm crash" in app.algorithm_error


def test_step_algorithm_malformed_result_containment():
    """Verify malformed return (e.g. None) does not crash platform."""
    app = AppController()
    app.initialize()

    malformed_algo = MockCustomAlgorithm()
    malformed_algo.return_invalid = True
    app._active_algorithm = malformed_algo
    app._active_algorithm_name = "malformed_algo"

    packet = app.get_next_frame()
    assert packet is not None

    pub_res, lat_ms, track_res, state_res, cent_res, det_res = app.step_algorithm(packet)
    assert pub_res.algorithm_is_tracking is False
    assert state_res.state == TrackingState.SEARCHING
    assert app.algorithm_error is not None
    assert "PublicTrackingResult" in app.algorithm_error


def test_bm1_simulation_with_baseline_plugin():
    """Verify 15 frames of BM1 simulation run cleanly through baseline algorithm plugin."""
    app = AppController()
    app.initialize()
    assert app.active_algorithm_name == "baseline_tracker"

    for _ in range(15):
        packet = app.get_next_frame()
        if packet is None:
            break
        pub_res, lat_ms, track_res, state_res, cent_res, det_res = app.step_algorithm(packet)
        assert isinstance(pub_res, PublicTrackingResult)
        assert lat_ms >= 0.0

        # Step PTZ with algorithm result
        ptz_cmd = app.ptz_controller.compute(
            track_result=track_res,
            tracking_state=state_res.state,
            frame_width=packet.width,
            frame_height=packet.height,
            dt=1.0 / 30.0,
        )
        assert ptz_cmd is not None

        gt = app.ground_truth_provider.get_truth(packet.frame_number) if app.ground_truth_provider else None
        cam_pan = app.camera_model.pan_deg if app.camera_model else 0.0
        cam_tilt = app.camera_model.tilt_deg if app.camera_model else 0.0
        app.metrics_engine.update(
            frame_packet=packet,
            track_result=track_res,
            state_result=state_res,
            centroid_result=cent_res,
            detection_result=det_res,
            ptz_command=ptz_cmd,
            ground_truth=gt,
            camera_pan_deg=cam_pan,
            camera_tilt_deg=cam_tilt,
            processing_time_ms=lat_ms,
        )

    summary = app.metrics_engine.finalize()
    assert summary is not None
    assert summary.total_frames >= 15


def test_bm1_simulation_with_mock_custom_algorithm():
    """Verify BM1 simulation runs cleanly with an injected custom algorithm."""
    app = AppController()
    app.initialize()

    mock_algo = MockCustomAlgorithm()
    app._active_algorithm = mock_algo
    app._active_algorithm_name = "mock_tracker"

    for _ in range(10):
        packet = app.get_next_frame()
        if packet is None:
            break
        pub_res, lat_ms, track_res, state_res, cent_res, det_res = app.step_algorithm(packet)
        assert pub_res.algorithm_is_tracking is True

        ptz_cmd = app.ptz_controller.compute(
            track_result=track_res,
            tracking_state=state_res.state,
            frame_width=packet.width,
            frame_height=packet.height,
            dt=1.0 / 30.0,
        )
        assert ptz_cmd is not None

    assert mock_algo.frame_count == 10


def test_benchmark_manager_algorithm_parameter():
    """Verify BenchmarkManager.run_benchmark accepts and executes with selected algorithm."""
    app = AppController()
    app.initialize()

    # Run benchmark with baseline_tracker specified
    bm = app.benchmark_manager
    res = bm.run_benchmark(max_frames=10, algorithm_name="baseline_tracker")
    assert res is not None
    assert res.total_frames == 10
    assert app.active_algorithm_name == "baseline_tracker"


def test_app_controller_reset_lifecycle():
    """Verify reset() invokes reset() on active algorithm."""
    app = AppController()
    app.initialize()

    mock_algo = MockCustomAlgorithm()
    app._active_algorithm = mock_algo
    app._active_algorithm_name = "mock_tracker"

    assert mock_algo.reset_called is False
    app.reset()
    assert mock_algo.reset_called is True
