"""
Tracking State Manager — Module 13 per Architecture v1.2 §8.2 Stage 7 and §10.1.

Manages the logical tracking state machine lifecycle:
  SEARCHING  → No track established. Looking for candidates.
  ACQUIRING  → Candidate detected; confirming stable lock across N_lock frames.
  TRACKING   → Stable beacon lock maintained with accepted measurements.
  REACQUIRING → Measurement temporarily missing; coasting on predictions up to N_loss frames.
  LOST       → Target unrecovered after N_loss frames; transitioning back to search.

Features:
  - Hysteresis and multi-frame confirmation to prevent state oscillation.
  - Transition timestamp logging for PS metric evaluation (acquisition time, reacquisition time).
  - Diagnostic counters for acquisition, loss, and reacquisition frames.

FIREWALL ENFORCEMENT:
  Has ZERO access to GroundTruth, GroundTruthProvider, or simulator internals.
  Consumes exclusively TrackResult observations and timing.
"""

from __future__ import annotations

import time
from typing import Optional, List, Tuple

from src.interfaces.strategy_interfaces import ITrackingStateManager
from src.frame.data_contracts import (
    TrackingState,
    TrackResult,
    TrackingStateResult,
)
from src.config.config_manager import StateConfig
from src.config import defaults


class TrackingStateManager(ITrackingStateManager):
    """
    Tracking State Manager (Module 13 - P0 Baseline).
    """

    def __init__(self, config: Optional[StateConfig] = None) -> None:
        cfg = config or StateConfig()
        self._cfg = cfg

        # Confirmation frame thresholds
        self._lock_confirm_frames = cfg.lock_confirm_frames
        self._loss_confirm_frames = cfg.loss_confirm_frames
        self._reacquire_confirm_frames = getattr(
            cfg, "reacquire_confirm_frames", defaults.STATE_REACQUIRE_CONFIRM_FRAMES
        )

        # State machine variables
        self._current_state = TrackingState.SEARCHING
        self._previous_state = TrackingState.SEARCHING
        self._is_locked = False
        self._transition_reason = "Initial state"

        # Frame counters
        self._acquisition_frames = 0
        self._loss_frames = 0
        self._reacquisition_frames = 0

        # Timing tracking
        self._state_start_time = 0.0
        self._acquisition_timestamp: Optional[float] = None
        self._lock_timestamp: Optional[float] = None
        self._acquisition_time: Optional[float] = None
        self._loss_timestamp: Optional[float] = None
        self._reacquisition_timestamp: Optional[float] = None
        self._reacquisition_time: Optional[float] = None

        # Transition history for diagnostics
        self._history: List[Tuple[float, TrackingState, TrackingState, str]] = []

    @property
    def current_state(self) -> TrackingState:
        return self._current_state

    @property
    def is_locked(self) -> bool:
        return self._is_locked

    @property
    def history(self) -> List[Tuple[float, TrackingState, TrackingState, str]]:
        return list(self._history)

    @property
    def acquisition_time(self) -> Optional[float]:
        return self._acquisition_time

    @property
    def reacquisition_time(self) -> Optional[float]:
        return self._reacquisition_time

    def get_name(self) -> str:
        return "TrackingStateManager"

    def reset(self) -> None:
        """Reset state machine to initial SEARCHING state."""
        self._current_state = TrackingState.SEARCHING
        self._previous_state = TrackingState.SEARCHING
        self._is_locked = False
        self._transition_reason = "Reset"
        self._acquisition_frames = 0
        self._loss_frames = 0
        self._reacquisition_frames = 0
        self._state_start_time = 0.0
        self._acquisition_timestamp = None
        self._lock_timestamp = None
        self._acquisition_time = None
        self._loss_timestamp = None
        self._reacquisition_timestamp = None
        self._reacquisition_time = None
        self._history.clear()

    def update(
        self,
        track_result: Optional[TrackResult],
        timestamp: float = 0.0,
    ) -> TrackingStateResult:
        """
        Evaluate tracking result and advance state machine.

        Args:
            track_result: Result from temporal tracker.
            timestamp: Frame timestamp in seconds.

        Returns:
            TrackingStateResult containing current state and diagnostic metrics.
        """
        t0 = time.perf_counter()

        # Extract timing and measurement status
        if track_result is not None:
            if timestamp == 0.0 and track_result.timestamp > 0.0:
                timestamp = track_result.timestamp
            frame_number = track_result.frame_number
            accepted = track_result.measurement_accepted
            conf = track_result.confidence
        else:
            frame_number = 0
            accepted = False
            conf = 0.0

        prev_state = self._current_state
        reason = ""

        # -------------------------------------------------------------------
        # State Machine Transitions
        # -------------------------------------------------------------------
        if self._current_state == TrackingState.SEARCHING:
            if accepted:
                self._acquisition_frames = 1
                self._acquisition_timestamp = timestamp
                if self._acquisition_frames >= self._lock_confirm_frames:
                    self._current_state = TrackingState.TRACKING
                    self._is_locked = True
                    self._lock_timestamp = timestamp
                    self._acquisition_time = 0.0
                    reason = f"Lock confirmed immediately (threshold={self._lock_confirm_frames})"
                else:
                    self._current_state = TrackingState.ACQUIRING
                    self._is_locked = False
                    reason = "Candidate detected; acquiring lock"
            else:
                self._acquisition_frames = 0
                self._is_locked = False

        elif self._current_state == TrackingState.ACQUIRING:
            if accepted:
                self._acquisition_frames += 1
                if self._acquisition_frames >= self._lock_confirm_frames:
                    self._current_state = TrackingState.TRACKING
                    self._is_locked = True
                    self._lock_timestamp = timestamp
                    if self._acquisition_timestamp is not None:
                        self._acquisition_time = max(0.0, self._lock_timestamp - self._acquisition_timestamp)
                    if self._loss_timestamp is not None:
                        self._reacquisition_timestamp = timestamp
                        self._reacquisition_time = max(0.0, timestamp - self._loss_timestamp)
                    reason = f"Lock confirmed after {self._acquisition_frames} frames"
            else:
                # Measurement dropped during acquisition -> abort back to SEARCHING
                self._current_state = TrackingState.SEARCHING
                self._acquisition_frames = 0
                self._is_locked = False
                reason = "Acquisition aborted: measurement lost before confirmation"

        elif self._current_state == TrackingState.TRACKING:
            if accepted:
                self._loss_frames = 0
                self._is_locked = True
            else:
                # Measurement missing -> transition to REACQUIRING (loss episode start)
                self._current_state = TrackingState.REACQUIRING
                self._loss_frames = 1
                self._reacquisition_frames = 0
                self._is_locked = False
                self._loss_timestamp = timestamp
                reason = "Measurement missing; coasting in reacquisition"

        elif self._current_state == TrackingState.REACQUIRING:
            if accepted:
                self._reacquisition_frames += 1
                if self._reacquisition_frames >= self._reacquire_confirm_frames:
                    self._current_state = TrackingState.TRACKING
                    self._is_locked = True
                    self._reacquisition_timestamp = timestamp
                    if self._loss_timestamp is not None:
                        self._reacquisition_time = max(0.0, self._reacquisition_timestamp - self._loss_timestamp)
                    self._loss_frames = 0
                    reason = f"Reacquisition confirmed after {self._reacquisition_frames} frames"
            else:
                self._reacquisition_frames = 0
                self._loss_frames += 1
                if self._loss_frames >= self._loss_confirm_frames:
                    self._current_state = TrackingState.LOST
                    self._is_locked = False
                    reason = f"Track lost after {self._loss_frames} consecutive missed frames"

        elif self._current_state == TrackingState.LOST:
            if accepted:
                # Measurement recovered after loss -> acquire
                self._current_state = TrackingState.ACQUIRING
                self._acquisition_frames = 1
                self._loss_frames = 0
                self._acquisition_timestamp = timestamp
                self._is_locked = False
                reason = "Target re-detected after loss; acquiring lock"
            else:
                # Return to SEARCHING mode
                self._current_state = TrackingState.SEARCHING
                self._loss_frames = 0
                self._is_locked = False
                reason = "Returning to search mode"

        # Record state changes
        if self._current_state != prev_state:
            self._previous_state = prev_state
            self._transition_reason = reason
            self._state_start_time = timestamp
            self._history.append((timestamp, prev_state, self._current_state, reason))

        time_in_state = max(0.0, timestamp - self._state_start_time)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return TrackingStateResult(
            state=self._current_state,
            previous_state=self._previous_state,
            transition_reason=self._transition_reason,
            is_locked=self._is_locked,
            confidence_level=conf,
            is_valid=self._is_locked or (self._current_state == TrackingState.REACQUIRING),
            acquisition_frames=self._acquisition_frames,
            loss_frames=self._loss_frames,
            reacquisition_frames=self._reacquisition_frames,
            time_in_state=time_in_state,
            acquisition_timestamp=self._acquisition_timestamp,
            lock_timestamp=self._lock_timestamp,
            acquisition_time=self._acquisition_time,
            loss_timestamp=self._loss_timestamp,
            reacquisition_timestamp=self._reacquisition_timestamp,
            reacquisition_time=self._reacquisition_time,
            frame_number=frame_number,
            timestamp=timestamp,
            should_trigger_loss=(self._current_state == TrackingState.LOST),
            processing_time_ms=elapsed_ms,
        )


# Production aliases
StateManager = TrackingStateManager
TrackingStateMachine = TrackingStateManager
