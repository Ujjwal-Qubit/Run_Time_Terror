"""Summarize held-out metrics stored in versioned model artifacts."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Optional


class ModelEvaluator:
    """Read and validate real validation/test metrics for exported model packages."""

    def __init__(self, output_dir: str = "experiments/results/model-evaluation") -> None:
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def _read_package(model_dir: str, task: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(model_dir, "model.json")
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as stream:
            model = json.load(stream)
        validation = model.get("validation_metrics")
        test = model.get("test_metrics")
        if not isinstance(validation, dict) or not isinstance(test, dict):
            raise ValueError(f"{task} model package lacks validation/test metrics: {path}")
        return {
            "task": task,
            "model_name": model.get("model_name", task),
            "model_version": model.get("model_version", "unknown"),
            "algorithm": model.get("algorithm", "unknown"),
            "validation_metrics": validation,
            "test_metrics": test,
            "artifact": os.path.abspath(path),
        }

    def evaluate_combinations(
        self,
        candidate_model_dir: str = "models/candidate_classifier/v001",
        temporal_model_dir: str = "models/temporal_predictor/v001",
    ) -> str:
        """Write artifact metrics without inventing cross-task comparison scores."""
        packages = [
            package for package in (
                self._read_package(candidate_model_dir, "candidate_classification"),
                self._read_package(temporal_model_dir, "temporal_prediction"),
            ) if package is not None
        ]
        if not packages:
            raise FileNotFoundError("No model packages were found to evaluate")
        summary_path = os.path.join(self.output_dir, "summary.json")
        with open(summary_path, "w", encoding="utf-8") as stream:
            json.dump({
                "evaluation_type": "held_out_model_artifact_metrics",
                "models": packages,
                "winner": None,
                "winner_note": "Different tasks/metrics are reported independently and are not rank-comparable.",
            }, stream, indent=2)
        print(f"[ModelEvaluator] Held-out model metrics saved to {summary_path}")
        return summary_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate exported model artifacts")
    parser.add_argument("--candidate-model", type=str, default="models/candidate_classifier/v001")
    parser.add_argument("--temporal-model", type=str, default="models/temporal_predictor/v001")
    parser.add_argument("--output", type=str, default="experiments/results/model-evaluation")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluator = ModelEvaluator(output_dir=args.output)
    evaluator.evaluate_combinations(args.candidate_model, args.temporal_model)


if __name__ == "__main__":
    main()