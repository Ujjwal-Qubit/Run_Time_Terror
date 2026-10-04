"""
Application Controller — Module 1 per Architecture v1.2 §4.

Top-level orchestrator that owns the simulation loop, connects all
19 production modules, and manages the application lifecycle.

Phase 5.3 connects FrameProvider (Module 8):
  - Module 4  — SceneManager
  - Module 5  — TargetManager
  - Module 6  — CameraModel
  - Module 7  — DisturbanceEngine
  - Module 8  — FrameProvider (SimulationFrameProvider or MP4FrameProvider)
  - Module 14 — GroundTruthProvider
"""

from __future__ import annotations

from typing import Optional, Tuple, Dict, Any, List, Union
from pathlib import Path
import logging
import math
import threading
import queue
import time
import cv2

import numpy as np

from src.config.config_manager import ConfigManager, SystemConfig
from src.config.scenario_manager import ScenarioManager
from src.metrics.logging_engine import LoggingEngine
from src.metrics.metrics_engine import MetricsEngine
from src.evaluation.benchmark_manager import BenchmarkManager
from src.simulation.scene_manager import SceneManager
from src.simulation.target_manager import TargetManager, MultiBeaconManager
from src.simulation.camera_model import CameraModel
from src.simulation.disturbance_engine import DisturbanceEngine
from src.simulation.ground_truth_provider import GroundTruthProvider
from src.interfaces.strategy_interfaces import (
    IFrameProvider,
    IDetector,
    ICentroidEstimator,
    IBeaconIdentifier,
    ITracker,
    ITrackingStateManager,
    IPTZController,
    IMetricsEngine,
)
from src.control.ptz_controller import ProportionalDeadbandPTZController, PTZController
from src.frame.simulation_provider import SimulationFrameProvider
from src.frame.mp4_provider import MP4FrameProvider
from src.tracker.detection_engine import P0ThresholdDetector
from src.tracker.centroid_estimator import IntensityWeightedCentroidEstimator
from src.tracker.candidate_identifier import CandidateIdentifier
from src.tracker.ai_classifier import AIClassifier
from src.tracker.temporal_tracker import ConstantVelocityKalmanTracker
from src.tracker.state_manager import TrackingStateManager
from src.frame.data_contracts import (
    FramePacket,
    GroundTruth,
    DetectionResult,
    VisualizationState,
    TrackerOutput,
    FrameSource,
    ROI,
    TrackResult,
    TrackingState,
    TrackingStateResult,
    CentroidResult,
    CandidateRegion,
    PTZCommand,
)
from src.api.v1 import (
    ITrackingAlgorithm,
    FramePacket as PublicFramePacket,
    TrackingResult as PublicTrackingResult,
)
from src.plugins.loader import PluginLoader
from src.plugins.models import DiscoveredPlugin, LoadedPlugin
from src.plugins.algorithms.baseline_tracker.baseline_tracker import BaselineTracker
from src.app.visualization_state import VisualizationStateManager
from src.app.simulation_worker import SimulationWorkerThread

logger = logging.getLogger(__name__)


class AppController:
    """
    Application Controller — Module 1.

    Responsibilities:
      - Initialize all modules with configuration
      - Run the main simulation/processing loop
      - Coordinate FrameProvider -> Tracker -> PTZ -> Metrics flow
      - Manage start/stop/reset lifecycle
    """

    def __init__(self, plugins_dir: Optional[Union[str, Path]] = None) -> None:
        self._lock = threading.RLock()

        # Module 2 — Configuration Manager
        self._config_manager = ConfigManager()

        # Module 3 — Scenario Manager
        self._scenario_manager = ScenarioManager()

        # Module 16 — Logging Engine
        self._logging_engine = LoggingEngine()

        # Phase 6.4 — Algorithm Plugin Management
        self._plugin_loader = PluginLoader(plugins_dir=plugins_dir)
        self._active_algorithm: Optional[ITrackingAlgorithm] = None
        self._active_algorithm_name: Optional[str] = None
        self._active_plugin: Optional[LoadedPlugin] = None
        self._algorithm_error: Optional[str] = None

        # --- Module slots ---
        # Module 4  — SceneManager (Sim domain)
        self._scene_manager: Optional[SceneManager] = None
        # Module 5  — TargetManager (Sim domain)
        self._target_manager: Optional[TargetManager] = None
        # Module 6  — CameraModel (Sim domain)
        self._camera_model: Optional[CameraModel] = None
        # Module 7  — DisturbanceEngine (Sim domain)
        self._disturbance_engine: Optional[DisturbanceEngine] = None
        # Module 8  — FrameProvider (Firewall adapter)
        self._frame_provider: Optional[IFrameProvider] = None
        # Module 9  — DetectionEngine
        self._detection_engine: Optional[IDetector] = None
        # Module 10 — CentroidEstimator
        self._centroid_estimator: Optional[ICentroidEstimator] = None
        # Module 11 — CandidateIdentifier
        self._candidate_identifier: Optional[IBeaconIdentifier] = None
        # Module 12 — TrackingEngine / TemporalTracker
        self._tracking_engine: Optional[ITracker] = None
        # Module 13 — TrackingStateManager
        self._tracking_state_manager: Optional[ITrackingStateManager] = None
        # Module 14 — PTZController (Control domain)
        self._ptz_controller: Optional[IPTZController] = None
        # Module 15 — GroundTruthProvider (Sim only -> Metrics only)
        self._ground_truth_provider: Optional[GroundTruthProvider] = None
        # Module 15 — MetricsEngine
        self._metrics_engine = None
        # Module 17 — BenchmarkManager
        self._benchmark_manager = None
        # Module 18 — VisualizationEngine
        self._visualization_engine = None
        # Module 19 — GUIController
        self._gui_controller = None

        self._running = False
        self._paused = False
        self._frame_count = 0
        self._sim_time = 0.0

        # Multi-beacon and PTZ actuation controls
        self._multi_beacon_manager: Optional[MultiBeaconManager] = None
        self._ptz_enabled: bool = True
        self._tracking_enabled: bool = True
        self._had_tracking_lock: bool = False

        # Phase 5.10 / F-ARCH-01 decoupled execution and visualization state
        self._viz_manager = VisualizationStateManager(maxsize=30)
        self._sim_worker = SimulationWorkerThread(self, self._viz_manager)

    @property
    def _viz_queue(self) -> queue.Queue:
        return self._viz_manager.queue

    @property
    def _sim_thread(self) -> Optional[threading.Thread]:
        return self._sim_worker.thread

    @property
    def simulation_worker(self) -> SimulationWorkerThread:
        return self._sim_worker

    @property
    def visualization_manager(self) -> VisualizationStateManager:
        return self._viz_manager

    @property
    def plugin_loader(self) -> PluginLoader:
        return self._plugin_loader

    @property
    def active_algorithm(self) -> Optional[ITrackingAlgorithm]:
        return self._active_algorithm

    @property
    def active_algorithm_name(self) -> Optional[str]:
        return self._active_algorithm_name

    @property
    def active_plugin(self) -> Optional[LoadedPlugin]:
        return self._active_plugin

    @property
    def algorithm_error(self) -> Optional[str]:
        return self._algorithm_error

    def discover_algorithms(self) -> Dict[str, DiscoveredPlugin]:
        """Discover available tracking algorithm plugins via PluginLoader."""
        with self._lock:
            res = self._plugin_loader.discover()
            return res.discovered

    def get_available_algorithms(self) -> List[str]:
        """Return list of discovered algorithm plugin names in deterministic alphabetical order."""
        with self._lock:
            discovered = self.discover_algorithms()
            return sorted(list(discovered.keys()))

    def _build_algorithm_config(self) -> Dict[str, Any]:
        """Build dictionary configuration from SystemConfig for algorithm plugins."""
        cfg = self._config_manager.config
        return {
            "detector": vars(cfg.detector) if hasattr(cfg.detector, "__dict__") else {},
            "centroid": vars(cfg.centroid) if hasattr(cfg.centroid, "__dict__") else {},
            "identifier": vars(cfg.identifier) if hasattr(cfg.identifier, "__dict__") else {},
            "tracker": vars(cfg.tracker) if hasattr(cfg.tracker, "__dict__") else {},
            "state": vars(cfg.state) if hasattr(cfg.state, "__dict__") else {},
            "aiml": vars(cfg.aiml) if hasattr(cfg.aiml, "__dict__") else {},
            "use_ai_classifier": True,
        }

    def select_algorithm(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Loads and activates an algorithm plugin by name.
        Instantiates via PluginLoader and initializes with configuration.
        """
        with self._lock:
            try:
                loaded = self._plugin_loader.load_plugin(plugin_name)
                instance = loaded.instance

                base_cfg = self._build_algorithm_config()
                if config is not None:
                    base_cfg.update(config)
                config = base_cfg

                init_ok = instance.initialize(config)
                if not init_ok:
                    err_msg = f"Algorithm '{plugin_name}' initialize() returned False."
                    self._algorithm_error = err_msg
                    logger.error(err_msg)
                    return False

                self._active_algorithm = instance
                self._active_algorithm_name = plugin_name
                self._active_plugin = loaded
                self._algorithm_error = None

                # Maintain backward compatibility with legacy stage inspection
                if type(instance).__name__ == "BaselineTracker" or hasattr(instance, "_detector"):
                    self._detection_engine = getattr(instance, "_detector", None)
                    self._centroid_estimator = getattr(instance, "_centroid_estimator", None)
                    self._candidate_identifier = getattr(instance, "_identifier", None)
                    self._tracking_engine = getattr(instance, "_tracker", None)
                    self._tracking_state_manager = getattr(instance, "_state_manager", None)
                else:
                    self._detection_engine = None
                    self._centroid_estimator = None
                    self._candidate_identifier = None
                    self._tracking_engine = None
                    self._tracking_state_manager = None

                logger.info(f"Successfully selected and initialized algorithm plugin: '{plugin_name}'")
                return True
            except Exception as e:
                err_msg = f"Failed to select algorithm '{plugin_name}': {e}"
                self._algorithm_error = err_msg
                logger.error(err_msg)
                return False

    @property
    def config_manager(self) -> ConfigManager:
        return self._config_manager

    @property
    def scenario_manager(self) -> ScenarioManager:
        return self._scenario_manager

    @property
    def logging_engine(self) -> LoggingEngine:
        return self._logging_engine

    @property
    def scene_manager(self) -> Optional[SceneManager]:
        return self._scene_manager

    @property
    def target_manager(self) -> Optional[TargetManager]:
        return self._target_manager

    @property
    def multi_beacon_manager(self) -> Optional[MultiBeaconManager]:
        return self._multi_beacon_manager

    @property
    def ptz_enabled(self) -> bool:
        return self._ptz_enabled

    def set_ptz_enabled(self, enabled: bool) -> None:
        """Enable or disable PTZ camera actuation."""
        with self._lock:
            self._ptz_enabled = bool(enabled)
            if self._ptz_controller is not None and hasattr(self._ptz_controller, "reset"):
                try:
                    self._ptz_controller.reset()
                except Exception as e:
                    logger.warning(f"PTZ controller reset error on ptz toggle: {e}")
            logger.info(f"[AppController] PTZ enabled: {self._ptz_enabled}")

    def set_ptz_velocity(self, pan_velocity_deg_s: float, tilt_velocity_deg_s: float) -> None:
        """Dynamically command PTZ angular velocity slewing under mutex guard."""
        with self._lock:
            if self._camera_model is not None and self._ptz_enabled:
                dt = 1.0 / (self._config_manager.config.camera.update_rate_hz if self._config_manager and self._config_manager.config and self._config_manager.config.camera else 30.0)
                d_pan = float(pan_velocity_deg_s) * dt
                d_tilt = float(tilt_velocity_deg_s) * dt
                self._camera_model.apply_pan_tilt(d_pan, d_tilt)
            logger.debug(f"[AppController] PTZ velocity command: pan={pan_velocity_deg_s}, tilt={tilt_velocity_deg_s}")

    @property
    def tracking_enabled(self) -> bool:
        return self._tracking_enabled

    def set_tracking_enabled(self, enabled: bool) -> None:
        """Enable or disable active target tracking pipeline."""
        with self._lock:
            self._tracking_enabled = bool(enabled)
            if not self._tracking_enabled:
                self._had_tracking_lock = False
                if hasattr(self._active_algorithm, "reset"):
                    try:
                        self._active_algorithm.reset()
                    except Exception as e:
                        logger.warning(f"Algorithm reset error on tracking disable: {e}")
            logger.info(f"[AppController] Tracking enabled: {self._tracking_enabled}")

    def set_target_motion_type(self, pattern: str) -> None:
        """Dynamically update target motion pattern."""
        with self._lock:
            pat = pattern.upper()
            if self._config_manager and self._config_manager.config:
                self._config_manager.config.motion.motion_type = pat
            if self._target_manager is not None and hasattr(self._target_manager, "set_motion_type"):
                self._target_manager.set_motion_type(pat)

    def set_target_size(self, size: int) -> None:
        """Dynamically update target size / divergence."""
        with self._lock:
            sz = int(size)
            if self._config_manager and self._config_manager.config:
                self._config_manager.config.target.size = sz
            if self._target_manager is not None and hasattr(self._target_manager, "set_size"):
                self._target_manager.set_size(sz)

    def set_atmospheric_condition(self, condition: str) -> None:
        """Dynamically update atmospheric condition in DisturbanceEngine."""
        with self._lock:
            cond = condition.upper()
            if self._config_manager and self._config_manager.config:
                self._config_manager.config.atmospheric.condition = cond
            if self._disturbance_engine is not None and hasattr(self._disturbance_engine, "_atmos_cfg"):
                self._disturbance_engine._atmos_cfg.condition = cond

    def set_noise_enabled(self, noise_type: str, enabled: bool) -> None:
        """Dynamically update noise toggle (gaussian, poisson, salt_and_pepper)."""
        with self._lock:
            nt = noise_type.lower()
            en = bool(enabled)
            if self._disturbance_engine is not None and hasattr(self._disturbance_engine, "_noise_cfg"):
                if nt in ("gaussian", "gnoise"):
                    self._disturbance_engine._noise_cfg.gaussian_enabled = en
                elif nt in ("poisson", "pnoise"):
                    self._disturbance_engine._noise_cfg.poisson_enabled = en
                elif nt in ("salt_and_pepper", "sp", "spnoise"):
                    self._disturbance_engine._noise_cfg.sp_enabled = en
            if self._config_manager and self._config_manager.config:
                if nt in ("gaussian", "gnoise"):
                    self._config_manager.config.noise.gaussian_enabled = en
                elif nt in ("poisson", "pnoise"):
                    self._config_manager.config.noise.poisson_enabled = en
                elif nt in ("salt_and_pepper", "sp", "spnoise"):
                    self._config_manager.config.noise.sp_enabled = en

    def set_ptz_parameters(
        self,
        kp: Optional[float] = None,
        ki: Optional[float] = None,
        deadband: Optional[float] = None,
    ) -> None:
        """Dynamically update PTZ controller gains and deadband."""
        with self._lock:
            if self._ptz_controller is not None and hasattr(self._ptz_controller, "_ptz_cfg"):
                if kp is not None:
                    self._ptz_controller._ptz_cfg.proportional_gain = float(kp)
                if ki is not None:
                    self._ptz_controller._ptz_cfg.integral_gain = float(ki)
                if deadband is not None:
                    self._ptz_controller._ptz_cfg.deadband_px = float(deadband)
            if self._config_manager and self._config_manager.config:
                if kp is not None:
                    self._config_manager.config.ptz.proportional_gain = float(kp)
                if ki is not None:
                    self._config_manager.config.ptz.integral_gain = float(ki)
                if deadband is not None:
                    self._config_manager.config.ptz.deadband_px = float(deadband)

    def set_target_speed(self, speed: float) -> None:
        """Dynamically update primary target speed in running simulation."""
        with self._lock:
            sp = max(0.0, float(speed))
            if self._config_manager and self._config_manager.config:
                self._config_manager.config.target.speed = sp
                if self._config_manager.config.beacons:
                    for b in self._config_manager.config.beacons:
                        if getattr(b, "role", "primary") == "primary":
                            b.speed = sp
            if self._multi_beacon_manager is not None:
                self._multi_beacon_manager.set_speed(sp)
            elif self._target_manager is not None:
                self._target_manager.set_speed(sp)

    def set_secondary_beacon_speed(self, index: int, speed: float) -> None:
        """Dynamically update secondary beacon speed by index (0-based)."""
        with self._lock:
            sp = max(0.0, float(speed))
            if self._config_manager and self._config_manager.config:
                if self._config_manager.config.beacons:
                    sec_idx = 0
                    for b in self._config_manager.config.beacons:
                        if getattr(b, "role", "primary") == "secondary":
                            if sec_idx == index:
                                b.speed = sp
                                break
                            sec_idx += 1
            if self._multi_beacon_manager is not None:
                self._multi_beacon_manager.set_secondary_speed(index, sp)

    def get_telemetry_snapshot(self) -> Optional[Any]:
        """Return the latest telemetry record or state snapshot under lock guard."""
        with self._lock:
            if self._metrics_engine is not None and hasattr(self._metrics_engine, "latest_record"):
                return getattr(self._metrics_engine, "latest_record", None)
            return None

    @property
    def camera_model(self) -> Optional[CameraModel]:
        return self._camera_model

    @property
    def disturbance_engine(self) -> Optional[DisturbanceEngine]:
        return self._disturbance_engine

    @property
    def frame_provider(self) -> Optional[IFrameProvider]:
        return self._frame_provider

    @property
    def ground_truth_provider(self) -> Optional[GroundTruthProvider]:
        return self._ground_truth_provider

    @property
    def detection_engine(self) -> Optional[IDetector]:
        return self._detection_engine

    @property
    def centroid_estimator(self) -> Optional[ICentroidEstimator]:
        return self._centroid_estimator

    @property
    def candidate_identifier(self) -> Optional[IBeaconIdentifier]:
        return self._candidate_identifier

    @property
    def tracking_engine(self) -> Optional[ITracker]:
        return self._tracking_engine

    @property
    def tracking_state_manager(self) -> Optional[ITrackingStateManager]:
        return self._tracking_state_manager

    @property
    def ptz_controller(self) -> Optional[IPTZController]:
        return self._ptz_controller

    @property
    def metrics_engine(self) -> Optional[IMetricsEngine]:
        return self._metrics_engine

    @property
    def benchmark_manager(self) -> Optional[BenchmarkManager]:
        return self._benchmark_manager

    @property
    def is_running(self) -> bool:
        with self._lock:
            if hasattr(self, "_sim_worker") and self._sim_worker is not None:
                if self._sim_worker.thread is not None:
                    if not self._sim_worker.is_alive() and not self._paused:
                        self._running = False
                return bool(self._running and (self._sim_worker.is_alive() or self._sim_worker.thread is None))
            return bool(self._running)

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def initialize(self, config: Optional[SystemConfig] = None) -> None:
        """
        Initialize the application with configuration and instantiate modules.
        Phase 5.3 connects FrameProvider (Module 8) for either SIMULATION or MP4 mode.
        """
        with self._lock:
            if config:
                self._config_manager._config = config
            self._had_tracking_lock = False

            # Validate configuration against PS requirements
            errors = self._config_manager.validate()
            if errors:
                for err in errors:
                    print(f"[CONFIG WARNING] {err}")

            cfg = self._config_manager.config

            # Initialize logging: finalize any pre-existing LoggingEngine before re-initializing
            if hasattr(self, "_logging_engine") and self._logging_engine is not None:
                try:
                    self._logging_engine.finalize()
                except Exception as e:
                    logger.warning(f"[AppController] Failed to finalize previous LoggingEngine: {e}")

            self._logging_engine = LoggingEngine(
                output_dir=cfg.logging.output_dir,
                run_id="",
                csv_enabled=cfg.logging.csv_enabled,
                json_summary_enabled=cfg.logging.json_summary_enabled,
            )
            self._logging_engine.initialize()
            self._logging_engine.write_config_snapshot(cfg.to_dict())

            # Instantiate frame provider based on mode
            mode = cfg.simulation.mode.upper()
            if mode == "SIMULATION":
                self._scene_manager = SceneManager(cfg.scene)

                # Multi-beacon support: if cfg.beacons is populated, use MultiBeaconManager
                # for the full multi-target scenario; otherwise fall back to single TargetManager.
                if cfg.beacons:
                    self._multi_beacon_manager = MultiBeaconManager(
                        beacon_configs=cfg.beacons,
                        motion_config=cfg.motion,
                        scene_width=cfg.scene.width,
                        scene_height=cfg.scene.height,
                        seed=cfg.simulation.random_seed,
                    )
                    # Expose primary's TargetManager for backward-compat attribute access
                    self._target_manager = self._multi_beacon_manager._primary_manager
                else:
                    self._multi_beacon_manager = None
                    self._target_manager = TargetManager(
                        target_config=cfg.target,
                        motion_config=cfg.motion,
                        scene_width=cfg.scene.width,
                        scene_height=cfg.scene.height,
                        seed=cfg.simulation.random_seed,
                    )

                self._camera_model = CameraModel(
                    camera_config=cfg.camera,
                    scene_width=cfg.scene.width,
                    scene_height=cfg.scene.height,
                    background_intensity=cfg.scene.background_intensity,
                )
                self._disturbance_engine = DisturbanceEngine(
                    platform_cfg=cfg.platform_motion,
                    jitter_cfg=cfg.jitter,
                    atmos_cfg=cfg.atmospheric,
                    noise_cfg=cfg.noise,
                    local_contrast_cfg=cfg.local_contrast,
                    seed=cfg.simulation.random_seed,
                )
                self._ground_truth_provider = GroundTruthProvider(
                    background_intensity=cfg.scene.background_intensity
                )

                # FrameProvider (Module 8) in simulation mode
                # Pass multi_beacon_manager if available so SimulationFrameProvider
                # can composite multiple beacons per frame.
                self._frame_provider = SimulationFrameProvider(
                    scene_manager=self._scene_manager,
                    target_manager=self._target_manager,
                    camera_model=self._camera_model,
                    disturbance_engine=self._disturbance_engine,
                    ground_truth_provider=self._ground_truth_provider,
                    fps=cfg.camera.update_rate_hz,
                    max_duration_s=cfg.simulation.duration_s,
                    multi_beacon_manager=self._multi_beacon_manager,
                )
            elif mode == "MP4":
                if not cfg.simulation.mp4_path:
                    raise ValueError("MP4 mode selected but mp4_path is not specified.")
                # In MP4 mode: simulation modules and ground truth provider do NOT exist (firewall guarantee)
                self._scene_manager = None
                self._target_manager = None
                self._multi_beacon_manager = None
                self._camera_model = None
                self._disturbance_engine = None
                self._ground_truth_provider = None

                self._frame_provider = MP4FrameProvider(cfg.simulation.mp4_path)
            else:
                raise ValueError(f"Unsupported simulation mode: {mode}")

            # Instantiate Module 14: PTZController (runs in both SIMULATION and MP4 modes; actuation bypassed in MP4)
            pm = self._camera_model.projection_model if self._camera_model else None
            self._ptz_controller = ProportionalDeadbandPTZController(
                ptz_config=cfg.ptz,
                camera_config=cfg.camera,
                projection_model=pm,
            )

            self._metrics_engine = MetricsEngine(run_id=self._logging_engine.run_id)
            self._benchmark_manager = BenchmarkManager(self)

            # Initialize or select tracking algorithm plugin (Phase 6.4)
            if self._active_algorithm is None:
                self.discover_algorithms()
                avail = self.get_available_algorithms()
                default_algo = "baseline_tracker" if "baseline_tracker" in avail else (avail[0] if avail else None)
                if default_algo:
                    self.select_algorithm(default_algo, config=self._build_algorithm_config())
                else:
                    logger.warning("No algorithm plugins discovered in plugins directory.")
            else:
                self._active_algorithm.initialize(self._build_algorithm_config())

            # Fallback to direct stage instantiation if no plugin was loaded
            if self._active_algorithm is None:
                self._detection_engine = P0ThresholdDetector(cfg.detector)
                self._centroid_estimator = IntensityWeightedCentroidEstimator(cfg.centroid)
                self._candidate_identifier = AIClassifier(cfg.identifier)
                self._tracking_engine = ConstantVelocityKalmanTracker(cfg.tracker)
                self._tracking_state_manager = TrackingStateManager(cfg.state)

            self._frame_count = 0
            self._sim_time = 0.0

    def get_next_frame(self) -> Optional[FramePacket]:
        """
        Unified entry point to obtain the next frame via the FrameProvider firewall.
        Downstream modules receive FramePacket regardless of whether source is simulation or MP4.
        """
        with self._lock:
            if self._frame_provider is None:
                raise RuntimeError("FrameProvider not initialized. Call initialize() first.")
            packet = self._frame_provider.get_next_frame()
            if packet is not None:
                self._frame_count = packet.frame_number
                self._sim_time = packet.timestamp
            return packet

    def step_algorithm(
        self, packet: FramePacket
    ) -> Tuple[PublicTrackingResult, float, Optional[TrackResult], TrackingStateResult, Optional[CentroidResult], Optional[DetectionResult]]:
        """
        Executes the active algorithm on a frame through the public API firewall.
        
        Args:
            packet: Internal FramePacket from FrameProvider.
            
        Returns:
            Tuple of:
              - public_result: PublicTrackingResult from algorithm
              - latency_ms: Measured execution time of process_frame() in ms
              - track_result: Bridge TrackResult for PTZ/Metrics
              - state_result: Bridge TrackingStateResult for PTZ/Metrics
              - centroid_result: Bridge CentroidResult for Metrics
              - detection_result: Bridge DetectionResult for Metrics
        """
        with self._lock:
            if self._active_algorithm is None:
                raise RuntimeError("No algorithm plugin selected. Call select_algorithm() or initialize() first.")

            if not self._tracking_enabled:
                # Tracking OFF: Frame generation continues, but perception/tracking is disabled.
                # Downstream PTZ receives non-tracking state and does not actuate on stale commands.
                state_res = TrackingStateResult(state=TrackingState.LOST, confidence_level=0.0)
                public_res = PublicTrackingResult(
                    algorithm_is_tracking=False,
                    centroid_x=None,
                    centroid_y=None,
                    confidence=0.0,
                    roi=None,
                )
                return (public_res, 0.0, None, state_res, None, None)

            # 1. Convert to public observable contract (Enforce Ground-Truth Firewall)
            fov = None
            if self._camera_model and hasattr(self._config_manager.config, "camera"):
                fov = (self._config_manager.config.camera.fov_h_deg, self._config_manager.config.camera.fov_v_deg)

            public_packet = PublicFramePacket(
                image=packet.image,
                timestamp=packet.timestamp,
                frame_number=packet.frame_number,
                resolution=(packet.width, packet.height),
                fov=fov,
            )

            # 2. Execute Algorithm with Failure Isolation
            t0 = time.perf_counter()
            try:
                public_res = self._active_algorithm.process_frame(public_packet)
                if not isinstance(public_res, PublicTrackingResult):
                    raise TypeError(f"Algorithm returned {type(public_res).__name__}, expected PublicTrackingResult")
            except Exception as e:
                err_str = str(e)
                logger.error(f"Algorithm '{self._active_algorithm_name}' error on frame {packet.frame_number}: {err_str}")
                self._algorithm_error = err_str
                public_res = PublicTrackingResult(
                    algorithm_is_tracking=False,
                    centroid_x=None,
                    centroid_y=None,
                    confidence=0.0,
                    roi=None,
                )
            t_elapsed_ms = (time.perf_counter() - t0) * 1000.0

            # 3. Derive Bridge Data Contracts for Downstream Platform Systems (PTZ & Metrics)
            is_tracking = bool(public_res.algorithm_is_tracking)
            cent_x = public_res.centroid_x
            cent_y = public_res.centroid_y
            conf = public_res.confidence if public_res.confidence is not None else (1.0 if is_tracking else 0.0)

            # Coordinate sanity check
            coords_valid = False
            if is_tracking and cent_x is not None and cent_y is not None:
                if math.isfinite(cent_x) and math.isfinite(cent_y):
                    coords_valid = True
                else:
                    logger.warning(f"Algorithm '{self._active_algorithm_name}' returned non-finite coordinates: ({cent_x}, {cent_y})")
                    is_tracking = False

            if hasattr(self._active_algorithm, "current_state"):
                state = self._active_algorithm.current_state
            elif is_tracking:
                self._had_tracking_lock = True
                state = TrackingState.TRACKING
            else:
                state = TrackingState.LOST if getattr(self, "_had_tracking_lock", False) else TrackingState.SEARCHING

            if state == TrackingState.TRACKING:
                self._had_tracking_lock = True
            state_res = TrackingStateResult(state=state, confidence_level=conf)

            roi_contract = None
            if public_res.roi:
                rx, ry, rw, rh = public_res.roi
                roi_contract = ROI(x=rx, y=ry, width=rw, height=rh)

            track_res = None
            centroid_res = None
            if coords_valid:
                track_res = TrackResult(
                    estimated_x=float(cent_x),
                    estimated_y=float(cent_y),
                    confidence=conf,
                    frame_number=packet.frame_number,
                    timestamp=packet.timestamp,
                    measurement_valid=True,
                    is_coasting=False,
                )
                centroid_res = CentroidResult(
                    x=float(cent_x),
                    y=float(cent_y),
                    valid=True,
                    frame_number=packet.frame_number,
                    processing_time_ms=t_elapsed_ms,
                )
            elif state == TrackingState.REACQUIRING and hasattr(self._active_algorithm, "_tracker"):
                tr = getattr(self._active_algorithm, "_tracker", None)
                if tr is not None and getattr(tr, "is_initialized", False):
                    track_res = TrackResult(
                        estimated_x=float(tr.state_vector[0, 0]),
                        estimated_y=float(tr.state_vector[1, 0]),
                        confidence=conf,
                        frame_number=packet.frame_number,
                        timestamp=packet.timestamp,
                        measurement_valid=False,
                        is_coasting=True,
                    )

            cand_list = []
            if coords_valid and cent_x is not None and cent_y is not None:
                bx, by, bw, bh = (roi_contract.x, roi_contract.y, roi_contract.width, roi_contract.height) if roi_contract else (int(cent_x - 5), int(cent_y - 5), 10, 10)
                cand_list.append(
                    CandidateRegion(
                        bbox_x=int(bx),
                        bbox_y=int(by),
                        bbox_w=int(bw),
                        bbox_h=int(bh),
                        peak_intensity=255.0,
                        mean_intensity=200.0,
                        area=int(bw * bh),
                        raw_centroid_x=float(cent_x),
                        raw_centroid_y=float(cent_y),
                        detection_score=conf,
                    )
                )

            detection_res = DetectionResult(
                frame_number=packet.frame_number,
                timestamp=packet.timestamp,
                candidates=cand_list,
                processing_time_ms=0.0,
                roi=roi_contract,
            )

            return (public_res, t_elapsed_ms, track_res, state_res, centroid_res, detection_res)

    def step_simulation(self, dt: float) -> Tuple[np.ndarray, GroundTruth, np.ndarray]:
        """
        Execute a single simulation frame step directly (for simulation inspection/testing).
        """
        with self._lock:
            if (
                self._scene_manager is None
                or self._target_manager is None
                or self._camera_model is None
                or self._disturbance_engine is None
                or self._ground_truth_provider is None
            ):
                raise RuntimeError("Simulation modules not initialized. Call initialize() in SIMULATION mode.")

            # 1. Advance target physics
            target_state = self._target_manager.step(dt)

            # 2. Geometric disturbances
            cam_x, cam_y = self._camera_model.world_position
            eff_cam_x, eff_cam_y = self._disturbance_engine.apply_geometric_disturbances(
                cam_x, cam_y, dt
            )

            # 3. Render scene canvas
            canvas = self._scene_manager.render(
                target_state.world_x, target_state.world_y, target_state.patch
            )

            # 4. Extract clean camera viewport
            clean_viewport = self._camera_model.extract_viewport(
                canvas, eff_cam_x, eff_cam_y
            )

            # 5. Capture synchronized ground truth (before pixel noise)
            gt = self._ground_truth_provider.capture(
                frame_number=self._frame_count,
                timestamp=self._sim_time,
                target_state=target_state,
                camera_model=self._camera_model,
                clean_viewport=clean_viewport,
                effective_cam_x=eff_cam_x,
                effective_cam_y=eff_cam_y,
            )

            # 6. Apply pixel disturbances (Atmospheric -> Poisson -> Gaussian -> S&P)
            disturbed_frame = self._disturbance_engine.apply_pixel_pipeline(clean_viewport)
            disturbed_frame.flags.writeable = False

            self._frame_count += 1
            self._sim_time += dt

            return (disturbed_frame, gt, clean_viewport)

    def step(self) -> Optional[VisualizationState]:
        """
        Executes exactly one synchronized simulation and tracking step.
        Guarded by self._lock (RLock) to prevent concurrent execution.
        Returns the freshly generated VisualizationState, or None on EOF/stopped.
        """
        with self._lock:
            if self._frame_provider is None:
                return None

            packet = self.get_next_frame()
            if packet is None:
                self._running = False
                return None

            # Execute active algorithm via public API
            (
                public_res,
                t_elapsed_ms,
                track_res,
                state_res,
                centroid_res,
                detection_res,
            ) = self.step_algorithm(packet)

            # Control (PTZ) — only active in SIMULATION mode
            ptz_cmd = None
            if self._ptz_controller and packet.source == FrameSource.SIMULATION:
                if self._ptz_enabled:
                    dt = 1.0 / (self._config_manager.config.camera.update_rate_hz if self._config_manager and self._config_manager.config and self._config_manager.config.camera else 30.0)
                    pm = self._camera_model.projection_model if self._camera_model else None
                    ptz_cmd = self._ptz_controller.compute(
                        track_res,
                        state_res.state,
                        packet.width,
                        packet.height,
                        dt=dt,
                        projection_model=pm,
                    )
                    if self._camera_model and ptz_cmd.valid:
                        self._camera_model.apply_pan_tilt(ptz_cmd.delta_pan_deg, ptz_cmd.delta_tilt_deg)
                else:
                    self._ptz_controller.reset()
                    ptz_cmd = PTZCommand(
                        delta_pan_deg=0.0,
                        delta_tilt_deg=0.0,
                        pan_velocity_deg_s=0.0,
                        tilt_velocity_deg_s=0.0,
                        valid=False,
                        timestamp=packet.timestamp,
                        frame_number=packet.frame_number,
                    )

            # Ground truth retrieval
            gt = None
            if self._ground_truth_provider:
                gt = self._ground_truth_provider.get_truth(packet.frame_number)

            cam_pan = self._camera_model.pan_deg if self._camera_model else 0.0
            cam_tilt = self._camera_model.tilt_deg if self._camera_model else 0.0

            # Metrics / Logging update
            if self._metrics_engine and state_res:
                telemetry = self._metrics_engine.update(
                    frame_packet=packet,
                    track_result=track_res,
                    state_result=state_res,
                    centroid_result=centroid_res,
                    detection_result=detection_res,
                    ptz_command=ptz_cmd,
                    ground_truth=gt,
                    camera_pan_deg=cam_pan,
                    camera_tilt_deg=cam_tilt,
                    processing_time_ms=t_elapsed_ms,
                )
                self._logging_engine.log_frame(telemetry)

            # Build VisualizationState for frontend
            cam_fov = (
                self._config_manager.config.camera.fov_h_deg
                if (self._config_manager and self._config_manager.config and self._config_manager.config.camera)
                else 4.0
            )
            cam_fov_v = (
                self._config_manager.config.camera.fov_v_deg
                if (self._config_manager and self._config_manager.config and self._config_manager.config.camera)
                else 3.0
            )
            roi_contract = None
            if public_res.roi:
                roi_contract = ROI(
                    x=public_res.roi[0],
                    y=public_res.roi[1],
                    width=public_res.roi[2],
                    height=public_res.roi[3],
                )

            tgt_spd = (
                self._config_manager.config.target.speed
                if (self._config_manager and self._config_manager.config and self._config_manager.config.target)
                else None
            )

            viz_state = VisualizationState(
                frame_number=packet.frame_number,
                timestamp=packet.timestamp,
                pan_angle_deg=cam_pan,
                tilt_angle_deg=cam_tilt,
                camera_fov=cam_fov,
                display_image=packet.image,
                camera_fov_v=cam_fov_v,
                camera_width=packet.width,
                camera_height=packet.height,
                estimated_centroid_x=centroid_res.x if centroid_res and centroid_res.valid else None,
                estimated_centroid_y=centroid_res.y if centroid_res and centroid_res.valid else None,
                tracking_state=state_res.state.name,
                tracking_error_px=None,
                roi=roi_contract,
                processing_latency_ms=t_elapsed_ms,
                fps=1000.0 / t_elapsed_ms if t_elapsed_ms > 0 else 0.0,
                ground_truth_x=gt.ideal_projected_x if gt else None,
                ground_truth_y=gt.ideal_projected_y if gt else None,
                target_speed_px_s=tgt_spd,
                ptz_enabled=self._ptz_enabled,
            )

            self._viz_manager.push_state(viz_state)
            return viz_state

    def run(self) -> None:
        """Main run loop."""
        with self._lock:
            self._running = True
            print(
                f"[AppController] Running with source: "
                f"{self._frame_provider.get_source_type() if self._frame_provider else 'NONE'}"
            )
        if self._benchmark_manager:
            self._benchmark_manager.run_benchmark()

    def start_background_loop(self) -> None:
        """Starts the internal simulation loop in a background thread for GUI mode."""
        with self._lock:
            self._running = True
            self._paused = False
            self._sim_worker.start()

    def pause(self) -> None:
        with self._lock:
            self._paused = True
            if hasattr(self, "_sim_worker") and self._sim_worker is not None:
                self._sim_worker.pause()

    def resume(self) -> None:
        with self._lock:
            self._paused = False
            if hasattr(self, "_sim_worker") and self._sim_worker is not None:
                self._sim_worker.resume()

    def get_latest_visualization_state(self) -> Optional[VisualizationState]:
        """Called by GUI to drain the queue and get the freshest frame."""
        return self._viz_manager.get_latest_state()

    def stop(self) -> None:
        """Stop the application safely without deadlock."""
        self._running = False
        if hasattr(self, "_sim_worker") and self._sim_worker is not None:
            self._sim_worker.stop(timeout=1.0)
        with self._lock:
            if self._frame_provider:
                self._frame_provider.close()
            self._logging_engine.finalize()
            logger.info(f"[AppController] Stopped after {self._frame_count} frames.")

    def reset(self) -> None:
        """Reset all modules to initial state under mutex guard."""
        self.stop()
        with self._lock:
            self._frame_count = 0
            self._sim_time = 0.0
            self._running = False
            self._paused = False
            self._had_tracking_lock = False
            self._viz_manager.clear()

            if self._active_algorithm:
                self._active_algorithm.reset()
            if self._frame_provider:
                try:
                    self._frame_provider.reset()
                except Exception as e:
                    logger.error(f"[AppController] Failed to reset frame provider: {e}")
            if self._scene_manager:
                self._scene_manager.reset()
            if self._target_manager:
                self._target_manager.reset()
            if self._camera_model:
                self._camera_model.reset()
            if self._disturbance_engine:
                self._disturbance_engine.reset()
            if self._ground_truth_provider:
                self._ground_truth_provider.clear()
            if self._tracking_engine:
                self._tracking_engine.reset()
            if self._tracking_state_manager:
                self._tracking_state_manager.reset()
            if self._ptz_controller:
                self._ptz_controller.reset()
            if self._metrics_engine:
                self._metrics_engine.reset()
