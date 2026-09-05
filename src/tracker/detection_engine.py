"""
Detection Engine — Module 9 per Architecture v1.2 §4 and §8.2.

P0 Baseline Detector:
  Median (3x3) -> Local Background Estimation -> Adaptive Thresholding -> Connected Components

FIREWALL ENFORCEMENT:
Has zero access to simulation truth, truth provider, or simulator internals.
Consumes ONLY the observed FramePacket and operates completely resolution-agnostic.
Does NOT perform sub-pixel centroiding, target identification, tracking, or PTZ control.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np

from src.interfaces.strategy_interfaces import IDetector
from src.frame.data_contracts import (
    FramePacket,
    CandidateRegion,
    DetectionResult,
    ROI,
)
from src.config.config_manager import DetectorConfig
from src.config import defaults


class P0ThresholdDetector(IDetector):
    """
    P0 Baseline Detection Engine (Module 9).

    Algorithm Pipeline:
      1. Preprocessing: 3x3 median filter to eliminate impulse/salt-and-pepper noise.
      2. Local Background Estimation: Moving average / box filter over local neighborhood.
      3. Difference Enhancement & Thresholding: Difference from background, thresholded by
         (threshold_offset + k * sigma).
      4. Connected Components Analysis: 8-connectivity labeling to extract candidate regions.
      5. Conservative Filtering: Area, intensity, aspect ratio, and local contrast gating.
      6. Feature Extraction: Bounding box, raw geometric center, peak/mean intensity,
         local contrast, compactness, and detection score.

    Modular Design:
      Local background estimation is isolated in `estimate_background()` to allow
      direct drop-in replacement by P1 CFAR or P2 learned detectors.
    """

    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        cfg = config or DetectorConfig()
        self._cfg = cfg

        self._bg_kernel_size = cfg.bg_kernel_size
        self._threshold_multiplier = cfg.threshold_multiplier
        self._threshold_offset = cfg.threshold_offset
        self._min_candidate_area = cfg.min_candidate_area
        self._max_candidate_area = cfg.max_candidate_area
        self._min_candidate_intensity = cfg.min_candidate_intensity
        self._median_kernel_size = cfg.median_kernel_size
        self._min_local_contrast = cfg.min_local_contrast
        self._max_aspect_ratio = getattr(cfg, "max_aspect_ratio", 4.0)

    @property
    def config(self) -> DetectorConfig:
        return self._cfg

    def get_name(self) -> str:
        return "P0ThresholdDetector"

    def estimate_background(self, image: np.ndarray) -> np.ndarray:
        """
        Estimate spatially varying local background intensity.

        Isolated for modularity — can be replaced by CFAR cell averaging in P1.
        Uses a 2D box filter with configurable kernel size.
        """
        h, w = image.shape[:2]
        k = self._bg_kernel_size
        # Kernel size must be odd and <= image dimensions
        k = min(k, min(h, w))
        if k % 2 == 0:
            k = max(1, k - 1)
        if k <= 1:
            return image.copy()

        return cv2.boxFilter(image, ddepth=-1, ksize=(k, k), borderType=cv2.BORDER_REPLICATE)

    def detect(
        self,
        packet: Union[FramePacket, np.ndarray],
        roi: Optional[ROI] = None,
    ) -> DetectionResult:
        """
        Detect candidate beacon regions in the input frame packet.

        Args:
            packet: FramePacket containing observed image and frame metadata,
                    or a 2D numpy array uint8 (for direct testing).
            roi: Optional region of interest to restrict detection.

        Returns:
            DetectionResult with candidate list, frame number, timestamp, and metadata.
        """
        t_start = time.perf_counter()

        # Unpack FramePacket or raw array
        if isinstance(packet, FramePacket):
            raw_image = packet.image
            frame_num = packet.frame_number
            timestamp = packet.timestamp
        elif isinstance(packet, np.ndarray):
            raw_image = packet
            frame_num = 0
            timestamp = 0.0
        else:
            raise TypeError(f"Expected FramePacket or np.ndarray, got {type(packet)}")

        # Ensure working with 2D monochrome uint8
        if raw_image.ndim == 3:
            gray = cv2.cvtColor(raw_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = raw_image

        # Handle ROI sub-window if provided
        roi_offset_x = 0
        roi_offset_y = 0
        if roi is not None:
            img_h, img_w = gray.shape[:2]
            rx0 = max(0, min(roi.x, img_w - 1))
            ry0 = max(0, min(roi.y, img_h - 1))
            rx1 = max(rx0 + 1, min(rx0 + roi.width, img_w))
            ry1 = max(ry0 + 1, min(ry0 + roi.height, img_h))
            work_image = gray[ry0:ry1, rx0:rx1]
            roi_offset_x = rx0
            roi_offset_y = ry0
        else:
            work_image = gray

        # -------------------------------------------------------------------
        # 1. Preprocessing: Median Filter (non-mutating, preserves uint8)
        # -------------------------------------------------------------------
        k_med = self._median_kernel_size
        if k_med > 1:
            if k_med % 2 == 0:
                k_med += 1
            filtered = cv2.medianBlur(work_image, k_med)
        else:
            filtered = work_image.copy()

        # -------------------------------------------------------------------
        # 2. Local Background Estimation
        # -------------------------------------------------------------------
        bg = self.estimate_background(filtered)

        # -------------------------------------------------------------------
        # 3. Difference Enhancement & Thresholding
        # -------------------------------------------------------------------
        # Compute positive difference above background
        diff = np.maximum(0, filtered.astype(np.int16) - bg.astype(np.int16)).astype(np.float32)

        # Estimate local noise standard deviation via robust standard deviation of diff
        sigma = float(np.std(diff))
        # Adaptive threshold: baseline offset + k * sigma
        threshold = self._threshold_offset + self._threshold_multiplier * sigma

        # Generate binary detection mask
        binary_mask = np.zeros(filtered.shape, dtype=np.uint8)
        valid_pixel_mask = (diff >= threshold) & (filtered >= self._min_candidate_intensity)
        binary_mask[valid_pixel_mask] = 255

        # -------------------------------------------------------------------
        # 4. Connected Components Analysis
        # -------------------------------------------------------------------
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            binary_mask, connectivity=8, ltype=cv2.CV_32S
        )

        candidates: List[CandidateRegion] = []
        candidate_id = 0

        # Label 0 is background — iterate over foreground components
        for label_idx in range(1, num_labels):
            area = int(stats[label_idx, cv2.CC_STAT_AREA])

            # Area gating: must accommodate 5x5 to 20x20 targets
            if area < self._min_candidate_area or area > self._max_candidate_area:
                continue

            bw = int(stats[label_idx, cv2.CC_STAT_WIDTH])
            bh = int(stats[label_idx, cv2.CC_STAT_HEIGHT])
            bx = int(stats[label_idx, cv2.CC_STAT_LEFT])
            by = int(stats[label_idx, cv2.CC_STAT_TOP])

            # Aspect ratio check (reject long thin noise artifacts)
            aspect_ratio = max(bw, bh) / max(1.0, float(min(bw, bh)))
            if aspect_ratio > self._max_aspect_ratio:
                continue

            # Extract component pixels from the filtered image
            comp_mask = labels[by : by + bh, bx : bx + bw] == label_idx
            comp_pixels = filtered[by : by + bh, bx : bx + bw][comp_mask]

            if comp_pixels.size == 0:
                continue

            peak_val = float(np.max(comp_pixels))
            mean_val = float(np.mean(comp_pixels))

            # Intensity gating
            if peak_val < self._min_candidate_intensity:
                continue

            # Local background around the component
            bg_patch = bg[by : by + bh, bx : bx + bw]
            local_bg_mean = float(np.mean(bg_patch)) if bg_patch.size > 0 else 1.0
            local_contrast = mean_val / max(1.0, local_bg_mean)

            # Contrast gating
            if local_contrast < self._min_local_contrast:
                continue

            # Geometric compactness: area / bounding box area
            bbox_area = float(bw * bh)
            compactness = area / bbox_area if bbox_area > 0 else 0.0

            # Raw geometric center (metadata ONLY — NOT subpixel centroid)
            raw_cx = float(centroids[label_idx][0]) + roi_offset_x
            raw_cy = float(centroids[label_idx][1]) + roi_offset_y

            # Normalized detection score in [0.0, 1.0]
            # Weights: brightness (0.4), contrast (0.4), compactness (0.2)
            norm_peak = min(1.0, peak_val / 255.0)
            norm_contrast = min(1.0, max(0.0, (local_contrast - 1.0) / 2.0))
            score = float(np.clip(0.4 * norm_peak + 0.4 * norm_contrast + 0.2 * compactness, 0.0, 1.0))

            cand = CandidateRegion(
                bbox_x=bx + roi_offset_x,
                bbox_y=by + roi_offset_y,
                bbox_w=bw,
                bbox_h=bh,
                peak_intensity=peak_val,
                mean_intensity=mean_val,
                area=area,
                local_contrast=local_contrast,
                compactness=compactness,
                candidate_id=candidate_id,
                raw_centroid_x=raw_cx,
                raw_centroid_y=raw_cy,
                detection_score=score,
            )
            candidates.append(cand)
            candidate_id += 1

        t_end = time.perf_counter()
        elapsed_ms = (t_end - t_start) * 1000.0

        return DetectionResult(
            frame_number=frame_num,
            timestamp=timestamp,
            candidates=candidates,
            processing_time_ms=elapsed_ms,
            roi=roi,
        )


# Alias for Module 9 production mapping
DetectionEngine = P0ThresholdDetector
