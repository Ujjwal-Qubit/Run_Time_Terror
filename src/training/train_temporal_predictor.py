"""Train a residual temporal predictor from grouped temporal dataset splits."""

from __future__ import annotations

import argparse
import json
import os
from typing import Dict, List, Tuple

import numpy as np

from src.training.export_model import ModelExporter


def _load_examples(path: str) -> Tuple[np.ndarray, np.ndarray]:
    with open(path, "r", encoding="utf-8") as stream:
        records = json.load(stream)
    features: List[List[float]] = []
    residuals: List[List[float]] = []
    for record in records:
        history = [
            item for item in record.get("input_history", [])
            if item.get("valid") and item.get("x") is not None and item.get("y") is not None
        ]
        target = record.get("target", {})
        if len(history) < 2 or target.get("x") is None or target.get("y") is None:
            continue
        latest = history[-1]
        horizon = int(record["frame_number"]) / 30.0 - float(latest["timestamp"])
        if horizon <= 0.0:
            continue
        vx = vy = 0.0
        for previous, current in zip(history, history[1:]):
            dt = float(current["timestamp"]) - float(previous["timestamp"])
            if dt <= 0.0:
                continue
            measured_vx = (float(current["x"]) - float(previous["x"])) / dt
            measured_vy = (float(current["y"]) - float(previous["y"])) / dt
            vx = 0.6 * vx + 0.4 * measured_vx
            vy = 0.6 * vy + 0.4 * measured_vy
        features.append([vx, vy, min(1.0, len(history) / 20.0)])
        residuals.append([
            float(target["x"]) - (float(latest["x"]) + vx * horizon),
            float(target["y"]) - (float(latest["y"]) + vy * horizon),
        ])
    if not features:
        return np.empty((0, 3), dtype=np.float32), np.empty((0, 2), dtype=np.float32)
    return np.asarray(features, dtype=np.float32), np.asarray(residuals, dtype=np.float32)


def train_temporal_predictor(
    dataset_dir: str = "datasets/processed/temporal-v1",
    output_model_dir: str = "models/temporal_predictor/v001",
    seed: int = 42,
    epochs: int = 1500,
) -> str:
    """Train a small ReLU MLP and select its checkpoint on validation RMSE."""
    splits: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
    for name in ("train", "val", "test"):
        path = os.path.join(dataset_dir, f"{name}.json")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Required temporal {name} split not found: {path}")
        splits[name] = _load_examples(path)
        if len(splits[name][0]) == 0:
            raise ValueError(f"Temporal {name} split contains no usable sequences")

    x_train, y_train = splits["train"]
    x_val, y_val = splits["val"]
    x_test, y_test = splits["test"]
    input_mean = x_train.mean(axis=0)
    input_std = x_train.std(axis=0)
    input_std[input_std == 0.0] = 1.0
    x_train = (x_train - input_mean) / input_std
    x_val_scaled = (x_val - input_mean) / input_std

    rng = np.random.RandomState(seed)
    n_inputs, n_hidden, n_outputs = 3, 8, 2
    weights_h = (rng.randn(n_inputs, n_hidden) * np.sqrt(2.0 / n_inputs)).astype(np.float32)
    bias_h = np.zeros(n_hidden, dtype=np.float32)
    weights_o = (rng.randn(n_hidden, n_outputs) * 0.01).astype(np.float32)
    bias_o = np.zeros(n_outputs, dtype=np.float32)
    best_val_rmse = float("inf")
    best_params = None

    for _ in range(max(1, epochs)):
        hidden_pre = x_train @ weights_h + bias_h
        hidden = np.maximum(0.0, hidden_pre)
        error = hidden @ weights_o + bias_o - y_train
        grad_output = (2.0 / len(y_train)) * error
        grad_weights_o = hidden.T @ grad_output
        grad_bias_o = grad_output.sum(axis=0)
        grad_hidden = (grad_output @ weights_o.T) * (hidden_pre > 0.0)
        grad_weights_h = x_train.T @ grad_hidden
        grad_bias_h = grad_hidden.sum(axis=0)
        weights_o -= 0.01 * grad_weights_o
        bias_o -= 0.01 * grad_bias_o
        weights_h -= 0.01 * grad_weights_h
        bias_h -= 0.01 * grad_bias_h

        val_prediction = np.maximum(0.0, x_val_scaled @ weights_h + bias_h) @ weights_o + bias_o
        val_rmse = float(np.sqrt(np.mean((val_prediction - y_val) ** 2)))
        if np.isfinite(val_rmse) and val_rmse < best_val_rmse:
            best_val_rmse = val_rmse
            best_params = tuple(p.copy() for p in (weights_h, bias_h, weights_o, bias_o))
    if best_params is None:
        raise RuntimeError("Temporal training produced no finite validation checkpoint")
    weights_h, bias_h, weights_o, bias_o = best_params

    def calculate_rmse(features: np.ndarray, targets: np.ndarray) -> float:
        normalized = (features - input_mean) / input_std
        predicted = np.maximum(0.0, normalized @ weights_h + bias_h) @ weights_o + bias_o
        return float(np.sqrt(np.mean((predicted - targets) ** 2)))

    validation_metrics = {
        "residual_rmse_px": calculate_rmse(x_val, y_val),
        "examples": float(len(y_val)),
    }
    test_metrics = {
        "residual_rmse_px": calculate_rmse(x_test, y_test),
        "examples": float(len(y_test)),
    }
    out_dir = ModelExporter.export_temporal_predictor(
        output_dir=output_model_dir,
        weights_h=weights_h,
        bias_h=bias_h,
        weights_o=weights_o,
        bias_o=bias_o,
        model_name="temporal_predictor",
        model_version="v001",
        algorithm="residual_mlp",
        validation_metrics=validation_metrics,
        test_metrics=test_metrics,
        input_mean=input_mean,
        input_std=input_std,
    )
    print(
        f"[TrainTemporalPredictor] Exported {out_dir} "
        f"(validation RMSE: {validation_metrics['residual_rmse_px']:.4f}px; "
        f"test RMSE: {test_metrics['residual_rmse_px']:.4f}px)"
    )
    return out_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train temporal residual predictor")
    parser.add_argument("--dataset", type=str, default="datasets/processed/temporal-v1")
    parser.add_argument("--output", type=str, default="models/temporal_predictor/v001")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=1500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_temporal_predictor(args.dataset, args.output, seed=args.seed, epochs=args.epochs)


if __name__ == "__main__":
    main()