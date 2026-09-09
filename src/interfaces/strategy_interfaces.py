"""
Strategy interfaces for the SIH 2026 FSOC tracking pipeline.

These abstract base classes define the replaceable algorithm contracts
per Architecture v1.2 §8.2 (pipeline stages) and §9.3 (strategy pattern).

Each interface corresponds to one pipeline stage. Concrete implementations
are selected via configuration — never hard-coded.

Production modules using these interfaces:
  - DetectionEngine (Module 9)   → IDetector
  - CentroidEstimator (Module 10) → ICentroidEstimator
  - TrackingEngine (Module 11)   → ITracker
  - PTZController (Module 13)    → IPTZController
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from src.frame.data_contracts import (
    FramePacket,
    CandidateRegion,
    ScoredCandidate,
    CentroidResult,
    TrackResult,
    PTZCommand,
    TrackingState,
    ROI,
    DetectionResult,
    TrackingStateResult,
    GroundTruth,
    TelemetryRecord,
    MetricsSummary,
)


class IPreprocessor(ABC):
    """
    Strategy interface for preprocessing stage.
    Architecture v1.2 §8.2 Stage 1.

    Responsibility: Prepare the raw frame for detection.
    Latency target: <1ms.
    """

    @abstractmethod
    def preprocess(self, image: object, roi: Optional[ROI] = None) -> object:
        """
        Preprocess the input image (or ROI sub-image).

        Args:
            image: numpy ndarray (H, W) uint8 monochrome.
            roi: Optional region of interest. If None, process full frame.

        Returns:
            Preprocessed image (same or smaller resolution).
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Return human-readable name for logging/reporting."""
        ...


class ICandidateGenerator(ABC):
    """
    Strategy interface for candidate generation stage.
    Architecture v1.2 §8.2 Stage 2.

    Responsibility: Identify bright regions that could potentially be
    the beacon. Fast, high-recall, low-precision filtering.
    Latency target: <3ms.
    """

    @abstractmethod
    def generate_candidates(
        self,
        preprocessed_image: object,
        roi: Optional[ROI] = None,
    ) -> List[CandidateRegion]:
        """
        Generate candidate regions from the preprocessed image.

        Args:
            preprocessed_image: Output from preprocessor.
            roi: If not full-frame, candidates are in ROI-local coordinates.

        Returns:
            List of candidate regions. Empty list if none found.
        """
        ...

    @abstractmethod
    def configure(self, **params) -> None:
        """Update detection parameters dynamically."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        ...


class IDetector(ABC):
    """
    Strategy interface for detection engine stage.
    Architecture v1.2 §4 Module 9 and §8.2.

    Responsibility: Given a FramePacket (and optional ROI), detect candidate regions,
    estimate local background, and produce a DetectionResult containing CandidateRegion
    detections suitable for downstream centroiding and tracking.
    Latency target: <8ms.
    """

    @abstractmethod
    def detect(
        self,
        packet: FramePacket,
        roi: Optional[ROI] = None,
    ) -> DetectionResult:
        """
        Detect candidate beacon regions in the input frame packet.

        Args:
            packet: FramePacket containing observed image and frame metadata.
            roi: Optional region of interest to restrict detection.

        Returns:
            DetectionResult with candidate list, frame number, timestamp, and metadata.
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Return human-readable detector algorithm name."""
        ...



class IBeaconIdentifier(ABC):
    """
    Strategy interface for beacon identification stage.
    Architecture v1.2 §8.2 Stage 4.

    Responsibility: Select the best candidate as the beacon. Reject
    false positives using spatial, temporal, and appearance consistency.
    Latency target: <1ms.
    """

    @abstractmethod
    def identify(
        self,
        scored_candidates: List[ScoredCandidate],
        predicted_position: Optional[Tuple[float, float]],
        current_state: TrackingState,
    ) -> Optional[ScoredCandidate]:
        """
        Identify the beacon among scored candidates.

        Args:
            scored_candidates: From detection stage.
            predicted_position: (x, y) from temporal tracker, if available.
            current_state: Current tracking state.

        Returns:
            The identified beacon candidate, or None if no valid beacon.
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        ...


class ICentroidEstimator(ABC):
    """
    Strategy interface for centroid estimation stage.
    Architecture v1.2 §8.2 Stage 5.

    Responsibility: Refine the detected candidate region to sub-pixel
    accuracy using Intensity-Weighted Centroiding (IWC).
    Latency target: <2ms.
    """

    @abstractmethod
    def estimate(
        self,
        frame: object,
        candidate: object,
    ) -> CentroidResult:
        """
        Estimate sub-pixel centroid of the beacon candidate.

        Args:
            frame: FramePacket or 2D numpy array containing observed image.
            candidate: CandidateRegion or ScoredCandidate with bounding box.

        Returns:
            CentroidResult with sub-pixel (x, y) coordinates.
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Return human-readable centroiding algorithm name."""
        ...



class ITracker(ABC):
    """
    Strategy interface for temporal tracking stage.
    Architecture v1.2 §8.2 Stage 6.

    Responsibility: Associate current detection with previous track.
    Predict next position. Maintain track continuity. Update ROI.
    Latency target: <1ms.
    """

    @abstractmethod
    def update(
        self,
        centroid: Optional[CentroidResult],
        dt: float,
    ) -> TrackResult:
        """
        Update the track with a new centroid measurement (or None if
        no detection this frame).

        Args:
            centroid: New centroid measurement, or None if no detection.
            dt: Time step in seconds since last update.

        Returns:
            TrackResult with estimated position, velocity, prediction.
        """
        ...

    @abstractmethod
    def predict(self) -> Tuple[float, float]:
        """
        Return the predicted position for the next frame.
        Used for ROI centering and candidate gating.
        """
        ...

    @abstractmethod
    def get_roi(self, frame_width: int, frame_height: int) -> ROI:
        """
        Compute the adaptive ROI for the next frame.
        Falls back to full-frame during SEARCHING/REACQUIRING.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset tracker state (e.g., on simulation restart)."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        ...


class ITrackingStateManager(ABC):
    """
    Strategy interface for tracking state management stage.
    Architecture v1.2 §8.2 Stage 7 and §10.1.

    Responsibility: Manage tracking state transitions (SEARCHING, ACQUIRING,
    TRACKING, REACQUIRING, LOST), record transition timestamps, and apply hysteresis.
    Latency target: <0.1ms.
    """

    @abstractmethod
    def update(
        self,
        track_result: Optional[TrackResult],
        timestamp: float = 0.0,
    ) -> TrackingStateResult:
        """
        Update state machine based on the current tracking result.

        Args:
            track_result: Current TrackResult from temporal tracker.
            timestamp: Current frame timestamp in seconds.

        Returns:
            TrackingStateResult with current state, lock status, and counters.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset state machine to initial SEARCHING state."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        ...


class IPTZController(ABC):
    """
    Strategy interface for PTZ control.
    Architecture v1.2 §11.1.

    Responsibility: Compute PTZ command from tracker output.
    The controller consumes ProjectionModel via CameraModel for
    pixel-to-angle conversion.
    """

    @abstractmethod
    def compute(
        self,
        track_result: Optional[TrackResult],
        tracking_state: TrackingState,
        frame_width: int,
        frame_height: int,
        dt: float,
    ) -> PTZCommand:
        """
        Compute pan/tilt command.

        Args:
            track_result: Current track result (None if no track).
            tracking_state: Current state machine state.
            frame_width: Frame width for image center calculation.
            frame_height: Frame height for image center calculation.
            dt: Time step in seconds.

        Returns:
            PTZCommand with delta_pan_deg and delta_tilt_deg.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset controller state."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        ...


class IFrameProvider(ABC):
    """
    FrameProvider firewall interface.
    Architecture v1.2 §6.

    The tracker pipeline consumes frames ONLY through this interface.
    It must not know whether the frame came from the simulator or an MP4.
    """

    @property
    @abstractmethod
    def fps(self) -> float:
        """Nominal source update rate in Hz / frames per second."""
        ...

    @property
    @abstractmethod
    def resolution(self) -> Tuple[int, int]:
        """Source image dimensions as (width, height) in pixels."""
        ...

    @abstractmethod
    def get_next_frame(self) -> Optional[FramePacket]:
        """
        Return the next frame, or None if the source is exhausted.
        The returned FramePacket is immutable (read-only image array).
        """
        ...

    @abstractmethod
    def is_exhausted(self) -> bool:
        """Return True if no more frames are available."""
        ...

    @abstractmethod
    def get_source_type(self) -> str:
        """Return 'SIMULATION' or 'MP4_FILE'."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset to the beginning of the source."""
        ...

    def close(self) -> None:
        """Release underlying source resources (e.g., video decoder)."""
        pass

    def __enter__(self) -> IFrameProvider:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()


class IMetricsEngine(ABC):
    """
    Strategy interface for Metrics Engine (Module 15).
    Architecture v1.2 §13.1.

    Responsibilities:
      - Compute running spatial accuracy (centroiding error, tracking error, RMSE)
      - Track operational timing (acquisition time, reacquisition time episodes)
      - Track retention metrics (lock retention rate, target loss rate)
      - Measure processing latency and frame rate
      - Produce per-frame TelemetryRecord and end-of-run MetricsSummary
    """

    @abstractmethod
    def update(
        self,
        frame_packet: FramePacket,
        track_result: Optional[TrackResult],
        state_result: TrackingStateResult,
        centroid_result: Optional[CentroidResult] = None,
        detection_result: Optional[DetectionResult] = None,
        ptz_command: Optional[PTZCommand] = None,
        ground_truth: Optional[GroundTruth] = None,
        camera_pan_deg: float = 0.0,
        camera_tilt_deg: float = 0.0,
        processing_time_ms: float = 0.0,
    ) -> TelemetryRecord:
        """
        Record a processed frame, compute errors and running metrics,
        and return the comprehensive per-frame TelemetryRecord.
        """
        ...

    @abstractmethod
    def get_current_summary(self) -> MetricsSummary:
        """Return running aggregate metrics up to the current frame."""
        ...

    @abstractmethod
    def finalize(self) -> MetricsSummary:
        """Compute final aggregate statistics for the completed run."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset all metric accumulators, episodes, and running state."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Return human-readable algorithm/engine name."""
        ...

