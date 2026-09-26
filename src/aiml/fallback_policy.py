"""
Fallback Policy — Evaluates fallback conditions for AIML inference per Spec §11.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import numpy as np

from src.aiml.contracts import CandidateClassification, PredictionResult


class FallbackPolicy:
    """
    Evaluates fallback triggers (NaN/Inf, missing file, low confidence, excessive latency).
    """

    @staticmethod
    def is_invalid_output(val: float) -> bool:
        return math.isnan(val) or math.isinf(val)

    @staticmethod
    def check_classification(
        classification: CandidateClassification,
        min_confidence: float = 0.3,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if classification requires fallback.
        """
        if classification.used_fallback:
            return True, classification.fallback_reason

        if FallbackPolicy.is_invalid_output(classification.beacon_probability):
            return True, "Probability output NaN/Inf"

        if classification.beacon_probability < min_confidence:
            return True, "Confidence below minimum threshold"

        return False, None

    @staticmethod
    def check_prediction(
        prediction: PredictionResult,
        max_frame_width: int = 4000,
        max_frame_height: int = 4000,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if temporal prediction requires fallback.
        """
        if prediction.used_fallback:
            return True, prediction.fallback_reason

        if (
            FallbackPolicy.is_invalid_output(prediction.predicted_x)
            or FallbackPolicy.is_invalid_output(prediction.predicted_y)
        ):
            return True, "Predicted coordinates NaN/Inf"

        # Out-of-bounds check (allow margin)
        margin = 500
        if not (-margin <= prediction.predicted_x <= max_frame_width + margin) or not (
            -margin <= prediction.predicted_y <= max_frame_height + margin
        ):
            return True, "Prediction far out of frame bounds"

        return False, None
