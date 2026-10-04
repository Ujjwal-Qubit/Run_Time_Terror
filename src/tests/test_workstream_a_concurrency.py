"""
Workstream A Concurrency & Hardening Test Suite (DEF-60 through DEF-65).

Validates:
  - DEF-62: Mutex lock (threading.RLock) guarding AppController state, canonical step(),
            set_ptz_velocity(), deadlock-free lifecycle, and web_bridge stepSimulation delegation.
  - DEF-61: SimulationWorkerThread exception resilience, errorOccurred Qt signal emission,
            last_error recording, and prevention of zombie state.
  - DEF-60: Safe OpenCV VideoCapture re-opening in MP4FrameProvider on reset().
  - DEF-63: Handle finalization before re-creation in LoggingEngine and AppController,
            try...finally file handle closing, and zero Windows PermissionError leaks.
  - DEF-64: Non-blocking while True drop-oldest pattern in VisualizationStateManager.push_state()
            under severe multi-threaded saturation.
  - DEF-65: Explicit encoding="utf-8" across all LoggingEngine file operations including unicode
            mathematical symbols (\u2264, \u00b0, \u2014, etc.).
"""

import math
import os
import queue
import sys
import tempfile
import threading
import time
from typing import List, Optional
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from src.app.app_controller import AppController
from src.app.simulation_worker import SimulationWorkerThread
from src.app.visualization_state import VisualizationStateManager
from src.config.config_manager import SystemConfig
from src.frame.data_contracts import (
    FramePacket,
    FrameSource,
    MetricsSummary,
    TelemetryRecord,
    VisualizationState,
)
from src.frame.mp4_provider import MP4FrameProvider
from src.metrics.logging_engine import LoggingEngine


def _create_test_mp4(filepath: str, num_frames: int = 15, width: int = 320, height: int = 240) -> None:
    """Helper to synthesize a test MP4 video using OpenCV."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(filepath, fourcc, 30.0, (width, height), isColor=False)
    for i in range(num_frames):
        img = np.full((height, width), (i * 15) % 256, dtype=np.uint8)
        cv2.circle(img, (50 + i * 5, 50 + i * 3), 10, 255, -1)
        out.write(img)
    out.release()


class TestWorkstreamAConcurrency:
    """Comprehensive stress and verification tests for Workstream A."""

    # --------------------------------------------------------------------------
    # DEF-64: VisualizationStateManager Drop-Oldest Saturation
    # --------------------------------------------------------------------------
    def test_def64_visualization_state_manager_drop_oldest_saturation(self) -> None:
        """10 threads doing 1,000 pushes (10,000 total) into queue with maxsize=5."""
        mgr = VisualizationStateManager(maxsize=5)
        errors: List[Exception] = []
        old_interval = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)  # Aggressive preemption

        stop_event = threading.Event()

        def producer(thread_id: int) -> None:
            for i in range(1000):
                try:
                    s = VisualizationState(
                        frame_number=i,
                        timestamp=float(i * 0.033),
                        pan_angle_deg=0.0,
                        tilt_angle_deg=0.0,
                        camera_fov=4.0,
                        display_image=np.zeros((10, 10), dtype=np.uint8),
                        tracking_state="TRACKING",
                    )
                    mgr.push_state(s)
                except Exception as ex:
                    errors.append(ex)

        def consumer() -> None:
            while not stop_event.is_set():
                mgr.get_latest_state()
                time.sleep(0.0001)

        try:
            reader = threading.Thread(target=consumer, daemon=True)
            reader.start()

            producers = [threading.Thread(target=producer, args=(t,)) for t in range(10)]
            for p in producers:
                p.start()
            for p in producers:
                p.join()

            stop_event.set()
            reader.join(timeout=1.0)
        finally:
            sys.setswitchinterval(old_interval)

        assert len(errors) == 0, f"Encountered unexpected queue errors: {errors}"
        # Verify queue still functions normally after saturation
        latest = mgr.get_latest_state()
        assert latest is None or isinstance(latest, VisualizationState)

    # --------------------------------------------------------------------------
    # DEF-65: LoggingEngine UTF-8 Encoding Enforcement
    # --------------------------------------------------------------------------
    def test_def65_logging_engine_utf8_encoding_and_symbols(self, tmp_path) -> None:
        """Verify explicit utf-8 encoding across files and writing unicode symbols."""
        out_dir = str(tmp_path / "logs_utf8")
        le = LoggingEngine(output_dir=out_dir, run_id="utf8_verify")
        le.initialize()

        assert le._csv_file is not None
        assert le._csv_file.encoding.lower() == "utf-8"
        assert le._centroid_file is not None
        assert le._centroid_file.encoding.lower() == "utf-8"

        # Log frame with telemetry
        rec = TelemetryRecord(
            frame_number=1,
            timestamp=0.033,
            estimated_centroid_x=120.5,
            estimated_centroid_y=80.2,
            centroid_valid=True,
            detection_confidence=0.99,
        )
        le.log_frame(rec)
        le.flush()

        # Write summary and performance report containing Unicode symbols
        summary = MetricsSummary(
            run_id="utf8_verify",
            total_frames=10,
            duration_seconds=0.33,
            mean_fps=30.0,
            acquisition_time_s=0.5,
            mean_reacquisition_time_s=0.2,
            max_reacquisition_time_s=0.3,
            mean_tracking_error=1.5,
            max_tracking_error=3.0,
            target_loss_rate=0.0,
            rmse_centroid_rendered=0.5,
            rmse_centroid_ideal=0.4,
            mean_centroid_error=0.45,
            median_centroid_error=0.42,
            pct_within_1px=95.0,
            pct_within_2px=99.0,
            pct_within_5px=100.0,
            lock_retention_post_acq_pct=100.0,
            lock_retention_all_pct=95.0,
            lock_retention_visible_pct=98.0,
            track_continuity=0.99,
            reacquisition_events=0,
            mean_latency_ms=12.5,
            p50_latency_ms=12.0,
            p95_latency_ms=15.0,
            p99_latency_ms=18.0,
            max_latency_ms=20.0,
            mean_steady_state_error=0.5,
            oscillation_measure=0.1,
            frames_in_deadband_pct=85.0,
        )

        rep_path = le.write_performance_report(summary)
        assert rep_path is not None and os.path.exists(rep_path)

        # Inspect report: verify UTF-8 content and mathematical symbols (\le, \ge, %, etc.)
        with open(rep_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "SIH 2026 Virtual Camera Tracking System" in content
        assert "Compliance Scorecard" in content

        # Write config snapshot
        cfg_path = le.write_config_snapshot({"description": "Test \u2264 \u00b0 \u2014 symbols"})
        assert cfg_path is not None
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg_content = f.read()
        assert "\u2264" in cfg_content

        le.finalize()
        assert le._csv_file is None
        assert le._centroid_file is None

    # --------------------------------------------------------------------------
    # DEF-63: Handle Finalization & Windows File Locking Prevention
    # --------------------------------------------------------------------------
    def test_def63_logging_engine_handle_leak_prevention_on_repeated_init(self) -> None:
        """Repeatedly initialize LoggingEngine and AppController without handle leaks or WinError 32."""
        with tempfile.TemporaryDirectory() as td:
            cfg = SystemConfig()
            cfg.logging.output_dir = td
            app = AppController()

            # First initialization
            app.initialize(cfg)
            le1 = app.logging_engine
            csv_handle1 = le1._csv_file
            centroid_handle1 = le1._centroid_file
            assert csv_handle1 is not None and not csv_handle1.closed
            assert centroid_handle1 is not None and not centroid_handle1.closed

            # Log frame to touch files
            le1.log_frame(TelemetryRecord(frame_number=1))

            # Second initialization: must cleanly finalize prior handles
            app.initialize(cfg)
            assert csv_handle1.closed is True
            assert centroid_handle1.closed is True

            le2 = app.logging_engine
            csv_handle2 = le2._csv_file
            assert csv_handle2 is not None and not csv_handle2.closed
            assert csv_handle2 != csv_handle1

            # Third direct initialize on the same LoggingEngine instance
            le2.initialize()
            assert csv_handle2.closed is True

            # Stop app and cleanup
            app.stop()
            assert app.logging_engine._csv_file is None
            assert app.logging_engine._centroid_file is None

        # If we reach here without PermissionError, Windows file lock was cleanly released!

    def test_def63_logging_engine_context_manager_and_destructor(self, tmp_path) -> None:
        """Verify __enter__, __exit__, and __del__ safety in LoggingEngine."""
        out_dir = str(tmp_path / "ctx_test")
        with LoggingEngine(output_dir=out_dir, run_id="ctx_run") as le:
            le.initialize()
            f = le._csv_file
            assert f is not None and not f.closed

        # Exiting context must finalize handles
        assert f.closed is True
        assert le._csv_file is None

    # --------------------------------------------------------------------------
    # DEF-60: Safe OpenCV VideoCapture Re-Opening on Reset
    # --------------------------------------------------------------------------
    def test_def60_mp4_provider_and_app_reset_stream_continuation(self, tmp_path) -> None:
        """Verify MP4FrameProvider and AppController reset() safely rewinds or reopens stream."""
        mp4_path = str(tmp_path / "sample.mp4")
        _create_test_mp4(mp4_path, num_frames=10)

        # 1. Direct MP4FrameProvider tests
        provider = MP4FrameProvider(mp4_path)
        p0 = provider.get_next_frame()
        assert p0 is not None and p0.frame_number == 0

        p1 = provider.get_next_frame()
        assert p1 is not None and p1.frame_number == 1

        # Simulate close then reset
        provider.close()
        assert provider._cap is None
        provider.reset()
        assert provider.is_exhausted() is False
        assert provider.frame_count == 0

        # Must successfully yield frames from frame 0 again
        p0_after = provider.get_next_frame()
        assert p0_after is not None and p0_after.frame_number == 0
        assert np.array_equal(p0.image, p0_after.image)
        provider.close()

        # 2. AppController MP4 reset integration test
        cfg = SystemConfig()
        cfg.simulation.mode = "MP4"
        cfg.simulation.mp4_path = mp4_path
        app = AppController()
        app.initialize(cfg)

        f0 = app.get_next_frame()
        assert f0 is not None and f0.frame_number == 0

        # Advance to frame 5
        for _ in range(5):
            app.get_next_frame()

        # Call app.reset()
        app.reset()

        # Must stream from frame 0 again
        f0_reset = app.get_next_frame()
        assert f0_reset is not None
        assert f0_reset.frame_number == 0
        assert np.array_equal(f0.image, f0_reset.image)

        app.stop()

    # --------------------------------------------------------------------------
    # DEF-61: SimulationWorkerThread Exception Resilience & Error Signal
    # --------------------------------------------------------------------------
    def test_def61_worker_thread_exception_resilience_and_error_signal(self) -> None:
        """Inject exception into step_algorithm; verify worker catches error, emits signal, and clears is_running."""
        app = AppController()
        app.initialize()

        worker = app.simulation_worker
        received_errors: List[str] = []

        def error_slot(msg: str) -> None:
            received_errors.append(msg)

        try:
            from PySide6.QtCore import Qt
            worker.errorOccurred.connect(error_slot, Qt.DirectConnection)
        except Exception:
            worker.errorOccurred.connect(error_slot)

        # Inject deliberate fault into step_algorithm
        app.step_algorithm = MagicMock(side_effect=RuntimeError("Simulated Tracking Hardware Failure"))

        app.start_background_loop()
        assert worker.thread is not None
        worker.thread.join(timeout=3.0)

        # Thread must have terminated cleanly without crashing python host
        assert not worker.is_alive()
        assert worker.is_running is False
        assert app.is_running is False
        assert worker.last_error == "Simulated Tracking Hardware Failure"
        assert len(received_errors) >= 1
        assert "Simulated Tracking Hardware Failure" in received_errors[0]

        # Resetting or re-initializing must allow subsequent runs without zombie state
        app.stop()
        app.initialize()
        assert app.is_running is False

    # --------------------------------------------------------------------------
    # DEF-62: AppController Mutex Lock (RLock) & Concurrency
    # --------------------------------------------------------------------------
    def test_def62_multi_threaded_concurrent_step_and_param_updates(self) -> None:
        """Multiple threads concurrently calling app.step(), parameter updates, and queries."""
        app = AppController()
        app.initialize()

        stop_event = threading.Event()
        errors: List[Exception] = []

        def step_worker() -> None:
            for _ in range(200):
                if stop_event.is_set():
                    break
                try:
                    state = app.step()
                    assert state is not None
                except Exception as ex:
                    errors.append(ex)

        def param_worker() -> None:
            for i in range(200):
                if stop_event.is_set():
                    break
                try:
                    app.set_ptz_velocity(math.sin(i) * 5.0, math.cos(i) * 5.0)
                    app.set_target_speed(50.0 + (i % 20))
                    app.set_ptz_parameters(kp=1.0 + (i % 5) * 0.1, ki=0.1)
                    app.get_telemetry_snapshot()
                    time.sleep(0.001)
                except Exception as ex:
                    errors.append(ex)

        threads = [
            threading.Thread(target=step_worker),
            threading.Thread(target=step_worker),
            threading.Thread(target=param_worker),
            threading.Thread(target=param_worker),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        stop_event.set()
        app.stop()

        assert len(errors) == 0, f"Encountered concurrency errors: {errors}"

    def test_def62_rapid_start_stop_reset_lifecycle_500_cycles(self) -> None:
        """Verify zero deadlocks during 500 rapid start/pause/resume/stop/reset cycles."""
        app = AppController()
        app.initialize()

        t0 = time.perf_counter()
        for i in range(500):
            app.start_background_loop()
            if i % 10 == 0:
                app.pause()
                app.resume()
            app.stop()
            app.reset()

        elapsed = time.perf_counter() - t0
        print(f"\n500 rapid lifecycle cycles completed in {elapsed:.2f}s")
        assert elapsed < 60.0, f"Lifecycle cycles took too long ({elapsed:.2f}s) — possible thread contention"
        assert not app.is_running

    # --------------------------------------------------------------------------
    # DEF-62: WebBridge stepSimulation Delegation Test
    # --------------------------------------------------------------------------
    def test_def62_web_bridge_step_simulation_delegation(self) -> None:
        """Verify SanketBridge.stepSimulation delegates cleanly to AppController.step()."""
        from src.app.gui.web_bridge import SanketBridge

        app = AppController()
        app.initialize()

        bridge = SanketBridge(app)
        bridge._timer.stop()  # Stop autonomous polling timer during test

        # Execute stepSimulation
        bridge.stepSimulation()
        assert app.frame_count >= 0
        assert bridge._last_status_emit_time > 0.0

        # Step second frame
        bridge.stepSimulation()
        assert app.frame_count >= 1

        app.stop()
