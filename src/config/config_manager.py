"""
Configuration Manager — Module 2 per Architecture v1.2 §4.

Centralizes all runtime configuration. Parameters are loaded from
defaults, then optionally overridden by scenario files or GUI input.

No parameter is scattered across source files — everything flows
through this manager.
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


@dataclass
class PTZConfig:
    """Pan/tilt controller configuration."""
    max_pan_speed_deg_s: float = defaults.PTZ_DEFAULT_PAN_SPEED_DEG_S
    max_tilt_speed_deg_s: float = defaults.PTZ_DEFAULT_TILT_SPEED_DEG_S
    update_rate_hz: int = defaults.PTZ_DEFAULT_UPDATE_RATE_HZ
    proportional_gain: float = defaults.PTZ_DEFAULT_PROPORTIONAL_GAIN
    deadband_px: float = defaults.PTZ_DEFAULT_DEADBAND_PX


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
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON export."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SystemConfig:
        """Deserialize from dictionary."""
        config = cls()
        for section_name, section_data in data.items():
            if hasattr(config, section_name) and isinstance(section_data, dict):
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

        return errors
