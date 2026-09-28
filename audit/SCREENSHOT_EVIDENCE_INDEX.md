# DELIVERABLE 4: SCREENSHOT EVIDENCE INDEX
## FSOC-VPAT — AI-Assisted Virtual Camera Tracking & Coarse Alignment Testbed
### SIH Problem Statement 26169 | Team: Run Time Terror (Team ID: 69)

This index provides a forensic catalog of all visual evidence captured during live browser runtime execution on `http://127.0.0.1:5173/` and `http://127.0.0.1:8000/`.

---

## 1. Visual Evidence Catalog

### Screenshot 1: `UI-001-DEVELOPER-INITIAL`
* **File:** [initial_developer_page_1790365369498.png](file:///C:/Users/sanje/.gemini/antigravity-ide/brain/06f0cdfc-ac2f-4286-ba0b-4685e9942bf9/initial_developer_page_1790365369498.png)
* **Route:** `/` (Developer Workspace)
* **Viewport:** 1440 x 900 (Desktop)
* **State:** Normal / Initial Idle
* **Action:** Navigated to root URL upon server startup.
* **Forensic Observations:**
  - Header displays project brand `FSOC-VPAT`, `ID: 69`, status indicator `Connected (FastAPI :8000)`, `WS: Active (30 FPS)`, and navigation tabs (`Developer`, `Evaluator`, `Results & Analysis`).
  - Left sidebar displays comprehensive environment tuning panels: Target Parameters, Optical Channel ($C_n^2$, Wind, Jitter), Sensor / Camera (Resolution, FPS, FOV), Tracking Algorithm, and Gimbal Servo (PID).
  - Main viewport renders 2D Sensor Viewport (640x480 canvas) with reticle crosshairs and sub-pixel peak centroid readout `(320.00, 240.00)`.
  - Right sidebar displays Real-Time Telemetry HUD with Tracking Error charts, Centroid Error ($\Delta X, \Delta Y$), Lock Status (`LOCKED`), and Ground Truth vs Estimated state.
* **Related Requirements:** REQ-01, REQ-02, REQ-10, REQ-22.
* **Related Findings:** F-A11Y-01, F-A11Y-02.

---

### Screenshot 2: `UI-002-DEVELOPER-ACTIVE-TRACKING-2D`
* **File:** [active_tracking_2d_1790365437912.png](file:///C:/Users/sanje/.gemini/antigravity-ide/brain/06f0cdfc-ac2f-4286-ba0b-4685e9942bf9/active_tracking_2d_1790365437912.png)
* **Route:** `/` (Developer Workspace - 2D Viewport)
* **Viewport:** 1440 x 900 (Desktop)
* **State:** Running / Active Tracking (2D Mode)
* **Action:** Clicked `Start Tracking` button with live synthetic simulation running.
* **Forensic Observations:**
  - Real-time optical beacon tracking active under simulated atmospheric turbulence and platform jitter.
  - 2D Canvas overlays bounding box around target, centroid reticle tracking target wander, and motion trajectory trail.
  - Telemetry HUD updates dynamically: Frame counter increments, FPS badge stable at 30–60 FPS, Centroid Error dynamically oscillating within sub-pixel bounds.
  - Control panel switches `Start Tracking` to active `Stop Tracking` state.
* **Related Requirements:** REQ-01, REQ-03, REQ-04, REQ-07, REQ-10, REQ-15.
* **Related Findings:** F-PERF-01, F-REL-01.

---

### Screenshot 3: `UI-003-DEVELOPER-ACTIVE-TRACKING-3D`
* **File:** [active_tracking_3d_1790365469801.png](file:///C:/Users/sanje/.gemini/antigravity-ide/brain/06f0cdfc-ac2f-4286-ba0b-4685e9942bf9/active_tracking_3d_1790365469801.png)
* **Route:** `/` (Developer Workspace - 3D Orbit Viewport)
* **Viewport:** 1440 x 900 (Desktop)
* **State:** Running / Active 3D Spatial Trajectory Mode
* **Action:** Clicked `3D Trajectory` tab toggle in main viewport.
* **Forensic Observations:**
  - Three.js WebGL canvas initializes flawlessly, rendering Earth wireframe/shaded sphere, satellite orbital trajectory path, ground station line-of-sight vector, and gimbal pointing angles.
  - Interactive orbit controls permit rotation, pan, and zoom without dropping frame rate or interrupting background telemetry stream.
  - Pointing error vector dynamically visualized between gimbal optical axis and beacon vector.
* **Related Requirements:** REQ-10, REQ-11, REQ-15.
* **Related Findings:** Verified-Correct Visualization Area.

---

### Screenshot 4: `UI-004-DEVELOPER-MP4-INGESTION-MODE`
* **File:** [mp4_mode_1790365583840.png](file:///C:/Users/sanje/.gemini/antigravity-ide/brain/06f0cdfc-ac2f-4286-ba0b-4685e9942bf9/mp4_mode_1790365583840.png)
* **Route:** `/` (Developer Workspace - Input Source Modal)
* **Viewport:** 1440 x 900 (Desktop)
* **State:** Configuration / Modal Interaction
* **Action:** Clicked `Source: Synthetic` dropdown and selected `MP4 Video File`.
* **Forensic Observations:**
  - Drag-and-drop file ingestion modal displayed with upload zone for `.mp4`, `.avi`, `.mov` files.
  - Options for frame rate override, loop playback, and ground-truth annotation file input displayed.
  - Proves implementation of non-synthetic external video processing capability adhering to standard `FrameProvider` boundary.
* **Related Requirements:** REQ-13, REQ-20.
* **Related Findings:** F-REL-02.

---

### Screenshot 5: `UI-005-EVALUATOR-INITIAL`
* **File:** [evaluator_page_initial_1790365630769.png](file:///C:/Users/sanje/.gemini/antigravity-ide/brain/06f0cdfc-ac2f-4286-ba0b-4685e9942bf9/evaluator_page_initial_1790365630769.png)
* **Route:** `/` (Evaluator Workspace)
* **Viewport:** 1440 x 900 (Desktop)
* **State:** Normal / Initial Idle
* **Action:** Clicked `Evaluator` navigation tab in top navigation header.
* **Forensic Observations:**
  - Standardized Benchmark Matrix suite displayed: BM1 Smoke Test, BM2 Atmospheric Sweep, BM3 Dynamic Occlusion & Outage, BM4 Solar Glint & High Dynamic Range, BM5 Long-Duration Orbit Pass.
  - Dedicated "Run Full AI Scenario Workflow" execution panel with model selection and test scenario configuration.
  - Clear parameter definitions, scenario duration, expected pass/fail criteria cards.
* **Related Requirements:** REQ-08, REQ-14, REQ-22.
* **Related Findings:** F-A11Y-01.

---

### Screenshot 6: `UI-006-EVALUATOR-BENCHMARK-RUNNING`
* **File:** [benchmark_matrix_running_1790365718071.png](file:///C:/Users/sanje/.gemini/antigravity-ide/brain/06f0cdfc-ac2f-4286-ba0b-4685e9942bf9/benchmark_matrix_running_1790365718071.png)
* **Route:** `/` (Evaluator Workspace - Execution State)
* **Viewport:** 1440 x 900 (Desktop)
* **State:** Running / Error Triggered
* **Action:** Clicked `Run BM1 Smoke` button on Evaluator Page.
* **Forensic Observations:**
  - UI triggers loading indicator `Executing BM1 Smoke...`.
  - Terminal log on backend records immediate unhandled exception: `AttributeError: 'BenchmarkMatrixResults' object has no attribute 'batch_id'`.
  - Proves the exact runtime defect between `src/api/server.py:288` and `src/evaluation/benchmark_matrix.py`.
* **Related Requirements:** REQ-14, REQ-22.
* **Related Findings:** F-DEF-01.

---

### Screenshot 7: `UI-007-EVALUATOR-AI-SCENARIO-RUNNING`
* **File:** [ai_scenario_running_1790365756958.png](file:///C:/Users/sanje/.gemini/antigravity-ide/brain/06f0cdfc-ac2f-4286-ba0b-4685e9942bf9/ai_scenario_running_1790365756958.png)
* **Route:** `/` (Evaluator Workspace - AI Execution State)
* **Viewport:** 1440 x 900 (Desktop)
* **State:** Running / Error Triggered
* **Action:** Clicked `Run AI Scenario Workflow` button.
* **Forensic Observations:**
  - UI enters loading state `Running AI Scenario...`.
  - Backend logs record unhandled exception: `TypeError: AIScenarioWorkflow.__init__() missing 1 required positional argument: 'harness'`.
  - Proves the exact API contract mismatch in `src/api/server.py:308-316`.
* **Related Requirements:** REQ-08, REQ-14.
* **Related Findings:** F-DEF-02.

---

### Screenshot 8: `UI-008-RESULTS-PAGE`
* **File:** [results_analysis_page_1790365778127.png](file:///C:/Users/sanje/.gemini/antigravity-ide/brain/06f0cdfc-ac2f-4286-ba0b-4685e9942bf9/results_analysis_page_1790365778127.png)
* **Route:** `/` (Results & Analysis Workspace)
* **Viewport:** 1440 x 900 (Desktop)
* **State:** Normal / Telemetry Scorecard
* **Action:** Clicked `Results & Analysis` navigation tab.
* **Forensic Observations:**
  - Renders top scorecard metrics: Mean FPS (`638.9`), Centroid RMSE (`1.42 px`), Target Loss Rate (`0.0%`), Total Benchmark Pass Rate (`19/19`).
  - Displays Detailed Verification Breakdown cards: Acquisition Latency (`0.033 s`), Re-acquisition Latency (`0.067 s`), Jitter Rejection Ratio (`14.2 dB`), Max Gimbal Slew (`5.0°/s`).
  - Forensic code analysis confirms these metrics are hardcoded static mockups in `ResultsPage.tsx:76-88` rather than dynamic aggregations from backend runs.
* **Related Requirements:** REQ-16, REQ-17, REQ-18, REQ-19, REQ-22.
* **Related Findings:** F-UX-01, F-UX-02.

---

## 2. Complete Session Recording
* **File:** [vpat_browser_audit_1790365318518.webp](file:///C:/Users/sanje/.gemini/antigravity-ide/brain/06f0cdfc-ac2f-4286-ba0b-4685e9942bf9/vpat_browser_audit_1790365318518.webp)
* **Description:** Continuous WebP video capturing the full interactive browser audit across Developer (2D/3D), Evaluator, and Results workflows, documenting all interactions, transitions, and runtime errors.
