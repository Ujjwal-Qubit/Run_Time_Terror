"""
Temporal Predictor — Module for temporal beacon motion prediction per Spec §5.3, §5.4 & §7.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
import json
import os
import time
from typing import Deque, List, Optional, Tuple
import numpy as np

from src.aiml.contracts import PredictionRequest, PredictionResult, TrackObservation
from src.aiml.fallback_policy import FallbackPolicy


class ITemporalPredictor(ABC):
    """
    Abstract interface for temporal predictors.
    """

    @abstractmethod
    def predict(self, request: PredictionRequest) -> PredictionResult:
        """Predict next frame position from PredictionRequest."""
        ...

    @abstractmethod
    def update(self, observation: TrackObservation) -> None:
        """Update predictor internal state with new observation."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset predictor state and clear history buffer."""
        ...


class BoundedHistoryBuffer:
    """
    Memory-safe ring buffer storing up to maxlen compact TrackObservation elements.
    Never retains complete FramePacket, image arrays, or simulator scenes.
    """

    def __init__(self, maxlen: int = 32) -> None:
        self.maxlen = maxlen
        self._buffer: Deque[TrackObservation] = deque(maxlen=maxlen)

    def append(self, obs: TrackObservation) -> None:
        self._buffer.append(obs)

    def clear(self) -> None:
        self._buffer.clear()

    def get_history(self) -> Tuple[TrackObservation, ...]:
        return tuple(self._buffer)


    def __len__(self) -> int:
        return len(self._buffer)


class KalmanPredictor(ITemporalPredictor):
    """
    Deterministic Constant Velocity Kalman Filter predictor baseline.
    """

    def __init__(self, history_length: int = 20) -> None:
        self.history = BoundedHistoryBuffer(maxlen=history_length)
        self._last_x: float = 0.0
        self._last_y: float = 0.0
        self._vx: float = 0.0
        self._vy: float = 0.0
        self._is_initialized = False
        self._last_observation_timestamp: Optional[float] = None

    def update(self, obs: TrackObservation) -> None:
        self.history.append(obs)
        if obs.measurement_accepted and obs.x is not None and obs.y is not None:
            if not self._is_initialized:
                self._last_x = obs.x
                self._last_y = obs.y
                self._vx = 0.0
                self._vy = 0.0
                self._is_initialized = True
            else:
                previous_timestamp = self._last_observation_timestamp
                dt = (
                    max(0.001, obs.timestamp - previous_timestamp)
                    if previous_timestamp is not None
                    else 0.033
                )
                # Simple alpha-beta update
                self._vx = 0.6 * self._vx + 0.4 * ((obs.x - self._last_x) / dt)
                self._vy = 0.6 * self._vy + 0.4 * ((obs.y - self._last_y) / dt)
                self._last_x = obs.x
                self._last_y = obs.y
            self._last_observation_timestamp = obs.timestamp

    def predict(self, request: PredictionRequest) -> PredictionResult:
        t0 = time.perf_counter()
        dt = request.horizon_seconds if request.horizon_seconds > 0 else 0.033

        if not self._is_initialized:
            # Fallback zero-order
            px = request.frame_width / 2.0
            py = request.frame_height / 2.0
            return PredictionResult(
                frame_number=request.frame_number,
                timestamp=request.timestamp,
                predicted_x=px,
                predicted_y=py,
                predicted_vx=0.0,
                predicted_vy=0.0,
                uncertainty_x=50.0,
                uncertainty_y=50.0,
                confidence=0.1,
                horizon_seconds=dt,
                model_name="KalmanBaseline",
                model_version="v1.0",
                used_fallback=True,
                fallback_reason="Predictor uninitialized",
                inference_time_ms=(time.perf_counter() - t0) * 1000.0,
            )

        pred_x = self._last_x + self._vx * dt
        pred_y = self._last_y + self._vy * dt

        return PredictionResult(
            frame_number=request.frame_number,
            timestamp=request.timestamp,
            predicted_x=float(pred_x),
            predicted_y=float(pred_y),
            predicted_vx=float(self._vx),
            predicted_vy=float(self._vy),
            uncertainty_x=5.0,
            uncertainty_y=5.0,
            confidence=0.85,
            horizon_seconds=dt,
            model_name="KalmanBaseline",
            model_version="v1.0",
            used_fallback=False,
            fallback_reason=None,
            inference_time_ms=(time.perf_counter() - t0) * 1000.0,
        )

    def reset(self) -> None:
        self.history.clear()
        self._is_initialized = False
        self._last_x = 0.0
        self._last_y = 0.0
        self._vx = 0.0
        self._vy = 0.0
        self._last_observation_timestamp = None


class ResidualCorrectionPredictor(ITemporalPredictor):
    """
    Robust Kalman baseline + learned residual displacement correction (MLP).
    Per Spec §14 (Recommended architecture for temporal prediction).
    """

    def __init__(
        self,
        model_dir: str = "models/temporal_predictor/v001",
        kalman_baseline: Optional[KalmanPredictor] = None,
    ) -> None:
        self.model_dir = model_dir
        self.baseline = kalman_baseline or KalmanPredictor()
        self.history = self.baseline.history
        self._weights_h: Optional[np.ndarray] = None
        self._bias_h: Optional[np.ndarray] = None
        self._weights_o: Optional[np.ndarray] = None
        self._bias_o: Optional[np.ndarray] = None
        self._input_mean = np.zeros(3, dtype=np.float32)
        self._input_std = np.ones(3, dtype=np.float32)
        self.is_loaded = False

        self._load_weights()

    def _load_weights(self) -> None:
        model_path = os.path.join(self.model_dir, "model.json")
        if os.path.exists(model_path):
            try:
                with open(model_path, "r") as f:
                    data = json.load(f)
                    self._weights_h = np.array(data["weights_h"], dtype=np.float32)
                    self._bias_h = np.array(data["bias_h"], dtype=np.float32)
                    self._weights_o = np.array(data["weights_o"], dtype=np.float32)
                    self._bias_o = np.array(data["bias_o"], dtype=np.float32)
                    self._input_mean = np.asarray(data.get("input_mean", [0.0, 0.0, 0.0]), dtype=np.float32)
                    self._input_std = np.asarray(data.get("input_std", [1.0, 1.0, 1.0]), dtype=np.float32)
                    self._input_std[self._input_std == 0.0] = 1.0
                    if (
                        self._weights_h.ndim != 2
                        or self._weights_h.shape[0] != 3
                        or self._bias_h.shape != (self._weights_h.shape[1],)
                        or self._weights_o.shape != (self._weights_h.shape[1], 2)
                        or self._bias_o.shape != (2,)
                        or self._input_mean.shape != (3,)
                        or self._input_std.shape != (3,)
                        or not all(np.isfinite(value).all() for value in (
                            self._weights_h, self._bias_h, self._weights_o,
                            self._bias_o, self._input_mean, self._input_std,
                        ))
                    ):
                        raise ValueError("Temporal model has invalid dimensions or non-finite parameters")
                    self.is_loaded = True
            except Exception as e:
                print(f"[ResidualCorrectionPredictor] Warning loading weights: {e}")

    def update(self, obs: TrackObservation) -> None:
        self.baseline.update(obs)

    def predict(self, request: PredictionRequest) -> PredictionResult:
        t0 = time.perf_counter()
        # Compute baseline prediction first
        base_res = self.baseline.predict(request)

        if not self.is_loaded or base_res.used_fallback:
            return base_res

        # Extract features for residual prediction
        history = request.history
        if len(history) < 3:
            return base_res

        try:
            valid_obs = [
                observation for observation in history
                if observation.measurement_accepted
                and observation.x is not None
                and observation.y is not None
            ]
            if len(valid_obs) < 2:
                return base_res

            # Predict residual (dx_residual, dy_residual)
            res_x = 0.0
            res_y = 0.0

            if self._weights_h is not None and self._weights_o is not None:
                feat = np.array(
                    [base_res.predicted_vx, base_res.predicted_vy, float(len(valid_obs))],
                    dtype=np.float32,
                )
                feat = (feat - self._input_mean) / self._input_std
                h_act = np.maximum(0, np.dot(feat, self._weights_h) + self._bias_h)
                out = np.dot(h_act, self._weights_o) + self._bias_o
                res_x = float(out[0])
                res_y = float(out[1])

            final_x = base_res.predicted_x + res_x
            final_y = base_res.predicted_y + res_y

            total_ms = (time.perf_counter() - t0) * 1000.0

            return PredictionResult(
                frame_number=request.frame_number,
                timestamp=request.timestamp,
                predicted_x=final_x,
                predicted_y=final_y,
                predicted_vx=base_res.predicted_vx,
                predicted_vy=base_res.predicted_vy,
                uncertainty_x=base_res.uncertainty_x,
                uncertainty_y=base_res.uncertainty_y,
                confidence=base_res.confidence,
                horizon_seconds=request.horizon_seconds,
                model_name="ResidualCorrectionPredictor",
                model_version="v001",
                used_fallback=False,
                fallback_reason=None,
                inference_time_ms=total_ms,
            )

        except Exception as e:
            print(f"[ResidualCorrectionPredictor] Exception: {e}. Falling back.")
            return base_res

    def reset(self) -> None:
        self.baseline.reset()
