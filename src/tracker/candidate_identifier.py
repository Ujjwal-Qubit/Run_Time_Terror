"""
Candidate Identification — Module 11 per Architecture v1.2 §8.2 Stage 4.

P0 Rule-Based Beacon Identification Strategy:
  Selects the most likely designated beacon from detected candidate regions
  using ONLY observed-frame features and temporal consistency.

Observable features used:
  1. Peak and mean intensity.
  2. Size similarity relative to expected beacon geometry.
  3. Local contrast ratio.
  4. Temporal spatial proximity to predicted position (when tracking).

FIREWALL ENFORCEMENT:
  Has ZERO access to GroundTruth, GroundTruthProvider, or simulator internals.
  Consumes exclusively observed candidates and tracking predictions.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from src.interfaces.strategy_interfaces import IBeaconIdentifier
from src.frame.data_contracts import (
    CandidateRegion,
    ScoredCandidate,
    IdentificationResult,
    TrackingState,
)
from src.config.config_manager import IdentifierConfig
from src.config import defaults


@dataclass
class _SpatialTrack:
    """Persistent spatial track representation for nearest-neighbor tracking (DEF-14)."""
    track_id: Any
    pos: Tuple[float, float]
    age: int = 1
    hits: int = 1
    missed_frames: int = 0
    score: float = 0.0


class CandidateIdentifier(IBeaconIdentifier):
    """
    Candidate Identifier (Module 11 - P0 Baseline).

    Ranks detected candidates using appearance, contrast, and temporal proximity.
    Produces an explicit IdentificationResult without relying on ground truth.
    """

    def __init__(self, config: Optional[IdentifierConfig] = None) -> None:
        cfg = config or IdentifierConfig()
        self._cfg = cfg
        self._w_int = cfg.intensity_weight
        self._w_size = cfg.size_weight
        self._w_contrast = cfg.contrast_weight
        self._w_prox = cfg.proximity_weight
        self._expected_size = float(cfg.expected_beacon_size)
        self._min_confidence = getattr(cfg, "min_confidence", defaults.IDENTIFIER_MIN_CONFIDENCE)
        self._gate_distance = defaults.GATE_MAX_DISTANCE

        # Hysteresis anti-switching state
        # Prevents momentary noise-induced switches to secondary beacons.
        self._switch_margin = getattr(
            cfg, "switch_score_margin", defaults.IDENTIFIER_SWITCH_SCORE_MARGIN
        )
        self._switch_confirm_frames = int(getattr(
            cfg, "switch_confirmation_frames", defaults.IDENTIFIER_SWITCH_CONFIRMATION_FRAMES
        ))
        # Persistent spatial track store (DEF-14)
        self._tracks: Dict[Any, _SpatialTrack] = {}
        self._next_track_id: int = 0
        self._max_staleness: int = 5
        # ID of the current tracked candidate (by persistent candidate_id or None)
        self._current_candidate_id: Optional[Any] = None
        # Spatial position of current track (persistent across raster candidate_id swaps) (DEF-14)
        self._current_track_pos: Optional[Tuple[float, float]] = None
        # Current track's score in the most recent valid TRACKING frame
        self._current_track_score: float = 0.0
        # Challenger tracking (hysteresis buffer)
        self._challenger_id: Optional[Any] = None
        self._challenger_frames: int = 0

    @property
    def config(self) -> IdentifierConfig:
        return self._cfg

    def get_name(self) -> str:
        return "CandidateIdentifier"

    @staticmethod
    def _get_candidate_pos(cand: Any) -> Tuple[float, float]:
        """Extract subpixel centroid coordinates with bounding box fallback (DEF-14)."""
        bx = float(getattr(cand, "bbox_x", 0.0))
        by = float(getattr(cand, "bbox_y", 0.0))
        bw = float(getattr(cand, "bbox_w", 0.0))
        bh = float(getattr(cand, "bbox_h", 0.0))
        default_cx = bx + bw / 2.0
        default_cy = by + bh / 2.0

        cx = getattr(cand, "raw_centroid_x", None)
        if cx is None:
            cx = getattr(cand, "centroid_x", None)
        cy = getattr(cand, "raw_centroid_y", None)
        if cy is None:
            cy = getattr(cand, "centroid_y", None)

        if cx is not None and cy is not None:
            # If centroid is within or reasonably close to bbox, use it;
            # otherwise (e.g. default 0.0, 0.0 when bbox is at 200, 200), fallback to bbox center
            if (bx - 1.0 <= cx <= bx + bw + 1.0) and (by - 1.0 <= cy <= by + bh + 1.0):
                return (float(cx), float(cy))

        return (default_cx, default_cy)

    def reset(self) -> None:
        """Reset hysteresis state and persistent tracks. Call between benchmark runs for clean slate."""
        self._tracks.clear()
        self._next_track_id = 0
        self._current_candidate_id = None
        self._current_track_pos = None
        self._current_track_score = 0.0
        self._challenger_id = None
        self._challenger_frames = 0

    def score_candidate(
        self,
        candidate: CandidateRegion,
        predicted_position: Optional[Tuple[float, float]],
        current_state: TrackingState,
    ) -> float:
        """
        Compute an explicit confidence score in [0, 1] for a candidate region.
        """
        # 1. Intensity score: peak intensity normalized to [0, 1]
        s_int = float(min(1.0, max(0.0, candidate.peak_intensity / 255.0)))

        # 2. Size score: Gaussian penalty around expected beacon size
        cand_size = (float(candidate.bbox_w) + float(candidate.bbox_h)) / 2.0
        delta_size = abs(cand_size - self._expected_size)
        sigma_size = max(3.0, self._expected_size / 2.0)
        s_size = float(math.exp(-0.5 * (delta_size / sigma_size) ** 2))

        # 3. Contrast score: normalized local contrast above background
        if candidate.local_contrast > 0.0:
            s_contrast = float(min(1.0, max(0.0, (candidate.local_contrast - 1.0) / 3.0)))
        else:
            s_contrast = s_int

        # 4. Proximity score: temporal consistency against predicted position
        is_tracking_mode = (
            current_state in (TrackingState.TRACKING, TrackingState.ACQUIRING, TrackingState.REACQUIRING)
            and predicted_position is not None
        )

        if is_tracking_mode and predicted_position is not None:
            pred_x, pred_y = predicted_position
            # Candidate geometric center (using subpixel accuracy where available)
            cand_cx, cand_cy = self._get_candidate_pos(candidate)
            dist = math.hypot(cand_cx - pred_x, cand_cy - pred_y)

            sigma_dist = max(10.0, self._gate_distance / 2.0)
            if dist <= self._gate_distance:
                s_prox = float(math.exp(-0.5 * (dist / sigma_dist) ** 2))
            else:
                # Heavy penalty if outside gate
                s_prox = 0.001

            # Weighted combination with temporal proximity
            w_total = self._w_int + self._w_size + self._w_contrast + self._w_prox
            score = (
                self._w_int * s_int
                + self._w_size * s_size
                + self._w_contrast * s_contrast
                + self._w_prox * s_prox
            ) / max(1e-6, w_total)
        else:
            # SEARCHING mode: observation-only ranking without spatial bias
            w_obs = self._w_int + self._w_size + self._w_contrast
            score = (
                self._w_int * s_int
                + self._w_size * s_size
                + self._w_contrast * s_contrast
            ) / max(1e-6, w_obs)

        # Incorporate detector detection_score if provided
        if candidate.detection_score > 0.0:
            score = 0.7 * score + 0.3 * candidate.detection_score

        return float(min(1.0, max(0.0, score)))

    def identify(
        self,
        scored_candidates: Union[List[ScoredCandidate], List[CandidateRegion]],
        predicted_position: Optional[Tuple[float, float]] = None,
        current_state: TrackingState = TrackingState.SEARCHING,
        frame_number: int = 0,
        timestamp: float = 0.0,
    ) -> IdentificationResult:
        """
        Select the most likely beacon candidate from candidates list.

        Args:
            scored_candidates: List of CandidateRegion or ScoredCandidate.
            predicted_position: (x, y) predicted image coordinates, if available.
            current_state: Current tracking lifecycle state.
            frame_number: Current frame sequence number.
            timestamp: Frame timestamp in seconds.

        Returns:
            IdentificationResult containing the selected candidate and confidence.
        """
        t0 = time.perf_counter()

        if not scored_candidates:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return IdentificationResult(
                selected_candidate=None,
                selected_candidate_id=None,
                valid=False,
                confidence=0.0,
                all_scored_candidates=[],
                frame_number=frame_number,
                timestamp=timestamp,
                processing_time_ms=elapsed_ms,
            )

        # Unpack candidates
        raw_candidates: List[CandidateRegion] = []
        for item in scored_candidates:
            if isinstance(item, ScoredCandidate):
                raw_candidates.append(item.candidate)
            elif isinstance(item, CandidateRegion):
                raw_candidates.append(item)
            else:
                raise TypeError(f"Expected CandidateRegion or ScoredCandidate, got {type(item)}")

        # ------------------------------------------------------------------
        # Spatial Nearest-Neighbor Candidate Association (DEF-14)
        # ------------------------------------------------------------------
        # Re-tag candidates with persistent track IDs based on subpixel Euclidean
        # proximity to existing active tracks, immune to ephemeral raster scan swaps.
        cand_positions = [self._get_candidate_pos(c) for c in raw_candidates]
        active_track_ids = list(self._tracks.keys())

        # Pairwise distance matrix between active tracks and raw candidates
        pair_distances: List[Tuple[float, Any, int]] = []
        for tid in active_track_ids:
            t_pos = self._tracks[tid].pos
            for c_idx, c_pos in enumerate(cand_positions):
                d = math.hypot(t_pos[0] - c_pos[0], t_pos[1] - c_pos[1])
                if d <= self._gate_distance:
                    pair_distances.append((d, tid, c_idx))

        pair_distances.sort(key=lambda x: x[0])
        matched_tracks: set = set()
        matched_cands: set = set()

        for d, tid, c_idx in pair_distances:
            if tid not in matched_tracks and c_idx not in matched_cands:
                matched_tracks.add(tid)
                matched_cands.add(c_idx)
                trk = self._tracks[tid]
                trk.pos = cand_positions[c_idx]
                trk.hits += 1
                trk.age += 1
                trk.missed_frames = 0
                # Re-tag candidate with persistent track ID
                raw_candidates[c_idx].candidate_id = trk.track_id

        # Allocate new persistent tracks for unassociated candidates
        for c_idx, cand in enumerate(raw_candidates):
            if c_idx not in matched_cands:
                cid = getattr(cand, "candidate_id", None)
                if cid is None or cid in self._tracks:
                    while self._next_track_id in self._tracks:
                        self._next_track_id += 1
                    new_id = self._next_track_id
                    self._next_track_id += 1
                else:
                    new_id = cid
                    if isinstance(new_id, int) and new_id >= self._next_track_id:
                        self._next_track_id = new_id + 1
                cand.candidate_id = new_id
                self._tracks[new_id] = _SpatialTrack(
                    track_id=new_id,
                    pos=cand_positions[c_idx],
                    age=1,
                    hits=1,
                    missed_frames=0,
                )

        # Track staleness and pruning for unmatched active tracks
        unmatched_tracks = set(active_track_ids) - matched_tracks
        for tid in unmatched_tracks:
            trk = self._tracks[tid]
            trk.missed_frames += 1
            trk.age += 1
            if trk.missed_frames > self._max_staleness:
                del self._tracks[tid]

        # Score and rank all candidates
        scored_list: List[ScoredCandidate] = []
        for cand in raw_candidates:
            score = self.score_candidate(cand, predicted_position, current_state)
            is_beacon = bool(score >= self._min_confidence)
            scored_list.append(ScoredCandidate(candidate=cand, score=score, is_beacon=is_beacon))

        # Sort descending by score
        scored_list.sort(key=lambda sc: sc.score, reverse=True)

        best_scored = scored_list[0]
        is_tracking = current_state in (
            TrackingState.TRACKING, TrackingState.ACQUIRING,
        )

        # ------------------------------------------------------------------
        # Hysteresis anti-switching logic on persistent track IDs (TRACKING mode only)
        # ------------------------------------------------------------------
        if is_tracking and (self._current_candidate_id is not None or self._current_track_pos is not None) and len(scored_list) > 1:
            current_in_list = next(
                (sc for sc in scored_list
                 if getattr(sc.candidate, "candidate_id", None) == self._current_candidate_id),
                None,
            )

            # Spatial fallback if ID lookup misses but candidate is within gate
            if current_in_list is None and self._current_track_pos is not None:
                cand_dists = [
                    (math.hypot(self._get_candidate_pos(sc.candidate)[0] - self._current_track_pos[0],
                                self._get_candidate_pos(sc.candidate)[1] - self._current_track_pos[1]), sc)
                    for sc in scored_list
                ]
                cand_dists.sort(key=lambda item: item[0])
                if cand_dists and cand_dists[0][0] <= self._gate_distance:
                    current_in_list = cand_dists[0][1]

            top_challenger = scored_list[0]
            top_challenger_id = getattr(top_challenger.candidate, "candidate_id", None)

            if (
                current_in_list is not None
                and top_challenger is not current_in_list
            ):
                # A challenger is trying to take over. Apply hysteresis.
                required_margin = self._switch_margin
                challenger_score = top_challenger.score
                current_score = current_in_list.score
                self._current_track_score = current_score

                if challenger_score > current_score + required_margin:
                    # Challenger qualifies — confirm for N consecutive frames
                    if top_challenger_id == self._challenger_id:
                        self._challenger_frames += 1
                    else:
                        self._challenger_id = top_challenger_id
                        self._challenger_frames = 1

                    if self._challenger_frames >= self._switch_confirm_frames:
                        # Switch confirmed — challenger becomes the new current
                        best_scored = top_challenger
                        self._current_candidate_id = top_challenger_id
                        self._challenger_id = None
                        self._challenger_frames = 0
                    else:
                        # Not yet confirmed — hold current candidate
                        best_scored = current_in_list
                else:
                    # Challenger does not beat margin — reset challenge counter
                    self._challenger_id = None
                    self._challenger_frames = 0
                    best_scored = current_in_list
            else:
                # Top candidate IS the current tracked one — reset challenge counter
                self._challenger_id = None
                self._challenger_frames = 0
                if current_in_list is not None:
                    self._current_track_score = current_in_list.score

        # Update current candidate ID on successful identification
        is_valid = bool(best_scored.score >= self._min_confidence)
        selected_cand = best_scored.candidate if is_valid else None
        selected_id = getattr(selected_cand, "candidate_id", None) if selected_cand else None

        if is_valid:
            self._current_candidate_id = selected_id
            if selected_cand is not None:
                self._current_track_pos = self._get_candidate_pos(selected_cand)
                if selected_id in self._tracks:
                    self._tracks[selected_id].score = best_scored.score
        elif not is_tracking:
            # In SEARCHING/REACQUIRING, clear hysteresis so it does not
            # lock onto a stale candidate from a previous tracking session.
            self._current_candidate_id = None
            self._current_track_pos = None
            self._current_track_score = 0.0
            self._challenger_id = None
            self._challenger_frames = 0

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return IdentificationResult(
            selected_candidate=selected_cand,
            selected_candidate_id=selected_id,
            valid=is_valid,
            confidence=best_scored.score if is_valid else 0.0,
            all_scored_candidates=scored_list,
            frame_number=frame_number,
            timestamp=timestamp,
            processing_time_ms=elapsed_ms,
            # Backward-compatibility duck typing for ScoredCandidate
            candidate=selected_cand,
            score=best_scored.score if is_valid else 0.0,
            is_beacon=is_valid,
        )


# Aliases for Module 11 production mapping
BeaconIdentifier = CandidateIdentifier
