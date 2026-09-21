# LumiTrack — AI-Assisted Virtual Camera Tracking & Evaluation Platform

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-green.svg)](https://doc.qt.io/qtforpython/)
[![Test Suite](https://img.shields.io/badge/tests-403%20passed%20%28100%25%29-brightgreen.svg)](https://pytest.org/)
[![SIH Problem Statement](https://img.shields.io/badge/SIH%20%2726-PS%2026169%20%2F%20PS--4-orange.svg)](https://sih.gov.in/)
[![Organization](https://img.shields.io/badge/Organization-ISRO%20%2F%20Dept%20of%20Space-blueviolet.svg)](https://www.isro.gov.in/)
[![Architecture](https://img.shields.io/badge/Architecture-v1.2%20Frozen%20Baseline-success.svg)](docs/FRESH_ARCHITECTURE_BASELINE.md)
[![Graph Analysis](https://img.shields.io/badge/Graphify-1836%20nodes%20%7C%2089%20communities-indigo.svg)](graphify-out/GRAPH_REPORT.md)

---

## 📌 Table of Contents

1. [Executive Summary & Mission](#-executive-summary--mission)
2. [SIH Problem Statement 26169 Alignment](#-sih-problem-statement-26169-alignment)
3. [System Architecture & Data Flow](#-system-architecture--data-flow)
4. [Baseline Tracking Algorithm Pipeline](#-baseline-tracking-algorithm-pipeline)
5. [Benchmark Modes: BM1 vs. BM2](#-benchmark-modes-bm1-vs-bm2)
6. [AI-Assisted Scenario Generation](#-ai-assisted-scenario-generation)
7. [Graphical User Interface & 3D Visualization](#-graphical-user-interface--3d-visualization)
8. [Installation & Quickstart](#-installation--quickstart)
9. [Command Line Interface (CLI) Reference](#-command-line-interface-cli-reference)
10. [Algorithm Plugin Development Guide](#-algorithm-plugin-development-guide)
11. [Verification, Testing & Robustness](#-verification-testing--robustness)
12. [Repository Layout](#-repository-layout)
13. [Documentation Index](#-documentation-index)
14. [Scope & Operational Boundaries](#-scope--operational-boundaries)

---

## 🌟 Executive Summary & Mission

**LumiTrack** is a high-precision **Algorithm Evaluation Platform** and **Simulation Testbed** built for the autonomous coarse alignment of mobile **Free Space Optical Communication (FSOC)** terminals.

```
+---------------------------------------------------------------------------------------------------+
|                                      LUMITRACK PLATFORM                                           |
|                                                                                                   |
|  +---------------------------+       Observable       +----------------------------------------+  |
|  |     SIMULATION / MP4      |      FramePacket       |         TRACKING ALGORITHM             |  |
|  |  * 2000x2000 Scene Engine | ---------------------> |        (Unit Under Test - UUT)         |  |
|  |  * Kinematic Target Model |   (Strict Firewall)    |  * Adaptive P0 Detector                |  |
|  |  * Atmospheric Disturbance|                        |  * AI Clutter Classifier               |  |
|  |  * Sensor Noise & Jitter  |                        |  * Sub-pixel Intensity Centroiding     |  |
|  +---------------------------+                        |  * Kalman State Estimator & FSM        |  |
|               |                                       +----------------------------------------+  |
|   True Target | Ground Truth                                               | Subjective           |
|   Coordinates | (Firewalled)                                               | TrackingResult       |
|               v                                                            v                      |
|  +---------------------------------------------------------------------------------------------+  |
|  |                             PLATFORM CONTROLLER & METRICS HARNESS                           |  |
|  |  * Proportional-Deadband PTZ Gimbal Control                                                |  |
|  |  * Objective Metrics Engine (Centroid RMSE, Lock Retention, Acquisition Time, Latency, FPS)|  |
|  |  * Dual-Viewport Visualization (2D HUD Sensor View + 3D Geometric Orbital Viewport)        |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

### Why LumiTrack Exists

Free Space Optical Communication provides gigabit-to-terabit data transmission across satellites, UAVs, and maritime vessels without radio-frequency licensing or electromagnetic interference. However, transmitting data over divergence-limited optical beams requires sub-milliradian pointing accuracy. Pointing, Acquisition, and Tracking (PAT) operates in two distinct stages:

1. **Coarse Alignment:** Locating and centering the remote optical beacon within the sensor Field-of-View (FOV) using a motorized Pan-Tilt-Zoom (PTZ) gimbal mount under severe disturbances.
2. **Fine Alignment:** Fast steering mirrors (FSM) or piezoelectric actuators refining sub-microradian alignment.

Evaluating coarse alignment algorithms on physical hardware requires expensive optical benches, gimbal hardware, vibration tables, and atmospheric test chambers. **LumiTrack eliminates this hardware dependency** by providing:
- A deterministic, physics-informed virtual camera simulation testbed.
- A standardized **Plugin API (`ITrackingAlgorithm`)** that treats tracking algorithms as independent Units Under Test (UUT).
- A rigorous **Ground-Truth Firewall** ensuring evaluation metrics are completely isolated from algorithm internals.
- End-to-end benchmark automation for synthetic scenarios (Benchmark 1) and external video recordings (Benchmark 2).

---

## 🎯 SIH Problem Statement 26169 Alignment

LumiTrack is engineered in strict compliance with **Smart India Hackathon 2026 Problem Statement 26169 (PS-4)**, sponsored by the **Department of Space / Indian Space Research Organisation (ISRO)**.

### Specification & Compliance Matrix

| Parameter / Requirement | SIH Specification Limit | LumiTrack Platform Capability | Status |
|---|---|---|:---:|
| **Virtual Scene Dimensions** | $\ge 2000 \times 2000\text{ px}$ | $2000 \times 2000\text{ px}$ (Configurable world canvas) | ✅ **PASS** |
| **Virtual Camera Resolution** | $640 \times 480\text{ px}$ | $640 \times 480\text{ px}$ (Configurable viewport) | ✅ **PASS** |
| **Camera Field of View (FOV)** | $4.0^\circ \times 3.0^\circ$ | $4.0^\circ \times 3.0^\circ$ (Configurable angular projection) | ✅ **PASS** |
| **Camera Update Rate** | $\ge 30\text{ Hz}$ | $30\text{ Hz}$ base simulation clock | ✅ **PASS** |
| **Target Beacon Sizes** | $5 \times 5\text{ to } 20 \times 20\text{ px}$ | $5 \times 5$, $10 \times 10$, $20 \times 20\text{ px}$ supported | ✅ **PASS** |
| **Target Motion Profiles** | Straight Line, Circular, Figure-8, Random | Straight Line, Circular, Figure-8, Random, Spiral, Sinusoidal | ✅ **PASS** |
| **PTZ Gimbal Speeds** | Max $5^\circ/\text{s} - 10^\circ/\text{s}$ | Dynamic rate-limiting clamp ($5.0^\circ/\text{s}$ default) | ✅ **PASS** |
| **Acquisition Time** | $\le 2.0\text{ s}$ | Measured: **$0.000\text{ s} - 0.033\text{ s}$** (Instantaneous P0 lock) | ✅ **PASS** |
| **Reacquisition Time** | $\le 1.0\text{ s}$ | Measured: **$\le 0.067\text{ s}$** post-occlusion | ✅ **PASS** |
| **Tracking Error** | $\le 10.0\text{ px}$ | Measured Mean: **$0.000\text{ px} - 2.850\text{ px}$** across matrix | ✅ **PASS** |
| **Target Loss Rate** | $< 5.0\%$ | Measured: **$0.0\%$** across standard matrix | ✅ **PASS** |
| **Processing Throughput** | $\ge 20\text{ FPS}$ | Measured: **$638.9\text{ FPS}$** (Baseline Tracker Core) | ✅ **PASS** |
| **Sensor Noise Injection** | Gaussian, Poisson, Salt & Pepper | Additive Gaussian ($\sigma \le 20$), Poisson, S&P ($\le 10\%$) | ✅ **PASS** |
| **Atmospheric Disturbances** | Clear, Haze, Fog, Rain, Low Light | Contrast attenuation & ambient brightness offsets | ✅ **PASS** |
| **Mechanical Disturbances** | Jitter & Platform Drift ($\le \pm 20\text{ px}$) | High-frequency jitter & low-frequency sinusoidal drift | ✅ **PASS** |
| **Evaluation Modes** | Benchmark 1 & Benchmark 2 | BM1 (Simulation) & BM2 (MP4 + Reference CSV) | ✅ **PASS** |

---

## 🏛 System Architecture & Data Flow

LumiTrack follows a decoupled, 19-module architecture governed by the frozen **Architecture v1.2 specification**.

```
                                    +-----------------------+
                                    |     Configuration     |
                                    |     Manager (M2)      |
                                    +-----------------------+
                                                |
               +--------------------------------+-------------------------------+
               |                                                                |
               v                                                                v
+-----------------------------+                                  +-----------------------------+
|    SIMULATION SUBSYSTEM     |                                  |   VIDEO INGESTION (BM2)     |
| * SceneManager (M4)         |                                  | * MP4FrameProvider (M8)     |
| * TargetManager (M5)        |                                  | * GroundTruth = None        |
| * CameraModel (M6)          |                                  +-----------------------------+
| * DisturbanceEngine (M7)    |                                                 |
| * SimulationFrameProvider   |                                                 |
+-----------------------------+                                                 |
               |                                                                |
               +--------------------------------+-------------------------------+
                                                |
                                                v
                               +---------------------------------+
                               |    FrameProvider Firewall (M8)  |
                               +---------------------------------+
                                                |
                                                | FramePacket (Public Contract)
                                                v
                               +---------------------------------+
                               |   ITrackingAlgorithm (Plugin)   |
                               |  * P0ThresholdDetector (M9)     |
                               |  * IWCentroidEstimator (M10)    |
                               |  * CandidateIdentifier (M11)    |
                               |  * TemporalKalmanTracker (M12)  |
                               |  * TrackingStateManager (M13)   |
                               +---------------------------------+
                                                |
                                                | TrackingResult (Subjective)
                                                v
                               +---------------------------------+
                               |   Application Controller (M1)   |
                               +---------------------------------+
                                 /              |              \
                                /               |               \
                               v                v                v
                 +-------------------+  +---------------+  +--------------------+
                 |   PTZ Controller  |  | MetricsEngine |  | VisualizationEngine|
                 |     (M14/M15)     |  |     (M17)     |  |       (M18)        |
                 +-------------------+  +---------------+  +--------------------+
                           |                    |                    |
                           v                    v                    v
                   [Camera Actuation]   [LoggingEngine]    [2D Sensor Viewport]
                   (Bypassed in BM2)    [Markdown/JSON]    [3D Orbital Viewport]
```

### The Strict Ground-Truth Firewall

A foundational design invariant in LumiTrack is the **Ground-Truth Firewall**:
1. **Public Input Contract (`FramePacket`):** External tracking algorithms receive strictly observable pixel data (`numpy.ndarray`), image resolution, timestamp, and camera FOV.
2. **Public Output Contract (`TrackingResult`):** Algorithms return subjective tracking state, estimated centroid $(x, y)$, confidence $[0.0, 1.0]$, and tracking ROI.
3. **No Ground Truth Leakage:** True target positions $(x_{\text{world}}, y_{\text{world}})$, platform disturbances, and scene coordinates are passed directly from `GroundTruthProvider` to `MetricsEngine`. Algorithms have **zero access** to simulator state.
4. **Benchmark-2 Isolation:** When executing in MP4 mode (BM2), simulation models are not instantiated, and ground-truth metrics are only computed if an independent reference CSV is provided by the evaluator.

### Graphify Architectural Analysis

Static and dynamic topological graph analysis performed via `Graphify` establishes the following validated metrics:

* **Total Nodes:** 1,836
* **Total Edges:** 4,369
* **Discovered Communities:** 89
* **Import Cycles:** **0 (Zero circular dependencies)**
* **Top-10 God Nodes (Core Architectural Abstractions):**
  1. `AppController` (196 edges) — Central orchestrator & lifecycle supervisor.
  2. `BenchmarkManager` (70 edges) — Evaluation harness & batch coordinator.
  3. `ProportionalDeadbandPTZController` (69 edges) — Gimbal pointing control law.
  4. `TrackingState` (69 edges) — Standardized tracking lifecycle state machine.
  5. `PluginLoader` (60 edges) — Dynamic manifest discovery and algorithm loader.
  6. `IntensityWeightedCentroidEstimator` (60 edges) — Sub-pixel localization engine.
  7. `FramePacket` (59 edges) — Primary observable input contract.
  8. `P0ThresholdDetector` (59 edges) — Dynamic noise estimation and thresholding.
  9. `TrackResult` (56 edges) — Temporal filtering and velocity tracking contract.
  10. `CentroidResult` (55 edges) — Sub-pixel centroid estimation contract.

---

## 🔬 Baseline Tracking Algorithm Pipeline

The default plugin (`src/plugins/algorithms/baseline_tracker`) encapsulates the validated 5-stage optical tracking pipeline:

```
Raw FramePacket
      │
      ▼
[Stage 1: P0 Threshold Detector]
  ├── Dynamic 75th-percentile background noise estimation (sigma)
  └── Adaptive thresholding: T = mu_bg + k * sigma
      │
      ▼
[Stage 2: Candidate Identifier & AI Classifier]
  ├── Connected component labeling & bounding-box extraction
  └── 4D Logistic feature scoring: [peak_intensity, contrast, compactness, aspect_ratio]
      │
      ▼
[Stage 3: Intensity-Weighted Centroid Estimator]
  ├── Background-subtracted center-of-mass calculation:
  │     x_c = sum((I - B) * x) / sum(I - B),  y_c = sum((I - B) * y) / sum(I - B)
  └── Sub-pixel resolution (RMSE <= 0.03 px)
      │
      ▼
[Stage 4: Constant-Velocity Kalman Temporal Tracker]
  ├── 4D State vector: [x, y, v_x, v_y]^T
  ├── Euclidean innovation gating for clutter rejection
  └── Continuous velocity prediction across temporary dropouts
      │
      ▼
[Stage 5: Tracking State Manager]
  ├── Finite State Machine: SEARCHING -> ACQUIRING -> TRACKING -> REACQUIRING -> LOST
  └── Lock confirmation counters & hysteresis verification
```

### Platform PTZ Control Law

The platform owns a **Proportional Deadband PTZ Controller** (`ProportionalDeadbandPTZController`) that commands the virtual camera gimbal:
1. **Pixel Error:** Computes displacement from image center: $\Delta x = x_{\text{target}} - x_{\text{center}}$, $\Delta y = y_{\text{target}} - y_{\text{center}}$.
2. **Deadband Filter:** Suppresses micro-jitter if $\sqrt{\Delta x^2 + \Delta y^2} \le \text{deadband\_px}$.
3. **Angular Projection:** Converts pixel offsets to optical angles $(\theta_{\text{pan}}, \theta_{\text{tilt}})$ via `ProjectionModel`.
4. **Rate Clamping:** Clamps angular velocities to configured gimbal limits ($5^\circ/\text{s} - 10^\circ/\text{s}$).

---

## 📊 Benchmark Modes: BM1 vs. BM2

LumiTrack provides dedicated evaluation harnesses for both mandatory SIH benchmark workflows:

```
                                  EVALUATION HARNESS
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
         [Benchmark 1 (BM1)]                       [Benchmark 2 (BM2)]
      Closed-Loop Simulation                    Recorded MP4 Video Feed
  * 19 Standard Scenario Matrix             * PTZ Actuation Bypassed
  * Closed-loop PTZ Camera Control          * Evaluator Reference CSV Comparison
  * Live Ground Truth Comparison            * Rule 6 Metric Suppression if No CSV
  * Deterministic Random Seed               * Multi-video Batch Processing
```

### Benchmark 1 (BM1) — Closed-Loop Simulation
- **Mechanism:** The simulator drives target kinematics and disturbances, and the PTZ controller actively repositions the camera viewport to track the beacon.
- **Scenario Subsets:**
  - `SMOKE` (3 scenarios): Rapid sanity check (Linear nominal, Circular nominal, Dense fog).
  - `CORE` (6 scenarios): Primary SIH validation scenarios across fundamental motion patterns.
  - `DISTURBANCE` (8 scenarios): Systematic stress sweep over noise, atmospheric attenuation, and jitter.
  - `FULL` (19 scenarios): Exhaustive benchmark matrix covering all operational envelopes.

### Benchmark 2 (BM2) — Evaluator Video Processing
- **Mechanism:** Ingests recorded `.mp4` video files frame-by-frame. The PTZ camera control loop is automatically bypassed to evaluate tracking on fixed footage.
- **Reference Comparator:** Evaluates against external ground-truth CSV files (`frame,true_x,true_y` or `frame,x,y`).
- **Rule 6 Ground-Truth Firewall Compliance:** If an external reference CSV is not provided, accuracy metrics (e.g., Centroid RMSE) are **suppressed** rather than fabricated from assumptions.

---

## 🤖 AI-Assisted Scenario Generation

LumiTrack includes an intelligent **Natural Language Scenario Generation Subsystem** that translates human descriptions into validated, deterministic physical test scenarios.

```
"Fast target in heavy fog moving in a spiral at 75 px/s"
                          │
                          ▼
             [AI Interpretation Engine]
             Extracts kinematic & environmental parameters
                          │
                          ▼
            [Candidate Scenario Specification]
                          │
                          ▼
          [Scenario Specification Validator]
          Enforces boundary constraints:
          - Speed: 5 - 150 px/s
          - Coordinates: within 2000x2000 world canvas
          - Noise & atmospheric validity
                 │
                 ├── [REJECT] -> Clear error diagnostics
                 └── [ACCEPT]
                          │
                          ▼
       [Deterministic Trajectory Generator]
       Produces mathematical trajectory from seed
                          │
                          ▼
             [Tagged Scenario JSON]
             (is_ai_generated = True)
                          │
                          ▼
             [Evaluation Execution]
```

### Supported Trajectory Geometries
- `STRAIGHT_LINE` — Constant velocity linear crossing.
- `CIRCULAR` — Orbital trajectory with configurable center and radius.
- `FIGURE_8` — Dual-lobe lemniscate trajectory testing continuous acceleration reversals.
- `RANDOM` — Stochastic continuous random walk.
- `SPIRAL` — Archimedean expanding/contracting spiral trajectory.
- `SINUSOIDAL` — Transverse wave trajectory testing harmonic tracking.

---

## 🖥 Graphical User Interface & 3D Visualization

LumiTrack features a dark-themed UI built in **PySide6 (Qt6)**.

```
+---------------------------------------------------------------------------------------------------+
|  LumiTrack v1.0 — FSOC Virtual Camera Tracking System                                    [-][x]   |
+-----------------------+---------------------------------------------------+-----------------------+
|  CONTROL PANEL        |  CENTRAL VIEWPORT (Tabbed 2D / 3D)                |  CONFIGURATION TABS   |
|                       |                                                   |                       |
|  Algorithm:           |  +---------------------------------------------+  |  [Camera]             |
|  [ baseline_tracker ] |  | 2D SENSOR VIEW                              |  |  Resolution: 640x480  |
|                       |  |                                             |  |  FOV: 4.0 x 3.0 deg   |
|  Mode:                |  |       [+] Centroid (Red Crosshair)          |  |                       |
|  (o) Simulation (BM1) |  |       [ ] Adaptive ROI (Cyan Box)           |  |  [Target]             |
|  ( ) Video MP4 (BM2)  |  |       --- Aiming Reticle (White)            |  |  Pattern: CIRCULAR    |
|                       |  |                                             |  |  Speed: 50.0 px/s     |
|  Scenario:            |  |   HUD: Frame 120 | 30.0 FPS | State: TRACK  |  |  Size: 10x10 px       |
|  [ scenario_2_circ. ] |  +---------------------------------------------+  |                       |
|                       |  | 3D GEOMETRIC TERMINAL VIEW                  |  |  [Disturbances]       |
|  [ > Start ] [ || ]   |  |   * Terminal Pedestal & Gimbal Frustum      |  |  Atmosphere: HAZE     |
|  [ [] Stop ] [ Rst ]  |  |   * Real-time Optical Axis Ray & Beam       |  |  Noise: GAUSSIAN      |
|                       |  |   * Beacon Trajectory Breadcrumbs           |  |  Jitter: 3.0 px       |
|  [ Run Batch Tests ]  |  |   * Interactive 3D Orbit, Pan, and Zoom     |  |  Platform: LINEAR     |
+-----------------------+---------------------------------------------------+-----------------------+
|  TELEMETRY HUD: Frame: 120 | State: TRACKING | Status: LOCKED (Green) | Error: 1.24 px | FPS: 30.0|
+---------------------------------------------------------------------------------------------------+
```

### Key UI Capabilities
1. **Dynamic Algorithm Switching:** Select and hot-reload any discovered tracking plugin from the GUI dropdown without restarting.
2. **2D Sensor HUD Viewport:** Displays real-time camera feed with color-coded overlays (Cyan bounding box, Red sub-pixel centroid, White boresight crosshair, Green ground-truth marker).
3. **3D Geometric Scene Viewport (`View3DWidget`):**
   - High-performance **QPainter-based 3D projection** (zero OpenGL/hardware driver dependency).
   - Renders 3D coordinate ground grid, optical terminal pedestal, camera FOV viewing frustum oriented with live pan/tilt gimbal angles, optical line-of-sight laser beam, and dynamic target trajectory breadcrumb trails.
   - Interactive mouse controls: **Left-click drag** (Orbit view), **Right-click drag** (Pan), **Scroll wheel** (Zoom).
4. **Real-Time Telemetry Bar:** Live telemetry updates for frame index, state machine status, tracking error ($\text{px}$), sub-pixel centroid coordinates $(x, y)$, pan/tilt angles ($^\circ$), and processing FPS.

---

## 🚀 Installation & Quickstart

### Prerequisites
- **Operating System:** Windows 10/11, Linux, or macOS.
- **Python:** Python `3.10`, `3.11`, or `3.12` (Python `3.11` recommended).

### Option A: Standalone Windows Executable (Zero-Install)
LumiTrack is bundled as a standalone Windows executable requiring no Python environment:

```powershell
# Run the interactive GUI:
.\dist\LumiTrack\LumiTrack.exe --gui

# Or double-click the root batch script:
.\run_lumitrack.bat
```

### Option B: Running from Source

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Ujjwal-Qubit/Run_Time_Error.git
   cd Run_Time_Error
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   # Windows PowerShell:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install PySide6 numpy opencv-python pytest
   ```

4. **Validate system foundation:**
   ```bash
   python -m src.main --validate
   ```

5. **Launch the Graphical User Interface:**
   ```bash
   python -m src.main --gui
   ```

---

## 💻 Command Line Interface (CLI) Reference

LumiTrack provides a unified CLI entry point via `python -m src.main` (or `LumiTrack.exe`).

### Complete Argument Reference

| Flag | Type | Default | Description |
|---|---|---|---|
| `--gui` | Flag | `False` | Launches the interactive PySide6 graphical user interface. |
| `--validate` | Flag | `False` | Executes foundation contracts and configuration integrity check. |
| `--scenario <name>` | String | `None` | Loads a specific scenario JSON from the `scenarios/` directory. |
| `--mp4 <path>` | String | `None` | Runs Benchmark 2 on an external MP4 video file with PTZ bypass. |
| `--reference-csv <path>` | String | `None` | External evaluator reference CSV for BM2 ground-truth comparison. |
| `--algorithm <name>` | String | `baseline_tracker` | Target tracking algorithm plugin under test. |
| `--matrix <SUBSET>` | Choice | `None` | Executes a standard benchmark matrix subset (`SMOKE`, `CORE`, `DISTURBANCE`, `FULL`). |
| `--ai-scenario "<prompt>"` | String | `None` | Interprets natural language prompt, generates scenario, and evaluates algorithm. |
| `--eval-scenarios <dir>` | String | `None` | Batch evaluates all JSON scenarios in a directory. |
| `--eval-mp4s <dir>` | String | `None` | Batch evaluates all MP4 video files in a directory. |
| `--config <path>` | String | `None` | Path to a custom system JSON configuration file. |
| `--output-dir <dir>` | String | `output` | Destination directory for reports, summaries, and telemetry CSVs. |
| `--plugins-dir <dir>` | String | `src/plugins/algorithms` | Custom root directory for external algorithm plugins. |
| `--seed <int>` | Integer | `42` | Deterministic random seed for simulation reproducibility. |
| `--max-frames <int>` | Integer | `None` | Maximum frames to process per scenario. |

### Practical CLI Examples

#### 1. Execute Core Benchmark Matrix
```bash
python -m src.main --matrix CORE --algorithm baseline_tracker --output-dir output
```

#### 2. Evaluate External Video with Reference Ground Truth (BM2)
```bash
python -m src.main --mp4 tests/sample_video.mp4 --reference-csv tests/sample_ref.csv
```

#### 3. AI-Assisted Natural Language Scenario Generation
```bash
python -m src.main --ai-scenario "High-speed optical target moving in a spiral under dense fog with jitter" --algorithm baseline_tracker
```

#### 4. Batch Evaluate All Scenarios
```bash
python -m src.main --eval-scenarios scenarios --output-dir output/batch_eval
```

---

## 🧩 Algorithm Plugin Development Guide

LumiTrack uses a manifest-driven plugin architecture. Anyone can develop and evaluate custom tracking algorithms in 3 steps:

### Step 1: Create Plugin Directory Structure
Create a new directory inside `src/plugins/algorithms/` (e.g. `my_custom_tracker/`):
```
src/plugins/algorithms/my_custom_tracker/
├── manifest.json
└── my_tracker.py
```

### Step 2: Define `manifest.json`
```json
{
  "name": "my_custom_tracker",
  "version": "1.0.0",
  "api_version": "v1",
  "entry_point": "my_tracker:MyCustomTracker",
  "description": "Deep Learning / Advanced Correlation Filter FSOC Tracker",
  "author": "Research Team",
  "dependencies": ["numpy", "opencv-python"]
}
```

### Step 3: Implement `ITrackingAlgorithm`
In `my_tracker.py`, inherit from `src.api.v1.ITrackingAlgorithm`:

```python
from typing import Any, Dict
import numpy as np
from src.api.v1.algorithm import ITrackingAlgorithm
from src.api.v1.contracts import FramePacket, TrackingResult

class MyCustomTracker(ITrackingAlgorithm):
    """Custom tracking algorithm implementation."""

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Called once before scenario execution starts."""
        self.frame_count = 0
        return True

    def process_frame(self, frame_packet: FramePacket) -> TrackingResult:
        """
        The only per-frame execution entry point.
        Receives ONLY observable sensor data via FramePacket.
        """
        image = frame_packet.image  # 2D numpy array (grayscale uint8)
        h, w = frame_packet.resolution

        # Custom detection logic (e.g. brightest spot):
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(image)
        cx, cy = float(max_loc[0]), float(max_loc[1])
        is_tracking = max_val > 50

        return TrackingResult(
            algorithm_is_tracking=is_tracking,
            centroid_x=cx if is_tracking else None,
            centroid_y=cy if is_tracking else None,
            confidence=float(max_val / 255.0),
            roi=(max(0, int(cx - 20)), max(0, int(cy - 20)), 40, 40) if is_tracking else None
        )

    def reset(self) -> None:
        """Clears all internal temporal state, buffers, and memory."""
        self.frame_count = 0
```

### Step 4: Run and Benchmark Your Algorithm
Your plugin will be discovered automatically and appear in the GUI dropdown and CLI:
```bash
python -m src.main --matrix CORE --algorithm my_custom_tracker
```

---

## 🧪 Verification, Testing & Robustness

### Automated Regression Suite

LumiTrack includes a comprehensive automated test suite spanning 24 test files:

```bash
# Run full test suite:
pytest -v
```

**Results:**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\Newfolder\Project2O\Projects\SIH '26\external
configfile: pytest.ini
testpaths: src/tests
collected 403 items

src\tests\test_ai_classifier.py ...                                      [  0%]
src\tests\test_algorithm_api.py .......                                  [  2%]
src\tests\test_baseline_plugin.py ..........                             [  4%]
src\tests\test_benchmark_manager.py ...                                  [  5%]
src\tests\test_bm2_workflow.py ........                                  [  7%]
src\tests\test_centroid_estimator.py .................................   [ 15%]
src\tests\test_def01_def02_regression.py ........                        [ 17%]
src\tests\test_detection_engine.py ........................              [ 23%]
src\tests\test_foundation.py ....................................        [ 32%]
src\tests\test_frame_provider.py .................                       [ 36%]
src\tests\test_gui_lifecycle.py ......                                   [ 38%]
src\tests\test_metrics_engine.py ..............                          [ 41%]
src\tests\test_performance_and_hardening.py ....                         [ 42%]
src\tests\test_phase5_10_patch.py ....                                   [ 43%]
src\tests\test_phase6_4_injection.py ............                        [ 46%]
src\tests\test_phase6_5_harness.py .........                             [ 49%]
src\tests\test_phase6_6_matrix.py .........                              [ 51%]
src\tests\test_phase6_7_ai_scenario.py ..............                    [ 54%]
src\tests\test_phase6_8_sih_validation.py .............................. [ 62%]
.............................                                            [ 69%]
src\tests\test_plugin_loader.py ....................                     [ 74%]
src\tests\test_ptz_controller.py ...................................     [ 83%]
src\tests\test_simulation.py .....................................       [ 92%]
src\tests\test_tracking_pipeline.py ...............................      [100%]

============================ 403 passed in 19.60s =============================
```

### Comprehensive Robustness Sweep Campaign

Execute systematic multidimensional sweeps across all target sizes, kinematics, noise types, and environmental stress levels:

```bash
python run_robustness_campaign.py
```
Outputs detailed JSON metrics and Markdown reports to `output/robustness_campaign_results.json`.

---

## 📁 Repository Layout

```
Run_Time_Error/
├── docs/                                  # Primary Engineering Documentation
│   ├── FRESH_ARCHITECTURE_BASELINE.md     # Architectural baseline & forensic audit
│   ├── FINAL_ENGINEERING_REPORT.md        # Comprehensive phase-by-phase report
│   ├── SIH_REQUIREMENT_TRACEABILITY_MATRIX.md # Full requirement compliance matrix
│   ├── USER_AND_EVALUATOR_MANUAL.md       # Evaluator guide & user instructions
│   └── LumiTrack_v1.0_Technical_Report.pdf# Technical report deliverable
├── graphify-out/                          # Graphify Knowledge Graph & Reports
│   ├── GRAPH_REPORT.md                    # Structural graph analysis & god nodes
│   ├── graph.json                         # Serialized graph topology
│   └── graph.html                         # Interactive 3D visual graph explorer
├── Imp. .md/                              # Project Specification & System Models
│   ├── PS.md                              # SIH Problem Statement 26169 definition
│   ├── PRD.md                             # Product Requirements Document
│   ├── system_architecture.md             # System architecture specification
│   ├── SIH_26_Engineering_Context_Technical_Model.md # Engineering technical model
│   └── AGENTS.md                          # Multi-agent development conventions
├── scenarios/                             # Standard Preconfigured Scenarios
│   ├── scenario_1_static.json             # Static beacon verification scenario
│   ├── scenario_2_circular.json           # Circular orbit trajectory scenario
│   ├── scenario_3_figure8.json            # Figure-8 trajectory scenario
│   └── scenario_4_fog_gaussian.json       # Fog & Gaussian noise scenario
├── src/                                   # Source Code (19 Modules)
│   ├── api/v1/                            # Frozen Public Plugin API (Contracts & Interfaces)
│   ├── app/                               # Application Controller & PySide6 GUI
│   │   └── gui/                           # 2D Viewport, 3D Orbital Widget, Panels
│   ├── config/                            # Configuration & Scenario Managers
│   ├── control/                           # Proportional-Deadband PTZ Controller
│   ├── evaluation/                        # Benchmark Harness, Matrix, AI Scenarios, Reporting
│   ├── frame/                             # Internal Data Contracts & Enumerations
│   ├── interfaces/                        # Internal Strategy Interfaces
│   ├── metrics/                           # Real-time Metrics & Logging Engines
│   ├── plugins/                           # Manifest-based Plugin Discovery System
│   │   └── algorithms/baseline_tracker/   # Official Baseline Tracking Algorithm Plugin
│   ├── simulation/                        # Scene, Target, Camera, Disturbance & Frame Providers
│   ├── tests/                             # 403-Test Regression Suite (100% Pass)
│   ├── tracker/                           # Baseline Detector, Centroid, Kalman & State Manager
│   └── main.py                            # Unified CLI & GUI Application Entry Point
├── dist/LumiTrack/                        # Packaged Standalone Executable
├── lumitrack.spec                         # PyInstaller Packaging Specification
├── run_lumitrack.bat                      # Windows One-Click Application Launcher
├── run_robustness_campaign.py             # Robustness Sweep Campaign Script
├── pytest.ini                             # Pytest Configuration
├── pyrefly.toml                           # Pyrefly Static Analysis Configuration
└── README.md                              # Master Repository Documentation
```

---

## 📖 Documentation Index

| Document | Location | Purpose |
|---|---|---|
| **Evaluator & User Manual** | [docs/USER_AND_EVALUATOR_MANUAL.md](docs/USER_AND_EVALUATOR_MANUAL.md) | Step-by-step evaluator instructions, GUI walkthrough, and operations guide. |
| **Final Engineering Report** | [docs/FINAL_ENGINEERING_REPORT.md](docs/FINAL_ENGINEERING_REPORT.md) | Architectural evolution, phase-by-phase implementation summary, and verification results. |
| **Requirement Traceability Matrix** | [docs/SIH_REQUIREMENT_TRACEABILITY_MATRIX.md](docs/SIH_REQUIREMENT_TRACEABILITY_MATRIX.md) | 100% clause-by-clause mapping against SIH Problem Statement 26169. |
| **Fresh Architecture Baseline** | [docs/FRESH_ARCHITECTURE_BASELINE.md](docs/FRESH_ARCHITECTURE_BASELINE.md) | Architectural audit, ground-truth firewall verification, and Graphify metrics. |
| **SIH Problem Statement** | [Imp. .md/PS.md](Imp.%20.md/PS.md) | Official SIH 2026 Problem Statement 4 (ISRO / Department of Space). |
| **System Architecture Specification** | [Imp. .md/system_architecture.md](Imp.%20.md/system_architecture.md) | Detailed technical model of all 19 platform modules. |
| **Graphify Analysis Report** | [graphify-out/GRAPH_REPORT.md](graphify-out/GRAPH_REPORT.md) | Codebase knowledge graph topology, God nodes, and dependency clusters. |

---

## 🛡 Scope & Operational Boundaries

### What LumiTrack v1.0 Supports
- **Pluggable Tracking Algorithm Architecture:** Dynamic loading, sandboxing, and evaluation of external tracking plugins via `ITrackingAlgorithm`.
- **End-to-End Simulation & Kinematics:** 2D world canvas with multi-trajectory target motion models and rate-limited virtual PTZ gimbal actuation.
- **Physics-Informed Environmental Disturbances:** Additive Gaussian sensor noise, Poisson shot noise, Salt & Pepper impulse noise, atmospheric haze/fog/rain attenuation, high-frequency camera jitter, and platform attitude drift.
- **Dual Benchmark Workflows:** Closed-loop simulation evaluation (BM1) and external MP4 video evaluation with reference comparator (BM2).
- **AI Scenario Generation:** Safe, validated natural language scenario synthesis with deterministic mathematical replay.
- **Dual Visualizations:** 2D sensor HUD viewport and lightweight, QPainter-based 3D geometric orbital perspective view.

### Out of Scope (By Design)
- **Fine Pointing & Fast Steering Mirrors (FSM):** The platform is strictly designed for **Coarse Alignment** (PAT Stage 1) within the camera FOV. Micro-radian piezo beam steering is out of scope.
- **Hardware Optical Gimbal Drivers:** Hardware-in-the-loop physical serial/CAN bus gimbal communication is not implemented; the platform provides virtual simulation models.
- **Active Laser Transmitter Modulation:** Communication data transmission, optical wavefront correction, and bit-error-rate (BER) modulation are outside coarse tracking scope.
- **Proprietary GPU Compute Requirements:** The platform and 3D visualizer are intentionally engineered to run on CPU without requiring dedicated GPU acceleration or external OpenGL drivers.

---

<div align="center">
  <sub>Developed for Smart India Hackathon 2026 • Problem Statement 26169 (PS-4) • Department of Space / ISRO</sub>
</div>
