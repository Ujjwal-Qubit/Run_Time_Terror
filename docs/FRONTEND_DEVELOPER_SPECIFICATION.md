# LumiTrack — Frontend Product & Integration Specification

> **Document Classification:** Engineering Design & Integration Specification  
> **Target Audience:** Frontend Software Engineers (Web & Desktop), UI/UX Engineers, Platform Integrators  
> **Status:** Implementation-Ready Specification  
> **Authoritative Baseline:** Architecture v1.2 Frozen Baseline & Forensic Repository Audit (2026-09-21)  
> **Target File:** `docs/FRONTEND_DEVELOPER_SPECIFICATION.md`

---

## 📌 Executive Summary

This document is the authoritative, comprehensive product and integration specification for the **LumiTrack** frontend. It is written specifically for software engineers joining the project to develop, refine, and modernize the frontend interface.

### Context & What LumiTrack Is

LumiTrack is an **Algorithm Evaluation Platform** and **Simulation Testbed** engineered for the autonomous coarse alignment of mobile **Free Space Optical Communication (FSOC)** terminals. Developed under the Smart India Hackathon (SIH 2026) Problem Statement 26169 (PS-4) for the **Department of Space / Indian Space Research Organisation (ISRO)**, the platform evaluates optical beacon tracking algorithms under severe realistic disturbances (atmospheric turbulence, mechanical camera jitter, sensor noise, platform motion).

**Critical Insight for Frontend Engineers:**  
LumiTrack is **not** a simple video player, and **not** merely a simulation control panel. It is a dual-mode scientific evaluation platform where:
1. External computer vision and AI tracking algorithms are treated as independent **Units Under Test (UUT)** loaded dynamically via a standardized plugin interface (`ITrackingAlgorithm`).
2. The platform tests these algorithms across two distinct benchmark regimes:
   - **Benchmark 1 (BM1):** Closed-loop 2D simulation with active Pan-Tilt-Zoom (PTZ) gimbal tracking, where camera attitude responds to algorithm commands.
   - **Benchmark 2 (BM2):** Open-loop ingestion of recorded MP4 video files with PTZ camera control bypassed, comparing tracking outputs against optional external reference coordinates.
3. The platform strictly enforces a **Ground-Truth Firewall**: tracking algorithms receive only observable pixel data (`FramePacket`) and never observe true physical target locations.
4. Evaluation metrics (Centroid RMSE, Tracking Error, Target Loss Rate, Processing FPS, Acquisition Time) are computed independently by the platform harness and formatted into decision-ready scorecards and audit reports.

### Purpose of the Frontend

The frontend enables researchers, algorithm developers, and competition evaluators to configure scenarios, inspect real-time sensor feeds and 3D terminal geometry, execute reproducible benchmark suites, generate AI-assisted test scenarios, and review multi-dimensional performance scorecards.

### Status Markers Used in this Specification

To guarantee absolute engineering honesty and avoid ungrounded assumptions, every component, control, API contract, and workflow in this document is explicitly marked with one of the following validated status flags:

* `[Implemented / Verified]`: Exists in code, tested, and passing verification in the current repository.
* `[Partially implemented]`: Exists in code but contains stubs, incomplete UI hookups, or missing backend wiring.
* `[Planned / Not currently implemented]`: Required by the product workflow or architecture, but not currently written in code.
* `[Frontend work required]`: A specific task or screen that the new frontend developers are tasked with implementing or wiring.
* `[Not established from current repository]`: Cannot be confirmed or deduced from the codebase without inventing facts.

---

## 🏛 Product Overview & Architectural Context

### 1. The Physical Problem: Optical Coarse Alignment

Free Space Optical Communication (FSOC) transmits high-throughput optical data between moving platforms (satellites, aircraft, UAVs, naval vessels, ground stations) using divergence-limited laser beams ($< 1\text{ mrad}$). Establishing an optical link requires Pointing, Acquisition, and Tracking (PAT):
- **Coarse Alignment:** Detecting an incoming optical beacon spot ($5\times 5$ to $20\times 20$ pixels) across a wide field-of-view ($640\times 480$) and actuating a motorized PTZ gimbal ($5^\circ/\text{s} - 10^\circ/\text{s}$) to drive the spot to the optical axis center $(320, 240)$.
- **Fine Alignment:** Piezoelectric fast steering mirrors (sub-microradian) refine the beam once coarse alignment is maintained within a narrow deadband.

LumiTrack provides the virtual testbed and evaluation harness that replaces physical optical tables and gimbals.

### 2. High-Level Data Flow & The Strict Ground-Truth Firewall

```
+---------------------------------------------------------------------------------------------------+
|                                      LUMITRACK PLATFORM                                           |
|                                                                                                   |
|  +---------------------------+       Observable       +----------------------------------------+  |
|  |     SIMULATION / MP4      |      FramePacket       |         TRACKING ALGORITHM             |  |
|  |  * 2000x2000 Scene Engine | ---------------------> |        (Unit Under Test - UUT)         |  |
|  |  * Kinematic Target Model |   (Strict Firewall)    |  * Adaptive P0 Threshold Detector      |  |
|  |  * Atmospheric Engine     |                        |  * AI Clutter Classifier (Logistic Reg)|  |
|  |  * Sensor Noise & Jitter  |                        |  * Sub-pixel Intensity Centroiding     |  |
|  +---------------------------+                        |  * Kalman State Estimator & FSM        |  |
|               |                                       +----------------------------------------+  |
|   True Target | Ground Truth                                               | Subjective           |
|   Coordinates | (Firewalled)                                               | TrackingResult       |
|               v                                                            v                      |
|  +---------------------------------------------------------------------------------------------+  |
|  |                             PLATFORM CONTROLLER & METRICS HARNESS                           |  |
|  |  * Proportional-Deadband PTZ Gimbal Control (M14)                                          |  |
|  |  * Objective Metrics Engine (Centroid RMSE, Lock Retention, Acquisition Time, Latency, FPS)|  |
|  |  * Dual-Viewport Visualization (2D HUD Sensor View + 3D Geometric Orbital Viewport)        |  |
|  +---------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

#### Ground-Truth Firewall Rules:
1. **Observable Data Only:** External algorithms implement `ITrackingAlgorithm` (`src/api/v1/algorithm.py`) and receive only `FramePacket` (`src/api/v1/contracts.py`), containing a grayscale NumPy array, timestamp, frame number, resolution, and FOV.
2. **Subjective Output:** Algorithms output a `TrackingResult` declaring subjective belief: `algorithm_is_tracking` (bool), `centroid_x`, `centroid_y`, `confidence` $[0.0, 1.0]$, and `roi` bounding box.
3. **No Leakage:** Physical target position $(x_{\text{world}}, y_{\text{world}})$, ideal image projection, and disturbance parameters bypass the algorithm completely, flowing straight to `MetricsEngine`.
4. **Benchmark 2 Isolation:** In MP4 mode, simulation physics modules (`SceneManager`, `TargetManager`, `CameraModel`, `DisturbanceEngine`, `GroundTruthProvider`) are not instantiated (`None`). Ground truth is strictly absent unless an external evaluator reference CSV is supplied.

### 3. Graphify Codebase Architecture & God Node Topography

Static and topological graph analysis (`graphify-out/GRAPH_REPORT.md`) establishes a clean, cycle-free architecture across the repository:
* **Total Nodes:** 1,836
* **Total Edges:** 4,369
* **Discovered Communities:** 89
* **Import Cycles:** **0 (Zero circular dependencies)**
* **Top-10 Core Architectural God Nodes:**
  1. `AppController` (`src/app/app_controller.py` — 196 edges): Top-level lifecycle orchestrator and module coordinator.
  2. `BenchmarkManager` (`src/evaluation/benchmark_manager.py` — 70 edges): Benchmark-1/2 batch coordinator and report orchestrator.
  3. `ProportionalDeadbandPTZController` (`src/control/ptz_controller.py` — 69 edges): Closed-loop gimbal control law.
  4. `TrackingState` (`src/frame/data_contracts.py` — 69 edges): Central tracking FSM enum (`SEARCHING`, `ACQUIRING`, `TRACKING`, `LOST`, `REACQUIRING`).
  5. `PluginLoader` (`src/plugins/loader.py` — 60 edges): Dynamic manifest discovery and algorithm loading engine.
  6. `IntensityWeightedCentroidEstimator` (`src/tracker/centroid_estimator.py` — 60 edges): Sub-pixel localization engine.
  7. `FramePacket` (`src/frame/data_contracts.py` & `src/api/v1/contracts.py` — 59 edges): Public input data contract.
  8. `P0ThresholdDetector` (`src/tracker/detection_engine.py` — 59 edges): Dynamic noise estimation and thresholding.
  9. `TrackResult` (`src/frame/data_contracts.py` — 56 edges): Temporal filtering output contract.
  10. `CentroidResult` (`src/frame/data_contracts.py` — 55 edges): Sub-pixel centroid estimation contract.

---

## 👥 User Personas & Supported User Journeys

The frontend must support four distinct user personas, each with specific technical goals and workflows:

```
+--------------------------------------------------------------------------------------------------+
|                                    LUMITRACK USER PERSONAS                                       |
+---------------------------+---------------------------+------------------------------------------+
| 1. FIRST-TIME USER /      | 2. ALGORITHM DEVELOPER    | 3. EVALUATOR / JUDGE (SIH)               |
|    OBSERVER               |                           |                                          |
| Needs rapid orientation,  | Injects new CV/AI plugins,| Runs standardized benchmark matrix       |
| one-click demo, clear     | tunes parameters live,    | (BM1/BM2), validates SIH compliance,     |
| visual feedback, and zero | diagnoses tracking loss,  | inspects objective scorecards, and       |
| cognitive friction.       | and inspects latency.     | exports audit reports.                   |
+---------------------------+---------------------------+------------------------------------------+
|                                  4. RESEARCHER / DATA SCIENTIST                                  |
| Generates synthetic stress scenarios via natural language AI prompts, conducts multi-algorithm   |
| comparative bake-offs, analyzes loss episodes, and inspects raw telemetry CSVs.                  |
+--------------------------------------------------------------------------------------------------+
```

### 1. First-Time User Journey
* **Goal:** Launch the platform, understand what it does within 15 seconds, run a demonstration, and see tracking in action.
* **Flow:**
  1. Launches application (`run_lumitrack.bat` or `python -m src.main --gui`).
  2. Arrives at the **Developer Workflow** screen with defaults pre-loaded (`baseline_tracker`, `scenario_2_circular.json`).
  3. Clicks **Start**.
  4. Observes live 2D sensor video with tracking crosshairs and reticle, synchronized with the interactive 3D terminal view.
  5. Observes real-time telemetry HUD updating (FPS: ~30, State: `TRACKING`, Status: `LOCKED` in green).
  6. Clicks **Stop** or **Reset** to return to idle.

### 2. Algorithm Developer Journey
* **Goal:** Test a custom tracking algorithm against the platform testbed, verify plugin loading, and tune parameters live.
* **Flow:**
  1. Places algorithm package in `src/plugins/algorithms/<my_algorithm>/` with valid `manifest.json`.
  2. Launches UI; the **Algorithm** dropdown automatically displays the newly discovered algorithm.
  3. Selects the custom algorithm. Manifest metadata (version, author, description) populates immediately.
  4. Selects a stress scenario (e.g. `scenario_4_fog_gaussian.json`).
  5. Clicks **Start**.
  6. Tweaks configuration sliders live (target speed, jitter amplitude, atmospheric fog) and observes if the algorithm maintains track lock.
  7. If the algorithm throws an exception, the UI isolates the failure, displays an error badge, and prevents application crash.

### 3. Evaluator / Competition Judge Journey
* **Goal:** Objectively evaluate an algorithm submission against the official SIH 26169 benchmark criteria.
* **Flow:**
  1. Navigates via the sidebar to **Evaluator Workflow**.
  2. Selects the algorithm under test and chooses benchmark suite:
     - **Benchmark 1:** Selects matrix subset (`SMOKE`, `CORE`, `DISTURBANCE`, or `FULL`).
     - **Benchmark 2:** Loads an external test video (`.mp4`) and evaluator reference CSV.
  3. Clicks **Run Benchmark Matrix**.
  4. Progress bar and evaluation console log execution across scenarios.
  5. Upon completion, UI automatically navigates to **Results & Analysis**, displaying the aggregate scorecard, threshold verdicts (PASS/FAIL against SIH limits), and generated report file paths.
  6. Clicks **Export to PDF/Markdown** to produce the final official evaluation package.

### 4. Researcher Journey
* **Goal:** Explore edge-case vulnerabilities using natural language generative scenarios.
* **Flow:**
  1. Navigates to **Evaluator Workflow** → **AI-Assisted Evaluation**.
  2. Enters a natural language prompt: *"Fast target moving in a spiral at 85 px/s through dense haze with 4 px jitter"*.
  3. Clicks **Generate & Run AI Scenario**.
  4. The platform parses NLP entities, validates boundaries against physical constraints, deterministically generates the trajectory, and executes the evaluation run.
  5. Researcher inspects error curves, loss episodes, and reacquisition timestamps in the Results dashboard.

---

## 🖥 Complete Screen Inventory

The current product defines three primary workflow pages housed in a sidebar navigation layout (`src/app/gui/main_window.py`).

```
+---------------------------------------------------------------------------------------------------+
|  LumiTrack — Virtual Camera Tracking & Algorithm Evaluation Platform                     [-][x]   |
+-------------------+-------------------------------------------------------------------------------+
|  SIDEBAR          |  MAIN CONTENT AREA (QStackedWidget)                                           |
|                   |                                                                               |
|  [Logo] LumiTrack |  PAGE 0: 🔧 Developer Workflow                                                |
|                   |  - Left: Operation Mode + Algorithm Selector + Playback Controls + Config     |
|  [ ] Dev Workflow |  - Center: Tabbed 2D Sensor View / 3D Geometric Scene View                    |
|  [ ] Evaluator    |  - Bottom: Real-time Telemetry Dashboard Bar                                  |
|  [ ] Results      |                                                                               |
|                   |  PAGE 1: 📊 Evaluator Workflow                                                |
|                   |  - Standard Benchmark Matrix Execution (SMOKE / CORE / FULL)                  |
|                   |  - AI-Assisted Generative Scenario Prompt & Execution                         |
|                   |  - Real-time Evaluation Console Log                                           |
|                   |                                                                               |
|                   |  PAGE 2: 📈 Results & Analysis                                                |
|                   |  - Benchmark Scorecard Data Grid (RMSE, FPS, Loss Rate, Verdicts)             |
|                   |  - Failure Analysis & Episode Breakdown Panel                                 |
|                   |  - Refresh & Export Actions                                                   |
+-------------------+-------------------------------------------------------------------------------+
```

---

### Screen 1: Developer Workflow (`page_dev`)

* **Status:** `[Implemented / Verified]` (UI layout & interactive loop verified in `src/app/gui/main_window.py`).
* **Purpose:** Interactive real-time testbed for live simulation tuning, manual algorithm verification, and dual-viewport sensor/geometric inspection.
* **Target Users:** Algorithm Developers, First-Time Users.
* **Entry Point:** Application launch default; Sidebar button "🔧 Developer Workflow" (index 0).
* **Exit / Navigation:** Sidebar buttons to Evaluator Workflow or Results.
* **Sub-Panels & Components:**
  1. `ControlPanel` (`src/app/gui/control_panel.py`): Operation mode toggles, scenario file picker, MP4 file picker, algorithm plugin dropdown and status metadata, playback controls (`Start`, `Stop`, `Pause`, `Resume`, `Reset`).
  2. `ConfigPanel` (`src/app/gui/config_panel.py`): Tabbed configuration editor (`Camera`, `Target`, `Disturbances`) with live parameter synchronization.
  3. `QTabWidget` Central Viewports:
     - Tab 0: `VideoWidget` (`src/app/gui/video_widget.py`) — 2D OpenCV-rendered camera sensor feed with HUD overlays.
     - Tab 1: `View3DWidget` (`src/app/gui/view_3d.py`) — QPainter-based 3D geometric scene with interactive orbit/pan/zoom.
  4. `TelemetryPanel` (`src/app/gui/telemetry_panel.py`): 11-field live telemetry grid displaying state, lock status, sub-pixel coordinates, error, angles, FPS, and latency.
* **Inputs:** Scenario JSON path, MP4 file path, algorithm selection, parameter spinbox/combobox inputs, playback button clicks, 3D mouse gestures.
* **Outputs:** 30 FPS visual frame feed, live 3D orientation, telemetry metrics, CSV/JSON logs in `output/`.
* **State Dependencies:** `AppController` lifecycle (`IDLE`, `RUNNING`, `PAUSED`), `VisualizationState` queue.
* **Backend Dependencies:** `AppController`, `SimulationFrameProvider`, `MP4FrameProvider`, `VisualizationEngine`, `PluginLoader`.
* **API / Interface Dependencies:** `ITrackingAlgorithm`, `FramePacket`, `TrackingResult`, `VisualizationState`.
* **Loading State:** Disabled buttons during worker startup; `VideoWidget` displays black canvas or last frame.
* **Empty State:** Video display shows black canvas with "Simulation Reset" or reticle; telemetry shows `---` and `IDLE`.
* **Error State:** Modal dialog (`QMessageBox.critical`) on initialization failure or invalid configuration; algorithm status badge shows red `Error`.
* **Success State:** Playback active; status indicator glows green `LOCKED`; video renders at smooth frame rates.
* **Disabled State:** During playback, `Start` and `Reset` are disabled; `Stop` and `Pause` are enabled. In MP4 mode, scenario configuration tabs are disabled.
* **Permissions / Restrictions:** Algorithms cannot modify camera geometry or access ground truth.

---

### Screen 2: Evaluator Workflow (`page_eval`)

* **Status:** `[Partially implemented]` (Matrix execution wired; AI execution button stubbed in `src/app/gui/evaluation_panel.py`).
* **Purpose:** High-level batch evaluation suite execution across standardized benchmark matrices (BM1) and AI-generated scenarios.
* **Target Users:** Evaluators, Competition Judges, Researchers.
* **Entry Point:** Sidebar button "📊 Evaluator Workflow" (index 1).
* **Exit / Navigation:** Automatically navigates to Results page upon matrix completion, or manual sidebar navigation.
* **Sub-Panels & Components:**
  1. Standard Evaluation Group: Explanatory banner, `Run Benchmark Matrix` button.
  2. AI-Assisted Evaluation Group: Explanatory banner, `Generate & Run AI Scenario` button.
  3. Evaluation Console Log (`QTextEdit`): Real-time streaming log of batch execution, verdicts, and report export paths.
* **Inputs:** Active algorithm selection (from ControlPanel or default), benchmark trigger clicks.
* **Outputs:** Multi-run batch execution, console log stream, comprehensive reports written to `output/matrix/` or `output/ai_scenarios/`.
* **State Dependencies:** `BenchmarkManager._is_running`, `EvaluationHarness`.
* **Backend Dependencies:** `BenchmarkManager`, `BenchmarkMatrixRunner`, `AIScenarioWorkflow`, `ComprehensiveReportGenerator`.
* **API / Interface Dependencies:** `BenchmarkScenarioDefinition`, `EvaluationOutcome`, `BenchmarkMatrixResults`.
* **Loading State:** Console logs "Starting Benchmark Matrix...", UI buttons disabled to prevent concurrent runs.
* **Empty State:** Console log empty; default placeholder text.
* **Error State:** Console appends `ERROR: <message>`; error dialog displayed if execution halts.
* **Success State:** Console outputs `Verdict: PASSED (PS 26169 Compliant)`, summary stats, and file paths; success popup displayed.
* **Disabled State:** Controls disabled while a benchmark batch is running.
* **Frontend Work Required:**
  - Connect `btn_run_ai` to a modal dialog prompting for natural language input (currently a stub `pass` at line 90 of `evaluation_panel.py`).
  - Add subset selector dropdown (`SMOKE`, `CORE`, `DISTURBANCE`, `FULL`) instead of hardcoding `SMOKE`.
  - Add execution progress bar (currently missing; evaluator cannot see scenario progress).

---

### Screen 3: Results & Analysis (`page_results`)

* **Status:** `[Partially implemented]` (Scorecard table population verified; Refresh and Export buttons unlinked in `src/app/gui/results_panel.py`).
* **Purpose:** Detailed review of benchmark scorecards, pass/fail compliance gates, failure episode diagnostics, and artifact export.
* **Target Users:** Evaluators, Researchers, Algorithm Developers.
* **Entry Point:** Sidebar button "📈 Results & Analysis" (index 2); or auto-redirect from completed benchmark.
* **Exit / Navigation:** Sidebar navigation to other pages.
* **Sub-Panels & Components:**
  1. Latest Evaluation Scorecard (`QTableWidget`): 3-column table (`Metric`, `Value`, `Status`) displaying Algorithm, Verdict, Mean FPS, Centroid RMSE, Target Loss Rate with color-coded pass/fail text.
  2. Failure Analysis Panel (`QTextEdit`): Textual breakdown of failed runs, error messages, and loss episodes.
  3. Action Buttons: `Refresh Results`, `Export to PDF/Markdown`.
* **Inputs:** User clicks on action buttons; `load_results(matrix_res, report_path)` programmatic invocation.
* **Outputs:** Formatted scorecards, exported PDF/Markdown files in `output/`.
* **State Dependencies:** `BenchmarkMatrixResults` cached in panel.
* **Backend Dependencies:** `ComprehensiveReportGenerator`, `LoggingEngine`.
* **Loading State:** Table displays "Loading results...".
* **Empty State:** Empty table with headers; failure text displays "No benchmark results loaded. Run an evaluation first."
* **Error State:** Status text highlights in red (`FAIL`); failure panel lists specific error traces.
* **Success State:** Verdict displays `PASSED` in bold green; all gate metrics show `PASS`.
* **Disabled State:** Export button disabled if no report path is loaded.
* **Frontend Work Required:**
  - Wire `btn_refresh.clicked` to re-scan `output/` for the latest `*_summary.json` or `*_report.json`.
  - Wire `btn_export.clicked` to trigger `ComprehensiveReportGenerator` export or open the system file explorer at `output/`.
  - Add comparative side-by-side view for multi-algorithm benchmarking (`ComparisonSummary`).

---

## 🎛 Complete Button & Control Specification

Below is the complete inventory of all frontend controls across the application. Each control is documented with its location, purpose, action, backend integration, state transitions, and error handling.

| Control Label / Identifier | Location | Purpose | Enabled When | User Action | Backend / API Called | State Change | Success Feedback | Failure / Error Handling | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **Developer Workflow** (`btn_nav_dev`) | Sidebar | Switches view to interactive simulation testbed | Always | Click | None (UI view switch) | `stacked_widget.currentIndex = 0` | Page switches; button highlighted | N/A | `[Implemented / Verified]` |
| **Evaluator Workflow** (`btn_nav_eval`) | Sidebar | Switches view to benchmark matrix & AI runner | Always | Click | None (UI view switch) | `stacked_widget.currentIndex = 1` | Page switches; button highlighted | N/A | `[Implemented / Verified]` |
| **Results & Analysis** (`btn_nav_results`) | Sidebar | Switches view to evaluation scorecard & diagnostics | Always | Click | None (UI view switch) | `stacked_widget.currentIndex = 2` | Page switches; button highlighted | N/A | `[Implemented / Verified]` |
| **Simulation Mode Radio** (`radio_sim`) | ControlPanel | Selects Benchmark 1 closed-loop simulation mode | `IDLE` state | Select radio | `ConfigManager.config.simulation.mode = "SIMULATION"` | Mode toggled; enables scenario picker & config tabs | Scenario picker enabled; MP4 picker disabled | N/A | `[Implemented / Verified]` |
| **MP4 Mode Radio** (`radio_mp4`) | ControlPanel | Selects Benchmark 2 open-loop video processing | `IDLE` state | Select radio | `ConfigManager.config.simulation.mode = "MP4"` | Mode toggled; enables MP4 picker; locks sim config tabs | MP4 picker enabled; config tabs grayed out | N/A | `[Implemented / Verified]` |
| **Scenario Browse** (`scenario_btn`) | ControlPanel | Opens file dialog to load a scenario JSON | `IDLE` & Sim Mode | Click | `ConfigManager.load_from_file()`, updates ConfigPanel | Config updated to match file | Input path updated; spinboxes reflect scenario values | `FileNotFoundError` -> User alert | `[Implemented / Verified]` |
| **MP4 Browse** (`mp4_btn`) | ControlPanel | Opens file dialog to load test video file | `IDLE` & MP4 Mode | Click | Updates `simulation.mp4_path` | MP4 path stored in config | LineEdit displays chosen `.mp4` path | File format validation error dialog | `[Implemented / Verified]` |
| **Algorithm Selector** (`algo_combo`) | ControlPanel | Selects active algorithm plugin under test (UUT) | `IDLE` state | Dropdown Select | `AppController.select_algorithm(algo_name)` | `active_algorithm` updated, instantiated, initialized | Version, author, description, and status `Active` updated | If init fails, status shows `Error`, error logged | `[Implemented / Verified]` |
| **Start Playback** (`btn_start`) | ControlPanel | Starts continuous simulation or video playback | `IDLE` state | Click | `AppController.initialize()`, `start_background_loop()` | `IDLE` -> `RUNNING`; worker thread spawned | Video stream renders; telemetry updates; Start disabled | `QMessageBox.critical` displays initialization failure | `[Implemented / Verified]` |
| **Stop Playback** (`btn_stop`) | ControlPanel | Halts active playback loop and finalizes logs | `RUNNING` or `PAUSED` | Click | `AppController.stop()` | `RUNNING` -> `IDLE`; thread joined; files finalized | Playback halts; Start enabled; Stop disabled | Worker join timeout logged if thread hangs | `[Implemented / Verified]` |
| **Pause Playback** (`btn_pause`) | ControlPanel | Temporarily suspends frame loop without reset | `RUNNING` | Click | `AppController.pause()` | `RUNNING` -> `PAUSED` | Frame ingestion halts; Pause disabled; Resume enabled | N/A | `[Implemented / Verified]` |
| **Resume Playback** (`btn_resume`) | ControlPanel | Resumes suspended frame loop | `PAUSED` | Click | `AppController.resume()` | `PAUSED` -> `RUNNING` | Frame ingestion resumes; Resume disabled; Pause enabled | N/A | `[Implemented / Verified]` |
| **Reset Simulation** (`btn_reset`) | ControlPanel | Flushes filters, resets camera, clears display | `IDLE` state | Click | `AppController.reset()`, `VideoWidget.reset()`, `TelemetryPanel.reset()` | All modules reset to initial parameters | Video cleared to "Simulation Reset"; telemetry cleared to `IDLE` | N/A | `[Implemented / Verified]` |
| **Live Config Inputs** (Spinboxes, Comboboxes) | ConfigPanel | Dynamically tunes camera, target, and disturbance parameters | Sim Mode | Value Changed | Signal `config_changed` -> live updates TargetManager & DisturbanceEngine | `SystemConfig` fields modified in real time | Simulation physics adapt instantly without restart | Out-of-bounds rejected by spinbox min/max limits | `[Implemented / Verified]` |
| **2D / 3D Tab Selector** (`view_tabs`) | Central Viewport | Toggles between 2D camera HUD and 3D terminal geometry | Always | Click Tab | None (QTabWidget native switch) | Active viewport tab index toggled | Displays selected visualizer | N/A | `[Implemented / Verified]` |
| **3D Orbit Control** (Left Mouse Drag) | View3DWidget | Rotates orbital azimuth and elevation angles | Over 3D view | Mouse Drag | Updates internal `_cam_azimuth_deg`, `_cam_elevation_deg` | 3D projection matrix recalculated | Viewport smoothly orbits scene | Elevation clamped to $[-85^\circ, +85^\circ]$ | `[Implemented / Verified]` |
| **3D Pan Control** (Right Mouse Drag) | View3DWidget | Translates 3D focal center across world plane | Over 3D view | Mouse Drag | Updates internal `_cam_target` $[x, y]$ | Target focal center displaced | Scene pans with mouse cursor | N/A | `[Implemented / Verified]` |
| **3D Zoom Control** (Mouse Wheel) | View3DWidget | Adjusts camera distance from target | Over 3D view | Scroll Wheel | Updates internal `_cam_distance` | Projection scale updated | Viewport zooms in / out | Clamped between $[100.0, 2000.0]\text{ units}$ | `[Implemented / Verified]` |
| **Run Benchmark Matrix** (`btn_run_matrix`) | EvaluationPanel | Executes batch evaluation over scenario matrix | `IDLE` state | Click | `BenchmarkManager.run_benchmark_matrix()`, `generate_comprehensive_report()` | Evaluator running batch; results written to disk | Console displays progress, verdicts, and report path; auto-navigates to Results | Logs error in console; shows error message | `[Implemented / Verified]` |
| **Run AI Scenario** (`btn_run_ai`) | EvaluationPanel | Generates and executes scenario from natural language | `IDLE` state | Click | `AIScenarioWorkflow.execute_prompt()` | Generates scenario, runs harness, logs results | Console displays parsed spec, validation status, and scores | Logs rejection reasons if prompt invalid | `[Partially implemented]` *(Stubbed handler in GUI)* |
| **Refresh Results** (`btn_refresh`) | ResultsPanel | Reloads latest scorecard from output artifacts | Always | Click | Re-reads latest report from `output/` | Results table refreshed with newest metrics | Table reflects latest evaluation run | Warning banner if no output files found | `[Frontend work required]` *(Needs click handler wiring)* |
| **Export Scorecard** (`btn_export`) | ResultsPanel | Exports evaluation scorecard to Markdown/PDF | Results loaded | Click | Opens file explorer at report path or triggers PDF export | None (file write/open) | System dialog opens or report opened in default viewer | Error banner if report file missing | `[Frontend work required]` *(Needs click handler wiring)* |

---

## 🔄 UI State Machine & Lifecycle Model

The application transitions through five formal states governed by the `AppController` and UI action guards.

```
       +-------------------------------------------------------+
       |                                                       |
       v                                                       |
   [ IDLE ] <-------------------+                              |
       │                        │                              |
       │ (Select / Configure)   │ (Reset)                      |
       v                        │                              |
 [ CONFIGURING ]                │                              |
       │                        │                              |
       │ (Start Playback / Run) │                              |
       v                        │                              |
  [ RUNNING ] ──────────────────┤                              |
       │   ▲                    │                              |
(Pause)│   │(Resume)            │                              |
       v   │                    │                              |
  [ PAUSED ]                    │                              |
       │                        │                              |
       │ (Stream End / Stop)    │                              |
       v                        │                              |
  [ COMPLETED ] ────────────────┘                              |
       │                                                       |
       │ (Auto / View Results)                                 |
       v                                                       |
  [ RESULTS ] ─────────────────────────────────────────────────+
```

### State Definitions & Control Matrix

| System State | Visual Indicators | Enabled Controls | Disabled Controls | Background Activity | Transition Trigger |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IDLE** | Video shows "Simulation Reset" or reticle; Telemetry shows `IDLE` / `UNLOCKED` | Mode radios, Browse buttons, Algorithm combo, `Start`, `Reset`, Config inputs, `Run Matrix` | `Stop`, `Pause`, `Resume` | None. All background worker threads terminated. | User selects parameters or loads scenario. |
| **CONFIGURING** | Parameters highlight as modified; Algorithm status badge updates (`Ready` / `Active`) | All IDLE controls active | `Stop`, `Pause`, `Resume` | Config validation; algorithm manifest parsing and class verification. | User clicks `Start` or triggers evaluation. |
| **RUNNING** | Video feed renders at 30 FPS with live overlays; Telemetry updates rapidly; Status shows `LOCKED` (green) or `SEARCHING` (red) | `Stop`, `Pause`, Live disturbance sliders, 3D mouse gestures | `Start`, `Reset`, Mode radios, Algorithm combo, Scenario picker | FrameProvider extraction, Algorithm `process_frame()`, PTZ calculation, LoggingEngine writing to disk, queue dispatch. | User clicks `Pause` or `Stop`, or video file reaches EOF. |
| **PAUSED** | Video feed freezes on current frame; Telemetry retains frozen metrics; HUD displays `PAUSED` | `Resume`, `Stop`, 3D mouse gestures | `Start`, `Pause`, `Reset`, Mode radios, Algorithm combo | Simulation clock paused; frame worker sleeps; no queue updates. | User clicks `Resume` -> `RUNNING`; User clicks `Stop` -> `COMPLETED`. |
| **COMPLETED** | Video halts on final frame; Telemetry shows final metrics; Console logs run completion summary | `Start`, `Reset`, `View Results`, Mode radios, Algorithm combo | `Stop`, `Pause`, `Resume` | Worker thread joins; LoggingEngine flushes CSV buffers; summary JSON written to disk. | User clicks `Reset` -> `IDLE`; User views results -> `RESULTS`. |
| **RESULTS** | Full scorecard data grid visible; Pass/fail compliance badges; Failure episode breakdown | `Refresh`, `Export`, Navigation sidebar | Playback controls inactive on Results tab | JSON report reading and table formatting. | User navigates back to Developer or Evaluator workflow. |

---

## 🎯 Benchmark 1 (BM1) Frontend Workflow

**Benchmark 1** evaluates algorithms in a closed-loop synthetic simulation where the tracking algorithm drives the virtual camera's PTZ gimbal to maintain lock on a moving optical beacon under synthetic environmental stress.

```
[Evaluator Selects BM1]
           │
           ▼
[Choose Scenario] ──> Predefined JSON (19 standard scenarios) or Custom Tuning
           │
           ▼
[Select Algorithm UUT] ──> (e.g., baseline_tracker or custom plugin)
           │
           ▼
[Start Evaluation]
           │
           ├── Worker Thread: SceneManager -> TargetManager -> CameraModel -> DisturbanceEngine
           ├── Observable Pixel Feed -> PublicFramePacket -> Algorithm.process_frame()
           ├── Algorithm Output -> TrackingResult -> ProportionalDeadbandPTZController
           ├── PTZ Command -> CameraModel Pose Update (Closed-Loop Actuation)
           ├── GroundTruthProvider -> True Target Coordinates -> MetricsEngine (Firewalled)
           └── Queue -> VisualizationState -> 2D Sensor HUD + 3D Orbital Frustum Viewport
           │
           ▼
[Stop / Completion] ──> Automated Metric Aggregation & Report Generation
```

### 1. Configuration Parameters Available
* **Simulation:** Random seed (int, default `42`), duration ($s$, default indefinite for interactive, $30.0\text{ s}$ for benchmarks).
* **Camera:** Resolution ($640\times 480$ default, up to $4000\times 4000$), FOV ($4.0^\circ \times 3.0^\circ$ default), Update rate ($10 - 120\text{ Hz}$, $30\text{ Hz}$ default).
* **Target:** Size ($5\times 5$ to $20\times 20\text{ px}$, $10\text{ px}$ default), Shape (`square`, `circle`, `gaussian`), Speed ($0.0 - 500.0\text{ px/s}$, $50.0\text{ px/s}$ default), Motion pattern (`STRAIGHT_LINE`, `CIRCULAR`, `FIGURE_8`, `RANDOM`, `SPIRAL`, `SINUSOIDAL`).
* **Disturbances:**
  - Atmospheric: `CLEAR`, `HAZE`, `FOG`, `RAIN`, `LOW_LIGHT`.
  - Noise: `NONE`, `GAUSSIAN` ($\sigma \le 20.0$), `SALT_AND_PEPPER` (density $\le 0.10$), `POISSON`.
  - Mechanical: Platform motion (`LINEAR`, $\le 50.0\text{ px/f}$), Camera jitter (enabled, amplitude $\le 20.0\text{ px/f}$).
* **PTZ Controller:** Proportional gain ($K_p = 8.0$), Integral gain ($K_i = 2.0$), Deadband ($1.0\text{ px}$), Max pan/tilt speed ($5.0^\circ/\text{s}$).

### 2. BM1 Standard Scenarios Subsets
The standard benchmark matrix (`src/evaluation/matrix.py`) defines 19 frozen scenarios grouped into four standard evaluation subsets:
* `SMOKE` (3 scenarios): Rapid sanity check (`matrix_01_linear_nominal`, `matrix_02_circular_nominal`, `matrix_09_atmos_fog`).
* `CORE` (6 scenarios): Primary SIH validation scenarios across fundamental motion patterns.
* `DISTURBANCE` (8 scenarios): Systematic stress sweep over noise, atmospheric attenuation, and jitter.
* `FULL` (19 scenarios): Exhaustive benchmark matrix covering the entire operational envelope.

---

## 📹 Benchmark 2 (BM2) Frontend Workflow

**Benchmark 2** evaluates algorithms on pre-recorded external MP4 video footage covering arbitrary resolutions and challenging unmodeled optics.

```
[Evaluator Selects BM2]
           │
           ▼
[Select MP4 File] ──> Validates format, resolution, and frame readability
           │
           ▼
[Optional Reference CSV] ──> (frame, true_x, true_y)
           │
           ├── [Reference Provided]     ──> Spatial Accuracy Computed (RMSE, Mean Err, Coverage)
           └── [Reference NOT Provided] ──> Accuracy Metrics Suppressed (Rule 6 Honesty Guarantee)
           │
           ▼
[PTZ Camera Bypassed] ──> Gimbal actuation disabled; frame processed as fixed sensor footage
           │
           ▼
[Evaluation Execution] ──> Video decoded frame-by-frame; Algorithm processes PublicFramePacket
           │
           ▼
[Grand Summary & Scorecard] ──> Throughput FPS, Loss Rate, Acquisition Time, Detection Rate
```

### 1. The Rule 6 Reference Honesty Guarantee
A critical platform requirement is that **accuracy metrics must never be fabricated**:
* **Reference CSV Present:** If the evaluator provides an annotated CSV (`frame,true_x,true_y`), the platform calculates:
  - Sub-pixel Centroid Root-Mean-Square Error (RMSE) against reference coordinates.
  - Mean and Maximum spatial error.
  - Percentage of frames within $1\text{ px}$, $2\text{ px}$, and $5\text{ px}$.
  - Reference frame annotation coverage percentage.
* **Reference CSV Absent:** If no reference CSV is provided, accuracy metrics are populated as `None` / `N/A`. The frontend **must** display `N/A (Reference not provided)` rather than zero or an estimated value.

### 2. Supported Evaluator CSV Formats
The CSV parser (`BenchmarkManager.load_evaluator_reference_csv`) supports standard header variations:
- Standard: `frame,true_x,true_y`
- Alternative: `frame,x,y` or `frame_idx,centroid_x,centroid_y`
- Headerless: 3 numeric columns parsed as `[frame, x, y]`.

---

## 🧩 Algorithm Plugin Interface & Selection UI

LumiTrack implements a decoupled plugin architecture (`src/plugins/`) where external algorithms are treated as Units Under Test (UUT).

```
src/plugins/algorithms/
└── <plugin_name>/
    ├── manifest.json       <-- Required plugin metadata
    └── <entry_module>.py   <-- Implements ITrackingAlgorithm
```

### 1. Plugin Manifest Schema (`manifest.json`)
Every plugin folder must contain a valid `manifest.json` following this schema:

```json
{
  "name": "baseline_tracker",
  "version": "1.0.0",
  "api_version": "v1",
  "entry_point": "baseline_tracker:BaselineTracker",
  "description": "SIH '26 Baseline Tracking Algorithm (P0 Threshold Detection + IW Centroiding + AI Classifier + Kalman + FSM)",
  "author": "SIH Evaluator Team",
  "dependencies": [
    "numpy",
    "opencv-python"
  ],
  "metadata": {
    "recommended_fps": 30
  }
}
```

### 2. Public Algorithm API Contract (`src/api/v1/algorithm.py`)
External algorithms implement three lifecycle methods:

```python
class ITrackingAlgorithm(ABC):
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Called once before scenario starts with algorithm-specific config."""
        pass

    @abstractmethod
    def process_frame(self, frame_packet: FramePacket) -> TrackingResult:
        """Per-frame execution entry point. Receives observable FramePacket only."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Clears temporal state, Kalman matrices, and buffers between runs."""
        pass
```

### 3. Frontend Plugin Handling & Error Isolation
* **Discovery:** At startup, `AppController.discover_algorithms()` scans `src/plugins/algorithms` in deterministic alphabetical order.
* **Selection:** Selecting an algorithm from the UI dropdown invokes `select_algorithm(name)`. The UI displays:
  - Plugin Name (`algo_combo`)
  - Version: `v<version>` (`lbl_algo_version`)
  - Description: Paragraph text (`lbl_algo_desc`)
  - Status Badge: `Active` in bold green (`lbl_algo_status`)
* **Fault Containment:** If an algorithm raises an unhandled exception during initialization or execution, the platform catches the exception, records the error string in `AppController.algorithm_error`, marks the status badge as `Error` in red, and gracefully continues without crashing the application.

---

## 🧠 AI-Assisted Scenario Generation Workflow

LumiTrack includes an intelligent Natural Language Scenario Generation Subsystem (`src/evaluation/ai_scenario.py`) that translates unstructured human prompts into fully validated, deterministic physical test scenarios.

```
[Natural Language Prompt]
"Fast optical beacon in dense fog moving in a spiral at 75 px/s with severe jitter"
                           │
                           ▼
              [AI Interpretation Engine]
              Extracts kinematic & environmental parameters via NLP regex & heuristic rules
                           │
                           ▼
             [Candidate Scenario Specification]
             (trajectory_type="SPIRAL", speed=75.0, atmos="FOG", jitter=True, amp=6.0)
                           │
                           ▼
           [Scenario Specification Validator]
           Enforces physical safety & boundary constraints:
           * Target speed: 5.0 <= speed <= 150.0 px/s
           * Coordinates: within 2000x2000 world canvas
           * Target size: 5 <= size <= 20 px
           * Noise & disturbance parameter bounds
                  │
                  ├── [REJECT] ──> Displays explicit validation error list in UI
                  └── [ACCEPT]
                           │
                           ▼
        [Deterministic Trajectory Generator]
        Computes closed-form mathematical coordinates from seed (SPIRAL, SINUSOIDAL, etc.)
                           │
                           ▼
              [Tagged Scenario JSON]
              (is_ai_generated = True, spec_hash = <sha256>)
                           │
                           ▼
           [Simulator & Evaluation Harness]
           Executes benchmark under strict Ground-Truth Firewall
```

### Authoritative Constraints:
1. **AI Output is NOT Authoritative:** The AI engine outputs a candidate specification. The validator is the authoritative gatekeeper.
2. **Deterministic Trajectory Generator is Authoritative:** The mathematical trajectory generator calculates continuous coordinates; the AI never injects arbitrary frame-by-frame coordinates directly into the simulation.
3. **Supported Geometries:** `STRAIGHT_LINE`, `CIRCULAR`, `FIGURE_8`, `RANDOM`, `SPIRAL`, `SINUSOIDAL`.

---

## 👁 Visualization Requirements: 2D HUD & 3D Scene

The central viewport is a tabbed interface providing dual visual perspectives:

### 1. 2D Camera HUD Viewport (`VideoWidget`)
Displays the monochrome camera image with colored graphical overlays rendered by `VisualizationEngine` (`src/app/visualization_engine.py`):
* **Raw Camera Sensor Feed:** Grayscale monochrome image scaled preserving aspect ratio against a dark background.
* **Cyan Bounding Box:** Adaptive tracking Region of Interest (ROI) box ($1\text{ px}$ cyan line), indicating the localized window searched by the detector.
* **Red Crosshair & Circle:** Sub-pixel estimated centroid $(\hat{x}, \hat{y})$ produced by the algorithm ($10\text{ px}$ crosshair with $5\text{ px}$ radius circle), active in `TRACKING`, `ACQUIRING`, and `REACQUIRING` states.
* **White Center Reticle:** Camera optical axis boresight crosshair at frame center $(w/2, h/2)$ ($15\text{ px}$ white line).
* **Green Marker (Ground Truth):** Physical target location rendered as a small green square (available in debug mode; verified strictly isolated from algorithm output).
* **Live HUD Text (Top-Left):**
  - `FRAME: <frame_number>`
  - `STATE: <state>` (Color-coded: Green = `TRACKING`, Cyan = `ACQUIRING`/`REACQUIRING`, Red = `LOST`, White = `SEARCHING`)
  - `TRK ERR: <error> px` (Euclidean distance to optical axis)
  - `LATENCY: <ms> ms` | `FPS: <fps>`
  - `PTZ: P <pan_deg>deg / T <tilt_deg>deg`

### 2. 3D Geometric Scene Viewport (`View3DWidget`)
A lightweight, high-performance 3D visualizer built using **PySide6 QPainter perspective projection** (`src/app/gui/view_3d.py`).
* **Zero GPU Driver Dependency:** Operates using CPU projection mathematics, completely eliminating OpenGL driver crashes on virtualized, remote, or headless machines.
* **Rendered Visual Elements:**
  - **Ground Grid:** $400\times 400$ unit coordinate grid with subtle dotted lines.
  - **Coordinate Axes:** Color-coded reference axes ($X = \text{Red}$, $Y = \text{Green}$, $Z = \text{Blue}$).
  - **Terminal Pedestal:** 3D cylindrical base representing the optical terminal mount.
  - **PTZ Camera Frustum:** 4-sided wireframe pyramid oriented dynamically in 3D space using real-time pan and tilt angles ($\theta_p, \theta_t$), representing the sensor's physical field-of-view cone.
  - **Optical Axis Ray:** Dashed yellow vector projecting from the terminal aperture along the camera pointing vector.
  - **Target Beacon & Breadcrumbs:** Red sphere representing the 3D optical beacon, trailing an orange historical path of the previous 60 frames.
  - **Line-of-Sight (LOS) Beam:** Semi-transparent green laser vector connecting the terminal aperture directly to the target.
* **Interactive Controls:**
  - **Left-Click Drag:** Orbit azimuth $[0^\circ, 360^\circ]$ and elevation $[-85^\circ, +85^\circ]$.
  - **Right-Click Drag:** Pan focal center across the ground plane.
  - **Scroll Wheel:** Zoom distance clamped between $[100.0, 2000.0]\text{ units}$.

---

## 📊 Telemetry & Real-Time Metrics Dashboard

The `TelemetryPanel` (`src/app/gui/telemetry_panel.py`) occupies the bottom dashboard bar, displaying 11 synchronized metrics refreshed at ~20 FPS via Qt Signals:

| Metric Label | Key | Initial / Idle Value | Live Source Field | Format / Styling | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Algorithm** | `algo_lbl` | `baseline_tracker` | `active_algorithm_name` | Blue, Bold | Name of active tracking plugin under test |
| **Frame** | `frame_lbl` | `---` | `VisualizationState.frame_number` | Plain text | Monotonically increasing frame index |
| **State** | `state_lbl` | `IDLE` | `VisualizationState.tracking_state` | Bold, color-coded | FSM state (`SEARCHING`, `ACQUIRING`, `TRACKING`, `LOST`) |
| **Lock Status** | `lock_lbl` | `UNLOCKED` | Derived from state | Red / Yellow / Green | `LOCKED` (green) if `TRACKING`; `ACQUIRING` (yellow); `UNLOCKED` (red) |
| **Tracking Error** | `err_lbl` | `---` | Derived: $\sqrt{(\hat{x}-c_x)^2 + (\hat{y}-c_y)^2}$ | Float (`0.00 px`) | Euclidean distance from estimated centroid to frame optical axis |
| **Centroid X** | `cx_lbl` | `---` | `VisualizationState.estimated_centroid_x` | Float (`0.00`) | Sub-pixel horizontal coordinate in image plane |
| **Centroid Y** | `cy_lbl` | `---` | `VisualizationState.estimated_centroid_y` | Float (`0.00`) | Sub-pixel vertical coordinate in image plane |
| **Pan Angle** | `pan_lbl` | `0.00` | `VisualizationState.pan_angle_deg` | Float (`0.00 deg`) | Current camera gimbal pan angle relative to boresight |
| **Tilt Angle** | `tilt_lbl` | `0.00` | `VisualizationState.tilt_angle_deg` | Float (`0.00 deg`) | Current camera gimbal tilt angle relative to boresight |
| **FPS** | `fps_lbl` | `---` | `VisualizationState.fps` | Float (`0.0`) | Instantaneous algorithm execution throughput rate |
| **Latency** | `lat_lbl` | `---` | `VisualizationState.processing_latency_ms` | Float (`0.0 ms`) | Execution latency of algorithm's `process_frame()` |

---

## 📈 Results Dashboard & Compliance Reporting

The Results view (`src/app/gui/results_panel.py`) displays evaluation scorecards against official **SIH Problem Statement 26169 Threshold Limits**:

### 1. SIH 26169 Pass/Fail Compliance Thresholds

| Benchmark Metric | SIH Required Limit | Platform Baseline Measurement | Verdict Status |
| :--- | :--- | :--- | :---: |
| **Processing Throughput (FPS)** | $\ge 20.0\text{ FPS}$ | **$638.9\text{ FPS}$** (Algorithm Core) / **$30.0\text{ FPS}$** (Platform Clock) | ✅ **PASS** |
| **Tracking Error (Mean)** | $\le 10.0\text{ px}$ | **$0.000\text{ px} - 2.850\text{ px}$** across standard matrix | ✅ **PASS** |
| **Acquisition Time** | $\le 2.0\text{ s}$ | **$0.000\text{ s} - 0.033\text{ s}$** (Instantaneous P0 lock) | ✅ **PASS** |
| **Reacquisition Time** | $\le 1.0\text{ s}$ | **$\le 0.067\text{ s}$** post-occlusion | ✅ **PASS** |
| **Target Loss Rate** | $< 5.0\%$ | **$0.0\%$** across standard scenarios | ✅ **PASS** |
| **PTZ Gimbal Slew Rates** | Max $5^\circ/\text{s} - 10^\circ/\text{s}$ | Clamped dynamically at $5.0^\circ/\text{s}$ | ✅ **PASS** |

### 2. Multi-Format Report Artifacts (`src/evaluation/reporting.py`)
Every benchmark execution automatically generates three artifacts in `output/`:
1. **JSON Report (`<suite_id>_report.json`):** Complete machine-readable audit containing run summaries, per-frame statistics, failure analysis summaries, and SIH gate verdicts.
2. **CSV Matrix Summary (`<suite_id>_matrix_summary.csv`):** Tabular format summarizing total frames, algorithm FPS, benchmark throughput FPS, centroid RMSE, tracking error, loss rate, and compliance verdicts per scenario.
3. **Markdown Scorecard (`<suite_id>_comprehensive_report.md`):** Human-readable GitHub-Flavored Markdown report with executive summary tables, compliance verdicts, and failure episode breakdowns.

---

## 🔌 API & Integration Contract

This section defines the exact communication mechanics between the frontend and the underlying platform.

### CURRENT CONTRACT: In-Process Desktop Python Architecture

> **Architecture Reality:**  
> LumiTrack is currently an in-process, single-runtime desktop application (`PySide6`).  
> **No frontend-backend network port is currently required or open.**

```
+-----------------------------------------------------------------------------------------------+
|                                     IN-PROCESS RUNTIME                                        |
|                                                                                               |
|  [PySide6 Frontend]                                 [Platform Engine]                         |
|  MainWindow / Panels                                AppController (Module 1)                  |
|          │                                                    │                               |
|          ├── Calls app.select_algorithm(name) --------------> ├── PluginLoader.load_plugin()  |
|          ├── Calls app.initialize(config) ------------------> ├── Scene/Camera/Disturbance    |
|          ├── Calls app.start_background_loop() -------------> ├── Spawns Worker Thread       |
|          │                                                    │       │                       |
|          │   [Polling via QTimer (50ms)]                      │       │                       |
|          ├── Calls app.get_latest_visualization_state() <────┼───────┴─ Writes to Queue       |
|          │                                                    │          (_viz_queue, max=30) |
|          ├── Emits Qt Signal state_updated(state)             │                               |
|          │       │                                            │                               |
|          │       ├── TelemetryPanel.update_state()            │                               |
|          │       └── View3DWidget.update_state()              │                               |
|          │                                                    │                               |
|          └── Calls BenchmarkManager.run_benchmark_matrix() ─> ├── Executes Matrix Harness    |
+-----------------------------------------------------------------------------------------------+
```

* **Method Invocations:** Frontend panels hold direct references to `AppController` and `BenchmarkManager`. Actions are direct synchronous Python method calls.
* **Frame Dispatch:** The simulation loop runs on a background daemon thread (`AppController._simulation_loop()`), writing `VisualizationState` instances to a thread-safe FIFO queue (`_viz_queue = queue.Queue(maxsize=30)`).
* **Frame Ingestion:** `VideoWidget` runs a `QTimer` at $50\text{ ms}$ intervals (~20 FPS) on the Qt main thread. It invokes `app.get_latest_visualization_state()`, which drains the queue, discards stale frames, and emits the freshest state via a Qt Signal (`state_updated = Signal(object)`).
* **Panel Synchronization:** `VideoWidget.state_updated` is connected directly to `TelemetryPanel.update_state` and `View3DWidget.update_state`.

---

### REQUIRED FRONTEND CONTRACT: Client-Server Web Architecture

> **Specification for Web Modernization:**  
> If the new frontend developers are building a decoupled web interface (e.g. React / Next.js / Vite) to replace or augment the desktop GUI, the backend interface is currently not exposed as HTTP/REST.  
> **Frontend integration contract required — backend network interface currently not exposed.**

To enable a web frontend, a lightweight web service (FastAPI recommended) must be wrapped around `AppController` and `BenchmarkManager`. Below is the required API contract that must be implemented to support the frontend:

#### Required REST Endpoints

| Method | Endpoint | Purpose | Request Body | Response Body | Error Codes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/algorithms` | Returns list of discovered algorithm plugins | None | `{"algorithms": [{"name": "baseline_tracker", "version": "1.0.0", "description": "...", "status": "Ready"}]}` | 500 |
| `POST` | `/api/v1/algorithms/select` | Activates an algorithm plugin | `{"algorithm_name": "baseline_tracker"}` | `{"success": true, "active_algorithm": "baseline_tracker"}` | 400, 404, 500 |
| `GET` | `/api/v1/scenarios` | Returns list of available scenario JSON files | None | `{"scenarios": ["scenario_1_static", "scenario_2_circular", ...]}` | 500 |
| `GET` | `/api/v1/config` | Returns current system configuration | None | `SystemConfig` JSON | 500 |
| `PUT` | `/api/v1/config` | Updates system configuration | Partial `SystemConfig` JSON | `{"success": true, "updated_config": {...}}` | 400, 422 |
| `POST` | `/api/v1/simulation/start` | Starts simulation / video loop | None | `{"status": "RUNNING"}` | 400, 409 |
| `POST` | `/api/v1/simulation/stop` | Stops active simulation loop | None | `{"status": "IDLE"}` | 400 |
| `POST` | `/api/v1/simulation/pause` | Pauses simulation loop | None | `{"status": "PAUSED"}` | 400 |
| `POST` | `/api/v1/simulation/resume` | Resumes simulation loop | None | `{"status": "RUNNING"}` | 400 |
| `POST` | `/api/v1/simulation/reset` | Resets all modules to origin | None | `{"status": "IDLE"}` | 400 |
| `POST` | `/api/v1/evaluation/matrix` | Executes benchmark matrix | `{"subset": "CORE", "algorithm": "baseline_tracker", "seed": 42}` | `{"batch_id": "matrix_CORE_...", "status": "COMPLETED", "verdict": "PASS"}` | 400, 500 |
| `POST` | `/api/v1/evaluation/ai-scenario` | Generates & executes AI scenario | `{"prompt": "Fast target in fog", "algorithm": "baseline_tracker"}` | `{"scenario_id": "ai_...", "valid": true, "results": {...}}` | 400, 422 |
| `GET` | `/api/v1/reports/latest` | Returns latest benchmark scorecard | None | JSON representation of `BenchmarkMatrixResults` | 404 |

#### Required Realtime Streaming Contract (WebSocket)

* **Endpoint:** `ws://localhost:8000/ws/live`
* **Protocol:** JSON message stream or Binary JPEG/WebP frames + JSON metadata packet.
* **Payload Schema (`VisualizationPacket`):**
  ```json
  {
    "frame_number": 120,
    "timestamp": 4.0,
    "tracking_state": "TRACKING",
    "lock_status": "LOCKED",
    "estimated_centroid": {"x": 321.4, "y": 239.8},
    "roi": {"x": 300, "y": 220, "w": 40, "h": 40},
    "pan_angle_deg": 1.25,
    "tilt_angle_deg": -0.84,
    "camera_fov": 4.0,
    "tracking_error_px": 1.41,
    "fps": 30.0,
    "latency_ms": 1.56,
    "image_base64": "data:image/jpeg;base64,..."
  }
  ```

---

## 💻 Ports, Processes & Local Development

### Current Desktop Development Environment

| Process / Entity | Implementation | Host / Binding | Port | Startup Command | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Desktop Application** | PySide6 / Qt6 | Local OS Process | **None** | `python -m src.main --gui` | Runs in-process on main OS thread. |
| **Simulation Worker** | Python `threading.Thread` | In-Process Thread | **None** | Spawned via `AppController.start_background_loop()` | Runs background simulation loop. |
| **Standalone Executable**| PyInstaller Bundle | Local OS Process | **None** | `.\dist\LumiTrack\LumiTrack.exe --gui` | Self-contained zero-install binary. |

### Proposed Web Architecture Environment (If Transitioning to Web)

| Process / Entity | Technology | Host | Port | Startup Command |
| :--- | :--- | :--- | :--- | :--- |
| **Backend API Server** | FastAPI / Uvicorn | `127.0.0.1` | `8000` | `uvicorn src.api.server:app --reload --port 8000` |
| **Frontend Dev Server** | Vite / React | `localhost` | `3000` | `npm run dev` (in `frontend/`) |
| **Live WebSocket** | WebSocket Adapter | `127.0.0.1` | `8000` | Mounted on `/ws/live` |

---

## 🛠 Recommended Frontend Project Structure

To maintain clean separation between the existing backend and any newly introduced web frontend components, developers must adopt the following project directory layout:

```text
external/
├── docs/                               <-- System architecture & specifications
│   ├── FRESH_ARCHITECTURE_BASELINE.md
│   └── FRONTEND_DEVELOPER_SPECIFICATION.md  <-- THIS AUTHORITATIVE DOCUMENT
├── scenarios/                          <-- Predefined standard scenario JSONs
├── src/                                <-- Core Python Platform & Modules
│   ├── api/v1/                         <-- Authoritative algorithm plugin contracts
│   ├── app/                            <-- Application controller & visualization
│   │   ├── gui/                        <-- [EXISTING] Active PySide6 Desktop Frontend
│   │   │   ├── config_panel.py         <-- Configuration tabs editor
│   │   │   ├── control_panel.py        <-- Playback & mode controls
│   │   │   ├── evaluation_panel.py     <-- Evaluator benchmark & AI runner
│   │   │   ├── main_window.py          <-- Main application window & sidebar
│   │   │   ├── results_panel.py        <-- Scorecard & diagnostics view
│   │   │   ├── telemetry_panel.py      <-- Bottom HUD dashboard bar
│   │   │   ├── video_widget.py         <-- 2D OpenCV sensor feed
│   │   │   └── view_3d.py              <-- 3D QPainter geometric scene
│   │   ├── app_controller.py           <-- Module 1: Central orchestrator
│   │   └── visualization_engine.py     <-- Module 18: 2D HUD overlay renderer
│   ├── evaluation/                     <-- Module 17: Benchmark Manager & Harness
│   ├── plugins/                        <-- Algorithm plugins & PluginLoader
│   └── simulation/                     <-- Virtual environment & camera models
└── frontend/                           <-- [PLANNED / RECOMMENDED FOR WEB]
    ├── src/
    │   ├── api/                        <-- REST & WebSocket API clients
    │   ├── components/                 <-- Reusable UI components (buttons, badges)
    │   │   ├── control/                <-- Playback buttons, mode switchers
    │   │   ├── config/                 <-- Parameter forms & sliders
    │   │   ├── telemetry/              <-- Telemetry HUD cards
    │   │   └── visualization/          <-- Canvas 2D player & Three.js 3D viewport
    │   ├── layouts/                    <-- Sidebar, navigation header
    │   ├── pages/                      <-- DeveloperPage, EvaluatorPage, ResultsPage
    │   ├── hooks/                      <-- useSimulation, useWebSocket, useBenchmark
    │   ├── types/                      <-- TypeScript models matching contracts.py
    │   └── utils/                      <-- Formatting, mathematical helpers
    ├── package.json
    └── vite.config.ts
```

---

## 🛡 Security & Trust Boundaries

Frontend developers must enforce strict boundaries to protect benchmark integrity and prevent security issues:

1. **Ground-Truth Protection:** The frontend must never expose true target coordinates as if they were algorithm estimates. Ground truth markers (green square) are permitted strictly in debug mode and must be clearly labeled as simulation truth.
2. **In-Process Algorithm Isolation:** Algorithm plugins run in the same Python process. Malformed return values (non-numeric coordinates, `None`, unhandled exceptions) must be sanitized and isolated before passing to PTZ or UI renderers.
3. **AI Prompt Sanitization:** Prompts submitted to the AI scenario generator must pass boundary checks in `ScenarioSpecificationValidator`. Malformed inputs must be rejected with diagnostic messages before reaching the simulation engine.
4. **File Path Traversal:** When browsing scenarios, MP4 videos, or reference CSVs, paths must be validated to prevent unauthorized directory access outside the workspace.
5. **No Secret Storage:** API keys or tokens for optional remote LLM services must never be stored in frontend code or client-side assets; they must remain in environment variables on the backend.

---

## 📋 Frontend Developer Responsibilities & Workstream Breakdown

The frontend development roadmap is divided into two balanced, decoupled workstreams designed for two engineers working in parallel:

```
+--------------------------------------------------------------------------------------------------+
|                                    DEVELOPER WORKSTREAMS                                         |
+--------------------------------------------------+-----------------------------------------------+
| DEVELOPER A — CORE APP & CONTROLS                | DEVELOPER B — VISUALIZATION & EVALUATION      |
+--------------------------------------------------+-----------------------------------------------+
| Focus: Application shell, navigation,            | Focus: Sensor rendering, 3D geometric views,  |
| configuration forms, algorithm management,       | real-time telemetry HUD, benchmark runner,   |
| scenario selectors, and mode switching.          | results scorecards, and reporting exports.    |
+--------------------------------------------------+-----------------------------------------------+
```

### Developer A: Application Shell, Configuration & Algorithm Management
* **Task A1: Refine / Rebuild Application Shell & Navigation**
  - Dependencies: None.
  - Integration Point: `MainWindow` / Navigation Sidebar.
  - Output: Responsive layout with clean mode switching (`Developer`, `Evaluator`, `Results`).
* **Task A2: Complete ControlPanel & Mode Switcher**
  - Dependencies: Task A1.
  - Integration Point: `src/app/gui/control_panel.py`.
  - Output: Operation mode toggle (`SIMULATION` vs `MP4`), file browsers with path validation, playback button states (`Start`, `Stop`, `Pause`, `Resume`, `Reset`).
* **Task A3: Algorithm Plugin Management UI**
  - Dependencies: Task A2.
  - Integration Point: `src/app/app_controller.py` (`get_available_algorithms`, `select_algorithm`).
  - Output: Algorithm dropdown, metadata card (version, author, description), live status badge (`Active` / `Error`), and exception banner.
* **Task A4: Comprehensive Configuration Panel**
  - Dependencies: Task A1.
  - Integration Point: `src/app/gui/config_panel.py`, `ConfigManager`.
  - Output: Full parameter coverage (`Camera`, `Target`, `Disturbances`, `PTZ`) with live tuning signal emission.

### Developer B: Visualization, Telemetry, Evaluation & Results
* **Task B1: Real-Time 2D Sensor Viewport & Overlays**
  - Dependencies: None.
  - Integration Point: `src/app/gui/video_widget.py`, `VisualizationEngine`.
  - Output: High-performance canvas rendering camera frames with Cyan ROI, Red Centroid crosshairs, White Aiming reticle, and Top-Left HUD text.
* **Task B2: Interactive 3D Geometric Terminal Viewport**
  - Dependencies: None.
  - Integration Point: `src/app/gui/view_3d.py`.
  - Output: 3D orbital viewport rendering terminal pedestal, dynamic PTZ camera frustum, LOS beam, and historical trajectory breadcrumbs with mouse orbit/pan/zoom.
* **Task B3: Real-Time Telemetry Bar**
  - Dependencies: Task B1.
  - Integration Point: `src/app/gui/telemetry_panel.py`.
  - Output: 11-metric telemetry dashboard updating at 20 FPS with color-coded lock indicators.
* **Task B4: Evaluator Workflow & AI Scenario Generator Dialog**
  - Dependencies: Task A1.
  - Integration Point: `src/app/gui/evaluation_panel.py`, `BenchmarkManager`, `AIScenarioWorkflow`.
  - Output: Benchmark matrix runner with subset selector (`SMOKE`, `CORE`, `DISTURBANCE`, `FULL`), execution progress bar, and AI prompt input modal dialog.
* **Task B5: Results Dashboard & Report Export Actions**
  - Dependencies: Task B4.
  - Integration Point: `src/app/gui/results_panel.py`, `ComprehensiveReportGenerator`.
  - Output: Scorecard data grid, pass/fail SIH compliance badges, failure episode text view, and working `Refresh` and `Export` buttons.

---

## ✅ Frontend Acceptance Criteria

Before signing off on any frontend implementation or update, developers must verify compliance against the following objective criteria:

### Application & Navigation
1. Application launches with zero warnings or errors via `run_lumitrack.bat` or `python -m src.main --gui`.
2. Sidebar transitions smoothly between Developer, Evaluator, and Results views without frame stutter or visual artifacts.
3. Dark theme aesthetic is uniformly maintained across all panels, tables, dialogs, and inputs.

### Algorithm Plugin Management
4. All valid algorithm subdirectories in `src/plugins/algorithms/` appear in the algorithm dropdown in alphabetical order.
5. Selecting an algorithm displays its declared version, description, and author.
6. Deliberately injecting a broken plugin (e.g. invalid syntax or crashing `initialize()`) displays a red `Error` status badge without crashing the UI.

### Benchmark 1 (Simulation) Mode
7. Starting playback launches the background simulation thread; video feed displays moving beacon at ~30 FPS.
8. Live adjustments to target speed or atmospheric disturbance sliders take effect immediately in the viewport without restart.
9. Clicking `Pause` freezes playback cleanly; clicking `Resume` continues smoothly.
10. Clicking `Reset` stops the worker thread, flushes filters, resets camera pointing to origin, and clears telemetry labels to `IDLE`.

### Benchmark 2 (MP4) Mode
11. Selecting MP4 mode gray-outs simulation configuration tabs and enables MP4 file browser.
12. Loading an MP4 decodes frames cleanly across standard ($640\times 480$) and non-standard ($800\times 600$) resolutions.
13. If an evaluator reference CSV is supplied, accuracy metrics (Centroid RMSE) are populated; if omitted, accuracy fields display `N/A` without error.

### 3D Visualization
14. 3D Geometric Scene renders ground grid, terminal pedestal, camera frustum, optical ray, and target beacon.
15. Left-click drag smoothly orbits the camera; right-click drag pans; scroll wheel zooms.
16. Frustum dynamically reorients in sync with camera pan and tilt angles.

### Evaluator & Results Dashboard
17. Triggering Benchmark Matrix executes scenarios sequentially and logs progress to the console.
18. Results view populates with overall verdict (`PASSED` / `FAILED`), Mean FPS, Centroid RMSE, and Target Loss Rate.
19. SIH compliance gates are explicitly highlighted with green `PASS` or red `FAIL` badges.
20. Clicking export produces valid Markdown and JSON report files in `output/`.

---

## 🔍 Forensic Repository Findings & Current Limitations

During the forensic audit of the codebase, several discrepancies between documentation and active code were identified:

1. **Superseded Tkinter Controller:**  
   `src/app/gui_controller.py` is a legacy Tkinter GUI. It has been superseded by the active PySide6 implementation in `src/app/gui/`. Frontend developers must work in `src/app/gui/` and avoid modifying or importing `gui_controller.py`.
2. **Stubbed AI Generation Button in GUI:**  
   `EvaluationPanel._on_run_ai()` (`src/app/gui/evaluation_panel.py:90`) currently contains a stub (`pass`). However, the underlying backend engine (`AIScenarioWorkflow` in `src/evaluation/ai_scenario.py`) is fully functional, tested, and passing CLI tests. Developer B must wire this button to an input modal dialog.
3. **Unwired Results Panel Actions:**  
   `ResultsPanel.btn_refresh` and `btn_export` (`src/app/gui/results_panel.py:44`) are instantiated but lack `.clicked.connect(...)` signal handlers. Developer B must wire these buttons to reload results and trigger exports.
4. **Desktop vs. Web Integration:**  
   The platform is currently an in-process PySide6 desktop application. No REST/WebSocket server exists in the current repository. If building a web frontend, developers must implement the lightweight FastAPI adapter specified in Section 19.

---

## 📚 Reference Documentation & Traceability

Developers should cross-reference the following authoritative repository artifacts:

* **Core Architecture Baseline:** `docs/FRESH_ARCHITECTURE_BASELINE.md`
* **System Architecture Specification:** `Imp. .md/system_architecture.md`
* **SIH Problem Statement Alignment:** `Imp. .md/PS.md` & `README.md`
* **SIH Requirement Traceability Matrix:** `docs/SIH_REQUIREMENT_TRACEABILITY_MATRIX.md`
* **Graph Topological Analysis:** `graphify-out/GRAPH_REPORT.md`
* **Public Plugin Algorithm API:** `src/api/v1/algorithm.py` & `src/api/v1/contracts.py`
* **Application Lifecycle Controller:** `src/app/app_controller.py`
* **Benchmark & Matrix Subsystems:** `src/evaluation/benchmark_manager.py` & `src/evaluation/matrix.py`
* **Active PySide6 GUI Root:** `src/app/gui/main_window.py`
