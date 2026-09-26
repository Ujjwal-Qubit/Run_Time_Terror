"""
Model Exporter — Exports trained models into standard versioned package directories.

Per Spec §10 & Runbook §4.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class ModelExporter:
    """
    Exports trained weights, normalization parameters, and metadata into versioned package directories.
    """

    @staticmethod
    def export_candidate_classifier(
        output_dir: str,
        weights: np.ndarray,
        bias: float,
        mean: np.ndarray,
        std: np.ndarray,
        feature_names: Tuple[str, ...],
        classification_threshold: float = 0.5,
        model_name: str = "candidate_classifier",
        model_version: str = "v001",
        algorithm: str = "logistic_regression",
        validation_metrics: Optional[Dict[str, float]] = None,
        test_metrics: Optional[Dict[str, float]] = None,
        random_seed: int = 42,
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)

        model_data = {
            "model_name": model_name,
            "model_version": model_version,
            "algorithm": algorithm,
            "feature_schema_version": "candidate-v1",
            "feature_names": list(feature_names),
            "weights": weights.tolist(),
            "bias": float(bias),
            "mean": mean.tolist(),
            "std": std.tolist(),
            "classification_threshold": float(classification_threshold),
            "training_dataset_version": "candidate-v1",
            "random_seed": int(random_seed),
            "validation_metrics": validation_metrics or {},
            "test_metrics": test_metrics or {},
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        metadata_data = {
            "model_name": model_name,
            "model_version": model_version,
            "algorithm": algorithm,
            "feature_count": len(feature_names),
            "created_at": model_data["created_at"],
        }

        schema_data = {
            "feature_schema_version": "candidate-v1",
            "feature_names": list(feature_names),
        }

        with open(os.path.join(output_dir, "model.json"), "w") as f:
            json.dump(model_data, f, indent=2)

        with open(os.path.join(output_dir, "metadata.json"), "w") as f:
            json.dump(metadata_data, f, indent=2)

        with open(os.path.join(output_dir, "feature_schema.json"), "w") as f:
            json.dump(schema_data, f, indent=2)

        return output_dir

    @staticmethod
    def export_temporal_predictor(
        output_dir: str,
        weights_h: np.ndarray,
        bias_h: np.ndarray,
        weights_o: np.ndarray,
        bias_o: np.ndarray,
        model_name: str = "temporal_predictor",
        model_version: str = "v001",
        algorithm: str = "residual_mlp",
        validation_metrics: Optional[Dict[str, float]] = None,
        test_metrics: Optional[Dict[str, float]] = None,
        input_mean: Optional[np.ndarray] = None,
        input_std: Optional[np.ndarray] = None,
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)

        model_data = {
            "model_name": model_name,
            "model_version": model_version,
            "algorithm": algorithm,
            "weights_h": weights_h.tolist(),
            "bias_h": bias_h.tolist(),
            "weights_o": weights_o.tolist(),
            "bias_o": bias_o.tolist(),
            "input_mean": input_mean.tolist() if input_mean is not None else [0.0, 0.0, 0.0],
            "input_std": input_std.tolist() if input_std is not None else [1.0, 1.0, 1.0],
            "validation_metrics": validation_metrics or {},
            "test_metrics": test_metrics or {},
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        with open(os.path.join(output_dir, "model.json"), "w") as f:
            json.dump(model_data, f, indent=2)

        return output_dir
