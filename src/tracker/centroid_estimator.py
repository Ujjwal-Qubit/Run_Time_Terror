"""
Centroid Estimator — Module 10 per Architecture v1.2 §4 and §8.2.

P0 Baseline Algorithm:
  Intensity-Weighted Centroiding (IWC) with local background subtraction.

Mathematical Formulation:
  1. Define local ROI around detected candidate bounding box with margin M.
  2. Estimate local background intensity B from perimeter border pixels.
  3. Calculate positive signal weights: w_i = max(I_i - B, 0.0).
  4. Compute sub-pixel centroid:
       x_hat = sum(w_i * x_i) / sum(w_i)
       y_hat = sum(w_i * y_i) / sum(w_i)

FIREWALL ENFORCEMENT:
Has zero access to GroundTruth, GroundTruthProvider, or simulator internals.
Consumes ONLY the observed image and candidate region.
Coordinates produced are sub-pixel floating point (never rounded to integer).
"""

from __future__ import annotations

import time
from typing import Optional, Tuple, Union

import numpy as np

from src.interfaces.strategy_interfaces import ICentroidEstimator
from src.frame.data_contracts import (
    FramePacket,
    CandidateRegion,
    ScoredCandidate,
    CentroidResult,
)
from src.config.config_manager import CentroidConfig
from src.config import defaults


class IntensityWeightedCentroidEstimator(ICentroidEstimator):
    """
    Intensity-Weighted Centroid Estimator (Module 10 - P0 Baseline).

    Refines a candidate bounding box into a high-precision sub-pixel
    centroid estimate using positive signal weighting above local background.
    """

    def __init__(self, config: Optional[CentroidConfig] = None) -> None:
        cfg = config or CentroidConfig()
        self._cfg = cfg
        self._bg_margin = max(1, cfg.bg_margin)
        self._min_signal_weight = getattr(cfg, "min_signal_weight", defaults.CENTROID_MIN_SIGNAL_WEIGHT)
        self._bg_method = getattr(cfg, "bg_method", defaults.CENTROID_BG_METHOD)

    @property
    def config(self) -> CentroidConfig:
        return self._cfg

    def get_name(self) -> str:
        return "IntensityWeightedCentroidEstimator"

    def estimate_local_background(self, roi: np.ndarray) -> float:
        """
        Estimate the local background intensity from the perimeter pixels of the ROI.

        Using the outer border ring avoids allowing the bright central beacon
        from corrupting the background estimate.
        """
        h, w = roi.shape[:2]
        if h <= 2 or w <= 2:
            return float(np.min(roi))

        # Extract perimeter border pixels (top, bottom, left, right excluding corners)
        top = roi[0, :]
        bottom = roi[-1, :]
        left = roi[1:-1, 0]
        right = roi[1:-1, -1]

        border = np.concatenate([top, bottom, left, right])
        # Median is robust against single-pixel noise spikes on the boundary
        return float(np.median(border))

    def estimate(
        self,
        frame: Union[FramePacket, np.ndarray],
        candidate: Union[CandidateRegion, ScoredCandidate],
    ) -> CentroidResult:
        """
        Refine candidate detection to sub-pixel centroid coordinates.

        Args:
            frame: FramePacket or 2D numpy array containing observed frame.
            candidate: CandidateRegion or ScoredCandidate.

        Returns:
            CentroidResult containing sub-pixel floating-point coordinates.
        """
        t_start = time.perf_counter()

        # Unpack image and metadata
        if isinstance(frame, FramePacket):
            raw_image = frame.image
            frame_num = frame.frame_number
            timestamp = frame.timestamp
        elif isinstance(frame, np.ndarray):
            raw_image = frame
            frame_num = 0
            timestamp = 0.0
        else:
            raise TypeError(f"Expected FramePacket or np.ndarray, got {type(frame)}")

        # Unpack candidate region
        if isinstance(candidate, ScoredCandidate):
            cand = candidate.candidate
        elif isinstance(candidate, CandidateRegion):
            cand = candidate
        else:
            raise TypeError(f"Expected CandidateRegion or ScoredCandidate, got {type(candidate)}")

        img_h, img_w = raw_image.shape[:2]
        bx, by, bw, bh = cand.bbox_x, cand.bbox_y, cand.bbox_w, cand.bbox_h
        cand_id = getattr(cand, "candidate_id", 0)

        # Fallback default coordinates (geometric center of bounding box)
        geom_cx = float(bx + bw / 2.0)
        geom_cy = float(by + bh / 2.0)

        # -------------------------------------------------------------------
        # 1. Local ROI Extraction with Border Margin
        # -------------------------------------------------------------------
        margin = self._bg_margin
        x0 = max(0, bx - margin)
        y0 = max(0, by - margin)
        x1 = min(img_w, bx + bw + margin)
        y1 = min(img_h, by + bh + margin)

        if x1 <= x0 or y1 <= y0:
            # Degenerate ROI
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return CentroidResult(
                x=geom_cx,
                y=geom_cy,
                quality=0.0,
                valid=False,
                frame_number=frame_num,
                timestamp=timestamp,
                candidate_id=cand_id,
                total_signal=0.0,
                estimated_bg=0.0,
                roi_bbox=None,
                processing_time_ms=elapsed_ms,
            )

        # Extract ROI as float64 (non-mutating view copy)
        roi_patch = raw_image[y0:y1, x0:x1].astype(np.float64)

        # -------------------------------------------------------------------
        # 2. Local Background Estimation
        # -------------------------------------------------------------------
        bg_est = self.estimate_local_background(roi_patch)

        # -------------------------------------------------------------------
        # 3. Positive Signal Weight Calculation
        # -------------------------------------------------------------------
        weights = np.maximum(0.0, roi_patch - bg_est)
        total_weight = float(np.sum(weights))

        # -------------------------------------------------------------------
        # 4. Numerical Stability & Zero-Signal Check
        # -------------------------------------------------------------------
        if total_weight < self._min_signal_weight or np.isnan(total_weight):
            # No signal above background (e.g. uniform ROI or complete extinction)
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return CentroidResult(
                x=geom_cx,
                y=geom_cy,
                quality=0.0,
                valid=False,
                frame_number=frame_num,
                timestamp=timestamp,
                candidate_id=cand_id,
                total_signal=total_weight,
                estimated_bg=bg_est,
                roi_bbox=(x0, y0, x1 - x0, y1 - y0),
                processing_time_ms=elapsed_ms,
            )

        # -------------------------------------------------------------------
        # 5. Intensity-Weighted Sub-Pixel Centroiding
        # -------------------------------------------------------------------
        y_grid, x_grid = np.mgrid[y0:y1, x0:x1]
        hat_x = float(np.sum(x_grid * weights) / total_weight)
        hat_y = float(np.sum(y_grid * weights) / total_weight)

        # Quality metric: peak signal contrast ratio above background
        peak_intensity = float(np.max(roi_patch))
        contrast_range = max(1.0, 255.0 - bg_est)
        quality = float(np.clip((peak_intensity - bg_est) / contrast_range, 0.0, 1.0))

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return CentroidResult(
            x=hat_x,
            y=hat_y,
            quality=quality,
            valid=True,
            frame_number=frame_num,
            timestamp=timestamp,
            candidate_id=cand_id,
            total_signal=total_weight,
            estimated_bg=bg_est,
            roi_bbox=(x0, y0, x1 - x0, y1 - y0),
            processing_time_ms=elapsed_ms,
        )


# Alias for Module 10 production mapping
CentroidEstimator = IntensityWeightedCentroidEstimator
