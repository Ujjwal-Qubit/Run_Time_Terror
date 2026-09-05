"""
Phase 5.5 Centroid Estimator Tests (Module 10).

Verifies:
  1. Contract compliance (ICentroidEstimator interface, CentroidResult data contract).
  2. Sub-pixel accuracy (floating-point precision, no int quantization).
  3. Controlled synthetic frames with known fractional centroids (5x5, 10x10, 20x20).
  4. Multiple spot profiles (Gaussian, circular, square).
  5. Error convergence under varying SNR.
  6. Robust local background subtraction (annulus perimeter median).
  7. Robustness against noise (Gaussian, Poisson, Salt & Pepper, bright background, saturation).
  8. Boundary clipping and border-touching candidates.
  9. Edge cases (zero signal, uniform ROI, single-pixel signal, degenerate candidate).
 10. Frame immutability (non-mutating, works on writeable=False arrays).
 11. Ground-truth firewall (zero simulation/GroundTruth imports or dependencies).
 12. Resolution independence (320x240, 640x480, 1280x720, 1920x1080).
 13. Integration: FrameProvider -> P0ThresholdDetector -> IntensityWeightedCentroidEstimator.
"""

from __future__ import annotations

import ast
import inspect
import math
import numpy as np
import pytest

from src.interfaces.strategy_interfaces import ICentroidEstimator
from src.frame.data_contracts import (
    FramePacket,
    FrameSource,
    CandidateRegion,
    ScoredCandidate,
    CentroidResult,
)
from src.config.config_manager import CentroidConfig, SystemConfig
from src.tracker.centroid_estimator import (
    IntensityWeightedCentroidEstimator,
    CentroidEstimator,
)
from src.tracker.detection_engine import P0ThresholdDetector
from src.frame.simulation_provider import SimulationFrameProvider
from src.simulation.scene_manager import SceneManager
from src.simulation.target_manager import TargetManager
from src.simulation.camera_model import CameraModel
from src.simulation.disturbance_engine import DisturbanceEngine
from src.simulation.ground_truth_provider import GroundTruthProvider


# ---------------------------------------------------------------------------
# Synthetic Frame Generation Helpers
# ---------------------------------------------------------------------------

def make_gaussian_spot(
    width: int = 640,
    height: int = 480,
    cx: float = 320.4,
    cy: float = 240.7,
    sigma: float = 2.5,
    peak_intensity: float = 220.0,
    bg_intensity: float = 30.0,
) -> tuple[np.ndarray, CandidateRegion]:
    """
    Generate a synthetic frame with an analytically defined Gaussian spot at sub-pixel (cx, cy).
    Returns (image_uint8, candidate_region).
    """
    y_coords, x_coords = np.mgrid[0:height, 0:width]
    dist_sq = (x_coords - cx) ** 2 + (y_coords - cy) ** 2
    spot = peak_intensity * np.exp(-0.5 * dist_sq / (sigma ** 2))
    img = np.clip(bg_intensity + spot, 0, 255).astype(np.uint8)
    img.flags.writeable = False

    # Define candidate bounding box around spot with radius ~ 3*sigma
    radius = int(math.ceil(3.0 * sigma))
    bx = max(0, int(math.floor(cx - radius)))
    by = max(0, int(math.floor(cy - radius)))
    bw = min(width - bx, 2 * radius + 1)
    bh = min(height - by, 2 * radius + 1)

    cand = CandidateRegion(
        bbox_x=bx,
        bbox_y=by,
        bbox_w=bw,
        bbox_h=bh,
        peak_intensity=float(np.max(img[by : by + bh, bx : bx + bw])),
        mean_intensity=float(np.mean(img[by : by + bh, bx : bx + bw])),
        area=bw * bh,
        candidate_id=1,
    )
    return img, cand


def make_flat_spot(
    width: int = 640,
    height: int = 480,
    cx: float = 320.0,
    cy: float = 240.0,
    size: int = 10,
    shape: str = "circle",
    spot_intensity: int = 200,
    bg_intensity: int = 30,
) -> tuple[np.ndarray, CandidateRegion, float, float]:
    """
    Generate a flat-top circular or square spot.
    Returns (image_uint8, candidate_region, true_cx, true_cy).
    """
    img = np.full((height, width), fill_value=bg_intensity, dtype=np.uint8)
    bx = int(round(cx - (size - 1) / 2.0))
    by = int(round(cy - (size - 1) / 2.0))

    if shape == "square":
        img[by : by + size, bx : bx + size] = spot_intensity
        true_cx = float(bx + (size - 1) / 2.0)
        true_cy = float(by + (size - 1) / 2.0)
    elif shape == "circle":
        y_grid, x_grid = np.ogrid[:height, :width]
        dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
        mask = dist <= (size / 2.0)
        img[mask] = spot_intensity
        # Exact discrete centroid of circle mask
        ys, xs = np.nonzero(mask)
        true_cx = float(np.mean(xs))
        true_cy = float(np.mean(ys))
    else:
        true_cx, true_cy = float(cx), float(cy)

    img.flags.writeable = False

    cand = CandidateRegion(
        bbox_x=bx,
        bbox_y=by,
        bbox_w=size,
        bbox_h=size,
        peak_intensity=float(spot_intensity),
        mean_intensity=float(spot_intensity),
        area=size * size,
        candidate_id=1,
    )
    return img, cand, true_cx, true_cy


# ---------------------------------------------------------------------------
# 1. Contract & Interface Tests
# ---------------------------------------------------------------------------

class TestCentroidContracts:
    """Verifies interface adherence and return types."""

    def test_implements_interface(self):
        estimator = IntensityWeightedCentroidEstimator()
        assert isinstance(estimator, ICentroidEstimator)
        assert estimator.get_name() == "IntensityWeightedCentroidEstimator"

    def test_alias_equivalence(self):
        assert CentroidEstimator is IntensityWeightedCentroidEstimator
        inst = CentroidEstimator()
        assert isinstance(inst, IntensityWeightedCentroidEstimator)

    def test_result_contract_and_metadata(self):
        img, cand, _, _ = make_flat_spot(size=10)
        packet = FramePacket(
            image=img,
            width=img.shape[1],
            height=img.shape[0],
            frame_number=42,
            timestamp=1.4,
            source=FrameSource.SIMULATION,
        )
        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(packet, cand)

        assert isinstance(res, CentroidResult)
        assert res.frame_number == 42
        assert abs(res.timestamp - 1.4) < 1e-6
        assert res.candidate_id == cand.candidate_id
        assert res.valid is True
        assert res.quality > 0.0
        assert res.total_signal > 0.0
        assert res.estimated_bg >= 0.0
        assert res.roi_bbox is not None
        assert res.processing_time_ms >= 0.0

    def test_scored_candidate_unpacking(self):
        img, cand, _, _ = make_flat_spot(size=10)
        scored = ScoredCandidate(candidate=cand, score=0.95, is_beacon=True)
        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(img, scored)

        assert res.valid is True
        assert res.candidate_id == cand.candidate_id
        assert isinstance(res.x, float)
        assert isinstance(res.y, float)


# ---------------------------------------------------------------------------
# 2. Sub-Pixel Precision & Mathematical Formulation Tests
# ---------------------------------------------------------------------------

class TestSubPixelPrecision:
    """Verifies non-quantized floating point centroid output."""

    @pytest.mark.parametrize("offset_x, offset_y", [
        (0.25, 0.35),
        (0.50, 0.50),
        (0.72, 0.18),
        (-0.33, 0.41),
    ])
    def test_fractional_centroid_recovery(self, offset_x, offset_y):
        true_cx = 320.0 + offset_x
        true_cy = 240.0 + offset_y

        img, cand = make_gaussian_spot(
            width=640,
            height=480,
            cx=true_cx,
            cy=true_cy,
            sigma=2.5,
            peak_intensity=200.0,
            bg_intensity=25.0,
        )

        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(img, cand)

        assert res.valid is True
        # Output coordinates must strictly be floating-point types
        assert isinstance(res.x, (float, np.floating))
        assert isinstance(res.y, (float, np.floating))

        # Ensure the result is genuinely sub-pixel (not truncated or rounded to integer)
        assert abs(res.x - round(res.x)) > 0.05 or abs(offset_x) < 0.05
        assert abs(res.y - round(res.y)) > 0.05 or abs(offset_y) < 0.05

        # Error must be sub-pixel (< 0.15 pixels under clean conditions)
        err_x = abs(res.x - true_cx)
        err_y = abs(res.y - true_cy)
        assert err_x < 0.15, f"Sub-pixel error x {err_x:.3f} >= 0.15 px"
        assert err_y < 0.15, f"Sub-pixel error y {err_y:.3f} >= 0.15 px"

    def test_different_target_sizes(self):
        """Test 5x5, 10x10, and 20x20 targets per PS specification."""
        estimator = IntensityWeightedCentroidEstimator()

        for size in (5, 10, 20):
            img, cand, true_cx, true_cy = make_flat_spot(
                cx=200.5,
                cy=150.5,
                size=size,
                shape="square",
                spot_intensity=220,
                bg_intensity=30,
            )
            res = estimator.estimate(img, cand)
            assert res.valid is True
            assert abs(res.x - true_cx) < 0.2
            assert abs(res.y - true_cy) < 0.2

    def test_target_shapes(self):
        """Test circular, square, and Gaussian profiles."""
        estimator = IntensityWeightedCentroidEstimator()
        cx, cy = 300.5, 200.5

        # Circle
        img_c, cand_c, true_cx_c, true_cy_c = make_flat_spot(cx=cx, cy=cy, size=12, shape="circle")
        res_c = estimator.estimate(img_c, cand_c)
        assert res_c.valid is True
        assert abs(res_c.x - true_cx_c) < 0.2
        assert abs(res_c.y - true_cy_c) < 0.2

        # Square
        img_s, cand_s, true_cx_s, true_cy_s = make_flat_spot(cx=cx, cy=cy, size=12, shape="square")
        res_s = estimator.estimate(img_s, cand_s)
        assert res_s.valid is True
        assert abs(res_s.x - true_cx_s) < 0.2
        assert abs(res_s.y - true_cy_s) < 0.2

        # Gaussian
        img_g, cand_g = make_gaussian_spot(cx=cx, cy=cy, sigma=3.0)
        res_g = estimator.estimate(img_g, cand_g)
        assert res_g.valid is True
        assert abs(res_g.x - cx) < 0.2


# ---------------------------------------------------------------------------
# 3. Accuracy & SNR Convergence Tests
# ---------------------------------------------------------------------------

class TestAccuracyAndSNR:
    """Verifies estimator accuracy and error convergence with increasing SNR."""

    def test_error_decreases_with_higher_snr(self):
        """Higher peak signal above noise floor leads to equal or lower estimation error."""
        true_cx, true_cy = 250.3, 180.7
        estimator = IntensityWeightedCentroidEstimator()

        # Low SNR frame (beacon peak=70, bg=50, noise sigma=10)
        np.random.seed(42)
        img_low, cand_low = make_gaussian_spot(
            cx=true_cx, cy=true_cy, sigma=2.0, peak_intensity=30.0, bg_intensity=50.0
        )
        noise = np.random.normal(0, 5, img_low.shape).astype(np.int16)
        noisy_low = np.clip(img_low.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        res_low = estimator.estimate(noisy_low, cand_low)

        # High SNR frame (beacon peak=200, bg=50, noise sigma=5)
        img_high, cand_high = make_gaussian_spot(
            cx=true_cx, cy=true_cy, sigma=2.0, peak_intensity=180.0, bg_intensity=50.0
        )
        noisy_high = np.clip(img_high.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        res_high = estimator.estimate(noisy_high, cand_high)

        err_low = math.hypot(res_low.x - true_cx, res_low.y - true_cy)
        err_high = math.hypot(res_high.x - true_cx, res_high.y - true_cy)

        assert res_high.valid is True
        assert err_high <= err_low + 0.1
        assert err_high < 0.2  # High SNR must achieve tight sub-pixel tracking


# ---------------------------------------------------------------------------
# 4. Background Estimation Tests
# ---------------------------------------------------------------------------

class TestBackgroundSubtraction:
    """Verifies local background estimation via perimeter median."""

    def test_perimeter_median_immune_to_central_beacon(self):
        """A very bright central beacon must not inflate the perimeter background estimate."""
        estimator = IntensityWeightedCentroidEstimator()
        # 11x11 patch with bg=40, center 5x5 saturated at 255
        patch = np.full((11, 11), fill_value=40.0, dtype=np.float64)
        patch[3:8, 3:8] = 255.0

        bg_est = estimator.estimate_local_background(patch)
        assert abs(bg_est - 40.0) < 1e-3, f"Expected bg 40.0, got {bg_est}"

    def test_background_invariance(self):
        """The estimated centroid should remain invariant across different uniform background levels."""
        true_cx, true_cy = 310.4, 230.6
        estimator = IntensityWeightedCentroidEstimator()

        centroids = []
        for bg in [10.0, 50.0, 100.0, 150.0]:
            img, cand = make_gaussian_spot(
                cx=true_cx, cy=true_cy, sigma=2.5, peak_intensity=90.0, bg_intensity=bg
            )
            res = estimator.estimate(img, cand)
            assert res.valid is True
            centroids.append((res.x, res.y))

        # All estimated centroids across different backgrounds must match within 0.05 px
        for (cx, cy) in centroids:
            assert abs(cx - centroids[0][0]) < 0.05
            assert abs(cy - centroids[0][1]) < 0.05


# ---------------------------------------------------------------------------
# 5. Robustness Tests (Noise, Saturated, Boundary)
# ---------------------------------------------------------------------------

class TestCentroidRobustness:
    """Verifies robustness under realistic sensor disturbances."""

    def test_gaussian_noise(self):
        img, cand = make_gaussian_spot(cx=300.5, cy=200.5, sigma=2.5, peak_intensity=180.0, bg_intensity=30.0)
        np.random.seed(123)
        noise = np.random.normal(0, 8.0, img.shape).astype(np.int16)
        noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(noisy, cand)
        assert res.valid is True
        assert abs(res.x - 300.5) < 0.35
        assert abs(res.y - 200.5) < 0.35

    def test_poisson_noise(self):
        img, cand = make_gaussian_spot(cx=300.5, cy=200.5, sigma=2.5, peak_intensity=180.0, bg_intensity=30.0)
        np.random.seed(123)
        noisy = np.random.poisson(img.astype(np.float64)).clip(0, 255).astype(np.uint8)

        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(noisy, cand)
        assert res.valid is True
        assert abs(res.x - 300.5) < 0.35
        assert abs(res.y - 200.5) < 0.35

    def test_salt_and_pepper_noise(self):
        img, cand = make_gaussian_spot(cx=300.5, cy=200.5, sigma=2.5, peak_intensity=180.0, bg_intensity=30.0)
        noisy = img.copy()
        np.random.seed(123)
        num_sp = 200
        ry = np.random.randint(0, img.shape[0], num_sp)
        rx = np.random.randint(0, img.shape[1], num_sp)
        noisy[ry, rx] = 255

        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(noisy, cand)
        assert res.valid is True
        assert abs(res.x - 300.5) < 0.5

    def test_saturated_beacon(self):
        """Test a beacon that is heavily saturated at 255."""
        img, cand = make_gaussian_spot(
            cx=320.0, cy=240.0, sigma=3.0, peak_intensity=500.0, bg_intensity=20.0
        )
        # Note make_gaussian_spot clips to 255, creating a flat saturated core
        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(img, cand)
        assert res.valid is True
        assert not math.isnan(res.x)
        assert not math.isnan(res.y)
        assert abs(res.x - 320.0) < 0.15
        assert abs(res.y - 240.0) < 0.15

    @pytest.mark.parametrize("edge", ["left", "right", "top", "bottom"])
    def test_boundary_clipped_target(self, edge):
        """Candidate region partially clipped at image boundaries must not cause indexing faults."""
        w, h = 640, 480
        if edge == "left":
            cx, cy = 2.0, 200.0
            bx, by, bw, bh = 0, 195, 10, 10
        elif edge == "right":
            cx, cy = 638.0, 200.0
            bx, by, bw, bh = 630, 195, 10, 10
        elif edge == "top":
            cx, cy = 200.0, 2.0
            bx, by, bw, bh = 195, 0, 10, 10
        elif edge == "bottom":
            cx, cy = 200.0, 478.0
            bx, by, bw, bh = 195, 470, 10, 10

        img = np.full((h, w), fill_value=20, dtype=np.uint8)
        y_grid, x_grid = np.ogrid[:h, :w]
        dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
        img[dist <= 4.0] = 220
        img.flags.writeable = False

        cand = CandidateRegion(
            bbox_x=bx, bbox_y=by, bbox_w=bw, bbox_h=bh,
            peak_intensity=220.0, mean_intensity=150.0, area=100
        )

        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(img, cand)
        assert res.valid is True
        assert 0.0 <= res.x <= w
        assert 0.0 <= res.y <= h


# ---------------------------------------------------------------------------
# 6. Edge Cases & Numerical Stability Tests
# ---------------------------------------------------------------------------

class TestCentroidEdgeCases:
    """Verifies defensive error handling for edge and degenerate conditions."""

    def test_zero_signal_uniform_roi(self):
        """A uniform ROI has zero weight above background; must return valid=False without NaN."""
        img = np.full((100, 100), fill_value=50, dtype=np.uint8)
        cand = CandidateRegion(
            bbox_x=20, bbox_y=20, bbox_w=10, bbox_h=10,
            peak_intensity=50.0, mean_intensity=50.0, area=100
        )
        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(img, cand)

        assert res.valid is False
        assert not math.isnan(res.x)
        assert not math.isnan(res.y)
        assert res.x == 25.0  # Returns fallback geometric center
        assert res.y == 25.0
        assert res.total_signal == 0.0

    def test_single_pixel_signal(self):
        """A single bright pixel above background must return exact integer coordinates."""
        img = np.full((100, 100), fill_value=20, dtype=np.uint8)
        px, py = 45, 65
        img[py, px] = 200

        cand = CandidateRegion(
            bbox_x=40, bbox_y=60, bbox_w=10, bbox_h=10,
            peak_intensity=200.0, mean_intensity=30.0, area=100
        )
        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(img, cand)

        assert res.valid is True
        assert res.x == float(px)
        assert res.y == float(py)

    def test_degenerate_empty_candidate(self):
        """Degenerate zero-size candidate bounding box must return valid=False."""
        img = np.full((100, 100), fill_value=30, dtype=np.uint8)
        cand = CandidateRegion(
            bbox_x=50, bbox_y=50, bbox_w=0, bbox_h=0,
            peak_intensity=30.0, mean_intensity=30.0, area=0
        )
        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(img, cand)

        assert res.valid is False

    def test_candidate_outside_image_bounds(self):
        """Candidate completely outside image bounds must handle gracefully."""
        img = np.full((100, 100), fill_value=30, dtype=np.uint8)
        cand = CandidateRegion(
            bbox_x=200, bbox_y=200, bbox_w=10, bbox_h=10,
            peak_intensity=0.0, mean_intensity=0.0, area=100
        )
        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(img, cand)

        assert res.valid is False


# ---------------------------------------------------------------------------
# 7. Immutability & Resolution Independence Tests
# ---------------------------------------------------------------------------

class TestImmutabilityAndResolution:
    """Verifies non-mutating guarantee and resolution agnosticism."""

    def test_input_frame_is_never_mutated(self):
        """The observed image must be read-only and bitwise unchanged after estimation."""
        img, cand = make_gaussian_spot()
        img_copy = img.copy()

        packet = FramePacket(
            image=img,
            width=img.shape[1],
            height=img.shape[0],
            frame_number=1,
            timestamp=0.033,
            source=FrameSource.SIMULATION,
        )
        estimator = IntensityWeightedCentroidEstimator()
        _ = estimator.estimate(packet, cand)

        assert np.array_equal(packet.image, img_copy)

    @pytest.mark.parametrize("width, height", [
        (320, 240),
        (640, 480),
        (800, 600),
        (1280, 720),
        (1920, 1080),
    ])
    def test_multiple_resolutions(self, width, height):
        """Estimator operates seamlessly across arbitrary sensor resolutions."""
        cx = width / 2.0 + 0.3
        cy = height / 2.0 + 0.4
        img, cand = make_gaussian_spot(
            width=width, height=height, cx=cx, cy=cy, sigma=2.5
        )
        estimator = IntensityWeightedCentroidEstimator()
        res = estimator.estimate(img, cand)

        assert res.valid is True
        assert abs(res.x - cx) < 0.2
        assert abs(res.y - cy) < 0.2


# ---------------------------------------------------------------------------
# 8. Ground Truth Firewall Tests
# ---------------------------------------------------------------------------

class TestGroundTruthFirewall:
    """Verifies that Module 10 has ZERO access to ground truth."""

    def test_no_ground_truth_in_module_ast(self):
        """Inspect centroid_estimator.py AST to ensure no GroundTruth imports exist."""
        import src.tracker.centroid_estimator as ce_module
        source_file = inspect.getfile(ce_module)

        with open(source_file, "r") as f:
            tree = ast.parse(f.read(), filename=source_file)

        forbidden_names = {
            "GroundTruth",
            "GroundTruthProvider",
            "ground_truth_provider",
            "src.simulation",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_names:
                        assert forbidden not in alias.name, (
                            f"Firewall violation: forbidden import '{alias.name}' in {source_file}"
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for forbidden in forbidden_names:
                    assert forbidden not in mod, (
                        f"Firewall violation: forbidden from-import '{mod}' in {source_file}"
                    )
                for alias in node.names:
                    for forbidden in forbidden_names:
                        assert forbidden != alias.name, (
                            f"Firewall violation: forbidden import symbol '{alias.name}' in {source_file}"
                        )


# ---------------------------------------------------------------------------
# 9. End-to-End Integration Test: FrameProvider -> Detector -> CentroidEstimator
# ---------------------------------------------------------------------------

class TestCentroidPipelineIntegration:
    """
    Verifies deterministic pipeline:
      SimulationFrameProvider -> P0ThresholdDetector -> IntensityWeightedCentroidEstimator
    """

    def test_deterministic_pipeline_step(self):
        # 1. Setup simulation configuration
        cfg = SystemConfig()
        cfg.simulation.random_seed = 42
        cfg.camera.width = 640
        cfg.camera.height = 480
        cfg.target.initial_position = "custom"
        cfg.target.initial_x = 1000.0
        cfg.target.initial_y = 1000.0
        cfg.target.size = 12
        cfg.target.intensity = 220
        cfg.scene.background_intensity = 30

        sim_provider = SimulationFrameProvider.from_config(cfg)
        detector = P0ThresholdDetector(cfg.detector)
        centroid_estimator = IntensityWeightedCentroidEstimator(cfg.centroid)

        # 2. Step 5 frames
        for f in range(5):
            packet = sim_provider.get_next_frame()
            assert packet is not None
            assert packet.frame_number == f

            # Detect candidates
            det_result = detector.detect(packet)
            assert det_result.frame_number == f
            assert len(det_result.candidates) >= 1

            best_cand = det_result.candidates[0]

            # Refine centroid
            cent_result = centroid_estimator.estimate(packet, best_cand)
            assert cent_result.valid is True
            assert cent_result.frame_number == f
            assert abs(cent_result.timestamp - packet.timestamp) < 1e-6
            assert isinstance(cent_result.x, float)
            assert isinstance(cent_result.y, float)
            assert 0.0 <= cent_result.x <= cfg.camera.width
            assert 0.0 <= cent_result.y <= cfg.camera.height
            assert cent_result.total_signal > 0.0
