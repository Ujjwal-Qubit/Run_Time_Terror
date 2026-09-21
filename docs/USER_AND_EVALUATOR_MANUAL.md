# LumiTrack — FSOC Virtual Camera Tracking System
## Complete Evaluator and User Manual (SIH '26)

**Problem Statement:** Development of an AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile Free Space Optical Communication (FSOC) Terminals

---

## 1. Quick Start & Execution

### 1.1 Launching the Standalone Executable Application
LumiTrack is packaged as a standalone Windows executable (`dist/LumiTrack/LumiTrack.exe`) requiring zero Python installation.

```powershell
# Interactive GUI (2D Camera Feed + 3D Geometric Terminal + Telemetry HUD):
.\dist\LumiTrack\LumiTrack.exe --gui

# Or simply double-click:
run_lumitrack.bat
```

*(Alternatively, run from source: `python -m src.main --gui`)*

### 1.2 Running Benchmark 1 (BM1) — Closed-Loop Simulation
To execute automated batch evaluation across all production scenarios:
```powershell
# Standalone binary:
.\dist\LumiTrack\LumiTrack.exe --eval-scenarios scenarios

# From source:
python -m src.main --eval-scenarios scenarios
```
Outputs generated in `output/`:
- `output/batch_scenarios_<id>_grand_evaluator_report.md`
- `output/batch_scenarios_<id>_grand_summary.json`

### 1.3 Running Benchmark 2 (BM2) — Evaluator Video Processing with Reference Comparator
To evaluate external MP4 video recordings with PTZ bypass and automated comparison against ground-truth/reference coordinates:
```powershell
# Single MP4 evaluation with evaluator reference CSV:
.\dist\LumiTrack\LumiTrack.exe --mp4 path/to/video.mp4 --reference-csv path/to/reference.csv

# Batch MP4 directory evaluation:
.\dist\LumiTrack\LumiTrack.exe --eval-mp4s path/to/mp4_dir/ --reference-csv path/to/reference.csv
```

#### Evaluator Reference CSV Format
The external reference CSV must contain frame indices and true coordinates:
```csv
frame,true_x,true_y
0,320.00,290.00
1,327.00,289.00
...
```
*(Column headers `frame,x,y` are also supported).*
Outputs computed:
- **Centroid RMSE:** Sub-pixel localization root-mean-square error against reference coordinates.
- **Mean & Max Centroid Error:** Peak and average spatial deviation.
- **Frame Coverage (%):** Percentage of video frames with corresponding reference annotations.

### 1.4 Validating System Foundation & Running Test Suite
```powershell
# Validate architecture foundation contracts:
.\dist\LumiTrack\LumiTrack.exe --validate

# Run complete 255-test automated regression suite:
python -m pytest
```

---

## 2. Graphical User Interface (GUI) Guide

### Left Control Panel
- **Operation Mode:** Toggle between `Simulation (Benchmark 1)` and `MP4 Video (Benchmark 2)`.
- **Scenario Selector:** Browse and load any JSON scenario (auto-populates all config fields).
- **MP4 Selector:** Select external video files for frame-only evaluation.
- **Playback Controls:**
  - `Start`: Initializes the pipeline and begins real-time processing.
  - `Pause` / `Resume`: Temporarily suspends frame ingestion without resetting state.
  - `Stop`: Cleanly shuts down background worker threads and finalizes logging.
  - `Reset`: Flushes tracking filters, clears telemetry, and repositions camera to origin.
- **Reporting:**
  - `Run Batch Scenarios`: Executes unattended evaluation across a directory.
  - `Generate Report`: Finalizes metrics and produces markdown and JSON reports.

### Configuration Tabs
- **Camera:** Configure resolution (Width, Height), Field of View (FOV), and Base FPS.
- **Target:** Beacon size (px), target linear speed (px/s), and motion pattern (`STRAIGHT_LINE`, `CIRCULAR`, `FIGURE_8`, `RANDOM`).
- **Disturbances:**
  - Atmospheric conditions (`CLEAR`, `HAZE`, `FOG`, `RAIN`, `LOW_LIGHT`).
  - Sensor noise (`NONE`, `GAUSSIAN`, `POISSON`, `SALT_AND_PEPPER`).
  - Platform motion (`LINEAR`, `CIRCULAR`, `RANDOM`, `SPIRAL`, `FIGURE_8`) and amplitude.
  - Camera jitter enable and amplitude (px/frame).

### Center Visualization Viewport (Tabbed)
1. **2D Camera View:**
   - Raw sensor viewport with real-time HUD (Frame count, Tracking state, Alignment error, Latency, FPS, Pan/Tilt angles).
   - Adaptive tracking ROI box (Cyan).
   - Estimated beacon centroid crosshair (Red).
   - Ground truth marker (Green square, available in debug mode).
   - Center aiming reticle (White).
2. **3D Geometric Scene:**
   - Spatial ground grid and coordinate axes.
   - Virtual optical terminal pedestal.
   - Camera viewing frustum (3D pyramid) oriented with live pan/tilt angles.
   - Optical axis ray (dashed yellow).
   - Beacon position and breadcrumb trajectory trail.
   - Line-of-sight ray connecting aperture to beacon.
   - Interactive orbit (Left-click drag), Pan (Right-click drag), and Zoom (Scroll wheel).

### Bottom Telemetry Dashboard
- **Frame:** Monotonically increasing frame index.
- **State:** Live state machine state (`IDLE`, `SEARCHING`, `ACQUIRING`, `TRACKING`, `LOST`).
- **Lock Status:** Prominent status indicator (`LOCKED` in green, `ACQUIRING` in yellow, `UNLOCKED` in red).
- **Tracking Error:** Euclidean pixel distance from optical axis to target centroid.
- **Centroid Coordinates:** Sub-pixel centroid coordinates $(x, y)$.
- **PTZ Angles:** Real-time camera Pan and Tilt angles in degrees.
- **FPS & Latency:** Decoupled processing speed and end-to-end latency per frame.

---

## 3. Architecture & Core Algorithms

### 3.1 Strict Ground-Truth Firewall
In compliance with the Problem Statement and Operating Contract:
- **`IFrameProvider`** forms a strict barrier between simulation and tracking.
- The tracking engine, detector, centroid estimator, and candidate identifier **never receive Ground Truth**.
- In MP4 mode (BM2), simulation models (`SceneManager`, `TargetManager`, `CameraModel`, `DisturbanceEngine`, `GroundTruthProvider`) are not instantiated (`None`).

### 3.2 Proportional-Integral (PI) Anti-Windup PTZ Controller
Eliminates steady-state velocity lag during continuous beacon motion:
$$\Delta \theta_p = K_p \cdot e_x + K_i \cdot \int e_x \, dt, \quad \Delta \theta_t = - (K_p \cdot e_y + K_i \cdot \int e_y \, dt)$$
Features:
- Integral anti-windup clamping to prevent overshoot during acquisition.
- 95% integral decay inside the deadband to avoid hunting.
- Dynamic rate limiting to enforce user-configured pan/tilt speed limits ($5^\circ/\text{s} - 10^\circ/\text{s}$).

### 3.3 Sub-Pixel Intensity Centroiding
Computes beacon center using background-subtracted intensity weighting:
$$x_c = \frac{\sum_i (I_i - B) x_i}{\sum_i (I_i - B)}, \quad y_c = \frac{\sum_i (I_i - B) y_i}{\sum_i (I_i - B)}$$
Achieves sub-pixel precision ($RMSE \le 0.03\text{ px}$).

### 3.4 Robust Percentile-Based Noise Estimation
In cropped ROIs, standard deviation of difference is computed on the lower 75th percentile:
$$p_{75} = \text{Percentile}_{75}(\text{diff}), \quad \sigma = \text{std}(\text{diff} \le p_{75})$$
Prevents bright targets from self-masking in tight ROIs, allowing seamless tracking of target sizes from $5\times 5$ to $20\times 20\text{ px}$.

### 3.5 AI Candidate Classifier
Lightweight logistic regression inference over a 4D feature vector:
$$\mathbf{x} = [\text{peak\_intensity}, \text{local\_contrast}, \text{compactness}, \text{aspect\_ratio}]$$
Discriminates compact, high-contrast beacons from irregular clutter streaks with $< 0.01\text{ ms}$ inference time.

---

## 4. Verification & Experimental Evidence

### 4.1 Benchmark 1 (BM1) Closed-Loop Production Batch Results
Evaluated over all 4 standardized production scenarios (3,600 frames total) via standalone executable `LumiTrack.exe`:
- **Processing Frame Rate:** 75.0 FPS (PS Requirement: $\ge 20.0$ FPS) -> **PASS**
- **Target Acquisition Time:** 0.07 s (PS Requirement: $\le 2.00$ s) -> **PASS**
- **Mean Tracking Alignment Error:** 3.54 px (PS Requirement: $\le 10.0$ px) -> **PASS**
- **Target Loss Rate:** 0.00% (PS Requirement: $< 5.0\%$) -> **PASS**
- **Ground Truth Centroid RMSE:** 0.028 px
- **Mean End-to-End Latency:** 4.48 ms (P95: 8.06 ms)

### 4.2 Benchmark 2 (BM2) Evaluator Video & Reference Comparator Results
Evaluated on synthetic MP4 video with external evaluator reference CSV (`frame,true_x,true_y`):
- **Processing Speed:** 455.9 FPS (Batch) / 272.6 FPS (Single) -> **PASS**
- **Centroid RMSE vs. Evaluator Reference:** 0.278 px (Sub-pixel accuracy) -> **PASS**
- **Mean Centroid Error:** 0.077 px (Max: 1.297 px)
- **Reference Frame Coverage:** 100.0% (60/60 frames matched)
- **Ground Truth Firewall:** Verified 100% isolation; simulation models `None`, PTZ actuation bypassed.

### 4.3 Default Out-of-the-Box Configuration (Zero Scenario JSON)
Evaluated with system defaults ($K_p = 8.0, K_i = 2.0, \text{deadband} = 1.0\text{ px}$):
- **Straight Line Motion:** 4.58 px tracking error, 0.00% loss -> **PASS**
- **Circular Motion:** 5.86 px tracking error, 0.00% loss -> **PASS**
- **Figure-8 Motion:** 6.39 px tracking error, 0.00% loss -> **PASS**
- **Random Walk Motion:** 6.96 px tracking error, 0.00% loss -> **PASS**

### 4.4 Comprehensive 24-Test Robustness Campaign
Executed across 6 experimental dimensions (Target Size, Motion Pattern, Sensor Noise, Atmosphere, Disturbances, Progressive Stress):
- **Tracking Error Compliance ($\le 10.0$ px):** 24/24 runs (100.0%) -> **PASS**
- **Frame Rate Compliance ($\ge 20.0$ FPS):** 24/24 runs (100.0%, range: 21.8 - 439.4 FPS) -> **PASS**
- **Acquisition Time Compliance ($\le 2.0$ s):** 24/24 runs (100.0%, 0.067 s nominal) -> **PASS**
- **Target Loss Rate ($< 5.0\%$):** 24/24 runs (0.00% loss across all tests) -> **PASS**

### 4.5 Automated Regression Test Suite
- **Total Tests:** 255 collected
- **Results:** 255 passed, 0 failed, 0 errors, 0 skipped (100.0% pass rate in 10.64s)
