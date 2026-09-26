"""
AIML Data Contracts — Typed data transfer objects for feature extraction,
candidate classification, and temporal prediction.

Per AIML Backend Integration Specification §5.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class CandidateFeatureVector:
    """
    Feature vector representation for a single detected CandidateRegion.
    Never contains raw simulator ground truth or true target states.
    """

    frame_number: int
    candidate_id: int
    values: Tuple[float, ...]
    feature_names: Tuple[str, ...]
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int


@dataclass(frozen=True)
class CandidateClassification:
    """
    Classification output for a single candidate.
    """

    candidate_id: int
    beacon_probability: float
    is_beacon: bool
    classifier_score: float
    model_name: str
    model_version: str
    inference_time_ms: float
    used_fallback: bool = False
    fallback_reason: Optional[str] = None


@dataclass(frozen=True)
class CandidateClassificationBatch:
    """
    Batch of classifications for all candidates in a frame.
    """

    frame_number: int
    classifications: List[CandidateClassification]


@dataclass(frozen=True)
class TrackObservation:
    """
    Bounded track observation element for prediction history.
    Does NOT contain image arrays or simulator ground truth.
    """

    timestamp: float
    x: Optional[float]
    y: Optional[float]
    measurement_valid: bool
    measurement_accepted: bool
    confidence: float
    state: str
    processing_latency_ms: float = 0.0


@dataclass(frozen=True)
class PredictionRequest:
    """
    Request object passed to temporal predictor.
    """

    frame_number: int
    timestamp: float
    history: Tuple[TrackObservation, ...]
    frame_width: int
    frame_height: int
    horizon_seconds: float
    current_roi: Optional[Tuple[int, int, int, int]] = None


@dataclass(frozen=True)
class PredictionResult:
    """
    Result object returned by temporal predictor.
    Predicted coordinates must be in image pixel coordinates.
    """

    frame_number: int
    timestamp: float
    predicted_x: float
    predicted_y: float
    predicted_vx: float
    predicted_vy: float
    uncertainty_x: float
    uncertainty_y: float
    confidence: float
    horizon_seconds: float
    model_name: str
    model_version: str
    used_fallback: bool = False
    fallback_reason: Optional[str] = None
    inference_time_ms: float = 0.0
