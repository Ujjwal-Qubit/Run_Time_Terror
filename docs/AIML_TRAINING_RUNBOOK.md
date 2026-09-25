# AIML Dataset and Model Workflow

This project keeps learned components behind the algorithm/plugin boundary. The learned candidate classifier and temporal residual predictor are optional and disabled by default; the deterministic baseline detector, rule/legacy candidate scoring, Kalman tracker, and plugin API continue to work without model files. When enabled, the temporal model only influences candidate ranking; the existing Kalman tracker remains the authoritative state estimator.

Run these commands from the `Run_Time_Error` project root, using the same Python environment as the application.

## Generate datasets

```powershell
python -m src.data.dataset_generator --task candidate --scenarios 9 --frames-per-scenario 100 --output datasets/processed/candidate-v1
python -m src.data.dataset_generator --task temporal --scenarios 9 --frames-per-scenario 100 --output datasets/processed/temporal-v1
```

Splits are grouped by simulation run/sequence to prevent adjacent frames from leaking between train, validation, and test partitions. At least three independent groups are required.

## Train and report models

```powershell
python -m src.training.train_candidate_classifier --dataset datasets/processed/candidate-v1 --output models/candidate_classifier/v001 --seed 42
python -m src.training.train_temporal_predictor --dataset datasets/processed/temporal-v1 --output models/temporal_predictor/v001 --seed 42
python -m src.training.evaluate_models --output experiments/results/model-evaluation
```

Candidate training selects its probability threshold using the validation split and reports test metrics separately. Temporal training selects the checkpoint using validation residual RMSE and reports held-out test RMSE. Training fails clearly when required real splits are missing; it does not manufacture placeholder test scores.

## Enable the learned classifier

In the desktop application, open **Configuration → AI/ML**, enable **Use learned candidate classifier**, and confirm the package directory. The equivalent scenario JSON section is:

```json
{
  "aiml": {
    "candidate_classifier_enabled": true,
    "candidate_model_dir": "models/candidate_classifier/v001",
    "temporal_predictor_enabled": true,
    "temporal_model_dir": "models/temporal_predictor/v001"
  }
}
```

Relative model directories resolve from the project root. If a model is absent, invalid, or incompatible with the declared feature schema, the algorithm falls back to its existing candidate-identification path.

## Model artifacts and boundaries

- `models/candidate_classifier/v001/` contains a classifier trained from the checked-in grouped candidate dataset. Re-train it after regenerating or changing feature data.
- `models/temporal_predictor/v001/` contains the dataset-trained residual predictor and normalization parameters. Its inference API uses only bounded observable track history; the plugin uses valid predictions as a candidate-ranking prior.
- The evaluator reports actual per-task validation/test metrics independently; it does not invent a winner across incomparable classification and regression tasks.
- Ground truth is used only to label offline simulation datasets and compute evaluation metrics. It is not passed into runtime classifier or predictor features.
