"""
Simulation Worker Thread — Component extracted from AppController (F-ARCH-01).

Responsibilities:
  - Executes the continuous tracking simulation loop in a background daemon thread for GUI/interactive modes.
  - Coordinates frame acquisition, tracking step, PTZ actuation, metrics updates, and telemetry publishing.
  - Enforces loop timing and frame pacing matching camera update rates.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import traceback
from typing import Optional, List, Any, TYPE_CHECKING

try:
    from PySide6.QtCore import QObject, Signal
except ImportError:  # Fallback for headless environments without PySide6
    class QObject:  # type: ignore[no-redef]
        def __init__(self, parent: Optional[Any] = None) -> None:
            pass

    class Signal:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._callbacks: List[Any] = []

        def connect(self, callback: Any) -> None:
            self._callbacks.append(callback)

        def emit(self, *args: Any, **kwargs: Any) -> None:
            for cb in self._callbacks:
                try:
                    cb(*args, **kwargs)
                except Exception:
                    pass

from src.frame.data_contracts import (
    FrameSource,
    ROI,
    VisualizationState,
    PTZCommand,
)
from src.app.visualization_state import VisualizationStateManager

if TYPE_CHECKING:
    from src.app.app_controller import AppController

logger = logging.getLogger(__name__)


class SimulationWorkerThread(QObject):
    """Manages the background simulation thread and loop execution."""

    errorOccurred = Signal(str)

    def __init__(
        self,
        app: "AppController",
        viz_manager: VisualizationStateManager,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._app = app
        self._viz_manager = viz_manager
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._paused: bool = False
        self._last_error: Optional[str] = None

    @property
    def thread(self) -> Optional[threading.Thread]:
        return self._thread

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        """Starts the internal simulation loop in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.info("[AppController] Simulation is already running.")
            return

        self._running = True
        self._paused = False
        self._last_error = None
        self._viz_manager.clear()

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self, timeout: float = 1.0) -> None:
        """Stops the background simulation thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            if threading.current_thread() != self._thread:
                self._thread.join(timeout=timeout)

    def _run_loop(self) -> None:
        """Internal worker thread executing the tracker pipeline with robust exception handling."""
        logger.info("[AppController] Background simulation loop started.")
        self._last_error = None
        try:
            while self._running:
                if self._paused:
                    time.sleep(0.01)
                    continue

                loop_t0 = time.perf_counter()

                # Step pipeline under AppController lock
                viz_state = self._app.step()
                if viz_state is None:
                    # EOF or stopped
                    self._running = False
                    self._app._running = False
                    break

                # Loop pacing matching camera frame rate
                target_fps = (
                    float(self._app.config_manager.config.camera.update_rate_hz)
                    if (self._app.config_manager and self._app.config_manager.config and self._app.config_manager.config.camera)
                    else 30.0
                )
                target_period = 1.0 / max(1.0, min(120.0, target_fps))
                loop_duration = time.perf_counter() - loop_t0
                sleep_time = max(0.001, target_period - loop_duration)
                time.sleep(sleep_time)

        except Exception as e:
            tb = traceback.format_exc()
            err_msg = f"Unhandled exception in simulation worker thread: {e}"
            logger.error(f"{err_msg}\n{tb}")
            self._last_error = str(e)
            try:
                self.errorOccurred.emit(str(e))
            except Exception as emit_err:
                logger.error(f"Failed to emit errorOccurred signal: {emit_err}")
        finally:
            self._running = False
            self._app._running = False
            logger.info("[AppController] Background simulation loop terminated.")
