"""
Camera Model & Projection Model — Module 6 per Architecture v1.2 §4 and §6.

Maintains camera pointing state (pan/tilt, world position).
Encapsulates all projection mathematics in ProjectionModel so that
PTZController and other modules do not duplicate geometric calculations.
Extracts the clean camera viewport from the scene canvas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from src.config.config_manager import CameraConfig
from src.config import defaults


@dataclass(frozen=True)
class CameraPose:
    """Immutable camera pose representation in World Coordinate System (WCS)."""
    world_x: float          # Center X of camera viewport in WCS (pixels)
    world_y: float          # Center Y of camera viewport in WCS (pixels)
    pan_deg: float          # Pan angle (degrees)
    tilt_deg: float         # Tilt angle (degrees)


class ProjectionModel:
    """
    Encapsulates all camera geometry and projection mathematics.
    Per Architecture v1.2 §6 and §189.

    Consumed by CameraModel, GroundTruthProvider, and PTZController
    to avoid duplicated geometric equations across modules.
    """

    def __init__(
        self,
        width: int = defaults.CAMERA_DEFAULT_WIDTH,
        height: int = defaults.CAMERA_DEFAULT_HEIGHT,
        fov_h_deg: float = defaults.CAMERA_DEFAULT_FOV_H_DEG,
        fov_v_deg: float = defaults.CAMERA_DEFAULT_FOV_V_DEG,
    ) -> None:
        self._width = width
        self._height = height
        self._fov_h_deg = fov_h_deg
        self._fov_v_deg = fov_v_deg

        # Linear FOV mapping (Architecture v1.2 §6.2)
        self._deg_per_px_h = fov_h_deg / width
        self._deg_per_px_v = fov_v_deg / height
        self._px_per_deg_h = width / fov_h_deg
        self._px_per_deg_v = height / fov_v_deg

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def fov_h_deg(self) -> float:
        return self._fov_h_deg

    @property
    def fov_v_deg(self) -> float:
        return self._fov_v_deg

    @property
    def deg_per_px_h(self) -> float:
        return self._deg_per_px_h

    @property
    def deg_per_px_v(self) -> float:
        return self._deg_per_px_v

    @property
    def px_per_deg_h(self) -> float:
        return self._px_per_deg_h

    @property
    def px_per_deg_v(self) -> float:
        return self._px_per_deg_v

    def world_to_image(
        self,
        world_x: float,
        world_y: float,
        cam_world_x: float,
        cam_world_y: float,
    ) -> Tuple[float, float]:
        """
        Transform world coordinates (WCS) to camera image pixel coordinates (IPC).
        Image coordinate (0, 0) is top-left of the viewport.
        """
        v_left = cam_world_x - self._width / 2.0
        v_top = cam_world_y - self._height / 2.0
        img_x = world_x - v_left
        img_y = world_y - v_top
        return (img_x, img_y)

    def image_to_world(
        self,
        img_x: float,
        img_y: float,
        cam_world_x: float,
        cam_world_y: float,
    ) -> Tuple[float, float]:
        """
        Transform camera image pixel coordinates (IPC) back to world coordinates (WCS).
        """
        v_left = cam_world_x - self._width / 2.0
        v_top = cam_world_y - self._height / 2.0
        world_x = img_x + v_left
        world_y = img_y + v_top
        return (world_x, world_y)

    def image_to_angles(
        self,
        img_x: float,
        img_y: float,
    ) -> Tuple[float, float]:
        """
        Convert pixel coordinates (IPC) to angular offset from optical axis center.
        Optical axis center is at (width / 2, height / 2) -> (0.0, 0.0) deg.
        """
        dx_px = img_x - self._width / 2.0
        dy_px = img_y - self._height / 2.0
        d_pan = dx_px * self._deg_per_px_h
        d_tilt = dy_px * self._deg_per_px_v
        return (d_pan, d_tilt)

    def angles_to_image_offset(
        self,
        d_pan_deg: float,
        d_tilt_deg: float,
    ) -> Tuple[float, float]:
        """Convert angular offset in degrees to pixel displacement from image center."""
        dx_px = d_pan_deg * self._px_per_deg_h
        dy_px = d_tilt_deg * self._px_per_deg_v
        return (dx_px, dy_px)

    def angles_to_world_displacement(
        self,
        d_pan_deg: float,
        d_tilt_deg: float,
    ) -> Tuple[float, float]:
        """Convert angular command to world coordinate displacement in pixels."""
        d_world_x = d_pan_deg * self._px_per_deg_h
        d_world_y = d_tilt_deg * self._px_per_deg_v
        return (d_world_x, d_world_y)

    def is_visible(
        self,
        world_x: float,
        world_y: float,
        cam_world_x: float,
        cam_world_y: float,
        margin: float = 0.0,
    ) -> bool:
        """Check if world coordinate falls within the camera viewport."""
        img_x, img_y = self.world_to_image(world_x, world_y, cam_world_x, cam_world_y)
        return (
            (-margin <= img_x < self._width + margin)
            and (-margin <= img_y < self._height + margin)
        )


class CameraModel:
    """
    CameraModel (Module 6).

    Responsibilities:
      - Maintain camera pointing pose (world position, pan/tilt angles)
      - Provide ProjectionModel abstraction for coordinate transforms
      - Extract clean 2D viewport from scene canvas
      - Handle boundary padding gracefully
    """

    def __init__(
        self,
        camera_config: CameraConfig | None = None,
        scene_width: int = defaults.SCENE_DEFAULT_WIDTH,
        scene_height: int = defaults.SCENE_DEFAULT_HEIGHT,
        background_intensity: int = defaults.SCENE_BACKGROUND_INTENSITY,
    ) -> None:
        cfg = camera_config or CameraConfig()
        self._cfg = cfg
        self._scene_w = scene_width
        self._scene_h = scene_height
        self._bg_intensity = background_intensity

        self._width = cfg.width
        self._height = cfg.height
        self._fov_h_deg = cfg.fov_h_deg
        self._fov_v_deg = cfg.fov_v_deg

        # Projection model abstraction
        self._projection_model = ProjectionModel(
            width=self._width,
            height=self._height,
            fov_h_deg=self._fov_h_deg,
            fov_v_deg=self._fov_v_deg,
        )

        # Initial camera world position — default to center of scene (PS Row 6)
        if cfg.initial_x is not None:
            self._world_x = float(cfg.initial_x)
        else:
            self._world_x = self._scene_w / 2.0

        if cfg.initial_y is not None:
            self._world_y = float(cfg.initial_y)
        else:
            self._world_y = self._scene_h / 2.0

        self._initial_x = self._world_x
        self._initial_y = self._world_y
        self._pan_deg = 0.0
        self._tilt_deg = 0.0

    @property
    def projection_model(self) -> ProjectionModel:
        return self._projection_model

    @property
    def pose(self) -> CameraPose:
        return CameraPose(
            world_x=self._world_x,
            world_y=self._world_y,
            pan_deg=self._pan_deg,
            tilt_deg=self._tilt_deg,
        )

    @property
    def world_position(self) -> Tuple[float, float]:
        return (self._world_x, self._world_y)

    @property
    def pan_deg(self) -> float:
        return self._pan_deg

    @property
    def tilt_deg(self) -> float:
        return self._tilt_deg

    def reset(self) -> None:
        """Reset camera to initial position and angles."""
        self._world_x = self._initial_x
        self._world_y = self._initial_y
        self._pan_deg = 0.0
        self._tilt_deg = 0.0

    def set_position(self, world_x: float, world_y: float) -> None:
        """Directly set camera center in world coordinates."""
        self._world_x = float(world_x)
        self._world_y = float(world_y)

    def apply_pan_tilt(self, delta_pan_deg: float, delta_tilt_deg: float) -> None:
        """
        Apply PTZ angular shift to camera pose.
        Updates pan/tilt angles and moves camera center in world coordinates.
        """
        self._pan_deg += delta_pan_deg
        self._tilt_deg += delta_tilt_deg

        # Convert angular displacements to world coordinates displacement
        dw_x, dw_y = self._projection_model.angles_to_world_displacement(
            delta_pan_deg, delta_tilt_deg
        )
        self._world_x += dw_x
        self._world_y += dw_y

    def extract_viewport(
        self,
        scene_canvas: np.ndarray,
        effective_x: Optional[float] = None,
        effective_y: Optional[float] = None,
    ) -> np.ndarray:
        """
        Extract the camera viewport from the scene canvas.

        Args:
            scene_canvas: 2D numpy array (scene_h, scene_w) uint8
            effective_x: Optional perturbed center X (from disturbances).
                         If None, uses self._world_x.
            effective_y: Optional perturbed center Y (from disturbances).
                         If None, uses self._world_y.

        Returns:
            Clean camera frame as 2D numpy array (height, width) uint8.
        """
        cx = effective_x if effective_x is not None else self._world_x
        cy = effective_y if effective_y is not None else self._world_y

        v_left = int(round(cx - self._width / 2.0))
        v_top = int(round(cy - self._height / 2.0))
        v_right = v_left + self._width
        v_bottom = v_top + self._height

        scene_h, scene_w = scene_canvas.shape

        # Fast path: viewport completely inside scene
        if 0 <= v_left and v_right <= scene_w and 0 <= v_top and v_bottom <= scene_h:
            return scene_canvas[v_top:v_bottom, v_left:v_right].copy()

        # Boundary path: viewport overlaps boundary, pad with background intensity
        frame = np.full(
            (self._height, self._width),
            fill_value=self._bg_intensity,
            dtype=np.uint8,
        )

        src_x0 = max(0, v_left)
        src_y0 = max(0, v_top)
        src_x1 = min(scene_w, v_right)
        src_y1 = min(scene_h, v_bottom)

        if src_x1 > src_x0 and src_y1 > src_y0:
            dst_x0 = src_x0 - v_left
            dst_y0 = src_y0 - v_top
            dst_x1 = dst_x0 + (src_x1 - src_x0)
            dst_y1 = dst_y0 + (src_y1 - src_y0)
            frame[dst_y0:dst_y1, dst_x0:dst_x1] = scene_canvas[src_y0:src_y1, src_x0:src_x1]

        return frame
