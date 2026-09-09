"""
Data contracts for the SIH 2026 FSOC Virtual Camera Tracking System.

These dataclasses define the shared data structures that flow between
the 19 production modules. They implement the contracts described in
Architecture v1.2 §3 (Data Contracts).

Ground truth contracts are consumed ONLY by MetricsEngine, LoggingEngine,
and VisualizationEngine — NEVER by the tracker pipeline.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TrackingState(enum.Enum):
    """
    Tracking state machine states per Architecture v1.2 §10.1.

    SEARCHING  → No track exists. Full-frame detection active.
    ACQUIRING  → Candidate found, not yet confirmed as stable lock.
    TRACKING   → Beacon locked. Centroiding and tracking active.
    LOST       → Track broken. Full-frame re-detection active.
    REACQUIRING → Candidate re-found after loss. Confirming re-lock.
    """
    SEARCHING = "SEARCHING"
    ACQUIRING = "ACQUIRING"
    TRACKING = "TRACKING"
    LOST = "LOST"
    REACQUIRING = "REACQUIRING"


class MotionType(enum.Enum):
    """Target motion patterns per PS Row 12."""
    STRAIGHT_LINE = "STRAIGHT_LINE"
    CIRCULAR = "CIRCULAR"
    FIGURE_8 = "FIGURE_8"
    RANDOM = "RANDOM"
    # Optional patterns (PS Row 12)
    SPIRAL = "SPIRAL"
    SINUSOIDAL = "SINUSOIDAL"
    USER_DEFINED = "USER_DEFINED"


class AtmosphericCondition(enum.Enum):
    """Atmospheric modes per PS Row 24."""
    CLEAR = "CLEAR"
    HAZE = "HAZE"
    FOG = "FOG"
    RAIN = "RAIN"
    LOW_LIGHT = "LOW_LIGHT"


class NoiseType(enum.Enum):
    """Noise types per PS Row 21."""
    SALT_AND_PEPPER = "SALT_AND_PEPPER"
    GAUSSIAN = "GAUSSIAN"
    POISSON = "POISSON"


class FrameSource(enum.Enum):
    """Source of the frame — used for FrameProvider firewall."""
    SIMULATION = "SIMULATION"
    MP4_FILE = "MP4_FILE"


class PlatformMotionType(enum.Enum):
    """Platform motion patterns per PS Row 25."""
    NONE = "NONE"
    LINEAR = "LINEAR"          # Mandatory
    CIRCULAR = "CIRCULAR"      # Optional
    RANDOM = "RANDOM"          # Optional
    SPIRAL = "SPIRAL"          # Optional
    FIGURE_8 = "FIGURE_8"     # Optional


# ---------------------------------------------------------------------------
# Core data contracts
# ---------------------------------------------------------------------------

@dataclass
class FramePacket:
    """
    The fundamental data contract between FrameProvider and the tracker
    pipeline. Per Architecture v1.2 §3.1.

    The tracker receives ONLY this — never simulator state or ground truth.
    """
    frame_number: int
    timestamp: float                   # seconds since simulation/video start
    image: object                      # numpy ndarray (H, W) uint8 monochrome
    width: int                         # frame width in pixels
    height: int                        # frame height in pixels
    source: FrameSource = FrameSource.SIMULATION


@dataclass
class GroundTruth:
    """
    Ground truth record for a single frame. Per Architecture v1.2 §12.1b.

    Consumed ONLY by MetricsEngine, LoggingEngine, VisualizationEngine.
    NEVER provided to Detector, Identifier, CentroidEstimator, Tracker,
    or PTZController.

    Distinguishes four position concepts:
      1. target_world_position   — true position in world/scene coordinates
      2. ideal_projected_position — mathematically perfect projection onto
                                    the image plane
      3. rendered_centroid        — actual intensity centroid of the rendered
                                    beacon on the pixel grid
      4. (estimated_centroid)     — produced by the tracker, NOT in this struct
    """
    frame_number: int
    timestamp: float
    target_world_x: float              # world/scene coordinates
    target_world_y: float
    ideal_projected_x: Optional[float] = None   # image coordinates
    ideal_projected_y: Optional[float] = None
    rendered_centroid_x: Optional[float] = None  # image coordinates
    rendered_centroid_y: Optional[float] = None
    target_visible: bool = True        # is the target within the camera FOV?
    camera_pan_deg: float = 0.0        # current camera pointing
    camera_tilt_deg: float = 0.0


@dataclass
class CandidateRegion:
    """
    A detected candidate region from candidate generation.
    Per Architecture v1.2 §8.2 Stage 2.
    """
    bbox_x: int                         # bounding box top-left x
    bbox_y: int                         # bounding box top-left y
    bbox_w: int                         # bounding box width
    bbox_h: int                         # bounding box height
    peak_intensity: float               # maximum intensity in region
    mean_intensity: float               # mean intensity in region
    area: int                           # pixel count
    local_contrast: float = 0.0         # beacon mean / local background mean
    compactness: float = 0.0            # area / bbox_area
    candidate_id: int = 0               # unique sequential candidate ID per frame
    raw_centroid_x: float = 0.0         # geometric center (candidate metadata only, NOT subpixel centroid)
    raw_centroid_y: float = 0.0         # geometric center (candidate metadata only)
    detection_score: float = 0.0        # detection confidence / score [0, 1]


@dataclass
class DetectionResult:
    """
    Output contract of DetectionEngine (Module 9).
    Per Architecture v1.2 §4 Module 9 and §8.2 Stage 2/3.

    Contains observed candidates and frame metadata.
    Does NOT contain ground truth or tracker state.
    """
    frame_number: int
    timestamp: float
    candidates: List[CandidateRegion] = field(default_factory=list)
    processing_time_ms: float = 0.0
    roi: Optional[ROI] = None



@dataclass
class ScoredCandidate:
    """
    A candidate scored by detection/classification.
    Per Architecture v1.2 §8.2 Stage 3.
    """
    candidate: CandidateRegion
    score: float                        # identification confidence [0, 1]
    is_beacon: bool = False             # final identification decision


@dataclass
class CentroidResult:
    """
    Result of centroid estimation. Per Architecture v1.2 §8.2 Stage 5.
    Sub-pixel coordinates — NOT rounded to integers.
    """
    x: float                            # sub-pixel centroid x
    y: float                            # sub-pixel centroid y
    quality: float = 1.0                # estimation quality [0, 1]
    valid: bool = True                  # whether estimation succeeded
    frame_number: int = 0               # source frame number
    timestamp: float = 0.0              # frame timestamp in seconds
    candidate_id: int = 0               # associated candidate ID
    total_signal: float = 0.0           # total positive signal weight sum(w_i)
    estimated_bg: float = 0.0           # estimated local background intensity
    roi_bbox: Optional[Tuple[int, int, int, int]] = None  # (x0, y0, w, h) ROI used
    processing_time_ms: float = 0.0     # centroid estimation latency in ms



@dataclass
class IdentificationResult:
    """
    Output contract of Candidate Identification (Module 11).
    Per Architecture v1.2 §8.2 Stage 4.
    """
    selected_candidate: Optional[CandidateRegion] = None
    selected_candidate_id: Optional[int] = None
    valid: bool = False
    confidence: float = 0.0
    all_scored_candidates: List[ScoredCandidate] = field(default_factory=list)
    centroid: Optional[CentroidResult] = None
    frame_number: int = 0
    timestamp: float = 0.0
    processing_time_ms: float = 0.0
    # Backward-compatibility duck typing for ScoredCandidate
    candidate: Optional[CandidateRegion] = None
    score: float = 0.0
    is_beacon: bool = False


@dataclass
class TrackResult:
    """
    Result from temporal tracking. Per Architecture v1.2 §8.2 Stage 6.
    """
    estimated_x: float                  # filtered/estimated position x
    estimated_y: float                  # filtered/estimated position y
    velocity_x: float = 0.0            # estimated velocity px/s
    velocity_y: float = 0.0
    confidence: float = 0.0            # track confidence [0, 1]
    track_age: int = 0                 # frames since track started
    predicted_x: float = 0.0           # predicted position for next frame
    predicted_y: float = 0.0
    frame_number: int = 0               # current frame number
    timestamp: float = 0.0              # current frame timestamp
    measurement_valid: bool = False     # whether an input measurement was provided
    measurement_accepted: bool = False  # whether measurement passed innovation gate
    innovation_x: float = 0.0           # residual in x (meas - pred)
    innovation_y: float = 0.0           # residual in y (meas - pred)
    innovation_distance: float = 0.0    # euclidean norm of innovation
    is_coasting: bool = False           # True if running prediction only without update
    status: str = "TRACKING"            # human-readable status string
    processing_time_ms: float = 0.0     # tracker execution latency


# Alias for contract equivalence
TrackingResult = TrackResult


@dataclass
class TrackingStateResult:
    """
    Output from tracking state manager stage.
    Per Architecture v1.2 §8.2 Stage 7 and §10.1.
    """
    state: TrackingState = TrackingState.SEARCHING
    previous_state: TrackingState = TrackingState.SEARCHING
    transition_reason: str = ""
    is_locked: bool = False             # true when in stable TRACKING/LOCKED state
    confidence_level: float = 0.0       # overall tracking confidence [0, 1]
    is_valid: bool = False              # is the current track valid
    acquisition_frames: int = 0         # consecutive valid frames during acquisition
    loss_frames: int = 0                # consecutive lost frames
    reacquisition_frames: int = 0       # consecutive reacquired frames
    time_in_state: float = 0.0          # time elapsed in current state (seconds)
    acquisition_timestamp: Optional[float] = None       # timestamp of first observation considered
    lock_timestamp: Optional[float] = None              # timestamp when TRACKING lock was confirmed
    acquisition_time: Optional[float] = None            # lock_timestamp - acquisition_timestamp
    loss_timestamp: Optional[float] = None              # timestamp when loss episode began
    reacquisition_timestamp: Optional[float] = None     # timestamp when re-lock was confirmed
    reacquisition_time: Optional[float] = None          # reacquisition_timestamp - loss_timestamp
    frame_number: int = 0
    timestamp: float = 0.0
    should_trigger_loss: bool = False   # should transition to LOST
    processing_time_ms: float = 0.0


# Backward compatibility alias
StateDecision = TrackingStateResult


@dataclass
class PTZCommand:
    """
    Pan/tilt command from the PTZ controller.
    Per Architecture v1.2 §11.1.
    """
    delta_pan_deg: float = 0.0          # pan displacement in degrees (integrated over dt)
    delta_tilt_deg: float = 0.0         # tilt displacement in degrees (integrated over dt)
    pan_velocity_deg_s: float = 0.0     # rate-limited pan angular velocity (deg/s)
    tilt_velocity_deg_s: float = 0.0    # rate-limited tilt angular velocity (deg/s)
    error_x_px: float = 0.0             # image-plane error x (px)
    error_y_px: float = 0.0             # image-plane error y (px)
    error_pan_deg: float = 0.0          # angular error pan (deg)
    error_tilt_deg: float = 0.0         # angular error tilt (deg)
    in_deadband: bool = False           # True only when both |err_x| <= d and |err_y| <= d
    is_saturated: bool = False          # True if rate limiting clamped either axis
    valid: bool = False                 # True if active control command was generated
    timestamp: float = 0.0              # command timestamp (seconds)
    frame_number: int = 0               # sequence frame number
    processing_time_ms: float = 0.0     # computation latency (ms)


@dataclass
class ROI:
    """
    Region of interest for adaptive ROI detection.
    """
    x: int = 0                          # top-left x
    y: int = 0                          # top-left y
    width: int = 0                      # ROI width
    height: int = 0                     # ROI height
    is_full_frame: bool = True          # whether this covers the entire frame


@dataclass
class TrackerOutput:
    """
    Complete output from one tracker pipeline invocation.
    Aggregates all per-frame tracker results for downstream consumption
    by MetricsEngine, LoggingEngine, and PTZController.
    """
    frame_number: int
    timestamp: float
    state: TrackingState
    previous_state: TrackingState
    transition_reason: str
    centroid: Optional[CentroidResult]
    track: Optional[TrackResult]
    detection_valid: bool
    candidate_count: int
    confidence: float
    roi: ROI
    processing_time_ms: float = 0.0


@dataclass
class TelemetryRecord:
    """
    Complete per-frame telemetry record for CSV/JSON logging.
    Combines tracker output with ground truth for post-hoc analysis.
    Per Architecture v1.2 §16.
    """
    run_id: str = ""
    frame_number: int = 0
    timestamp: float = 0.0
    source: str = ""
    state: str = ""
    previous_state: str = ""
    transition_reason: str = ""
    target_present: bool = False
    # Ground truth (metrics channel only)
    ground_truth_x: Optional[float] = None
    ground_truth_y: Optional[float] = None
    ideal_projected_x: Optional[float] = None
    ideal_projected_y: Optional[float] = None
    rendered_centroid_x: Optional[float] = None
    rendered_centroid_y: Optional[float] = None
    # Tracker estimates
    estimated_centroid_x: Optional[float] = None
    estimated_centroid_y: Optional[float] = None
    # Errors (computed by MetricsEngine)
    centroid_error_ideal: Optional[float] = None
    centroid_error_rendered: Optional[float] = None
    tracking_error: Optional[float] = None
    # Detection
    detection_confidence: float = 0.0
    candidate_count: int = 0
    detection_valid: bool = False
    # Camera / PTZ
    pan_angle: float = 0.0
    tilt_angle: float = 0.0
    pan_command: float = 0.0
    tilt_command: float = 0.0
    # Performance
    processing_time_ms: float = 0.0
    fps: float = 0.0
    # Enriched diagnostic fields (Phase 5.8)
    target_visible: bool = True
    centroid_valid: bool = False
    tracking_error_optical_axis: Optional[float] = None
    tracking_error_gt: Optional[float] = None
    is_coasting: bool = False
    ptz_pan_velocity: float = 0.0
    ptz_tilt_velocity: float = 0.0
    ptz_in_deadband: bool = False
    ptz_is_saturated: bool = False
    time_detection_ms: float = 0.0
    time_centroid_ms: float = 0.0
    time_tracking_ms: float = 0.0
    time_state_ms: float = 0.0
    time_ptz_ms: float = 0.0
    time_metrics_ms: float = 0.0


@dataclass
class MetricsSummary:
    """
    Aggregate metrics summary for a run. Per Stage 4 §7 and Architecture v1.2 §13.

    All metric definitions are PROVISIONAL — the PS does not fully
    define every metric. Definitions must remain replaceable.
    """
    run_id: str = ""
    total_frames: int = 0
    duration_seconds: float = 0.0
    # Detection
    detection_rate: float = 0.0
    false_positive_rate: float = 0.0
    mean_candidate_count: float = 0.0
    mean_detection_latency_ms: float = 0.0
    # Centroiding (PROVISIONAL definitions)
    mean_centroid_error: float = 0.0
    median_centroid_error: float = 0.0
    rmse_centroid: float = 0.0
    rmse_centroid_ideal: float = 0.0
    rmse_centroid_rendered: float = 0.0
    max_centroid_error: float = 0.0
    pct_within_1px: float = 0.0
    pct_within_2px: float = 0.0
    pct_within_5px: float = 0.0
    # Tracking
    mean_tracking_error: float = 0.0
    mean_tracking_error_optical_axis: float = 0.0
    mean_tracking_error_gt: float = 0.0
    max_tracking_error: float = 0.0
    max_tracking_error_optical_axis: float = 0.0
    max_tracking_error_gt: float = 0.0
    rmse_tracking_optical_axis: float = 0.0
    rmse_tracking_gt: float = 0.0
    lock_retention_rate: float = 0.0
    lock_retention_post_acq_pct: float = 0.0
    lock_retention_all_pct: float = 0.0
    lock_retention_visible_pct: float = 0.0
    target_loss_rate: float = 0.0
    track_continuity: float = 0.0
    # Acquisition
    acquisition_time_s: Optional[float] = None
    acquisition_time_from_detect_s: Optional[float] = None
    acquisition_time_total_s: Optional[float] = None
    reacquisition_events: int = 0
    mean_reacquisition_time_s: Optional[float] = None
    max_reacquisition_time_s: Optional[float] = None
    # Counts
    frames_evaluated_count: int = 0
    frames_tracked_count: int = 0
    frames_lost_count: int = 0
    # Performance
    mean_fps: float = 0.0
    mean_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    # PTZ
    mean_steady_state_error: float = 0.0
    oscillation_measure: float = 0.0
    frames_in_deadband_pct: float = 0.0


@dataclass
class BatchRunItem:
    """Individual run outcome within a batch evaluation."""
    item_id: str                          # scenario name or mp4 filename
    source_path: str                      # full path or relative path
    success: bool = True
    error_message: Optional[str] = None
    summary: Optional[MetricsSummary] = None


@dataclass
class GrandEvaluationSummary:
    """
    Aggregated evaluator scorecard across a batch of scenarios or MP4 sequences.
    Per Architecture v1.2 §17 and Module 17 specifications.
    """
    batch_id: str = ""
    batch_type: str = "SCENARIOS"          # "SCENARIOS" or "MP4"
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    run_items: List[BatchRunItem] = field(default_factory=list)
    # Aggregated Macro Metrics (averaged across successful runs)
    mean_fps: float = 0.0
    mean_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    mean_acquisition_time_s: Optional[float] = None
    mean_rmse_centroid: float = 0.0
    mean_rmse_centroid_rendered: float = 0.0
    mean_tracking_error: float = 0.0
    mean_lock_retention_pct: float = 0.0
    mean_target_loss_rate_pct: float = 0.0
    total_frames_processed: int = 0
    total_duration_s: float = 0.0
    # PS 26169 Compliance Flags
    passed_fps_spec: bool = True          # >= 20 FPS
    passed_acquisition_spec: bool = True  # <= 2.0 s
    passed_tracking_error_spec: bool = True # <= 10.0 px
    passed_loss_rate_spec: bool = True    # < 5.0 %
    overall_compliance: bool = True
    timestamp: float = 0.0


@dataclass
class VisualizationState:
    """
    Contract for data sent from the backend to the frontend renderers (2D and future 3D).
    Contains only what is necessary for visualization, separating tracking state
    from simulator internals per Phase 5.10 design.
    """
    frame_number: int
    timestamp: float
    
    # Camera Pose / Telemetry
    pan_angle_deg: float
    tilt_angle_deg: float
    camera_fov: float
    
    # Visualization Frame
    display_image: object  # Reference to np.ndarray for GUI
    
    # Tracking Overlays
    estimated_centroid_x: Optional[float] = None
    estimated_centroid_y: Optional[float] = None
    tracking_state: str = "SEARCHING"
    tracking_error_px: Optional[float] = None
    roi: Optional[ROI] = None
    
    # Dashboard Telemetry
    processing_latency_ms: float = 0.0
    fps: float = 0.0
    
    # Visualization-only Truth (Debug Mode)
    ground_truth_x: Optional[float] = None
    ground_truth_y: Optional[float] = None
