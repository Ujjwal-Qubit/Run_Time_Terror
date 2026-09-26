"""
Calibration — Probability calibration and threshold calibration utilities per Spec §6 & §9.
"""

from __future__ import annotations

from typing import List, Tuple
import numpy as np


class ProbabilityCalibrator:
    """
    Applies temperature scaling / Platt scaling to align raw scores with true probabilities.
    """

    def __init__(self, temperature: float = 1.0) -> None:
        self.temperature = max(1e-3, temperature)

    def calibrate(self, raw_score: float) -> float:
        """Apply temperature scaling."""
        probability = float(np.clip(raw_score, 1e-7, 1.0 - 1e-7))
        logit = np.log(probability / (1.0 - probability))
        scaled_logit = logit / self.temperature
        calibrated_prob = 1.0 / (1.0 + np.exp(-scaled_logit))
        return float(np.clip(calibrated_prob, 0.0, 1.0))

    @staticmethod
    def find_optimal_threshold(
        y_true: np.ndarray,
        y_scores: np.ndarray,
        target_metric: str = "f1",
    ) -> float:
        """Find optimal decision threshold on validation set."""
        thresholds = np.linspace(0.1, 0.9, 81)
        best_thresh = 0.5
        best_val = -1.0

        for t in thresholds:
            y_pred = (y_scores >= t).astype(int)
            tp = np.sum((y_pred == 1) & (y_true == 1))
            fp = np.sum((y_pred == 1) & (y_true == 0))
            fn = np.sum((y_pred == 0) & (y_true == 1))

            prec = tp / max(1, tp + fp)
            rec = tp / max(1, tp + fn)
            f1 = 2 * prec * rec / max(1e-6, prec + rec)

            if target_metric == "f1" and f1 > best_val:
                best_val = f1
                best_thresh = float(t)
            elif target_metric == "precision" and prec > best_val:
                best_val = prec
                best_thresh = float(t)

        return best_thresh
