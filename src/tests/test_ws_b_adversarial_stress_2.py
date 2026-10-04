"""
Adversarial Stress Testing & Invariant Verification Suite for Workstream B (Gen 2).
Authored by Challenger 2 (critic, specialist).

Focus Areas:
  1. DEF-14: Raster-Scan Noise Index Swapping Adversarial Falsification & Anti-Hijack Hysteresis
  2. DEF-14 / Kinematics: Track Age, Staleness Hysteresis, and Velocity Retention during Disappearance
  3. DEF-27/31: Dataset Generator & NoiseConfig gaussian_sigma / gaussian_std Compatibility
  4. DEF-02 / DEF-24: Static Ground-Truth Firewall Audit across Frontend Viewports
"""

import math
import os
import random
import tempfile
from pathlib import Path
from typing import List, Tuple, Any, Optional

import numpy as np
import pytest

from src.frame.data_contracts import (
    CandidateRegion,
    ScoredCandidate,
    TrackingState,
    CentroidResult,
    TrackResult,
)
from src.config.config_manager import (
    ConfigManager,
    NoiseConfig,
    IdentifierConfig,
)
from src.config import defaults
from src.tracker.candidate_identifier import CandidateIdentifier, _SpatialTrack
from src.tracker.temporal_tracker import ConstantVelocityKalmanTracker
from src.tracker.state_manager import TrackingStateManager
from src.simulation.disturbance_engine import DisturbanceEngine
from src.data.dataset_generator import SyntheticDatasetGenerator


# =============================================================================
# STRESS TEST 1: Raster-Scan Noise Index Swapping Adversarial Falsification
# =============================================================================

class TestStressTest1RasterScanNoiseIndexSwapping:
    """
    Stress Test 1: Raster-Scan Noise Index Swapping Adversarial Falsification.
    In CandidateIdentifier, inject candidate detections where high-scoring noise
    detections are placed above and to the left of the true beacon (e.g. noise at (50, 50),
    true beacon at (200, 200)). In OpenCV raster-scan order, noise gets candidate_id 0
    and true beacon gets candidate_id 1. On subsequent frames, jitter the positions
    and insert/remove noise. Assert that CandidateIdentifier maintains continuous spatial
    tracking on the true beacon's persistent track ID and NEVER swaps lock to the noise.
    """

    def test_raster_scan_noise_index_swapping_continuous_lock(self):
        """
        100-frame adversarial simulation:
        - True beacon initialized at (200, 200).
        - Noise injected at (50, 50) with higher detection score (0.98 vs 0.88).
        - In raster-scan order, noise gets candidate_id 0 and true beacon gets candidate_id 1.
        - Noise is intermittently present (75% of frames) with position jitter.
        - True beacon position wanders with Brownian jitter.
        - Verified: CandidateIdentifier NEVER swaps to noise across all 100 frames.
        """
        random.seed(42)
        ci = CandidateIdentifier()

        # Frame 1: True beacon discovered at (200, 200) in SEARCHING mode
        beacon_f1 = CandidateRegion(
            bbox_x=195, bbox_y=195, bbox_w=10, bbox_h=10,
            peak_intensity=220, mean_intensity=200, area=100,
            raw_centroid_x=200.0, raw_centroid_y=200.0,
            candidate_id=0, detection_score=0.90,
        )
        res_f1 = ci.identify([beacon_f1], current_state=TrackingState.SEARCHING, frame_number=1)
        assert res_f1.valid is True
        beacon_track_id = res_f1.selected_candidate_id
        assert beacon_track_id is not None

        bx, by = 200.0, 200.0
        swapped_frames = []

        for fn in range(2, 102):
            # True beacon wanders slightly
            bx += random.uniform(-0.8, 0.8)
            by += random.uniform(-0.8, 0.8)

            candidates: List[CandidateRegion] = []
            has_noise = (fn % 4 != 0)  # Noise present in 75% of frames

            if has_noise:
                # Noise placed above and left (raster scan index 0)
                nx = 50.0 + random.uniform(-3.0, 3.0)
                ny = 50.0 + random.uniform(-3.0, 3.0)
                noise_cand = CandidateRegion(
                    bbox_x=int(nx - 5), bbox_y=int(ny - 5), bbox_w=10, bbox_h=10,
                    peak_intensity=255, mean_intensity=245, area=100,
                    raw_centroid_x=nx, raw_centroid_y=ny,
                    candidate_id=0, detection_score=0.98,  # Higher score than beacon
                )
                candidates.append(noise_cand)
                beacon_raster_id = 1
            else:
                beacon_raster_id = 0

            beacon_cand = CandidateRegion(
                bbox_x=int(bx - 5), bbox_y=int(by - 5), bbox_w=10, bbox_h=10,
                peak_intensity=210, mean_intensity=190, area=100,
                raw_centroid_x=bx, raw_centroid_y=by,
                candidate_id=beacon_raster_id, detection_score=0.88,
            )
            candidates.append(beacon_cand)

            r = ci.identify(
                candidates,
                predicted_position=(bx, by),
                current_state=TrackingState.TRACKING,
                frame_number=fn,
            )

            assert r.valid is True
            assert r.selected_candidate is not None
            # Verify spatial continuity
            sel_pos = ci._get_candidate_pos(r.selected_candidate)
            dist_to_beacon = math.hypot(sel_pos[0] - bx, sel_pos[1] - by)

            if r.selected_candidate_id != beacon_track_id or dist_to_beacon > 5.0:
                swapped_frames.append((fn, r.selected_candidate_id, dist_to_beacon))

        assert len(swapped_frames) == 0, (
            f"Adversarial lock swapped to noise on {len(swapped_frames)} frames: {swapped_frames}"
        )

    def test_multi_distractor_raster_scan_precedence(self):
        """
        Adversarial test with 3 distinct noise artifacts placed prior to the beacon
        in raster-scan order (indices 0, 1, 2; beacon is index 3).
        Asserts beacon's persistent track ID is preserved without corruption.
        """
        ci = CandidateIdentifier()

        # Frame 1: Establish beacon lock
        b = CandidateRegion(
            bbox_x=295, bbox_y=295, bbox_w=10, bbox_h=10,
            peak_intensity=220, mean_intensity=200, area=100,
            raw_centroid_x=300.0, raw_centroid_y=300.0,
            candidate_id=0, detection_score=0.90,
        )
        r1 = ci.identify([b], current_state=TrackingState.SEARCHING, frame_number=1)
        beacon_track_id = r1.selected_candidate_id

        # Frame 2: Inject 3 noise distractors earlier in raster scan
        noises = [
            CandidateRegion(bbox_x=20, bbox_y=20, bbox_w=10, bbox_h=10, peak_intensity=250, mean_intensity=240, area=100, raw_centroid_x=25.0, raw_centroid_y=25.0, candidate_id=0, detection_score=0.95),
            CandidateRegion(bbox_x=50, bbox_y=80, bbox_w=10, bbox_h=10, peak_intensity=240, mean_intensity=230, area=100, raw_centroid_x=55.0, raw_centroid_y=85.0, candidate_id=1, detection_score=0.92),
            CandidateRegion(bbox_x=100, bbox_y=40, bbox_w=10, bbox_h=10, peak_intensity=245, mean_intensity=235, area=100, raw_centroid_x=105.0, raw_centroid_y=45.0, candidate_id=2, detection_score=0.94),
        ]
        beacon_f2 = CandidateRegion(
            bbox_x=296, bbox_y=296, bbox_w=10, bbox_h=10,
            peak_intensity=220, mean_intensity=200, area=100,
            raw_centroid_x=301.0, raw_centroid_y=301.0,
            candidate_id=3, detection_score=0.89,
        )

        r2 = ci.identify(
            noises + [beacon_f2],
            predicted_position=(300.0, 300.0),
            current_state=TrackingState.TRACKING,
            frame_number=2,
        )

        assert r2.selected_candidate_id == beacon_track_id
        assert math.isclose(r2.selected_candidate.raw_centroid_x, 301.0, abs_tol=0.1)


# =============================================================================
# STRESS TEST 2: Track Age & Staleness Hysteresis Stress
# =============================================================================

class TestStressTest2TrackAgeStalenessHysteresis:
    """
    Stress Test 2: Track Age & Staleness Hysteresis Stress.
    Test beacon disappearance for 1..5 frames (verify track survives and retains position/velocity),
    and test disappearance for 6+ frames (verify track is purged cleanly without memory leaks).
    """

    def test_candidate_identifier_staleness_with_clutter(self):
        """
        When beacon disappears but background clutter/noise is present:
        - Frames 1..5: track survives in _tracks with incrementing missed_frames (1..5), retaining position.
        - Frame 6+: track is purged cleanly from _tracks (missed_frames > 5), preventing memory leak.
        """
        ci = CandidateIdentifier()

        # Initialize beacon at (200, 200)
        beacon = CandidateRegion(
            bbox_x=195, bbox_y=195, bbox_w=10, bbox_h=10,
            peak_intensity=220, mean_intensity=200, area=100,
            raw_centroid_x=200.0, raw_centroid_y=200.0,
            candidate_id=0, detection_score=0.90,
        )
        r1 = ci.identify([beacon], current_state=TrackingState.SEARCHING, frame_number=1)
        track_id = r1.selected_candidate_id
        assert track_id in ci._tracks
        init_pos = ci._tracks[track_id].pos

        # Noise distractor at (50, 50) (far outside gate 200 px)
        noise = CandidateRegion(
            bbox_x=45, bbox_y=45, bbox_w=10, bbox_h=10,
            peak_intensity=180, mean_intensity=160, area=100,
            raw_centroid_x=50.0, raw_centroid_y=50.0,
            candidate_id=0, detection_score=0.75,
        )

        # Disappearance for 1..5 frames (frames 2 to 6)
        for fn in range(2, 7):
            expected_missed = fn - 1
            ci.identify([noise], current_state=TrackingState.TRACKING, frame_number=fn)
            assert track_id in ci._tracks, f"Track {track_id} unexpectedly purged at missed frame {expected_missed}"
            trk = ci._tracks[track_id]
            assert trk.missed_frames == expected_missed, f"Expected missed_frames={expected_missed}, got {trk.missed_frames}"
            assert trk.pos == init_pos, "Track position mutated during disappearance"

        # Frame 7: 6th consecutive missed frame (> _max_staleness=5)
        ci.identify([noise], current_state=TrackingState.TRACKING, frame_number=7)
        assert track_id not in ci._tracks, f"Track {track_id} was NOT purged after 6 missed frames (memory leak)!"

    def test_candidate_identifier_empty_candidate_aging_investigation(self):
        """
        Empirical observation test:
        Investigate whether CandidateIdentifier ages tracks when scored_candidates is empty ([]).
        Finds that line 220 early return bypasses track aging and pruning when no candidates are detected.
        """
        ci = CandidateIdentifier()
        beacon = CandidateRegion(
            bbox_x=195, bbox_y=195, bbox_w=10, bbox_h=10,
            peak_intensity=220, mean_intensity=200, area=100,
            raw_centroid_x=200.0, raw_centroid_y=200.0,
            candidate_id=0, detection_score=0.90,
        )
        ci.identify([beacon], current_state=TrackingState.SEARCHING, frame_number=1)
        assert 0 in ci._tracks

        # Feed 8 consecutive empty frames
        for fn in range(2, 10):
            ci.identify([], current_state=TrackingState.TRACKING, frame_number=fn)

        # Document whether track aged or purged
        track_still_present = (0 in ci._tracks)
        missed_frames_count = ci._tracks[0].missed_frames if track_still_present else None
        
        # This confirms the early-return behavior:
        # In current implementation, empty candidates list early-returns before lines 299-306.
        assert track_still_present is True
        assert missed_frames_count == 0  # Does not increment when candidates list is []

    def test_temporal_tracker_velocity_retention_and_coasting(self):
        """
        Verifies that ConstantVelocityKalmanTracker retains position and velocity
        during 1..5 frames of disappearance, and coasts predictably.
        """
        tracker = ConstantVelocityKalmanTracker()

        # Initialize with moving beacon (vx = 30.0 px/s, vy = 15.0 px/s)
        dt = 0.0333
        c1 = CentroidResult(x=100.0, y=100.0, valid=True, frame_number=1, timestamp=0.0333)
        tracker.update(c1, dt=dt, frame_number=1, timestamp=0.0333)

        c2 = CentroidResult(x=101.0, y=100.5, valid=True, frame_number=2, timestamp=0.0667)
        r2 = tracker.update(c2, dt=dt, frame_number=2, timestamp=0.0667)
        assert r2.is_coasting is False
        init_vx = r2.velocity_x
        init_vy = r2.velocity_y

        # Disappearance for 5 frames (frames 3..7)
        prev_x = r2.estimated_x
        prev_y = r2.estimated_y
        for fn in range(3, 8):
            t = fn * dt
            r = tracker.update(None, dt=dt, frame_number=fn, timestamp=t)
            assert r.is_coasting is True
            # Velocity must be retained
            assert math.isclose(r.velocity_x, init_vx, abs_tol=1e-4)
            assert math.isclose(r.velocity_y, init_vy, abs_tol=1e-4)
            # Position advances along velocity vector
            assert r.estimated_x > prev_x
            assert r.estimated_y > prev_y
            prev_x = r.estimated_x
            prev_y = r.estimated_y

        assert tracker.consecutive_coasts == 5


# =============================================================================
# STRESS TEST 3: Dataset Generator Sigma Compatibility (DEF-27/31)
# =============================================================================

class TestStressTest3DatasetGeneratorSigmaCompatibility:
    """
    Stress Test 3: Dataset Generator Sigma Compatibility.
    Test DatasetGenerator / SyntheticDatasetGenerator with custom NoiseConfig
    instances using both gaussian_sigma and gaussian_std. Assert zero AttributeError.
    """

    def test_noise_config_sigma_and_std_properties(self):
        """NoiseConfig supports both gaussian_sigma and gaussian_std seamlessly."""
        # 1. Access and mutate via gaussian_sigma
        nc = NoiseConfig(gaussian_sigma=7.5)
        assert nc.gaussian_sigma == 7.5
        assert nc.gaussian_std == 7.5

        # 2. Mutate via gaussian_std setter
        nc.gaussian_std = 12.3
        assert nc.gaussian_sigma == 12.3
        assert nc.gaussian_std == 12.3

        # 3. Assert zero AttributeError
        try:
            _ = nc.gaussian_sigma
            _ = nc.gaussian_std
            nc.gaussian_sigma = 5.0
            nc.gaussian_std = 6.0
        except AttributeError as e:
            pytest.fail(f"Unexpected AttributeError on NoiseConfig: {e}")

    def test_disturbance_engine_with_custom_noise_configs(self):
        """DisturbanceEngine consumes custom NoiseConfig with both sigma and std."""
        nc1 = NoiseConfig(gaussian_enabled=True, gaussian_sigma=8.0)
        de1 = DisturbanceEngine(noise_cfg=nc1, seed=123)
        img1 = np.ones((64, 64), dtype=np.uint8) * 128
        out1 = de1.apply_gaussian_noise(img1)
        assert out1.shape == (64, 64)

        nc2 = NoiseConfig(gaussian_enabled=True)
        nc2.gaussian_std = 11.5
        de2 = DisturbanceEngine(noise_cfg=nc2, seed=456)
        out2 = de2.apply_gaussian_noise(img1)
        assert out2.shape == (64, 64)

    def test_synthetic_dataset_generator_execution(self):
        """SyntheticDatasetGenerator candidate and temporal dataset generation runs with zero AttributeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = SyntheticDatasetGenerator(output_dir=tmpdir)
            # Candidate dataset generation executes line 108 (cfg.noise.gaussian_sigma = ...)
            cand_manifest = gen.generate_candidate_dataset(num_scenarios=3, frames_per_scenario=3, seed=42)
            assert os.path.exists(cand_manifest)

            # Temporal dataset generation
            temp_manifest = gen.generate_temporal_dataset(num_scenarios=3, frames_per_scenario=25, seed=42)
            assert os.path.exists(temp_manifest)


# =============================================================================
# STRESS TEST 4: Static Ground-Truth Firewall Audit
# =============================================================================

class TestStressTest4StaticGroundTruthFirewallAudit:
    """
    Stress Test 4: Static Ground-Truth Firewall Audit.
    Scan WorldCanvasView.tsx and DeveloperWorkspace.tsx for forbidden ground-truth tokens
    ('target_x', 'ground_truth_x', 'hidden_world_x', 'trajectory_truth', 'unblinded_error').
    Verify zero violations.
    """

    FORBIDDEN_TOKENS = [
        'target_x',
        'target_y',
        'ground_truth_x',
        'ground_truth_y',
        'hidden_world_x',
        'hidden_world_y',
        'trajectory_truth',
        'unblinded_error',
    ]

    def test_world_canvas_view_firewall(self):
        """WorldCanvasView.tsx has strictly zero forbidden ground-truth tokens."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        target_files = [
            repo_root / "frontend" / "src" / "workspaces" / "DeveloperWorkspace" / "WorldCanvasView.tsx",
            repo_root / "frontend" / "src" / "workspaces" / "world_canvas" / "WorldCanvasView.tsx",
        ]

        for tf in target_files:
            assert tf.exists(), f"Target file does not exist: {tf}"
            content = tf.read_text(encoding="utf-8").lower()
            violations = [tok for tok in self.FORBIDDEN_TOKENS if tok in content]
            assert len(violations) == 0, f"Ground-truth firewall violations found in {tf}: {violations}"

    def test_developer_workspace_firewall(self):
        """DeveloperWorkspace.tsx has strictly zero forbidden ground-truth tokens."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        tf = repo_root / "frontend" / "src" / "workspaces" / "DeveloperWorkspace" / "DeveloperWorkspace.tsx"
        assert tf.exists(), f"Target file does not exist: {tf}"
        content = tf.read_text(encoding="utf-8").lower()
        violations = [tok for tok in self.FORBIDDEN_TOKENS if tok in content]
        assert len(violations) == 0, f"Ground-truth firewall violations found in {tf}: {violations}"

    def test_entire_frontend_src_firewall_sweep(self):
        """Exhaustive scan of all .ts and .tsx files in frontend/src/ for forbidden tokens."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        frontend_src = repo_root / "frontend" / "src"
        assert frontend_src.exists()

        all_violations = []
        for file_path in frontend_src.rglob("*.tsx"):
            content = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for tok in self.FORBIDDEN_TOKENS:
                if tok in content:
                    all_violations.append((str(file_path.relative_to(repo_root)), tok))

        for file_path in frontend_src.rglob("*.ts"):
            content = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for tok in self.FORBIDDEN_TOKENS:
                if tok in content:
                    all_violations.append((str(file_path.relative_to(repo_root)), tok))

        assert len(all_violations) == 0, f"Firewall violations detected across frontend/src: {all_violations}"
