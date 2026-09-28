# 03 — Problem Statement Traceability Analysis

**Date:** 2026-09-28  
**Scope:** Forensic Traceability of SIH 26169 Problem Statement Table (Rows 1–25) and Evaluation Stages (1–4) through Requirements, Architecture, Implementation, and Testing.

---

## 1. Traceability Matrix: Specification to Implementation & Evidence

| PS Row | Specification Limit | System Feature | Implementation Module | Test Case | Evidence Status | Finding & Broken Traceability |
|---|---|---|---|---|:---:|---|
| **1** | Screen Size $\ge 2000 \times 2000\text{ px}$ | Scene Canvas | `SceneManager.py` | `test_req1_virtual_scene_minimum_2000x2000` | **Broken Test** | Code creates 2000×2000 canvas. Test only asserts `hasattr(cfg, 'camera')` and `width > 0`. |
| **2** | Monochrome Camera (FPA) | Grayscale output | `SceneManager.py` | `test_req2_monochrome_grayscale_output` | **Broken Test** | Test literally greps for string `"uint8"` in python source. |
| **3** | Camera Resolution $640 \times 480$ | Viewport cropping | `CameraModel.py` | `test_req3_camera_resolution_640x480` | **Verified** | Viewport is extracted as $640 \times 480$ slice. |
| **4** | Camera FOV $4^\circ \times 3^\circ$ | Angular projection | `CameraModel.py` | `test_req4_camera_fov_user_defined` | **Verified** | Configurable, defaults to $4^\circ \times 3^\circ$. |
| **5** | Update Rate $\ge 30\text{ Hz}$ | Simulation loop clock | `SimulationWorkerThread.py` | `test_req5_camera_update_rate_30hz_minimum` | **Verified** | Base clock is 30 Hz. |
| **6** | Initial Camera Pos: Center | Camera reset pose | `CameraModel.py` | `test_req6_initial_camera_position_center` | **Broken Test** | Test only asserts `assert ptz is not None`. |
| **7** | Target Type: Beacon Spot | Patch compositing | `TargetManager.py` | `test_req7_target_type_beacon_spot` | **Broken Test** | Test only asserts `hasattr(cfg, 'target')`. |
| **8** | Target Count: $\ge 1$ mandatory | Single / Multi target | `TargetManager.py`, `MultiBeaconManager` | `test_req8_minimum_one_target` | **Broken Test** | Test only asserts `hasattr(cfg.target, 'size')`. |
| **9** | Target Shape: Square default | Patch generator | `TargetManager._generate_patch` | `test_req9_target_shape_user_defined` | **Broken Test** | Test only asserts `cfg.target.size > 0`. |
| **10** | Target Size: $5\text{--}20\text{ px}$ | Patch size parameter | `TargetManager.py` | `test_req10_target_size_5_to_20_pixels` | **Verified** | Bounds check `5 <= size <= 20` enforced in constructor. |
| **11** | Initial Location: Random / Center | Target initialization | `TargetManager._init_kinematics` | `test_req11_target_location_user_defined` | **Broken Logic** | Target spawn clamped to center $\pm 150\text{ px}$, forcing initial in-FOV presence. |
| **12** | Motion: Straight, Circle, Fig-8, Random | Kinematic generator | `TargetManager.step()` | `test_req12_motion_types_four_minimum` | **Verified** | Implements all 4 mandatory profiles + spiral + sinusoidal. |
| **13** | Max Pan Speed: $5\text{--}10^\circ/\text{s}$ | Slew rate clamp | `PTZController.compute()` | `test_req13_max_pan_speed_user_defined` | **Broken Test** | Clamped in controller. Test only asserts `assert ptz is not None`. |
| **14** | Max Tilt Speed: $5\text{--}10^\circ/\text{s}$ | Slew rate clamp | `PTZController.compute()` | `test_req14_max_tilt_speed_user_defined` | **Broken Test** | Clamped in controller. Test only asserts `assert ptz is not None`. |
| **15** | Update Interval $\ge 20\text{ Hz}$ | PTZ update rate | `PTZController.py` | `test_req15_update_interval_20hz_minimum` | **Verified** | Evaluated at frame rate ($\ge 20\text{ Hz}$). |
| **16** | Acquisition Time $\le 2\text{ s}$ | State transition timing | `TrackingStateManager.py` | `test_req16_acquisition_time_le_2s` | **Broken Feature** | Trivially $\le 0.033\text{ s}$ because target spawns inside FOV. If spawned outside FOV, acquisition NEVER occurs (inf). |
| **17** | Tracking Error $\le 10\text{ px}$ | Centroid RMSE | `MetricsEngine.py` | `test_req17_tracking_error_le_10px` | **Verified** | Measured RMSE is $\sim 1\text{--}3\text{ px}$ under nominal tracking. |
| **18** | Target Loss Rate $< 5\%$ | Loss frame ratio | `MetricsEngine.py` | `test_req18_target_loss_lt_5_percent` | **Verified** | Measured loss rate is $0.0\%$ on standard matrix. |
| **19** | Reacquisition Time $\le 1\text{ s}$ | Reacquisition timer | `TrackingStateManager.py` | `test_req19_reacquisition_time_le_1s` | **Broken Test** | Test only asserts `assert "reacquisition_time_s" in fields`! |
| **20** | Processing Speed $\ge 20\text{ FPS}$ | Pipeline latency | `app_controller.py`, `baseline_tracker.py` | `test_baseline_plugin_processing_speed` | **Verified** | Exceeds $400\text{ FPS}$ in headless mode; $>30\text{ FPS}$ with GUI. |
| **21** | Noise: Gaussian, Poisson, S&P | Image noise generator | `DisturbanceEngine.py` | `test_gaussian_noise_enabled_and_disabled` | **Verified** | All 3 noise types implemented via NumPy. |
| **22** | Noise Std Dev $\le 20\text{ px}$ | Gaussian sigma clamp | `DisturbanceEngine.py` | `test_gaussian_noise_enabled_and_disabled` | **Verified** | Sigma clamped to $\le 20.0$. |
| **23** | Camera Jitter $\pm 20\text{ px/frame}$ | Frame-to-frame offset | `DisturbanceEngine.compute_camera_jitter` | `test_jitter_ps_limit_enforced` | **Verified** | Sampled from Gaussian and clamped to $\pm 20\text{ px}$. |
| **24** | Atmospheric: Clear, Haze, Fog, Rain, Low-light | Contrast & brightness offset | `DisturbanceEngine.apply_atmospheric_degradation` | `test_atmospheric_degradation_modes` | **Verified (Simple)** | Implemented as linear pixel scale and bias. |
| **25** | Platform Motion $\pm 20\text{ px/frame}$ | Sinusoidal / linear drift | `DisturbanceEngine.compute_platform_motion` | `test_platform_motion_ps_limit_enforced` | **Verified** | Clamped to $\pm 20\text{ px/frame}$. |

---

## 2. Forensic Breakdown of Broken Traceability Chains

### Case 1: Target Acquisition Scan (Row 16) — Broken Chain
- **Requirement:** System must acquire target within $\le 2\text{ s}$.
- **Operational Reality:** In PAT, the beacon can appear anywhere in the uncertainty zone.
- **Implementation:** `TargetManager` restricts target spawn to center $\pm 150\text{ px}$. The camera viewport is $640 \times 480$, centered at $(1000, 1000)$. The target is ALWAYS inside the FOV on frame 0.
- **Defect:** `PTZController` commands `delta_pan = 0, delta_tilt = 0` whenever state is `SEARCHING` or `LOST`.
- **Consequence:** If the target starts outside the FOV, the system has **infinite acquisition time** and never finds it.

### Case 2: Reacquisition Verification (Row 19) — Broken Test
- **Requirement:** Reacquisition time $\le 1.0\text{ s}$ following occlusion.
- **Test in Code:** `test_phase6_8_sih_validation.py:258` asserts:
  ```python
  fields = {f.name for f in dataclasses.fields(EvaluationRunResult)}
  assert "reacquisition_time_s" in fields
  ```
- **Consequence:** The test passes without running a simulation, verifying only that a dataclass has a variable named `reacquisition_time_s`.

### Case 3: "AI-Based" Claim vs. Codebase Reality — Broken Capability
- **Requirement:** "Development of an AI-Based Virtual Camera Tracking System".
- **Claimed in Documentation:** "Deep learning candidate classification", "AI-assisted tracking", "Kalman-CNN".
- **Reality in Code:**
  1. `AIClassifier` is a 4-feature Logistic Regression trained on 400 uniform random numbers.
  2. The 11-feature candidate classifier and 2-layer residual MLP in `src/aiml/` were trained on 30 examples and are **disabled by default** (`_aiml_candidate_enabled = False`, `_aiml_temporal_enabled = False`).
  3. The "AI Scenario Generator" is a regex substring matcher (`if "spiral" in prompt: ...`).
- **Consequence:** Evaluators inspecting the model will discover that the tracking system is 100% classical computer vision and heuristic gating, with cosmetic AI wrappers.

### Case 4: Dual Frontend Redundancy — Broken System Purpose
- **Deliverable Requirement:** "A standalone executable application implementing the complete virtual camera tracking system".
- **Implementation:**
  - Full PySide6 Desktop GUI (`src/app/gui/`).
  - Full React 18 / Vite / Three.js Web Dashboard (`frontend/`).
  - Full FastAPI REST & WebSocket server (`src/api/server.py`).
- **Consequence:** Doubled maintenance overhead, dependency fragmentation (Python + Node.js), and packaging friction for zero judging criteria gain.
