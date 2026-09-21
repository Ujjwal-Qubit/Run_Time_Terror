"""
Platform Algorithm API v1

This package exposes the authoritative boundary between the Platform and 
external tracking algorithm plugins. 

Plugins must ONLY import from this package, never from platform internals.
"""

from .contracts import FramePacket, TrackingResult
from .algorithm import ITrackingAlgorithm

API_VERSION = "v1"

__all__ = [
    "FramePacket",
    "TrackingResult",
    "ITrackingAlgorithm",
    "API_VERSION"
]
