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
            # Random position within scene margin
            low_x = self._margin
            high_x = self._scene_w - self._margin
            low_y = self._margin
            high_y = self._scene_h - self._margin
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
            # Bounded random walk
            max_disp = self._motion_cfg.random_max_displacement
            dx = float(self._rng.uniform(-max_disp, max_disp))
            dy = float(self._rng.uniform(-max_disp, max_disp))
            new_x = self._x + dx
            new_y = self._y + dy

            # Clamp / bounce within boundaries
            min_bound_x = self._margin
            max_bound_x = self._scene_w - self._margin
            min_bound_y = self._margin
            max_bound_y = self._scene_h - self._margin

            if min_bound_x <= new_x <= max_bound_x:
                self._x = new_x
                self._vx = dx / dt if dt > 0 else 0.0
            else:
                self._vx = -self._vx

            if min_bound_y <= new_y <= max_bound_y:
                self._y = new_y
                self._vy = dy / dt if dt > 0 else 0.0
            else:
                self._vy = -self._vy

        return self.target_state
