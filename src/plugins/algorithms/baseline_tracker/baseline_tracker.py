"""
Baseline Tracking Algorithm Plugin (Module 9, 10, 11, 12, 13 Encapsulation)

Implements the frozen Phase 6.1 ITrackingAlgorithm public API by wrapping the
validated tracking science:
  - Module 9:  P0ThresholdDetector
  - Module 10: IntensityWeightedCentroidEstimator
  - Module 11: CandidateIdentifier / AIClassifier
  - Module 12: ConstantVelocityKalmanTracker
  - Module 13: TrackingStateManager

FIREWALL ENFORCEMENT:
  Has ZERO access to GroundTruth, GroundTruthProvider, SimulatorState,
  SceneManager, TargetManager, CameraModel, DisturbanceEngine, MetricsEngine,
  or PTZController. Consumes only observable pixel data and public timestamps.
"""

from dataclasses import replace
import logging
from typing import Any, Dict, Optional, Tuple

from src.api.v1.algorithm import ITrackingAlgorithm
from src.api.v1.contracts import FramePacket as PublicFramePacket, TrackingResult as PublicTrackingResult
from src.config.config_manager import (
    CentroidConfig,
    DetectorConfig,
    IdentifierConfig,
    StateConfig,
    TrackerConfig,
)
from src.frame.data_contracts import (
    FramePacket as InternalFramePacket,
    FrameSource,
    ROI,
    TrackingState,
)
from src.tracker.ai_classifier import AIClassifier
from src.tracker.candidate_identifier import CandidateIdentifier
from src.tracker.centroid_estimator import IntensityWeightedCentroidEstimator
from src.tracker.detection_engine import P0ThresholdDetector
from src.tracker.state_manager import TrackingStateManager
from src.tracker.temporal_tracker import ConstantVelocityKalmanTracker

logger = logging.getLogger(__name__)


class BaselineTracker(ITrackingAlgorithm):
    """
    Official Platform Baseline Tracking Algorithm.
    
    Provides sub-pixel optical tracking of dynamic target beacons in degraded
    atmospheric, noisy, and dynamic platform environments.
    """

    def __init__(self) -> None:
        """
        Initialize the BaselineTracker with authoritative default configurations.
        Reuses existing configuration dataclasses directly without duplicating constants.
        """
        self._detector_cfg = DetectorConfig()
        self._centroid_cfg = CentroidConfig()
        self._identifier_cfg = IdentifierConfig()
        self._tracker_cfg = TrackerConfig()
        self._state_cfg = StateConfig()

        self._detector: Optional[P0ThresholdDetector] = None
        self._centroid_estimator: Optional[IntensityWeightedCentroidEstimator] = None
        self._identifier: Optional[CandidateIdentifier] = None
        self._tracker: Optional[ConstantVelocityKalmanTracker] = None
        self._state_manager: Optional[TrackingStateManager] = None

        self._use_ai_classifier: bool = True
        self._is_initialized: bool = False

        # Build pipeline with initial defaults
        self._instantiate_pipeline()

    def _instantiate_pipeline(self) -> None:
        """Instantiates or re-instantiates internal stages with current configurations."""
        self._detector = P0ThresholdDetector(self._detector_cfg)
        self._centroid_estimator = IntensityWeightedCentroidEstimator(self._centroid_cfg)
        
        if self._use_ai_classifier:
            try:
                self._identifier = AIClassifier(self._identifier_cfg)
            except Exception as e:
                logger.warning(f"Failed to load AIClassifier, falling back to rule-based CandidateIdentifier: {e}")
                self._identifier = CandidateIdentifier(self._identifier_cfg)
        else:
            self._identifier = CandidateIdentifier(self._identifier_cfg)

        self._tracker = ConstantVelocityKalmanTracker(self._tracker_cfg)
        self._state_manager = TrackingStateManager(self._state_cfg)
        self._is_initialized = True

    @property
    def current_state(self) -> TrackingState:
        """Returns internal state machine state for diagnostics."""
        if self._state_manager is not None:
            return self._state_manager.current_state
        return TrackingState.SEARCHING

    @property
    def is_locked(self) -> bool:
        """Returns True if the algorithm maintains stable tracking lock."""
        if self._state_manager is not None:
            return self._state_manager.is_locked
        return False

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Configures the tracking algorithm using configuration parameters.
        
        Adapts dictionary overrides into the authoritative internal configuration
        dataclasses without introducing duplicate constants or competing systems.
        
        Args:
            config: Optional configuration dictionary containing sub-section overrides:
                    'detector', 'centroid', 'identifier', 'tracker', 'state'.
                    
        Returns:
            bool: True if initialization succeeded, False otherwise.
        """
        if config is None:
            config = {}

        if not isinstance(config, dict):
            logger.error(f"Configuration must be a dictionary, got {type(config).__name__}")
            return False

        try:
            # Check for AI Classifier override
            if "use_ai_classifier" in config:
                self._use_ai_classifier = bool(config["use_ai_classifier"])

            # Adapt sub-dictionaries into dataclasses using field matching
            def _apply_overrides(cfg_obj: Any, overrides: Optional[Dict[str, Any]]) -> Any:
                if not overrides or not isinstance(overrides, dict):
                    return cfg_obj
                valid_fields = set(cfg_obj.__dataclass_fields__.keys())
                filtered_overrides = {}
                for k, v in overrides.items():
                    if k in valid_fields:
                        filtered_overrides[k] = v
                    else:
                        logger.warning(f"Ignoring unrecognized configuration field '{k}' for {type(cfg_obj).__name__}")
                return replace(cfg_obj, **filtered_overrides)

            self._detector_cfg = _apply_overrides(self._detector_cfg, config.get("detector"))
            self._centroid_cfg = _apply_overrides(self._centroid_cfg, config.get("centroid"))
            self._identifier_cfg = _apply_overrides(self._identifier_cfg, config.get("identifier"))
            self._tracker_cfg = _apply_overrides(self._tracker_cfg, config.get("tracker"))
            self._state_cfg = _apply_overrides(self._state_cfg, config.get("state"))

            # Re-instantiate internal stages with updated parameters
            self._instantiate_pipeline()
            self.reset()
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize BaselineTracker with provided configuration: {e}")
            return False

    def process_frame(self, frame_packet: PublicFramePacket) -> PublicTrackingResult:
        """
        Processes a single observable frame and returns the algorithm's subjective tracking result.
        
        Args:
            frame_packet: Authoritative PublicFramePacket (image, timestamp, frame_number, resolution).
            
        Returns:
            PublicTrackingResult (algorithm_is_tracking, centroid_x, centroid_y, confidence, roi).
        """
        if not isinstance(frame_packet, PublicFramePacket):
            raise TypeError(f"Expected PublicFramePacket, got {type(frame_packet).__name__}")

        width, height = frame_packet.resolution

        # 1. Adaptive ROI Computation (from temporal tracker prediction)
        roi: ROI = self._tracker.get_roi(width, height)

        # 2. Convert public contract to internal FramePacket for sub-module compatibility
        internal_packet = InternalFramePacket(
            image=frame_packet.image,
            width=width,
            height=height,
            frame_number=frame_packet.frame_number,
            timestamp=frame_packet.timestamp,
            source=FrameSource.SIMULATION
        )

        # 3. Stage 1: Detection
        detection_res = self._detector.detect(internal_packet, roi=roi)

        # 4. Stage 2: Candidate Identification
        pred_pos = self._tracker.predict() if self._tracker.is_initialized else None
        curr_state = self._state_manager.current_state
        ident_res = self._identifier.identify(
            detection_res.candidates,
            predicted_position=pred_pos,
            current_state=curr_state,
            frame_number=frame_packet.frame_number,
            timestamp=frame_packet.timestamp,
        )

        # 5. Stage 3: Centroid Refinement
        centroid_res = None
        if ident_res.valid and ident_res.selected_candidate is not None:
            centroid_res = self._centroid_estimator.estimate(
                internal_packet,
                ident_res.selected_candidate
            )

        # 6. Stage 4: Temporal Tracking Update (Kalman Filter)
        track_res = self._tracker.update(
            centroid_res,
            dt=0.0,
            frame_number=frame_packet.frame_number,
            timestamp=frame_packet.timestamp,
        )

        # 7. Stage 5: Tracking State Machine Update
        state_res = self._state_manager.update(
            track_res,
            timestamp=frame_packet.timestamp,
        )

        # 8. Output Mapping to Public Contract
        # Subjective tracking belief: True iff confirmed locked in TRACKING state
        is_tracking = (state_res.state == TrackingState.TRACKING)

        if is_tracking:
            if centroid_res is not None and centroid_res.valid:
                centroid_x = float(centroid_res.x)
                centroid_y = float(centroid_res.y)
            else:
                centroid_x = float(track_res.estimated_x)
                centroid_y = float(track_res.estimated_y)
            confidence = float(min(1.0, max(0.0, state_res.confidence_level)))
        else:
            centroid_x = None
            centroid_y = None
            confidence = float(min(1.0, max(0.0, state_res.confidence_level)))

        public_roi = (roi.x, roi.y, roi.width, roi.height) if roi is not None else None

        return PublicTrackingResult(
            algorithm_is_tracking=is_tracking,
            centroid_x=centroid_x,
            centroid_y=centroid_y,
            confidence=confidence,
            roi=public_roi,
        )

    def reset(self) -> None:
        """
        Clears all temporal state across all tracking stages.
        
        Resets Kalman filter state, covariances, track age, and state-machine
        counters/histories. Guarantees zero state leakage across scenario runs.
        """
        if self._tracker is not None:
            self._tracker.reset()
        if self._state_manager is not None:
            self._state_manager.reset()
