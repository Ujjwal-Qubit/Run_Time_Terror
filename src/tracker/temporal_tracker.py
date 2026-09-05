"""
Temporal Tracker — Module 12 per Architecture v1.2 §8.2 Stage 6.

P0 Baseline Tracking Algorithm:
  Constant-Velocity Kalman Filter (CV-KF)

State Vector:
  x = [x, y, v_x, v_y]^T
  - Position: sub-pixel floating-point coordinates (px).
  - Velocity: sub-pixel velocity (px/s).

Process Model:
  x_{k+1} = F * x_k + w_k
  F = [[1, 0, dt,  0],
       [0, 1,  0, dt],
       [0, 0,  1,  0],
       [0, 0,  0,  1]]

Measurement Model:
  z_k = H * x_k + v_k
  H = [[1, 0, 0, 0],
       [0, 1, 0, 0]]

Features:
  - Timestamp-derived adaptive dt with bounds checking.
  - Sub-pixel coordinate preservation (never integer quantized).
  - Euclidean innovation/residual distance gating (||y||_2 <= gate_max_distance) to reject spatial outliers.
  - Joseph-form covariance update for numerical stability.
  - Support for coasting / predict-only on missing measurements.
  - Adaptive ROI generation for downstream stages.

FIREWALL ENFORCEMENT:
  Has ZERO access to GroundTruth, GroundTruthProvider, or simulator internals.
  Consumes exclusively CentroidResult and frame timing.
"""

from __future__ import annotations

import math
import time
from typing import Optional, Tuple

import numpy as np

from src.interfaces.strategy_interfaces import ITracker
from src.frame.data_contracts import (
    CentroidResult,
    TrackResult,
    ROI,
)
from src.config.config_manager import TrackerConfig
from src.config import defaults


class ConstantVelocityKalmanTracker(ITracker):
    """
    Constant-Velocity Kalman Tracker (Module 12 - P0 Baseline).
    """

    def __init__(self, config: Optional[TrackerConfig] = None) -> None:
        cfg = config or TrackerConfig()
        self._cfg = cfg

        # Filter parameters
        self._q_pos = cfg.process_noise_pos
        self._q_vel = cfg.process_noise_vel
        self._r_noise = cfg.measurement_noise
        self._p_init_pos = getattr(cfg, "initial_covariance_pos", defaults.KALMAN_INITIAL_COVARIANCE_POS)
        self._p_init_vel = getattr(cfg, "initial_covariance_vel", defaults.KALMAN_INITIAL_COVARIANCE_VEL)
        self._gate_max_dist = cfg.gate_max_distance

        # Adaptive ROI parameters
        self._roi_min = cfg.roi_min_size
        self._roi_max = cfg.roi_max_size
        self._roi_margin_factor = cfg.roi_margin_factor

        # Measurement matrix H (2 x 4)
        self._H = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ], dtype=np.float64)

        # Measurement noise covariance R (2 x 2)
        self._R = np.eye(2, dtype=np.float64) * (self._r_noise ** 2)

        # Identity matrix I (4 x 4)
        self._I = np.eye(4, dtype=np.float64)

        # Filter state
        self._x = np.zeros((4, 1), dtype=np.float64)
        self._P = np.eye(4, dtype=np.float64)
        self._is_initialized = False
        self._track_age = 0
        self._last_timestamp: Optional[float] = None
        self._nominal_dt = 1.0 / 30.0

    @property
    def config(self) -> TrackerConfig:
        return self._cfg

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    @property
    def track_age(self) -> int:
        return self._track_age

    @property
    def state_vector(self) -> np.ndarray:
        return self._x.copy()

    @property
    def covariance(self) -> np.ndarray:
        return self._P.copy()

    def get_name(self) -> str:
        return "ConstantVelocityKalmanTracker"

    def reset(self) -> None:
        """Reset filter state to uninitialized."""
        self._x = np.zeros((4, 1), dtype=np.float64)
        self._P = np.eye(4, dtype=np.float64)
        self._is_initialized = False
        self._track_age = 0
        self._last_timestamp = None

    def _build_f_matrix(self, dt: float) -> np.ndarray:
        """Construct state transition matrix F(dt)."""
        F = np.eye(4, dtype=np.float64)
        F[0, 2] = dt
        F[1, 3] = dt
        return F

    def _build_q_matrix(self, dt: float) -> np.ndarray:
        """
        Construct process noise covariance matrix Q(dt).
        Continuous white noise acceleration model:
          Q_pos = q_pos * [[dt^3/3, dt^2/2], [dt^2/2, dt]]
        """
        dt2 = dt * dt
        dt3 = dt2 * dt

        q11 = (dt3 / 3.0) * self._q_pos
        q12 = (dt2 / 2.0) * self._q_pos
        q22 = dt * self._q_vel

        Q = np.zeros((4, 4), dtype=np.float64)
        # Position-velocity block for X
        Q[0, 0] = q11
        Q[0, 2] = q12
        Q[2, 0] = q12
        Q[2, 2] = q22

        # Position-velocity block for Y
        Q[1, 1] = q11
        Q[1, 3] = q12
        Q[3, 1] = q12
        Q[3, 3] = q22

        return Q

    def _resolve_dt(
        self,
        dt_param: float,
        timestamp: float,
    ) -> float:
        """
        Compute effective dt using incoming timestamps with safe bounding.
        """
        if self._last_timestamp is not None and timestamp > 0.0:
            computed_dt = timestamp - self._last_timestamp
            if computed_dt > 0.0:
                # Normal positive elapsed time
                dt = min(1.0, computed_dt)
            elif abs(computed_dt) < 1e-6:
                # Repeated timestamp: use tiny positive step to avoid singular covariance
                dt = 1e-4
            else:
                # Non-monotonic timestamp: fallback
                dt = self._nominal_dt
        elif dt_param > 0.0:
            dt = min(1.0, dt_param)
        else:
            dt = self._nominal_dt

        if timestamp > 0.0:
            self._last_timestamp = timestamp

        return float(dt)

    def update(
        self,
        centroid: Optional[CentroidResult],
        dt: float = 0.0,
        frame_number: int = 0,
        timestamp: float = 0.0,
    ) -> TrackResult:
        """
        Perform Kalman prediction and measurement update.

        Args:
            centroid: Observed sub-pixel centroid, or None if no detection.
            dt: Optional explicit time step in seconds.
            frame_number: Optional frame number.
            timestamp: Optional measurement timestamp.

        Returns:
            TrackResult containing filtered state, velocities, and diagnostics.
        """
        t0 = time.perf_counter()

        # Extract timing from centroid if available
        if centroid is not None:
            if frame_number == 0 and centroid.frame_number > 0:
                frame_number = centroid.frame_number
            if timestamp == 0.0 and centroid.timestamp > 0.0:
                timestamp = centroid.timestamp

        effective_dt = self._resolve_dt(dt, timestamp)

        # -------------------------------------------------------------------
        # 1. Initialization on First Valid Measurement
        # -------------------------------------------------------------------
        has_valid_measurement = (centroid is not None and centroid.valid)

        if not self._is_initialized:
            if has_valid_measurement and centroid is not None:
                self._x[0, 0] = float(centroid.x)
                self._x[1, 0] = float(centroid.y)
                self._x[2, 0] = 0.0
                self._x[3, 0] = 0.0

                self._P = np.diag([
                    self._p_init_pos,
                    self._p_init_pos,
                    self._p_init_vel,
                    self._p_init_vel,
                ]).astype(np.float64)

                self._is_initialized = True
                self._track_age = 1

                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return TrackResult(
                    estimated_x=float(centroid.x),
                    estimated_y=float(centroid.y),
                    velocity_x=0.0,
                    velocity_y=0.0,
                    confidence=1.0,
                    track_age=1,
                    predicted_x=float(centroid.x),
                    predicted_y=float(centroid.y),
                    frame_number=frame_number,
                    timestamp=timestamp,
                    measurement_valid=True,
                    measurement_accepted=True,
                    innovation_x=0.0,
                    innovation_y=0.0,
                    innovation_distance=0.0,
                    is_coasting=False,
                    status="INITIALIZED",
                    processing_time_ms=elapsed_ms,
                )
            else:
                # Uninitialized and no measurement
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return TrackResult(
                    estimated_x=0.0,
                    estimated_y=0.0,
                    velocity_x=0.0,
                    velocity_y=0.0,
                    confidence=0.0,
                    track_age=0,
                    predicted_x=0.0,
                    predicted_y=0.0,
                    frame_number=frame_number,
                    timestamp=timestamp,
                    measurement_valid=False,
                    measurement_accepted=False,
                    innovation_x=0.0,
                    innovation_y=0.0,
                    innovation_distance=0.0,
                    is_coasting=True,
                    status="UNINITIALIZED",
                    processing_time_ms=elapsed_ms,
                )

        # -------------------------------------------------------------------
        # 2. Prediction Step
        # -------------------------------------------------------------------
        F = self._build_f_matrix(effective_dt)
        Q = self._build_q_matrix(effective_dt)

        x_prior = F @ self._x
        P_prior = F @ self._P @ F.T + Q

        # -------------------------------------------------------------------
        # 3. Measurement Gating & Update
        # -------------------------------------------------------------------
        accepted = False
        innov_x = 0.0
        innov_y = 0.0
        innov_dist = 0.0

        if has_valid_measurement and centroid is not None:
            z = np.array([[centroid.x], [centroid.y]], dtype=np.float64)

            # Innovation (residual)
            y = z - self._H @ x_prior
            innov_x = float(y[0, 0])
            innov_y = float(y[1, 0])
            innov_dist = math.hypot(innov_x, innov_y)

            # Innovation covariance S
            S = self._H @ P_prior @ self._H.T + self._R

            # Euclidean innovation/residual distance gate check
            # For young tracks (age <= 2), allow wider gate to lock onto target velocity
            effective_gate = self._gate_max_dist * 2.0 if self._track_age <= 2 else self._gate_max_dist

            if innov_dist <= effective_gate:
                # Measurement Accepted -> Kalman Update
                accepted = True
                S_inv = np.linalg.inv(S)
                K = P_prior @ self._H.T @ S_inv

                # Updated state
                self._x = x_prior + K @ y

                # Joseph-form covariance update: P = (I - K H) P_prior (I - K H)^T + K R K^T
                IKH = self._I - K @ self._H
                self._P = IKH @ P_prior @ IKH.T + K @ self._R @ K.T
                # Enforce symmetry
                self._P = 0.5 * (self._P + self._P.T)
                self._track_age += 1
            else:
                # Measurement Rejected as Outlier -> Coast on Prediction
                accepted = False
                self._x = x_prior
                self._P = P_prior
        else:
            # Missing Measurement -> Coast on Prediction
            accepted = False
            self._x = x_prior
            self._P = P_prior

        # -------------------------------------------------------------------
        # 4. Next Frame Prediction
        # -------------------------------------------------------------------
        pred_x = float(self._x[0, 0] + self._x[2, 0] * self._nominal_dt)
        pred_y = float(self._x[1, 0] + self._x[3, 0] * self._nominal_dt)

        # Confidence: scales with measurement status and covariance
        pos_var = float(self._P[0, 0] + self._P[1, 1])
        conf = float(math.exp(-0.5 * pos_var / 100.0))
        if not accepted:
            conf *= 0.8

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        status_str = "TRACKING" if accepted else ("COASTING" if self._is_initialized else "LOST")

        return TrackResult(
            estimated_x=float(self._x[0, 0]),
            estimated_y=float(self._x[1, 0]),
            velocity_x=float(self._x[2, 0]),
            velocity_y=float(self._x[3, 0]),
            confidence=float(min(1.0, max(0.0, conf))),
            track_age=self._track_age,
            predicted_x=pred_x,
            predicted_y=pred_y,
            frame_number=frame_number,
            timestamp=timestamp,
            measurement_valid=has_valid_measurement,
            measurement_accepted=accepted,
            innovation_x=innov_x,
            innovation_y=innov_y,
            innovation_distance=innov_dist,
            is_coasting=not accepted,
            status=status_str,
            processing_time_ms=elapsed_ms,
        )

    def predict(self) -> Tuple[float, float]:
        """
        Return the predicted position for the next frame.
        """
        if not self._is_initialized:
            return (0.0, 0.0)
        pred_x = float(self._x[0, 0] + self._x[2, 0] * self._nominal_dt)
        pred_y = float(self._x[1, 0] + self._x[3, 0] * self._nominal_dt)
        return (pred_x, pred_y)

    def get_roi(self, frame_width: int, frame_height: int) -> ROI:
        """
        Compute the adaptive ROI for the next frame based on prediction and speed.
        """
        if not self._is_initialized:
            return ROI(x=0, y=0, width=frame_width, height=frame_height)

        pred_x, pred_y = self.predict()
        speed = math.hypot(float(self._x[2, 0]), float(self._x[3, 0]))

        # Scale ROI size with target velocity
        dynamic_size = self._roi_min + speed * self._nominal_dt * self._roi_margin_factor * 2.0
        roi_size = int(max(self._roi_min, min(self._roi_max, dynamic_size)))

        half = roi_size // 2
        x0 = max(0, min(frame_width - roi_size, int(pred_x - half)))
        y0 = max(0, min(frame_height - roi_size, int(pred_y - half)))

        return ROI(x=x0, y=y0, width=roi_size, height=roi_size)


# Production aliases
TemporalTracker = ConstantVelocityKalmanTracker
TrackingEngine = ConstantVelocityKalmanTracker
KalmanTracker = ConstantVelocityKalmanTracker
