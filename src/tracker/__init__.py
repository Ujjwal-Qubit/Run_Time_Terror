"""
Tracker domain — Modules 9, 10, 11, 12 per Architecture v1.2.
"""

from src.tracker.detection_engine import P0ThresholdDetector, DetectionEngine
from src.tracker.centroid_estimator import (
    IntensityWeightedCentroidEstimator,
    CentroidEstimator,
)
from src.tracker.candidate_identifier import (
    CandidateIdentifier,
    BeaconIdentifier,
)
from src.tracker.temporal_tracker import (
    ConstantVelocityKalmanTracker,
    TemporalTracker,
    TrackingEngine,
    KalmanTracker,
)
from src.tracker.state_manager import (
    TrackingStateManager,
    StateManager,
    TrackingStateMachine,
)

__all__ = [
    "P0ThresholdDetector",
    "DetectionEngine",
    "IntensityWeightedCentroidEstimator",
    "CentroidEstimator",
    "CandidateIdentifier",
    "BeaconIdentifier",
    "ConstantVelocityKalmanTracker",
    "TemporalTracker",
    "TrackingEngine",
    "KalmanTracker",
    "TrackingStateManager",
    "StateManager",
    "TrackingStateMachine",
]

