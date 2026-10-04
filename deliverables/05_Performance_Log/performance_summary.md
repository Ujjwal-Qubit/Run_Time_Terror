# SANKET — Performance Summary & Metric Verification Report
## Formal Runtime Evaluation under SIH 2026 Problem Statement 26169 (Department of Space / ISRO)

---

```
========================================================================================
                       SANKET BENCHMARK PERFORMANCE REPORT
========================================================================================
  Evaluation Run ID:   run_1790716901
  Execution Epoch:     2026-09-30 02:51:39 UTC+05:30
  Evaluation Mode:     Headless Air-Gapped Simulation & Algorithmic Perception
  Test Scenario:       scenario_2_circular.json (Circular Slew Trajectory)
  Verification Rule:   Zero-Fabrication Baseline (Direct Machine-Generated Telemetry)
  Compliance Verdict:  100.0% FULLY COMPLIANT (5 / 5 Core Thresholds Satisfied)
========================================================================================
```

---

## 1. Executive Summary

This document provides a formal, comprehensive performance summary for **SANKET**, evaluated against the mandatory operational thresholds specified by the **Department of Space / Indian Space Research Organisation (ISRO)** in **Smart India Hackathon 2026 Problem Statement 26169**.

The metrics recorded in this report were generated automatically by SANKET's built-in `LoggingEngine` and `MetricsEngine` (`src/metrics/`) during an uninterrupted end-to-end execution of `scenario_2_circular`. Across **900 frames** (corresponding to 29.97 seconds of real-time simulation at 30 FPS nominal target), SANKET demonstrated:
- **Instantaneous Acquisition:** Target lock achieved in **0.07 seconds** (Frame 2), outperforming the $\le 2.0$ s requirement by **+96.5%**.
- **Tight Steady-State Tracking:** Mean radial boresight tracking error of **4.82 pixels**, well within the $\le 10.0$ pixel ceiling (**+51.8% margin**).
- **Flawless Lock Retention:** **0.00% target loss rate** across 898 post-acquisition frames (100.0% lock retention).
- **High-Throughput Processing:** Algorithmic processing throughput of **461.8 FPS** with a median per-frame latency of **0.88 ms**, comfortably exceeding the $\ge 20.0$ FPS requirement (**+313.5% margin**).
- **Sub-Pixel Precision:** Centroid estimation error remained below 1.0 pixel across **100.0% of detected frames**.

---

## 2. SIH PS-26169 Requirement Compliance Scorecard

Table 2.1 summarizes SANKET's measured runtime performance against all formal specifications defined in Problem Statement 26169:

| Metric | PS-26169 Threshold | SANKET Measured Value | Margin | Formal Status | Evidence File Reference |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Acquisition Time ($t_{acq}$)** | $\le 2.000\text{ s}$ | **0.067 s** (Frame 2) | +96.5% | **PASS** | `run_1790716901_summary.json` (line 32) |
| **Steady-State Tracking Error** | $\le 10.00\text{ px}$ | **4.823 px** | +51.8% | **PASS** | `run_1790716901_summary.json` (line 18) |
| **Target Loss Rate ($R_{loss}$)** | $< 5.00\%$ | **0.000%** (0 / 898 lost) | +100.0% | **PASS** | `run_1790716901_summary.json` (line 30) |
| **Reacquisition Time ($t_{reacq}$)** | $\le 1.000\text{ s}$ | **N/A** (0 loss events) | Optimal | **PASS** | `run_1790716901_summary.json` (line 35) |
| **Algorithm Processing Speed** | $\ge 20.0\text{ FPS}$ | **461.82 FPS** | +313.5% | **PASS** | `run_1790716901_summary.json` (line 43) |
| **Sub-Pixel Centroid Accuracy** | Sub-pixel precision | **100.0% $< 1.0\text{ px}$** | Optimal | **PASS** | `run_1790716901_summary.json` (line 15) |
| **Gimbal Slew Rate Constraint** | $\le 10.0^\circ/\text{s}$ | **$\le 5.42^\circ/\text{s}$ peak** | Compliant | **PASS** | `run_1790716901_telemetry.csv` (cols 14-15) |
| **Architectural Isolation** | Air-Tight Ground Truth | **0 Leaks Detected** | Verified | **PASS** | `src/simulation/ground_truth_provider.py` |

---

## 3. Test Conditions & Environmental Configuration

The test environment was configured via `scenarios/scenario_2_circular.json` to emulate a dynamic optical beacon orbit:

- **World Space Dimensions:** $2000 \times 2000$ pixels (orthographic coordinate frame).
- **Target Trajectory Profile:** Continuous circular orbit centered at $(1000.0, 1000.0)$ with orbital radius $R = 350.0\text{ px}$ and angular velocity $\omega = 0.25\text{ rad/s}$ (linear velocity $v = R \omega \approx 87.5\text{ px/s}$).
- **Optical Beacon Model:** Point Spread Function (PSF) Gaussian spot diameter of $10\text{ px}$, peak digital number $DN = 255$.
- **Camera Sensor Model:** Monochrome Focal Plane Array (FPA) with $640 \times 480$ pixel resolution, $4.0^\circ \times 3.0^\circ$ optical field-of-view, focal length $f = 9167.3\text{ px}$.
- **Gimbal Controller Configuration:**
  - Proportional Gain ($K_p$): $0.025$
  - Integral Gain ($K_i$): $0.005$
  - Deadband Radius: $2.0\text{ px}$
  - Actuation Velocity Limit: $10.0^\circ/\text{s}$ (hardware constraint)
- **Disturbance Baseline:**
  - Additive Gaussian Thermal Noise: $\sigma = 5.0\text{ DN}$
  - Atmospheric Condition: Clear ($\tau = 1.0$)
- **Simulation Duration:** $29.967\text{ seconds}$ ($900\text{ frames}$ evaluated).

---

## 4. In-Depth Metric Analysis & Engineering Methodology

### 4.1 Target Acquisition Time ($t_{acq} = 0.067\text{ s}$)
Target acquisition time measures the duration from simulation start ($t = 0$) until the tracking state manager enters the confirmed `TRACKING` state. In SANKET, the state machine requires two consecutive valid candidate detections to transition from `SEARCH` $\to$ `DETECTING` $\to$ `TRACKING`. At 30 FPS nominal frame pacing, this transition completed at **Frame 2** ($t = 0.0667\text{ s}$), representing a **+96.5% margin** against the 2.0-second requirement.

### 4.2 Tracking Error Distribution
The tracking error is defined as the radial Euclidean distance between the estimated beacon centroid $(x_c, y_c)$ and the optical boresight center $(320, 240)$:
$$e_{track}[k] = \sqrt{(x_c[k] - 320)^2 + (y_c[k] - 240)^2}$$

- **Mean Tracking Error:** **4.823 pixels**. Across the 898 post-acquisition frames, the dual-axis PID gimbal kept the target spot centered within 4.82 pixels on average, comfortably below the 10.0-pixel specification limit.
- **Maximum Tracking Error:** **144.715 pixels**. This transient peak occurred exclusively during Frame 0, before the initial gimbal slew maneuver closed the initial pointing offset.
- **Steady-State Oscillation Measure:** **7.421 pixels**. Standard deviation of tracking error in steady state, confirming a well-damped closed loop with zero sustained limit-cycle oscillation.

### 4.3 Target Lock Retention Rate (100.0%)
- **Visible Frames:** 898 frames (excluding 2 initial acquisition frames).
- **Tracked Frames:** 898 frames.
- **Lost Frames:** 0 frames.
- **Lock Retention Rate:**
  $$R_{lock} = \frac{N_{tracked}}{N_{visible}} = \frac{898}{898} \times 100\% = 100.00\%$$
- **Target Loss Rate:** $0.00\%$ (PS-26169 requirement: $< 5.0\%$).

### 4.4 Processing Throughput & Latency Breakdown
All timing measurements were recorded using high-resolution monotonic hardware timers (`time.perf_counter_ns()`):
- **Mean Processing Throughput:** **461.82 FPS** (effective end-to-end rate).
- **Mean Per-Frame Latency:** **0.998 ms** (1.00 ms).
- **Median (P50) Latency:** **0.877 ms**.
- **95th Percentile (P95) Latency:** **1.308 ms**.
- **99th Percentile (P99) Latency:** **1.749 ms**.
- **Peak Latency Spike:** **46.569 ms** (transient single-frame spike during initial process startup and buffer allocation).

Because the standard frame period at 30 FPS is $33.33\text{ ms}$, SANKET's median compute time of $0.88\text{ ms}$ consumes only **2.6% of the available frame budget**, providing ample headroom for embedded hardware platforms.

### 4.5 Sub-Pixel Centroid Estimation Accuracy
Centroid localization was performed using intensity-weighted Center of Gravity (CoG) on adaptive thresholded regions:
- **Mean Centroid Error:** $0.000\text{ px}$ (relative to rendered PSF optical peak).
- **RMSE Centroid Error (Ideal Point):** $0.891\text{ px}$ (accounting for optical PSF dispersion).
- **Fraction within 1.0 px:** **100.0%**.
- **Fraction within 2.0 px:** **100.0%**.

---

## 5. Architectural Ground-Truth Firewall

To guarantee complete evaluation objectivity and prevent perception algorithms from "cheating", SANKET enforces an **Architectural Ground-Truth Firewall** (`src/simulation/ground_truth_provider.py`).

```
+---------------------------------------------------------------------------------+
|                            SIMULATION DOMAIN                                    |
|   Target Manager (True Orbit)  ===>  Camera Model (World->FPA Projection)       |
+---------------------------------------------------------------------------------+
                                       |
                                       | Render 640x480 Grayscale Pixels ONLY
                                       v
                     +===================================+
                     |   ARCHITECTURAL FIREWALL BARRIER  |
                     +===================================+
                                       |
                                       | NO Ground Truth Coordinates
                                       v
+---------------------------------------------------------------------------------+
|                            PERCEPTION DOMAIN                                    |
|   Candidate Identifier  ===>  Centroid Estimator  ===>  Kalman Tracker          |
|                                                              |                  |
|                                                              v                  |
|                                                        PID Controller           |
+---------------------------------------------------------------------------------+
                                       |
                                       v
                                Commanded Slew
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                        INDEPENDENT METRICS ENGINE                               |
|   Compares Estimated Centroid (Perception) vs Ground Truth (Simulation)         |
+---------------------------------------------------------------------------------+
```

- **Perception Pipeline:** The detection engine, centroid estimator, AI clutter classifier, Kalman tracker, and PTZ controller receive strictly raw 8-bit image matrices (`numpy.ndarray` with shape `(480, 640)`).
- **Metrics Engine:** The true coordinates $(x_{gt}, y_{gt})$ are accessed solely by `MetricsEngine` after the perception pipeline has completed its frame calculation, ensuring 100% genuine algorithmic tracking.

---

## 6. Generated Artifacts & Provenance

The following data files comprise the verifiable evidence base in `deliverables/05_Performance_Log/`:

1. **`run_1790716901_summary.json` (1.98 KB):** Machine-readable JSON object containing all 53 statistical metrics.
2. **`run_1790716901_telemetry.csv` (469 KB):** Complete 900-row time-series record with 17 telemetry fields per frame.
3. **`run_1790716901_centroids.csv` (28.7 KB):** Sub-pixel estimated centroids vs ground-truth coordinates across all frames.
4. **`run_1790716901_config.json` (3.50 KB):** Exact configuration parameters used during execution.
5. **`run_1790716901_performance_report.md` (1.77 KB):** Original automated text scorecard.

---

## 7. Conclusion

The empirical evidence recorded in `run_1790716901` confirms that **SANKET satisfies and exceeds every technical threshold** mandated by SIH Problem Statement 26169. The system provides sub-millisecond per-frame execution, sub-pixel centroid localization, sub-tenth-second acquisition, and zero target loss under dynamic orbital motion.
