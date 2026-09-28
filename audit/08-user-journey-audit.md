# 08 — User Journey & Operational Workflow Audit

**Date:** 2026-09-28  
**Discipline:** UX / Product Researcher (`deterministic-design`)  
**Scope:** Human-Computer Interaction, Operational Workflows, and Evaluator Experience

---

## 1. User Personas & Core Workflows

### Persona A: The SIH Evaluator / ISRO Judge
- **Goal:** In 10–15 minutes, verify:
  1. Functional operational success (camera tracks moving beacon).
  2. Benchmark Performance 1 (runs standard scenarios, produces centroid error log).
  3. Benchmark Performance 2 (bypasses PTZ, loads custom `.mp4` video, verifies RMSE and FPS).
  4. Understand algorithm architecture and innovation.
- **Pain Points & Friction Points in Current System:**
  - **Which UI do I run?** The repository provides `run_lumitrack.bat` (PySide6 Desktop) and `run_web.bat` (FastAPI Web Server). There is no single unified entry point.
  - **Web Launch Failure:** Running `run_web.bat` starts the FastAPI backend, but navigating to `http://localhost:8000` serves a 404 unless `frontend/dist` has been compiled via `npm run build`. Evaluators lacking Node.js will fail immediately.
  - **BM2 Reference Truth Confusion:** If an evaluator provides an MP4 video without an accompanying CSV ground truth, the UI displays `N/A` for RMSE, leaving them unsure whether the tracker succeeded.
  - **Silent Gimbal Freeze:** If an evaluator increases target speed beyond $80\text{ px/s}$ or starts the camera away from the target, the camera halts with zero explanatory feedback.

### Persona B: The Algorithm Researcher / Optical Engineer
- **Goal:** Rapidly prototype and benchmark novel optical tracking algorithms against disturbances.
- **Pain Points & Friction Points in Current System:**
  - **Heavy Scaffolding:** To test a simple tracking algorithm, the developer must implement `ITrackingAlgorithm`, craft a `manifest.json`, define public data contract bridges, and run it through `PluginLoader`.
  - **Tuning Visibility:** The UI does not provide live innovation residual plots ($y_k = z_k - H \hat{x}_{k|k-1}$) or Kalman covariance error ellipses, making it hard to diagnose filter divergence.

---

## 2. Walkthrough: The Evaluator's 10-Minute Assessment

```text
[Step 1: Application Launch]
  Desktop GUI (`run_lumitrack.bat`) opens cleanly in < 2 seconds.
  Immediate visual: 2D HUD sensor view, Control panel on left, Telemetry on right.
  Rating: EXCELLENT (Desktop) / POOR (Web requires Node.js)

[Step 2: Interactive Tracking Run]
  Evaluator selects "Circular", clicks "Start".
  Target orbits in center, camera pans/tilts smoothly, green lock box stays pinned.
  Centroid error displayed as 1.2 px, Latency 1.8 ms, FPS 30.
  Rating: HIGH VISUAL QUALITY & POLISH

[Step 3: Stress Testing (The Trap)]
  Evaluator sets initial camera position to (200, 200) while target is at (1000, 1000).
  Result: Camera viewport shows black noise. Gimbal does NOT move. Tracker reports "SEARCHING".
  System remains completely dead until reset.
  Rating: CRITICAL WORKFLOW FAILURE

[Step 4: Benchmark Performance 1 (Matrix Run)]
  Evaluator clicks "Run Benchmark Matrix (CORE)".
  System runs 6 scenarios headless in 4 seconds.
  Automatically generates clean Markdown scorecard in output/matrix/.
  Rating: EXCELLENT AUTOMATION & DEMONSTRABILITY

[Step 5: Benchmark Performance 2 (External MP4)]
  Evaluator selects an MP4 video file. PTZ gimbal controls are correctly disabled.
  Video plays at 30 FPS, green tracking box follows the beacon spot.
  Scorecard outputs Mean FPS = 420 FPS, Loss Rate = 0.0%, RMSE = "N/A" (Rule 6).
  Rating: ROBUST & COMPLIANT
```

---

## 3. UX Recommendations for the Ideal System
1. **Kill the Dual-Frontend:** Retire the web application and consolidate 100% of effort into the PySide6 standalone desktop application.
2. **Add Search State Animation & Explanation:** When in `SEARCHING` or `LOST` state, display an active scanning HUD overlay ("EXECUTING ARCHIMEDEAN SPIRAL ACQUISITION SCAN").
3. **Auto-Extract Baseline Truth for BM2:** Provide an optional "Self-Reference Optical Flow / High-SNR Peak Centroid" baseline for MP4 videos lacking external CSV files, so evaluators can visually compare relative centroid error.
