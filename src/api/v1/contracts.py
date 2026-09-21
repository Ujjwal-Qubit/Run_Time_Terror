"""
Platform Algorithm API Contracts (v1)

This module defines the authoritative data contracts for external algorithms
evaluating under the SIH '26 Algorithm Evaluation Platform.

These contracts are strictly isolated from internal simulator state and ground truth.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np

@dataclass
class FramePacket:
    """
    The fundamental data contract provided by the Platform to the Algorithm.

    Represents a single observable frame. It must NOT contain ground-truth
    channels or side-channel information.
    """
    image: np.ndarray
    timestamp: float
    frame_number: int
    resolution: Tuple[int, int]
    fov: Optional[Tuple[float, float]] = None

    def __post_init__(self):
        if not isinstance(self.image, np.ndarray):
            raise TypeError(f"image must be a numpy.ndarray, got {type(self.image)}")
        if len(self.resolution) != 2:
            raise ValueError(f"resolution must be a 2-tuple (width, height), got {self.resolution}")
        if self.fov is not None and len(self.fov) != 2:
            raise ValueError(f"fov must be a 2-tuple (horizontal, vertical) if provided, got {self.fov}")
        if self.frame_number < 0:
            raise ValueError(f"frame_number must be non-negative, got {self.frame_number}")
        if self.timestamp < 0.0:
            raise ValueError(f"timestamp must be non-negative, got {self.timestamp}")


@dataclass
class TrackingResult:
    """
    The authoritative output contract produced by an Algorithm.

    Represents the algorithm's SUBJECTIVE belief about the target.
    It does not indicate objective lock.
    
    Coordinate System: Image Pixel Coordinates (IPC)
    - Origin (0,0): Top-left
    - X: Increases to the right
    - Y: Increases downward
    """
    algorithm_is_tracking: bool
    centroid_x: Optional[float]
    centroid_y: Optional[float]
    confidence: Optional[float] = None
    roi: Optional[Tuple[int, int, int, int]] = None

    def __post_init__(self):
        if not isinstance(self.algorithm_is_tracking, bool):
            raise TypeError("algorithm_is_tracking must be a boolean.")
        
        # Validation for centroids when tracking
        if self.algorithm_is_tracking:
            if self.centroid_x is not None and not np.isfinite(self.centroid_x):
                raise ValueError("centroid_x must be finite when provided.")
            if self.centroid_y is not None and not np.isfinite(self.centroid_y):
                raise ValueError("centroid_y must be finite when provided.")
            
        # Confidence bounds
        if self.confidence is not None:
            if not (0.0 <= self.confidence <= 1.0):
                raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")

        # ROI validation
        if self.roi is not None:
            if len(self.roi) != 4:
                raise ValueError(f"roi must be a 4-tuple (x, y, w, h), got {self.roi}")
            _, _, w, h = self.roi
            if w < 0 or h < 0:
                raise ValueError(f"roi width and height must be non-negative, got w={w}, h={h}")
