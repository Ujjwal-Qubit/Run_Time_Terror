import pytest
import numpy as np
from typing import Dict, Any

from src.api.v1 import (
    FramePacket, 
    TrackingResult, 
    ITrackingAlgorithm,
    API_VERSION
)

def test_api_version_exists():
    """Verify that the API exposes a version string."""
    assert API_VERSION == "v1"

class DummyAlgorithm(ITrackingAlgorithm):
    """A minimal dummy algorithm implementation strictly for testing the API contract."""
    def __init__(self):
        self.initialized = False
        self.reset_called = False

    def initialize(self, config: Dict[str, Any]) -> bool:
        self.initialized = True
        return config.get("success", True)

    def process_frame(self, frame_packet: FramePacket) -> TrackingResult:
        return TrackingResult(
            algorithm_is_tracking=True,
            centroid_x=10.0,
            centroid_y=20.0,
            confidence=0.9,
            roi=(0, 0, 100, 100)
        )

    def reset(self) -> None:
        self.reset_called = True

def test_dummy_algorithm_lifecycle():
    """Verify the ITrackingAlgorithm contract can be implemented and behaves correctly."""
    algo = DummyAlgorithm()
    
    assert algo.initialize({"success": True}) is True
    assert algo.initialized is True

    img = np.zeros((480, 640), dtype=np.uint8)
    packet = FramePacket(
        image=img,
        timestamp=0.0,
        frame_number=0,
        resolution=(640, 480),
        fov=(45.0, 35.0)
    )

    result = algo.process_frame(packet)
    assert isinstance(result, TrackingResult)
    assert result.algorithm_is_tracking is True
    assert result.centroid_x == 10.0

    algo.reset()
    assert algo.reset_called is True

def test_frame_packet_valid_construction():
    """Verify FramePacket can be constructed with valid parameters."""
    img = np.zeros((480, 640), dtype=np.uint8)
    fp = FramePacket(
        image=img,
        timestamp=1.5,
        frame_number=30,
        resolution=(640, 480),
        fov=None
    )
    assert fp.frame_number == 30
    assert fp.resolution == (640, 480)
    assert fp.fov is None

def test_frame_packet_invalid_construction():
    """Verify FramePacket validates its fields."""
    img = np.zeros((480, 640), dtype=np.uint8)
    
    with pytest.raises(TypeError):
        # Image must be np.ndarray
        FramePacket(image="not_an_image", timestamp=0.0, frame_number=0, resolution=(640, 480))
        
    with pytest.raises(ValueError):
        # Resolution must be a 2-tuple
        FramePacket(image=img, timestamp=0.0, frame_number=0, resolution=(640,))
        
    with pytest.raises(ValueError):
        # fov must be a 2-tuple if provided
        FramePacket(image=img, timestamp=0.0, frame_number=0, resolution=(640, 480), fov=(45.0,))
        
    with pytest.raises(ValueError):
        # Negative timestamp
        FramePacket(image=img, timestamp=-1.0, frame_number=0, resolution=(640, 480))
        
    with pytest.raises(ValueError):
        # Negative frame number
        FramePacket(image=img, timestamp=0.0, frame_number=-5, resolution=(640, 480))

def test_tracking_result_valid_construction():
    """Verify TrackingResult accepts valid tracking states."""
    res1 = TrackingResult(algorithm_is_tracking=False, centroid_x=None, centroid_y=None)
    assert res1.algorithm_is_tracking is False
    
    res2 = TrackingResult(
        algorithm_is_tracking=True, 
        centroid_x=320.5, 
        centroid_y=240.5, 
        confidence=0.8,
        roi=(0, 0, 50, 50)
    )
    assert res2.algorithm_is_tracking is True
    assert res2.centroid_x == 320.5

def test_tracking_result_invalid_construction():
    """Verify TrackingResult rejects invalid states."""
    with pytest.raises(TypeError):
        TrackingResult(algorithm_is_tracking="Yes", centroid_x=1.0, centroid_y=1.0)
        
    with pytest.raises(ValueError):
        # Infinite centroid when tracking
        TrackingResult(algorithm_is_tracking=True, centroid_x=np.inf, centroid_y=1.0)
        
    with pytest.raises(ValueError):
        # NaN centroid when tracking
        TrackingResult(algorithm_is_tracking=True, centroid_x=1.0, centroid_y=np.nan)
        
    with pytest.raises(ValueError):
        # Confidence out of bounds
        TrackingResult(algorithm_is_tracking=True, centroid_x=1.0, centroid_y=1.0, confidence=1.5)
        
    with pytest.raises(ValueError):
        # Negative ROI dimensions
        TrackingResult(algorithm_is_tracking=False, centroid_x=None, centroid_y=None, roi=(0, 0, -10, 50))

def test_architectural_firewall():
    """
    Contract-level test ensuring the API structs do not expose platform internals.
    The goal of this test is to verify that FramePacket doesn't contain a ground_truth reference
    or a 'source' enum that leaks if it's from SIMULATION or MP4.
    """
    img = np.zeros((10, 10), dtype=np.uint8)
    packet = FramePacket(image=img, timestamp=0.0, frame_number=0, resolution=(10, 10))
    
    # Assert that no accidental property exists
    assert not hasattr(packet, "ground_truth")
    assert not hasattr(packet, "source")
    assert not hasattr(packet, "target_manager")
    assert not hasattr(packet, "simulator_state")
