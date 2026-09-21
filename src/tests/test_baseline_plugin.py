"""
Tests for Baseline Tracking Algorithm Plugin (Phase 6.3)

Verifies:
1. Discovery and loading via the Phase 6.2 PluginLoader.
2. Complete ITrackingAlgorithm lifecycle compliance (initialize, process_frame, reset).
3. Zero state leakage across scenario runs (lifecycle isolation).
4. Strict ground-truth firewall integrity.
5. Exact behavioral equivalence against the legacy monolithic pipeline on identical frame streams.
6. Performance verification (PS requirement >= 20 FPS).
"""

import math
import time
from typing import List, Tuple
import numpy as np
import pytest

from src.api.v1 import ITrackingAlgorithm, FramePacket as PublicFramePacket, TrackingResult as PublicTrackingResult
from src.frame.data_contracts import (
    CandidateRegion,
    CentroidResult,
    FramePacket as InternalFramePacket,
    FrameSource,
    ROI,
    TrackingState,
)
from src.plugins.algorithms.baseline_tracker.baseline_tracker import BaselineTracker
from src.plugins.loader import PluginLoader
from src.tracker.ai_classifier import AIClassifier
from src.tracker.candidate_identifier import CandidateIdentifier
from src.tracker.centroid_estimator import IntensityWeightedCentroidEstimator
from src.tracker.detection_engine import P0ThresholdDetector
from src.tracker.state_manager import TrackingStateManager
from src.tracker.temporal_tracker import ConstantVelocityKalmanTracker


# --- 1. Discovery and Loading ---

def test_baseline_plugin_discovery():
    """Verify PluginLoader discovers the baseline_tracker in src/plugins/algorithms."""
    loader = PluginLoader()
    result = loader.discover()

    assert "baseline_tracker" in result
    assert len(loader.failures) == 0
    discovered = result["baseline_tracker"]
    assert discovered.name == "baseline_tracker"
    assert discovered.manifest.version == "1.0.0"
    assert discovered.manifest.api_version == "v1"
    assert discovered.manifest.entry_point == "baseline_tracker:BaselineTracker"


def test_baseline_plugin_loading():
    """Verify PluginLoader loads and instantiates BaselineTracker."""
    loader = PluginLoader()
    loader.discover()
    loaded = loader.load_plugin("baseline_tracker")

    assert loaded.manifest.name == "baseline_tracker"
    assert loaded.algorithm_class.__name__ == "BaselineTracker"
    assert isinstance(loaded.instance, ITrackingAlgorithm)
    assert isinstance(loaded.instance, loaded.algorithm_class)


# --- 2. Lifecycle & Configuration ---

def test_baseline_plugin_lifecycle_default():
    """Verify initialize, process_frame, and reset lifecycle with default parameters."""
    tracker = BaselineTracker()
    assert tracker.initialize({}) is True
    assert tracker.current_state == TrackingState.SEARCHING
    assert tracker.is_locked is False

    # Process blank frame
    blank = PublicFramePacket(
        image=np.zeros((480, 640), dtype=np.uint8),
        timestamp=0.0,
        frame_number=0,
        resolution=(640, 480)
    )
    res = tracker.process_frame(blank)
    assert isinstance(res, PublicTrackingResult)
    assert res.algorithm_is_tracking is False
    assert res.centroid_x is None
    assert res.centroid_y is None

    # Reset
    tracker.reset()
    assert tracker.current_state == TrackingState.SEARCHING
    assert tracker.is_locked is False


def test_baseline_plugin_custom_configuration():
    """Verify adaptation of configuration dictionary into existing dataclasses."""
    tracker = BaselineTracker()
    config = {
        "detector": {"threshold_offset": 25, "bg_kernel_size": 19},
        "tracker": {"gate_max_distance": 50.0, "process_noise_pos": 0.5},
        "state": {"lock_confirm_frames": 4},
        "use_ai_classifier": False
    }
    assert tracker.initialize(config) is True
    assert tracker._detector_cfg.threshold_offset == 25
    assert tracker._detector_cfg.bg_kernel_size == 19
    assert tracker._tracker_cfg.gate_max_distance == 50.0
    assert tracker._tracker_cfg.process_noise_pos == 0.5
    assert tracker._state_cfg.lock_confirm_frames == 4
    assert tracker._use_ai_classifier is False


def test_baseline_plugin_invalid_configuration_handling():
    """Verify graceful handling when invalid configuration types are passed."""
    tracker = BaselineTracker()
    assert tracker.initialize("not_a_dict") is False  # type: ignore


# --- 3. Frame Processing Edge Cases ---

def test_baseline_plugin_bright_target_acquisition():
    """Verify target acquisition, lock establishment, and centroid reporting."""
    tracker = BaselineTracker()
    tracker.initialize({"use_ai_classifier": False})

    target_x, target_y = 320.0, 240.0
    dt = 1.0 / 30.0

    # Feed 10 frames with target stationary at (320, 240)
    tracking_established = False
    for f in range(10):
        img = np.full((480, 640), fill_value=20, dtype=np.uint8)
        # Draw target beacon patch
        bx, by = int(round(target_x - 5)), int(round(target_y - 5))
        img[by:by + 10, bx:bx + 10] = 230

        packet = PublicFramePacket(
            image=img,
            timestamp=f * dt,
            frame_number=f,
            resolution=(640, 480)
        )
        res = tracker.process_frame(packet)

        if res.algorithm_is_tracking:
            tracking_established = True
            assert res.centroid_x is not None
            assert res.centroid_y is not None
            assert abs(res.centroid_x - target_x) < 2.0
            assert abs(res.centroid_y - target_y) < 2.0
            assert res.confidence is not None and res.confidence > 0.0
            assert res.roi is not None

    assert tracking_established is True, "Algorithm failed to establish lock across 10 frames"


# --- 4. Lifecycle Isolation (Zero State Leakage) ---

def test_baseline_plugin_lifecycle_isolation():
    """
    Verifies that calling reset() flushes all temporal state and history.
    Running the exact same frame sequence twice must produce bitwise identical results.
    """
    tracker = BaselineTracker()
    tracker.initialize({"use_ai_classifier": False})

    dt = 1.0 / 30.0
    num_frames = 40

    def generate_frames():
        frames = []
        for f in range(num_frames):
            img = np.full((480, 640), fill_value=20, dtype=np.uint8)
            tx = 150.0 + 10.0 * (f * dt)
            ty = 150.0 + 5.0 * (f * dt)
            bx, by = int(round(tx - 5)), int(round(ty - 5))
            img[by:by + 10, bx:bx + 10] = 220
            frames.append(PublicFramePacket(
                image=img,
                timestamp=f * dt,
                frame_number=f,
                resolution=(640, 480)
            ))
        return frames

    test_frames = generate_frames()

    # Pass 1
    outputs_pass_1: List[Tuple[bool, float | None, float | None]] = []
    for pkt in test_frames:
        r = tracker.process_frame(pkt)
        outputs_pass_1.append((r.algorithm_is_tracking, r.centroid_x, r.centroid_y))

    # Reset
    tracker.reset()

    # Pass 2
    outputs_pass_2: List[Tuple[bool, float | None, float | None]] = []
    for pkt in test_frames:
        r = tracker.process_frame(pkt)
        outputs_pass_2.append((r.algorithm_is_tracking, r.centroid_x, r.centroid_y))

    assert len(outputs_pass_1) == len(outputs_pass_2) == num_frames
    for f_idx, (out1, out2) in enumerate(zip(outputs_pass_1, outputs_pass_2)):
        assert out1[0] == out2[0], f"Tracking state mismatch at frame {f_idx}: {out1[0]} vs {out2[0]}"
        if out1[0]:  # When tracking
            assert out1[1] == out2[1], f"Centroid X mismatch at frame {f_idx}: {out1[1]} vs {out2[1]}"
            assert out1[2] == out2[2], f"Centroid Y mismatch at frame {f_idx}: {out1[2]} vs {out2[2]}"


# --- 5. Ground-Truth Firewall Integrity ---

def test_baseline_plugin_firewall():
    """Verify BaselineTracker has zero access to ground truth or simulator state."""
    tracker = BaselineTracker()
    assert not hasattr(tracker, "ground_truth")
    assert not hasattr(tracker, "target_manager")
    assert not hasattr(tracker, "scene_manager")
    assert not hasattr(tracker, "camera_model")
    assert not hasattr(tracker, "ptz_controller")

    # Ensure TypeError if unexpected ground-truth kwargs or packets are supplied
    with pytest.raises(TypeError):
        tracker.process_frame("invalid_packet")  # type: ignore


# --- 6. CRITICAL: Behavioral Equivalence against Legacy Monolithic Pipeline ---

def test_behavioral_equivalence_on_identical_frame_stream():
    """
    CRITICAL TEST: Verifies that Pipeline A (legacy internal monolithic pipeline)
    and Pipeline B (BaselineTracker plugin) produce IDENTICAL behavior when fed the
    EXACT SAME deterministic frame stream.

    Diagnostic Protocol:
    1. Test exact equality first.
    2. If any difference occurs, identify FIRST divergent frame and diagnose cause.
    3. Treat any unexplained behavioral difference as an immediate FAILURE.
    """
    # Initialize Pipeline A (Legacy monolithic components)
    det_a = P0ThresholdDetector()
    ident_a = CandidateIdentifier()
    cent_a = IntensityWeightedCentroidEstimator()
    track_a = ConstantVelocityKalmanTracker()
    state_a = TrackingStateManager()

    # Initialize Pipeline B (BaselineTracker plugin with rule-based identifier for fair comparison)
    tracker_b = BaselineTracker()
    tracker_b.initialize({"use_ai_classifier": False})

    dt = 1.0 / 30.0
    total_frames = 100
    x0, y0 = 150.0, 150.0
    vx_true, vy_true = 25.0, 15.0

    np.random.seed(42)

    divergence_found = False
    first_divergent_frame = None
    divergence_reason = ""

    a_tracking_states = []
    b_tracking_states = []
    a_centroids = []
    b_centroids = []

    for f in range(total_frames):
        t_sim = f * dt
        true_x = x0 + vx_true * t_sim
        true_y = y0 + vy_true * t_sim

        # -------------------------------------------------------------------
        # Generate Identical Input Frame
        # -------------------------------------------------------------------
        is_occluded = (40 <= f <= 44)  # 5-frame occlusion
        is_outlier = (f == 30)          # Single outlier
        is_noisy = (20 <= f <= 29)      # Noise stage

        raw_img = np.full((480, 640), fill_value=25, dtype=np.uint8)

        if not is_occluded:
            if is_outlier:
                meas_x, meas_y = 550.0, 420.0
            else:
                noise_x = float(np.random.normal(0, 1.5)) if is_noisy else 0.0
                noise_y = float(np.random.normal(0, 1.5)) if is_noisy else 0.0
                meas_x = true_x + noise_x
                meas_y = true_y + noise_y

            # Render synthetic beacon spot
            y_g, x_g = np.ogrid[:480, :640]
            dist = np.sqrt((x_g - meas_x) ** 2 + (y_g - meas_y) ** 2)
            raw_img[dist <= 4.0] = 230

        # Exactly identical packets
        public_packet = PublicFramePacket(
            image=raw_img.copy(),
            timestamp=t_sim,
            frame_number=f,
            resolution=(640, 480)
        )
        internal_packet_a = InternalFramePacket(
            image=raw_img.copy(),
            width=640,
            height=480,
            frame_number=f,
            timestamp=t_sim,
            source=FrameSource.SIMULATION
        )

        # -------------------------------------------------------------------
        # Pipeline A Execution (Legacy monolithic orchestration)
        # -------------------------------------------------------------------
        roi_a = track_a.get_roi(640, 480)
        det_res_a = det_a.detect(internal_packet_a, roi=roi_a)
        pred_pos_a = track_a.predict() if track_a.is_initialized else None
        ident_res_a = ident_a.identify(
            det_res_a.candidates,
            predicted_position=pred_pos_a,
            current_state=state_a.current_state,
            frame_number=f,
            timestamp=t_sim
        )
        cent_res_a = None
        if ident_res_a.valid and ident_res_a.selected_candidate is not None:
            cent_res_a = cent_a.estimate(internal_packet_a, ident_res_a.selected_candidate)
        track_res_a = track_a.update(cent_res_a, dt=0.0, frame_number=f, timestamp=t_sim)
        state_res_a = state_a.update(track_res_a, timestamp=t_sim)

        is_tracking_a = (state_res_a.state == TrackingState.TRACKING)
        if is_tracking_a:
            if cent_res_a is not None and cent_res_a.valid:
                cx_a = float(cent_res_a.x)
                cy_a = float(cent_res_a.y)
            else:
                cx_a = float(track_res_a.estimated_x)
                cy_a = float(track_res_a.estimated_y)
        else:
            cx_a = None
            cy_a = None

        a_tracking_states.append(is_tracking_a)
        a_centroids.append((cx_a, cy_a))

        # -------------------------------------------------------------------
        # Pipeline B Execution (BaselineTracker Plugin)
        # -------------------------------------------------------------------
        res_b = tracker_b.process_frame(public_packet)

        b_tracking_states.append(res_b.algorithm_is_tracking)
        b_centroids.append((res_b.centroid_x, res_b.centroid_y))

        # -------------------------------------------------------------------
        # Frame-by-Frame Diagnostic Comparison
        # -------------------------------------------------------------------
        # 1. State equality
        if res_b.algorithm_is_tracking != is_tracking_a:
            if not divergence_found:
                first_divergent_frame = f
                divergence_reason = f"Tracking state mismatch at frame {f}: Pipeline A={is_tracking_a}, Pipeline B={res_b.algorithm_is_tracking}"
                divergence_found = True

        # 2. Centroid equality when tracking
        if is_tracking_a and res_b.algorithm_is_tracking:
            dx = abs(res_b.centroid_x - cx_a)  # type: ignore
            dy = abs(res_b.centroid_y - cy_a)  # type: ignore
            # Exact bitwise or sub-floating point check
            if dx > 1e-12 or dy > 1e-12:
                if not divergence_found:
                    first_divergent_frame = f
                    divergence_reason = f"Centroid coordinate discrepancy at frame {f}: dx={dx}, dy={dy}"
                    divergence_found = True

        # 3. ROI equality
        roi_b_tuple = res_b.roi
        roi_a_tuple = (roi_a.x, roi_a.y, roi_a.width, roi_a.height) if roi_a else None
        if roi_b_tuple != roi_a_tuple:
            if not divergence_found:
                first_divergent_frame = f
                divergence_reason = f"ROI discrepancy at frame {f}: Pipeline A={roi_a_tuple}, Pipeline B={roi_b_tuple}"
                divergence_found = True

    # Assert no unexplained behavioral divergence occurred
    if divergence_found:
        pytest.fail(f"Behavioral divergence detected! First divergent frame: {first_divergent_frame}. Reason: {divergence_reason}")

    # Summary checks: Both must have acquired, lost, and reacquired at the identical frames
    assert a_tracking_states == b_tracking_states, "Full tracking state trajectories do not match"
    assert a_centroids == b_centroids, "Full centroid estimation trajectories do not match"


# --- 7. Performance & Latency Verification ---

def test_baseline_plugin_processing_speed():
    """
    Performance verification:
    - PS Requirement: Processing speed >= 20 FPS (<= 50 ms / frame).
    - Internal Engineering Targets: Speed > 500 FPS, Adapter Overhead < 0.05 ms.
    """
    tracker = BaselineTracker()
    tracker.initialize({"use_ai_classifier": False})

    # Prepare standard frame
    img = np.full((480, 640), fill_value=25, dtype=np.uint8)
    img[235:245, 315:325] = 220
    packet = PublicFramePacket(
        image=img,
        timestamp=0.033,
        frame_number=1,
        resolution=(640, 480)
    )

    # Warmup
    for _ in range(5):
        tracker.process_frame(packet)

    # Timed benchmark across 50 frames
    num_runs = 50
    latencies_ms = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        tracker.process_frame(packet)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    mean_latency_ms = float(np.mean(latencies_ms))
    achieved_fps = 1000.0 / mean_latency_ms if mean_latency_ms > 0 else 9999.0

    print(f"\n[PERFORMANCE] BaselineTracker Mean Latency: {mean_latency_ms:.3f} ms ({achieved_fps:.1f} FPS)")

    # PS Requirement Assertion
    assert achieved_fps >= 20.0, f"Failed PS Requirement of >= 20 FPS (achieved: {achieved_fps:.1f} FPS)"
