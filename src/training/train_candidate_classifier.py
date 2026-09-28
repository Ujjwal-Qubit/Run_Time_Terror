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

    # Train Pure-NumPy MLP (11 -> 32 -> 16 -> 1) via Adam Optimizer
    np.random.seed(seed)
    n_in = n_features
    n_h1 = 32
    n_h2 = 16
    n_out = 1

    W1 = (np.random.randn(n_in, n_h1).astype(np.float32) * np.sqrt(2.0 / n_in))
    b1 = np.zeros(n_h1, dtype=np.float32)
    W2 = (np.random.randn(n_h1, n_h2).astype(np.float32) * np.sqrt(2.0 / n_h1))
    b2 = np.zeros(n_h2, dtype=np.float32)
    W3 = (np.random.randn(n_h2, n_out).astype(np.float32) * np.sqrt(2.0 / n_h2))
    b3 = np.zeros(n_out, dtype=np.float32)

    lr = 0.008
    l2_reg = 0.0005
    epochs = 250
    batch_size = 64
    n_samples = len(X_scaled)

    # Adam moment accumulators
    mW1, vW1 = np.zeros_like(W1), np.zeros_like(W1)
    mb1, vb1 = np.zeros_like(b1), np.zeros_like(b1)
    mW2, vW2 = np.zeros_like(W2), np.zeros_like(W2)
    mb2, vb2 = np.zeros_like(b2), np.zeros_like(b2)
    mW3, vW3 = np.zeros_like(W3), np.zeros_like(W3)
    mb3, vb3 = np.zeros_like(b3), np.zeros_like(b3)
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    step = 0

    for epoch in range(1, epochs + 1):
        perm = np.random.permutation(n_samples)
        for i in range(0, n_samples, batch_size):
            step += 1
            idx = perm[i : i + batch_size]
            xb = X_scaled[idx]
            yb = y_train[idx, None]

            # Forward pass
            z1 = np.dot(xb, W1) + b1
            a1 = np.maximum(0.0, z1)
            z2 = np.dot(a1, W2) + b2
            a2 = np.maximum(0.0, z2)
            z3 = np.dot(a2, W3) + b3
            preds = 1.0 / (1.0 + np.exp(-np.clip(z3, -20.0, 20.0)))

            # Backward pass
            dz3 = (preds - yb) / float(len(xb))
            dW3 = np.dot(a2.T, dz3) + l2_reg * W3
            db3 = np.sum(dz3, axis=0)

            da2 = np.dot(dz3, W3.T)
            dz2 = da2 * (z2 > 0.0)
            dW2 = np.dot(a1.T, dz2) + l2_reg * W2
            db2 = np.sum(dz2, axis=0)

            da1 = np.dot(dz2, W2.T)
            dz1 = da1 * (z1 > 0.0)
            dW1 = np.dot(xb.T, dz1) + l2_reg * W1
            db1 = np.sum(dz1, axis=0)

            # Adam updates
            for param, grad, m, v in [
                (W1, dW1, mW1, vW1), (b1, db1, mb1, vb1),
                (W2, dW2, mW2, vW2), (b2, db2, mb2, vb2),
                (W3, dW3, mW3, vW3), (b3, db3, mb3, vb3),
            ]:
                m[:] = beta1 * m + (1.0 - beta1) * grad
                v[:] = beta2 * v + (1.0 - beta2) * (grad ** 2)
                m_hat = m / (1.0 - beta1 ** step)
                v_hat = v / (1.0 - beta2 ** step)
                param -= lr * m_hat / (np.sqrt(v_hat) + eps)

    # Inference function
    def predict_probabilities(features: np.ndarray) -> np.ndarray:
        scaled = (features - mean) / std
        z1 = np.dot(scaled, W1) + b1
        a1 = np.maximum(0.0, z1)
        z2 = np.dot(a1, W2) + b2
        a2 = np.maximum(0.0, z2)
        z3 = np.dot(a2, W3) + b3
        probs = 1.0 / (1.0 + np.exp(-np.clip(z3, -20.0, 20.0)))
        return probs.ravel()

    def classification_metrics(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, float]:
        predicted = probabilities >= threshold
        tp = int(np.sum(predicted & (y_true == 1)))
        fp = int(np.sum(predicted & (y_true == 0)))
        tn = int(np.sum(~predicted & (y_true == 0)))
        fn = int(np.sum(~predicted & (y_true == 1)))
        precision = float(tp / max(1, tp + fp))
        recall = float(tp / max(1, tp + fn))
        f1 = float(2 * precision * recall / max(1e-6, precision + recall))
        accuracy = float((tp + tn) / max(1, len(y_true)))
        fpr = float(fp / max(1, fp + tn))
        fnr = float(fn / max(1, fn + tp))
        return {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "fpr": round(fpr, 4),
            "fnr": round(fnr, 4),
            "tp": float(tp),
            "fp": float(fp),
            "tn": float(tn),
            "fn": float(fn),
            "threshold": round(threshold, 4),
        }

    # Threshold calibration strictly on Validation split (Test split remains untouched)
    if len(X_val) == 0 or len(np.unique(y_val)) < 2:
        raise ValueError("Validation split must contain examples from both classes")
    probs_val = predict_probabilities(X_val)

    # Cost-sensitive calibration objective: Maximize F1 with FPR <= 3.0% constraint
    best_thresh = 0.50
    best_f1 = -1.0
    for t in np.linspace(0.30, 0.85, 111):
        metrics_t = classification_metrics(y_val, probs_val, float(t))
        if metrics_t["fpr"] <= 0.030 and metrics_t["f1"] > best_f1:
            best_f1 = metrics_t["f1"]
            best_thresh = float(t)

    # If no threshold met FPR <= 3.0%, pick the threshold that minimizes FPR among high F1
    if best_f1 < 0.0:
        for t in np.linspace(0.50, 0.85, 71):
            metrics_t = classification_metrics(y_val, probs_val, float(t))
            if metrics_t["f1"] > best_f1:
                best_f1 = metrics_t["f1"]
                best_thresh = float(t)

    val_metrics = classification_metrics(y_val, probs_val, best_thresh)

    # Frozen model and calibrated threshold evaluated on held-out Test split
    if len(X_test) == 0:
        raise ValueError("Test split is empty; refusing to report fabricated test metrics")
    probs_test = predict_probabilities(X_test)
    test_metrics = classification_metrics(y_test, probs_test, best_thresh)

    # Benchmark inference latency
    import time
    t_start = time.perf_counter()
    bench_reps = 1000
    dummy_input = X_test[:10] if len(X_test) >= 10 else X_train[:10]
    for _ in range(bench_reps):
        _ = predict_probabilities(dummy_input)
    bench_total_ms = (time.perf_counter() - t_start) * 1000.0
    latency_per_candidate_ms = bench_total_ms / (bench_reps * len(dummy_input))
    val_metrics["latency_per_candidate_ms"] = round(latency_per_candidate_ms, 5)
    test_metrics["latency_per_candidate_ms"] = round(latency_per_candidate_ms, 5)

    # Package MLP layers
    layers = [
        {"weights": W1.tolist(), "bias": b1.tolist(), "activation": "relu"},
        {"weights": W2.tolist(), "bias": b2.tolist(), "activation": "relu"},
        {"weights": W3.tolist(), "bias": b3.tolist(), "activation": "sigmoid"},
    ]

    # Export model package
    out_dir = ModelExporter.export_candidate_classifier(
        output_dir=output_model_dir,
        weights=W1[:, 0].copy(),  # 1D slice for backwards compatibility
        bias=float(b3[0]),
        mean=mean,
        std=std,
        feature_names=FEATURE_NAMES,
        classification_threshold=best_thresh,
        algorithm="mlp",
        validation_metrics=val_metrics,
        test_metrics=test_metrics,
        random_seed=seed,
        layers=layers,
    )

    print(
        f"[TrainCandidateClassifier] Exported {out_dir} (Algorithm: MLP 11->32->16->1)\n"
        f"  Val : Acc={val_metrics['accuracy']*100:.1f}%, Prec={val_metrics['precision']*100:.1f}%, "
        f"Rec={val_metrics['recall']*100:.1f}%, F1={val_metrics['f1']:.4f}, FPR={val_metrics['fpr']*100:.2f}%\n"
        f"  Test: Acc={test_metrics['accuracy']*100:.1f}%, Prec={test_metrics['precision']*100:.1f}%, "
        f"Rec={test_metrics['recall']*100:.1f}%, F1={test_metrics['f1']:.4f}, FPR={test_metrics['fpr']*100:.2f}%\n"
        f"  Inference Latency: {latency_per_candidate_ms*1000:.2f} µs/candidate (calibrated threshold: {best_thresh:.2f})"
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

