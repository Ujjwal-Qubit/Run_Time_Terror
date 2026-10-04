"""
Adversarial Concurrency Stress Testing & Deadlock Falsification Suite for Workstream A.
Created by Challenger 1 (critic, specialist) to empirically stress-test:
  1. AppController (DEF-62)
  2. SimulationWorkerThread (DEF-61)
  3. VisualizationStateManager (DEF-64)

Empirical Invariant: If a bug cannot be reproduced empirically, it does not count.
"""

from __future__ import annotations

import math
import queue
import random
import sys
import threading
import time
from typing import List, Dict, Any, Optional

import numpy as np
import pytest

from src.app.app_controller import AppController
from src.app.simulation_worker import SimulationWorkerThread
from src.app.visualization_state import VisualizationStateManager
from src.config.config_manager import SystemConfig
from src.frame.data_contracts import VisualizationState


class TestWorkstreamAAdversarialStress:
    """Independent empirical stress testing harness for Workstream A."""

    # =========================================================================
    # STRESS TEST 1: Concurrency Race Condition Falsification
    # =========================================================================
    def test_stress1_concurrency_race_condition_20_threads(self) -> None:
        """
        Stress Test 1: Concurrency Race Condition Falsification.
        Launch 20 concurrent threads calling step(), set_ptz_velocity(), and
        parameter setters simultaneously. Verify zero race conditions or crashes.
        """
        cfg = SystemConfig()
        cfg.simulation.duration_s = 100.0  # 3,000 frames capacity at 30fps
        app = AppController()
        app.initialize(cfg)

        num_threads = 20
        iterations_per_thread = 75
        errors: List[Exception] = []
        error_lock = threading.Lock()
        stop_event = threading.Event()

        # Categorize threads:
        # - 8 Step workers: calling app.step()
        # - 4 PTZ velocity workers: calling app.set_ptz_velocity()
        # - 4 Parameter update workers: calling set_target_speed, set_ptz_parameters, etc.
        # - 4 Query/telemetry workers: calling get_telemetry_snapshot, get_latest_visualization_state, etc.

        step_counts: List[int] = [0] * 8

        def step_worker(worker_idx: int) -> None:
            count = 0
            for i in range(iterations_per_thread):
                if stop_event.is_set():
                    break
                try:
                    state = app.step()
                    if state is not None:
                        assert isinstance(state, VisualizationState)
                        assert isinstance(state.frame_number, int)
                        assert state.frame_number >= 0
                        count += 1
                except Exception as ex:
                    with error_lock:
                        errors.append(ex)
                    break
            step_counts[worker_idx] = count

        def ptz_worker(worker_idx: int) -> None:
            for i in range(iterations_per_thread):
                if stop_event.is_set():
                    break
                try:
                    pan_vel = math.sin(i * 0.1 + worker_idx) * 15.0
                    tilt_vel = math.cos(i * 0.1 + worker_idx) * 10.0
                    app.set_ptz_velocity(pan_vel, tilt_vel)
                    time.sleep(0.0002)
                except Exception as ex:
                    with error_lock:
                        errors.append(ex)
                    break

        def param_worker(worker_idx: int) -> None:
            motion_types = ["LINEAR", "FIGURE8", "BROWNIAN"]
            for i in range(iterations_per_thread):
                if stop_event.is_set():
                    break
                try:
                    # Dynamically mutate various parameters guarded by RLock
                    app.set_target_speed(10.0 + (i % 50))
                    app.set_ptz_parameters(
                        kp=0.5 + (i % 10) * 0.1,
                        ki=0.05 + (i % 5) * 0.01,
                        deadband=2.0 + (i % 3) * 0.5,
                    )
                    app.set_target_size(5 + (i % 15))
                    app.set_target_motion_type(motion_types[i % len(motion_types)])
                    app.set_noise_enabled("gaussian", (i % 2 == 0))
                    app.set_noise_enabled("poisson", (i % 3 == 0))
                    app.set_ptz_enabled(True)
                    app.set_tracking_enabled(True)
                    time.sleep(0.0003)
                except Exception as ex:
                    with error_lock:
                        errors.append(ex)
                    break

        def query_worker(worker_idx: int) -> None:
            for i in range(iterations_per_thread):
                if stop_event.is_set():
                    break
                try:
                    _ = app.get_telemetry_snapshot()
                    _ = app.get_latest_visualization_state()
                    _ = app.frame_count
                    _ = app.is_running
                    _ = app.is_paused
                    _ = app.get_available_algorithms()
                    time.sleep(0.0002)
                except Exception as ex:
                    with error_lock:
                        errors.append(ex)
                    break

        threads: List[threading.Thread] = []
        for idx in range(8):
            threads.append(threading.Thread(target=step_worker, args=(idx,), name=f"step-{idx}"))
        for idx in range(4):
            threads.append(threading.Thread(target=ptz_worker, args=(idx,), name=f"ptz-{idx}"))
        for idx in range(4):
            threads.append(threading.Thread(target=param_worker, args=(idx,), name=f"param-{idx}"))
        for idx in range(4):
            threads.append(threading.Thread(target=query_worker, args=(idx,), name=f"query-{idx}"))

        assert len(threads) == 20, f"Expected 20 threads, got {len(threads)}"

        t0 = time.perf_counter()
        # Launch all 20 threads simultaneously
        for t in threads:
            t.start()

        # Await completion with safe timeout
        for t in threads:
            t.join(timeout=45.0)
            if t.is_alive():
                stop_event.set()
                pytest.fail(f"Thread {t.name} failed to terminate within timeout (deadlock detected)")

        elapsed = time.perf_counter() - t0
        total_steps = sum(step_counts)

        # Cleanup
        app.stop()

        # Empirical Assertions
        assert len(errors) == 0, f"Race condition errors detected across 20 threads: {errors}"
        assert total_steps > 0, "No steps were completed by step workers"
        assert app.frame_count >= total_steps - 1, f"Expected frame_count >= {total_steps - 1}, got {app.frame_count}"
        print(f"\n[Stress Test 1 PASSED] 20 concurrent threads: {total_steps} total steps in {elapsed:.2f}s ({total_steps/elapsed:.1f} steps/s). Zero errors.")

    # =========================================================================
    # STRESS TEST 2: Rapid Lifecycle Stress (1,000 rapid cycles)
    # =========================================================================
    def test_stress2_rapid_lifecycle_1000_cycles(self) -> None:
        """
        Stress Test 2: Rapid Lifecycle Stress (1,000 rapid cycles).
        Execute start_background_loop(), pause(), resume(), stop(), and reset()
        1,000 times in a tight loop. Verify zero deadlocks and zero thread leaks.
        """
        app = AppController()
        app.initialize()

        # Capture initial baseline thread identities
        initial_threads = {t.ident for t in threading.enumerate() if t.is_alive()}

        cycle_count = 1000
        t0 = time.perf_counter()

        for cycle in range(cycle_count):
            # 1. Start background loop (spawns daemon SimulationWorkerThread)
            app.start_background_loop()
            assert app.is_running or app.simulation_worker.is_alive()

            # 2. Pause
            app.pause()
            assert app.is_paused

            # 3. Resume
            app.resume()
            assert not app.is_paused

            # 4. Stop
            app.stop()
            assert not app.is_running

            # 5. Reset
            app.reset()
            assert not app.is_running
            assert not app.is_paused
            assert app.frame_count == 0

        elapsed = time.perf_counter() - t0

        # Verify post-lifecycle state
        assert not app.is_running
        assert not app.simulation_worker.is_alive()
        assert app.simulation_worker.thread is not None
        assert not app.simulation_worker.thread.is_alive()

        # Check for lingering threads / thread leaks
        time.sleep(0.1)  # Brief grace period for OS thread cleanup
        current_threads = [t for t in threading.enumerate() if t.is_alive()]
        leaked_worker_threads = [
            t for t in current_threads
            if t.ident not in initial_threads and "SimulationWorkerThread" in str(getattr(t, "_target", ""))
        ]

        assert len(leaked_worker_threads) == 0, f"Detected leaked worker threads: {leaked_worker_threads}"
        # Total active thread count should remain stable
        print(f"\n[Stress Test 2 PASSED] 1,000 rapid lifecycle cycles in {elapsed:.2f}s ({cycle_count/elapsed:.1f} cycles/s). Zero deadlocks, zero thread leaks.")

    # =========================================================================
    # STRESS TEST 3: Visualization Queue Preemption Falsification
    # =========================================================================
    def test_stress3_visualization_queue_preemption_50000_states(self) -> None:
        """
        Stress Test 3: Visualization Queue Preemption Falsification.
        Launch 10 producer threads pushing 50,000 states under aggressive thread
        preemption (sys.setswitchinterval(1e-6)). Verify zero unhandled
        queue.Full or queue.Empty errors.
        """
        mgr = VisualizationStateManager(maxsize=5)  # Tiny bounded capacity for maximum pressure
        total_producers = 10
        pushes_per_producer = 5000  # 10 x 5,000 = 50,000 states total
        total_expected_pushes = total_producers * pushes_per_producer

        errors: List[Exception] = []
        error_lock = threading.Lock()
        stop_event = threading.Event()
        consumed_count = 0
        consumed_lock = threading.Lock()

        # Save and configure hyper-aggressive thread preemption interval
        old_interval = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)

        dummy_img = np.zeros((16, 16), dtype=np.uint8)

        def producer_worker(producer_id: int) -> None:
            for i in range(pushes_per_producer):
                try:
                    state = VisualizationState(
                        frame_number=producer_id * pushes_per_producer + i,
                        timestamp=float(i * 0.033),
                        pan_angle_deg=float(producer_id),
                        tilt_angle_deg=float(i % 360),
                        camera_fov=4.0,
                        display_image=dummy_img,
                        tracking_state="TRACKING",
                    )
                    mgr.push_state(state)
                except Exception as ex:
                    with error_lock:
                        errors.append(ex)
                    break

        def consumer_worker() -> None:
            nonlocal consumed_count
            local_consumed = 0
            while not stop_event.is_set():
                try:
                    s = mgr.get_latest_state()
                    if s is not None:
                        local_consumed += 1
                except Exception as ex:
                    with error_lock:
                        errors.append(ex)
                    break
                time.sleep(0.00001)
            with consumed_lock:
                consumed_count += local_consumed

        t0 = time.perf_counter()
        try:
            # Launch 2 consumer threads
            consumers = [
                threading.Thread(target=consumer_worker, daemon=True, name=f"consumer-{i}")
                for i in range(2)
            ]
            for c in consumers:
                c.start()

            # Launch 10 producer threads
            producers = [
                threading.Thread(target=producer_worker, args=(p,), name=f"producer-{p}")
                for p in range(total_producers)
            ]
            for p in producers:
                p.start()

            # Wait for all producers to finish
            for p in producers:
                p.join(timeout=30.0)
                if p.is_alive():
                    pytest.fail(f"Producer thread {p.name} timed out under preemption stress")

            # Signal consumers to stop and wait
            stop_event.set()
            for c in consumers:
                c.join(timeout=2.0)

        finally:
            # Always restore system switch interval
            sys.setswitchinterval(old_interval)

        elapsed = time.perf_counter() - t0

        # Final queue verification
        final_state = mgr.get_latest_state()
        assert mgr.queue.qsize() <= 5

        # Empirical Assertions
        assert len(errors) == 0, f"Encountered unhandled queue exceptions: {errors}"
        print(f"\n[Stress Test 3 PASSED] 50,000 states across 10 producers under 1µs preemption in {elapsed:.2f}s ({total_expected_pushes/elapsed:.1f} states/s). Zero unhandled queue errors.")

    # =========================================================================
    # STRESS TEST 4: Boundary Stress — Concurrent Mutation During Lifecycle
    # =========================================================================
    def test_stress4_concurrent_step_and_lifecycle_mutation(self) -> None:
        """
        Adversarial test: Interleave concurrent app.step() and get_latest_visualization_state()
        calls while another thread continuously calls stop() and reset().
        Verify no unhandled NoneType errors, race conditions, or unhandled exceptions.
        """
        app = AppController()
        app.initialize()

        stop_test = threading.Event()
        errors: List[Exception] = []
        error_lock = threading.Lock()

        def stepper() -> None:
            while not stop_test.is_set():
                try:
                    _ = app.step()
                except Exception as ex:
                    with error_lock:
                        errors.append(ex)
                time.sleep(0.001)

        def lifecycle_mutator() -> None:
            for _ in range(50):
                if stop_test.is_set():
                    break
                try:
                    app.stop()
                    app.reset()
                    app.initialize()
                except Exception as ex:
                    with error_lock:
                        errors.append(ex)
                time.sleep(0.005)

        t_step = threading.Thread(target=stepper, name="stepper-interleaved")
        t_life = threading.Thread(target=lifecycle_mutator, name="lifecycle-mutator")

        t_step.start()
        t_life.start()

        t_life.join(timeout=20.0)
        stop_test.set()
        t_step.join(timeout=5.0)

        app.stop()
        assert len(errors) == 0, f"Errors during interleaved lifecycle mutation: {errors}"
        print("\n[Stress Test 4 PASSED] Interleaved lifecycle mutation during concurrent step(): Zero errors.")
