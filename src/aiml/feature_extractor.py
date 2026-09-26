"""
Candidate Feature Extractor — Module for converting CandidateRegion objects into
11-dimensional normalized feature vectors per AIML Integration Specification §5.1.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple
import numpy as np

from src.aiml.contracts import CandidateFeatureVector
from src.frame.data_contracts import CandidateRegion, FramePacket, TrackingState


FEATURE_SCHEMA_VERSION = "candidate-v1"
FEATURE_NAMES: Tuple[str, ...] = (
    "peak_intensity_norm",
    "mean_intensity_norm",
    "local_contrast",
    "area_norm",
    "compactness",
    "aspect_ratio",
    "size_error_norm",
    "distance_to_prediction_norm",
    "innovation_norm",
    "frame_border_distance_norm",
    "candidate_detection_score",
)


class CandidateFeatureExtractor:
    """
    Extracts numerical feature vectors from CandidateRegion objects.

    Guarantees:
      - Never produces NaN or Infinity.
      - Resolution-independent normalization.
      - Preserves exact feature order across training and inference.
    """

    def __init__(self, expected_target_size: int = 10) -> None:
        self.expected_target_size = expected_target_size
        self.expected_area = float(expected_target_size * expected_target_size)

    def extract(
        self,
        packet: FramePacket,
        candidate: CandidateRegion,
        predicted_position: Optional[Tuple[float, float]] = None,
        prediction_uncertainty: Optional[Tuple[float, float]] = None,
        previous_position: Optional[Tuple[float, float]] = None,
        current_state: TrackingState = TrackingState.SEARCHING,
        candidate_id: Optional[int] = None,
    ) -> CandidateFeatureVector:
        """
        Extract the 11-dimensional feature vector from candidate and metadata.
        """
        fw = float(packet.width)
        fh = float(packet.height)
        frame_diagonal = math.hypot(fw, fh)

        # 1. Peak intensity norm [0, 1]
        peak_intensity_norm = float(np.clip(candidate.peak_intensity / 255.0, 0.0, 1.0))

        # 2. Mean intensity norm [0, 1]
        mean_intensity_norm = float(np.clip(candidate.mean_intensity / 255.0, 0.0, 1.0))

        # 3. Local contrast (ratio >= 1.0)
        local_contrast = float(max(1.0, candidate.local_contrast))

        # 4. Area norm (normalized by frame area)
        frame_area = max(1.0, fw * fh)
        area_norm = float(candidate.area / frame_area)

        # 5. Compactness [0, 1]
        compactness = float(np.clip(candidate.compactness, 0.0, 1.0))

        # 6. Aspect ratio (>= 1.0)
        bw = max(1.0, float(candidate.bbox_w))
        bh = max(1.0, float(candidate.bbox_h))
        aspect_ratio = float(max(bw, bh) / min(bw, bh))

        # 7. Size error norm (|area - expected_area| / expected_area)
        size_error_norm = float(abs(candidate.area - self.expected_area) / max(1.0, self.expected_area))

        cand_x = getattr(candidate, "centroid_x", float(candidate.bbox_x + candidate.bbox_w / 2.0))
        cand_y = getattr(candidate, "centroid_y", float(candidate.bbox_y + candidate.bbox_h / 2.0))

        # 8. Distance to prediction norm (Euclidean distance / frame diagonal)
        if predicted_position is not None:
            dx = cand_x - predicted_position[0]
            dy = cand_y - predicted_position[1]
            dist_pred = math.hypot(dx, dy)
            distance_to_prediction_norm = float(dist_pred / max(1.0, frame_diagonal))
        else:
            distance_to_prediction_norm = 1.0

        # 9. Innovation norm (distance to previous position / frame diagonal)
        if previous_position is not None:
            dx_prev = cand_x - previous_position[0]
            dy_prev = cand_y - previous_position[1]
            dist_prev = math.hypot(dx_prev, dy_prev)
            innovation_norm = float(dist_prev / max(1.0, frame_diagonal))
        else:
            innovation_norm = 1.0

        # 10. Frame border distance norm (min dist to border / min(fw, fh))
        dist_left = cand_x
        dist_right = fw - cand_x
        dist_top = cand_y
        dist_bottom = fh - cand_y

        min_border_dist = max(0.0, min(dist_left, dist_right, dist_top, dist_bottom))
        frame_border_distance_norm = float(min_border_dist / max(1.0, min(fw, fh)))

        # 11. Candidate detection score
        raw_score = getattr(candidate, "detection_score", 0.8)
        candidate_detection_score = float(np.clip(raw_score, 0.0, 1.0))

        values = (
            peak_intensity_norm,
            mean_intensity_norm,
            local_contrast,
            area_norm,
            compactness,
            aspect_ratio,
            size_error_norm,
            distance_to_prediction_norm,
            innovation_norm,
            frame_border_distance_norm,
            candidate_detection_score,
        )

        # Sanity check for NaN/Inf
        sanitized_values = tuple(
            0.0 if (math.isnan(v) or math.isinf(v)) else float(v)
            for v in values
        )

        return CandidateFeatureVector(
            frame_number=packet.frame_number,
            candidate_id=(candidate.candidate_id if candidate_id is None else candidate_id),
            values=sanitized_values,
            feature_names=FEATURE_NAMES,
            bbox_x=candidate.bbox_x,
            bbox_y=candidate.bbox_y,
            bbox_w=candidate.bbox_w,
            bbox_h=candidate.bbox_h,
        )

    def extract_batch(
        self,
        packet: FramePacket,
        candidates: List[CandidateRegion],
        predicted_position: Optional[Tuple[float, float]] = None,
        prediction_uncertainty: Optional[Tuple[float, float]] = None,
        previous_position: Optional[Tuple[float, float]] = None,
        current_state: TrackingState = TrackingState.SEARCHING,
    ) -> List[CandidateFeatureVector]:
        """Extract feature vectors for a batch of candidates."""
        return [
            self.extract(
                packet=packet,
                candidate=cand,
                predicted_position=predicted_position,
                prediction_uncertainty=prediction_uncertainty,
                previous_position=previous_position,
                current_state=current_state,
                candidate_id=cand.candidate_id,
            )
            for idx, cand in enumerate(candidates)
        ]
