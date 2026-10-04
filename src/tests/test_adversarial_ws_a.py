"""
Adversarial Fault Injection & Resource Lifecycle Verification Suite for Workstream A.
Challenger 2 Independent Empirical Stress & Verification Harness.

Defects Audited:
  - DEF-61: SimulationWorkerThread exception resilience, errorOccurred emission, last_error recording,
            absence of zombie thread state, and immediate UI restartability.
  - DEF-60: MP4FrameProvider VideoCapture handle resurrection after exhaustion and closure across repeated resets.
  - DEF-63: Windows file descriptor leak prevention across 50 repeated AppController initializations and clean deletion.
  - DEF-65: UTF-8 encoding enforcement and mathematical symbol byte-level serialization in LoggingEngine.
"""

import gc
import json
import math
import os
import shutil
import tempfile
import threading
import time
from typing import List, Optional
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from src.app.app_controller import AppController
from src.app.simulation_worker import SimulationWorkerThread
from src.app.visualization_state import VisualizationStateManager
from src.config.config_manager import SystemConfig
from src.frame.data_contracts import (
    BatchRunItem,
    FramePacket,
    FrameSource,
    GrandEvaluationSummary,
    MetricsSummary,
    TelemetryRecord,
    TrackingState,
    TrackingStateResult,
    VisualizationState,
)
from src.frame.mp4_provider import MP4FrameProvider
from src.metrics.logging_engine import LoggingEngine


def _generate_synthetic_mp4(filepath: str, num_frames: int = 20, width: int = 320, height: int = 240) -> None:
    """Creates a deterministic synthetic test video file using OpenCV."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(filepath, fourcc, 30.0, (width, height), isColor=False)
    for i in range(num_frames):
        # Create patterned monochrome frames
        frame = np.full((height, width), (i * 12) % 256, dtype=np.uint8)
        cv2.circle(frame, (40 + i * 8, 40 + i * 6), 12, 255, -1)
        writer.write(frame)
    writer.release()


class TestAdversarialWorkstreamA:
    """Empirical challenger test suite executing adversarial verification for Workstream A."""

    # =========================================================================
    # Test 1: Fault Injection in SimulationWorkerThread (DEF-61)
    # =========================================================================
    def test_fault_injection_step_algorithm_exception_and_ui_restart(self) -> None:
        """
        Fault Injection Test 1A:
        Inject runtime exception into step_algorithm(). Verify worker thread catches it,
        emits errorOccurred Qt signal, sets last_error, terminates cleanly without host crash,
        and app.is_running returns False (no zombie state). Verify the UI can immediately restart.
        """
        app = AppController()
        app.initialize()

        worker = app.simulation_worker
        emitted_signals: List[str] = []

        def on_error(msg: str) -> None:
            emitted_signals.append(msg)

        try:
            from PySide6.QtCore import Qt
            worker.errorOccurred.connect(on_error, Qt.DirectConnection)
        except Exception:
            worker.errorOccurred.connect(on_error)

        # 1. Inject simulated hardware tracking exception
        fault_message = "ADVERSARIAL_INJECTION: Optical Flow Core Bus Failure"
        original_step_algo = app.step_algorithm
        app.step_algorithm = MagicMock(side_effect=RuntimeError(fault_message))

        app.start_background_loop()
        assert worker.thread is not None
        worker.thread.join(timeout=3.0)

        # 2. Assert clean termination and absence of zombie state
        assert not worker.is_alive(), "Worker thread must not remain alive after unhandled exception."
        assert worker.is_running is False, "Worker is_running flag must be False."
        assert app.is_running is False, "AppController.is_running must be False (no zombie state)."
        assert worker.last_error == fault_message, f"Expected last_error to be '{fault_message}', got '{worker.last_error}'"
        assert len(emitted_signals) >= 1, "errorOccurred signal was not emitted."
        assert fault_message in emitted_signals[0], f"Emitted signal does not contain error: {emitted_signals}"

        # 3. Verify UI can immediately restart the simulation
        app.step_algorithm = original_step_algo  # Restore healthy algorithm
        app.start_background_loop()

        # Let it run healthy for a few iterations
        time.sleep(0.15)
        assert app.is_running is True, "App must successfully restart after fault."
        assert worker.is_alive() is True, "Worker thread must be alive and executing."
        assert worker.last_error is None, "Worker last_error must be reset on fresh start."

        # Clean stop
        app.stop()
        assert app.is_running is False

    def test_fault_injection_frame_acquisition_exception_and_multi_cycle_restart(self) -> None:
        """
        Fault Injection Test 1B:
        Inject runtime exceptions during frame acquisition. Verify repeated fault -> catch -> restart
        cycles (5 consecutive iterations) maintain clean state and thread lifecycle without leaking threads.
        """
        app = AppController()
        app.initialize()

        worker = app.simulation_worker
        captured_errors: List[str] = []

        def on_error(msg: str) -> None:
            captured_errors.append(msg)

        try:
            from PySide6.QtCore import Qt
            worker.errorOccurred.connect(on_error, Qt.DirectConnection)
        except Exception:
            worker.errorOccurred.connect(on_error)

        original_get_frame = app.get_next_frame

        for cycle in range(5):
            cycle_err = f"FAULT_CYCLE_{cycle}: Sensor DMA Timeout"
            app.get_next_frame = MagicMock(side_effect=IOError(cycle_err))

            app.start_background_loop()
            assert worker.thread is not None
            worker.thread.join(timeout=2.0)

            assert not worker.is_alive(), f"Cycle {cycle}: Worker thread stayed alive."
            assert app.is_running is False, f"Cycle {cycle}: Zombie state detected in app.is_running."
            assert worker.last_error == cycle_err, f"Cycle {cycle}: Incorrect worker.last_error."

            # Verify immediate restartability with healthy function
            app.get_next_frame = original_get_frame
            app.start_background_loop()
            time.sleep(0.05)
            assert app.is_running is True, f"Cycle {cycle}: Failed to restart cleanly."
            app.stop()
            assert app.is_running is False

        assert len(captured_errors) == 5, f"Expected 5 error signals, got {len(captured_errors)}"

    # =========================================================================
    # Test 2: VideoCapture Handle Resurrection (DEF-60)
    # =========================================================================
    def test_videocapture_handle_resurrection_after_exhaustion_and_closure(self, tmp_path) -> None:
        """
        Resource Test 2A:
        Simulate exhausted and explicitly closed VideoCapture handles. Call reset(),
        and verify that get_next_frame() continues reading valid frames indefinitely
        across 25 repeated cycles.
        """
        mp4_path = str(tmp_path / "resurrection_stream.mp4")
        num_frames = 15
        _generate_synthetic_mp4(mp4_path, num_frames=num_frames, width=320, height=240)

        provider = MP4FrameProvider(mp4_path)
        first_frame_packet = provider.get_next_frame()
        assert first_frame_packet is not None
        expected_first_frame = first_frame_packet.image.copy()

        # Run 25 consecutive cycles of exhaustion -> closure -> reset -> read
        for cycle in range(25):
            # Exhaust remaining frames
            while not provider.is_exhausted():
                p = provider.get_next_frame()
                if p is None:
                    break
            assert provider.is_exhausted() is True

            # Adversarially close and destroy underlying capture handle
            provider.close()
            assert provider._cap is None

            # Attempt frame read on closed provider — must safely return None
            assert provider.get_next_frame() is None

            # Resurrect provider via reset()
            provider.reset()
            assert provider.is_exhausted() is False
            assert provider.frame_count == 0
            assert provider._cap is not None
            assert provider._cap.isOpened() is True

            # Read resurrected frame 0
            resurrected_frame_0 = provider.get_next_frame()
            assert resurrected_frame_0 is not None, f"Cycle {cycle}: Resurrected frame 0 is None"
            assert resurrected_frame_0.frame_number == 0
            assert np.array_equal(resurrected_frame_0.image, expected_first_frame), (
                f"Cycle {cycle}: Resurrected frame 0 image does not match original frame 0."
            )

            # Advance a few frames into stream
            for expected_idx in range(1, 5):
                f = provider.get_next_frame()
                assert f is not None
                assert f.frame_number == expected_idx

        provider.close()

    def test_videocapture_handle_resurrection_under_app_controller(self, tmp_path) -> None:
        """
        Resource Test 2B:
        Verify AppController in MP4 mode correctly resurrects exhausted video stream
        across repeated app.reset() cycles, allowing continuous step() calls indefinitely.
        """
        mp4_path = str(tmp_path / "app_resurrection.mp4")
        num_frames = 10
        _generate_synthetic_mp4(mp4_path, num_frames=num_frames)

        cfg = SystemConfig()
        cfg.simulation.mode = "MP4"
        cfg.simulation.mp4_path = mp4_path

        app = AppController()
        app.initialize(cfg)

        for cycle in range(10):
            # Step until stream exhaustion
            frames_read = 0
            while True:
                state = app.step()
                if state is None:
                    break
                frames_read += 1
            assert frames_read >= 1, f"Cycle {cycle}: No frames stepped."

            # Reset AppController
            app.reset()
            assert app.frame_count == 0
            assert app.is_running is False

            # Next step must yield frame 0 again
            first_state = app.step()
            assert first_state is not None, f"Cycle {cycle}: Failed to step after reset."
            assert first_state.frame_number == 0

        app.stop()

    def test_videocapture_fallback_when_seek_fails(self, tmp_path) -> None:
        """
        Resource Test 2C:
        Simulate OpenCV CAP_PROP_POS_FRAMES seek failure on an opened handle.
        Verify that reset() detects the failed seek and falls back to releasing
        and re-opening the VideoCapture cleanly.
        """
        mp4_path = str(tmp_path / "seek_fail.mp4")
        _generate_synthetic_mp4(mp4_path, num_frames=8)

        provider = MP4FrameProvider(mp4_path)
        provider.get_next_frame()

        # Create a mock VideoCapture whose set() returns False to simulate seek failure
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.set.return_value = False
        provider._cap = mock_cap

        # Call reset() — must detect rewound=False, release and reopen
        provider.reset()

        assert provider._cap is not None
        assert provider._cap != mock_cap
        assert provider._cap.isOpened() is True
        # Verify provider can read frame 0 after fallback reopen
        f0 = provider.get_next_frame()
        assert f0 is not None
        assert f0.frame_number == 0

        provider.close()

    # =========================================================================
    # Test 3: Windows File Descriptor Leak Check (DEF-63)
    # =========================================================================
    def test_windows_file_descriptor_leak_check_50_initializations(self) -> None:
        """
        Resource Test 3A:
        Call AppController.initialize() 50 times in a loop with logging active.
        Then attempt to delete the output directory.
        Verify zero PermissionError: [WinError 32] and all OS handles are properly closed.
        """
        temp_dir = tempfile.mkdtemp(prefix="sanket_handle_leak_test_")
        try:
            cfg = SystemConfig()
            cfg.logging.output_dir = temp_dir
            cfg.logging.csv_enabled = True
            cfg.logging.json_summary_enabled = True

            app = AppController()

            # Execute 50 consecutive initializations
            for i in range(50):
                app.initialize(cfg)

                # Log multiple records in each initialization to touch the file handles
                for frame_idx in range(5):
                    app.logging_engine.log_frame(
                        TelemetryRecord(
                            frame_number=frame_idx,
                            timestamp=frame_idx * 0.033,
                            estimated_centroid_x=100.0 + i,
                            estimated_centroid_y=200.0 + i,
                            centroid_valid=True,
                            detection_confidence=0.95,
                        )
                    )
                app.logging_engine.flush()

            # Cleanly stop the application
            app.stop()

            # Assert all LoggingEngine handles are None
            assert app.logging_engine._csv_file is None
            assert app.logging_engine._centroid_file is None

            # Attempt deletion of the entire output directory
            # If any handle leaked on Windows, this raises PermissionError: [WinError 32]
            shutil.rmtree(temp_dir)
            assert not os.path.exists(temp_dir), "Output directory must be completely deleted."

        except PermissionError as pe:
            pytest.fail(f"WINDOWS FILE DESCRIPTOR LEAK DETECTED: {pe}")
        finally:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

    def test_logging_engine_repeated_init_standalone_without_manual_finalize(self) -> None:
        """
        Resource Test 3B:
        Repeatedly call initialize() 50 times on a standalone LoggingEngine instance
        without manual finalize() calls in between. Verify old handles are released
        internally, preventing Windows file locking on directory deletion.
        """
        temp_dir = tempfile.mkdtemp(prefix="sanket_le_leak_test_")
        try:
            le = LoggingEngine(output_dir=temp_dir, run_id="standalone_leak")

            for i in range(50):
                le.initialize()
                le.log_frame(TelemetryRecord(frame_number=i))
                le.flush()

            le.finalize()
            assert le._csv_file is None
            assert le._centroid_file is None

            # Delete directory cleanly
            shutil.rmtree(temp_dir)
            assert not os.path.exists(temp_dir)

        except PermissionError as pe:
            pytest.fail(f"STANDALONE LOGGING ENGINE FILE DESCRIPTOR LEAK: {pe}")
        finally:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

    # =========================================================================
    # Test 4: UTF-8 Encoding & Mathematical Symbol Serialization (DEF-65)
    # =========================================================================
    def test_logging_engine_utf8_byte_serialization_and_mathematical_symbols(self) -> None:
        """
        Encoding Test 4:
        Write non-ASCII and mathematical symbols (≤ \u2264, ° \u00b0, — \u2014, ≥ \u2265, π \u03c0, σ \u03c3)
        into LoggingEngine. Verify clean UTF-8 byte serialization without UnicodeEncodeError,
        and confirm raw byte serialization contains valid multi-byte UTF-8 sequences.
        """
        temp_dir = tempfile.mkdtemp(prefix="sanket_utf8_test_")
        try:
            le = LoggingEngine(output_dir=temp_dir, run_id="utf8_adversarial")
            le.initialize()

            # Non-ASCII and mathematical test strings
            math_symbols = "\u2264 \u00b0 \u2014 \u2265 \u03c0 \u03c3 \u00b1 \u221e"
            unicode_text = "संकेत Tracking — θ = 45.0° (≤ 2.0s limit)"

            # 1. Config snapshot writing
            cfg_data = {
                "system": "SANKET",
                "symbols": math_symbols,
                "label": unicode_text,
                "thresholds": {"acq_time": "≤ 2.0 s", "angle": "± 5°"},
            }
            cfg_path = le.write_config_snapshot(cfg_data)
            assert cfg_path is not None and os.path.exists(cfg_path)

            # Inspect config snapshot raw bytes
            with open(cfg_path, "rb") as f:
                cfg_raw_bytes = f.read()

            # Verify UTF-8 decode
            cfg_decoded = cfg_raw_bytes.decode("utf-8")
            assert math_symbols in cfg_decoded
            assert unicode_text in cfg_decoded

            # Verify raw byte sequences for ≤ (\u2264 -> b'\xe2\x89\xa4')
            assert b"\xe2\x89\xa4" in cfg_raw_bytes, "Expected UTF-8 bytes for \u2264 (≤) not found."
            # Verify raw byte sequences for ° (\u00b0 -> b'\xc2\xb0')
            assert b"\xc2\xb0" in cfg_raw_bytes, "Expected UTF-8 bytes for \u00b0 (°) not found."
            # Verify raw byte sequences for — (\u2014 -> b'\xe2\x80\x94')
            assert b"\xe2\x80\x94" in cfg_raw_bytes, "Expected UTF-8 bytes for \u2014 (—) not found."

            # Verify ensure_ascii=False was respected: the literal escape '\u2264' should NOT be present
            assert b"\\u2264" not in cfg_raw_bytes, "JSON escaped Unicode characters instead of UTF-8 byte serialization."

            # 2. Performance Report writing
            summary = MetricsSummary(
                run_id="utf8_adversarial",
                total_frames=100,
                duration_seconds=3.33,
                mean_fps=30.0,
                acquisition_time_s=1.2,
                mean_reacquisition_time_s=0.5,
                max_reacquisition_time_s=0.8,
                mean_tracking_error=2.5,
                max_tracking_error=5.0,
                target_loss_rate=1.0,
                rmse_centroid_rendered=0.8,
                rmse_centroid_ideal=0.7,
                mean_centroid_error=0.75,
                median_centroid_error=0.70,
                pct_within_1px=90.0,
                pct_within_2px=95.0,
                pct_within_5px=99.0,
                lock_retention_post_acq_pct=98.0,
                lock_retention_all_pct=95.0,
                lock_retention_visible_pct=97.0,
                track_continuity=0.98,
                reacquisition_events=1,
                mean_latency_ms=10.0,
                p50_latency_ms=9.5,
                p95_latency_ms=14.0,
                p99_latency_ms=16.0,
                max_latency_ms=18.0,
                mean_steady_state_error=0.4,
                oscillation_measure=0.05,
                frames_in_deadband_pct=88.0,
            )
            rep_path = le.write_performance_report(summary)
            assert rep_path is not None and os.path.exists(rep_path)

            with open(rep_path, "rb") as f:
                rep_raw_bytes = f.read()

            rep_decoded = rep_raw_bytes.decode("utf-8")
            assert "Compliance Scorecard" in rep_decoded
            assert "—" in rep_decoded
            assert b"\xe2\x80\x94" in rep_raw_bytes  # em-dash

            # 3. Grand Summary (JSON & Markdown) with Unicode and mathematical symbols
            grand_summary = GrandEvaluationSummary(
                batch_id="batch_utf8_test",
                batch_type="STRESS_BENCHMARK",
                total_runs=1,
                successful_runs=1,
                failed_runs=0,
                total_frames_processed=100,
                total_duration_s=3.33,
                mean_fps=30.0,
                passed_fps_spec=True,
                passed_acquisition_spec=True,
                passed_tracking_error_spec=True,
                passed_loss_rate_spec=True,
                overall_compliance=True,
                run_items=[
                    BatchRunItem(
                        item_id="run_1_≤_test",
                        source_path="datasets/test_—_path.mp4",
                        success=True,
                        summary=summary,
                    )
                ],
            )

            json_path, md_path = LoggingEngine.write_grand_summary(grand_summary, output_dir=temp_dir)
            assert os.path.exists(json_path)
            assert os.path.exists(md_path)

            # Inspect grand summary JSON raw bytes
            with open(json_path, "rb") as f:
                grand_json_bytes = f.read()
            assert b"\xe2\x89\xa4" in grand_json_bytes  # ≤ in item_id
            assert b"\xe2\x80\x94" in grand_json_bytes  # — in source_path
            assert b"\\u2264" not in grand_json_bytes   # ensure_ascii=False verified

            # Inspect grand summary Markdown raw bytes
            with open(md_path, "rb") as f:
                grand_md_bytes = f.read()
            grand_md_decoded = grand_md_bytes.decode("utf-8")
            assert "Grand Evaluation Scorecard" in grand_md_decoded
            assert "—" in grand_md_decoded

            le.finalize()

        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    # =========================================================================
    # Additional Empirical Hardening: Concurrency Contention During Faults
    # =========================================================================
    def test_adversarial_fault_injection_under_concurrent_thread_contention(self) -> None:
        """
        Verify that when a runtime fault is injected into SimulationWorkerThread,
        concurrent external threads actively calling AppController mutex-guarded methods
        (set_ptz_velocity, get_telemetry_snapshot) do NOT deadlock, lockups do not occur,
        and both worker thread and controller exit cleanly to is_running=False.
        """
        app = AppController()
        app.initialize()

        worker = app.simulation_worker
        stop_threads = threading.Event()
        contention_errors: List[Exception] = []

        def hammer_app_controller() -> None:
            while not stop_threads.is_set():
                try:
                    app.set_ptz_velocity(2.5, -1.5)
                    app.set_target_speed(45.0)
                    app.get_telemetry_snapshot()
                    time.sleep(0.001)
                except Exception as ex:
                    contention_errors.append(ex)

        # Start concurrent hammering threads
        threads = [threading.Thread(target=hammer_app_controller) for _ in range(3)]
        for t in threads:
            t.start()

        try:
            # Inject exception into step
            app.step = MagicMock(side_effect=RuntimeError("CONCURRENT_CONTENTION_FAULT"))

            app.start_background_loop()
            assert worker.thread is not None
            worker.thread.join(timeout=3.0)

            # Assert clean fault termination under concurrency
            assert not worker.is_alive()
            assert app.is_running is False
            assert worker.last_error == "CONCURRENT_CONTENTION_FAULT"
        finally:
            stop_threads.set()
            for t in threads:
                t.join(timeout=2.0)
            app.stop()

        assert len(contention_errors) == 0, f"Contention threads encountered errors: {contention_errors}"

    def test_windows_file_descriptor_leak_with_all_report_types_50_cycles(self) -> None:
        """
        Comprehensive Handle Leak Test:
        In each of 50 consecutive initializations, execute complete file generation:
        - Telemetry CSV rows
        - Centroid CSV rows
        - Config snapshot JSON
        - Metrics summary JSON
        - Markdown performance scorecard
        Verify that after 50 cycles, zero file locks remain and the directory
        can be deleted cleanly on Windows without PermissionError [WinError 32].
        """
        temp_dir = tempfile.mkdtemp(prefix="sanket_full_reports_leak_")
        try:
            cfg = SystemConfig()
            cfg.logging.output_dir = temp_dir
            cfg.logging.csv_enabled = True
            cfg.logging.json_summary_enabled = True

            app = AppController()

            summary = MetricsSummary(
                run_id="leak_test",
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

            for i in range(50):
                app.initialize(cfg)
                le = app.logging_engine
                # Write all report varieties
                le.log_frame(TelemetryRecord(frame_number=i, detection_confidence=0.9))
                le.flush()
                le.write_summary(summary)
                le.write_performance_report(summary)

            app.stop()

            # Critical assertion: entire directory tree can be deleted on Windows
            shutil.rmtree(temp_dir)
            assert not os.path.exists(temp_dir), "Temp directory must be completely removed without WinError 32."

        except PermissionError as pe:
            pytest.fail(f"WINDOWS FILE LOCK LEAK ON FULL REPORTS: {pe}")
        finally:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

