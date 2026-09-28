# PHASE 4: LEGACY COMPONENT AUDIT & INVENTORY

**Document ID:** LUMITRACK-PHASE4-AUDIT-001  
**Version:** 1.0.0  
**Date:** September 28, 2026  
**System:** LumiTrack Autonomous Optical Beacon Tracking & PTZ Control Platform  
**Scope:** SIH 26169 / ISRO Dept. of Space  
**Status:** COMPLETE (Component Classifications & Dependency Proofs)  

---

## 1. Executive Summary

As part of Phase 4 (Legacy Cleanup, Standalone Windows Packaging, and Evaluator Readiness), this audit catalogs all software components, subsystems, models, datasets, and documentation across the LumiTrack repository. 

Every component is formally classified under one of eight governance categories:
1. **ACTIVE / REQUIRED:** Essential for runtime standalone desktop operation, tracking execution, and PTZ control.
2. **ACTIVE / SUPPORTING:** Operational auxiliary modules (e.g. dataset generator, probability calibration, training scripts, alternative classifiers).
3. **TEST ONLY:** Automated verification test suites, fixtures, and regression test cases.
4. **BENCHMARK ONLY:** Evaluation harnesses, scenario matrix runners, and reproducible validation scripts.
5. **DOCUMENTATION ONLY:** Manuals, guides, architecture documents, and specifications.
6. **LEGACY / SAFE TO REMOVE:** Confirmed dead or misplaced files with zero incoming imports, test dependencies, or packaging references.
7. **LEGACY / RETAIN FOR TRACEABILITY:** Historical forensic audits, pre-remediation baselines, and archived scripts retained for provenance.
8. **DEAD / CONFIRMED UNUSED:** Stale build artifacts, orphaned caches, or duplicate data files.

---

## 2. Component Inventory & Classification

### 2.1 Core Runtime Architecture (`src/`)

| Path / Module | Governance Status | Role & Functionality | Dependency / Incoming References |
| :--- | :--- | :--- | :--- |
| `src/main.py` | **ACTIVE / REQUIRED** | Unified application CLI & GUI launcher entry point. | Entrypoint for PyInstaller `lumitrack.spec`, batch CLI, GUI. |
| `src/app/app_controller.py` | **ACTIVE / REQUIRED** | Top-level system coordinator (Module 1). | Instantiated by `main.py`, GUI, benchmark harness. |
| `src/app/simulation_worker.py` | **ACTIVE / SUPPORTING** | Background simulation thread for PySide6 GUI. | Imported by `src/app/gui/main_window.py`. |
| `src/app/visualization_state.py`| **ACTIVE / SUPPORTING** | Thread-safe visualization contract between worker and UI. | Imported by `simulation_worker.py` and GUI widgets. |
| `src/app/gui/main_window.py` | **ACTIVE / REQUIRED** | Primary PySide6 desktop window for evaluator demonstration. | Launched by `src/app/gui/__init__.py:launch_gui()`. |
| `src/app/gui/config_panel.py` | **ACTIVE / REQUIRED** | Interactive GUI controls for scene, camera, target, and disturbances. | Embedded in `MainWindow`. |
| `src/app/gui/control_panel.py` | **ACTIVE / REQUIRED** | Play, pause, step, reset, and scenario selection controls. | Embedded in `MainWindow`. |
| `src/app/gui/evaluation_panel.py`| **ACTIVE / REQUIRED** | Evaluator GUI interface for BM1 scenarios and BM2 video replay. | Embedded in `MainWindow`. |
| `src/app/gui/results_panel.py` | **ACTIVE / REQUIRED** | Post-run scorecard, compliance metrics, and report export UI. | Embedded in `MainWindow`. |
| `src/app/gui/telemetry_panel.py`| **ACTIVE / REQUIRED** | Live numeric HUD displaying centroid error, state, and rate commands. | Embedded in `MainWindow`. |
| `src/app/gui/video_widget.py` | **ACTIVE / REQUIRED** | 2D OpenGL/QPainter camera viewport rendering target & reticle. | Embedded in `MainWindow`. |
| `src/app/gui/view_3d.py` | **ACTIVE / REQUIRED** | 3D orbital trajectory spatial visualization (CPU-safe QPainter). | Embedded in `MainWindow`. |
| `src/config/config_manager.py`| **ACTIVE / REQUIRED** | Authoritative `SystemConfig` dataclasses and validation (Module 2).| Core dependency across entire repository. |
| `src/config/defaults.py` | **ACTIVE / REQUIRED** | PS constants, default values, and operational limits. | Referenced by `config_manager.py`, tests, algorithms. |
| `src/config/scenario_manager.py`| **ACTIVE / REQUIRED** | JSON scenario serialization, discovery, and loading (Module 3). | Used by `AppController`, CLI, and GUI. |
| `src/simulation/scene_manager.py`| **ACTIVE / REQUIRED** | 2D rasterized $2000 \times 2000$ canvas rendering engine (Module 4). | Used by `AppController` and `SimulationFrameProvider`. |
| `src/simulation/target_manager.py`| **ACTIVE / REQUIRED** | Moving target kinematic generator with 9 trajectory modes (Module 5).| Used by `SceneManager`. |
| `src/simulation/camera_model.py`| **ACTIVE / REQUIRED** | Pinhole camera model, FOV projection, and pan/tilt motion (Module 6).| Used by `AppController` and PTZ controllers. |
| `src/simulation/disturbance_engine.py`| **ACTIVE / REQUIRED** | Atmospheric, jitter, drift, and noise perturbation engine (Module 7).| Used by `SceneManager`. |
| `src/control/ptz_controller.py`| **ACTIVE / REQUIRED** | Proportional deadband PTZ controller with anti-windup (Module 15).| Primary closed-loop gimbal controller. |
| `src/frame/data_contracts.py` | **ACTIVE / REQUIRED** | Public data contracts: `FramePacket`, `TrackingState`, `GroundTruth`.| Base contract across all operational modules. |
| `src/frame/simulation_provider.py`| **ACTIVE / REQUIRED** | Simulation frame provider (Module 8). | Ingested by `AppController` in BM1 mode. |
| `src/frame/mp4_provider.py` | **ACTIVE / REQUIRED** | OpenCV video ingestion provider for Benchmark-2 (Module 8). | Ingested by `AppController` in BM2 mode. |
| `src/interfaces/strategy_interfaces.py`| **ACTIVE / REQUIRED** | Formal abstract strategy interfaces for perception and control. | Inherited by algorithms and controllers. |
| `src/tracker/temporal_tracker.py`| **ACTIVE / REQUIRED** | Constant Velocity Kalman tracker with predictive coasting (Module 12).| Used by `BaselineTracker` and `TrackingPipeline`. |
| `src/tracker/candidate_identifier.py`| **ACTIVE / REQUIRED**| Candidate clustering, bounding box, and heuristic scoring (Module 10).| Used by detection pipeline. |
| `src/tracker/centroid_estimator.py`| **ACTIVE / REQUIRED**| Sub-pixel intensity-weighted center of mass estimator (Module 14).| Used by tracking pipeline. |
| `src/tracker/detection_engine.py`| **ACTIVE / REQUIRED**| Adaptive local background subtraction and segmentation (Module 9). | Used by tracking pipeline. |
| `src/tracker/tracking_pipeline.py`| **ACTIVE / REQUIRED**| Monolithic reference pipeline wrapper. | Tested in regression suite. |
| `src/tracker/ai_classifier.py`| **ACTIVE / SUPPORTING**| Alternative 4-feature Logistic Regression candidate classifier. | Tested in `test_ai_classifier.py`. |
| `src/aiml/candidate_classifier.py`| **ACTIVE / REQUIRED**| 11-feature pure-NumPy MLP candidate classifier (Phase 2 model). | Primary AI classifier active in `temporal_tracker.py`. |
| `src/aiml/model_loader.py` | **ACTIVE / REQUIRED** | Safe versioned model loader and schema validator. | Used by `LearnedCandidateClassifier`. |
| `src/aiml/feature_extractor.py`| **ACTIVE / REQUIRED**| 11-feature normalized candidate feature vector computation. | Used by `temporal_tracker.py` and dataset generator. |
| `src/aiml/contracts.py` | **ACTIVE / REQUIRED** | Candidate classification data contracts. | Used across `src/aiml/`. |
| `src/aiml/calibration.py` | **ACTIVE / SUPPORTING**| Probability calibrator (Platt scaling / temperature). | Used by `LearnedCandidateClassifier`. |
| `src/aiml/temporal_predictor.py`| **ACTIVE / SUPPORTING**| Linear/Kalman temporal predictor for candidate gating. | Used in auxiliary tracking tests. |
| `src/plugins/loader.py` | **ACTIVE / REQUIRED** | Dynamic plugin loader discovering external tracking algorithms. | Discovers `src/plugins/algorithms/`. |
| `src/plugins/algorithms/baseline_tracker/`| **ACTIVE / REQUIRED**| Reference `ITrackingAlgorithm` plugin implementing baseline. | Default tracking plugin bundled in PyInstaller. |
| `src/evaluation/harness.py` | **ACTIVE / REQUIRED** | Standardized evaluation experiment executor (Module 17). | Used by benchmarks, test suites, and CLI. |
| `src/evaluation/metrics_engine.py`| **ACTIVE / REQUIRED**| Objective calculation of RMSE, loss rate, FPS, latency. | Firewalled evaluation engine. |
| `src/evaluation/benchmark_manager.py`| **ACTIVE / REQUIRED**| High-level batch evaluation coordinator for BM1 and BM2. | Used by CLI (`--matrix`, `--eval-scenarios`). |
| `src/evaluation/matrix.py` | **ACTIVE / REQUIRED** | 19 standard benchmark scenario matrix definitions. | Core benchmark definitions. |
| `src/evaluation/ai_scenario.py`| **ACTIVE / REQUIRED**| Natural language scenario parsing and execution. | Tested in `test_phase6_7_ai_scenario.py`. |
| `src/data/dataset_generator.py`| **ACTIVE / SUPPORTING**| Generates candidate training datasets from simulation runs. | Used for offline model training. |
| `src/training/train_candidate_classifier.py`| **ACTIVE / SUPPORTING**| Pure-NumPy MLP training script (Phase 2). | Used to produce production weights. |
| `src/training/export_model.py`| **ACTIVE / SUPPORTING**| Model export and metadata serialization utility. | Exports `model.json` and `metadata.json`. |
| `src/api/server.py` | **ACTIVE / SUPPORTING**| FastAPI backend providing REST endpoints for scenario management. | Tested in `test_security_scenarios.py`. |
| `src/api/v1/` | **ACTIVE / REQUIRED** | Public Phase 6.1 `ITrackingAlgorithm` API contracts. | Public plugin boundary. |

---

### 2.2 Miscellaneous, Auxiliary & Historical Folders

| Directory / File | Governance Status | Disposition & Dependency Proof |
| :--- | :--- | :--- |
| `frontend/` (React/Vite) | **ACTIVE / SUPPORTING** | Contains optional Web Dashboard launched via `run_web.bat`. Not bundled in PyInstaller executable (desktop uses pure PySide6). Kept intact. |
| `audit/` | **LEGACY / RETAIN FOR TRACEABILITY** | Historical audit trail, system specification, and requirement traceability. Preserved per instruction ("Do not modify historical audit reports"). |
| `docs/` | **DOCUMENTATION ONLY** | User Manual, Traceability Matrix, Architecture Documentation. Updated in Phase 4. |
| `models/candidate_classifier/v001/` | **ACTIVE / REQUIRED** | Production 11-feature MLP weights (`model.json`) and metadata (`metadata.json`). Must be bundled in PyInstaller. |
| `datasets/` | **BENCHMARK / SUPPORTING** | Processed candidate datasets (`datasets/processed/candidate-v1/`). Retained for reproducibility. |
| `scenarios/` | **ACTIVE / REQUIRED** | Standard JSON scenario presets. Bundled in PyInstaller. |
| `scratch/` | **BENCHMARK ONLY** | Validation benchmark scripts (`test_r16_first_principles.py`, `test_adversarial_firewall.py`, etc.). Retained for proof generation. |
| `src/graphify-out/` | **DEAD / CONFIRMED UNUSED** | Misplaced duplicate graphify analysis output inside `src/`. Zero incoming python imports or tests depend on it. **Safe to remove** to prevent bundling 2.4 MB of stale JSON into package. |
| `.alignment-backup-local.diff` | **DEAD / CONFIRMED UNUSED** | 233 KB stale diff backup at repository root. Zero code references. **Safe to remove**. |
| `lr_model.json` | **ACTIVE / SUPPORTING** | Used by `AIClassifier` in `src/tracker/ai_classifier.py` and `test_ai_classifier.py`. Bundled in PyInstaller. |

---

## 3. Dependency Verification for Proposed Removals

### Proposed Removal 1: `src/graphify-out/`
- **Location:** `src/graphify-out/` (contains `.graphify_analysis.json`, `graph.json`, `manifest.json`, `cache/`)
- **Incoming Python Imports:** **0** (verified via global regex `import.*graphify` across `src/` and `src/tests/`).
- **Test Dependencies:** **0** (verified via `pytest src/tests/`).
- **Benchmark Dependencies:** **0** (not referenced in any benchmark script).
- **Packaging Dependencies:** Not listed in `lumitrack.spec`, but picked up unintentionally by recursive `src/` scans.
- **Verdict:** **SAFE TO REMOVE**. Eliminates 2.4 MB of redundant JSON inside the source tree. (Top-level `graphify-out/` at repository root is preserved).

### Proposed Removal 2: `.alignment-backup-local.diff`
- **Location:** `.alignment-backup-local.diff`
- **Incoming References:** **0** (stale patch file from prior session).
- **Verdict:** **SAFE TO REMOVE**.

### Components Deliberately Retained
- **`src/api/server.py`:** Retained because `src/tests/test_security_scenarios.py` and `src/tests/test_api_ai_scenario.py` depend directly on its route handlers to assert path-traversal security and response schemas.
- **`frontend/`:** Retained for optional browser-based demonstration via `run_web.bat`, but excluded from PyInstaller standalone desktop bundle.
- **`src/tracker/ai_classifier.py` and `lr_model.json`:** Retained because `src/tests/test_ai_classifier.py` verifies backward compatibility of alternative classifiers.
- **All 34 test files in `src/tests/`:** 100% retained.
