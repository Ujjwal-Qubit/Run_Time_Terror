# SIH 2026 Virtual Camera Tracking System — Performance Report

- **Run ID:** `run_1790716901`
- **Total Frames Processed:** `900`
- **Total Simulation Duration:** `29.97 s`
- **Mean Processing Throughput:** `461.8 FPS`

## 1. Compliance Scorecard (PS 26169 Thresholds)

| Metric | Specification | Measured Value | Compliance |
| :--- | :--- | :--- | :--- |
| **Acquisition Time** | $\le 2.0$ s | `0.07` s | **PASS** |
| **Tracking Error** | $\le 10.0$ px | `4.82` px (max: `144.72` px) | **PASS** |
| **Target Loss Rate** | $< 5.0\%$ | `0.00\%` | **PASS** |
| **Reacquisition Time** | $\le 1.0$ s | `N/A` s | **PASS** |
| **Processing Speed** | $\ge 20.0$ FPS | `461.8` FPS | **PASS** |

## 2. Accuracy & Sub-Pixel Localization

- **RMSE Centroiding Error (Rendered):** `0.000` px
- **RMSE Centroiding Error (Ideal):** `0.891` px
- **Mean Centroiding Error:** `0.000` px
- **Median Centroiding Error:** `0.000` px
- **Centroid Error $< 1$ px:** `100.0\%`
- **Centroid Error $< 2$ px:** `100.0\%`
- **Centroid Error $< 5$ px:** `100.0\%`

## 3. Tracking Continuity & Lock Retention

- **Lock Retention (Post-Acquisition):** `100.00\%`
- **Lock Retention (All Frames):** `99.78\%`
- **Lock Retention (When Visible):** `99.78\%`
- **Track Continuity Ratio:** `0.998`
- **Reacquisition Episodes:** `0`
- **Max Reacquisition Time:** `N/A` s

## 4. Latency Distribution (End-to-End Frame Processing)

- **Mean Latency:** `1.00` ms
- **Median (P50) Latency:** `0.88` ms
- **95th Percentile (P95):** `1.31` ms
- **99th Percentile (P99):** `1.75` ms
- **Max Frame Latency:** `46.57` ms

## 5. PTZ Camera Actuation

- **Steady-State Mean Error:** `4.82` px
- **Oscillation (Std Dev):** `7.421` px
- **Frames in Deadband:** `0.2\%`
