"""
Benchmark 2 (BM2) Evaluator Workflow Test Suite.
Verifies:
  1. MP4 loading across arbitrary resolutions (640x480, 800x600).
  2. Frame extraction, monochrome conversion, read-only guarantees.
  3. Strict ground-truth firewall (GroundTruthProvider is None, no simulation state leakage).
  4. PTZ actuation bypass (no camera model actuation in MP4 mode).
  5. Downstream detection, sub-pixel centroiding, and Kalman tracking.
  6. Batch MP4 evaluation and Grand Evaluator report generation.
"""

import os
import shutil
import tempfile
import cv2
import numpy as np
import pytest

from src.app.app_controller import AppController
from src.evaluation.benchmark_manager import BenchmarkManager
from src.frame.data_contracts import FrameSource
from src.frame.mp4_provider import MP4FrameProvider


def create_test_mp4(filepath: str, num_frames: int = 45, width: int = 640, height: int = 480):
    """Generates an MP4 video with a moving bright beacon against dark background."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(filepath, fourcc, 30.0, (width, height), isColor=True)
    for i in range(num_frames):
        # 3-channel BGR background
        frame = np.full((height, width, 3), 30, dtype=np.uint8)
        # Moving beacon
        cx = int(width / 2.0 + 80.0 * np.sin(i * 0.15))
        cy = int(height / 2.0 + 50.0 * np.cos(i * 0.15))
        cv2.circle(frame, (cx, cy), 6, (230, 230, 230), -1)
        out.write(frame)
    out.release()


@pytest.fixture
def temp_mp4_env():
    d = tempfile.mkdtemp(prefix="sih_bm2_")
    mp4_dir = os.path.join(d, "videos")
    out_dir = os.path.join(d, "output")
    os.makedirs(mp4_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    yield d, mp4_dir, out_dir
    shutil.rmtree(d, ignore_errors=True)


def test_mp4_frame_provider_arbitrary_resolutions(temp_mp4_env):
    """Verifies MP4FrameProvider correctly decodes arbitrary resolutions and outputs monochrome uint8."""
    _, mp4_dir, _ = temp_mp4_env

    for w, h in ((640, 480), (800, 600)):
        path = os.path.join(mp4_dir, f"test_{w}x{h}.mp4")
        create_test_mp4(path, num_frames=10, width=w, height=h)

        provider = MP4FrameProvider(path)
        assert provider.resolution == (w, h)
        assert provider.fps == 30.0
        assert provider.get_source_type() == FrameSource.MP4_FILE.value

        packet = provider.get_next_frame()
        assert packet is not None
        assert packet.width == w
        assert packet.height == h
        assert packet.image.shape == (h, w)
        assert packet.image.dtype == np.uint8
        assert packet.source == FrameSource.MP4_FILE
        assert packet.image.flags.writeable is False

        provider.close()


def test_bm2_ground_truth_firewall_and_ptz_bypass(temp_mp4_env):
    """Verifies that MP4 mode completely isolates simulation state and bypasses PTZ."""
    _, mp4_dir, out_dir = temp_mp4_env
    path = os.path.join(mp4_dir, "test_eval.mp4")
    create_test_mp4(path, num_frames=30, width=640, height=480)

    app = AppController()
    app.config_manager.update_section(
        "simulation",
        mode="MP4",
        mp4_path=path,
    )
    app.config_manager.update_section("logging", output_dir=out_dir)
    app.initialize()

    # Verify firewall invariants: simulation internals MUST be None
    assert app.ground_truth_provider is None
    assert app.camera_model is None
    assert app.target_manager is None
    assert app.scene_manager is None
    assert app.disturbance_engine is None

    bm = BenchmarkManager(app)
    summary = bm.run_benchmark()
    app.stop()

    assert summary.total_frames == 30
    assert summary.frames_tracked_count >= 15
    assert summary.detection_rate >= 0.6
    # Ground truth RMSE should be 0.0 because no ground truth exists in MP4 mode
    assert summary.rmse_centroid == 0.0

    # Verify telemetry CSV was logged
    logged_files = os.listdir(out_dir)
    assert any(f.endswith("_telemetry.csv") for f in logged_files)


def test_bm2_batch_evaluation_and_grand_report(temp_mp4_env):
    """Verifies evaluate_batch_mp4s processes multiple videos and creates grand scorecard."""
    _, mp4_dir, out_dir = temp_mp4_env
    for i in range(2):
        create_test_mp4(os.path.join(mp4_dir, f"video_{i}.mp4"), num_frames=20)

    bm = BenchmarkManager()
    grand = bm.evaluate_batch_mp4s(
        mp4_dir=mp4_dir,
        output_dir=out_dir,
    )

    assert grand.batch_type == "MP4"
    assert grand.total_runs == 2
    assert grand.successful_runs == 2
    assert grand.failed_runs == 0
    assert grand.total_frames_processed == 40
    assert grand.mean_fps > 20.0

    # Verify reports exist
    out_files = os.listdir(out_dir)
    assert any(f.endswith("_grand_summary.json") for f in out_files)
    assert any(f.endswith("_grand_evaluator_report.md") for f in out_files)


def test_bm2_evaluator_reference_comparator_valid_csv(temp_mp4_env):
    """Verifies BM2 correctly ingests an external evaluator reference CSV and calculates sub-pixel RMSE."""
    _, mp4_dir, out_dir = temp_mp4_env
    video_path = os.path.join(mp4_dir, "eval_ref_test.mp4")
    ref_csv_path = os.path.join(mp4_dir, "eval_ref_test.csv")

    num_frames = 30
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height), isColor=True)

    # Generate video and reference CSV independently
    ref_coords = []
    with open(ref_csv_path, "w", encoding="utf-8") as f_csv:
        f_csv.write("frame,true_x,true_y\n")
        for i in range(num_frames):
            frame = np.full((height, width, 3), 30, dtype=np.uint8)
            cx = float(int(width / 2.0 + 80.0 * np.sin(i * 0.15)))
            cy = float(int(height / 2.0 + 50.0 * np.cos(i * 0.15)))
            cv2.circle(frame, (int(cx), int(cy)), 6, (230, 230, 230), -1)
            out.write(frame)
            f_csv.write(f"{i},{cx:.2f},{cy:.2f}\n")
            ref_coords.append((cx, cy))
    out.release()

    app = AppController()
    app.config_manager.update_section("simulation", mode="MP4", mp4_path=video_path)
    app.config_manager.update_section("logging", output_dir=out_dir)
    app.initialize()

    bm = BenchmarkManager(app)
    summary = bm.run_benchmark(reference_csv=ref_csv_path)
    app.stop()

    assert summary.total_frames == num_frames
    assert summary.reference_frames_matched == num_frames
    assert summary.reference_frame_coverage_pct == 100.0
    assert summary.rmse_centroid > 0.0
    # True beacon circle vs sub-pixel centroid should have sub-pixel agreement (< 0.5 px)
    assert summary.rmse_centroid < 0.5
    assert summary.mean_centroid_error < 0.5


def test_bm2_evaluator_reference_offset_rmse(temp_mp4_env):
    """Verifies that an intentionally offset reference file produces an expected measured RMSE."""
    _, mp4_dir, out_dir = temp_mp4_env
    video_path = os.path.join(mp4_dir, "offset_test.mp4")
    ref_csv_path = os.path.join(mp4_dir, "offset_test.csv")

    num_frames = 20
    create_test_mp4(video_path, num_frames=num_frames, width=640, height=480)

    # Intentionally offset reference by +10.0 px in X and +0.0 px in Y
    with open(ref_csv_path, "w", encoding="utf-8") as f_csv:
        f_csv.write("frame,true_x,true_y\n")
        for i in range(num_frames):
            cx = float(int(640 / 2.0 + 80.0 * np.sin(i * 0.15))) + 10.0
            cy = float(int(480 / 2.0 + 50.0 * np.cos(i * 0.15)))
            f_csv.write(f"{i},{cx:.2f},{cy:.2f}\n")

    app = AppController()
    app.config_manager.update_section("simulation", mode="MP4", mp4_path=video_path)
    app.config_manager.update_section("logging", output_dir=out_dir)
    app.initialize()

    bm = BenchmarkManager(app)
    summary = bm.run_benchmark(reference_csv=ref_csv_path)
    app.stop()

    # Measured RMSE must be approximately 10 px (within 0.5 px due to subpixel centroid accuracy)
    assert 9.5 <= summary.rmse_centroid <= 10.5


def test_bm2_evaluator_reference_missing_and_malformed_handling(temp_mp4_env):
    """Verifies error handling for missing and malformed reference CSVs."""
    _, mp4_dir, out_dir = temp_mp4_env
    video_path = os.path.join(mp4_dir, "error_test.mp4")
    create_test_mp4(video_path, num_frames=10)

    app = AppController()
    app.config_manager.update_section("simulation", mode="MP4", mp4_path=video_path)
    app.config_manager.update_section("logging", output_dir=out_dir)
    app.initialize()
    bm = BenchmarkManager(app)

    # 1. Missing file
    with pytest.raises(FileNotFoundError):
        bm.run_benchmark(reference_csv="non_existent_reference_xyz.csv")

    # 2. Malformed CSV (bad header)
    bad_csv_path = os.path.join(mp4_dir, "bad_header.csv")
    with open(bad_csv_path, "w") as f:
        f.write("invalid_col1,invalid_col2\n1,2\n")
    with pytest.raises(ValueError):
        bm.run_benchmark(reference_csv=bad_csv_path)

    # 3. Malformed row (non-numeric coordinates)
    bad_row_path = os.path.join(mp4_dir, "bad_row.csv")
    with open(bad_row_path, "w") as f:
        f.write("frame,true_x,true_y\n0,not_a_number,240.0\n")
    with pytest.raises(ValueError):
        bm.run_benchmark(reference_csv=bad_row_path)

    app.stop()


def test_bm2_evaluator_reference_partial_frame_coverage(temp_mp4_env):
    """Verifies handling when reference CSV contains only a subset of video frames."""
    _, mp4_dir, out_dir = temp_mp4_env
    video_path = os.path.join(mp4_dir, "partial_test.mp4")
    ref_csv_path = os.path.join(mp4_dir, "partial_test.csv")

    num_frames = 20
    create_test_mp4(video_path, num_frames=num_frames)

    # Supply reference only for even frames (10 out of 20)
    with open(ref_csv_path, "w") as f_csv:
        f_csv.write("frame,true_x,true_y\n")
        for i in range(0, num_frames, 2):
            cx = float(int(640 / 2.0 + 80.0 * np.sin(i * 0.15)))
            cy = float(int(480 / 2.0 + 50.0 * np.cos(i * 0.15)))
            f_csv.write(f"{i},{cx:.2f},{cy:.2f}\n")

    app = AppController()
    app.config_manager.update_section("simulation", mode="MP4", mp4_path=video_path)
    app.config_manager.update_section("logging", output_dir=out_dir)
    app.initialize()

    bm = BenchmarkManager(app)
    summary = bm.run_benchmark(reference_csv=ref_csv_path)
    app.stop()

    assert summary.total_frames == num_frames
    assert summary.reference_frames_matched == 10
    assert summary.reference_frame_coverage_pct == 50.0
    assert summary.rmse_centroid > 0.0


def test_bm2_reference_firewall_integrity(temp_mp4_env):
    """Verifies that reference data flows strictly to metrics and never enters tracker components."""
    _, mp4_dir, out_dir = temp_mp4_env
    video_path = os.path.join(mp4_dir, "firewall_test.mp4")
    ref_csv_path = os.path.join(mp4_dir, "firewall_test.csv")

    create_test_mp4(video_path, num_frames=15)
    with open(ref_csv_path, "w") as f:
        f.write("frame,true_x,true_y\n")
        for i in range(15):
            f.write(f"{i},320.0,240.0\n")

    app = AppController()
    app.config_manager.update_section("simulation", mode="MP4", mp4_path=video_path)
    app.config_manager.update_section("logging", output_dir=out_dir)
    app.initialize()

    bm = BenchmarkManager(app)
    summary = bm.run_benchmark(reference_csv=ref_csv_path)
    app.stop()

    # Assert tracking components never held ground truth or reference attributes
    assert not hasattr(app.detection_engine, "ground_truth")
    assert not hasattr(app.centroid_estimator, "ground_truth")
    assert not hasattr(app.tracking_engine, "ground_truth")
    assert not hasattr(app.ptz_controller, "ground_truth")
    assert app.ground_truth_provider is None
    assert app.camera_model is None

