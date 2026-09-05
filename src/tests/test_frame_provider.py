"""
Phase 5.3 FrameProvider Tests

Tests cover:
  - SimulationFrameProvider:
      * Implements IFrameProvider interface
      * Frame ordering and sequential numbers
      * Timestamps match simulation clock
      * Image resolution, shape, and dtype
      * Source identification as SIMULATION
      * Deterministic sequence with identical seed
      * Zero-copy immutability (write=False)
      * Exhaustion when max_duration_s is reached
      * Reset behavior
      * Zero ground-truth leakage into FramePacket
  - MP4FrameProvider:
      * Implements IFrameProvider interface
      * Successful open and metadata extraction (FPS, count, resolution)
      * Frame ordering and sequential numbers
      * Timestamps from container / fallback
      * Arbitrary resolution preservation (testing 320x240 and 800x600)
      * Automatic conversion of 3-channel BGR to monochrome uint8
      * End-of-stream clean handling (returns None, is_exhausted is True)
      * Non-existent file raises FileNotFoundError
      * Corrupt/invalid file raises ValueError
      * Zero-copy immutability (write=False)
      * Reset behavior (rewinds to frame 0)
  - Common Contract Equivalence:
      * Both providers satisfy the exact same IFrameProvider ABC
      * Both emit identical FramePacket dataclass structure
  - AppController Integration:
      * SIMULATION mode produces FramePacket via get_next_frame()
      * MP4 mode produces FramePacket via get_next_frame()
"""

from __future__ import annotations

import os
import tempfile
import cv2
import numpy as np
import pytest

from src.interfaces.strategy_interfaces import IFrameProvider
from src.frame.data_contracts import FramePacket, FrameSource
from src.frame.simulation_provider import SimulationFrameProvider
from src.frame.mp4_provider import MP4FrameProvider
from src.config.config_manager import SystemConfig
from src.app.app_controller import AppController


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

def create_synthetic_mp4(
    file_path: str,
    width: int = 320,
    height: int = 240,
    fps: float = 25.0,
    num_frames: int = 10,
) -> None:
    """Helper to generate a deterministic synthetic video file using OpenCV."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(file_path, fourcc, fps, (width, height))
    for i in range(num_frames):
        # Draw a moving white square on a dark gray background
        frame = np.full((height, width, 3), fill_value=30, dtype=np.uint8)
        x = int(10 + i * (width - 40) / max(1, num_frames))
        y = int(height / 2 - 10)
        frame[y : y + 20, x : x + 20] = [220, 220, 220]  # BGR white beacon
        out.write(frame)
    out.release()


# ---------------------------------------------------------------------------
# 1. SimulationFrameProvider Tests
# ---------------------------------------------------------------------------

class TestSimulationFrameProvider:
    """Test the simulation adapter conforming to IFrameProvider."""

    def test_implements_interface(self):
        cfg = SystemConfig()
        provider = SimulationFrameProvider.from_config(cfg)
        assert isinstance(provider, IFrameProvider)
        assert provider.get_source_type() == FrameSource.SIMULATION.value
        assert provider.fps == 30.0
        assert provider.resolution == (640, 480)

    def test_frame_ordering_and_timestamps(self):
        cfg = SystemConfig()
        cfg.camera.update_rate_hz = 30
        provider = SimulationFrameProvider.from_config(cfg)

        for expected_num in range(15):
            packet = provider.get_next_frame()
            assert packet is not None
            assert packet.frame_number == expected_num
            expected_time = expected_num * (1.0 / 30.0)
            assert pytest.approx(packet.timestamp, abs=1e-5) == expected_time
            assert packet.source == FrameSource.SIMULATION

    def test_frame_packet_contract_and_immutability(self):
        cfg = SystemConfig()
        provider = SimulationFrameProvider.from_config(cfg)
        packet = provider.get_next_frame()

        assert packet is not None
        assert isinstance(packet, FramePacket)
        assert packet.width == 640
        assert packet.height == 480
        assert packet.image.shape == (480, 640)
        assert packet.image.dtype == np.uint8

        # Test immutability: array should be marked read-only
        assert packet.image.flags.writeable is False
        with pytest.raises(ValueError):
            packet.image[0, 0] = 255

    def test_zero_ground_truth_leakage(self):
        cfg = SystemConfig()
        provider = SimulationFrameProvider.from_config(cfg)
        packet = provider.get_next_frame()

        assert packet is not None
        # Verify packet contains no ground-truth attributes
        assert not hasattr(packet, "ground_truth")
        assert not hasattr(packet, "target_world_x")
        assert not hasattr(packet, "target_world_y")
        assert not hasattr(packet, "ideal_projected_x")
        assert not hasattr(packet, "rendered_centroid_x")

        # But side-channel GroundTruthProvider DOES record truth
        gt = provider.ground_truth_provider.get_truth(0)
        assert gt is not None
        assert gt.frame_number == 0
        assert gt.target_world_x is not None

    def test_deterministic_sequence(self):
        cfg1 = SystemConfig()
        cfg1.simulation.random_seed = 12345
        prov1 = SimulationFrameProvider.from_config(cfg1)

        cfg2 = SystemConfig()
        cfg2.simulation.random_seed = 12345
        prov2 = SimulationFrameProvider.from_config(cfg2)

        for _ in range(10):
            p1 = prov1.get_next_frame()
            p2 = prov2.get_next_frame()
            assert p1.frame_number == p2.frame_number
            assert p1.timestamp == p2.timestamp
            assert np.array_equal(p1.image, p2.image)

    def test_exhaustion_with_duration_limit(self):
        cfg = SystemConfig()
        cfg.camera.update_rate_hz = 10
        cfg.simulation.duration_s = 0.5  # 5 frames at 10 Hz
        provider = SimulationFrameProvider.from_config(cfg)

        frames = []
        while not provider.is_exhausted():
            pkt = provider.get_next_frame()
            if pkt is not None:
                frames.append(pkt)

        assert len(frames) == 5
        assert provider.is_exhausted() is True
        assert provider.get_next_frame() is None

    def test_reset_behavior(self):
        cfg = SystemConfig()
        cfg.camera.update_rate_hz = 20
        provider = SimulationFrameProvider.from_config(cfg)

        p0 = provider.get_next_frame()
        p1 = provider.get_next_frame()
        assert p1.frame_number == 1

        provider.reset()
        assert provider.frame_count == 0
        p0_after = provider.get_next_frame()
        assert p0_after.frame_number == 0
        assert p0_after.timestamp == 0.0


# ---------------------------------------------------------------------------
# 2. MP4FrameProvider Tests
# ---------------------------------------------------------------------------

class TestMP4FrameProvider:
    """Test the MP4 video adapter conforming to IFrameProvider."""

    def test_open_and_decode_320x240(self, tmp_path):
        video_path = str(tmp_path / "test_320x240.mp4")
        create_synthetic_mp4(video_path, width=320, height=240, fps=20.0, num_frames=8)

        provider = MP4FrameProvider(video_path)
        assert isinstance(provider, IFrameProvider)
        assert provider.get_source_type() == FrameSource.MP4_FILE.value
        assert provider.resolution == (320, 240)
        assert pytest.approx(provider.fps, abs=1.0) == 20.0
        assert provider.total_frames == 8

        frames = []
        for i in range(8):
            packet = provider.get_next_frame()
            assert packet is not None
            assert packet.frame_number == i
            assert packet.width == 320
            assert packet.height == 240
            assert packet.image.shape == (240, 320)
            assert packet.image.dtype == np.uint8
            assert packet.source == FrameSource.MP4_FILE
            frames.append(packet)

        assert len(frames) == 8
        # Next read should report exhaustion
        assert provider.get_next_frame() is None
        assert provider.is_exhausted() is True
        provider.close()

    def test_arbitrary_resolution_800x600_preservation(self, tmp_path):
        """Verify provider does NOT resize or force 640x480."""
        video_path = str(tmp_path / "test_800x600.mp4")
        create_synthetic_mp4(video_path, width=800, height=600, fps=30.0, num_frames=5)

        provider = MP4FrameProvider(video_path)
        assert provider.resolution == (800, 600)

        packet = provider.get_next_frame()
        assert packet is not None
        assert packet.width == 800
        assert packet.height == 600
        assert packet.image.shape == (600, 800)
        provider.close()

    def test_monochrome_uint8_conversion(self, tmp_path):
        """Verify 3-channel video frames are converted to single-channel 2D monochrome."""
        video_path = str(tmp_path / "color_video.mp4")
        create_synthetic_mp4(video_path, width=320, height=240, fps=25.0, num_frames=3)

        with MP4FrameProvider(video_path) as provider:
            packet = provider.get_next_frame()
            assert packet is not None
            assert len(packet.image.shape) == 2  # 2D array, not 3D
            assert packet.image.dtype == np.uint8

    def test_immutability(self, tmp_path):
        video_path = str(tmp_path / "immut_test.mp4")
        create_synthetic_mp4(video_path, width=320, height=240, num_frames=2)

        with MP4FrameProvider(video_path) as provider:
            packet = provider.get_next_frame()
            assert packet.image.flags.writeable is False
            with pytest.raises(ValueError):
                packet.image[0, 0] = 255

    def test_reset_and_rewind(self, tmp_path):
        video_path = str(tmp_path / "rewind_test.mp4")
        create_synthetic_mp4(video_path, width=320, height=240, num_frames=6)

        provider = MP4FrameProvider(video_path)
        p0 = provider.get_next_frame()
        p1 = provider.get_next_frame()
        assert p1.frame_number == 1

        provider.reset()
        assert provider.frame_count == 0
        assert provider.is_exhausted() is False

        p0_rewound = provider.get_next_frame()
        assert p0_rewound.frame_number == 0
        assert np.array_equal(p0.image, p0_rewound.image)
        provider.close()

    def test_nonexistent_file_raises_filenotfound(self):
        with pytest.raises(FileNotFoundError):
            MP4FrameProvider("non_existent_file_xyz_123.mp4")

    def test_corrupt_file_raises_valueerror(self, tmp_path):
        corrupt_file = str(tmp_path / "corrupt.mp4")
        with open(corrupt_file, "wb") as f:
            f.write(b"NOT_A_VALID_MP4_HEADER_DATA")

        with pytest.raises(ValueError):
            MP4FrameProvider(corrupt_file)


# ---------------------------------------------------------------------------
# 3. Contract Equivalence Tests
# ---------------------------------------------------------------------------

class TestContractEquivalence:
    """Verify that both providers yield identical contract structure."""

    def test_downstream_contract_identical(self, tmp_path):
        # 1. Simulation Provider
        sim_cfg = SystemConfig()
        sim_prov = SimulationFrameProvider.from_config(sim_cfg)
        sim_packet = sim_prov.get_next_frame()

        # 2. MP4 Provider
        video_path = str(tmp_path / "contract_equiv.mp4")
        create_synthetic_mp4(video_path, width=640, height=480, fps=30.0, num_frames=3)
        mp4_prov = MP4FrameProvider(video_path)
        mp4_packet = mp4_prov.get_next_frame()

        # Compare dataclass fields
        sim_fields = {k: type(v) for k, v in sim_packet.__dict__.items()}
        mp4_fields = {k: type(v) for k, v in mp4_packet.__dict__.items()}

        assert sim_fields.keys() == mp4_fields.keys()
        for k in sim_fields:
            assert sim_fields[k] == mp4_fields[k], f"Type mismatch for field {k}"

        # Both images must be 2D uint8 read-only ndarrays
        assert isinstance(sim_packet.image, np.ndarray)
        assert isinstance(mp4_packet.image, np.ndarray)
        assert sim_packet.image.ndim == 2
        assert mp4_packet.image.ndim == 2
        assert sim_packet.image.dtype == np.uint8
        assert mp4_packet.image.dtype == np.uint8
        assert sim_packet.image.flags.writeable is False
        assert mp4_packet.image.flags.writeable is False

        mp4_prov.close()


# ---------------------------------------------------------------------------
# 4. AppController Integration with FrameProvider
# ---------------------------------------------------------------------------

class TestAppControllerFrameProviderIntegration:
    """Verify AppController wires FrameProvider appropriately in both modes."""

    def test_app_controller_simulation_mode(self):
        app = AppController()
        app.initialize()  # Default mode is SIMULATION

        assert app.frame_provider is not None
        assert isinstance(app.frame_provider, SimulationFrameProvider)
        assert app.frame_provider.get_source_type() == FrameSource.SIMULATION.value

        packet = app.get_next_frame()
        assert packet is not None
        assert packet.source == FrameSource.SIMULATION
        assert packet.frame_number == 0

    def test_app_controller_mp4_mode(self, tmp_path):
        video_path = str(tmp_path / "app_ctrl_test.mp4")
        create_synthetic_mp4(video_path, width=400, height=300, fps=25.0, num_frames=5)

        cfg = SystemConfig()
        cfg.simulation.mode = "MP4"
        cfg.simulation.mp4_path = video_path

        app = AppController()
        app.initialize(cfg)

        assert app.frame_provider is not None
        assert isinstance(app.frame_provider, MP4FrameProvider)
        assert app.frame_provider.get_source_type() == FrameSource.MP4_FILE.value
        # Verify simulation modules are None in MP4 mode (firewall enforcement)
        assert app.scene_manager is None
        assert app.target_manager is None
        assert app.camera_model is None
        assert app.disturbance_engine is None
        assert app.ground_truth_provider is None

        packet = app.get_next_frame()
        assert packet is not None
        assert packet.source == FrameSource.MP4_FILE
        assert packet.width == 400
        assert packet.height == 300
        assert packet.frame_number == 0
        app.stop()
