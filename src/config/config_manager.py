"""
Configuration Manager — Module 2 per Architecture v1.2 §4.

Centralizes all runtime configuration. Parameters are loaded from
defaults, then optionally overridden by scenario files or GUI input.

No parameter is scattered across source files — everything flows
through this manager.

Multi-beacon extension (backward-compatible):
  Old scenario format (still works):
    { "target": { "count": 1, "size": 10, "intensity": 220 } }
  New optional format:
    { "beacons": [{"role":"primary", ...}, {"role":"secondary", ...}] }
  from_dict() normalizes old format → beacons list automatically.
"""

from __future__ import annotations

import json
import copy
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

from src.config import defaults
from src.frame.data_contracts import (
    MotionType,
    AtmosphericCondition,
    NoiseType,
    PlatformMotionType,
)


@dataclass
class SceneConfig:
    """Scene / virtual environment configuration."""
    width: int = defaults.SCENE_DEFAULT_WIDTH
    height: int = defaults.SCENE_DEFAULT_HEIGHT
    background_intensity: int = defaults.SCENE_BACKGROUND_INTENSITY


@dataclass
class CameraConfig:
    """Virtual camera configuration."""
    width: int = defaults.CAMERA_DEFAULT_WIDTH
    height: int = defaults.CAMERA_DEFAULT_HEIGHT
    fov_h_deg: float = defaults.CAMERA_DEFAULT_FOV_H_DEG
    fov_v_deg: float = defaults.CAMERA_DEFAULT_FOV_V_DEG
    update_rate_hz: int = defaults.CAMERA_DEFAULT_UPDATE_RATE_HZ
    # Initial position — None means center of scene (computed at runtime)
    initial_x: Optional[float] = defaults.CAMERA_INITIAL_X
    initial_y: Optional[float] = defaults.CAMERA_INITIAL_Y


@dataclass
class TargetConfig:
    """Beacon target configuration."""
    count: int = defaults.TARGET_COUNT
    size: int = defaults.TARGET_DEFAULT_SIZE
    shape: str = defaults.TARGET_DEFAULT_SHAPE
    intensity: int = defaults.TARGET_DEFAULT_INTENSITY
    initial_position: str = defaults.TARGET_DEFAULT_INITIAL_POSITION
    initial_x: Optional[float] = None   # if initial_position != "random"
    initial_y: Optional[float] = None
    speed: float = defaults.TARGET_DEFAULT_SPEED


@dataclass
class MotionConfig:
    """Target motion configuration."""
    motion_type: str = MotionType.STRAIGHT_LINE.value
    circle_radius: float = defaults.MOTION_CIRCLE_RADIUS
    figure8_radius_x: float = defaults.MOTION_FIGURE8_RADIUS_X
    figure8_radius_y: float = defaults.MOTION_FIGURE8_RADIUS_Y
    random_max_displacement: float = defaults.MOTION_RANDOM_MAX_DISPLACEMENT
    # Direction for straight line (angle in degrees, 0 = right)
    straight_line_angle_deg: float = 45.0
    # Optional parameters for extended/AI-assisted trajectories
    spiral_r0: float = 30.0
    spiral_expansion_rate: float = 8.0
    sinusoidal_amplitude: float = 80.0
    sinusoidal_frequency: float = 0.3
    polygon_sides: int = 4
    polygon_radius: float = 180.0
    zigzag_width: float = 400.0
    zigzag_height: float = 200.0
    is_ai_generated: bool = False
    ai_prompt: Optional[str] = None


@dataclass
class PTZConfig:
    """Pan/tilt controller configuration."""
    max_pan_speed_deg_s: float = defaults.PTZ_DEFAULT_PAN_SPEED_DEG_S
    max_tilt_speed_deg_s: float = defaults.PTZ_DEFAULT_TILT_SPEED_DEG_S
    update_rate_hz: int = defaults.PTZ_DEFAULT_UPDATE_RATE_HZ
    proportional_gain: float = defaults.PTZ_DEFAULT_PROPORTIONAL_GAIN
    deadband_px: float = defaults.PTZ_DEFAULT_DEADBAND_PX
    integral_gain: float = defaults.PTZ_DEFAULT_INTEGRAL_GAIN


@dataclass
class NoiseConfig:
    """Noise configuration."""
    # Salt & Pepper
    sp_enabled: bool = False
    sp_density: float = defaults.NOISE_SP_DEFAULT_DENSITY
    # Gaussian
    gaussian_enabled: bool = False
    gaussian_sigma: float = defaults.NOISE_GAUSSIAN_DEFAULT_SIGMA
    # Poisson
    poisson_enabled: bool = defaults.NOISE_POISSON_ENABLED
    # Poisson exposure scale: multiplier applied to pixel intensities before
    # drawing Poisson samples. 1.0 = standard. Lower = noisier (underexposure).
    poisson_scale: float = defaults.NOISE_POISSON_SCALE


@dataclass
class AtmosphericConfig:
    """Atmospheric condition configuration."""
    condition: str = defaults.ATMOS_DEFAULT_CONDITION
    # Allow user override of contrast/brightness factors
    contrast_factor: Optional[float] = None   # None = use default for condition
    brightness_offset: Optional[int] = None


@dataclass
class JitterConfig:
    """Camera jitter configuration."""
    enabled: bool = defaults.JITTER_ENABLED
    max_px_per_frame: float = defaults.JITTER_DEFAULT_PX_PER_FRAME


@dataclass
class PlatformMotionConfig:
    """Platform motion configuration."""
    enabled: bool = defaults.PLATFORM_MOTION_ENABLED
    motion_type: str = defaults.PLATFORM_MOTION_MANDATORY_TYPE
    max_px_per_frame: float = defaults.PLATFORM_MOTION_DEFAULT_PX_PER_FRAME


@dataclass
class DetectorConfig:
    """Detection pipeline configuration."""
    bg_kernel_size: int = defaults.DETECTOR_BG_KERNEL_SIZE
    threshold_multiplier: float = defaults.DETECTOR_THRESHOLD_MULTIPLIER
    threshold_offset: int = defaults.DETECTOR_THRESHOLD_OFFSET
    min_candidate_area: int = defaults.DETECTOR_MIN_CANDIDATE_AREA
    max_candidate_area: int = defaults.DETECTOR_MAX_CANDIDATE_AREA
    min_candidate_intensity: int = defaults.DETECTOR_MIN_CANDIDATE_INTENSITY
    median_kernel_size: int = defaults.DETECTOR_MEDIAN_KERNEL_SIZE
    min_local_contrast: float = defaults.DETECTOR_MIN_LOCAL_CONTRAST



@dataclass
class IdentifierConfig:
    """Beacon identification configuration."""
    intensity_weight: float = defaults.IDENTIFIER_INTENSITY_WEIGHT
    size_weight: float = defaults.IDENTIFIER_SIZE_WEIGHT
    contrast_weight: float = defaults.IDENTIFIER_CONTRAST_WEIGHT
    proximity_weight: float = defaults.IDENTIFIER_PROXIMITY_WEIGHT
    expected_beacon_size: int = defaults.TARGET_DEFAULT_SIZE
    min_confidence: float = defaults.IDENTIFIER_MIN_CONFIDENCE
    # Hysteresis anti-switching: challenger must beat current track by
    # switch_score_margin for switch_confirmation_frames consecutive frames.
    switch_score_margin: float = defaults.IDENTIFIER_SWITCH_SCORE_MARGIN
    switch_confirmation_frames: int = defaults.IDENTIFIER_SWITCH_CONFIRMATION_FRAMES


@dataclass
class BeaconConfig:
    """
    Configuration for a single synthetic optical beacon.

    Used in the multi-beacon scenario format (additive, backward-compatible).
    The primary beacon (role="primary") is the intended tracking target.
    Secondary beacons (role="secondary") are realistic distractor/clutter targets.

    Constraint: secondary intensity must be < primary intensity - margin.
    """
    beacon_id: str = "primary"
    role: str = "primary"           # "primary" or "secondary"
    x: Optional[float] = None       # World X coordinate (None = scene center)
    y: Optional[float] = None       # World Y coordinate (None = scene center)
    size: int = defaults.TARGET_DEFAULT_SIZE
    shape: str = defaults.TARGET_DEFAULT_SHAPE
    intensity: int = defaults.TARGET_DEFAULT_INTENSITY
    speed: float = defaults.TARGET_DEFAULT_SPEED
    motion_type: Optional[str] = None  # None = inherit from MotionConfig


@dataclass
class LocalContrastConfig:
    """
    Local contrast / background clutter disturbance configuration.

    Adds a spatially-varying background perturbation (Gaussian blobs at
    random positions) to the rendered frame, inserted between the atmospheric
    stage and Poisson noise. This simulates local illumination variation,
    surface reflections, or cluttered optical background without reducing
    the beacon signal itself.

    Validation: beacon peak must remain at least min_beacon_margin above
    the peak local clutter amplitude.
    """
    enabled: bool = defaults.LOCAL_CONTRAST_ENABLED
    amplitude: float = defaults.LOCAL_CONTRAST_AMPLITUDE
    spatial_scale: float = defaults.LOCAL_CONTRAST_SPATIAL_SCALE
    num_blobs: int = defaults.LOCAL_CONTRAST_NUM_BLOBS
    min_beacon_margin: float = defaults.LOCAL_CONTRAST_MIN_BEACON_MARGIN


@dataclass
class CentroidConfig:
    """Centroid estimation configuration."""
    bg_margin: int = defaults.CENTROID_BG_MARGIN
    min_signal_weight: float = defaults.CENTROID_MIN_SIGNAL_WEIGHT
    bg_method: str = defaults.CENTROID_BG_METHOD



@dataclass
class TrackerConfig:
    """Temporal tracker configuration."""
    process_noise_pos: float = defaults.KALMAN_PROCESS_NOISE_POS
    process_noise_vel: float = defaults.KALMAN_PROCESS_NOISE_VEL
    measurement_noise: float = defaults.KALMAN_MEASUREMENT_NOISE
    initial_covariance_pos: float = defaults.KALMAN_INITIAL_COVARIANCE_POS
    initial_covariance_vel: float = defaults.KALMAN_INITIAL_COVARIANCE_VEL
    roi_min_size: int = defaults.ROI_MIN_SIZE
    roi_max_size: int = defaults.ROI_MAX_SIZE
    roi_margin_factor: float = defaults.ROI_MARGIN_FACTOR
    gate_max_distance: float = defaults.GATE_MAX_DISTANCE


@dataclass
class StateConfig:
    """Tracking state machine configuration."""
    lock_threshold: float = defaults.STATE_LOCK_THRESHOLD
    loss_threshold: float = defaults.STATE_LOSS_THRESHOLD
    lock_confirm_frames: int = defaults.STATE_LOCK_CONFIRM_FRAMES
    loss_confirm_frames: int = defaults.STATE_LOSS_CONFIRM_FRAMES
    reacquire_confirm_frames: int = defaults.STATE_REACQUIRE_CONFIRM_FRAMES


@dataclass
class AIMLConfig:
    """Optional learned candidate classification configuration."""
    candidate_classifier_enabled: bool = False
    candidate_model_dir: str = "models/candidate_classifier/v001"
    temporal_predictor_enabled: bool = False
    temporal_model_dir: str = "models/temporal_predictor/v001"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    csv_enabled: bool = defaults.LOG_CSV_ENABLED
    json_summary_enabled: bool = defaults.LOG_JSON_SUMMARY_ENABLED
    output_dir: str = defaults.LOG_OUTPUT_DIR


@dataclass
class SimulationConfig:
    """Simulation execution configuration."""
    duration_s: float = defaults.SIM_DEFAULT_DURATION_S
    random_seed: int = defaults.SIM_DEFAULT_RANDOM_SEED
    mode: str = "SIMULATION"            # "SIMULATION" or "MP4"
    mp4_path: Optional[str] = None      # path for MP4 mode


@dataclass
class SystemConfig:
    """
    Top-level system configuration aggregating all sub-configurations.
    This is the single authoritative configuration object passed to
    AppController (Module 1) at startup.

    Multi-beacon: the optional `beacons` list supersedes `target` when present.
    Use ConfigManager.from_dict() which automatically normalizes old scenario
    files (single-target format) into the beacons list.
    """
    scene: SceneConfig = field(default_factory=SceneConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    target: TargetConfig = field(default_factory=TargetConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    ptz: PTZConfig = field(default_factory=PTZConfig)
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    atmospheric: AtmosphericConfig = field(default_factory=AtmosphericConfig)
    jitter: JitterConfig = field(default_factory=JitterConfig)
    platform_motion: PlatformMotionConfig = field(
        default_factory=PlatformMotionConfig
    )
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    identifier: IdentifierConfig = field(default_factory=IdentifierConfig)
    centroid: CentroidConfig = field(default_factory=CentroidConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    state: StateConfig = field(default_factory=StateConfig)
    aiml: AIMLConfig = field(default_factory=AIMLConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    # Multi-beacon list (optional). Empty = use legacy single-target config.
    # Populated by from_dict() normalization or direct GUI/scenario assignment.
    beacons: List[BeaconConfig] = field(default_factory=list)
    # Local contrast disturbance (new, optional)
    local_contrast: LocalContrastConfig = field(default_factory=LocalContrastConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SystemConfig:
        """
        Deserialize from dictionary.

        Backward-compatible: if the scenario provides the old-style `target`
        section, it is loaded normally (single-beacon mode). If a `beacons`
        list is provided, it is parsed into BeaconConfig objects. If both are
        absent, defaults apply.
        """
        config = cls()
        for section_name, section_data in data.items():
            if section_name == "beacons" and isinstance(section_data, list):
                # New multi-beacon format
                config.beacons = [
                    BeaconConfig(**{k: v for k, v in b.items() if hasattr(BeaconConfig, k) or k in BeaconConfig.__dataclass_fields__})
                    for b in section_data
                ]
            elif section_name == "local_contrast" and isinstance(section_data, dict):
                for key, value in section_data.items():
                    if hasattr(config.local_contrast, key):
                        setattr(config.local_contrast, key, value)
            elif hasattr(config, section_name) and isinstance(section_data, dict):
                section = getattr(config, section_name)
                for key, value in section_data.items():
                    if hasattr(section, key):
                        setattr(section, key, value)
        return config


class ConfigManager:
    """
    Configuration Manager — Module 2 per Architecture v1.2.

    Responsibilities:
      - Load default configuration from defaults.py
      - Override with scenario file if provided
      - Override with GUI input if provided
      - Provide immutable snapshots for experiment reproducibility
      - Serialize/deserialize for scenario files

    The ConfigManager does NOT interpret parameters — it only stores
    and distributes them. Modules read from it, not from defaults.py.
    """

    def __init__(self) -> None:
        self._config = SystemConfig()

    @property
    def config(self) -> SystemConfig:
        """Return the current configuration."""
        return self._config

    def get_snapshot(self) -> SystemConfig:
        """Return a deep copy for experiment reproducibility."""
        return copy.deepcopy(self._config)

    def load_from_file(self, path: str) -> None:
        """Load configuration from a JSON scenario file."""
        with open(path, "r") as f:
            data = json.load(f)
        self._config = SystemConfig.from_dict(data)

    def save_to_file(self, path: str) -> None:
        """Save current configuration to a JSON file."""
        with open(path, "w") as f:
            json.dump(self._config.to_dict(), f, indent=2)

    def update_section(self, section_name: str, **kwargs) -> None:
        """
        Update a specific configuration section.
        Used by GUI or programmatic override.
        """
        if hasattr(self._config, section_name):
            section = getattr(self._config, section_name)
            for key, value in kwargs.items():
                if hasattr(section, key):
                    setattr(section, key, value)
                else:
                    raise ValueError(
                        f"Unknown parameter '{key}' in section '{section_name}'"
                    )
        else:
            raise ValueError(f"Unknown config section '{section_name}'")

    def reset_to_defaults(self) -> None:
        """Reset all configuration to PS/engineering defaults."""
        self._config = SystemConfig()

    def validate(self) -> List[str]:
        """
        Validate configuration against PS requirements.
        Returns list of validation errors (empty = valid).
        """
        errors = []
        cfg = self._config

        # Scene minimum size (PS_REQUIRED)
        if cfg.scene.width < defaults.SCENE_MIN_WIDTH:
            errors.append(
                f"Scene width {cfg.scene.width} < PS minimum "
                f"{defaults.SCENE_MIN_WIDTH}"
            )
        if cfg.scene.height < defaults.SCENE_MIN_HEIGHT:
            errors.append(
                f"Scene height {cfg.scene.height} < PS minimum "
                f"{defaults.SCENE_MIN_HEIGHT}"
            )

        # Target size range (PS_REQUIRED)
        if not (defaults.TARGET_MIN_SIZE
                <= cfg.target.size
                <= defaults.TARGET_MAX_SIZE):
            errors.append(
                f"Target size {cfg.target.size} outside PS range "
                f"[{defaults.TARGET_MIN_SIZE}, {defaults.TARGET_MAX_SIZE}]"
            )

        # PTZ speed range (PS_REQUIRED)
        if cfg.ptz.max_pan_speed_deg_s > defaults.PTZ_MAX_PAN_SPEED_DEG_S:
            errors.append(
                f"Pan speed {cfg.ptz.max_pan_speed_deg_s} exceeds PS maximum "
                f"{defaults.PTZ_MAX_PAN_SPEED_DEG_S}"
            )
        if cfg.ptz.max_tilt_speed_deg_s > defaults.PTZ_MAX_TILT_SPEED_DEG_S:
            errors.append(
                f"Tilt speed {cfg.ptz.max_tilt_speed_deg_s} exceeds PS maximum "
                f"{defaults.PTZ_MAX_TILT_SPEED_DEG_S}"
            )

        # Jitter limit (PS_REQUIRED)
        if cfg.jitter.max_px_per_frame > defaults.JITTER_MAX_PX_PER_FRAME:
            errors.append(
                f"Jitter {cfg.jitter.max_px_per_frame} exceeds PS maximum "
                f"{defaults.JITTER_MAX_PX_PER_FRAME}"
            )

        # Platform motion limit (PS_REQUIRED)
        if (cfg.platform_motion.max_px_per_frame
                > defaults.PLATFORM_MOTION_MAX_PX_PER_FRAME):
            errors.append(
                f"Platform motion {cfg.platform_motion.max_px_per_frame} "
                f"exceeds PS maximum "
                f"{defaults.PLATFORM_MOTION_MAX_PX_PER_FRAME}"
            )

        # Motion type must be mandatory (PS_REQUIRED)
        if cfg.motion.motion_type not in (
            defaults.MOTION_MANDATORY_TYPES
            + defaults.MOTION_OPTIONAL_TYPES
        ):
            errors.append(
                f"Unknown motion type '{cfg.motion.motion_type}'"
            )

        # Camera parameters validation
        if cfg.camera.width <= 0 or cfg.camera.height <= 0:
            errors.append(
                f"Camera resolution {cfg.camera.width}x{cfg.camera.height} must be positive"
            )
        if cfg.camera.update_rate_hz <= 0:
            errors.append(
                f"Camera update rate {cfg.camera.update_rate_hz} must be positive"
            )

        # PTZ gains validation
        if cfg.ptz.proportional_gain < 0.0:
            errors.append(
                f"PTZ proportional gain {cfg.ptz.proportional_gain} cannot be negative"
            )
        if cfg.ptz.integral_gain < 0.0:
            errors.append(
                f"PTZ integral gain {cfg.ptz.integral_gain} cannot be negative"
            )

        # Multi-beacon intensity validation (ENGINEERING_DEFAULT constraint)
        if cfg.beacons:
            primary_beacons = [b for b in cfg.beacons if b.role == "primary"]
            secondary_beacons = [b for b in cfg.beacons if b.role == "secondary"]
            if len(primary_beacons) == 0:
                errors.append(
                    "Multi-beacon config must have exactly one beacon with role='primary'."
                )
            elif len(primary_beacons) > 1:
                errors.append(
                    f"Multi-beacon config has {len(primary_beacons)} primary beacons; "
                    "exactly one is required."
                )
            else:
                primary_intensity = primary_beacons[0].intensity
                margin = defaults.BEACON_PRIMARY_MARGIN
                for sec in secondary_beacons:
                    max_allowed = primary_intensity - margin
                    if sec.intensity >= primary_intensity:
                        errors.append(
                            f"Secondary beacon '{sec.beacon_id}' intensity "
                            f"({sec.intensity}) >= primary intensity ({primary_intensity}). "
                            f"Secondary beacons must be dimmer than the primary beacon."
                        )
                    elif sec.intensity > max_allowed:
                        errors.append(
                            f"Secondary beacon '{sec.beacon_id}' intensity "
                            f"({sec.intensity}) exceeds primary - margin "
                            f"({primary_intensity} - {margin} = {max_allowed}). "
                            f"Increase primary intensity or decrease secondary intensity."
                        )
                # Validate sizes
                for b in cfg.beacons:
                    if not (defaults.TARGET_MIN_SIZE <= b.size <= defaults.TARGET_MAX_SIZE):
                        errors.append(
                            f"Beacon '{b.beacon_id}' size {b.size} outside PS range "
                            f"[{defaults.TARGET_MIN_SIZE}, {defaults.TARGET_MAX_SIZE}]."
                        )
                    if not (0 <= b.intensity <= 255):
                        errors.append(
                            f"Beacon '{b.beacon_id}' intensity {b.intensity} outside "
                            f"valid image range [0, 255]."
                        )

        # Local contrast disturbance validation
        if cfg.local_contrast.enabled:
            if cfg.local_contrast.amplitude < 0:
                errors.append(
                    f"Local contrast amplitude {cfg.local_contrast.amplitude} cannot be negative."
                )
            if cfg.local_contrast.amplitude > 200:
                errors.append(
                    f"Local contrast amplitude {cfg.local_contrast.amplitude} exceeds "
                    f"safe limit (200). Beacon may become undetectable."
                )
            if cfg.local_contrast.spatial_scale <= 0:
                errors.append(
                    f"Local contrast spatial_scale must be positive, "
                    f"got {cfg.local_contrast.spatial_scale}."
                )
            primary_intensity = cfg.target.intensity
            if cfg.beacons:
                primaries = [b for b in cfg.beacons if b.role == "primary"]
                if primaries:
                    primary_intensity = primaries[0].intensity
            min_margin = getattr(cfg.local_contrast, "min_beacon_margin", 30.0)
            if primary_intensity - cfg.local_contrast.amplitude < min_margin:
                errors.append(
                    f"Beacon peak intensity ({primary_intensity}) minus local contrast amplitude "
                    f"({cfg.local_contrast.amplitude}) is below minimum detection margin ({min_margin})."
                )

        return errors

    @staticmethod
    def validate_beacon_list(beacons: list, margin: int = None) -> List[str]:
        """
        Standalone beacon list validator.

        Args:
            beacons: List of BeaconConfig objects.
            margin: Required intensity margin (default: defaults.BEACON_PRIMARY_MARGIN).

        Returns:
            List of error strings (empty = valid).
        """
        if margin is None:
            margin = defaults.BEACON_PRIMARY_MARGIN
        errors = []
        primaries = [b for b in beacons if b.role == "primary"]
        secondaries = [b for b in beacons if b.role == "secondary"]
        if len(primaries) != 1:
            errors.append(f"Must have exactly 1 primary beacon, got {len(primaries)}.")
            return errors
        primary_intensity = primaries[0].intensity
        for sec in secondaries:
            if sec.intensity >= primary_intensity - margin:
                errors.append(
                    f"Secondary beacon '{sec.beacon_id}' intensity ({sec.intensity}) "
                    f"must be <= primary ({primary_intensity}) - margin ({margin}) = "
                    f"{primary_intensity - margin}."
                )
        return errors
