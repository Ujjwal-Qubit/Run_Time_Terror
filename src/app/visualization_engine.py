from __future__ import annotations

import collections
import cv2
import numpy as np

from src.frame.data_contracts import VisualizationState


class VisualizationEngine:
    """
    Renders overlays on top of the raw camera frame for live display.
    Includes motion trail, velocity vector, reticle, and telemetry HUD.
    """

    def __init__(self, max_trail_len: int = 24) -> None:
        self._max_trail_len = max_trail_len
        self._trail: collections.deque = collections.deque(maxlen=max_trail_len)

    def reset(self) -> None:
        """Clear motion trail history upon reset."""
        self._trail.clear()

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

        # 2. Update and Draw Motion Trail
        is_tracking_state = state.tracking_state in ("TRACKING", "ACQUIRING", "REACQUIRING")
        if (
            state.estimated_centroid_x is not None
            and state.estimated_centroid_y is not None
            and is_tracking_state
        ):
            tx = float(state.estimated_centroid_x)
            ty = float(state.estimated_centroid_y)
            self._trail.append((tx, ty))
        elif state.tracking_state == "LOST":
            # Retain trail temporarily or let it decay
            pass

        # Draw fading motion trail dots and path line
        trail_pts = list(self._trail)
        n_pts = len(trail_pts)
        if n_pts >= 2:
            for i in range(1, n_pts):
                p1 = (int(round(trail_pts[i - 1][0])), int(round(trail_pts[i - 1][1])))
                p2 = (int(round(trail_pts[i][0])), int(round(trail_pts[i][1])))
                alpha = float(i) / float(n_pts)
                # Cyan-to-yellow gradient trail
                color = (int(255 * (1.0 - alpha * 0.5)), int(200 * alpha), int(50 * (1.0 - alpha)))
                cv2.line(display, p1, p2, color, 1, cv2.LINE_AA)
                radius = max(1, int(round(alpha * 3.0)))
                cv2.circle(display, p2, radius, color, -1)

            # Draw velocity vector arrow if moving
            last_pt = trail_pts[-1]
            lookback = min(5, n_pts - 1)
            prev_pt = trail_pts[-1 - lookback]
            vx = (last_pt[0] - prev_pt[0])
            vy = (last_pt[1] - prev_pt[1])
            vel_mag = (vx**2 + vy**2)**0.5
            if vel_mag > 1.0:
                arrow_scale = min(30.0, vel_mag * 3.0) / vel_mag
                tip = (
                    int(round(last_pt[0] + vx * arrow_scale)),
                    int(round(last_pt[1] + vy * arrow_scale)),
                )
                cv2.arrowedLine(
                    display,
                    (int(round(last_pt[0])), int(round(last_pt[1]))),
                    tip,
                    (0, 255, 255),  # Yellow arrow
                    1,
                    cv2.LINE_AA,
                    tipLength=0.35,
                )

        # 3. Draw Estimated Track (Red crosshair and circle)
        if (
            state.estimated_centroid_x is not None
            and state.estimated_centroid_y is not None
            and is_tracking_state
        ):
            tx_int = int(round(state.estimated_centroid_x))
            ty_int = int(round(state.estimated_centroid_y))
            color = (0, 0, 255) # Red for active track
            
            # Draw crosshair
            length = 10
            cv2.line(display, (tx_int - length, ty_int), (tx_int + length, ty_int), color, 1)
            cv2.line(display, (tx_int, ty_int - length), (tx_int, ty_int + length), color, 1)
            cv2.circle(display, (tx_int, ty_int), 5, color, 1)

        # 4. Draw Ground Truth if available (Debug Mode)
        if state.ground_truth_x is not None and state.ground_truth_y is not None:
            gx = int(round(state.ground_truth_x))
            gy = int(round(state.ground_truth_y))
            cv2.drawMarker(display, (gx, gy), (0, 255, 0), markerType=cv2.MARKER_SQUARE, markerSize=8, thickness=1)

        # 5. Draw Center Reticle (Camera Aim)
        cx, cy = w // 2, h // 2
        cv2.line(display, (cx - 15, cy), (cx + 15, cy), (255, 255, 255), 1)
        cv2.line(display, (cx, cy - 15), (cx, cy + 15), (255, 255, 255), 1)

        # 6. Draw HUD Text
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

        if state.pan_angle_deg is not None and state.tilt_angle_deg is not None:
            put_text(f"PTZ: P {state.pan_angle_deg:+.2f}deg / T {state.tilt_angle_deg:+.2f}deg", (200, 200, 200))

        # Speed and PTZ actuation indicators
        if getattr(state, "ptz_enabled", True):
            put_text("PTZ ACTUATION: HOLD CENTER", (0, 220, 100))
        else:
            put_text("PTZ ACTUATION: OFF (FREE SWEEP)", (0, 165, 255))

        if getattr(state, "target_speed_px_s", None) is not None:
            put_text(f"TARGET SPEED: {state.target_speed_px_s:.1f} px/s", (255, 220, 80))

        return display
