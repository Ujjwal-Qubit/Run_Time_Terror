"""
Ground Truth Provider — Module 14 per Architecture v1.2 §4 and §12.1b.

Collects true beacon position and camera state per frame.
Preserves the architectural distinction between four coordinate concepts:
  1. target_world_position (WCS)
  2. ideal_projected_position (IPC continuous)
  3. rendered_centroid (IPC discrete grid intensity centroid)
  4. (estimated_centroid — produced by tracker, NEVER here)

FIREWALL ENFORCEMENT:
Ground truth flows ONLY to MetricsEngine, LoggingEngine, and evaluation harness.
It is NEVER bundled into FramePacket or exposed to tracker modules.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from src.frame.data_contracts import GroundTruth
from src.simulation.target_manager import TargetState
from src.simulation.camera_model import CameraModel, ProjectionModel


class GroundTruthProvider:
    """
    GroundTruthProvider (Module 14).

    Responsibilities:
      - Capture synchronized ground truth for every simulated frame
      - Calculate ideal projected position using ProjectionModel
      - Calculate rendered intensity centroid on clean discrete viewport
      - Maintain thread-safe ground truth history
      - Enforce strict isolation from detection and tracking modules
    """

    def __init__(self, background_intensity: int = 30) -> None:
        self._bg_intensity = background_intensity
        self._history: Dict[int, GroundTruth] = {}

    def capture(
        self,
        frame_number: int,
        timestamp: float,
        target_state: TargetState,
        camera_model: CameraModel,
        clean_viewport: Optional[np.ndarray] = None,
        effective_cam_x: Optional[float] = None,
        effective_cam_y: Optional[float] = None,
    ) -> GroundTruth:
        """
        Capture and record a synchronized GroundTruth entry for a frame.

        Args:
            frame_number: Sequential frame index
            timestamp: Simulation time in seconds
            target_state: True kinematics from TargetManager
            camera_model: CameraModel instance
            clean_viewport: Clean extracted viewport (before noise/atmosphere)
            effective_cam_x: Perturbed camera center X (after geometric disturbances)
            effective_cam_y: Perturbed camera center Y (after geometric disturbances)

        Returns:
            The recorded GroundTruth dataclass
        """
        proj = camera_model.projection_model
        cam_x = effective_cam_x if effective_cam_x is not None else camera_model.world_position[0]
        cam_y = effective_cam_y if effective_cam_y is not None else camera_model.world_position[1]

        # 1. World coordinates
        tw_x = target_state.world_x
        tw_y = target_state.world_y

        # 2. Ideal projected image coordinates
        proj_x, proj_y = proj.world_to_image(tw_x, tw_y, cam_x, cam_y)

        # Check visibility within camera viewport
        is_vis = proj.is_visible(tw_x, tw_y, cam_x, cam_y)

        # 3. Rendered beacon intensity centroid on pixel grid
        rendered_cx: Optional[float] = None
        rendered_cy: Optional[float] = None

        if is_vis and clean_viewport is not None:
            rendered_cx, rendered_cy = self._compute_rendered_centroid(
                clean_viewport, proj_x, proj_y, target_state.size
            )

        gt = GroundTruth(
            frame_number=frame_number,
            timestamp=timestamp,
            target_world_x=tw_x,
            target_world_y=tw_y,
            ideal_projected_x=proj_x if is_vis else None,
            ideal_projected_y=proj_y if is_vis else None,
            rendered_centroid_x=rendered_cx,
            rendered_centroid_y=rendered_cy,
            target_visible=is_vis,
            camera_pan_deg=camera_model.pan_deg,
            camera_tilt_deg=camera_model.tilt_deg,
        )

        self._history[frame_number] = gt
        return gt

    def _compute_rendered_centroid(
        self,
        clean_viewport: np.ndarray,
        proj_x: float,
        proj_y: float,
        target_size: int,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Compute the actual intensity centroid of the rendered beacon on the clean pixel grid.
        Restricted to a local bounding box around the projected position to avoid
        stray artifacts or noise.
        """
        h, w = clean_viewport.shape
        margin = max(5, target_size)
        x0 = max(0, int(math.floor(proj_x - margin)))
        y0 = max(0, int(math.floor(proj_y - margin)))
        x1 = min(w, int(math.ceil(proj_x + margin + 1)))
        y1 = min(h, int(math.ceil(proj_y + margin + 1)))

        if x1 <= x0 or y1 <= y0:
            return (None, None)

        patch = clean_viewport[y0:y1, x0:x1].astype(np.float64)
        # Background subtraction
        signal = patch - self._bg_intensity
        signal[signal < 0] = 0.0

        total_signal = np.sum(signal)
        if total_signal <= 0:
            return (proj_x, proj_y)

        # Grid coordinate weighting
        y_coords, x_coords = np.mgrid[y0:y1, x0:x1]
        cx = float(np.sum(x_coords * signal) / total_signal)
        cy = float(np.sum(y_coords * signal) / total_signal)
        return (cx, cy)

    def get_truth(self, frame_number: int) -> Optional[GroundTruth]:
        """Retrieve GroundTruth for a specific frame. Consumed by MetricsEngine."""
        return self._history.get(frame_number)

    def get_all_truth(self) -> List[GroundTruth]:
        """Retrieve all recorded GroundTruth entries in chronological order."""
        return [self._history[k] for k in sorted(self._history.keys())]

    def clear(self) -> None:
        """Clear recorded ground truth history."""
        self._history.clear()
