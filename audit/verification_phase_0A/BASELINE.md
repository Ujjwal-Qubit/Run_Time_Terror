# PHASE 0A: REPRODUCIBLE BASELINE AND ENVIRONMENT RECORD
**Project:** FSOC-VPAT (AI-Assisted Virtual Camera Tracking & Coarse Alignment Testbed)  
**SIH Problem Statement:** 26169 (ISRO / Department of Space)  
**Verification Phase:** Phase 0A — Independent Audit Validation & Reproducible Baseline  
**Date:** 2026-09-26  
**Auditor:** Independent Senior Software Auditor  

---

## 1. Git Repository State

| Parameter | Value | Notes |
| :--- | :--- | :--- |
| **Current Branch** | `main` | Tracking `origin/main` |
| **Branch Up-to-date** | Yes | Fully synchronized with remote |
| **HEAD Commit Hash** | `449523f669db6ecdd8aa6b5791c28c8d8b88fc7c` | Merge pull request #1 from Ujjwal-Qubit/frontend-navigation-target-lock |
| **HEAD Commit Date** | `2026-09-26 09:57:57 +0530` | Merged by Ujjwal Kaushik |
| **Previous Audit Commit Baseline** | `deca2d8` ~ `2ed36aa` | Audit was created at `2026-09-25T19:34:21Z` (approx `2026-09-26 01:04 IST`) |
| **Working Tree Status** | Clean (Protected) | Zero application files modified during Phase 0A |
| **Untracked Directories** | `audit/` | Contains original audit reports (5 files) and Phase 0A verification directory |
| **Uncommitted Submodule Status** | `.agentic-awesome-skills` | Submodule has untracked/modified content (preserved as-is, untouched) |

### Recent Commit Trajectory
```
* 449523f (HEAD -> main, origin/main) Merge pull request #1 from Ujjwal-Qubit/frontend-navigation-target-lock
|\  
| * 101befe Add collapsible navigation and simultaneous tracking views
|/  
* 2ed36aa updated structre
* 6e4d358 Updated backend
* deca2d8 docs: add comprehensive running commands, quickstart guide, and requirements.txt
* c08afbe fix(frontend): compact control panel and enable smooth scrolling for disturbances configuration
* 270a055 feat(frontend): implement modern React + Vite + Three.js web interface and FastAPI server adapter on F1
```

---

## 2. Execution Environment & Dependencies

| Component | Verified Version | Notes |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Enterprise (64-bit) | PowerShell 5.1 host shell |
| **Python Runtime** | `3.11.9` | CPython 64-bit |
| **Node.js Runtime** | `v24.14.0` | Node.js engine |
| **Package Manager (NPM)** | `11.19.0` | NPM CLI |
| **Git CLI** | `2.53.0.windows.2` | Git for Windows |
| **Pytest** | `9.1.1` | Automated test runner |
| **FastAPI** | `0.141.1` | REST/WebSocket framework |
| **Starlette** | `1.6.0` | Underlying ASGI framework |
| **Uvicorn** | `0.52.4` | ASGI server |
| **OpenCV (`opencv-python`)**| `4.14.0.94` | Computer vision & frame ingestion |
| **NumPy** | `2.4.6` | Numerical computing engine |
| **PySide6** | `6.11.2` | Qt 6 GUI framework |
| **Pydantic** | `2.10.6` | Data validation & schemas |
| **WebSockets** | `17.0.1` | Low-level WebSocket protocol |
| **ONNX Runtime** | `1.29.0` | ML inference engine |

---

## 3. Documented Setup and Execution Commands

| Workflow | Documented Command | Actual Execution Behavior |
| :--- | :--- | :--- |
| **Run Pytest Test Suite** | `python -m pytest` | Discovers `src/tests`, executes **445 tests**, passes in **21.31s**. |
| **Run CLI Headless Benchmark** | `python -m src.main --benchmark-matrix SMOKE` | Dispatches to `BenchmarkManager.run_benchmark_matrix`, writes JSON/CSV/MD reports. |
| **Run CLI AI Scenario** | `python -m src.main --ai-scenario "Prompt..."` | Dispatches to `BenchmarkManager.run_ai_scenario`, evaluates scenario. |
| **Run Desktop PySide6 GUI** | `python -m src.main --desktop` (or `run_lumitrack.bat`) | Launches PySide6 Qt GUI. |
| **Run Web Server Backend** | `python -m src.main --web --port 8000` (or `run_web.bat`) | Starts Uvicorn FastAPI server on `http://127.0.0.1:8000`. |
| **Run Web Frontend Dev Server**| `npm run dev` in `frontend/` | Starts Vite dev server on `http://localhost:5173`. |
| **Web Production Server** | `run_web.bat` | Fails to serve frontend UI because `frontend/dist` is not built (HTTP 404). |

---

## 4. Test Suite Execution Baseline

```
=================================== Test Run ===================================
Command: python -m pytest -q
Platform: Windows (CPython 3.11.9, pytest 9.1.1, pluggy 1.6.0)
Rootdir: E:\Newfolder\Project2O\Projects\SIH '26\external
Config: pytest.ini (testpaths = src/tests, pythonpath = .)

Result Summary:
........................................................................ [ 16%]
........................................................................ [ 32%]
........................................................................ [ 48%]
........................................................................ [ 64%]
........................................................................ [ 80%]
........................................................................ [ 97%]
.............                                                            [100%]
============================= 445 passed in 21.31s =============================
```

### Module Breakdown (445 Tests Total)
* `src.tests.test_ai_classifier`: 3
* `src.tests.test_aiml_runtime`: 11
* `src.tests.test_algorithm_api`: 7
* `src.tests.test_baseline_plugin`: 10
* `src.tests.test_benchmark_manager`: 3
* `src.tests.test_bm2_workflow`: 8
* `src.tests.test_centroid_estimator`: 33
* `src.tests.test_def01_def02_regression`: 8
* `src.tests.test_detection_engine`: 24
* `src.tests.test_evaluator_fix`: 3
* `src.tests.test_foundation`: 36
* `src.tests.test_frame_provider`: 17
* `src.tests.test_gui_lifecycle`: 8
* `src.tests.test_local_contrast`: 6
* `src.tests.test_metrics_engine`: 14
* `src.tests.test_multi_beacon`: 9
* `src.tests.test_noise_controls`: 5
* `src.tests.test_performance_and_hardening`: 4
* `src.tests.test_phase5_10_patch`: 4
* `src.tests.test_phase6_4_injection`: 12
* `src.tests.test_phase6_5_harness`: 9
* `src.tests.test_phase6_6_matrix`: 9
* `src.tests.test_phase6_7_ai_scenario`: 14
* `src.tests.test_phase6_8_sih_validation`: 59
* `src.tests.test_plugin_loader`: 20
* `src.tests.test_ptz_controller`: 36
* `src.tests.test_simulation`: 37
* `src.tests.test_single_run_report`: 5
* `src.tests.test_tracking_pipeline`: 31
* **TOTAL:** **445 tests** (0 failed, 0 skipped, 0 xfailed)

---

## 5. Benchmark Performance Baseline (Reproduced)

### Benchmark Run 1: BM1 Smoke (Headless CLI / Simulation Domain)
* **Configuration:** Subset `SMOKE` (3 scenarios: `matrix_01_linear_nominal`, `matrix_02_circular_nominal`, `matrix_09_atmos_fog`), Algorithm: `baseline_tracker`, Random Seed: `42`.
* **Total Frames Executed:** 150 frames (50 per scenario).
* **Execution Throughput:** **353.3 FPS** algorithm execution rate; **366.7 FPS** total benchmark throughput.
* **Tracking Error (Centroid RMSE against Rendered Centroid):** **0.000 px**.
* **Tracking Error (Centroid RMSE against Ideal Continuous Projection):** **0.927 px**.
* **Target Loss Rate:** **0.0%**.
* **Lock Retention (Post-Acquisition):** **80.0%** (2 frames initial acquisition delay).
* **Initial Acquisition Latency:** **0.067 s** (2 frames @ 30 Hz).

### Benchmark Run 2: Gaussian Noise Scenario (`SCENARIO_NOISE_GAUSSIAN`)
* **Configuration:** Atmospheric condition `CLEAR`, Gaussian noise $\sigma = 10.0\text{ px}$, Target shape `square` (10x10), Algorithm: `baseline_tracker`.
* **Execution Throughput:** **340.5 FPS**.
* **Tracking Error (Centroid RMSE):** **0.0598 px**.
* **Centroid Mean Error:** **0.0538 px**.
* **Centroid Max Error:** **0.0977 px**.
* **Target Loss Rate:** **0.0%**.
* **% Within 1.0 px:** **100.0%**.

---

## 6. Verification Isolation & Constraints Record

* **Working Tree Protection:** Strictly enforced. No source files, tests, configurations, or packages were edited, updated, or removed.
* **Read-Only Invocations:** All test and verification invocations utilized read-only or isolated temporary directories (`tempfile.TemporaryDirectory()`).
* **Artifact Directory Separation:** Phase 0A verification artifacts are strictly isolated in `audit/verification_phase_0A/`. Original audit artifacts in `audit/` remain 100% unaltered.
