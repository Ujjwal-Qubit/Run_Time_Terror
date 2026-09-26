"""Offline model training, evaluation, and export utilities.

Exports are loaded lazily so ``python -m src.training.train_candidate_classifier``
does not import its target module before ``runpy`` executes it.
"""

__all__ = ["ModelExporter", "train_candidate_classifier", "train_temporal_predictor", "ModelEvaluator"]


def __getattr__(name: str):
    if name == "ModelExporter":
        from src.training.export_model import ModelExporter
        return ModelExporter
    if name == "train_candidate_classifier":
        from src.training.train_candidate_classifier import train_candidate_classifier
        return train_candidate_classifier
    if name == "train_temporal_predictor":
        from src.training.train_temporal_predictor import train_temporal_predictor
        return train_temporal_predictor
    if name == "ModelEvaluator":
        from src.training.evaluate_models import ModelEvaluator
        return ModelEvaluator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
