# 05 — Feature Inventory & Classification

**Date:** 2026-09-28  
**Scope:** Exhaustive inventory of every system feature discovered across source code, UI panels, APIs, configuration, and simulation.

---

## 1. Discovered Feature Inventory & Verdict Table

| # | Feature / Capability | Source Location | PS Requirement | Analytical Verdict | Rationale & Recommendation |
|---|---|---|---|---|---|
| **F-01** | 2D World Canvas Simulation | `src/simulation/scene_manager.py` | Row 1 (Screen $\ge 2000\times 2000$) | **KEEP / IMPROVE** | Clean, deterministic 2D canvas. Should be enhanced to allow textured background clutter and dynamic starfields. |
| **F-02** | Target Kinematic Motion | `src/simulation/target_manager.py` | Row 12 (Motion profiles) | **KEEP / IMPROVE** | Implements Straight Line, Circular, Figure-8, Random. **Must remove the $\pm 150\text{ px}$ center spawn cheat.** |
| **F-03** | Virtual Camera Viewport | `src/simulation/camera_model.py` | Rows 3–6 (Resolution & FOV) | **KEEP / IMPROVE** | Crops $640\times 480$ slice. Upgrade from flat pixel scaling to realistic pinhole camera matrix ($K$) and lens focal length. |
| **F-04** | Platform Angular Motion | `src/simulation/disturbance_engine.py` | Row 25 (Platform drift) | **KEEP / IMPROVE** | Implements sinusoidal linear drift. Should add multi-frequency harmonic orbital drift. |
| **F-05** | High-Frequency Camera Jitter | `src/simulation/disturbance_engine.py` | Row 23 (Jitter $\pm 20\text{ px}$) | **IMPROVE** | Currently white Gaussian noise. Should be shaped with reaction wheel vibration Power Spectral Density (PSD). |
| **F-06** | Sensor Noise Injection | `src/simulation/disturbance_engine.py` | Rows 21–22 (Gaussian/Poisson/S&P) | **KEEP** | Mathematically correct implementation of Poisson shot noise, Gaussian read noise, and impulse S&P noise. |
| **F-07** | Atmospheric Degradation | `src/simulation/disturbance_engine.py` | Row 24 (Haze/Fog/Rain/Low light) | **REBUILD** | Currently just `contrast * img + offset`. Should be upgraded to phase screen turbulence, beam wander, and scintillation. |
| **F-08** | Ground-Truth Firewall | `src/frame/data_contracts.py` | Mandatory Architecture | **KEEP** | Immaculate separation between truth and tracking. AST-verified leak-free. |
| **F-09** | MP4 Video Frame Ingestion | `src/frame/mp4_provider.py` | Benchmark 2 | **KEEP / IMPROVE** | Reliable OpenCV video stream decoder. Handles arbitrary resolution and framerate. |
| **F-10** | P0 Adaptive Threshold Detector | `src/tracker/detection_engine.py` | Expected Solution (Detection) | **KEEP / IMPROVE** | 3×3 median filter + box filter + connected components. Highly effective, running at $>600\text{ FPS}$. |
| **F-11** | Sub-Pixel Centroid Estimator | `src/tracker/centroid_estimator.py` | Expected Solution (Centroiding) | **KEEP** | Intensity-weighted centroiding with perimeter median background subtraction. Excellent accuracy ($<0.5\text{ px}$). |
| **F-12** | AI Candidate Classifier | `src/tracker/ai_classifier.py` | Expected Solution (AI) | **REPLACE / REMOVE** | **AI Theatre.** 4-feature Logistic Regression trained on 400 uniform random numbers. Replace with real learned CNN or clean classical gating. |
| **F-13** | Secondary AIML Models | `src/aiml/` | Expected Solution (AI) | **REMOVE** | 11-feature model and MLP trained on 30 synthetic examples, disabled by default. Dead weight. |
| **F-14** | Constant-Velocity Kalman Filter | `src/tracker/temporal_tracker.py` | Expected Solution (Tracking) | **KEEP / IMPROVE** | Solid 4-state Kalman filter with innovation gating. Upgrade to Extended Kalman Filter (EKF) or Interacting Multiple Model (IMM). |
| **F-15** | Tracking State Machine | `src/tracker/state_manager.py` | Tracking Lifecycle | **KEEP / IMPROVE** | 5-state FSM (SEARCHING, ACQUIRING, TRACKING, REACQUIRING, LOST). Works cleanly. |
| **F-16** | Proportional-Deadband PTZ | `src/control/ptz_controller.py` | Rows 13–14 (PTZ Gimbal) | **REBUILD** | **Fatal Flaw:** Outputs zero velocity when not in TRACKING. Must add active Archimedean spiral / raster acquisition search. |
| **F-17** | Objective Metrics Engine | `src/metrics/metrics_engine.py` | Evaluation Criteria | **KEEP** | Computes RMSE, lock retention, latency, FPS. Solid and honest. |
| **F-18** | Benchmark 1 Matrix (19 Scenarios) | `src/evaluation/matrix.py` | Benchmark Performance-1 | **KEEP / IMPROVE** | Automated scenario batch runner. Un-cheat scenario initial positions. |
| **F-19** | Benchmark 2 Video Evaluation | `src/evaluation/harness.py` | Benchmark Performance-2 | **IMPROVE** | Ingests MP4. Add automated beacon trajectory extraction when reference CSV is omitted. |
| **F-20** | "AI" Scenario Generator | `src/evaluation/ai_scenario.py` | Optional Feature | **REPLACE / SIMPLIFY** | Regex substring keyword matcher marketed as an "AI Interpretation Engine". Simplify to scenario preset generator. |
| **F-21** | Native PySide6 Desktop GUI | `src/app/gui/` | Deliverable 1 (Standalone App) | **KEEP & POLISH** | Single-executable, fast, native Qt GUI with HUD overlays and control panels. |
| **F-22** | 3D Visualization Viewport | `src/app/gui/view_3d.py` | GUI Enhancement | **KEEP / IMPROVE** | Software QPainter 3D projection. Zero crash risk. Renders gimbal cone and target LOS. |
| **F-23** | React 18 Web Dashboard | `frontend/` | Unofficial Add-on | **REMOVE / OPTIONAL** | Complete duplicate of Qt GUI. Requires separate Node/Vite build. Over-engineers a desktop hackathon project. |
| **F-24** | FastAPI REST/WebSocket Server | `src/api/server.py` | Unofficial Add-on | **REMOVE / OPTIONAL** | Exists only for web dashboard. Adds networking complexity and security vulnerabilities. |
| **F-25** | Dynamic Plugin Loader | `src/plugins/loader.py` | Architecture Flexibility | **SIMPLIFY** | Dynamic filesystem scanner and manifest validator for a single plugin. Replace with standard ABC inheritance. |
| **F-26** | Target Acquisition Scan Pattern | **MISSING** | Row 16 (Acquisition) | **MISSING (CRITICAL)** | Zero search pattern implemented. Gimbal halts when beacon is out of FOV. Must be added immediately. |
| **F-27** | Coarse-to-Fine Handoff Interface | **MISSING** | Background Domain PAT | **MISSING** | No boundary/handoff signal to Fast Steering Mirrors when beacon is centered within fine FOV ($\le 50\ \mu\text{rad}$). |
