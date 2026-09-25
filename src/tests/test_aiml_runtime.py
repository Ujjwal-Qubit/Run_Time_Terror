from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from src.aiml.calibration import ProbabilityCalibrator
from src.aiml.candidate_classifier import LearnedCandidateClassifier
from src.aiml.contracts import PredictionRequest, TrackObservation
from src.aiml.feature_extractor import CandidateFeatureExtractor, FEATURE_NAMES
from src.aiml.model_loader import ModelLoader
from src.aiml.temporal_predictor import (
    BoundedHistoryBuffer,
    KalmanPredictor,
    ResidualCorrectionPredictor,
)
from src.api.v1.contracts import FramePacket as PublicFramePacket
from src.config.config_manager import SystemConfig
from src.frame.data_contracts import CandidateRegion, FramePacket, FrameSource
from src.plugins.algorithms.baseline_tracker.baseline_tracker import BaselineTracker


def _candidate(candidate_id: int = 17) -> CandidateRegion:
    return CandidateRegion(
        bbox_x=100,
        bbox_y=80,
        bbox_w=10,
        bbox_h=10,
        peak_intensity=230.0,
        mean_intensity=190.0,
        area=100,
        compactness=1.0,
        candidate_id=candidate_id,
        detection_score=0.73,
    )


def test_feature_extractor_uses_detector_score_and_candidate_id():
    image = np.zeros((200, 300), dtype=np.uint8)
    packet = FramePacket(4, 0.1, image, 300, 200, FrameSource.SIMULATION)
    feature = CandidateFeatureExtractor().extract(packet, _candidate())

    assert feature.candidate_id == 17
    assert feature.feature_names == FEATURE_NAMES
    assert feature.values[-1] == pytest.approx(0.73)
    assert all(math.isfinite(value) for value in feature.values)


def test_model_loader_rejects_non_finite_parameters(tmp_path: Path):
    model = {
        "weights": [float("nan")],
        "bias": 0.0,
        "mean": [0.0],
        "std": [1.0],
        "feature_names": ["x"],
    }
    (tmp_path / "model.json").write_text(json.dumps(model), encoding="utf-8")

    with pytest.raises(ValueError, match="non-finite"):
        ModelLoader.load_candidate_classifier_package(str(tmp_path))


def test_learned_classifier_loads_nested_project_artifact():
    project_root = Path(__file__).resolve().parents[2]
    classifier = LearnedCandidateClassifier("models/candidate_classifier/v001")
    assert classifier.package is not None
    assert classifier.package.feature_names == FEATURE_NAMES
    assert (project_root / "models/candidate_classifier/v001/model.json").is_file()


def test_probability_calibration_clamps_out_of_range_scores():
    calibrator = ProbabilityCalibrator()
    assert 0.0 < calibrator.calibrate(-2.0) < 0.01
    assert 0.99 < calibrator.calibrate(3.0) < 1.0


def test_temporal_predictor_uses_last_accepted_timestamp():
    predictor = KalmanPredictor()
    predictor.update(TrackObservation(0.0, 0.0, 0.0, True, True, 1.0, "TRACKING"))
    predictor.update(TrackObservation(0.1, 10.0, 0.0, True, True, 1.0, "TRACKING"))
    # A rejected/missing frame must not become the velocity timestamp origin.
    predictor.update(TrackObservation(0.2, None, None, False, False, 0.0, "REACQUIRING"))
    predictor.update(TrackObservation(0.3, 30.0, 0.0, True, True, 1.0, "TRACKING"))

    assert predictor._vx == pytest.approx(64.0)


def test_aiml_candidate_classifier_runs_inside_plugin_firewall():
    image = np.full((480, 640), 25, dtype=np.uint8)
    image[235:245, 315:325] = 235
    tracker = BaselineTracker()
    assert tracker.initialize({
        "aiml": {
            "candidate_classifier_enabled": True,
            "candidate_model_dir": "models/candidate_classifier/v001",
            "temporal_predictor_enabled": True,
            "temporal_model_dir": "models/temporal_predictor/v001",
        }
    })

    for frame in range(6):
        result = tracker.process_frame(
            PublicFramePacket(image, frame / 30.0, frame, (640, 480))
        )
        assert isinstance(result.algorithm_is_tracking, bool)
    assert tracker._learned_classifier is not None
    assert tracker._feature_extractor is not None
    assert tracker._learned_classifier.package is not None
    assert tracker._temporal_predictor is not None
    assert tracker._temporal_predictor.is_loaded
    assert len(tracker._temporal_predictor.history) == 6


def test_system_config_round_trips_aiml_options():
    config = SystemConfig.from_dict({"aiml": {
        "candidate_classifier_enabled": True,
        "candidate_model_dir": "models/custom/v1",
        "temporal_predictor_enabled": True,
        "temporal_model_dir": "models/temporal/custom/v1",
    }})

    assert config.aiml.candidate_classifier_enabled is True
    assert config.aiml.candidate_model_dir == "models/custom/v1"
    assert config.aiml.temporal_predictor_enabled is True
    assert config.aiml.temporal_model_dir == "models/temporal/custom/v1"
    assert SystemConfig.from_dict(config.to_dict()).aiml == config.aiml


def test_bounded_history_remains_capped():
    history = BoundedHistoryBuffer(maxlen=4)
    for frame in range(20):
        history.append(TrackObservation(frame / 30, float(frame), 0.0, True, True, 1.0, "TRACKING"))
    assert len(history) == 4
    assert len(history.get_history()) == 4


def test_residual_predictor_loads_and_validates_temporal_artifact():
    project_root = Path(__file__).resolve().parents[2]
    predictor = ResidualCorrectionPredictor(
        model_dir=str(project_root / "models/temporal_predictor/v001")
    )
    assert predictor.is_loaded

    for frame in range(10):
        predictor.update(TrackObservation(
            timestamp=frame / 30.0,
            x=100.0 + frame * 1.2,
            y=200.0 + frame * 0.8,
            measurement_valid=True,
            measurement_accepted=True,
            confidence=0.9,
            state="TRACKING",
        ))
    prediction = predictor.predict(PredictionRequest(
        frame_number=10,
        timestamp=10 / 30.0,
        history=predictor.history.get_history(),
        frame_width=640,
        frame_height=480,
        horizon_seconds=1 / 30.0,
    ))
    assert math.isfinite(prediction.predicted_x)
    assert math.isfinite(prediction.predicted_y)


def test_dataset_split_builder_never_leaks_groups():
    from src.data.split_builder import SplitBuilder

    records = [
        {"run_id": f"run-{group}", "frame": frame}
        for group in range(10)
        for frame in range(4)
    ]
    train, validation, test = SplitBuilder.build_split(records, seed=9)
    groups = [set(row["run_id"] for row in part) for part in (train, validation, test)]

    assert all(groups)
    assert groups[0].isdisjoint(groups[1])
    assert groups[0].isdisjoint(groups[2])
    assert groups[1].isdisjoint(groups[2])


def test_dataset_split_builder_rejects_too_few_groups():
    from src.data.split_builder import SplitBuilder

    with pytest.raises(ValueError, match="three distinct groups"):
        SplitBuilder.build_split([{"run_id": "one"}, {"run_id": "two"}])
