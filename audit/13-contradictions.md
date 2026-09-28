# SIH 26169 — Repository Contradictions & Reality Gaps Audit

**Document ID**: `AUDIT-13-CONTRADICTIONS`  
**Target Repository**: `Ujjwal-Qubit/Run_Time_Error` (SIH 26169 Coarse Alignment FSOC)  
**Status**: COMPLETE / FORENSIC VERIFIED  
**Auditor**: Antigravity First-Principles Reconnaissance

---

## 1. Executive Summary

This forensic audit exposes the deep, systemic contradictions between what the codebase and its documentation *claim* to achieve versus what is *actually implemented* in executable Python and JavaScript code.

---

## 2. Table of Systemic Contradictions

| # | Stated Claim / Marketing Documentation | Concrete Codebase Reality | Severity | Evidence Location |
| :--- | :--- | :--- | :--- | :--- |
| **C1** | **"AI-Powered Deep Tracking System"**: System leverages machine learning to track FSOC laser terminals. | The active tracking pipeline is **100% classical OpenCV**: `cv2.threshold` + `cv2.findContours` + `cv2.moments` + standard linear Kalman Filter. The secondary ML model in `src/aiml/` is **explicitly disabled by default** (`_aiml_candidate_enabled = False`). | **CRITICAL** | `src/tracker/baseline_tracker.py:112-114` |
| **C2** | **"Autonomous Acquisition $\le 0.033\text{ s}$"**: Claims instant target acquisition compliant with ISRO PS Row 1. | System **commands zero pan/tilt velocity** when target is outside FOV. The $0.033\text{ s}$ metric is achieved purely because the simulator spawns the target inside the camera's $640 \times 480$ field of view. True acquisition time for an out-of-FOV target is $\infty$. | **CRITICAL** | `src/control/ptz_controller.py:184-205`; `scratch/test_acquisition_out_of_fov.py` |
| **C3** | **"Standalone Offline Windows Desktop Solution"**: Meets ISRO deliverable format of a self-contained `.exe`. | Massive engineering effort was diverted into a React 18 + Vite + Three.js web app (`frontend/`) and FastAPI backend (`src/api/server.py`), creating a heavy Node.js dependency. | **HIGH** | `frontend/package.json`; `src/api/server.py` |
| **C4** | **"Rigorous Ground-Truth Firewall"**: AST static analysis prevents information leakage from simulator to tracker. | While the AST static analysis prevents coordinate leakage, the simulation is so trivialized (white Gaussian blob on black canvas) that the tracker needs no external assistance to find the brightest blob. | **MEDIUM** | `src/evaluation/firewall.py`; `tests/test_firewall_ast.py` |
| **C5** | **"Atmospheric Turbulence & Scintillation Simulation"**: Implements physical atmospheric degradation. | The "turbulence" model is simply `cv2.GaussianBlur` with kernel size $\propto C_n^2$, and "scintillation" is additive white Gaussian noise. Wavefront phase distortion, speckle breakdown, beam wander, and log-normal fades are absent. | **HIGH** | `src/simulator/optical_simulator.py:130-165` |
| **C6** | **"Natural Language AI Scenario Engine"**: System uses AI to interpret natural language testing prompts. | The engine is 20 lines of basic Python regex substring searches (`re.search(r"spiral", prompt)`). There is no NLP model, LLM, or semantic parser. | **HIGH** | `src/evaluation/ai_scenario.py:45-75` |
| **C7** | **"454 / 454 Tests Passing (100% Rigorous Compliance)"**: All 25 PS requirements rigorously tested. | Tests for PS rows 13, 14, 19, etc., are tautological: they check dictionary keys (`"reacquisition_time_s" in fields`), object instantiation (`ptz is not None`), or source string matching (`"uint8" in src`). | **CRITICAL** | `tests/test_ps_requirements.py:145-210` |
| **C8** | **"Extensible Dynamic Plugin Framework"**: Production-grade modularity for third-party detectors. | The repository contains exactly one trivial dummy plugin. The plugin framework adds abstract indirection without any functional use. | **LOW** | `src/plugin/dummy_plugin.py` |

---

## 3. Deep-Dive: Contradiction C1 (The "AI" Mirage)

In the project README, presentations, and test suites, the project is described as an **"AI-Based Virtual Camera Tracking System"**.

However, inspecting `src/tracker/baseline_tracker.py`:
```python
# Lines 110-116
self._aiml_candidate_enabled = False  # ML candidate classifier DISABLED
self._aiml_temporal_enabled = False   # Temporal MLP DISABLED

# Lines 215-230: The actual active candidate extraction
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
_, thresh = cv2.threshold(gray, self.threshold_val, 255, cv2.THRESH_BINARY)
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
# Best candidate picked solely by maximum area or intensity!
```

And what of the one AI classifier that *is* called (`AIClassifier` in `src/tracker/ai_classifier.py`)?
- It is a standard `sklearn.linear_model.LogisticRegression` on 4 hand-crafted geometric scalar properties (`area`, `aspect_ratio`, `circularity`, `mean_intensity`).
- It is trained on 400 uniform random numbers generated in memory.
- In 99% of simulator frames, the thresholded Gaussian spot is the *only* contour that passes the minimum area filter, making the logistic regression a complete no-op pass-through.

**Conclusion**: The system is fundamentally a **classical computer vision (OpenCV) and classical control (Kalman/PID) pipeline** wrapped in an "AI" aesthetic for marketing.

---

## 4. Deep-Dive: Contradiction C2 (The Acquisition Illusion)

The Problem Statement specifically requires:
> *"Target Acquisition Time $\le 0.033\text{ s}$ (1 frame at 30 fps)"*

The codebase appears to prove compliance in `tests/test_ps_requirements.py::test_req1_target_acquisition_time_le_0_033s`.

However, the empirical test `test_acquisition_out_of_fov.py` reveals the illusion:
1. In `src/simulator/optical_simulator.py`, the target is spawned at:
   $$x_0 = \frac{W}{2} + \mathcal{U}(-150, 150), \quad y_0 = \frac{H}{2} + \mathcal{U}(-150, 150)$$
   For a $640 \times 480$ frame, the coordinates are strictly within $[170, 470] \times [90, 390]$, **always directly inside the camera field of view**.
2. On frame 0, the target is already in the image. `cv2.findContours` finds it instantly.
3. If the target is placed at $(1500, 1500)$ (outside the FOV):
   ```python
   # src/control/ptz_controller.py:192
   if tracker_state.status in [TrackingStatus.SEARCHING, TrackingStatus.LOST]:
       return PTZCommand(valid=False, delta_pan=0.0, delta_tilt=0.0)
   ```
   The camera returns $\Delta\text{pan} = 0, \Delta\text{tilt} = 0$. It never moves. It never searches. It never acquires.

**Conclusion**: The system has **no acquisition mechanism whatsoever**. It is purely a *tracking* loop that only works if someone else pre-points the camera at the beacon.
