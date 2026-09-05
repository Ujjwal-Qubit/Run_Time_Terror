"""
Simulation Frame Provider — Module 8 Adapter per Architecture v1.2 §4 and §6.

Adapts the simulation domain (Modules 4, 5, 6, 7, 14) to the common IFrameProvider contract.
Produces immutable FramePacket objects for downstream tracker consumption.

FIREWALL GUARANTEE:
Never injects ground truth or simulator state into FramePacket.
GroundTruth remains accessible exclusively via the ground_truth_provider property
for MetricsEngine and evaluation infrastructure.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from src.interfaces.strategy_interfaces import IFrameProvider
from src.frame.data_contracts import FramePacket, FrameSource
from src.simulation.scene_manager import SceneManager
from src.simulation.target_manager import TargetManager
from src.simulation.camera_model import CameraModel
from src.simulation.disturbance_engine import DisturbanceEngine
from src.simulation.ground_truth_provider import GroundTruthProvider
from src.config.config_manager import SystemConfig


class SimulationFrameProvider(IFrameProvider):
    """
    SimulationFrameProvider (Module 8 - Simulation Adapter).

    Connects:
      - Module 4: SceneManager
      - Module 5: TargetManager
      - Module 6: CameraModel
      - Module 7: DisturbanceEngine
      - Module 14: GroundTruthProvider (side-channel for metrics only)

    Emits:
      - FramePacket (FrameSource.SIMULATION, read-only numpy array)
    """

    def __init__(
        self,
        scene_manager: SceneManager,
        target_manager: TargetManager,
        camera_model: CameraModel,
        disturbance_engine: DisturbanceEngine,
        ground_truth_provider: Optional[GroundTruthProvider] = None,
        fps: float = 30.0,
        max_duration_s: Optional[float] = None,
    ) -> None:
        self._scene_manager = scene_manager
        self._target_manager = target_manager
        self._camera_model = camera_model
        self._disturbance_engine = disturbance_engine
        self._ground_truth_provider = ground_truth_provider

        self._fps = float(fps) if fps > 0 else 30.0
        self._dt = 1.0 / self._fps
        self._max_duration_s = max_duration_s
        self._max_frames = (
            int(round(max_duration_s * self._fps))
            if max_duration_s is not None and max_duration_s > 0
            else None
        )

        self._width = self._camera_model.projection_model.width
        self._height = self._camera_model.projection_model.height
        self._frame_count = 0
        self._sim_time = 0.0

    @classmethod
    def from_config(
        cls,
        config: SystemConfig,
        ground_truth_provider: Optional[GroundTruthProvider] = None,
    ) -> SimulationFrameProvider:
        """Convenience factory creating a SimulationFrameProvider from SystemConfig."""
        scene_mgr = SceneManager(config.scene)
        target_mgr = TargetManager(
            target_config=config.target,
            motion_config=config.motion,
            scene_width=config.scene.width,
            scene_height=config.scene.height,
            seed=config.simulation.random_seed,
        )
        cam_model = CameraModel(
            camera_config=config.camera,
            scene_width=config.scene.width,
            scene_height=config.scene.height,
            background_intensity=config.scene.background_intensity,
        )
        dist_engine = DisturbanceEngine(
            platform_cfg=config.platform_motion,
            jitter_cfg=config.jitter,
            atmos_cfg=config.atmospheric,
            noise_cfg=config.noise,
            seed=config.simulation.random_seed,
        )
        gt_prov = ground_truth_provider or GroundTruthProvider(
            background_intensity=config.scene.background_intensity
        )

        return cls(
            scene_manager=scene_mgr,
            target_manager=target_mgr,
            camera_model=cam_model,
            disturbance_engine=dist_engine,
            ground_truth_provider=gt_prov,
            fps=config.camera.update_rate_hz,
            max_duration_s=config.simulation.duration_s,
        )

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def resolution(self) -> Tuple[int, int]:
        return (self._width, self._height)

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def ground_truth_provider(self) -> Optional[GroundTruthProvider]:
        """Provides side-channel access to ground truth solely for MetricsEngine."""
        return self._ground_truth_provider

    def get_source_type(self) -> str:
        return FrameSource.SIMULATION.value

    def is_exhausted(self) -> bool:
        if self._max_frames is not None and self._frame_count >= self._max_frames:
            return True
        return False

    def reset(self) -> None:
        """Reset simulation provider and all underlying simulation modules."""
        self._frame_count = 0
        self._sim_time = 0.0
        self._scene_manager.reset()
        self._target_manager.reset()
        self._camera_model.reset()
        self._disturbance_engine.reset()
        if self._ground_truth_provider:
            self._ground_truth_provider.clear()

    def get_next_frame(self) -> Optional[FramePacket]:
        """
        Step simulation and produce the next FramePacket.
        The returned image array is read-only (zero-copy immutability guarantee).
        """
        if self.is_exhausted():
            return None

        # 1. Advance target physics
        target_state = self._target_manager.step(self._dt)

        # 2. Compute geometric disturbances on camera pose
        cam_x, cam_y = self._camera_model.world_position
        eff_cam_x, eff_cam_y = self._disturbance_engine.apply_geometric_disturbances(
            cam_x, cam_y, self._dt
        )

        # 3. Render target onto scene canvas
        canvas = self._scene_manager.render(
            target_state.world_x, target_state.world_y, target_state.patch
        )

        # 4. Extract clean camera viewport
        clean_viewport = self._camera_model.extract_viewport(
            canvas, eff_cam_x, eff_cam_y
        )

        # 5. Capture synchronized ground truth (side-channel only)
        if self._ground_truth_provider is not None:
            self._ground_truth_provider.capture(
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

        # Ensure frame immutability: read-only view with zero copy overhead
        disturbed_frame.flags.writeable = False

        packet = FramePacket(
            frame_number=self._frame_count,
            timestamp=self._sim_time,
            image=disturbed_frame,
            width=self._width,
            height=self._height,
            source=FrameSource.SIMULATION,
        )

        self._frame_count += 1
        self._sim_time += self._dt

        return packet
