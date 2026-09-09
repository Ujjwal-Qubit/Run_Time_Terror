"""
Visualization Engine — Module 18 per Architecture v1.2 §18.

Handles live rendering of the camera viewport with overlays:
- Target centroid (crosshair)
- Detected bounding boxes
- Telemetry text (FPS, State, Error)
- PTZ aiming reticle

Designed to be invoked by the GUI Controller.
"""

from __future__ import annotations

import cv2
import numpy as np

from src.frame.data_contracts import VisualizationState


class VisualizationEngine:
    """
    Renders overlays on top of the raw camera frame for live display.
    """

    def __init__(self) -> None:
        pass

    def render(self, state: VisualizationState) -> np.ndarray:
        """
        Renders the given VisualizationState with tracking overlays.
        Returns a BGR image suitable for GUI display.
        """
        # Convert grayscale (uint8) to BGR for color drawing
        if len(state.display_image.shape) == 2:
            display = cv2.cvtColor(state.display_image, cv2.COLOR_GRAY2BGR)
        else:
            display = state.display_image.copy()

        h, w = display.shape[:2]

        # 1. Draw Adaptive ROI
        if state.roi and not state.roi.is_full_frame:
            roi = state.roi
            cv2.rectangle(
                display,
                (roi.x, roi.y),
                (roi.x + roi.width, roi.y + roi.height),
                (255, 255, 0), # Cyan
                1,
                cv2.LINE_AA
            )

        # 2. Draw Estimated Track (Red crosshair and circle)
        if state.estimated_centroid_x is not None and state.estimated_centroid_y is not None and state.tracking_state in ("TRACKING", "ACQUIRING", "REACQUIRING"):
            tx = int(state.estimated_centroid_x)
            ty = int(state.estimated_centroid_y)
            color = (0, 0, 255) # Red for active track
            
            # Draw crosshair
            length = 10
            cv2.line(display, (tx - length, ty), (tx + length, ty), color, 1)
            cv2.line(display, (tx, ty - length), (tx, ty + length), color, 1)
            cv2.circle(display, (tx, ty), 5, color, 1)

        # 3. Draw Ground Truth if available (Debug Mode)
        if state.ground_truth_x is not None and state.ground_truth_y is not None:
            gx = int(state.ground_truth_x)
            gy = int(state.ground_truth_y)
            cv2.drawMarker(display, (gx, gy), (0, 255, 0), markerType=cv2.MARKER_SQUARE, markerSize=8, thickness=1)

        # 4. Draw Center Reticle (Camera Aim)
        cx, cy = w // 2, h // 2
        cv2.line(display, (cx - 15, cy), (cx + 15, cy), (255, 255, 255), 1)
        cv2.line(display, (cx, cy - 15), (cx, cy + 15), (255, 255, 255), 1)

        # 5. Draw HUD Text
        y_offset = 20
        def put_text(text: str, color: tuple = (255, 255, 255)):
            nonlocal y_offset
            cv2.putText(display, text, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
            y_offset += 20

        # State mapping colors
        state_color = (255, 255, 255)
        if state.tracking_state == "TRACKING":
            state_color = (0, 255, 0)
        elif state.tracking_state == "LOST":
            state_color = (0, 0, 255)
        elif state.tracking_state in ("ACQUIRING", "REACQUIRING"):
            state_color = (0, 255, 255)

        put_text(f"FRAME: {state.frame_number}")
        put_text(f"STATE: {state.tracking_state}", state_color)
        
        # Computing metrics on the fly for HUD
        if state.estimated_centroid_x is not None and state.estimated_centroid_y is not None:
            err_x = state.estimated_centroid_x - cx
            err_y = state.estimated_centroid_y - cy
            err = (err_x**2 + err_y**2)**0.5
            put_text(f"TRK ERR: {err:.1f} px", (200, 200, 200))
        
        if state.processing_latency_ms > 0:
            put_text(f"LATENCY: {state.processing_latency_ms:.1f} ms", (200, 200, 200))
            put_text(f"FPS: {state.fps:.1f}", (200, 200, 200))

        return display
