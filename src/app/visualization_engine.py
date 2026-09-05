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

from src.frame.data_contracts import FramePacket, TrackerOutput, GroundTruth


class VisualizationEngine:
    """
    Renders overlays on top of the raw camera frame for live display.
    """

    def __init__(self) -> None:
        pass

    def render(
        self,
        packet: FramePacket,
        tracker_output: TrackerOutput,
        ground_truth: GroundTruth | None = None,
        draw_ground_truth: bool = False
    ) -> np.ndarray:
        """
        Renders the given frame with tracking overlays.
        Returns a BGR image suitable for GUI display.
        """
        # Convert grayscale (uint8) to BGR for color drawing
        if len(packet.image.shape) == 2:
            display = cv2.cvtColor(packet.image, cv2.COLOR_GRAY2BGR)
        else:
            display = packet.image.copy()

        h, w = display.shape[:2]

        # 1. Draw Adaptive ROI
        if tracker_output.roi and not tracker_output.roi.is_full_frame:
            roi = tracker_output.roi
            cv2.rectangle(
                display,
                (roi.x, roi.y),
                (roi.x + roi.width, roi.y + roi.height),
                (255, 255, 0), # Cyan
                1,
                cv2.LINE_AA
            )

        # 2. Draw Estimated Track (Red crosshair and circle)
        if tracker_output.track is not None and tracker_output.state.name in ("TRACKING", "ACQUIRING", "REACQUIRING"):
            tx = int(tracker_output.track.estimated_x)
            ty = int(tracker_output.track.estimated_y)
            color = (0, 0, 255) # Red for active track
            if tracker_output.track.is_coasting:
                color = (0, 165, 255) # Orange for coasting
            
            # Draw crosshair
            length = 10
            cv2.line(display, (tx - length, ty), (tx + length, ty), color, 1)
            cv2.line(display, (tx, ty - length), (tx, ty + length), color, 1)
            cv2.circle(display, (tx, ty), 5, color, 1)

        # 3. Draw Ground Truth if requested
        if draw_ground_truth and ground_truth is not None and ground_truth.target_visible:
            if ground_truth.ideal_projected_x is not None and ground_truth.ideal_projected_y is not None:
                gx = int(ground_truth.ideal_projected_x)
                gy = int(ground_truth.ideal_projected_y)
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
        if tracker_output.state.name == "TRACKING":
            state_color = (0, 255, 0)
        elif tracker_output.state.name == "LOST":
            state_color = (0, 0, 255)
        elif tracker_output.state.name in ("ACQUIRING", "REACQUIRING"):
            state_color = (0, 255, 255)

        put_text(f"FRAME: {packet.frame_number}")
        put_text(f"STATE: {tracker_output.state.name}", state_color)
        
        # Computing metrics on the fly for HUD
        if tracker_output.track is not None:
            err_x = tracker_output.track.estimated_x - cx
            err_y = tracker_output.track.estimated_y - cy
            err = (err_x**2 + err_y**2)**0.5
            put_text(f"TRK ERR: {err:.1f} px", (200, 200, 200))
        
        if tracker_output.processing_time_ms > 0:
            fps = 1000.0 / tracker_output.processing_time_ms
            put_text(f"LATENCY: {tracker_output.processing_time_ms:.1f} ms", (200, 200, 200))
            put_text(f"FPS: {fps:.1f}", (200, 200, 200))

        return display
