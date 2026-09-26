"""
Candidate Classifier — Module for classifying detected candidates as beacon or noise.

Per AIML Integration Specification §5.2 & §6.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import os
from pathlib import Path
import time
from typing import List, Optional
import numpy as np

from src.aiml.contracts import CandidateClassification, CandidateFeatureVector
from src.aiml.model_loader import ModelLoader, ModelPackage
from src.aiml.calibration import ProbabilityCalibrator


class ICandidateClassifier(ABC):
    """
    Abstract interface for candidate classifiers.
    """

    @abstractmethod
    def classify(
        self,
        features: List[CandidateFeatureVector],
    ) -> List[CandidateClassification]:
        """
        Classify a list of candidate feature vectors.
        Preserves candidate input ordering.
        """
        ...


class RuleBasedClassifierFallback(ICandidateClassifier):
    """
    Rule-based baseline fallback classifier.
    """

    def classify(
        self,
        features: List[CandidateFeatureVector],
    ) -> List[CandidateClassification]:
        results = []
        t0 = time.perf_counter()
        for fv in features:
            # Simple rule-based score calculation
            vals = fv.values
            peak = vals[0] if len(vals) > 0 else 0.5
            contrast = vals[2] if len(vals) > 2 else 1.0
            dist_pred = vals[7] if len(vals) > 7 else 0.5

            score = 0.5 * peak + 0.3 * min(1.0, contrast / 5.0) + 0.2 * (1.0 - min(1.0, dist_pred))
            prob = float(np.clip(score, 0.0, 1.0))
            is_b = prob >= 0.5

            results.append(
                CandidateClassification(
                    candidate_id=fv.candidate_id,
                    beacon_probability=prob,
                    is_beacon=is_b,
                    classifier_score=score,
                    model_name="RuleBasedFallback",
                    model_version="v0.0",
                    inference_time_ms=(time.perf_counter() - t0) * 1000.0 / max(1, len(features)),
                    used_fallback=True,
                    fallback_reason="Rule-based baseline active",
                )
            )
        return results


class LearnedCandidateClassifier(ICandidateClassifier):
    """
    Learned candidate classifier executing logistic-regression / linear model inference.
    """

    def __init__(
        self,
        model_dir: str = "models/candidate_classifier/v001",
        fallback: Optional[ICandidateClassifier] = None,
    ) -> None:
        self.model_dir = model_dir
        self.fallback = fallback or RuleBasedClassifierFallback()
        self.package: Optional[ModelPackage] = None
        self.calibrator = ProbabilityCalibrator()

        self._load_model()

    def _load_model(self) -> None:
        try:
            model_path = Path(self.model_dir)
            if not model_path.is_absolute() and not model_path.exists():
                project_root = Path(__file__).resolve().parents[2]
                model_path = project_root / model_path
            if model_path.exists():
                self.package = ModelLoader.load_candidate_classifier_package(str(model_path))
        except Exception as e:
            print(f"[LearnedCandidateClassifier] Warning loading model from {self.model_dir}: {e}")
            self.package = None

    def classify(
        self,
        features: List[CandidateFeatureVector],
    ) -> List[CandidateClassification]:
        if not features:
            return []

        if self.package is None:
            return self.fallback.classify(features)

        results = []
        t0 = time.perf_counter()

        try:
            if any(tuple(fv.feature_names) != self.package.feature_names for fv in features):
                return self.fallback.classify(features)

            # Batch feature matrix
            X = np.array([fv.values for fv in features], dtype=np.float32)

            # Feature dimension check
            if X.shape[1] != len(self.package.weights):
                print(f"[LearnedCandidateClassifier] Dimension mismatch ({X.shape[1]} vs {len(self.package.weights)}). Using fallback.")
                return self.fallback.classify(features)

            # Standardize
            X_scaled = (X - self.package.mean) / self.package.std

            # Logistic Regression inference
            logits = np.dot(X_scaled, self.package.weights) + self.package.bias
            probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -20.0, 20.0)))
            if not np.isfinite(probs).all():
                return self.fallback.classify(features)

            total_ms = (time.perf_counter() - t0) * 1000.0
            per_item_ms = total_ms / len(features)

            for i, fv in enumerate(features):
                prob = float(probs[i])
                prob_cal = self.calibrator.calibrate(prob)
                is_b = prob_cal >= self.package.classification_threshold

                results.append(
                    CandidateClassification(
                        candidate_id=fv.candidate_id,
                        beacon_probability=prob_cal,
                        is_beacon=is_b,
                        classifier_score=prob,
                        model_name=self.package.model_name,
                        model_version=self.package.model_version,
                        inference_time_ms=per_item_ms,
                        used_fallback=False,
                        fallback_reason=None,
                    )
                )

        except Exception as e:
            print(f"[LearnedCandidateClassifier] Inference exception: {e}. Reverting to fallback.")
            return self.fallback.classify(features)

        return results
