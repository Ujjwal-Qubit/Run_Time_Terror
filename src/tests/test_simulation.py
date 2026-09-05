"""
Phase 5.2 Simulation Engine Tests

Tests cover:
  - SceneManager (Module 4): dimensions, coordinate conventions, deterministic rendering
  - TargetManager (Module 5): 4 mandatory trajectories, valid positions, reproducibility, bounds
  - CameraModel & ProjectionModel (Module 6): projection math, FOV scaling, viewport extraction, boundary padding
  - DisturbanceEngine (Module 7): deterministic seed, platform motion bounds, jitter bounds, atmospheric degradation, noise stages, sequence
  - GroundTruthProvider (Module 14): frame synchronization, coordinate distinction (world, projected, rendered), firewall isolation
  - AppController Integration: end-to-end multi-frame stepping
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from src.config.config_manager import (
    SceneConfig,
    CameraConfig,
    TargetConfig,
    MotionConfig,
    PlatformMotionConfig,
    JitterConfig,
    AtmosphericConfig,
    NoiseConfig,
    SystemConfig,
)
from src.config import defaults
from src.frame.data_contracts import (
    MotionType,
    AtmosphericCondition,
    FramePacket,
    FrameSource,
)
from src.simulation.scene_manager import SceneManager
from src.simulation.target_manager import TargetManager, TargetState
from src.simulation.camera_model import CameraModel, ProjectionModel
from src.simulation.disturbance_engine import DisturbanceEngine
from src.simulation.ground_truth_provider import GroundTruthProvider
from src.app.app_controller import AppController


# ===========================================================================
# 1. SceneManager Tests (Module 4)
# ===========================================================================

class TestSceneManager:
    """Test 2D global canvas, coordinate management, and background generation."""

    def test_default_dimensions(self):
        scene = SceneManager()
        assert scene.width == 2000
        assert scene.height == 2000
        assert scene.background_intensity == defaults.SCENE_BACKGROUND_INTENSITY
        assert scene.current_canvas.shape == (2000, 2000)
        assert scene.current_canvas.dtype == np.uint8

    def test_custom_valid_dimensions(self):
        cfg = SceneConfig(width=2500, height=3000, background_intensity=40)
        scene = SceneManager(cfg)
        assert scene.width == 2500
        assert scene.height == 3000
        assert scene.background_intensity == 40
        assert scene.current_canvas.shape == (3000, 2500)

    def test_dimensions_below_minimum_raises(self):
        cfg = SceneConfig(width=1999, height=2000)
        with pytest.raises(ValueError):
            SceneManager(cfg)

        cfg2 = SceneConfig(width=2000, height=1500)
        with pytest.raises(ValueError):
            SceneManager(cfg2)

    def test_deterministic_rendering(self):
        scene = SceneManager()
        patch = np.full((10, 10), fill_value=220, dtype=np.uint8)

        render1 = scene.render(1000.0, 1000.0, patch)
        canvas1 = render1.copy()

        # Reset and render again with identical parameters
        scene.reset()
        render2 = scene.render(1000.0, 1000.0, patch)

        assert np.array_equal(canvas1, render2)

    def test_target_compositing_within_canvas(self):
        scene = SceneManager(SceneConfig(width=2000, height=2000, background_intensity=30))
        patch = np.full((10, 10), fill_value=200, dtype=np.uint8)

        canvas = scene.render(500.0, 500.0, patch)
        # Background pixels away from beacon should equal 30
        assert canvas[0, 0] == 30
        # Beacon center pixels should equal 200
        assert canvas[500, 500] == 200

    def test_target_compositing_clipped_at_boundary(self):
        scene = SceneManager(SceneConfig(width=2000, height=2000, background_intensity=30))
        patch = np.full((20, 20), fill_value=220, dtype=np.uint8)

        # Place target right on top-left corner
        canvas = scene.render(0.0, 0.0, patch)
        assert canvas.shape == (2000, 2000)
        assert canvas[0, 0] == 220
        assert canvas[1999, 1999] == 30


# ===========================================================================
# 2. TargetManager Tests (Module 5)
# ===========================================================================

class TestTargetManager:
    """Test target generation, motion patterns, deterministic seeding, and state."""

    def test_target_size_limits(self):
        # Valid sizes 5 to 20
        TargetManager(target_config=TargetConfig(size=5))
        TargetManager(target_config=TargetConfig(size=20))

        with pytest.raises(ValueError):
            TargetManager(target_config=TargetConfig(size=4))

        with pytest.raises(ValueError):
            TargetManager(target_config=TargetConfig(size=25))

    def test_target_shapes(self):
        tm_square = TargetManager(target_config=TargetConfig(shape="square", size=10, intensity=220))
        assert tm_square.patch.shape == (10, 10)
        assert np.all(tm_square.patch == 220)

        tm_circle = TargetManager(target_config=TargetConfig(shape="circle", size=10, intensity=220))
        assert tm_circle.patch.shape == (10, 10)
        # Center of circle should be bright, corners dark
        assert tm_circle.patch[5, 5] == 220
        assert tm_circle.patch[0, 0] == 0

        tm_gauss = TargetManager(target_config=TargetConfig(shape="gaussian", size=15, intensity=240))
        assert tm_gauss.patch.shape == (15, 15)
        # Peak at center
        assert tm_gauss.patch[7, 7] == 240
        assert tm_gauss.patch[0, 0] < 50

    def test_straight_line_trajectory(self):
        cfg_t = TargetConfig(initial_position="custom", initial_x=500.0, initial_y=500.0, speed=100.0)
        cfg_m = MotionConfig(motion_type=MotionType.STRAIGHT_LINE.value, straight_line_angle_deg=0.0)
        tm = TargetManager(target_config=cfg_t, motion_config=cfg_m)

        init_x, init_y = tm.world_position
        assert pytest.approx(init_x, abs=1e-3) == 500.0
        assert pytest.approx(init_y, abs=1e-3) == 500.0

        # Step 0.1 s -> dx = 100.0 * 0.1 = 10.0 px
        state = tm.step(0.1)
        assert pytest.approx(state.world_x, abs=1e-3) == 510.0
        assert pytest.approx(state.world_y, abs=1e-3) == 500.0

    def test_straight_line_bounds_reflection(self):
        # Target heading directly towards right border
        cfg_t = TargetConfig(initial_position="custom", initial_x=1980.0, initial_y=1000.0, speed=100.0)
        cfg_m = MotionConfig(motion_type=MotionType.STRAIGHT_LINE.value, straight_line_angle_deg=0.0)
        tm = TargetManager(target_config=cfg_t, motion_config=cfg_m, scene_width=2000, scene_height=2000)

        # Step 0.5s -> would travel 50px to 2030, should bounce back inside
        state = tm.step(0.5)
        assert state.world_x < 2000.0
        assert state.vx < 0.0  # velocity reversed

    def test_circular_trajectory(self):
        cfg_t = TargetConfig(initial_position="custom", initial_x=1000.0, initial_y=1000.0, speed=50.0)
        cfg_m = MotionConfig(motion_type=MotionType.CIRCULAR.value, circle_radius=150.0)
        tm = TargetManager(target_config=cfg_t, motion_config=cfg_m)

        states = [tm.step(0.05) for _ in range(50)]
        # Distance from center should remain constant (radius ~150)
        center_x = tm._circle_cx
        center_y = tm._circle_cy
        for s in states:
            dist = math.sqrt((s.world_x - center_x) ** 2 + (s.world_y - center_y) ** 2)
            assert pytest.approx(dist, abs=1.0) == 150.0

    def test_figure8_trajectory(self):
        cfg_t = TargetConfig(initial_position="custom", initial_x=1000.0, initial_y=1000.0, speed=50.0)
        cfg_m = MotionConfig(motion_type=MotionType.FIGURE_8.value, figure8_radius_x=200.0, figure8_radius_y=100.0)
        tm = TargetManager(target_config=cfg_t, motion_config=cfg_m)

        states = [tm.step(0.05) for _ in range(100)]
        xs = [s.world_x for s in states]
        ys = [s.world_y for s in states]

        # X should stay within center +/- 200, Y within center +/- 100
        assert min(xs) >= tm._fig8_cx - 201.0
        assert max(xs) <= tm._fig8_cx + 201.0
        assert min(ys) >= tm._fig8_cy - 101.0
        assert max(ys) <= tm._fig8_cy + 101.0

    def test_random_trajectory_bounded(self):
        cfg_t = TargetConfig(initial_position="random", speed=50.0)
        cfg_m = MotionConfig(motion_type=MotionType.RANDOM.value, random_max_displacement=10.0)
        tm = TargetManager(target_config=cfg_t, motion_config=cfg_m, seed=12345)

        for _ in range(100):
            state = tm.step(0.033)
            assert 0.0 <= state.world_x <= 2000.0
            assert 0.0 <= state.world_y <= 2000.0

    def test_deterministic_reproducibility_with_seed(self):
        cfg_t = TargetConfig(initial_position="random")
        cfg_m = MotionConfig(motion_type=MotionType.RANDOM.value)

        tm1 = TargetManager(target_config=cfg_t, motion_config=cfg_m, seed=999)
        seq1 = [(s.world_x, s.world_y) for s in [tm1.step(0.05) for _ in range(30)]]

        tm2 = TargetManager(target_config=cfg_t, motion_config=cfg_m, seed=999)
        seq2 = [(s.world_x, s.world_y) for s in [tm2.step(0.05) for _ in range(30)]]

        assert seq1 == seq2


# ===========================================================================
# 3. CameraModel & ProjectionModel Tests (Module 6)
# ===========================================================================

class TestCameraModelAndProjection:
    """Test camera pose, projection transformations, and viewport extraction."""

    def test_fov_resolution_scale(self):
        proj = ProjectionModel(width=640, height=480, fov_h_deg=4.0, fov_v_deg=3.0)
        # 4.0 / 640 = 0.00625 deg/pixel
        assert pytest.approx(proj.deg_per_px_h, abs=1e-7) == 0.00625
        # 3.0 / 480 = 0.00625 deg/pixel
        assert pytest.approx(proj.deg_per_px_v, abs=1e-7) == 0.00625
        # Square pixels
        assert pytest.approx(proj.deg_per_px_h, abs=1e-7) == proj.deg_per_px_v

    def test_world_to_image_projection(self):
        proj = ProjectionModel(width=640, height=480, fov_h_deg=4.0, fov_v_deg=3.0)
        # Camera centered at (1000, 1000)
        # World point at (1000, 1000) should project to image optical center (320, 240)
        ix, iy = proj.world_to_image(1000.0, 1000.0, 1000.0, 1000.0)
        assert pytest.approx(ix, abs=1e-5) == 320.0
        assert pytest.approx(iy, abs=1e-5) == 240.0

        # World point 100 px to the right
        ix2, iy2 = proj.world_to_image(1100.0, 1000.0, 1000.0, 1000.0)
        assert pytest.approx(ix2, abs=1e-5) == 420.0
        assert pytest.approx(iy2, abs=1e-5) == 240.0

    def test_image_to_world_roundtrip(self):
        proj = ProjectionModel()
        cam_x, cam_y = 1200.0, 800.0
        orig_wx, orig_wy = 1250.0, 780.0

        ix, iy = proj.world_to_image(orig_wx, orig_wy, cam_x, cam_y)
        recon_wx, recon_wy = proj.image_to_world(ix, iy, cam_x, cam_y)

        assert pytest.approx(recon_wx, abs=1e-5) == orig_wx
        assert pytest.approx(recon_wy, abs=1e-5) == orig_wy

    def test_image_to_angles_and_inverse(self):
        proj = ProjectionModel(width=640, height=480, fov_h_deg=4.0, fov_v_deg=3.0)
        # Center of image -> (0, 0) degrees
        pan, tilt = proj.image_to_angles(320.0, 240.0)
        assert pytest.approx(pan, abs=1e-5) == 0.0
        assert pytest.approx(tilt, abs=1e-5) == 0.0

        # Offset 160 px right (quarter FOV_H = 1.0 degree)
        pan1, tilt1 = proj.image_to_angles(480.0, 240.0)
        assert pytest.approx(pan1, abs=1e-5) == 1.0
        assert pytest.approx(tilt1, abs=1e-5) == 0.0

        # Convert back
        dx, dy = proj.angles_to_image_offset(pan1, tilt1)
        assert pytest.approx(dx, abs=1e-5) == 160.0
        assert pytest.approx(dy, abs=1e-5) == 0.0

    def test_visibility_check(self):
        proj = ProjectionModel(width=640, height=480)
        cam_x, cam_y = 1000.0, 1000.0

        # Inside viewport
        assert proj.is_visible(1000.0, 1000.0, cam_x, cam_y) is True
        assert proj.is_visible(1300.0, 1200.0, cam_x, cam_y) is True

        # Outside viewport (too far right)
        assert proj.is_visible(1500.0, 1000.0, cam_x, cam_y) is False

    def test_viewport_extraction_clean(self):
        scene = SceneManager(SceneConfig(width=2000, height=2000, background_intensity=30))
        patch = np.full((20, 20), fill_value=220, dtype=np.uint8)
        canvas = scene.render(1000.0, 1000.0, patch)

        cam = CameraModel(CameraConfig(width=640, height=480), scene_width=2000, scene_height=2000)
        viewport = cam.extract_viewport(canvas)

        assert viewport.shape == (480, 640)
        # Optical center of viewport should contain beacon intensity
        assert viewport[240, 320] == 220
        # Far corner should be background
        assert viewport[0, 0] == 30

    def test_viewport_boundary_padding(self):
        scene = SceneManager(SceneConfig(width=2000, height=2000, background_intensity=30))
        canvas = scene.current_canvas

        cam = CameraModel(CameraConfig(width=640, height=480), scene_width=2000, scene_height=2000)
        # Position camera close to top-left corner (100, 100) -> viewport extends into negative coords
        viewport = cam.extract_viewport(canvas, effective_x=100.0, effective_y=100.0)

        assert viewport.shape == (480, 640)
        assert np.all(viewport == 30)

    def test_camera_pan_tilt_moves_world_coords(self):
        cam = CameraModel(CameraConfig(width=640, height=480, fov_h_deg=4.0, fov_v_deg=3.0))
        init_x, init_y = cam.world_position

        # Pan right by 1.0 degree -> should shift camera center right by 160 px
        cam.apply_pan_tilt(delta_pan_deg=1.0, delta_tilt_deg=0.0)
        new_x, new_y = cam.world_position

        assert pytest.approx(new_x - init_x, abs=1e-3) == 160.0
        assert pytest.approx(new_y, abs=1e-3) == init_y
        assert pytest.approx(cam.pan_deg, abs=1e-5) == 1.0


# ===========================================================================
# 4. DisturbanceEngine Tests (Module 7)
# ===========================================================================

class TestDisturbanceEngine:
    """Test ordered disturbances, bounds, noise stages, and determinism."""

    def test_platform_motion_bounds(self):
        cfg_plat = PlatformMotionConfig(enabled=True, motion_type="LINEAR", max_px_per_frame=15.0)
        eng = DisturbanceEngine(platform_cfg=cfg_plat)

        for _ in range(50):
            dx, dy = eng.compute_platform_motion(dt=0.033)
            assert abs(dx) <= 15.0
            assert abs(dy) <= 15.0

    def test_platform_motion_ps_limit_enforced(self):
        # Exceeding PS required max (20 px/frame) must raise ValueError
        with pytest.raises(ValueError):
            DisturbanceEngine(platform_cfg=PlatformMotionConfig(max_px_per_frame=25.0))

    def test_jitter_bounds(self):
        cfg_jit = JitterConfig(enabled=True, max_px_per_frame=10.0)
        eng = DisturbanceEngine(jitter_cfg=cfg_jit)

        for _ in range(50):
            jx, jy = eng.compute_camera_jitter()
            assert abs(jx) <= 10.0
            assert abs(jy) <= 10.0

    def test_jitter_ps_limit_enforced(self):
        with pytest.raises(ValueError):
            DisturbanceEngine(jitter_cfg=JitterConfig(max_px_per_frame=25.0))

    def test_atmospheric_degradation_modes(self):
        frame = np.full((100, 100), fill_value=100, dtype=np.uint8)

        # Clear -> unchanged
        eng_clear = DisturbanceEngine(atmos_cfg=AtmosphericConfig(condition=AtmosphericCondition.CLEAR.value))
        deg_clear = eng_clear.apply_atmospheric_degradation(frame)
        assert np.array_equal(frame, deg_clear)

        # Fog -> contrast 0.4, brightness +30 => 100 * 0.4 + 30 = 70
        eng_fog = DisturbanceEngine(atmos_cfg=AtmosphericConfig(condition=AtmosphericCondition.FOG.value))
        deg_fog = eng_fog.apply_atmospheric_degradation(frame)
        assert pytest.approx(deg_fog[50, 50], abs=2) == 70

        # Low light -> contrast 0.5, brightness -40 => 100 * 0.5 - 40 = 10
        eng_ll = DisturbanceEngine(atmos_cfg=AtmosphericConfig(condition=AtmosphericCondition.LOW_LIGHT.value))
        deg_ll = eng_ll.apply_atmospheric_degradation(frame)
        assert pytest.approx(deg_ll[50, 50], abs=2) == 10

    def test_gaussian_noise_enabled_and_disabled(self):
        frame = np.full((100, 100), fill_value=128, dtype=np.uint8)

        # Disabled
        eng_off = DisturbanceEngine(noise_cfg=NoiseConfig(gaussian_enabled=False, gaussian_sigma=10.0))
        assert np.array_equal(frame, eng_off.apply_gaussian_noise(frame))

        # Enabled
        eng_on = DisturbanceEngine(noise_cfg=NoiseConfig(gaussian_enabled=True, gaussian_sigma=10.0), seed=42)
        noisy = eng_on.apply_gaussian_noise(frame)
        assert not np.array_equal(frame, noisy)
        # Mean should be near 128, std near 10
        assert pytest.approx(np.mean(noisy), abs=1.0) == 128.0
        assert pytest.approx(np.std(noisy.astype(float)), abs=1.5) == 10.0

    def test_poisson_noise(self):
        frame = np.full((100, 100), fill_value=100, dtype=np.uint8)
        eng_pois = DisturbanceEngine(noise_cfg=NoiseConfig(poisson_enabled=True), seed=42)
        noisy = eng_pois.apply_poisson_noise(frame)
        # Poisson with lambda=100 has variance=100, std=10
        assert pytest.approx(np.mean(noisy), abs=2.0) == 100.0
        assert pytest.approx(np.std(noisy.astype(float)), abs=2.0) == 10.0

    def test_salt_and_pepper_noise(self):
        frame = np.full((100, 100), fill_value=128, dtype=np.uint8)
        eng_sp = DisturbanceEngine(noise_cfg=NoiseConfig(sp_enabled=True, sp_density=0.10), seed=42)
        corrupted = eng_sp.apply_salt_and_pepper_noise(frame)

        salt_count = np.sum(corrupted == 255)
        pepper_count = np.sum(corrupted == 0)
        total_corrupted = salt_count + pepper_count
        # Total corrupted should be ~10% of 10,000 = 1,000 pixels
        assert pytest.approx(total_corrupted, abs=200) == 1000

    def test_deterministic_disturbances_with_seed(self):
        frame = np.full((100, 100), fill_value=128, dtype=np.uint8)
        cfg_noise = NoiseConfig(sp_enabled=True, gaussian_enabled=True, poisson_enabled=True)

        eng1 = DisturbanceEngine(noise_cfg=cfg_noise, seed=777)
        out1 = eng1.apply_pixel_pipeline(frame)

        eng2 = DisturbanceEngine(noise_cfg=cfg_noise, seed=777)
        out2 = eng2.apply_pixel_pipeline(frame)

        assert np.array_equal(out1, out2)


# ===========================================================================
# 5. GroundTruthProvider Tests (Module 14)
# ===========================================================================

class TestGroundTruthProvider:
    """Test synchronized ground truth, coordinate separation, and firewall."""

    def test_capture_synchronization(self):
        gt_provider = GroundTruthProvider(background_intensity=30)
        cam = CameraModel(CameraConfig(width=640, height=480), scene_width=2000, scene_height=2000)
        t_state = TargetState(
            world_x=1050.0, world_y=950.0, vx=0.0, vy=0.0,
            size=10, shape="square", intensity=220,
            patch=np.full((10, 10), 220, dtype=np.uint8),
        )

        gt = gt_provider.capture(
            frame_number=1,
            timestamp=0.033,
            target_state=t_state,
            camera_model=cam,
        )

        assert gt.frame_number == 1
        assert pytest.approx(gt.timestamp, abs=1e-5) == 0.033
        assert gt.target_world_x == 1050.0
        assert gt.target_world_y == 950.0
        assert gt.target_visible is True
        # Camera is at (1000, 1000), target at (1050, 950) -> image (370, 190)
        assert pytest.approx(gt.ideal_projected_x, abs=1e-4) == 370.0
        assert pytest.approx(gt.ideal_projected_y, abs=1e-4) == 190.0

    def test_distinction_between_ideal_and_rendered_centroid(self):
        gt_provider = GroundTruthProvider(background_intensity=30)
        scene = SceneManager(SceneConfig(width=2000, height=2000, background_intensity=30))
        cam = CameraModel(CameraConfig(width=640, height=480), scene_width=2000, scene_height=2000)

        # Place target at subpixel coordinates (1000.3, 1000.7)
        patch = np.full((10, 10), 220, dtype=np.uint8)
        canvas = scene.render(1000.3, 1000.7, patch)
        viewport = cam.extract_viewport(canvas)

        t_state = TargetState(
            world_x=1000.3, world_y=1000.7, vx=0.0, vy=0.0,
            size=10, shape="square", intensity=220,
            patch=patch,
        )

        gt = gt_provider.capture(
            frame_number=0,
            timestamp=0.0,
            target_state=t_state,
            camera_model=cam,
            clean_viewport=viewport,
        )

        # Ideal projected: (320.3, 240.7)
        assert pytest.approx(gt.ideal_projected_x, abs=1e-3) == 320.3
        assert pytest.approx(gt.ideal_projected_y, abs=1e-3) == 240.7
        # Rendered centroid is discrete on pixel grid (close, but distinctly computed)
        assert gt.rendered_centroid_x is not None
        assert gt.rendered_centroid_y is not None
        assert abs(gt.rendered_centroid_x - gt.ideal_projected_x) < 1.0
        assert abs(gt.rendered_centroid_y - gt.ideal_projected_y) < 1.0

    def test_invisible_target_handling(self):
        gt_provider = GroundTruthProvider()
        cam = CameraModel(CameraConfig(width=640, height=480))
        # Target far away at (1800, 1800) outside camera viewport
        t_state = TargetState(
            world_x=1800.0, world_y=1800.0, vx=0.0, vy=0.0,
            size=10, shape="square", intensity=220,
            patch=np.full((10, 10), 220, dtype=np.uint8),
        )

        gt = gt_provider.capture(
            frame_number=5,
            timestamp=0.165,
            target_state=t_state,
            camera_model=cam,
        )

        assert gt.target_visible is False
        assert gt.ideal_projected_x is None
        assert gt.ideal_projected_y is None
        assert gt.rendered_centroid_x is None

    def test_history_retrieval(self):
        gt_provider = GroundTruthProvider()
        cam = CameraModel()
        t_state = TargetState(
            world_x=1000.0, world_y=1000.0, vx=0.0, vy=0.0,
            size=10, shape="square", intensity=220,
            patch=np.full((10, 10), 220, dtype=np.uint8),
        )

        for i in range(5):
            gt_provider.capture(frame_number=i, timestamp=i * 0.033, target_state=t_state, camera_model=cam)

        all_gt = gt_provider.get_all_truth()
        assert len(all_gt) == 5
        assert gt_provider.get_truth(2).frame_number == 2
        assert gt_provider.get_truth(999) is None

        gt_provider.clear()
        assert len(gt_provider.get_all_truth()) == 0

    def test_no_ground_truth_in_frame_packet(self):
        """Verify architectural firewall: FramePacket contains zero simulator/GT fields."""
        dummy_img = np.zeros((480, 640), dtype=np.uint8)
        packet = FramePacket(
            frame_number=10,
            timestamp=0.33,
            image=dummy_img,
            width=640,
            height=480,
            source=FrameSource.SIMULATION,
        )

        # Fields must be strictly limited to frame metadata
        assert not hasattr(packet, "ground_truth")
        assert not hasattr(packet, "target_world_x")
        assert not hasattr(packet, "ideal_projected_x")
        assert not hasattr(packet, "rendered_centroid_x")


# ===========================================================================
# 6. Full Simulation Smoke Run
# ===========================================================================

class TestSimulationIntegration:
    """Test full multi-frame execution of simulation domain via AppController."""

    def test_multi_frame_stepping(self):
        app = AppController()
        app.initialize()

        assert app.scene_manager is not None
        assert app.target_manager is not None
        assert app.camera_model is not None
        assert app.disturbance_engine is not None
        assert app.ground_truth_provider is not None

        # Step 30 frames (1 second at 30 FPS)
        for i in range(30):
            frame, gt, clean = app.step_simulation(dt=1.0 / 30.0)
            assert frame.shape == (480, 640)
            assert clean.shape == (480, 640)
            assert gt.frame_number == i
            assert pytest.approx(gt.timestamp, abs=1e-4) == i / 30.0

        all_gt = app.ground_truth_provider.get_all_truth()
        assert len(all_gt) == 30
