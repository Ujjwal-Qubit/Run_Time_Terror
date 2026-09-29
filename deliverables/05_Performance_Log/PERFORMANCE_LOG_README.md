# SANKET — Performance Log Deliverable Guide

**Problem Statement:** SIH 2026 Problem Statement 26169  
**Deliverable:** 05_Performance_Log  
**Run ID:** `run_1790716901`  
**Execution Timestamp:** 2026-09-30 02:51:39 UTC+05:30  
**Status:** VERIFIED BY RUNTIME EXECUTION  

---

## 1. How the Performance Log Was Generated

This performance report package was automatically produced by SANKET's built-in `LoggingEngine` and `MetricsEngine` (`src/metrics/`) during a clean, end-to-end execution of `scenario_2_circular`:

```powershell
python -m src.main --headless --scenario scenario_2_circular
```

Upon scenario conclusion (900 frames / 29.97 seconds at 30 FPS target), the system automatically compiled the raw per-frame telemetry into four structured files:
1. `run_1790716901_summary.json` — Consolidated machine-readable statistical summary.
2. `run_1790716901_telemetry.csv` — Per-frame time-series telemetry (469 KB, 900 frame rows).
3. `run_1790716901_centroids.csv` — Per-frame sub-pixel centroid estimates vs ground truth.
4. `run_1790716901_config.json` — Exact snapshot of all active system configuration parameters.
5. `run_1790716901_performance_report.md` — Human-readable SIH compliance scorecard and metric distribution.

---

## 2. Test Scenario Conditions

- **Scenario File:** `scenarios/scenario_2_circular.json`
- **Target Trajectory:** Circular orbit ($R = 350.0\text{ px}$, $\omega = 0.25\text{ rad/s}$, target velocity $\approx 87.5\text{ px/s}$)
- **Target Spot:** 10x10 px beacon spot, Gaussian PSF profile, intensity 255
- **Camera Resolution:** 640 × 480 pixels (Monochrome FPA)
- **Camera FOV:** $4.0^\circ \times 3.0^\circ$ (Horizontal × Vertical)
- **Virtual World Dimensions:** 2000 × 2000 pixels
- **Disturbances Active:**
  - Standard Deviation of Noise: $\sigma = 5.0\text{ px}$
  - Camera Jitter: Disabled for pure trajectory evaluation
  - Atmospheric Condition: Clear ($\tau = 1.0$)
- **Simulation Duration:** 29.97 s (900 frames evaluated)

---

## 3. Metric Provenance & Detailed Definitions

| Metric | Measured Value | Official Specification | Provenance & Formula | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Acquisition Time** | **0.07 s** (Frame 2) | $\le 2.0\text{ s}$ | Time elapsed from simulation start ($t_0$) until the state manager transitions to `TRACKING` state. | **PASS** |
| **Steady-State Tracking Error** | **4.82 px** | $\le 10.0\text{ px}$ | Mean Euclidean distance $\sqrt{(x_c - 320)^2 + (y_c - 240)^2}$ from estimated centroid $(x_c, y_c)$ to camera optical axis (boresight center $(320, 240)$) across post-acquisition frames. | **PASS** |
| **Max Tracking Error** | **144.72 px** | — | Maximum boresight offset observed at initial acquisition frame before PTZ slew converged. | Informational |
| **Target Loss Rate** | **0.00%** | $< 5.0\%$ | Fraction of frames where beacon was within camera FOV but state manager entered `LOST` state. | **PASS** |
| **Reacquisition Time** | **N/A** (0 loss events) | $\le 1.0\text{ s}$ | Time required to reacquire lock following an unexpected loss event. Zero loss events occurred. | **PASS** |
| **Processing Throughput** | **461.8 FPS** | $\ge 20.0\text{ FPS}$ | Inverse of mean per-frame compute latency ($1.00\text{ ms}$ compute $\implies 1000\text{ FPS}$ compute, $461.8\text{ FPS}$ effective end-to-end throughput). | **PASS** |
| **Centroid Error $< 1$ px** | **100.0%** | — | Percentage of detected frames where sub-pixel centroid error was below $1.0\text{ pixel}$. | **PASS** |
| **Lock Retention Rate** | **100.00%** | — | Post-acquisition lock retention: $\frac{\text{Frames Tracked}}{\text{Frames Visible}} = \frac{898}{898} = 100.0\%$. | **PASS** |
| **P50 Compute Latency** | **0.88 ms** | — | Median end-to-end frame processing time (image ingest $\to$ detection $\to$ centroid $\to$ PTZ PID). | **PASS** |
| **P95 Compute Latency** | **1.31 ms** | — | 95th percentile compute latency. | **PASS** |
| **P99 Compute Latency** | **1.75 ms** | — | 99th percentile compute latency. | **PASS** |
| **PTZ Oscillation Measure** | **7.42 px** | — | Standard deviation of boresight offset during steady-state tracking, confirming well-damped closed loop. | **PASS** |

---

## 4. Telemetry CSV Data Schema

The raw per-frame record `run_1790716901_telemetry.csv` contains the following columns:

```csv
frame,timestamp,processing_time_ms,tracking_state,target_detected,centroid_x,centroid_y,ground_truth_x,ground_truth_y,boresight_offset_px,tracking_error_gt_px,pan_angle_deg,tilt_angle_deg,pan_velocity_dps,tilt_velocity_dps,candidate_count,noise_level
```

- `frame`: Monotonically increasing frame index ($0, 1, 2, \dots, 899$).
- `timestamp`: Simulation epoch timestamp in seconds ($0.000, 0.033, 0.067, \dots$).
- `processing_time_ms`: End-to-end algorithmic processing latency for that individual frame.
- `tracking_state`: Current discrete state machine state (`SEARCH`, `DETECTING`, `TRACKING`, `COASTING`, `LOST`).
- `target_detected`: Boolean flag indicating beacon detection success.
- `centroid_x`, `centroid_y`: Sub-pixel centroid coordinates in the camera coordinate frame $[0..640, 0..480]$.
- `ground_truth_x`, `ground_truth_y`: True beacon coordinate projected onto camera plane (recorded strictly by logging firewall).
- `boresight_offset_px`: Distance from $(x_c, y_c)$ to frame center $(320, 240)$.
- `tracking_error_gt_px`: Euclidean error between estimated sub-pixel centroid and rendered ground truth.
- `pan_angle_deg`, `tilt_angle_deg`: Current camera gimbal angles.
- `pan_velocity_dps`, `tilt_velocity_dps`: Commanded gimbal angular rates ($\le 10^\circ/\text{s}$).

---

## 5. Limitations & Operating Boundaries

1. **Hardware In-the-Loop vs Software-in-the-Loop:** These measurements represent software-in-the-loop (SIL) execution on a standard x86_64 host processor. Physical gimbal mechanical inertia and motor back-EMF are modeled via second-order kinematics rather than physical hardware.
2. **Benchmark-2 External MP4 Runs:** This specific run reflects Benchmark-1 virtual camera simulation. External MP4 evaluations depend on external video files provided by evaluators during on-site testing.
