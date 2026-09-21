# LumiTrack Fresh Architecture & Codebase Baseline

**Date:** 2026-09-20
**Scope:** Read-only forensic architecture analysis and Graphify baseline regeneration.

---

## 1. Repository Baseline
The filesystem was audited to establish the current clean baseline following the historical cleanup.

* **Total Files in `src/`:** 264
* **Source `.py` Files (`src/` excluding tests):** 84
* **Test `.py` Files (`src/tests/`):** 24
* **Active Documentation:** 4 files (`FINAL_ENGINEERING_REPORT.md`, `SIH_REQUIREMENT_TRACEABILITY_MATRIX.md`, `USER_AND_EVALUATOR_MANUAL.md`, `LumiTrack_v1.0_Technical_Report.pdf`)
* **Archived Documentation:** 8 files (moved to `docs/archive/`)
* **Generated Artifacts:** `.graphifyignore` was explicitly updated. `graphify-out/` regenerated.

## 2. Current Product Definition
LumiTrack is an **Algorithm Evaluation Platform**, not a standalone hardcoded tracker. The product allows algorithm developers to inject tracking algorithms as plugins, which are independently evaluated by the platform's Simulation and Evaluation harnesses under controlled scenarios. 

## 3. Current Architecture
The frozen architecture is strictly maintained:
1. **Plugin API:** Decouples tracking logic from platform infrastructure.
2. **Simulation System:** `SceneManager`, `TargetManager`, `DisturbanceEngine`, and `CameraModel` manage the controlled environment.
3. **Evaluation Harness:** Controls BM1 (simulation) and BM2 (MP4) execution, isolating metrics from the algorithm.
4. **GUI/UX:** Provides an evaluation workflow with `ControlPanel`, `TelemetryPanel`, and a QPainter-based `View3DWidget`.

## 4. Data Flow (Critical Firewall)
The ground-truth firewall is intact and robustly enforced.
* **Simulator → FrameProvider → Algorithm:** The tracking algorithm receives *only* observable pixel data via the `FramePacket` public contract (image, dimensions, frame number, timestamp).
* **Simulator → GroundTruthProvider → MetricsEngine:** True target positions, platform state, and disturbances bypass the algorithm entirely and flow directly to the `MetricsEngine`.
* **Finding:** No instances of ground truth or simulation state leakage to the tracking algorithm were found.

## 5. Plugin/API Architecture
The algorithm integration follows the strict `ITrackingAlgorithm` interface. The `PluginLoader` discovers algorithms dynamically using a `manifest.json` file. 
* Current plugin: `baseline_tracker`.

## 6. Algorithm Pipeline
The official `baseline_tracker` encapsulates the following sequential 5-stage pipeline:
1. `P0ThresholdDetector`
2. `AIClassifier` (with `CandidateIdentifier` fallback)
3. `IntensityWeightedCentroidEstimator`
4. `ConstantVelocityKalmanTracker`
5. `TrackingStateManager`
* **Finding:** The baseline algorithm implements a proportional PTZ control (deadband) and Kalman estimation. There is NO implementation of PI, PID, or KCF correlation tracking in the active codebase.

## 7. Evaluation Architecture
* **BM1 (Simulator):** Executes deterministic, seed-based simulation for 19 standard scenarios.
* **BM2 (MP4):** Consumes MP4 files frame-by-frame. Respects Rule 6: If an optional reference CSV is absent, accuracy metrics are correctly suppressed rather than fabricated. 

## 8. GUI Architecture
The GUI (`src/app/gui/`) successfully coordinates the product pivot workflows:
* Dynamic algorithm selection.
* Run-time switching between BM1 and BM2.
* Reporting and AI Scenario generator integration.
* **3D Visualizer:** Driven entirely by `VisualizationState` broadcast events, keeping it fully decoupled from backend logic.

## 9. AI Scenario Architecture
The AI integration strictly generates structured scenario definitions:
* **Workflow:** `AIInterpretationEngine` → `CandidateScenarioSpec` → `ScenarioSpecificationValidator` → `DeterministicTrajectoryGenerator`.
* **Validation:** The AI is not an authoritative controller. It produces JSON that must pass bounds and capability validation.
* **Shapes:** The AI generator supports generating expanded geometric shapes (SQUARE, PENTAGON, ZIGZAG, SPIRAL, SINUSOIDAL) which map to deterministically evaluated trajectories.

## 10. Packaging
PyInstaller configuration (`lumitrack.spec`) and CLI launchers (`run_lumitrack.bat`) are intact. CLI validation modes like `LumiTrack.exe --validate` successfully execute integration smoke paths.

## 11. Test Baseline
The full canonical test suite was executed via `pytest -v`.
* **Expected from Documentation:** 398 passed tests.
* **Actual Result:** **403 passed in 36.26s (0 failures)**.

## 12. Graphify Baseline
The graph was entirely regenerated from the current clean repository, aggressively ignoring archives, caches, and legacy outputs.
* **Nodes:** 1833
* **Edges:** 5576
* **Communities:** 113
* **Validation:** Stale and deleted files have been completely purged from the graph.

## 13. Graph Architecture Findings
* **Expected:** The 19-module boundaries are visible and architecturally consistent.
* **Expected:** Strict separation between the `plugins/` community and `evaluation/` metrics gathering.

## 14. Stale Documentation Findings
Searches across the active repository revealed:
* **`FINAL_ENGINEERING_REPORT.md`** claims the test suite has **398** passing tests, but the actual suite possesses **403**. 
* **PI / PID / KCF References:** Erroneous references to these algorithms were only found in `docs/archive/` documents and have been successfully purged from the active architecture documentation.

## 15. Git State
The repository has uncommitted changes representing the product pivot and recent manual file manipulation:
* **Modified:** 31 files (including scenarios, core `src/`, `pytest.ini`, `.graphifyignore`).
* **Deleted:** 9 files (mostly smoke scripts and active root architectural docs moved to `archive/`).
* **Untracked:** 29 files (new product GUI panels, test files, harness mechanisms, plugin structures).

## 16. Open Findings
| Severity | Finding |
| :--- | :--- |
| **LOW** | Documentation Stale: `FINAL_ENGINEERING_REPORT.md` underreports passing tests (398 vs 403). |
| **INFO** | Git Working Tree: The repository has 31 modified, 9 deleted, and 29 untracked files awaiting commit. |

---
*No production code, tests, dependencies, or GUI logic were modified during this baseline analysis.*
