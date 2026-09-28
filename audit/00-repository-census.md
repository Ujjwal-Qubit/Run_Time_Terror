# 00 — Repository Artifact Census

**Date:** 2026-09-28  
**Scope:** SIH 26169 — Coarse Alignment of Mobile FSOC Terminals  
**Investigation Mode:** Zero-Assumption Forensic Audit (Read-Only)

---

## 1. Directory & File Family Census

| Directory / File Family | Purpose & Responsibilities | Key Technologies | Implementation Status | Problem Statement Relevance | Risk / Architectural Finding |
|---|---|---|---|---|---|
| `src/simulation/` | 2D environment simulation, target kinematic model, camera viewport extraction, and disturbance generation | Python, NumPy, OpenCV | Implemented & Working | High (Mandatory Core) | Flat 2D pixel-space canvas (`2000×2000`). Target always initialized at `(1000, 1000)` or `spawn_range = 150px`, guaranteeing initial FOV presence. |
| `src/tracker/` | Classical computer vision tracking sub-modules (detection, centroiding, candidate scoring, state machine, Kalman filter) | Python, NumPy, OpenCV | Implemented & Working | High (Mandatory Core) | Pure classical heuristics and Kalman filter. Contains `ai_classifier.py`, a 4-feature Logistic Regression trained on 400 uniform synthetic numbers. |
| `src/plugins/algorithms/baseline_tracker/` | Packaged algorithm plugin implementing `ITrackingAlgorithm` public contract | Python, NumPy | Implemented & Working | High (Mandatory Core) | Encapsulates `src/tracker/` behind ground-truth firewall. Has AI features (`_aiml_candidate_enabled`, `_aiml_temporal_enabled`) hard-disabled to `False` by default. |
| `src/control/` | Proportional-Deadband PTZ Gimbal controller (`ptz_controller.py`) | Python, NumPy | Implemented & Working | High (Mandatory Core) | **Fatal Flaw:** Zero actuation commanded when in `SEARCHING`, `ACQUIRING`, or `LOST` states. Zero acquisition search pattern exists. |
| `src/frame/` | Ground-truth isolation contracts (`FramePacket`, `IFrameProvider`, `SimulationFrameProvider`, `MP4FrameProvider`) | Python, dataclasses | Implemented & Working | High (Core Boundary) | Robust architectural firewall. Completely isolates tracking algorithms from ground truth. |
| `src/metrics/` | Objective metrics engine (`metrics_engine.py`, `logging_engine.py`) calculating RMSE, latency, loss rate, acquisition time | Python, NumPy | Implemented & Working | High (Mandatory Core) | Calculates metrics objectively. However, acquisition time is trivially small (`~0.033s`) because targets start inside FOV. |
| `src/evaluation/` | Benchmark harnesses (BM1 simulation matrix, BM2 MP4 ingestion, AI scenario generator) | Python, NumPy, JSON | Implemented & Working | High (Evaluation) | BM1 has 19 static scenarios. BM2 suppresses error metrics if reference CSV is omitted. `ai_scenario.py` uses regex substring matching. |
| `src/app/` | `AppController` orchestrator, `SimulationWorkerThread`, `VisualizationStateManager` | Python, threading, queue | Implemented & Working | High (Orchestrator) | `AppController` is an architectural God Node (208 graph edges). Concurrently coordinates simulation, GUI events, and benchmarks. |
| `src/app/gui/` | Desktop Standalone GUI built with PySide6 (Qt) | Python, PySide6 | Implemented & Working | High (Mandatory Deliverable) | Clean, functional Qt GUI with 2D HUD and software QPainter 3D wireframe orbit view. Fully satisfies standalone executable deliverable. |
| `frontend/` | Web Dashboard and evaluation cockpit | TypeScript, React 18, Vite, Three.js | Implemented & Working | Questionable / Redundant | Complete second UI. Duplicates PySide6 functionality. Relies on custom FastAPI WebSocket stream. Requires separate node build. |
| `src/api/` | FastAPI REST & WebSocket server (`server.py`) | Python, FastAPI, WebSockets | Implemented & Working | Questionable / Redundant | Exists exclusively to serve `frontend/`. Introduces network latency, JSON serialization overhead, and web security attack surface. |
| `src/aiml/` | Secondary ML components (Candidate Classifier, Temporal Predictor MLP) | Python, NumPy | Implemented but Disabled | Low / Questionable | Trained on 30 examples (`examples: 30.0` in `model.json`). Turned off by default in `baseline_tracker.py`. |
| `models/` | Model artifacts (`model.json`, `feature_schema.json`) | JSON | Implemented | Low | Minimal JSON weight matrices for handwritten NumPy forward passes. |
| `scenarios/` | JSON scenario definitions for BM1 evaluation suite | JSON | Implemented | Medium | 19 scenarios covering motion, disturbances, and noise. All center the target at `(1000, 1000)`. |
| `src/tests/` | Pytest test suite (454 tests across 24 test files) | Python, pytest | 454 Passed (100%) | Medium (Verification) | High pass rate hides weak assertions (`assert hasattr`, `assert ptz is not None`, relaxed loss rate `< 30%`). |

---

## 2. Reconstructed System Structural Map

```text
Problem: SIH 26169 (Coarse Alignment of Mobile FSOC Terminals)
  ↓
Users: Space Communication Engineers, Algorithm Researchers, SIH Evaluators
  ↓
User Goals: 
  1. Autonomously locate, acquire, and center a moving optical beacon
  2. Maintain beam pointing lock under atmospheric, platform, and sensor disturbances
  3. Validate performance on synthetic scenarios (BM1) and external real video recordings (BM2)
  ↓
Requirements (PS 26169 Table Rows 1–25):
  - Screen ≥ 2000×2000 px, Viewport 640×480 px, FOV 4°×3°, 30 Hz
  - Target beacon: 5–20 px, straight/circular/figure-8/random, speed 50 px/s
  - PTZ: max slew 5–10°/s, update ≥ 20 Hz
  - Metrics: Acq time ≤ 2s, Reacq time ≤ 1s, RMSE ≤ 10 px, Loss < 5%, FPS ≥ 20
  - Disturbances: Gaussian, Poisson, S&P noise; Haze/Fog/Rain/Low light; Jitter & platform motion ±20 px
  ↓
Capabilities:
  [Simulation Engine] [Firewall Barrier] [Tracking Pipeline] [Gimbal Control] [Metrics Engine] [Dual Frontends]
  ↓
Subsystems (19-Module Architecture v1.2):
  - Modules 4–7: Simulation (Scene, Target, Camera, Disturbance)
  - Module 8: FrameProvider Boundary
  - Modules 9–13: Tracking Pipeline (Detection, Centroiding, Scoring, Kalman, State Machine)
  - Module 14: PTZ Controller
  - Modules 15, 17: Metrics & Benchmark Manager
  - Modules 1, 16, 18, 19: AppController, Visualization, Plugins, 3D View
  - Web Subsystem: FastAPI (`server.py`) + React/Vite/Three.js (`frontend/`)
  ↓
Implementation:
  - 84 Python source files in `src/`
  - 24 Pytest files in `src/tests/`
  - React/TypeScript frontend in `frontend/`
  ↓
Data / Models / Algorithms:
  - Intensity-Weighted Centroiding (IWC) + 3×3 Median + Box Filter
  - Constant-Velocity Kalman Filter (CV-KF) with Innovation Gating
  - Logistic Regression (4-dim & 11-dim) + 2-layer MLP (Disabled by default)
  ↓
Tests / Validation:
  - 454 passing tests in 35.5s
  - Automated BM1 (19 scenarios) and BM2 (MP4 video) batch runners
  ↓
Deployment:
  - Desktop Standalone: PyInstaller (`lumitrack.spec`, `run_lumitrack.bat`)
  - Web Server: `run_web.bat` (`python -m src.main --web`)
```
