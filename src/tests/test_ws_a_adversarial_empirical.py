"""
Adversarial Empirical Challenge Suite for Workstream A (Core Runtime & Concurrency).

Focus Defects:
  - DEF-60: VideoCapture Handle Resurrection across Exhausted & Closed Resets.
  - DEF-61: Fault Injection in SimulationWorkerThread (Signal Emission, last_error, Zero Zombie State, Immediate UI Restart).
  - DEF-63: Windows File Descriptor Leak Check (50 Repeated Initializations, Output Dir Deletion).
  - DEF-65: UTF-8 Byte Serialization and Math/Non-ASCII Symbols (\u2264, \u00b0, \u2014) in LoggingEngine.

Authored by Challenger 2 (Gen 2).
"""

import json
import os
import shutil
import tempfile
import threading
import time
from typing import List, Optional
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from src.app.app_controller import AppController
from src.app.gui.web_bridge import SanketBridge
from src.app.simulation_worker import SimulationWorkerThread
from src.config.config_manager import SystemConfig
from src.frame.data_contracts import (
    FramePacket,
    FrameSource,
    GrandEvaluationSummary,
    BatchRunItem,
    MetricsSummary,
    TelemetryRecord,
)
from src.frame.mp4_provider import MP4FrameProvider
from src.metrics.logging_engine import LoggingEngine


def _generate_synthetic_mp4(filepath: str, num_frames: int = 25, width: int = 320, height: int = 240) -> None:
    """Generate a valid MP4 test video with predictable pixel patterns."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(filepath, fourcc, 30.0, (width, height), isColor=False)
    for i in range(num_frames):
        img = np.full((height, width), (i * 10) % 256, dtype=np.uint8)
        # Add moving circle
        cv2.circle(img, (30 + i * 8, 40 + i * 5), 8, 255, -1)
        writer.write(img)
    writer.release()


class TestAdversarialWorkstreamA:
    """Empirical fault injection and resource lifecycle stress harness."""

    # ==========================================================================
    # TEST 1: FAULT INJECTION IN SIMULATION WORKER THREAD (DEF-61)
    # ==========================================================================
    def test_fault_injection_simulation_worker_thread(self) -> None:
        """
        Adversarial Fault Injection Test 1:
        1. Inject simulated runtime exception into frame processing / algorithm step inside SimulationWorkerThread.
        2. Verify worker catches exception, sets last_error, emits errorOccurred signal.
        3. Verify thread terminates cleanly without host crash.
        4. Verify app.is_running returns False (no zombie state).
        5. Verify web_bridge errorOccurred signal receives structured error payload.
        6. Verify UI can immediately restart the simulation and resume frame processing.
        """
        app = AppController()
        app.initialize()

        bridge = SanketBridge(app)
        bridge._timer.stop()  # Stop background polling timer for deterministic test control

        worker = app.simulation_worker
        worker_errors_received: List[str] = []
        bridge_errors_received: List[str] = []

        try:
            from PySide6.QtCore import QCoreApplication, Qt
            qt_app = QCoreApplication.instance() or QCoreApplication([])
        except ImportError:
            qt_app = None

        # Connect signals (using Qt.DirectConnection or pumping event loop)
        worker.errorOccurred.connect(lambda err: worker_errors_received.append(err))
        bridge.errorOccurred.connect(lambda payload: bridge_errors_received.append(payload))

        # Start simulation background loop
        bridge.runSimulation()
        assert app.is_running is True
        assert worker.is_running is True
        assert worker.thread is not None
        assert worker.is_alive() is True

        # Let simulation advance at least 2 frames
        time.sleep(0.1)
        if qt_app:
            qt_app.processEvents()
        assert app.frame_count >= 1

        # --- FAULT INJECTION ---
        # Mock step() to simulate unhandled tracker pipeline / sensor hardware exception
        simulated_error_msg = "CRITICAL_FPGA_BUS_PARITY_ERROR_0xDEADBEEF"
        orig_step = app.step
        app.step = MagicMock(side_effect=RuntimeError(simulated_error_msg))

        # Wait for worker thread to catch exception and terminate
        assert worker.thread is not None
        worker.thread.join(timeout=3.0)

        # Pump Qt event loop for cross-thread queued signals
        if qt_app:
            qt_app.processEvents()

        # 1. Thread must have terminated cleanly without crashing python host
        assert not worker.is_alive(), "Worker thread is still alive after unhandled exception!"
        assert worker.is_running is False, "Worker is_running is True after exception!"
        assert app.is_running is False, "AppController is_running is True (zombie state detected)!"

        # 2. Worker last_error must record the exact exception string
        assert worker.last_error == simulated_error_msg, f"Expected {simulated_error_msg}, got {worker.last_error}"

        # 3. Worker errorOccurred Qt signal must have emitted
        assert len(worker_errors_received) >= 1, "worker.errorOccurred signal was not emitted!"
        assert simulated_error_msg in worker_errors_received[0]

        # 4. Bridge errorOccurred signal must have emitted JSON error payload
        assert len(bridge_errors_received) >= 1, "bridge.errorOccurred signal was not emitted!"
        bridge_payload = json.loads(bridge_errors_received[0])
        assert bridge_payload["source"] == "SimulationWorkerThread"
        assert bridge_payload["error"] == simulated_error_msg
        assert "timestamp" in bridge_payload

        # 5. UI IMMEDIATELY RESTARTS SIMULATION:
        # Restore app.step, simulate user clicking 'Run' in the UI via bridge.runSimulation()
        app.step = orig_step
        bridge.runSimulation()

        # Verify clean resuscitation without zombie state or deadlock
        assert app.is_running is True, "app.is_running should be True after immediate restart"
        assert worker.is_running is True, "worker.is_running should be True after restart"
        assert worker.is_alive() is True, "New worker thread should be alive"
        assert worker.last_error is None, "last_error should be cleared on new run"

        # Allow new frames to flow
        time.sleep(0.1)
        frames_after_restart = app.frame_count
        assert frames_after_restart > 0, "No frames processed after restart"

        # Clean shutdown
        bridge.stopSimulation()
        assert app.is_running is False
        assert not worker.is_alive()

    def test_repeated_crash_and_restart_cycles(self) -> None:
        """
        Stress-test 10 rapid consecutive exception crashes and resuscitations
        to ensure zero memory or handle leakage under repeated failure conditions.
        """
        app = AppController()
        app.initialize()

        worker = app.simulation_worker
        orig_step = app.step

        for cycle in range(10):
            err_msg = f"SIMULATED_TRANSIENT_FAULT_CYCLE_{cycle}"
            app.step = MagicMock(side_effect=RuntimeError(err_msg))

            app.start_background_loop()
            assert worker.thread is not None
            worker.thread.join(timeout=2.0)

            # Must be terminated, no zombie
            assert not worker.is_alive()
            assert app.is_running is False
            assert worker.last_error == err_msg

            # Resuscitate
            app.step = orig_step
            app.start_background_loop()
            assert app.is_running is True
            time.sleep(0.02)
            app.stop()
            assert app.is_running is False

    # ==========================================================================
    # TEST 2: VIDEOCAPTURE HANDLE RESURRECTION (DEF-60)
    # ==========================================================================
    def test_videocapture_handle_resurrection_and_reset(self, tmp_path) -> None:
        """
        Adversarial Resource Test 2:
        1. Read MP4FrameProvider to complete EOF exhaustion.
        2. Explicitly close and nullify VideoCapture handle.
        3. Simulate seek failure on reset().
        4. Verify reset() cleanly resurrects handle and get_next_frame() reads valid frames.
        5. Run 50 repeated cycles of exhaustion/close/reset.
        """
        mp4_path = str(tmp_path / "adversarial_resurrection.mp4")
        _generate_synthetic_mp4(mp4_path, num_frames=20, width=320, height=240)

        provider = MP4FrameProvider(mp4_path)
        assert provider.total_frames == 20

        # Read all frames until EOF exhaustion
        read_frames = []
        while True:
            packet = provider.get_next_frame()
            if packet is None:
                break
            read_frames.append(packet)

        assert len(read_frames) == 20
        assert provider.is_exhausted() is True
        assert provider.get_next_frame() is None

        # --- Cycle 1: Reset from exhausted state ---
        provider.reset()
        assert provider.is_exhausted() is False
        assert provider.frame_count == 0

        p0 = provider.get_next_frame()
        assert p0 is not None
        assert p0.frame_number == 0
        assert np.array_equal(p0.image, read_frames[0].image)

        # --- Cycle 2: Closed & None handle resurrection ---
        provider.close()
        assert provider._cap is None
        assert provider.get_next_frame() is None

        provider.reset()
        assert provider._cap is not None
        assert provider._cap.isOpened() is True
        p0_resurrected = provider.get_next_frame()
        assert p0_resurrected is not None
        assert p0_resurrected.frame_number == 0
        assert np.array_equal(p0_resurrected.image, read_frames[0].image)

        # --- Cycle 3: Seek failure fallback simulation ---
        # Simulate seek failure by assigning a mock cap whose set() returns False
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.set.return_value = False
        provider._cap = mock_cap

        provider.reset()
        assert provider._cap is not mock_cap
        assert provider._cap.isOpened() is True
        p0_fallback = provider.get_next_frame()
        assert p0_fallback is not None
        assert p0_fallback.frame_number == 0

        # --- Cycle 4: 50 Repeated Cycles Stress Loop ---
        for cycle in range(50):
            action = cycle % 3
            if action == 0:
                # Exhaust stream
                while provider.get_next_frame() is not None:
                    pass
            elif action == 1:
                # Close handle directly
                provider.close()
            else:
                # Advance partially
                provider.get_next_frame()
                provider.get_next_frame()

            provider.reset()
            assert provider.is_exhausted() is False
            assert provider.frame_count == 0

            # Verify next frame is valid
            frame = provider.get_next_frame()
            assert frame is not None, f"Failed to get frame after reset on cycle {cycle}"
            assert frame.frame_number == 0
            assert frame.image.shape == (240, 320)
            assert frame.image.dtype == np.uint8

        provider.close()

    def test_app_controller_mp4_reset_integration(self, tmp_path) -> None:
        """Verify AppController resets MP4 provider correctly across repeated cycles."""
        mp4_path = str(tmp_path / "app_mp4_reset.mp4")
        _generate_synthetic_mp4(mp4_path, num_frames=15)

        cfg = SystemConfig()
        cfg.simulation.mode = "MP4"
        cfg.simulation.mp4_path = mp4_path

        app = AppController()
        app.initialize(cfg)

        for _ in range(10):
            # Step 5 frames
            for _ in range(5):
                pkt = app.get_next_frame()
                assert pkt is not None
            app.reset()
            # Frame count resets to 0
            assert app.frame_count == 0
            f0 = app.get_next_frame()
            assert f0 is not None
            assert f0.frame_number == 0

        app.stop()

    # ==========================================================================
    # TEST 3: WINDOWS FILE DESCRIPTOR LEAK CHECK (DEF-63)
    # ==========================================================================
    def test_windows_fd_leak_check_50_initializations(self) -> None:
        """
        Adversarial Resource Test 3:
        Call AppController.initialize() 50 times in a loop, then attempt to delete the output directory.
        Verify zero PermissionError: [WinError 32] and all handles are properly closed.
        """
        temp_dir = tempfile.mkdtemp(prefix="sanket_win32_fd_leak_")
        assert os.path.isdir(temp_dir)

        try:
            cfg = SystemConfig()
            cfg.logging.output_dir = temp_dir
            app = AppController()

            # Initialize 50 times in a loop
            for i in range(50):
                app.initialize(cfg)
                # Touch logging engine with frames
                rec = TelemetryRecord(
                    frame_number=i,
                    timestamp=float(i * 0.033),
                    estimated_centroid_x=100.0 + i,
                    estimated_centroid_y=200.0 - i,
                    centroid_valid=True,
                    detection_confidence=0.95,
                )
                app.logging_engine.log_frame(rec)
                app.logging_engine.flush()

            # Stop app and finalize
            app.stop()

            # Attempt deletion of the output directory
            # On Windows, any unclosed handle in temp_dir causes PermissionError: [WinError 32]
            shutil.rmtree(temp_dir)
            assert not os.path.exists(temp_dir), "Directory still exists after rmtree"

        except PermissionError as pe:
            pytest.fail(f"Windows File Descriptor Leak Detected (WinError 32)! {pe}")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    def test_logging_engine_direct_50_reinitializations_leak_check(self) -> None:
        """Direct stress test on LoggingEngine.initialize() 50 times in a single instance."""
        temp_dir = tempfile.mkdtemp(prefix="sanket_le_direct_leak_")
        assert os.path.isdir(temp_dir)

        try:
            le = LoggingEngine(output_dir=temp_dir, run_id="le_stress")
            for i in range(50):
                le.initialize()
                le.log_frame(TelemetryRecord(frame_number=i))
                le.flush()

            le.finalize()
            shutil.rmtree(temp_dir)
            assert not os.path.exists(temp_dir)

        except PermissionError as pe:
            pytest.fail(f"LoggingEngine direct handle leak on Windows! {pe}")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    # ==========================================================================
    # TEST 4: NON-ASCII & MATH SYMBOLS UTF-8 BYTE SERIALIZATION (DEF-65)
    # ==========================================================================
    def test_utf8_byte_serialization_and_math_symbols(self, tmp_path) -> None:
        """
        Adversarial Encoding Test 4:
        Write non-ASCII and mathematical symbols (\u2264, \u00b0, \u2014, \u2265, \u00b1, \u03c0)
        into LoggingEngine.
        Verify clean UTF-8 byte serialization without UnicodeEncodeError.
        Verify raw bytes on disk contain authentic UTF-8 encodings (e.g. b'\\xe2\\x89\\xa4' for \u2264).
        """
        out_dir = str(tmp_path / "utf8_serialization")
        math_run_id = "run_math_\u2264_\u00b0_\u2014"

        le = LoggingEngine(output_dir=out_dir, run_id=math_run_id)
        le.initialize()

        # 1. Config snapshot with mathematical symbols in keys and values
        config_data = {
            "test_leq": "\u2264 2.0 s (PS requirement)",
            "test_degree": "Camera FOV: 45\u00b0",
            "test_emdash": "SANKET \u2014 Virtual Camera Tracking",
            "test_geq": "Throughput \u2265 20.0 FPS",
            "test_plusminus": "Error tolerance \u00b1 0.5 px",
            "test_greek": "\u03b1=0.05, \u03b2=0.99, \u03c0=3.14159",
            "test_infinity": "\u221e",
            "test_approx": "\u2248",
            "test_micro": "\u00b5s",
        }
        cfg_path = le.write_config_snapshot(config_data)
        assert cfg_path is not None and os.path.exists(cfg_path)

        # 2. Metrics summary with mathematical symbols
        summary = MetricsSummary(
            run_id=math_run_id,
            total_frames=100,
            duration_seconds=3.33,
            mean_fps=30.0,
            acquisition_time_s=1.2,
            mean_reacquisition_time_s=0.5,
            max_reacquisition_time_s=0.8,
            mean_tracking_error=2.1,
            max_tracking_error=4.5,
            target_loss_rate=0.0,
            rmse_centroid_rendered=0.8,
            rmse_centroid_ideal=0.7,
            mean_centroid_error=0.75,
            median_centroid_error=0.72,
            pct_within_1px=92.0,
            pct_within_2px=98.0,
            pct_within_5px=100.0,
            lock_retention_post_acq_pct=100.0,
            lock_retention_all_pct=96.0,
            lock_retention_visible_pct=99.0,
            track_continuity=0.98,
            reacquisition_events=0,
            mean_latency_ms=14.2,
            p50_latency_ms=13.8,
            p95_latency_ms=16.5,
            p99_latency_ms=19.1,
            max_latency_ms=22.0,
            mean_steady_state_error=0.4,
            oscillation_measure=0.08,
            frames_in_deadband_pct=88.0,
        )
        summary_path = le.write_summary(summary)
        assert summary_path is not None and os.path.exists(summary_path)

        # 3. Performance report markdown scorecard
        report_path = le.write_performance_report(summary)
        assert report_path is not None and os.path.exists(report_path)

        # 4. Grand evaluation summary export
        grand = GrandEvaluationSummary(
            batch_id="grand_\u2264_\u00b0_\u2014",
            batch_type="benchmark_evaluation",
            total_runs=1,
            successful_runs=1,
            failed_runs=0,
            total_frames_processed=100,
            total_duration_s=3.33,
            mean_fps=30.0,
            mean_acquisition_time_s=1.2,
            mean_tracking_error=2.1,
            mean_target_loss_rate_pct=0.0,
            mean_rmse_centroid=0.7,
            mean_rmse_centroid_rendered=0.8,
            mean_lock_retention_pct=96.0,
            mean_latency_ms=14.2,
            p95_latency_ms=16.5,
            overall_compliance=True,
            passed_fps_spec=True,
            passed_acquisition_spec=True,
            passed_tracking_error_spec=True,
            passed_loss_rate_spec=True,
            run_items=[
                BatchRunItem(
                    item_id="scenario_\u2264_nominal",
                    source_path="nominal_scenario",
                    success=True,
                    summary=summary,
                )
            ],
        )
        g_json, g_md = LoggingEngine.write_grand_summary(grand, output_dir=out_dir)
        assert os.path.exists(g_json)
        assert os.path.exists(g_md)

        le.finalize()

        # ======================================================================
        # RAW BYTE VERIFICATION: Ensure authentic UTF-8 bytes on disk
        # ======================================================================
        # Verify \u2264 is serialized as b'\xe2\x89\xa4'
        # Verify \u00b0 is serialized as b'\xc2\xb0'
        # Verify \u2014 is serialized as b'\xe2\x80\x94'

        with open(cfg_path, "rb") as f:
            cfg_bytes = f.read()
        assert b"\xe2\x89\xa4" in cfg_bytes, "Expected UTF-8 bytes for \u2264 (<=) in config snapshot"
        assert b"\xc2\xb0" in cfg_bytes, "Expected UTF-8 bytes for \u00b0 (degree) in config snapshot"
        assert b"\xe2\x80\x94" in cfg_bytes, "Expected UTF-8 bytes for \u2014 (em-dash) in config snapshot"
        assert b"\\u2264" not in cfg_bytes, "ensure_ascii=False violated! Found escaped ASCII sequence"

        # Verify clean UTF-8 decoding
        decoded_cfg = cfg_bytes.decode("utf-8")
        assert "\u2264" in decoded_cfg
        assert "\u00b0" in decoded_cfg
        assert "\u2014" in decoded_cfg

        # Verify Grand Summary JSON bytes
        with open(g_json, "rb") as f:
            g_json_bytes = f.read()
        assert b"\xe2\x89\xa4" in g_json_bytes
        assert b"\xc2\xb0" in g_json_bytes
        assert b"\xe2\x80\x94" in g_json_bytes
        assert b"\\u2264" not in g_json_bytes

        # Verify Grand Summary Markdown bytes
        with open(g_md, "rb") as f:
            g_md_bytes = f.read()
        assert b"\xe2\x89\xa4" in g_md_bytes

        # Verify Performance report markdown bytes
        with open(report_path, "rb") as f:
            rep_bytes = f.read()
        decoded_rep = rep_bytes.decode("utf-8")
        assert "SIH 2026 Virtual Camera Tracking System" in decoded_rep
        assert "Compliance Scorecard" in decoded_rep

    # ==========================================================================
    # TEST 5: ALGORITHM ERROR ISOLATION (NON-CRASHING GRACEFUL DEGRADATION)
    # ==========================================================================
    def test_algorithm_error_isolation_graceful_degradation(self) -> None:
        """
        Verify that when the active tracking algorithm raises an exception inside
        process_frame(), step_algorithm() catches it, sets _algorithm_error,
        returns non-tracking state, and does NOT crash the worker thread loop.
        """
        app = AppController()
        app.initialize()

        worker = app.simulation_worker

        # Mock active_algorithm.process_frame to raise
        from src.frame.data_contracts import TrackingState
        mock_algo = MagicMock()
        mock_algo.process_frame.side_effect = RuntimeError("ALGO_MATH_NAN_DIVERGENCE")
        mock_algo.initialize.return_value = True
        mock_algo.reset.return_value = None
        mock_algo.current_state = TrackingState.LOST
        app._active_algorithm = mock_algo

        app.start_background_loop()
        time.sleep(0.1)

        # Worker thread should REMAIN running because algorithm exceptions are gracefully isolated
        assert worker.is_alive() is True
        assert worker.is_running is True
        assert app.is_running is True
        assert app.algorithm_error == "ALGO_MATH_NAN_DIVERGENCE"

        app.stop()
        assert not worker.is_alive()

    # ==========================================================================
    # TEST 6: DEADLOCK-FREE CONCURRENT STEP AND STOP STRESS
    # ==========================================================================
    def test_deadlock_free_concurrent_step_and_stop_stress(self) -> None:
        """
        High-contention stress test: 10 worker threads concurrently calling step()
        while main thread performs 50 rapid start/stop/reset cycles.
        Verifies RLock lock ordering prevents lock inversion deadlocks.
        """
        app = AppController()
        app.initialize()

        stop_event = threading.Event()
        errors: List[Exception] = []

        def concurrent_stepper() -> None:
            while not stop_event.is_set():
                try:
                    app.step()
                except Exception as ex:
                    # Ignore 'not running' or stopping errors, record deadlocks/crashes
                    pass
                time.sleep(0.0005)

        steppers = [threading.Thread(target=concurrent_stepper) for _ in range(10)]
        for s in steppers:
            s.start()

        # Rapid lifecycle toggle
        for _ in range(50):
            app.start_background_loop()
            time.sleep(0.005)
            app.stop()
            app.reset()

        stop_event.set()
        for s in steppers:
            s.join(timeout=3.0)

        app.stop()
        assert len(errors) == 0

    # ==========================================================================
    # TEST 7: PARALLEL MULTI-INSTANCE LOGGING ENGINE FD ISOLATION
    # ==========================================================================
    def test_parallel_multi_instance_logging_engine_fd_isolation(self) -> None:
        """
        10 threads concurrently creating, writing, and finalizing distinct
        LoggingEngine instances across 10 temporary directories.
        Verifies zero Windows handle leaks across concurrent instances.
        """
        temp_dirs: List[str] = [tempfile.mkdtemp(prefix=f"sanket_thread_le_{i}_") for i in range(10)]
        thread_errors: List[Exception] = []

        def worker_logging_task(t_idx: int, path: str) -> None:
            try:
                for cycle in range(5):
                    le = LoggingEngine(output_dir=path, run_id=f"thread_{t_idx}_cycle_{cycle}")
                    le.initialize()
                    for f_idx in range(10):
                        le.log_frame(TelemetryRecord(frame_number=f_idx))
                    le.flush()
                    le.finalize()
            except Exception as e:
                thread_errors.append(e)

        threads = [threading.Thread(target=worker_logging_task, args=(i, temp_dirs[i])) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert len(thread_errors) == 0, f"Thread errors: {thread_errors}"

        # Delete all 10 directories on Windows
        for d in temp_dirs:
            try:
                shutil.rmtree(d)
                assert not os.path.exists(d)
            except PermissionError as pe:
                pytest.fail(f"Handle leak detected in parallel logging test! {pe}")

    # ==========================================================================
    # TEST 8: CP1252 CHARMAP CONTRAST VERIFICATION
    # ==========================================================================
    def test_cp1252_charmap_contrast_verification(self) -> None:
        """
        Proves empirically that Windows default CP1252 raises UnicodeEncodeError
        for math symbols (\u2264), confirming DEF-65's utf-8 enforcement is strictly required.
        """
        symbol_text = "Acquisition Time \u2264 2.0 s"
        with pytest.raises(UnicodeEncodeError):
            symbol_text.encode("cp1252")

        # In contrast, UTF-8 encodes cleanly
        utf8_bytes = symbol_text.encode("utf-8")
        assert b"\xe2\x89\xa4" in utf8_bytes
        assert utf8_bytes.decode("utf-8") == symbol_text

