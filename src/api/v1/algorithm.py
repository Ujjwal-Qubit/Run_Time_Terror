"""
Platform Algorithm API (v1)

Defines the core ITrackingAlgorithm interface that external algorithm plugins
must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from .contracts import FramePacket, TrackingResult

class ITrackingAlgorithm(ABC):
    """
    The authoritative interface for external algorithm plugins.
    
    Algorithms must implement this interface to be evaluated by the 
    SIH '26 Algorithm Evaluation Platform.
    """

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Called before the scenario starts to initialize the algorithm.
        
        Args:
            config: A dictionary containing algorithm-specific configuration parameters.
                    These parameters are defined by the algorithm's manifest and supplied
                    by the platform configuration.
                    
        Returns:
            bool: True if initialization succeeded, False otherwise.
        """
        pass

    @abstractmethod
    def process_frame(self, frame_packet: FramePacket) -> TrackingResult:
        """
        The only per-frame execution entry point.
        
        Args:
            frame_packet: The current frame and its observable metadata.
                          Contains no hidden ground-truth or simulator state.
                          
        Returns:
            TrackingResult: The algorithm's subjective evaluation of the target's
                            state (is tracking, centroid, confidence, etc).
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Clears all algorithm-owned temporal state.
        
        This is called by the platform to signal that a new scenario is beginning,
        or that previous context should be discarded (e.g. after a hard target loss
        where memory must be flushed).
        
        Algorithms must clear temporal buffers, Kalman filter states, and learned
        background context here.
        """
        pass
