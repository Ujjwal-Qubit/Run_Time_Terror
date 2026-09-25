"""
Target Manager — Module 5 per Architecture v1.2 §4.

Generates beacon spot(s) with configurable size, shape, and intensity.
Implements the four mandatory motion patterns:
  1. Straight Line
  2. Circular
  3. Figure-8
  4. Random
Exposes target state independently from the rendered image.
Guarantees mathematically reproducible trajectories via deterministic random seeds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.config.config_manager import TargetConfig, MotionConfig
from src.config import defaults
from src.frame.data_contracts import MotionType


@dataclass
class TargetState:
    """
    Independent state of the beacon target at a given simulation instant.
    Contains world-coordinate kinematics and the pre-generated beacon patch.
    """
    world_x: float
    world_y: float
    vx: float
    vy: float
    size: int
    shape: str
    intensity: int
    patch: np.ndarray


class TargetManager:
    """
    TargetManager (Module 5).

    Responsibilities:
      - Manage beacon spot generation (square, circle, gaussian)
      - Compute per-frame position based on selected motion pattern
      - Provide reproducible trajectories with random seed
      - Expose target state independently from image rendering
    """

    def __init__(
        self,
        target_config: TargetConfig | None = None,
        motion_config: MotionConfig | None = None,
        scene_width: int = defaults.SCENE_DEFAULT_WIDTH,
        scene_height: int = defaults.SCENE_DEFAULT_HEIGHT,
        seed: int = defaults.SIM_DEFAULT_RANDOM_SEED,
    ) -> None:
        self._target_cfg = target_config or TargetConfig()
        self._motion_cfg = motion_config or MotionConfig()
        self._scene_w = scene_width
        self._scene_h = scene_height
        self._seed = seed

        # Validate PS required target size limits: 5 to 20 pixels (PS Row 10)
        if not (defaults.TARGET_MIN_SIZE <= self._target_cfg.size <= defaults.TARGET_MAX_SIZE):
            raise ValueError(
                f"Target size {self._target_cfg.size} out of PS range "
                f"[{defaults.TARGET_MIN_SIZE}, {defaults.TARGET_MAX_SIZE}]."
            )

        self._size = self._target_cfg.size
        self._shape = self._target_cfg.shape.lower()
        self._intensity = int(np.clip(self._target_cfg.intensity, 0, 255))
        self._speed = float(self._target_cfg.speed)
        self._margin = float(self._size)

        # Generate precomputed beacon patch
        self._patch = self._generate_patch(self._size, self._shape, self._intensity)

        # Initialize RNG and kinematics
        self._rng = np.random.RandomState(self._seed)
        self._time = 0.0
        self._init_kinematics()

    @property
    def target_state(self) -> TargetState:
        return TargetState(
            world_x=self._x,
            world_y=self._y,
            vx=self._vx,
            vy=self._vy,
            size=self._size,
            shape=self._shape,
            intensity=self._intensity,
            patch=self._patch,
        )

    @property
    def world_position(self) -> tuple[float, float]:
        return (self._x, self._y)

    @property
    def patch(self) -> np.ndarray:
        return self._patch

    def _generate_patch(self, size: int, shape: str, intensity: int) -> np.ndarray:
        """Generate the beacon patch image (size x size) uint8."""
        patch = np.zeros((size, size), dtype=np.uint8)
        if shape == "square":
            # PS Default shape: Square (PS Row 9)
            patch.fill(intensity)
        elif shape == "circle":
            center = (size - 1) / 2.0
            radius = size / 2.0
            y_indices, x_indices = np.ogrid[:size, :size]
            dist_sq = (x_indices - center) ** 2 + (y_indices - center) ** 2
            mask = dist_sq <= radius ** 2
            patch[mask] = intensity
        elif shape == "gaussian":
            center = (size - 1) / 2.0
            sigma = max(1.0, size / 4.0)
            y_indices, x_indices = np.ogrid[:size, :size]
            dist_sq = (x_indices - center) ** 2 + (y_indices - center) ** 2
            profile = np.exp(-dist_sq / (2.0 * sigma ** 2))
            patch = (profile * intensity).astype(np.uint8)
        else:
            # Fallback to square
            patch.fill(intensity)
        return patch

    def _init_kinematics(self) -> None:
        """Initialize position and velocity for the selected motion pattern."""
        self._time = 0.0
        # Determine initial position
        if self._target_cfg.initial_position.lower() == "random":
            # Random position constrained to a central region to ensure
            # initial visibility for typical camera FOV at scene center.
            # (e.g., +/- 150 pixels from center)
            center_x = self._scene_w / 2.0
            center_y = self._scene_h / 2.0
            spawn_range = 150.0
            low_x = max(self._margin, center_x - spawn_range)
            high_x = min(self._scene_w - self._margin, center_x + spawn_range)
            low_y = max(self._margin, center_y - spawn_range)
            high_y = min(self._scene_h - self._margin, center_y + spawn_range)
            self._init_x = float(self._rng.uniform(low_x, high_x))
            self._init_y = float(self._rng.uniform(low_y, high_y))
        else:
            self._init_x = (
                float(self._target_cfg.initial_x)
                if self._target_cfg.initial_x is not None
                else self._scene_w / 2.0
            )
            self._init_y = (
                float(self._target_cfg.initial_y)
                if self._target_cfg.initial_y is not None
                else self._scene_h / 2.0
            )

        self._x = self._init_x
        self._y = self._init_y

        m_type = self._motion_cfg.motion_type.upper()
        if m_type == MotionType.STRAIGHT_LINE.value or m_type == "STRAIGHT_LINE":
            angle_rad = math.radians(self._motion_cfg.straight_line_angle_deg)
            self._vx = self._speed * math.cos(angle_rad)
            self._vy = self._speed * math.sin(angle_rad)
        elif m_type == MotionType.CIRCULAR.value or m_type == "CIRCULAR":
            self._circle_r = max(10.0, self._motion_cfg.circle_radius)
            self._omega = self._speed / self._circle_r
            # Center chosen so (init_x, init_y) is on the circle at phi=0
            # Clamp center so the circle stays within scene bounds
            self._circle_cx = np.clip(
                self._init_x - self._circle_r,
                self._circle_r + self._margin,
                self._scene_w - self._circle_r - self._margin,
            )
            self._circle_cy = np.clip(
                self._init_y,
                self._circle_r + self._margin,
                self._scene_h - self._circle_r - self._margin,
            )
            # Recompute init position from clamped center
            self._x = self._circle_cx + self._circle_r
            self._y = self._circle_cy
            self._vx = 0.0
            self._vy = self._speed
        elif m_type == MotionType.FIGURE_8.value or m_type == "FIGURE_8":
            self._fig8_rx = max(10.0, self._motion_cfg.figure8_radius_x)
            self._fig8_ry = max(10.0, self._motion_cfg.figure8_radius_y)
            denom = math.sqrt(self._fig8_rx ** 2 + self._fig8_ry ** 2)
            self._fig8_omega = self._speed / denom if denom > 0 else 0.1
            self._fig8_cx = np.clip(
                self._init_x,
                self._fig8_rx + self._margin,
                self._scene_w - self._fig8_rx - self._margin,
            )
            self._fig8_cy = np.clip(
                self._init_y,
                self._fig8_ry + self._margin,
                self._scene_h - self._fig8_ry - self._margin,
            )
            self._x = self._fig8_cx
            self._y = self._fig8_cy
            self._vx = self._fig8_rx * self._fig8_omega
            self._vy = 2.0 * self._fig8_ry * self._fig8_omega
        elif m_type == MotionType.RANDOM.value or m_type == "RANDOM":
            self._vx = float(self._rng.uniform(-self._speed, self._speed))
            self._vy = float(self._rng.uniform(-self._speed, self._speed))
        else:
            self._vx = self._speed
            self._vy = 0.0

    @property
    def speed(self) -> float:
        """Current target speed in pixels/second."""
        return self._speed

    def set_speed(self, speed: float) -> None:
        """Dynamically update beacon speed and rescale velocity components."""
        self._speed = max(0.0, float(speed))
        self._target_cfg.speed = self._speed
        m_type = self._motion_cfg.motion_type.upper()
        if m_type in (MotionType.STRAIGHT_LINE.value, "STRAIGHT_LINE"):
            current_norm = math.hypot(self._vx, self._vy)
            if current_norm > 1e-6:
                self._vx = (self._vx / current_norm) * self._speed
                self._vy = (self._vy / current_norm) * self._speed
            else:
                angle = math.radians(self._motion_cfg.straight_line_angle_deg)
                self._vx = self._speed * math.cos(angle)
                self._vy = self._speed * math.sin(angle)
        elif m_type in (MotionType.CIRCULAR.value, "CIRCULAR"):
            if hasattr(self, "_circle_r") and self._circle_r > 0:
                self._omega = self._speed / self._circle_r
        elif m_type in (MotionType.FIGURE_8.value, "FIGURE_8"):
            rx = getattr(self, "_fig8_rx", 100.0)
            ry = getattr(self, "_fig8_ry", 100.0)
            denom = math.sqrt(rx ** 2 + ry ** 2)
            self._fig8_omega = self._speed / denom if denom > 0 else 0.1
        elif m_type in (MotionType.RANDOM.value, "RANDOM"):
            current_norm = math.hypot(self._vx, self._vy)
            if current_norm > 1e-6:
                self._vx = (self._vx / current_norm) * self._speed
                self._vy = (self._vy / current_norm) * self._speed

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset target to initial conditions with optional new seed."""
        if seed is not None:
            self._seed = seed
        self._rng = np.random.RandomState(self._seed)
        self._init_kinematics()

    def step(self, dt: float) -> TargetState:
        """
        Advance target physics by dt seconds.

        Args:
            dt: Time step in seconds

        Returns:
            Updated TargetState
        """
        self._time += dt
        m_type = self._motion_cfg.motion_type.upper()

        if m_type in (MotionType.STRAIGHT_LINE.value, "STRAIGHT_LINE"):
            self._x += self._vx * dt
            self._y += self._vy * dt

            # Specular bounce off scene margins to keep beacon inside canvas
            min_bound_x = self._margin
            max_bound_x = self._scene_w - self._margin
            min_bound_y = self._margin
            max_bound_y = self._scene_h - self._margin

            if self._x <= min_bound_x:
                self._x = min_bound_x + (min_bound_x - self._x)
                self._vx = -self._vx
            elif self._x >= max_bound_x:
                self._x = max_bound_x - (self._x - max_bound_x)
                self._vx = -self._vx

            if self._y <= min_bound_y:
                self._y = min_bound_y + (min_bound_y - self._y)
                self._vy = -self._vy
            elif self._y >= max_bound_y:
                self._y = max_bound_y - (self._y - max_bound_y)
                self._vy = -self._vy

        elif m_type in (MotionType.CIRCULAR.value, "CIRCULAR"):
            theta = self._omega * self._time
            self._x = self._circle_cx + self._circle_r * math.cos(theta)
            self._y = self._circle_cy + self._circle_r * math.sin(theta)
            self._vx = -self._circle_r * self._omega * math.sin(theta)
            self._vy = self._circle_r * self._omega * math.cos(theta)

        elif m_type in (MotionType.FIGURE_8.value, "FIGURE_8"):
            theta = self._fig8_omega * self._time
            self._x = self._fig8_cx + self._fig8_rx * math.sin(theta)
            self._y = self._fig8_cy + self._fig8_ry * math.sin(2.0 * theta)
            self._vx = self._fig8_rx * self._fig8_omega * math.cos(theta)
            self._vy = 2.0 * self._fig8_ry * self._fig8_omega * math.cos(2.0 * theta)

        elif m_type in (MotionType.RANDOM.value, "RANDOM"):
            # Temporally coherent random motion (stochastic acceleration)
            # random_max_displacement is repurposed here as max delta_v per frame
            max_dv = self._motion_cfg.random_max_displacement
            dvx = float(self._rng.uniform(-max_dv, max_dv))
            dvy = float(self._rng.uniform(-max_dv, max_dv))
            
            self._vx += dvx
            self._vy += dvy
            
            # Constrain to configured speed limit
            current_speed = math.hypot(self._vx, self._vy)
            if current_speed > self._speed and current_speed > 0:
                scale = self._speed / current_speed
                self._vx *= scale
                self._vy *= scale
                
            self._x += self._vx * dt
            self._y += self._vy * dt

            # Specular bounce off scene margins
            min_bound_x = self._margin
            max_bound_x = self._scene_w - self._margin
            min_bound_y = self._margin
            max_bound_y = self._scene_h - self._margin

            if self._x <= min_bound_x:
                self._x = min_bound_x + (min_bound_x - self._x)
                self._vx = -self._vx
            elif self._x >= max_bound_x:
                self._x = max_bound_x - (self._x - max_bound_x)
                self._vx = -self._vx

            if self._y <= min_bound_y:
                self._y = min_bound_y + (min_bound_y - self._y)
                self._vy = -self._vy
            elif self._y >= max_bound_y:
                self._y = max_bound_y - (self._y - max_bound_y)
                self._vy = -self._vy

        return self.target_state

    @property
    def speed(self) -> float:
        return self._speed

    def set_speed(self, speed: float) -> None:
        """Dynamically update beacon speed and rescale velocity components."""
        self._speed = max(0.0, float(speed))
        self._target_cfg.speed = self._speed
        m_type = self._motion_cfg.motion_type
        if isinstance(m_type, MotionType):
            m_type = m_type.value
        m_type = str(m_type).upper()

        if m_type in (MotionType.STRAIGHT_LINE.value, "STRAIGHT_LINE"):
            current_norm = math.hypot(self._vx, self._vy)
            if current_norm > 1e-6:
                self._vx = (self._vx / current_norm) * self._speed
                self._vy = (self._vy / current_norm) * self._speed
            else:
                angle = math.radians(self._motion_cfg.straight_line_angle_deg)
                self._vx = self._speed * math.cos(angle)
                self._vy = self._speed * math.sin(angle)
        elif m_type in (MotionType.CIRCULAR.value, "CIRCULAR"):
            if hasattr(self, "_circle_r") and self._circle_r > 0:
                self._omega = self._speed / self._circle_r
        elif m_type in (MotionType.FIGURE_8.value, "FIGURE_8"):
            rx = getattr(self, "_fig8_rx", 100.0)
            ry = getattr(self, "_fig8_ry", 100.0)
            denom = math.sqrt(rx ** 2 + ry ** 2)
            self._fig8_omega = self._speed / denom if denom > 0 else 0.1
        elif m_type in (MotionType.RANDOM.value, "RANDOM"):
            current_norm = math.hypot(self._vx, self._vy)
            if current_norm > 1e-6:
                self._vx = (self._vx / current_norm) * self._speed
                self._vy = (self._vy / current_norm) * self._speed


# ---------------------------------------------------------------------------
# Multi-Beacon Extension (Additive — does not modify TargetManager above)
# ---------------------------------------------------------------------------

@dataclass
class SecondaryBeaconState:
    """
    Kinematic and appearance state for a single secondary (distractor) beacon.
    Mirrors TargetState structure for use with SceneManager compositing.
    """
    world_x: float
    world_y: float
    vx: float
    vy: float
    size: int
    shape: str
    intensity: int
    patch: np.ndarray
    beacon_id: str = "secondary"


class MultiBeaconManager:
    """
    Multi-Beacon Manager — manages a primary beacon (via TargetManager) plus
    zero or more secondary (distractor) beacons.

    Responsibilities:
      - Accept a list of BeaconConfig objects from SystemConfig.
      - Drive primary beacon through the existing TargetManager.
      - Drive secondary beacons through independent lightweight kinematic models.
      - Expose all beacon states for scene compositing (multi-render).
      - NEVER expose beacon identity or primary/secondary role to the tracker.

    Ground-Truth Firewall:
      Only the primary beacon's state is passed to GroundTruthProvider.
      Secondary beacons appear only in the rendered image.

    Backward Compatibility:
      If beacons list is empty or has only one primary beacon, this class
      delegates entirely to TargetManager and SceneManager.render() is called
      with single-target arguments exactly as before.
    """

    def __init__(
        self,
        beacon_configs: list,  # List[BeaconConfig]
        motion_config: MotionConfig,
        scene_width: int = defaults.SCENE_DEFAULT_WIDTH,
        scene_height: int = defaults.SCENE_DEFAULT_HEIGHT,
        seed: int = defaults.SIM_DEFAULT_RANDOM_SEED,
    ) -> None:
        from src.config.config_manager import BeaconConfig

        self._scene_w = scene_width
        self._scene_h = scene_height
        self._seed = seed
        self._time = 0.0

        # Separate primary from secondaries
        primaries = [b for b in beacon_configs if b.role == "primary"]
        secondaries = [b for b in beacon_configs if b.role == "secondary"]

        if len(primaries) != 1:
            raise ValueError(
                f"MultiBeaconManager requires exactly 1 primary beacon, "
                f"got {len(primaries)}."
            )

        primary = primaries[0]

        # Construct a TargetConfig from the primary BeaconConfig
        from src.config.config_manager import TargetConfig
        primary_target_cfg = TargetConfig(
            count=1,
            size=primary.size,
            shape=primary.shape,
            intensity=primary.intensity,
            initial_position="center" if primary.x is None else "fixed",
            initial_x=primary.x,
            initial_y=primary.y,
            speed=primary.speed,
        )

        # Primary managed by existing TargetManager (full fidelity)
        self._primary_manager = TargetManager(
            target_config=primary_target_cfg,
            motion_config=motion_config,
            scene_width=scene_width,
            scene_height=scene_height,
            seed=seed,
        )

        # Secondary beacons: lightweight independent kinematic instances
        self._secondaries: List[_SecondaryBeaconKinematics] = []
        for idx, sec in enumerate(secondaries):
            sec_seed = seed + 100 + idx
            kin = _SecondaryBeaconKinematics(
                beacon_cfg=sec,
                motion_cfg=motion_config,
                scene_width=scene_width,
                scene_height=scene_height,
                seed=sec_seed,
            )
            self._secondaries.append(kin)

    @property
    def primary_manager(self) -> TargetManager:
        """Access the underlying primary TargetManager instance."""
        return self._primary_manager

    @property
    def managers(self) -> list:
        """List of all beacon kinematic managers (primary first)."""
        return [self._primary_manager] + self._secondaries

    @property
    def primary_state(self) -> TargetState:
        """Primary beacon TargetState."""
        return self._primary_manager.target_state

    @property
    def primary_target_state(self) -> TargetState:
        """Primary beacon state — forwarded to GroundTruthProvider."""
        return self._primary_manager.target_state

    @property
    def world_position(self) -> tuple:
        """Primary beacon world position."""
        return self._primary_manager.world_position

    @property
    def patch(self) -> np.ndarray:
        """Primary beacon patch."""
        return self._primary_manager.patch

    def step(self, dt: float) -> TargetState:
        """
        Advance all beacons by dt seconds.
        Returns the PRIMARY beacon TargetState (for backward compatibility
        and GroundTruthProvider).
        """
        self._time += dt
        primary_state = self._primary_manager.step(dt)
        for kin in self._secondaries:
            kin.step(dt)
        return primary_state

    def get_all_beacon_states(self) -> list:
        """
        Returns a list of (world_x, world_y, patch) tuples for ALL beacons
        (primary first, then secondaries) for scene compositing.

        The ordering deliberately mixes roles so the tracker never knows
        which entry is primary — it only sees the rendered pixel image.
        """
        states = []
        ps = self._primary_manager.target_state
        states.append((ps.world_x, ps.world_y, ps.patch))
        for kin in self._secondaries:
            s = kin.state
            states.append((s.world_x, s.world_y, s.patch))
        return states

    def set_speed(self, speed: float, beacon_index: int = 0) -> None:
        """Set speed for primary (index 0) or secondary (index >= 1) beacon."""
        if beacon_index == 0:
            self._primary_manager.set_speed(speed)
        elif 1 <= beacon_index <= len(self._secondaries):
            self._secondaries[beacon_index - 1].set_speed(speed)

    def set_primary_speed(self, speed: float) -> None:
        """Set speed of primary beacon."""
        self._primary_manager.set_speed(speed)

    def set_secondary_speed(self, index: int, speed: float) -> None:
        """Set speed of secondary beacon at index."""
        if 0 <= index < len(self._secondaries):
            self._secondaries[index].set_speed(speed)

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset all beacons to initial conditions."""
        if seed is not None:
            self._seed = seed
        self._primary_manager.reset(seed=self._seed)
        for idx, kin in enumerate(self._secondaries):
            kin.reset(seed=self._seed + 100 + idx)
        self._time = 0.0


class _SecondaryBeaconKinematics:
    """
    Lightweight kinematic model for a secondary (distractor) beacon.
    Mirrors the essential motion patterns of TargetManager without the
    full interface overhead. Uses the same motion patterns as the primary.
    """

    def __init__(
        self,
        beacon_cfg,  # BeaconConfig
        motion_cfg: MotionConfig,
        scene_width: int,
        scene_height: int,
        seed: int,
    ) -> None:
        self._cfg = beacon_cfg
        self._motion_cfg = motion_cfg
        self._scene_w = scene_width
        self._scene_h = scene_height
        self._seed = seed
        self._size = int(np.clip(beacon_cfg.size, defaults.TARGET_MIN_SIZE, defaults.TARGET_MAX_SIZE))
        self._intensity = int(np.clip(beacon_cfg.intensity, 0, 255))
        self._beacon_id = beacon_cfg.beacon_id

        # Build patch using same method as TargetManager
        self._patch = self._generate_patch(self._size, beacon_cfg.shape, self._intensity)

        self._rng = np.random.RandomState(self._seed)
        self._time = 0.0
        self._speed = float(beacon_cfg.speed)
        self._init_kinematics()

    def _generate_patch(self, size: int, shape: str, intensity: int) -> np.ndarray:
        """Generate beacon patch (same logic as TargetManager._generate_patch)."""
        patch = np.zeros((size, size), dtype=np.uint8)
        shape = shape.lower()
        if shape == "square":
            patch.fill(intensity)
        elif shape == "circle":
            center = (size - 1) / 2.0
            radius = size / 2.0
            y_idx, x_idx = np.ogrid[:size, :size]
            mask = (x_idx - center) ** 2 + (y_idx - center) ** 2 <= radius ** 2
            patch[mask] = intensity
        elif shape == "gaussian":
            center = (size - 1) / 2.0
            sigma = max(1.0, size / 4.0)
            y_idx, x_idx = np.ogrid[:size, :size]
            dist_sq = (x_idx - center) ** 2 + (y_idx - center) ** 2
            patch = (np.exp(-dist_sq / (2.0 * sigma ** 2)) * intensity).astype(np.uint8)
        else:
            patch.fill(intensity)
        return patch

    def _init_kinematics(self) -> None:
        self._time = 0.0
        margin = float(self._size)
        center_x = self._scene_w / 2.0
        center_y = self._scene_h / 2.0

        # Use configured position or random offset from center
        if self._cfg.x is not None:
            self._x = float(self._cfg.x)
        else:
            spawn_range = 300.0
            self._x = float(self._rng.uniform(
                max(margin, center_x - spawn_range),
                min(self._scene_w - margin, center_x + spawn_range),
            ))
        if self._cfg.y is not None:
            self._y = float(self._cfg.y)
        else:
            spawn_range = 300.0
            self._y = float(self._rng.uniform(
                max(margin, center_y - spawn_range),
                min(self._scene_h - margin, center_y + spawn_range),
            ))

        self._init_x = self._x
        self._init_y = self._y

        # Use beacon-specific motion type or fall back to primary's motion config
        motion_type = (self._cfg.motion_type or self._motion_cfg.motion_type).upper()

        if motion_type in ("STRAIGHT_LINE",):
            angle_rad = math.radians(self._motion_cfg.straight_line_angle_deg + 30.0)
            self._vx = self._speed * math.cos(angle_rad)
            self._vy = self._speed * math.sin(angle_rad)
        elif motion_type == "CIRCULAR":
            r = max(10.0, self._motion_cfg.circle_radius * 0.7)
            omega = self._speed / r
            cx = np.clip(self._x - r, r + margin, self._scene_w - r - margin)
            cy = np.clip(self._y, r + margin, self._scene_h - r - margin)
            self._circle_cx = cx
            self._circle_cy = cy
            self._circle_r = r
            self._omega = omega
            self._x = cx + r
            self._y = cy
            self._vx = 0.0
            self._vy = self._speed
        elif motion_type == "FIGURE_8":
            rx = max(10.0, self._motion_cfg.figure8_radius_x * 0.6)
            ry = max(10.0, self._motion_cfg.figure8_radius_y * 0.6)
            omega = self._speed / max(1.0, math.sqrt(rx ** 2 + ry ** 2))
            self._fig8_cx = np.clip(self._x, rx + margin, self._scene_w - rx - margin)
            self._fig8_cy = np.clip(self._y, ry + margin, self._scene_h - ry - margin)
            self._fig8_rx = rx
            self._fig8_ry = ry
            self._fig8_omega = omega
            self._vx = rx * omega
            self._vy = 2.0 * ry * omega
        else:  # RANDOM or fallback
            self._vx = float(self._rng.uniform(-self._speed, self._speed))
            self._vy = float(self._rng.uniform(-self._speed, self._speed))

        self._motion_type = motion_type

    @property
    def state(self) -> SecondaryBeaconState:
        return SecondaryBeaconState(
            world_x=self._x,
            world_y=self._y,
            vx=self._vx,
            vy=self._vy,
            size=self._size,
            shape=self._cfg.shape,
            intensity=self._intensity,
            patch=self._patch,
            beacon_id=self._beacon_id,
        )

    def step(self, dt: float) -> SecondaryBeaconState:
        """Advance secondary beacon physics by dt seconds."""
        self._time += dt
        margin = float(self._size)
        m_type = self._motion_type

        if m_type == "STRAIGHT_LINE":
            self._x += self._vx * dt
            self._y += self._vy * dt
            # Specular bounce
            if self._x <= margin or self._x >= self._scene_w - margin:
                self._vx = -self._vx
                self._x = float(np.clip(self._x, margin, self._scene_w - margin))
            if self._y <= margin or self._y >= self._scene_h - margin:
                self._vy = -self._vy
                self._y = float(np.clip(self._y, margin, self._scene_h - margin))
        elif m_type == "CIRCULAR":
            theta = self._omega * self._time
            self._x = self._circle_cx + self._circle_r * math.cos(theta)
            self._y = self._circle_cy + self._circle_r * math.sin(theta)
        elif m_type == "FIGURE_8":
            theta = self._fig8_omega * self._time
            self._x = self._fig8_cx + self._fig8_rx * math.sin(theta)
            self._y = self._fig8_cy + self._fig8_ry * math.sin(2.0 * theta)
        else:  # RANDOM
            max_dv = self._motion_cfg.random_max_displacement
            dvx = float(self._rng.uniform(-max_dv, max_dv))
            dvy = float(self._rng.uniform(-max_dv, max_dv))
            self._vx = float(np.clip(self._vx + dvx, -self._speed, self._speed))
            self._vy = float(np.clip(self._vy + dvy, -self._speed, self._speed))
            self._x += self._vx * dt
            self._y += self._vy * dt
            if self._x <= margin or self._x >= self._scene_w - margin:
                self._vx = -self._vx
                self._x = float(np.clip(self._x, margin, self._scene_w - margin))
            if self._y <= margin or self._y >= self._scene_h - margin:
                self._vy = -self._vy
                self._y = float(np.clip(self._y, margin, self._scene_h - margin))

        return self.state

    @property
    def speed(self) -> float:
        return self._speed

    def set_speed(self, speed: float) -> None:
        """Dynamically update secondary beacon speed and rescale velocity components."""
        self._speed = max(0.0, float(speed))
        self._cfg.speed = self._speed
        motion_type = (self._cfg.motion_type or self._motion_cfg.motion_type).upper()
        if motion_type in ("STRAIGHT_LINE",):
            current_norm = math.hypot(self._vx, self._vy)
            if current_norm > 1e-6:
                self._vx = (self._vx / current_norm) * self._speed
                self._vy = (self._vy / current_norm) * self._speed
            else:
                angle = math.radians(self._motion_cfg.straight_line_angle_deg + 30.0)
                self._vx = self._speed * math.cos(angle)
                self._vy = self._speed * math.sin(angle)
        elif motion_type == "CIRCULAR":
            if hasattr(self, "_circle_r") and self._circle_r > 0:
                self._omega = self._speed / self._circle_r
        elif motion_type == "FIGURE_8":
            rx = getattr(self, "_fig8_rx", 100.0)
            ry = getattr(self, "_fig8_ry", 100.0)
            denom = math.sqrt(rx ** 2 + ry ** 2)
            self._fig8_omega = self._speed / denom if denom > 0 else 0.1
        elif motion_type == "RANDOM":
            current_norm = math.hypot(self._vx, self._vy)
            if current_norm > 1e-6:
                self._vx = (self._vx / current_norm) * self._speed
                self._vy = (self._vy / current_norm) * self._speed

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self._seed = seed
        self._rng = np.random.RandomState(self._seed)
        self._init_kinematics()


