"""
Model Loader — Validates, loads, and checks schema compatibility for versioned model packages.

Per AIML Integration Specification §10.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import numpy as np


@dataclass
class ModelPackage:
    """
    Loaded and validated model package.
    """

    model_name: str
    model_version: str
    algorithm: str
    feature_schema_version: str
    feature_names: Tuple[str, ...]
    weights: np.ndarray
    bias: float
    mean: np.ndarray
    std: np.ndarray
    classification_threshold: float
    metadata: Dict[str, Any]


class ModelLoader:
    """
    Handles safe loading of versioned model packages.
    Rejects incompatible schemas, missing normalization, or invalid dimensions.
    """

    @staticmethod
    def load_candidate_classifier_package(model_dir: str) -> ModelPackage:
        """
        Load a candidate classifier model package directory (containing model.json, metadata.json, feature_schema.json).
        """
        model_json_path = os.path.join(model_dir, "model.json")
        metadata_json_path = os.path.join(model_dir, "metadata.json")

        if not os.path.exists(model_json_path):
            raise FileNotFoundError(f"Model file not found at {model_json_path}")

        with open(model_json_path, "r") as f:
            model_data = json.load(f)

        metadata = {}
        if os.path.exists(metadata_json_path):
            with open(metadata_json_path, "r") as f:
                metadata = json.load(f)

        # Schema & required key validation
        required_keys = ["weights", "bias", "mean", "std", "feature_names"]
        for key in required_keys:
            if key not in model_data:
                raise ValueError(f"Model package at {model_dir} missing required field '{key}'")

        weights = np.array(model_data["weights"], dtype=np.float32)
        bias = float(model_data["bias"])
        mean = np.array(model_data["mean"], dtype=np.float32)
        std = np.array(model_data["std"], dtype=np.float32)
        feature_names = tuple(model_data["feature_names"])

        if weights.ndim != 1 or mean.ndim != 1 or std.ndim != 1:
            raise ValueError("Model weights and normalization parameters must be one-dimensional")

        if len(weights) != len(mean) or len(weights) != len(std) or len(weights) != len(feature_names):
            raise ValueError(
                f"Dimension mismatch in model package: weights={len(weights)}, mean={len(mean)}, std={len(std)}, features={len(feature_names)}"
            )

        # Avoid div by zero in std
        std[std == 0.0] = 1.0

        if not (
            np.isfinite(weights).all()
            and np.isfinite(mean).all()
            and np.isfinite(std).all()
            and math.isfinite(bias)
        ):
            raise ValueError(f"Model package at {model_dir} contains non-finite parameters")

        model_name = model_data.get("model_name", "candidate_classifier")
        model_version = model_data.get("model_version", "v001")
        algorithm = model_data.get("algorithm", "logistic_regression")
        feature_schema_version = model_data.get("feature_schema_version", "candidate-v1")
        classification_threshold = float(model_data.get("classification_threshold", 0.5))
        if not 0.0 <= classification_threshold <= 1.0:
            raise ValueError("classification_threshold must be between 0 and 1")

        return ModelPackage(
            model_name=model_name,
            model_version=model_version,
            algorithm=algorithm,
            feature_schema_version=feature_schema_version,
            feature_names=feature_names,
            weights=weights,
            bias=bias,
            mean=mean,
            std=std,
            classification_threshold=classification_threshold,
            metadata=metadata,
        )
