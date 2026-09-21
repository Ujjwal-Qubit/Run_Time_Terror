# Phase 5.10 — 2D Frontend Implementation & Backend Integration Plan

This document outlines the execution plan for Phase 5.10 of the SIH ’26 FSOC Virtual Camera Tracking System. This is a **planning-only** output derived directly from an inspection of the current repository structure.

## A. Current Frontend Reality

A comprehensive inspection of `src/app` and `src/main.py` yields the following GUI status:

| Component | File | Framework | Purpose | Implemented? | Wired? | Backend dependency | Status |
| --------- | ---- | --------- | ------- | ------------ | ------ | ------------------ | ------ |
| `GUIController` | `gui_controller.py` | Tkinter | Main Desktop App | Yes | Partially | High (Direct Calls) | **Duplicate Logic** |
| `VisualizationEngine` | `visualization_engine.py` | OpenCV + NumPy | Frame Overlays | Yes | Yes | `TrackerOutput` | **Functional** |
| App Launcher | `main.py` | CLI Argparse | Launch GUI with `--gui` | Yes | Yes | `AppController` | **Functional** |

### Additional Observations:
* **Current GUI Technology:** Standard Python Tkinter.
* **Current Application Entry Point:** `python -m src.main --gui`.
* **Current Window Type:** Basic 1024x768 Tkinter PanedWindow.
* **Existing Widgets:** Sidebar with Radiobuttons for Mode, Combobox for Motion/Atmospheric, Entry for MP4, Start/Stop buttons. Live video feed via Canvas.
* **Duplicate Frontend Implementation:** Critically, `gui_controller.py` contains a duplicate simulation loop inside `_run_loop()`. It manually sequences the Detection, Identification, Centroiding, and Tracking algorithms instead of delegating execution to a unified backend engine. This violates the separation of concerns.
* **Missing Functionality:** No Benchmark-1 controls, no report generation buttons, no live telemetry metrics beyond HUD overlays, no configuration for Camera parameters, Targets, and most Disturbance types. No pause/reset buttons.

## B. Frontend Gaps

The current implementation has significant architectural and functional gaps:
1. **Simulation Engine Duplication:** The GUI manually fetches frames and invokes the algorithm modules directly, essentially running as a second simulation engine.
2. **Missing Configuration:** 80% of `SystemConfig` variables (Camera resolution, PTZ limits, noise types, target attributes) are inaccessible from the UI.
3. **No Benchmark-1 Support:** The GUI cannot select multiple scenarios, run a batch benchmark, or display grand summary reports.
4. **No Metric Dashboards:** There are no UI panes for displaying tracking error, centroid RMSE, lock retention, or latency statistics in real-time.
5. **No Independent Display FPS:** The rendering FPS and the backend processing FPS are hard-coupled. The `_run_loop()` processes a frame and immediately waits via `time.sleep()`, restricting backend performance to the Tkinter refresh capabilities.
6. **Error Handling:** Currently relies on standard stack traces; no graceful notification system for invalid MP4s or simulation failures.

## C. Proposed 2D Frontend Architecture

We must redesign the frontend to act as a pure view-controller over the backend application logic.

```text
                    FRONTEND (Tkinter or PyQt/PySide)
                       │
        ┌──────────────┼──────────────┐
        │              │              │
  Configuration     Runtime View    Results (BM1/BM2)
        │              │              │
        └──────────────┼──────────────┘
                       │
                 Application API (AppController)
                       │
        ┌──────────────┼──────────────┐
        │              │              │
  Simulation Loop  ConfigManager  BenchmarkManager
  (Async/Thread)       │              │
```

**Key Architectural Changes:**
* Move the simulation `while` loop out of `gui_controller.py` and into `app_controller.py` (or a dedicated `SimulationRunner` worker).
* The GUI will communicate via control events (`start()`, `stop()`, `pause()`).
* The backend worker will emit/publish `TrackerOutput` packets asynchronously to a thread-safe queue. The GUI will consume this queue at its own rendering rate (e.g., 30 FPS max), discarding stale frames to prioritize fresh telemetry while allowing the backend to process at >100 FPS if possible.

## D. Complete Feature Inventory

1. **Application Shell:** Main window, status bar, clean start/stop.
2. **Simulation Configuration Tabs:**
   * **Camera:** Resolution, FOV, Base Update Rate.
   * **Target:** Count, Shape, Size, Position, Motion Type.
   * **Disturbances:** Noise types, Atmospheric conditions, Jitter, Platform motion.
3. **2D Camera Feed (Core View):** Live feed, ROI overlay, target centroid, track crosshair, camera center reticle.
4. **Real-time Status Dashboard:** FPS, Tracking Error, Centroid RMSE, PTZ pan/tilt angles, Tracking State.
5. **Simulation Controls:** Start, Stop, Pause, Resume, Reset, Load/Save Scenario.
6. **MP4 (Benchmark-2) Mode:** File browser, video properties, track and playback, bypass PTZ.
7. **Scenario (Benchmark-1) Mode:** Batch scenario selector, batch progress bar.
8. **Results & Reporting View:** Summary scorecard generation, export JSON/Markdown buttons, PS compliance indicator.

## E. Backend Integration Map

| GUI Control / Feature | Frontend Handler | Backend Module | Contract / Result | Visualization |
| --------------------- | ---------------- | -------------- | ----------------- | ------------- |
| Config Form Submit | `_apply_config()` | `ConfigManager` | `SystemConfig` | Config Validation UI |
| Start Button | `_on_start()` | `AppController.start_sim()` | Async worker thread | Status Bar -> RUNNING |
| Camera Feed | `_render_frame()` | `SimulationEngine` / `FrameProvider` | `FramePacket` + `TrackerOutput` | `VisualizationEngine` BGR Canvas |
| Dashboard Stats | `_update_hud()` | `MetricsEngine` | `TrackerOutput` & `TelemetryRecord` | Text Labels |
| Select MP4 | `_browse_mp4()` | `SystemConfig.simulation` | File Path | Entry UI |
| Run Batch Benchmarks | `_run_benchmarks()` | `BenchmarkManager` | `GrandEvaluationSummary` | Results Data Grid |
| Generate Report | `_export_report()` | `LoggingEngine` | JSON / Markdown Files | Output Directory Prompt |

## F. 3D Integration Strategy

To ensure seamless integration of a future 3D renderer, we will utilize a unified **Visualization Model Contract**.

```python
class VisualizationState(BaseModel):
    # World Context
    target_world_position: Tuple[float, float, float]
    camera_world_position: Tuple[float, float, float]
    pan_angle_deg: float
    tilt_angle_deg: float
    camera_fov: float
    
    # 2D Context
    tracker_output: TrackerOutput
    raw_frame: FramePacket
```

* **How it works:** The backend simulation worker will emit this `VisualizationState` packet via a publish/subscribe mechanism or queue. 
* **Phase 5.10 (2D):** The `VisualizationEngine` will consume this packet, extracting only the 2D elements (`raw_frame`, `tracker_output`) to render the Canvas overlays.
* **Future (3D):** A Three.js/React (via IPC) or PyOpenGL layer will subscribe to the *exact same queue*, extracting `target_world_position`, `pan_angle_deg`, etc., to position a 3D gimbal and target sphere. No backend changes will be required.

## G. Implementation Sub-Phases

**Phase 5.10.1: Architecture Realignment**
* Objective: Decouple GUI from the simulation loop.
* Files: `gui_controller.py`, `app_controller.py`.
* Action: Move the while loop into a background thread in `AppController`. Implement a thread-safe frame/telemetry queue.

**Phase 5.10.2: Application Shell & Configuration UI**
* Objective: Build out all configurable parameter inputs.
* Files: `gui_controller.py` (or new modular UI files).
* Action: Add notebook tabs for Camera, Target, and Disturbances mapping to `SystemConfig`.

**Phase 5.10.3: Telemetry Dashboard & Simulation Controls**
* Objective: Provide real-time PS metrics.
* Action: Add sidebars for live tracking error, FPS, RMSE, and full Start/Stop/Pause/Reset controls.

**Phase 5.10.4: Evaluation & Reporting Workflows**
* Objective: Integrate Benchmark-1 and Benchmark-2 fully.
* Action: Add batch evaluation views, MP4 selectors, and report generation buttons mapped to `BenchmarkManager`.

## H. Testing & Acceptance Criteria

### GUI Unit Tests
* Validate that invalid configuration (e.g., negative FOV) displays an error and does not modify `SystemConfig`.
* Validate Start/Stop/Pause state transitions and button enabling/disabling.

### Integration Tests
* Prove that pressing Start triggers the backend simulation loop and successfully populates the visualization queue.

### End-to-End Acceptance Criteria
1. Launch app with `--gui`.
2. Modify Camera FOV via UI.
3. Press Start -> Camera feed renders live frames with correct tracking crosshairs.
4. Telemetry dashboard updates at ~30 FPS showing processing latency independently of rendering.
5. Press Stop -> Feed halts cleanly.
6. Switch to Benchmark-1 -> Select scenario -> Run -> View generated summary.

## I. Technology Recommendation

**Recommendation: PySide6 (Qt for Python)**

* **Why it fits:** The current Tkinter implementation is functional but limited in layout flexibility, styling, and complex widgets (like tables for results). PySide6 offers a highly professional, native desktop experience, integrates natively with Python, and supports high-performance rendering via `QGraphicsView` or `QOpenGLWidget`.
* **High-Frequency Updates:** PySide6 uses a robust Signals and Slots mechanism which easily handles cross-thread communication, ensuring high-speed backend telemetry can update the UI without blocking the main event loop.
* **3D Ready:** Qt provides built-in support for 3D integration (`Qt3D` or embedding OpenGL). We can easily transition to 3D later without rebuilding the application shell.
* **Migration Cost:** Low-Medium. We must rewrite `gui_controller.py` from Tkinter to Qt, but since the core backend logic is already decoupled, we only rewrite the view layer. 

*Note: React/Electron was considered but rejected due to the heavy serialization overhead required to stream live, uncompressed OpenCV NumPy arrays across a Python-Node IPC bridge at 60+ FPS.*

> [!IMPORTANT]
> **User Review Required:**
> Proceeding with PySide6 requires adding `PySide6` to our project dependencies. Do you approve of rewriting the Tkinter GUI into PySide6, or should we strictly expand the existing Tkinter implementation?

## J. Risks / Open Decisions

1. **PySide6 vs Tkinter:** Awaiting decision (see above).
2. **Video Playback Synchronization:** In Benchmark-2 (MP4 mode), keeping frame-by-frame processing synchronized with visualization can cause choppy playback if processing is slower than real-time. We must define whether MP4 mode runs "as fast as possible" or attempts real-time simulation.
3. **Cross-Platform Compatibility:** Ensure any new GUI framework behaves consistently across Windows (current target) and potential Linux evaluation environments.

## K. Definition of Done

* [ ] `gui_controller.py` rewritten/expanded to support the full Feature Inventory.
* [ ] Simulation `while` loop completely removed from the frontend UI classes.
* [ ] GUI processing rendering FPS is decoupled from backend tracker FPS.
* [ ] Live camera feed with full overlays functioning.
* [ ] Real-time telemetry dashboard functioning.
* [ ] MP4 (BM2) and Scenario (BM1) modes fully executable via GUI.
* [ ] Report generation executable from GUI.
* [ ] All automated E2E and UI tests passing.
