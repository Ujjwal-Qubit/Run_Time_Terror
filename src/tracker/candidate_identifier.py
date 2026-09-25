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

import math
import time
from typing import List, Optional, Tuple, Union

from src.interfaces.strategy_interfaces import IBeaconIdentifier
from src.frame.data_contracts import (
    CandidateRegion,
    ScoredCandidate,
    IdentificationResult,
    TrackingState,
)
from src.config.config_manager import IdentifierConfig
from src.config import defaults


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
        # ID of the current tracked candidate (by candidate_id or None)
        self._current_candidate_id: Optional[str] = None
        # Current track's score in the most recent valid TRACKING frame
        self._current_track_score: float = 0.0
        # Challenger tracking (hysteresis buffer)
        self._challenger_id: Optional[str] = None
        self._challenger_frames: int = 0

    @property
    def config(self) -> IdentifierConfig:
        return self._cfg

    def get_name(self) -> str:
        return "CandidateIdentifier"

    def reset(self) -> None:
        """Reset hysteresis state. Call between benchmark runs for clean slate."""
        self._current_candidate_id = None
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
            # Candidate geometric center
            cand_cx = float(candidate.bbox_x + candidate.bbox_w / 2.0)
            cand_cy = float(candidate.bbox_y + candidate.bbox_h / 2.0)
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
        # Hysteresis anti-switching logic (TRACKING mode only)
        # ------------------------------------------------------------------
        if is_tracking and self._current_candidate_id is not None and len(scored_list) > 1:
            # Find the current tracked candidate in scored list
            current_in_list = next(
                (sc for sc in scored_list
                 if getattr(sc.candidate, "candidate_id", None) == self._current_candidate_id),
                None,
            )
            top_challenger = scored_list[0]
            top_challenger_id = getattr(top_challenger.candidate, "candidate_id", None)

            if (
                current_in_list is not None
                and top_challenger_id != self._current_candidate_id
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
                self._current_track_score = top_challenger.score

        # Update current candidate ID on successful identification
        is_valid = bool(best_scored.score >= self._min_confidence)
        selected_cand = best_scored.candidate if is_valid else None
        selected_id = getattr(selected_cand, "candidate_id", None) if selected_cand else None

        if is_valid:
            self._current_candidate_id = selected_id
        elif not is_tracking:
            # In SEARCHING/REACQUIRING, clear hysteresis so it does not
            # lock onto a stale candidate from a previous tracking session.
            self._current_candidate_id = None
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
