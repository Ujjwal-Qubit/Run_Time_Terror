"""
Frame domain — Module 8 and Data Contracts per Architecture v1.2.
"""

from src.frame.data_contracts import (
    TrackingState,
    MotionType,
    AtmosphericCondition,
    NoiseType,
    FrameSource,
    PlatformMotionType,
    FramePacket,
    GroundTruth,
    CandidateRegion,
    ScoredCandidate,
    CentroidResult,
    TrackResult,
    TrackingResult,
    StateDecision,
    TrackingStateResult,
    IdentificationResult,
    PTZCommand,
    ROI,
    TelemetryRecord,
    DetectionResult,
)

__all__ = [
    "TrackingState",
    "MotionType",
    "AtmosphericCondition",
    "NoiseType",
    "FrameSource",
    "PlatformMotionType",
    "FramePacket",
    "GroundTruth",
    "CandidateRegion",
    "ScoredCandidate",
    "CentroidResult",
    "TrackResult",
    "TrackingResult",
    "StateDecision",
    "TrackingStateResult",
    "IdentificationResult",
    "PTZCommand",
    "ROI",
    "TelemetryRecord",
    "DetectionResult",
    "SimulationFrameProvider",
    "MP4FrameProvider",
]


def __getattr__(name: str):
    if name == "SimulationFrameProvider":
        from src.frame.simulation_provider import SimulationFrameProvider
        return SimulationFrameProvider
    if name == "MP4FrameProvider":
        from src.frame.mp4_provider import MP4FrameProvider
        return MP4FrameProvider
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
