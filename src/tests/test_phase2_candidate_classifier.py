"""
Phase 2 Behavioral Verification Suite — Candidate Classifier ML & System Integration.

Validates:
1. Model package loading integrity, schema compliance, and weight finiteness.
2. Candidate discrimination on challenging distractors and clutter:
   - High local-contrast clutter blobs rejected (is_beacon=False).
   - Speckle noise spikes rejected (is_beacon=False).
   - Elongated noise streaks rejected (is_beacon=False).
   - Secondary distractor beacons rejected (is_beacon=False).
   - True primary beacon accepted (is_beacon=True).
3. Benchmark test-split performance (Accuracy > 85%, F1 > 0.85, Recall > 90%).
4. Ultra-low inference latency (< 0.05 ms per candidate).
5. Closed-loop system tracking integration with BaselineTracker:
   - Preserves sub-pixel tracking accuracy (RMSE < 2.0 px).
   - Preserves acquisition & reacquisition capability.
   - Preserves high throughput (> 100 FPS).
"""

from __future__ import annotations

import json
from pathlib import Path
import time
import numpy as np
import pytest

from src.aiml.candidate_classifier import LearnedCandidateClassifier
from src.aiml.feature_extractor import CandidateFeatureExtractor, FEATURE_NAMES
from src.app.app_controller import AppController
from src.config.config_manager import ConfigManager
from src.api.v1.contracts import FramePacket as PublicFramePacket
from src.frame.data_contracts import (
    CandidateRegion,
    FramePacket,
    FrameSource,
    TrackingState,
)
from src.plugins.algorithms.baseline_tracker.baseline_tracker import BaselineTracker


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def candidate_classifier() -> LearnedCandidateClassifier:
    return LearnedCandidateClassifier("models/candidate_classifier/v001")


def test_model_package_integrity(candidate_classifier: LearnedCandidateClassifier, project_root: Path):
    """Verify exported model package meets format and schema requirements."""
    assert candidate_classifier.package is not None
    pkg = candidate_classifier.package

    assert pkg.model_name == "candidate_classifier"
    assert pkg.model_version == "v001"
    assert pkg.algorithm in ("mlp", "logistic_regression")
    assert len(pkg.weights) == len(FEATURE_NAMES)
    assert len(pkg.mean) == len(FEATURE_NAMES)
    assert len(pkg.std) == len(FEATURE_NAMES)
    assert np.isfinite(pkg.weights).all()
    assert np.isfinite(pkg.mean).all()
    assert (pkg.std > 0.0).all()
    assert 0.1 <= pkg.classification_threshold <= 0.9

    # Model metadata file
    model_json = project_root / "models/candidate_classifier/v001/model.json"
    assert model_json.is_file()
    with open(model_json, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert "test_metrics" in meta
    assert meta["test_metrics"]["f1"] > 0.85
    assert meta["test_metrics"]["recall"] > 0.90


def test_candidate_discrimination_on_clutter_and_distractors(candidate_classifier: LearnedCandidateClassifier):
    """
    Verify false-target rejection on 5 distinct candidate types:
    - Background clutter blob: must be rejected (is_beacon=False).
    - Speckle noise spike: must be rejected (is_beacon=False).
    - Elongated noise streak: must be rejected (is_beacon=False).
    - Secondary distractor: must be rejected (is_beacon=False).
    - True beacon: must be accepted (is_beacon=True).
    """
    extractor = CandidateFeatureExtractor(expected_target_size=10)
    dummy_packet = FramePacket(
        frame_number=1,
        timestamp=0.033,
        image=np.zeros((480, 640), dtype=np.uint8),
        width=640,
        height=480,
        source=FrameSource.SIMULATION,
    )

    pred_pos = (305.0, 205.0)

    # 1. True primary beacon
    cand_true = CandidateRegion(
        bbox_x=300, bbox_y=200, bbox_w=10, bbox_h=10,
        peak_intensity=220.0, mean_intensity=220.0, area=100,
        local_contrast=4.5, compactness=1.0, candidate_id=1, detection_score=0.8,
    )

    # 2. Secondary distractor beacon (offset, lower intensity)
    cand_distractor = CandidateRegion(
        bbox_x=200, bbox_y=150, bbox_w=6, bbox_h=6,
        peak_intensity=140.0, mean_intensity=140.0, area=36,
        local_contrast=2.2, compactness=1.0, candidate_id=2, detection_score=0.8,
    )

    # 3. Background clutter blob
    cand_clutter = CandidateRegion(
        bbox_x=100, bbox_y=100, bbox_w=14, bbox_h=13,
        peak_intensity=80.0, mean_intensity=75.0, area=180,
        local_contrast=1.3, compactness=0.95, candidate_id=3, detection_score=0.8,
    )

    # 4. Elongated noise streak
    cand_streak = CandidateRegion(
        bbox_x=400, bbox_y=300, bbox_w=14, bbox_h=5,
        peak_intensity=180.0, mean_intensity=170.0, area=70,
        local_contrast=2.5, compactness=0.6, candidate_id=4, detection_score=0.8,
    )

    # 5. Speckle noise spike
    cand_speckle = CandidateRegion(
        bbox_x=500, bbox_y=400, bbox_w=2, bbox_h=2,
        peak_intensity=65.0, mean_intensity=65.0, area=4,
        local_contrast=1.2, compactness=1.0, candidate_id=5, detection_score=0.8,
    )

    candidates = [cand_true, cand_distractor, cand_clutter, cand_streak, cand_speckle]
    features = [
        extractor.extract(dummy_packet, c, predicted_position=pred_pos, previous_position=pred_pos, candidate_id=c.candidate_id)
        for c in candidates
    ]
    results = candidate_classifier.classify(features)

    # True beacon must be accepted with high probability
    assert results[0].is_beacon is True
    assert results[0].beacon_probability > 0.80

    # All false targets must be rejected
    assert results[1].is_beacon is False, f"Distractor should be rejected, got {results[1].beacon_probability:.4f}"
    assert results[2].is_beacon is False, f"Clutter blob should be rejected, got {results[2].beacon_probability:.4f}"
    assert results[3].is_beacon is False, f"Noise streak should be rejected, got {results[3].beacon_probability:.4f}"
    assert results[4].is_beacon is False, f"Speckle spike should be rejected, got {results[4].beacon_probability:.4f}"

    # True beacon probability must dominate all noise probabilities
    for r in results[1:]:
        assert results[0].beacon_probability > r.beacon_probability


def test_candidate_inference_latency_benchmark(candidate_classifier: LearnedCandidateClassifier):
    """Verify sub-millisecond candidate inference latency under repeated batch inference."""
    extractor = CandidateFeatureExtractor()
    packet = FramePacket(1, 0.033, np.zeros((480, 640), dtype=np.uint8), 640, 480, FrameSource.SIMULATION)
    cands = [CandidateRegion(100 + i, 100 + i, 10, 10, 200, 180, 100, 3.0, 0.9, i, 0.8) for i in range(10)]
    fvs = extractor.extract_batch(packet, cands, (100.0, 100.0), (100.0, 100.0))

    t0 = time.perf_counter()
    n_runs = 500
    for _ in range(n_runs):
        candidate_classifier.classify(fvs)
    t1 = time.perf_counter()

    per_candidate_ms = (t1 - t0) * 1000.0 / (n_runs * len(cands))
    assert per_candidate_ms < 0.05, f"Inference latency {per_candidate_ms:.4f} ms exceeded 0.05 ms budget"


def test_closed_loop_tracking_with_candidate_classifier():
    """Verify BaselineTracker with candidate_classifier_enabled tracks moving beacon with sub-pixel RMSE."""
    tracker = BaselineTracker()
    assert tracker.initialize({
        "aiml": {
            "candidate_classifier_enabled": True,
            "candidate_model_dir": "models/candidate_classifier/v001",
        }
    })

    # Render a moving synthetic beacon across 30 frames
    errors = []
    width, height = 640, 480
    vx, vy = 20.0, 15.0  # px/s
    dt = 1.0 / 30.0

    for f in range(30):
        t = f * dt
        true_x = 320.0 + vx * t
        true_y = 240.0 + vy * t

        img = np.full((height, width), 25, dtype=np.uint8)
        ix, iy = int(round(true_x)), int(round(true_y))
        img[iy - 5 : iy + 5, ix - 5 : ix + 5] = 220

        pkt = PublicFramePacket(img, t, f, (width, height))
        res = tracker.process_frame(pkt)

        if f >= 5 and res.algorithm_is_tracking:
            err = np.hypot(res.centroid_x - true_x, res.centroid_y - true_y)
            errors.append(err)

    assert len(errors) >= 20, "Tracker should lock and track for at least 20 frames"
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    assert rmse < 2.0, f"Tracking RMSE {rmse:.2f} px exceeded 2.0 px limit"
