"""
3D Visualization View — Module 19 (Visualization-Only Layer).
Per Architecture v1.2 and Operating Contract §L:
  - Consumes shared VisualizationState.
  - Strictly VISUALIZATION-ONLY: No independent physics, tracking, or camera simulation.
  - Renders 3D terminal geometry:
      * Ground grid & spatial reference frame
      * Virtual optical terminal / PTZ gimbal mount
      * Camera optical axis & 3D FOV viewing frustum
      * Target beacon position & line-of-sight ray
      * Historical tracking trajectory breadcrumbs
  - Interactive orbit/zoom/pan controls via QPainter 3D projection.
  - 100% portable: zero GPU/OpenGL driver crash risk on virtualized or headless displays.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple
import numpy as np

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

from src.frame.data_contracts import VisualizationState


class View3DWidget(QWidget):
    """
    3D Geometric Visualization Widget.
    Projects 3D terminal and target coordinates into an interactive perspective viewport.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

        # Orbit camera parameters
        self._cam_azimuth_deg = 35.0      # Orbit angle around vertical axis
        self._cam_elevation_deg = 25.0    # Orbit angle above ground plane
        # Keep the complete normalized line-of-sight envelope in view, even
        # when the tracked target moves to an extreme pan/tilt direction.
        self._cam_distance = 1100.0       # View distance
        self._cam_target = np.array([0.0, 0.0, 150.0], dtype=np.float32)

        # Mouse interaction state
        self._last_mouse_pos = None
        self._is_orbiting = False
        self._is_panning = False

        # Current visualization state
        self._current_state: Optional[VisualizationState] = None
        self._trajectory_history: List[np.ndarray] = []
        self._max_history = 60

        # Colors & styling
        self._bg_color = QColor(18, 22, 28)
        self._grid_color = QColor(45, 55, 72)
        self._axis_x_color = QColor(220, 60, 60)
        self._axis_y_color = QColor(60, 180, 75)
        self._axis_z_color = QColor(60, 120, 240)
        self._frustum_color = QColor(0, 220, 220, 140)
        self._optical_axis_color = QColor(255, 220, 0, 200)
        self._target_color = QColor(255, 60, 60)
        self._target_trail_color = QColor(255, 140, 60, 120)
        self._los_color = QColor(0, 255, 128, 160)

    def update_state(self, state: VisualizationState) -> None:
        """Slot to receive updated VisualizationState from backend/VideoWidget."""
        self._current_state = state

        # Compute 3D target position from pan/tilt and estimated error or ground truth
        # In FSOC terminal geometry:
        # Camera is at (0, 0, 0) looking along +Z with Pan (about Y) and Tilt (about X)
        range_est = 400.0  # Normalized nominal visual range in 3D scene
        pan_rad = math.radians(state.pan_angle_deg)
        tilt_rad = math.radians(state.tilt_angle_deg)

        # Target 3D position in terminal frame
        # Use the actual tracker estimate to place the beacon on its observed
        # line of sight. Ground truth is a visualization-only fallback while
        # the tracker has not acquired a measurement.
        target_x = state.estimated_centroid_x
        target_y = state.estimated_centroid_y
        if target_x is None or target_y is None:
            target_x = state.ground_truth_x
            target_y = state.ground_truth_y

        if target_x is not None and target_y is not None:
            width = max(1, int(state.camera_width))
            height = max(1, int(state.camera_height))
            fov_h = math.radians(state.camera_fov)
            fov_v = math.radians(state.camera_fov_v or state.camera_fov * height / width)
            dx_rad = (target_x - width / 2.0) * fov_h / width
            dy_rad = (target_y - height / 2.0) * fov_v / height
            
            tot_pan = pan_rad + dx_rad
            tot_tilt = tilt_rad - dy_rad
        else:
            tot_pan = pan_rad
            tot_tilt = tilt_rad

        tx = range_est * math.sin(tot_pan) * math.cos(tot_tilt)
        ty = range_est * math.sin(tot_tilt)
        tz = range_est * math.cos(tot_pan) * math.cos(tot_tilt)

        pos_3d = np.array([tx, ty, tz], dtype=np.float32)
        self._trajectory_history.append(pos_3d)
        if len(self._trajectory_history) > self._max_history:
            self._trajectory_history.pop(0)

        self.update()

    def reset_view(self) -> None:
        """Reset orbit view angles to default."""
        self._cam_azimuth_deg = 35.0
        self._cam_elevation_deg = 25.0
        self._cam_distance = 1100.0
        self._cam_target = np.array([0.0, 0.0, 150.0], dtype=np.float32)
        self._trajectory_history.clear()
        self.update()

    # -------------------------------------------------------------------------
    # Mouse Interaction
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_orbiting = True
            self._last_mouse_pos = event.position()
        elif event.button() == Qt.RightButton:
            self._is_panning = True
            self._last_mouse_pos = event.position()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_orbiting = False
        elif event.button() == Qt.RightButton:
            self._is_panning = False

    def mouseMoveEvent(self, event):
        if self._last_mouse_pos is None:
            return
        delta = event.position() - self._last_mouse_pos
        self._last_mouse_pos = event.position()

        if self._is_orbiting:
            self._cam_azimuth_deg = (self._cam_azimuth_deg + delta.x() * 0.5) % 360.0
            self._cam_elevation_deg = max(-85.0, min(85.0, self._cam_elevation_deg - delta.y() * 0.5))
            self.update()
        elif self._is_panning:
            factor = self._cam_distance * 0.002
            self._cam_target[0] -= delta.x() * factor
            self._cam_target[1] += delta.y() * factor
            self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        zoom_factor = 0.9 if delta > 0 else 1.1
        self._cam_distance = max(100.0, min(2000.0, self._cam_distance * zoom_factor))
        self.update()

    # -------------------------------------------------------------------------
    # 3D Math & Projection
    # -------------------------------------------------------------------------
    def _project_point(self, p: np.ndarray, w: int, h: int) -> Optional[QPointF]:
        """Projects a 3D world coordinate [x, y, z] to 2D viewport coordinates."""
        # Translate relative to camera target
        p_rel = p - self._cam_target

        # Orbit angles in radians
        az = math.radians(self._cam_azimuth_deg)
        el = math.radians(self._cam_elevation_deg)

        # Eye position in spherical coordinates
        cos_el = math.cos(el)
        sin_el = math.sin(el)
        cos_az = math.cos(az)
        sin_az = math.sin(az)

        # Eye vector
        eye = np.array([
            self._cam_distance * cos_el * sin_az,
            self._cam_distance * sin_el,
            self._cam_distance * cos_el * cos_az,
        ], dtype=np.float32)

        # View matrix basis vectors: Forward, Right, Up
        fwd = -eye / np.linalg.norm(eye)
        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        right = np.cross(world_up, -fwd)
        norm_r = np.linalg.norm(right)
        if norm_r < 1e-4:
            right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        else:
            right = right / norm_r
        up = np.cross(-fwd, right)

        # Vector from eye to point
        to_pt = p_rel - eye
        # Project onto camera basis
        cam_z = np.dot(to_pt, fwd)
        if cam_z <= 10.0:  # Behind camera near-plane
            return None

        cam_x = np.dot(to_pt, right)
        cam_y = np.dot(to_pt, up)

        # Perspective projection
        fov_rad = math.radians(45.0)
        focal = (h / 2.0) / math.tan(fov_rad / 2.0)

        screen_x = w / 2.0 + (cam_x / cam_z) * focal
        screen_y = h / 2.0 - (cam_y / cam_z) * focal

        return QPointF(screen_x, screen_y)

    # -------------------------------------------------------------------------
    # Painting
    # -------------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # 1. Fill background
        painter.fillRect(0, 0, w, h, self._bg_color)

        # 2. Draw ground grid
        self._draw_grid(painter, w, h)

        # 3. Draw world coordinate axes
        self._draw_axes(painter, w, h)

        # 4. Draw virtual terminal / camera gimbal and FOV frustum
        if self._current_state is not None:
            self._draw_terminal_and_frustum(painter, w, h, self._current_state)

        # 5. Draw target beacon & trajectory
        self._draw_target(painter, w, h)

        # 6. Draw 3D HUD overlay
        self._draw_hud(painter, w, h)

    def _draw_grid(self, painter: QPainter, w: int, h: int) -> None:
        pen = QPen(self._grid_color, 1, Qt.DotLine)
        painter.setPen(pen)

        grid_size = 400.0
        step = 50.0
        for i in range(-8, 9):
            pos = i * step
            # Lines along Z
            p1 = self._project_point(np.array([pos, 0.0, -grid_size]), w, h)
            p2 = self._project_point(np.array([pos, 0.0, grid_size]), w, h)
            if p1 and p2:
                painter.drawLine(p1, p2)

            # Lines along X
            p3 = self._project_point(np.array([-grid_size, 0.0, pos]), w, h)
            p4 = self._project_point(np.array([grid_size, 0.0, pos]), w, h)
            if p3 and p4:
                painter.drawLine(p3, p4)

    def _draw_axes(self, painter: QPainter, w: int, h: int) -> None:
        origin = self._project_point(np.array([0.0, 0.0, 0.0]), w, h)
        if not origin:
            return

        axis_len = 60.0
        # X-axis (Red)
        px = self._project_point(np.array([axis_len, 0.0, 0.0]), w, h)
        if px:
            painter.setPen(QPen(self._axis_x_color, 2))
            painter.drawLine(origin, px)

        # Y-axis (Green - Up)
        py = self._project_point(np.array([0.0, axis_len, 0.0]), w, h)
        if py:
            painter.setPen(QPen(self._axis_y_color, 2))
            painter.drawLine(origin, py)

        # Z-axis (Blue - Forward)
        pz = self._project_point(np.array([0.0, 0.0, axis_len]), w, h)
        if pz:
            painter.setPen(QPen(self._axis_z_color, 2))
            painter.drawLine(origin, pz)

    def _draw_terminal_and_frustum(self, painter: QPainter, w: int, h: int, state: VisualizationState) -> None:
        # Terminal pedestal
        base_origin = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        mount_top = np.array([0.0, 20.0, 0.0], dtype=np.float32)
        p_base = self._project_point(base_origin, w, h)
        p_mount = self._project_point(mount_top, w, h)
        if p_base and p_mount:
            painter.setPen(QPen(QColor(100, 110, 130), 4))
            painter.drawLine(p_base, p_mount)
            painter.setBrush(QBrush(QColor(80, 90, 110)))
            painter.drawEllipse(p_mount, 5, 5)

        # Pan/Tilt rotation angles
        pan_rad = math.radians(state.pan_angle_deg)
        tilt_rad = math.radians(state.tilt_angle_deg)
        fov_rad = math.radians(state.camera_fov)

        # Optical axis vector from mount
        frustum_len = 250.0
        dir_x = math.sin(pan_rad) * math.cos(tilt_rad)
        dir_y = math.sin(tilt_rad)
        dir_z = math.cos(pan_rad) * math.cos(tilt_rad)
        optical_axis_pt = mount_top + np.array([dir_x, dir_y, dir_z], dtype=np.float32) * frustum_len

        # Frustum corner half-widths at frustum_len
        half_w = frustum_len * math.tan(fov_rad / 2.0)
        fov_v_deg = state.camera_fov_v or state.camera_fov * 480.0 / 640.0
        half_h = frustum_len * math.tan(math.radians(fov_v_deg) / 2.0)

        # Local coordinate basis at aperture
        fwd = np.array([dir_x, dir_y, dir_z], dtype=np.float32)
        up_nom = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        right = np.cross(up_nom, fwd)
        norm_r = np.linalg.norm(right)
        right = right / norm_r if norm_r > 1e-4 else np.array([1.0, 0.0, 0.0], dtype=np.float32)
        up = np.cross(fwd, right)

        center_pt = mount_top + fwd * frustum_len
        c1 = center_pt - right * half_w + up * half_h
        c2 = center_pt + right * half_w + up * half_h
        c3 = center_pt + right * half_w - up * half_h
        c4 = center_pt - right * half_w - up * half_h

        # Project points
        p_aperture = self._project_point(mount_top, w, h)
        p_axis = self._project_point(optical_axis_pt, w, h)
        pc1 = self._project_point(c1, w, h)
        pc2 = self._project_point(c2, w, h)
        pc3 = self._project_point(c3, w, h)
        pc4 = self._project_point(c4, w, h)

        if p_aperture and p_axis:
            # Draw optical axis
            painter.setPen(QPen(self._optical_axis_color, 2, Qt.DashLine))
            painter.drawLine(p_aperture, p_axis)

        # Draw Frustum Wireframe & Semi-transparent Far Plane
        if pc1 and pc2 and pc3 and pc4 and p_aperture:
            # Frustum rays
            painter.setPen(QPen(self._frustum_color, 1))
            painter.drawLine(p_aperture, pc1)
            painter.drawLine(p_aperture, pc2)
            painter.drawLine(p_aperture, pc3)
            painter.drawLine(p_aperture, pc4)

            # Far rectangle
            poly = QPolygonF([pc1, pc2, pc3, pc4])
            painter.setBrush(QBrush(QColor(0, 200, 220, 25)))
            painter.drawPolygon(poly)

    def _draw_target(self, painter: QPainter, w: int, h: int) -> None:
        if not self._trajectory_history:
            return

        # Draw trajectory breadcrumbs
        if len(self._trajectory_history) > 1:
            painter.setPen(QPen(self._target_trail_color, 2))
            for i in range(len(self._trajectory_history) - 1):
                p1 = self._project_point(self._trajectory_history[i], w, h)
                p2 = self._project_point(self._trajectory_history[i + 1], w, h)
                if p1 and p2:
                    painter.drawLine(p1, p2)

        # Draw current target point
        curr_pos = self._trajectory_history[-1]
        p_tgt = self._project_point(curr_pos, w, h)
        if p_tgt:
            painter.setPen(QPen(Qt.white, 1))
            painter.setBrush(QBrush(self._target_color))
            painter.drawEllipse(p_tgt, 6, 6)

            # Draw Line-of-Sight to camera aperture
            p_aperture = self._project_point(np.array([0.0, 20.0, 0.0]), w, h)
            if p_aperture:
                painter.setPen(QPen(self._los_color, 1, Qt.DotLine))
                painter.drawLine(p_aperture, p_tgt)

    def _draw_hud(self, painter: QPainter, w: int, h: int) -> None:
        painter.setPen(QColor(200, 210, 225))
        painter.setFont(QFont("Consolas", 9))

        lines = [
            "3D GEOMETRIC SCENE (SYNCHRONIZED VIEW)",
            f"Orbit: Az {self._cam_azimuth_deg:.0f}°, El {self._cam_elevation_deg:.0f}° | Dist: {self._cam_distance:.0f}",
        ]

        if self._current_state:
            st = self._current_state
            lines.append(f"PTZ: Pan {st.pan_angle_deg:+.2f}° | Tilt {st.tilt_angle_deg:+.2f}° | FOV: {st.camera_fov:.1f}°")
            lines.append(f"State: {st.tracking_state}")

        lines.append("[Left-Drag: Orbit | Right-Drag: Pan | Scroll: Zoom]")

        y = 20
        for line in lines:
            painter.drawText(15, y, line)
            y += 18
