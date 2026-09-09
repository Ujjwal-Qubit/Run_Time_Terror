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

from typing import Optional, Tuple
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
from src.simulation.target_manager import TargetManager
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
from src.frame.data_contracts import FramePacket, GroundTruth, DetectionResult, VisualizationState, TrackerOutput, FrameSource


class AppController:
    """
    Application Controller — Module 1.

    Responsibilities:
      - Initialize all modules with configuration
      - Run the main simulation/processing loop
      - Coordinate FrameProvider -> Tracker -> PTZ -> Metrics flow
      - Manage start/stop/reset lifecycle
    """

    def __init__(self) -> None:
        # Module 2 — Configuration Manager
        self._config_manager = ConfigManager()

        # Module 3 — Scenario Manager
        self._scenario_manager = ScenarioManager()

        # Module 16 — Logging Engine
        self._logging_engine = LoggingEngine()

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

        # Phase 5.10 internal execution mechanism
        self._sim_thread: Optional[threading.Thread] = None
        self._viz_queue: queue.Queue = queue.Queue(maxsize=30)

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



    def initialize(self, config: Optional[SystemConfig] = None) -> None:
        """
        Initialize the application with configuration and instantiate modules.
        Phase 5.3 connects FrameProvider (Module 8) for either SIMULATION or MP4 mode.
        """
        if config:
            self._config_manager._config = config

        # Validate configuration against PS requirements
        errors = self._config_manager.validate()
        if errors:
            for err in errors:
                print(f"[CONFIG WARNING] {err}")

        cfg = self._config_manager.config

        # Initialize logging
        self._logging_engine = LoggingEngine(
            output_dir=cfg.logging.output_dir,
            run_id="",
        )
        self._logging_engine.initialize()
        self._logging_engine.write_config_snapshot(cfg.to_dict())

        # Instantiate frame provider based on mode
        mode = cfg.simulation.mode.upper()
        if mode == "SIMULATION":
            self._scene_manager = SceneManager(cfg.scene)
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
                seed=cfg.simulation.random_seed,
            )
            self._ground_truth_provider = GroundTruthProvider(
                background_intensity=cfg.scene.background_intensity
            )

            # FrameProvider (Module 8) in simulation mode
            self._frame_provider = SimulationFrameProvider(
                scene_manager=self._scene_manager,
                target_manager=self._target_manager,
                camera_model=self._camera_model,
                disturbance_engine=self._disturbance_engine,
                ground_truth_provider=self._ground_truth_provider,
                fps=cfg.camera.update_rate_hz,
                max_duration_s=cfg.simulation.duration_s,
            )
        elif mode == "MP4":
            if not cfg.simulation.mp4_path:
                raise ValueError("MP4 mode selected but mp4_path is not specified.")
            # In MP4 mode: simulation modules and ground truth provider do NOT exist (firewall guarantee)
            self._scene_manager = None
            self._target_manager = None
            self._camera_model = None
            self._disturbance_engine = None
            self._ground_truth_provider = None

            self._frame_provider = MP4FrameProvider(cfg.simulation.mp4_path)
        else:
            raise ValueError(f"Unsupported simulation mode: {mode}")

        # Instantiate Module 9: DetectionEngine (runs in both SIMULATION and MP4 modes)
        self._detection_engine = P0ThresholdDetector(cfg.detector)

        # Instantiate Module 10: CentroidEstimator (runs in both SIMULATION and MP4 modes)
        self._centroid_estimator = IntensityWeightedCentroidEstimator(cfg.centroid)

        # Instantiate Module 11: CandidateIdentifier (runs in both SIMULATION and MP4 modes)
        # We use the AI Augmentation instead of the baseline
        self._candidate_identifier = AIClassifier(cfg.identifier)

        # Instantiate Module 12: TrackingEngine / TemporalTracker (runs in both SIMULATION and MP4 modes)
        self._tracking_engine = ConstantVelocityKalmanTracker(cfg.tracker)

        # Instantiate Module 13: TrackingStateManager (runs in both SIMULATION and MP4 modes)
        self._tracking_state_manager = TrackingStateManager(cfg.state)

        # Instantiate Module 14: PTZController (runs in both SIMULATION and MP4 modes; actuation bypassed in MP4)
        pm = self._camera_model.projection_model if self._camera_model else None
        self._ptz_controller = ProportionalDeadbandPTZController(
            ptz_config=cfg.ptz,
            camera_config=cfg.camera,
            projection_model=pm,
        )

        self._metrics_engine = MetricsEngine(run_id=self._logging_engine.run_id)
        self._benchmark_manager = BenchmarkManager(self)

        self._frame_count = 0
        self._sim_time = 0.0

    def get_next_frame(self) -> Optional[FramePacket]:
        """
        Unified entry point to obtain the next frame via the FrameProvider firewall.
        Downstream modules receive FramePacket regardless of whether source is simulation or MP4.
        """
        if self._frame_provider is None:
            raise RuntimeError("FrameProvider not initialized. Call initialize() first.")
        packet = self._frame_provider.get_next_frame()
        if packet is not None:
            self._frame_count = packet.frame_number
            self._sim_time = packet.timestamp
        return packet

    def step_simulation(self, dt: float) -> Tuple[np.ndarray, GroundTruth, np.ndarray]:
        """
        Execute a single simulation frame step directly (for simulation inspection/testing).
        """
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

    def run(self) -> None:
        """Main run loop."""
        self._running = True
        print(
            f"[AppController] Running with source: "
            f"{self._frame_provider.get_source_type() if self._frame_provider else 'NONE'}"
        )
        if self._benchmark_manager:
            self._benchmark_manager.run_benchmark()

    def start_background_loop(self) -> None:
        """Starts the internal simulation loop in a background thread for GUI mode."""
        if self._sim_thread and self._sim_thread.is_alive():
            print("[AppController] Simulation is already running.")
            return

        self._running = True
        self._paused = False
        # Clear queue
        while not self._viz_queue.empty():
            try:
                self._viz_queue.get_nowait()
            except queue.Empty:
                break
                
        self._sim_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._sim_thread.start()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def _simulation_loop(self) -> None:
        """
        Internal worker thread executing the tracker pipeline.
        Publishes VisualizationState to _viz_queue.
        """
        print("[AppController] Background simulation loop started.")
        while self._running:
            if self._paused:
                time.sleep(0.01)
                continue

            packet = self.get_next_frame()
            if packet is None:
                # EOF
                self._running = False
                break

            t_start = time.perf_counter()

            # Tracking Pipeline
            roi = self.tracking_engine.get_roi(packet.width, packet.height) if self.tracking_engine else None
            detection_res = self.detection_engine.detect(packet, roi=roi)
            ident_res = self.candidate_identifier.identify(detection_res.candidates)
            
            centroid_res = None
            if ident_res.valid and ident_res.selected_candidate is not None:
                centroid_res = self.centroid_estimator.estimate(packet, ident_res.selected_candidate)
            
            track_res = self.tracking_engine.update(centroid_res, frame_number=packet.frame_number, timestamp=packet.timestamp)
            state_res = self.tracking_state_manager.update(track_res)

            # Control
            ptz_cmd = None
            if self.ptz_controller and packet.source == FrameSource.SIMULATION:
                dt = 1.0 / self.config_manager.config.camera.update_rate_hz
                ptz_cmd = self.ptz_controller.compute(track_res, state_res.state, packet.width, packet.height, dt)
                if self.camera_model and ptz_cmd.valid:
                    self.camera_model.apply_pan_tilt(ptz_cmd.delta_pan_deg, ptz_cmd.delta_tilt_deg)

            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

            # Telemetry/Metrics update
            tracker_output = TrackerOutput(
                frame_number=packet.frame_number,
                timestamp=packet.timestamp,
                state=state_res.state,
                previous_state=state_res.previous_state,
                transition_reason=state_res.transition_reason,
                centroid=centroid_res,
                track=track_res,
                detection_valid=ident_res.valid,
                candidate_count=len(detection_res.candidates),
                confidence=state_res.confidence_level,
                roi=roi,
                processing_time_ms=t_elapsed_ms
            )

            gt = None
            if self.ground_truth_provider:
                gt = self.ground_truth_provider.get_truth(packet.frame_number)
            
            cam_pan = self.camera_model.pan_deg if self.camera_model else 0.0
            cam_tilt = self.camera_model.tilt_deg if self.camera_model else 0.0

            if self.metrics_engine and state_res:
                telemetry = self.metrics_engine.update(
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
                self.logging_engine.log_frame(telemetry)

            # Build VisualizationState for frontend
            cam_fov = self.config_manager.config.camera.fov_h_deg

            viz_state = VisualizationState(
                frame_number=packet.frame_number,
                timestamp=packet.timestamp,
                pan_angle_deg=cam_pan,
                tilt_angle_deg=cam_tilt,
                camera_fov=cam_fov,
                display_image=packet.image,
                estimated_centroid_x=centroid_res.x if centroid_res and centroid_res.valid else None,
                estimated_centroid_y=centroid_res.y if centroid_res and centroid_res.valid else None,
                tracking_state=state_res.state.name,
                tracking_error_px=None, # Computed in UI or later if needed
                roi=roi,
                processing_latency_ms=t_elapsed_ms,
                fps=1000.0 / t_elapsed_ms if t_elapsed_ms > 0 else 0.0,
                ground_truth_x=gt.ideal_projected_x if gt else None,
                ground_truth_y=gt.ideal_projected_y if gt else None
            )

            # Put in queue (discard oldest if full to avoid blocking processing)
            try:
                self._viz_queue.put_nowait(viz_state)
            except queue.Full:
                try:
                    self._viz_queue.get_nowait()
                    self._viz_queue.put_nowait(viz_state)
                except queue.Empty:
                    pass
            
            # Yield slightly to allow other threads to run
            time.sleep(0.001)

    def get_latest_visualization_state(self) -> Optional[VisualizationState]:
        """Called by GUI to drain the queue and get the freshest frame."""
        latest_state = None
        while not self._viz_queue.empty():
            try:
                latest_state = self._viz_queue.get_nowait()
            except queue.Empty:
                break
        return latest_state

    def stop(self) -> None:
        """Stop the application."""
        self._running = False
        if self._sim_thread and self._sim_thread.is_alive():
            self._sim_thread.join(timeout=1.0)
        if self._frame_provider:
            self._frame_provider.close()
        self._logging_engine.finalize()
        print(f"[AppController] Stopped after {self._frame_count} frames.")

    def reset(self) -> None:
        """Reset all modules to initial state."""
        self.stop()
        self._frame_count = 0
        self._sim_time = 0.0
        self._running = False
        self._paused = False
        
        while not self._viz_queue.empty():
            try:
                self._viz_queue.get_nowait()
            except queue.Empty:
                break

        if self._frame_provider:
            self._frame_provider.reset()
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
