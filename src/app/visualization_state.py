"""
Visualization State Manager — Component extracted from AppController (F-ARCH-01).

Responsibilities:
  - Manages thread-safe FIFO queue of VisualizationState packets for UI / WebSocket clients.
  - Formats and serializes VisualizationState with bounded memory and drop-oldest backpressure.
  - Provides retrieval of the freshest visualization frame for rendering loops.
"""

from __future__ import annotations

import queue
from typing import Optional
from src.frame.data_contracts import VisualizationState


class VisualizationStateManager:
    """Manages the queue and lifecycle of visualization states."""

    def __init__(self, maxsize: int = 30) -> None:
        self._maxsize = maxsize
        self._queue: queue.Queue[VisualizationState] = queue.Queue(maxsize=maxsize)

    @property
    def queue(self) -> queue.Queue[VisualizationState]:
        return self._queue

    def clear(self) -> None:
        """Drains and discards all pending visualization states."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def push_state(self, state: VisualizationState) -> None:
        """
        Pushes a VisualizationState into the queue.
        Discards the oldest state if the queue is full (drop-oldest backpressure).
        """
        try:
            self._queue.put_nowait(state)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(state)
            except queue.Empty:
                pass

    def get_latest_state(self) -> Optional[VisualizationState]:
        """Drains the queue and returns the freshest VisualizationState."""
        latest_state: Optional[VisualizationState] = None
        while not self._queue.empty():
            try:
                latest_state = self._queue.get_nowait()
            except queue.Empty:
                break
        return latest_state
