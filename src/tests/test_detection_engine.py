"""
Phase 5.4 Detection Engine Tests (Module 9).

Tests cover:
  1. Contract Tests:
     - Implements IDetector interface
     - Output contract: DetectionResult with CandidateRegion list
     - Preserves frame_number, timestamp, and metadata
  2. Detection Tests:
     - 5x5, 10x10, and 20x20 targets (covering full PS range)
     - Target at various valid locations (center, quadrant, border)
     - Boundary-touching target
     - Multiple candidate detection
     - Empty frame / dark frame / saturated frame
  3. Robustness Tests:
     - Gaussian noise
     - Salt & Pepper noise (suppressed by median filter)
     - Varying background brightness
     - Arbitrary resolutions (320x240, 800x600, 1280x720)
     - Read-only input image immutability guarantee
  4. Isolation Tests:
     - ZERO access to GroundTruth, GroundTruthProvider, or simulator state
  5. Integration with FrameProviders:
     - Detect on SimulationFrameProvider packets
     - Detect on MP4FrameProvider packets
"""

from __future__ import annotations

import inspect
import numpy as np
import pytest

from src.interfaces.strategy_interfaces import IDetector
from src.frame.data_contracts import (
    FramePacket,
    FrameSource,
    CandidateRegion,
    DetectionResult,
    ROI,
)
from src.config.config_manager import DetectorConfig, SystemConfig
from src.tracker.detection_engine import P0ThresholdDetector, DetectionEngine
from src.frame.simulation_provider import SimulationFrameProvider
from src.frame.mp4_provider import MP4FrameProvider
from src.tests.test_frame_provider import create_synthetic_mp4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_test_frame(
    width: int = 640,
    height: int = 480,
    bg_intensity: int = 30,
    target_pos: tuple[int, int] | None = (320, 240),
    target_size: int = 10,
    target_intensity: int = 220,
    frame_number: int = 0,
    timestamp: float = 0.0,
) -> FramePacket:
    """Helper to synthesize a clean, read-only FramePacket with an optional beacon spot."""
    img = np.full((height, width), fill_value=bg_intensity, dtype=np.uint8)
    if target_pos is not None:
        tx, ty = target_pos
        half = target_size // 2
        x0 = max(0, tx - half)
        y0 = max(0, ty - half)
        x1 = min(width, x0 + target_size)
        y1 = min(height, y0 + target_size)
        img[y0:y1, x0:x1] = target_intensity

    # Enforce read-only constraint per Phase 5.3 contract
    img.flags.writeable = False

    return FramePacket(
        frame_number=frame_number,
        timestamp=timestamp,
        image=img,
        width=width,
        height=height,
        source=FrameSource.SIMULATION,
    )


# ---------------------------------------------------------------------------
# 1. Contract Tests
# ---------------------------------------------------------------------------

class TestDetectorContract:
    """Test strategy interface compliance and output contract."""

    def test_implements_interface(self):
        detector = P0ThresholdDetector()
        assert isinstance(detector, IDetector)
        assert detector.get_name() == "P0ThresholdDetector"

    def test_alias_mapping(self):
        assert DetectionEngine is P0ThresholdDetector

    def test_returns_detection_result_with_metadata(self):
        detector = P0ThresholdDetector()
        packet = make_test_frame(target_pos=(320, 240), frame_number=7, timestamp=0.233)
        res = detector.detect(packet)

        assert isinstance(res, DetectionResult)
        assert res.frame_number == 7
        assert pytest.approx(res.timestamp, abs=1e-4) == 0.233
        assert res.processing_time_ms >= 0.0
        assert len(res.candidates) >= 1

        cand = res.candidates[0]
        assert isinstance(cand, CandidateRegion)
        assert cand.area > 0
        assert 0.0 <= cand.detection_score <= 1.0
        assert cand.peak_intensity >= 200

    def test_raw_centroid_is_metadata_not_subpixel(self):
        detector = P0ThresholdDetector()
        packet = make_test_frame(target_pos=(320, 240), target_size=10)
        res = detector.detect(packet)
        cand = res.candidates[0]

        # Geometric center in CandidateRegion should be close to center (320, 240)
        assert pytest.approx(cand.raw_centroid_x, abs=2.0) == 320.0
        assert pytest.approx(cand.raw_centroid_y, abs=2.0) == 240.0


# ---------------------------------------------------------------------------
# 2. Target Detection Tests (covering full PS size range 5x5 to 20x20)
# ---------------------------------------------------------------------------

class TestTargetDetection:
    """Test detection across all valid PS beacon sizes and locations."""

    def test_detects_ideal_beacon(self):
        detector = P0ThresholdDetector()
        packet = make_test_frame(target_pos=(320, 240), target_size=10, target_intensity=220)
        res = detector.detect(packet)
        assert len(res.candidates) == 1
        c = res.candidates[0]
        assert abs(c.bbox_x + c.bbox_w / 2 - 320) <= 2
        assert abs(c.bbox_y + c.bbox_h / 2 - 240) <= 2

    def test_detects_target_size_5x5(self):
        """PS Row 10: Minimum target size is 5x5 pixels."""
        detector = P0ThresholdDetector()
        packet = make_test_frame(target_pos=(300, 200), target_size=5, target_intensity=220)
        res = detector.detect(packet)
        assert len(res.candidates) == 1
        c = res.candidates[0]
        # 5x5 area ~25 px (must pass min area filter >= 4)
        assert 15 <= c.area <= 35
        assert c.peak_intensity >= 200

    def test_detects_target_size_10x10(self):
        """PS Row 10: Default target size is 10x10 pixels."""
        detector = P0ThresholdDetector()
        packet = make_test_frame(target_pos=(300, 200), target_size=10, target_intensity=220)
        res = detector.detect(packet)
        assert len(res.candidates) == 1
        c = res.candidates[0]
        # 10x10 area ~100 px
        assert 80 <= c.area <= 110

    def test_detects_target_size_20x20(self):
        """PS Row 10: Maximum target size is 20x20 pixels."""
        detector = P0ThresholdDetector()
        packet = make_test_frame(target_pos=(300, 200), target_size=20, target_intensity=220)
        res = detector.detect(packet)
        assert len(res.candidates) == 1
        c = res.candidates[0]
        # 20x20 area ~400 px (must pass max area filter <= 500)
        assert 350 <= c.area <= 450

    def test_detects_target_at_various_locations(self):
        detector = P0ThresholdDetector()
        test_positions = [(100, 100), (500, 150), (200, 400), (450, 380)]

        for pos in test_positions:
            packet = make_test_frame(target_pos=pos, target_size=10)
            res = detector.detect(packet)
            assert len(res.candidates) == 1
            c = res.candidates[0]
            assert abs(c.raw_centroid_x - pos[0]) <= 2
            assert abs(c.raw_centroid_y - pos[1]) <= 2

    def test_detects_target_touching_boundary(self):
        detector = P0ThresholdDetector()
        # Target right at top-left corner
        packet = make_test_frame(target_pos=(5, 5), target_size=10)
        res = detector.detect(packet)
        assert len(res.candidates) == 1
        assert res.candidates[0].bbox_x == 0
        assert res.candidates[0].bbox_y == 0

    def test_detects_multiple_targets(self):
        img = np.full((480, 640), fill_value=30, dtype=np.uint8)
        # Place 3 separate beacons
        img[100:110, 100:110] = 220
        img[200:212, 300:312] = 230
        img[350:360, 500:510] = 210
        img.flags.writeable = False

        packet = FramePacket(frame_number=0, timestamp=0.0, image=img, width=640, height=480)
        detector = P0ThresholdDetector()
        res = detector.detect(packet)

        assert len(res.candidates) == 3

    def test_no_target_frame_returns_empty_candidates(self):
        detector = P0ThresholdDetector()
        packet = make_test_frame(target_pos=None)
        res = detector.detect(packet)
        assert len(res.candidates) == 0

    def test_all_dark_frame(self):
        detector = P0ThresholdDetector()
        img = np.zeros((480, 640), dtype=np.uint8)
        img.flags.writeable = False
        packet = FramePacket(frame_number=0, timestamp=0.0, image=img, width=640, height=480)
        res = detector.detect(packet)
        assert len(res.candidates) == 0

    def test_all_saturated_bright_frame(self):
        detector = P0ThresholdDetector()
        img = np.full((480, 640), fill_value=255, dtype=np.uint8)
        img.flags.writeable = False
        packet = FramePacket(frame_number=0, timestamp=0.0, image=img, width=640, height=480)
        res = detector.detect(packet)
        # Uniform bright frame has zero difference from background and full frame area exceeds max_area
        assert len(res.candidates) == 0


# ---------------------------------------------------------------------------
# 3. Robustness Tests
# ---------------------------------------------------------------------------

class TestDetectorRobustness:
    """Test performance under noise, varying backgrounds, resolutions, and immutability."""

    def test_gaussian_noise_robustness(self):
        # Create beacon with additive Gaussian noise (sigma=10)
        rng = np.random.RandomState(42)
        base = np.full((480, 640), fill_value=30, dtype=np.float32)
        base[235:245, 315:325] = 220.0
        noise = rng.normal(0, 10.0, base.shape)
        noisy = np.clip(base + noise, 0, 255).astype(np.uint8)
        noisy.flags.writeable = False

        packet = FramePacket(frame_number=0, timestamp=0.0, image=noisy, width=640, height=480)
        detector = P0ThresholdDetector()
        res = detector.detect(packet)

        # Beacon should be detected
        assert len(res.candidates) >= 1
        best = max(res.candidates, key=lambda c: c.detection_score)
        assert abs(best.raw_centroid_x - 320) <= 5
        assert abs(best.raw_centroid_y - 240) <= 5

    def test_salt_and_pepper_noise_suppressed_by_median_filter(self):
        # 10% Salt & Pepper noise (PS Row 21)
        rng = np.random.RandomState(123)
        img = np.full((480, 640), fill_value=30, dtype=np.uint8)
        img[235:245, 315:325] = 220

        # Inject S&P
        prob = rng.uniform(0, 1, img.shape)
        img[prob < 0.05] = 0
        img[(prob >= 0.05) & (prob < 0.10)] = 255
        img.flags.writeable = False

        packet = FramePacket(frame_number=0, timestamp=0.0, image=img, width=640, height=480)
        detector = P0ThresholdDetector()
        res = detector.detect(packet)

        # True beacon should be detected
        assert len(res.candidates) >= 1
        found_beacon = any(
            abs(c.raw_centroid_x - 320) <= 5 and abs(c.raw_centroid_y - 240) <= 5
            for c in res.candidates
        )
        assert found_beacon is True

    def test_varying_background_brightness(self):
        detector = P0ThresholdDetector()
        for bg in [15, 50, 90]:
            packet = make_test_frame(bg_intensity=bg, target_pos=(320, 240), target_intensity=220)
            res = detector.detect(packet)
            assert len(res.candidates) >= 1
            best = res.candidates[0]
            assert abs(best.raw_centroid_x - 320) <= 2

    def test_arbitrary_resolutions(self):
        detector = P0ThresholdDetector()
        for w, h in [(320, 240), (800, 600), (1280, 720)]:
            packet = make_test_frame(width=w, height=h, target_pos=(w // 2, h // 2), target_size=12)
            res = detector.detect(packet)
            assert len(res.candidates) == 1
            assert abs(res.candidates[0].raw_centroid_x - w // 2) <= 2
            assert abs(res.candidates[0].raw_centroid_y - h // 2) <= 2

    def test_read_only_input_unmutated(self):
        packet = make_test_frame(target_pos=(320, 240))
        assert packet.image.flags.writeable is False
        before_hash = hash(packet.image.tobytes())

        detector = P0ThresholdDetector()
        detector.detect(packet)

        assert packet.image.flags.writeable is False
        after_hash = hash(packet.image.tobytes())
        assert before_hash == after_hash


# ---------------------------------------------------------------------------
# 4. Ground-Truth Isolation Tests
# ---------------------------------------------------------------------------

class TestGroundTruthIsolation:
    """Verify detector module has zero coupling or access to ground truth."""

    def test_no_ground_truth_imports_in_detection_module(self):
        import ast
        from src.tracker import detection_engine
        source = inspect.getsource(detection_engine)
        tree = ast.parse(source)

        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.append(alias.name)

        assert "GroundTruth" not in imported_names
        assert "GroundTruthProvider" not in imported_names
        assert "target_world_x" not in source
        assert "ideal_projected_x" not in source
        assert "rendered_centroid_x" not in source

    def test_detection_result_has_no_truth_fields(self):
        detector = P0ThresholdDetector()
        packet = make_test_frame(target_pos=(320, 240))
        res = detector.detect(packet)

        assert not hasattr(res, "ground_truth")
        assert not hasattr(res, "target_world_x")
        assert not hasattr(res, "ideal_projected_x")


# ---------------------------------------------------------------------------
# 5. Integration with FrameProviders
# ---------------------------------------------------------------------------

class TestFrameProviderIntegration:
    """Verify detector works seamlessly with both FrameProvider sources."""

    def test_detect_simulation_frame_provider(self):
        cfg = SystemConfig()
        cfg.simulation.random_seed = 42
        cfg.target.initial_position = "custom"
        cfg.target.initial_x = 1000.0
        cfg.target.initial_y = 1000.0
        cfg.target.size = 12
        cfg.target.intensity = 220

        sim_provider = SimulationFrameProvider.from_config(cfg)
        packet = sim_provider.get_next_frame()
        assert packet is not None

        detector = P0ThresholdDetector()
        res = detector.detect(packet)

        assert res.frame_number == packet.frame_number
        assert len(res.candidates) >= 1

    def test_detect_mp4_frame_provider(self, tmp_path):
        video_path = str(tmp_path / "detector_mp4_test.mp4")
        create_synthetic_mp4(video_path, width=480, height=360, fps=30.0, num_frames=5)

        with MP4FrameProvider(video_path) as mp4_prov:
            packet = mp4_prov.get_next_frame()
            assert packet is not None

            detector = P0ThresholdDetector()
            res = detector.detect(packet)

            assert res.frame_number == 0
            assert len(res.candidates) >= 1

    def test_detect_large_target_in_small_roi_no_self_masking(self):
        """Verifies that a 20x20 target occupying 11% of a 60x60 ROI does not self-mask."""
        img = np.full((480, 640), 30, dtype=np.uint8)
        # Place 20x20 bright beacon at (320, 240)
        img[230:250, 310:330] = 220

        detector = P0ThresholdDetector()
        roi = ROI(x=290, y=210, width=60, height=60)
        packet = FramePacket(frame_number=1, timestamp=0.033, image=img, width=640, height=480)

        res = detector.detect(packet, roi=roi)
        assert len(res.candidates) >= 1
        cand = res.candidates[0]
        assert abs(cand.bbox_w - 20) <= 2
        assert abs(cand.bbox_h - 20) <= 2

