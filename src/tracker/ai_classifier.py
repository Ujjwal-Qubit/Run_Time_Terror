"""
AI Classifier — Module 11 AI Augmentation per Phase 3.

Uses a lightweight Logistic Regression classifier to classify candidates as beacon or noise.
Satisfies the "AI-based" requirement of the PRD while maintaining >= 20 FPS,
implemented purely in NumPy to avoid OpenCV ML module dependencies.
"""

from __future__ import annotations

import os
import json
import numpy as np
from typing import List, Optional, Tuple, Union

from src.tracker.candidate_identifier import CandidateIdentifier
from src.frame.data_contracts import CandidateRegion, ScoredCandidate, TrackingState
from src.config.config_manager import IdentifierConfig


class AIClassifier(CandidateIdentifier):
    """
    AI-Augmented Candidate Identifier using NumPy Logistic Regression.
    Overrides the P0 baseline rule-based scoring with an ML classifier.
    """

    def __init__(self, config: Optional[IdentifierConfig] = None, model_path: str = "lr_model.json") -> None:
        super().__init__(config)
        self.model_path = model_path
        self.weights = None
        self.bias = None
        self.is_trained = False
        
        # Load model if exists, else train a dummy
        if os.path.exists(self.model_path):
            with open(self.model_path, 'r') as f:
                data = json.load(f)
                self.weights = np.array(data["weights"], dtype=np.float32)
                self.bias = float(data["bias"])
            self.is_trained = True
        else:
            self._train_synthetic_model()

    def _train_synthetic_model(self) -> None:
        """
        Trains a synthetic baseline Logistic Regression model using Gradient Descent.
        """
        print("[AIClassifier] Training synthetic Logistic Regression model...")
        
        # Features: [norm_peak, norm_contrast, compactness, aspect_ratio]
        
        # Positive samples (Beacons)
        pos_samples = []
        for _ in range(200):
            peak = np.random.uniform(0.7, 1.0)
            contrast = np.random.uniform(0.5, 1.0)
            compactness = np.random.uniform(0.7, 1.0)
            aspect = np.random.uniform(0.9, 1.1)
            pos_samples.append([peak, contrast, compactness, aspect])
            
        # Negative samples (Noise/Clutter)
        neg_samples = []
        for _ in range(200):
            peak = np.random.uniform(0.1, 0.6)
            contrast = np.random.uniform(0.0, 0.4)
            compactness = np.random.uniform(0.1, 0.6)
            aspect = np.random.uniform(1.5, 3.0)
            neg_samples.append([peak, contrast, compactness, aspect])
            
        X = np.array(pos_samples + neg_samples, dtype=np.float32)
        y = np.array([1]*200 + [0]*200, dtype=np.float32)
        
        # Standardize features
        self.mean = np.mean(X, axis=0)
        self.std = np.std(X, axis=0)
        X_scaled = (X - self.mean) / self.std

        # Gradient Descent
        n_samples, n_features = X.shape
        self.weights = np.zeros(n_features)
        self.bias = 0.0
        learning_rate = 0.1
        
        for _ in range(1000):
            linear_model = np.dot(X_scaled, self.weights) + self.bias
            y_predicted = 1.0 / (1.0 + np.exp(-linear_model))
            
            dw = (1 / n_samples) * np.dot(X_scaled.T, (y_predicted - y))
            db = (1 / n_samples) * np.sum(y_predicted - y)
            
            self.weights -= learning_rate * dw
            self.bias -= learning_rate * db
            
        # Save model
        with open(self.model_path, 'w') as f:
            json.dump({
                "weights": self.weights.tolist(),
                "bias": self.bias,
                "mean": self.mean.tolist(),
                "std": self.std.tolist()
            }, f)
            
        self.is_trained = True
        print(f"[AIClassifier] Model saved to {self.model_path}")

    def _extract_features(self, candidate: CandidateRegion) -> np.ndarray:
        """Extracts the 4D feature vector."""
        norm_peak = min(1.0, candidate.peak_intensity / 255.0)
        norm_contrast = min(1.0, max(0.0, (candidate.local_contrast - 1.0) / 2.0))
        compactness = candidate.compactness
        
        bw = candidate.bbox_w
        bh = candidate.bbox_h
        aspect_ratio = max(bw, bh) / max(1.0, float(min(bw, bh)))
        
        return np.array([norm_peak, norm_contrast, compactness, aspect_ratio], dtype=np.float32)

    def score_candidate(
        self,
        candidate: CandidateRegion,
        predicted_position: Optional[Tuple[float, float]],
        current_state: TrackingState,
    ) -> float:
        """
        Overrides the baseline scoring to use the LR inference.
        """
        base_score = super().score_candidate(candidate, predicted_position, current_state)
        
        if not self.is_trained:
            return base_score
            
        # AI Inference
        features = self._extract_features(candidate)
        features_scaled = (features - self.mean) / self.std
        
        linear_model = np.dot(features_scaled, self.weights) + self.bias
        ai_score = 1.0 / (1.0 + np.exp(-linear_model))
        
        # Hybrid ensemble score: 60% AI, 40% Kinematic Proximity (Baseline)
        final_score = 0.6 * ai_score + 0.4 * base_score
        
        return float(final_score)
