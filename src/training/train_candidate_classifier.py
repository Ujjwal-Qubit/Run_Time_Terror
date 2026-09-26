"""
Candidate Classifier Training Script — Trains Logistic Regression / MLP classifiers,
evaluates precision/recall/F1/AUC, calibrates threshold on val split, and exports model package to
models/candidate_classifier/v001/ per Runbook §4.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import numpy as np

from src.aiml.feature_extractor import FEATURE_NAMES
from src.aiml.calibration import ProbabilityCalibrator
from src.training.export_model import ModelExporter


def train_candidate_classifier(
    dataset_dir: str = "datasets/processed/candidate-v1",
    output_model_dir: str = "models/candidate_classifier/v001",
    seed: int = 42,
) -> str:
    """
    Train candidate classifier on train.json, validate on val.json, test on test.json,
    and export model package to output_model_dir.
    """
    train_path = os.path.join(dataset_dir, "train.json")
    val_path = os.path.join(dataset_dir, "val.json")
    test_path = os.path.join(dataset_dir, "test.json")

    n_features = len(FEATURE_NAMES)

    def load_split(path: str):
        if not os.path.isfile(path):
            return np.empty((0, n_features), dtype=np.float32), np.empty(0, dtype=np.float32)
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        if not records:
            return np.empty((0, n_features), dtype=np.float32), np.empty(0, dtype=np.float32)
        x = np.asarray(
            [[record["features"][name] for name in FEATURE_NAMES] for record in records],
            dtype=np.float32,
        )
        y = np.asarray([record["label"] for record in records], dtype=np.float32)
        if x.ndim != 2 or x.shape[1] != n_features or not np.isfinite(x).all():
            raise ValueError(f"Invalid feature matrix in {path}; expected {n_features} finite features per row")
        if not np.isin(y, [0.0, 1.0]).all():
            raise ValueError(f"Invalid binary labels in {path}")
        return x, y

    X_train, y_train = load_split(train_path)
    X_val, y_val = load_split(val_path)
    X_test, y_test = load_split(test_path)

    if len(X_train) == 0:
        raise ValueError("Training split is empty; generate or provide a labeled candidate dataset")
    if len(np.unique(y_train)) < 2:
        raise ValueError("Training split must contain examples from both classes")

    # Standardize
    mean = np.mean(X_train, axis=0)
    std = np.std(X_train, axis=0)
    std[std == 0.0] = 1.0

    X_scaled = (X_train - mean) / std

    # Train Logistic Regression via Gradient Descent
    n_samples = X_scaled.shape[0]
    weights = np.zeros(n_features, dtype=np.float32)
    bias = 0.0
    lr = 0.1

    for _ in range(500):
        logits = np.dot(X_scaled, weights) + bias
        preds = 1.0 / (1.0 + np.exp(-np.clip(logits, -20.0, 20.0)))

        dw = (1.0 / n_samples) * np.dot(X_scaled.T, (preds - y_train))
        db = (1.0 / n_samples) * np.sum(preds - y_train)

        weights -= lr * dw
        bias -= lr * db

    # Evaluate validation metrics
    def predict_probabilities(features: np.ndarray) -> np.ndarray:
        scaled = (features - mean) / std
        logits = np.dot(scaled, weights) + bias
        return 1.0 / (1.0 + np.exp(-np.clip(logits, -20.0, 20.0)))

    def classification_metrics(y_true: np.ndarray, probabilities: np.ndarray, threshold: float):
        predicted = probabilities >= threshold
        tp = int(np.sum(predicted & (y_true == 1)))
        fp = int(np.sum(predicted & (y_true == 0)))
        fn = int(np.sum(~predicted & (y_true == 1)))
        precision = float(tp / max(1, tp + fp))
        recall = float(tp / max(1, tp + fn))
        f1 = float(2 * precision * recall / max(1e-6, precision + recall))
        return {"precision": precision, "recall": recall, "f1": f1}

    if len(X_val) == 0 or len(np.unique(y_val)) < 2:
        raise ValueError("Validation split must contain examples from both classes")
    probs_val = predict_probabilities(X_val)
    best_thresh = ProbabilityCalibrator.find_optimal_threshold(y_val, probs_val)
    val_metrics = classification_metrics(y_val, probs_val, best_thresh)

    if len(X_test) == 0:
        raise ValueError("Test split is empty; refusing to report fabricated test metrics")
    test_metrics = classification_metrics(y_test, predict_probabilities(X_test), best_thresh)

    # Export model package
    out_dir = ModelExporter.export_candidate_classifier(
        output_dir=output_model_dir,
        weights=weights,
        bias=bias,
        mean=mean,
        std=std,
        feature_names=FEATURE_NAMES,
        classification_threshold=best_thresh,
        validation_metrics=val_metrics,
        test_metrics=test_metrics,
        random_seed=seed,
    )

    print(
        f"[TrainCandidateClassifier] Exported {out_dir} "
        f"(validation F1: {val_metrics['f1']:.4f}, "
        f"test F1: {test_metrics['f1']:.4f}, threshold: {best_thresh:.2f})"
    )
    return out_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Candidate Classifier")
    parser.add_argument("--dataset", type=str, default="datasets/processed/candidate-v1")
    parser.add_argument("--output", type=str, default="models/candidate_classifier/v001")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_candidate_classifier(
        dataset_dir=args.dataset,
        output_model_dir=args.output,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()

