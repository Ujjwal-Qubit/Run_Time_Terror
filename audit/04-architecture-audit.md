# 04 — Architecture Audit From First Principles

**Date:** 2026-09-28  
**Discipline:** Principal Systems Architect (`architect-review`) & Technical Debt Specialist (`brooks-debt`)  
**Scope:** Evaluation of LumiTrack Architecture v1.2 against First-Principles Requirements

---

## 1. System Boundaries & Coupling Analysis (Graphify Insights)

Graphify knowledge graph analysis revealed key structural metrics:
- **Total Nodes:** 2,697 | **Total Edges:** 6,129 | **Communities:** 148
- **God Node 1:** `AppController` (208 edges, betweenness centrality 0.205)
- **God Node 2:** `BenchmarkManager` (104 edges)
- **God Node 3:** `ConfigManager` (88 edges)
- **God Node 4:** `TrackingState` (83 edges)
- **God Node 5:** `DisturbanceEngine` (80 edges)
- **God Node 6:** `FramePacket` (79 edges)

```
                                  [AppController] (God Node: 208 Edges)
                                   /       |       \
                                  /        |        \
        [Simulation Subsystem] <─+         |         +─> [Evaluation Subsystem]
        ├── SceneManager                   |             ├── BenchmarkManager
        ├── TargetManager                  |             ├── BenchmarkMatrixRunner
        ├── CameraModel                    |             └── EvaluationHarness
        └── DisturbanceEngine              |
                                           |
                                [FrameProvider Firewall]
                                           |
                                [BaselineTracker (Plugin)]
                                ├── P0ThresholdDetector
                                ├── IntensityWeightedCentroidEstimator
                                ├── AIClassifier (Heuristic)
                                ├── ConstantVelocityKalmanTracker
                                └── TrackingStateManager
                                           |
                                [PTZ Gimbal Controller]
```

### Architectural Strengths:
1. **Uncompromising Ground-Truth Firewall:** The `FramePacket` public contract cleanly separates the simulation domain from the tracking domain. Algorithms consume strictly 2D NumPy arrays without accessing ground-truth coordinates or internal simulator states.
2. **Deterministic Seed Control:** All pseudo-random number generators (PRNGs) for kinematics, jitter, and noise derive from a master seed, enabling 100% reproducible execution.
3. **Headless Execution Performance:** In batch evaluation mode, the Python pipeline achieves $>400\text{ FPS}$, vastly exceeding the $20\text{ FPS}$ SIH requirement.
4. **PySide6 Desktop Application:** The native Qt GUI (`src/app/gui/`) directly interfaces with the backend in-process, providing high-fps rendering without network serialization.

---

## 2. Architectural Weaknesses & Over-Engineering

### 1. The Dual-Frontend & Client-Server Split
- **Current State:** The repository contains TWO complete, independent user interfaces:
  - Native Qt GUI in `src/app/gui/` (`main_window.py`, `config_panel.py`, `control_panel.py`, `telemetry_panel.py`, `video_widget.py`, `view_3d.py`).
  - Web UI in `frontend/` (React 18, Vite, Three.js, Lucide icons, Tailwind CSS).
  - FastAPI server in `src/api/server.py` exposing REST endpoints and WebSocket frame streaming.
- **Architectural Cost:**
  - Video frames must be encoded to JPEG/PNG, base64-encoded, sent over WebSockets, and decoded in the browser at 30 Hz.
  - Requires maintaining two separate tech stacks (Python 3.11 + Node.js 18).
  - Packaging a standalone `.exe` (Deliverable 1) requires bundling Python, Chromium/Electron or forcing evaluators to run batch scripts and manage port conflicts.
- **Verdict:** **Massive Over-Engineering.** The web frontend was built for visual appeal rather than functional requirements. A single, polished native Qt desktop application completely satisfies the deliverable.

### 2. The Plugin System for a Single Plugin
- **Current State:** `PluginLoader` discovers algorithms by parsing directories, reading `manifest.json` files, validating class types, and checking AST contracts.
- **Reality:** There is only **one** plugin in the entire repository: `baseline_tracker`.
- **Verdict:** **Premature Abstraction.** A simple abstract base class (`BaseTracker`) or standard strategy interface is all that is required. The dynamic file-system discovery and manifest validation adds scaffolding without real utility.

### 3. God-Class Orchestrator (`AppController`)
- **Current State:** `AppController` coordinates simulation stepping, algorithm execution, PTZ control, metrics calculation, Qt signal bridging, worker thread lifecycle, logging, and scenario loading.
- **Risk:** Modifying evaluation code or adding search patterns directly touches the simulation loop, creating high blast radius for bugs.
- **Remedy:** Decompose into:
  - `SimulationHost` (manages world state and camera pose).
  - `TrackingRunner` (manages algorithm execution).
  - `EvaluationHost` (coordinates headless batch runs).

### 4. Controller Gating Flaw (Zero Search Pattern)
- **Current State:** `PTZController.compute()` checks:
  ```python
  if tracking_state in (TrackingState.SEARCHING, TrackingState.ACQUIRING, TrackingState.LOST):
      return PTZCommand(valid=False, delta_pan=0.0, delta_tilt=0.0...)
  ```
- **Consequence:** The control layer is completely decoupled from the search/acquisition requirement. When the beacon is lost or not yet acquired, the gimbal stops.
- **Remedy:** Implement an active Search Mode (Archimedean spiral / Lissajous scan) driven by the state machine.
