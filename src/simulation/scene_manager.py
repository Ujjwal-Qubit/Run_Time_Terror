"""
Scene Manager — Module 4 per Architecture v1.2 §4.

Manages the 2D global/world canvas (WCS), coordinate management,
background generation, and deterministic beacon compositing.
"""

from __future__ import annotations

import numpy as np

from src.config.config_manager import SceneConfig
from src.config import defaults


class SceneManager:
    """
    SceneManager (Module 4).

    Responsibilities:
      - Manage 2D global scene canvas in World Coordinate System (WCS)
      - Enforce scene dimensions (>= 2000x2000 per PS Row 1)
      - Render uniform/textured background
      - Deterministically composite beacon target(s) onto scene
    """

    def __init__(self, config: SceneConfig | None = None) -> None:
        cfg = config or SceneConfig()
        if cfg.width < defaults.SCENE_MIN_WIDTH or cfg.height < defaults.SCENE_MIN_HEIGHT:
            raise ValueError(
                f"Scene dimensions ({cfg.width}x{cfg.height}) violate PS requirement: "
                f"minimum is {defaults.SCENE_MIN_WIDTH}x{defaults.SCENE_MIN_HEIGHT}."
            )
        self._width: int = cfg.width
        self._height: int = cfg.height
        self._background_intensity: int = int(np.clip(cfg.background_intensity, 0, 255))
        self._background: np.ndarray = np.full(
            (self._height, self._width),
            fill_value=self._background_intensity,
            dtype=np.uint8,
        )
        self._current_canvas: np.ndarray = self._background.copy()

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def background_intensity(self) -> int:
        return self._background_intensity

    @property
    def current_canvas(self) -> np.ndarray:
        return self._current_canvas

    def reset(self) -> None:
        """Reset canvas to clean background."""
        self._background = np.full(
            (self._height, self._width),
            fill_value=self._background_intensity,
            dtype=np.uint8,
        )
        self._current_canvas = self._background.copy()

    def render(
        self,
        target_x: float,
        target_y: float,
        target_patch: np.ndarray,
    ) -> np.ndarray:
        """
        Deterministically composite a target patch onto the background canvas.

        Args:
            target_x: Center X coordinate in WCS (pixels)
            target_y: Center Y coordinate in WCS (pixels)
            target_patch: 2D numpy array (patch_h, patch_w) uint8 containing beacon

        Returns:
            Rendered world canvas as 2D numpy array (height, width) uint8
        """
        canvas = self._background.copy()
        patch_h, patch_w = target_patch.shape

        # Calculate bounding box in WCS (centered at target_x, target_y)
        x_min = int(round(target_x - patch_w / 2.0))
        y_min = int(round(target_y - patch_h / 2.0))
        x_max = x_min + patch_w
        y_max = y_min + patch_h

        # Compute intersection with canvas bounds
        src_x0 = max(0, -x_min)
        src_y0 = max(0, -y_min)
        src_x1 = patch_w - max(0, x_max - self._width)
        src_y1 = patch_h - max(0, y_max - self._height)

        dst_x0 = max(0, x_min)
        dst_y0 = max(0, y_min)
        dst_x1 = min(self._width, x_max)
        dst_y1 = min(self._height, y_max)

        if dst_x1 > dst_x0 and dst_y1 > dst_y0 and src_x1 > src_x0 and src_y1 > src_y0:
            patch_region = target_patch[src_y0:src_y1, src_x0:src_x1]
            canvas_region = canvas[dst_y0:dst_y1, dst_x0:dst_x1]
            # Beacon intensity composite (max blend preserves bright beacon over background)
            canvas[dst_y0:dst_y1, dst_x0:dst_x1] = np.maximum(canvas_region, patch_region)

        self._current_canvas = canvas
        return canvas
