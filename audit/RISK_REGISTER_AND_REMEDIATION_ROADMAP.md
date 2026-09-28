# DELIVERABLES 5, 6 & 7: ARCHITECTURE MAP, RISK REGISTER & REMEDIATION ROADMAP
## FSOC-VPAT — AI-Assisted Virtual Camera Tracking & Coarse Alignment Testbed
### SIH Problem Statement 26169 | Team: Run Time Terror (Team ID: 69)

---

# PART I — DELIVERABLE 5: ARCHITECTURE & DEPENDENCY MAP

## 1. Graphify Knowledge Graph Metrics
* **Total Nodes:** 2,267
* **Total Edges:** 4,821
* **Detected Communities:** 122
* **Graph Density:** 0.00188
* **Dominant God Node:** `src/app/controller.py::AppController`
  - Degree: **186 direct edges** (65 in-degrees, 121 out-degrees)
  - Betweenness Centrality: **0.205** (highest in the entire codebase by an order of magnitude)
  - Subsystem Role: Central orchestrator connecting Simulator, Trackers, Gimbal Controller, Evaluator, and UI event loops.

```
       +-------------------------------------------------------------+
       |                      USER INTERFACES                        |
       |  +------------------------+     +------------------------+  |
       |  |  React 18 / Three.js   |     |    PySide6 Desktop     |  |
       |  |     (Port 5173)        |     |      (Native Qt)       |  |
       |  +-----------+------------+     +-----------+------------+  |
       +--------------|------------------------------|---------------+
                      | HTTP / WebSocket             | Qt Signals
                      v                              v
       +-------------------------------------------------------------+
       |                     ORCHESTRATION LAYER                     |
       |               FastAPI Server (src/api/server.py)            |
       |                               &                             |
       |            AppController (src/app/controller.py)            |
       +--------------+------------------------------+---------------+
                      |                              |
         +------------v------------+    +------------v------------+
         |     SIMULATION DOMAIN   |    |    EVALUATION DOMAIN    |
         |  - Optical Beacon (Airy)|    |  - Benchmark Matrix     |
         |  - Hufnagel-Valley Turb |    |  - Metric Aggregator    |
         |  - Platform Jitter      |    |  - SIH PS Validation    |
         |  - Dynamic Clouds/Fog   |    |  - Exporter (JSON/CSV)  |
         |  - Solar Glint/Noise    |    +------------^------------+
         +------------+------------+                 |
                      | Ground Truth Array           | Estimated Centroid
                      | (Frame + State)              | + Time Metrics
                      v                              |
       +=============================================|===============+
       |      STRICT ISOLATION FIREWALL (src/core/boundary/)         |
       |           FrameProvider: Strips all GT coordinates          |
       |           Passes ONLY raw np.ndarray pixel buffer           |
       +=============================================|===============+
                      | Raw Pixels Only              |
                      v                              |
         +-------------------------------------------+---------------+
         |                     TRACKING DOMAIN                       |
         |         BaseTracker Interface (src/tracker/base.py)       |
         |  +-----------------------------------------------------+  |
         |  | Classical: CoG Centroid | Gaussian Fit | NCC        |  |
         |  | AI/ML:     Kalman-CNN Tracker | Deep Regressor      |  |
         |  +-----------------------------------------------------+  |
         +-----------------------------+-----------------------------+
                                       | Estimated Centroid
                                       v
         +-----------------------------------------------------------+
         |                      CONTROL DOMAIN                       |
         |         Closed-Loop Servo Model (src/control/servo.py)    |
         |         PID Gimbal Actuator (Pan/Tilt Rate Clamping)      |
         +-----------------------------------------------------------+
```

## 2. Key Architectural Discoveries
1. **Pristine Ground-Truth Isolation:** AST and static import graph analysis confirm that `src/tracker/` has **zero** imports from `src/simulator/` and **zero** access to ground-truth coordinates. Only `src/core/boundary/frame_provider.py` bridges the domains by extracting raw pixel data.
2. **Coupling Bottleneck:** `AppController` acts as a monolithic coordinator. While convenient for desktop PySide6 event dispatching, it directly couples GUI state with core execution logic, creating synchronization friction when adapting to FastAPI WebSocket streaming.
3. **Dead Architecture:** `src/app/gui_controller.py` is an unreferenced Tkinter controller (275 lines) completely superseded by `src/app/gui/` (PySide6) and `frontend/` (React), introducing dead-code noise.

---

# PART II — DELIVERABLE 6: CONSOLIDATED RISK REGISTER

### Risk Scoring Methodology
* **Severity:** CRITICAL (5), HIGH (4), MEDIUM (3), LOW (2), OBSERVATION (1)
* **Likelihood:** HIGH (3), MEDIUM (2), LOW (1)
* **Risk Score:** Severity $\times$ Likelihood (Scale 1 to 15)

| Risk ID | Identified Risk | Category | Severity | Likelihood | Risk Score | Evidence / Root Cause | Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **RSK-01** | Evaluator Benchmark Matrix Web API Crashes | Defect / Reliability | **CRITICAL** | HIGH | **15** | F-DEF-01: `server.py:288` accesses `.batch_id` instead of `.suite_id`. | Align API schema with `BenchmarkMatrixResults` dataclass fields. |
| **RSK-02** | Evaluator AI Scenario Workflow Web API Crashes | Defect / Reliability | **CRITICAL** | HIGH | **15** | F-DEF-02: `server.py:308` missing required `harness` parameter. | Pass `AppController` instance to `AIScenarioWorkflow` and unpack 4-tuple. |
| **RSK-03** | Path Traversal / Arbitrary File Ingestion via API | Security | **HIGH** | HIGH | **12** | F-SEC-02: `server.py:187` uses unsanitized `Path("scenarios") / name`. | Add strict filename sanitization and directory jail resolution check. |
| **RSK-04** | Insecure Wildcard CORS with Allowed Credentials | Security | **MEDIUM** | HIGH | **9** | F-SEC-01: `allow_origins=["*"]` + `allow_credentials=True`. | Restrict origins to `localhost:5173`, `127.0.0.1:5173`, and env vars. |
| **RSK-05** | False SIH Compliance Claims in Automated Test Suite | Requirement Violation | **HIGH** | HIGH | **12** | F-REQ-01 & F-REQ-02: Tests assert RMSE $\le 25\text{ px}$ and Loss $< 30\%$ instead of PS limits ($10\text{ px}$, $5\%$). | Restore strict PS 26169 thresholds ($\le 10.0\text{ px}$, $< 5.0\%$) in `test_phase6_8_sih_validation.py`. |
| **RSK-06** | Hardcoded Mockup Results Misleading Evaluators | UX / Scientific Integrity | **HIGH** | HIGH | **12** | F-UX-01 & F-UX-02: `ResultsPage.tsx:76-88` displays hardcoded string metrics. | Connect `ResultsPage.tsx` to live backend evaluation state and API results. |
| **RSK-07** | Desktop PySide6 AI Scenario Trigger Stubbed | Defect / Completeness | **HIGH** | MEDIUM | **8** | F-DEF-03: `evaluation_panel.py:90` has `def _on_run_ai(self): pass`. | Wire Qt button click signal to controller worker thread for AI execution. |
| **RSK-08** | Desktop Results Panel Buttons Disconnected | Defect / Usability | **HIGH** | MEDIUM | **8** | F-DEF-04: `results_panel.py:44` buttons instantiated without `.connect()`. | Bind `btn_refresh` and `btn_export` signals to export/reload handlers. |
| **RSK-09** | God Class Architectural Fragility | Architectural Risk | **MEDIUM** | MEDIUM | **6** | F-ARCH-01: `AppController` has 186 Graphify edges and 837 LOC. | Decompose `AppController` into focused sub-controllers (Sim, Track, Eval). |
| **RSK-10** | High CPU Overhead from Base64 JPEG WebSocket Encoding | Performance | **MEDIUM** | HIGH | **9** | F-PERF-01: `server.py:118` encodes raw frames to JPEG + Base64 every tick. | Implement throttled streaming or binary WebSocket frame transfer. |
| **RSK-11** | Unbounded WebSocket Client Queue Memory Growth | Reliability / Stability | **MEDIUM** | MEDIUM | **6** | F-REL-01: `server.py:65` broadcasts without backpressure or queue limits. | Introduce bounded buffer or drop-frame strategy for slow consumers. |
| **RSK-12** | Missing Dynamic Re-acquisition Verification | Verification Gap | **HIGH** | MEDIUM | **8** | F-REQ-03: `test_phase6_8_sih_validation.py` only verifies field existence. | Add dynamic occlusion test injecting 1.0s outage and measuring recovery time. |
| **RSK-13** | Frontend Accessibility Barriers for Screen Readers | Accessibility | **MEDIUM** | HIGH | **9** | F-A11Y-01 & F-A11Y-02: Missing `aria-label` on sliders and icon buttons. | Add explicit `aria-label`, `<label>`, and keyboard focus styles. |
| **RSK-14** | `run_web.bat` Fails to Serve Web Frontend | Usability / Deployment | **LOW** | HIGH | **6** | F-ARCH-03: Launches FastAPI without building `frontend/dist` or starting Vite. | Update `run_web.bat` to launch both Vite dev server and FastAPI or build static. |

---

# PART III — DELIVERABLE 7: PRIORITIZED REMEDIATION ROADMAP

```
   [Phase 0: Critical Blockers] ────> [Phase 1: Metric Alignment] ────> [Phase 2: Architecture]
                 │                                   │                           │
                 v                                   v                           v
   [Phase 3: Backend & API]     ────> [Phase 4: AI/CV & Tracking] ────> [Phase 5: Performance]
                 │                                   │                           │
                 v                                   v                           v
   [Phase 6: Frontend State]    ────> [Phase 7: UI/UX & Scientific]───> [Phase 8: Security]
                                                     │
                                                     v
                                [Phase 9: Testing] ──> [Phase 10: Final Polish]
```

### Phase 0 — Critical Blockers (Immediate Pre-requisites)
* **Task 0.1:** Fix `src/api/server.py:288` `AttributeError` by mapping `suite_id` and correct attribute names (`mean_target_loss_rate`) (Finding F-DEF-01).
* **Task 0.2:** Fix `src/api/server.py:308` `TypeError` by providing `harness` parameter and correctly unpacking the 4-tuple result from `AIScenarioWorkflow` (Finding F-DEF-02).
* **Task 0.3:** Sanitize scenario path resolution in `src/api/server.py:187-196` to eliminate path traversal vulnerability (Finding F-SEC-02).
* **Task 0.4:** Fix insecure CORS configuration in `src/api/server.py:46-52` (Finding F-SEC-01).

### Phase 1 — Core Correctness & Metric Alignment
* **Task 1.1:** Restore strict SIH PS Row 17 centroid tracking accuracy assertion (`result.centroid_rmse <= 10.0`) in `src/tests/test_phase6_8_sih_validation.py` (Finding F-REQ-01).
* **Task 1.2:** Restore strict SIH PS Row 18 target loss rate assertion (`result.target_loss_rate < 0.05`) in `src/tests/test_phase6_8_sih_validation.py` (Finding F-REQ-02).
* **Task 1.3:** Implement true dynamic occlusion recovery test asserting re-acquisition time $\le 0.5\text{ s}$ post-occlusion (Finding F-REQ-03).

### Phase 2 — Architecture & Refactoring
* **Task 2.1:** Decompose `AppController` (837 LOC) into specialized controllers: `SimulationController`, `TrackingController`, and `EvaluationController` (Finding F-ARCH-01).
* **Task 2.2:** Remove obsolete Tkinter legacy file `src/app/gui_controller.py` to eliminate dead code (Finding F-ARCH-02).
* **Task 2.3:** Enhance `run_web.bat` and `src/main.py --web` to properly build/serve `frontend/dist` or concurrently launch Vite (Finding F-ARCH-03).

### Phase 3 — Backend & API Resilience
* **Task 3.1:** Scrub raw server filesystem paths from API response in `src/api/server.py:353` (Finding F-SEC-03).
* **Task 3.2:** Introduce structured exception handling and RFC 7807 problem details across all `/api/evaluate/*` routes.
* **Task 3.3:** Add graceful error handling and validation for corrupt or missing MP4 files in `src/simulator/ingestion/video_provider.py` (Finding F-REL-02).

### Phase 4 — AI/CV & Tracking Pipeline
* **Task 4.1:** Implement missing PySide6 signal handler `_on_run_ai` in `src/app/gui/evaluation_panel.py:90` (Finding F-DEF-03).
* **Task 4.2:** Integrate multi-scale CNN feature extraction with Kalman re-acquisition confidence thresholding.
* **Task 4.3:** Add automated benchmark tests for severe scintillation index scenarios ($m > 0.8$).

### Phase 5 — Performance Optimization
* **Task 5.1:** Optimize WebSocket frame streaming via TurboJPEG or binary ArrayBuffer transmission to reduce CPU load (Finding F-PERF-01).
* **Task 5.2:** Add bounded ring-buffer backpressure to WebSocket client broadcaster in `src/api/server.py:65` (Finding F-REL-01).
* **Task 5.3:** Offload phase screen FFT generation to background worker pool for high-resolution frames (1080p).

### Phase 6 — Frontend State & Real Telemetry
* **Task 6.1:** Remove hardcoded static metrics from `frontend/src/components/results/ResultsPage.tsx:76-88` and bind to live run state (Finding F-UX-01).
* **Task 6.2:** Replace static scorecard defaults with dynamic aggregation and clear "No Run Data" empty states (Finding F-UX-02).
* **Task 6.3:** Wire missing signal handlers for `btn_refresh` and `btn_export` in PySide6 `src/app/gui/results_panel.py:44` (Finding F-DEF-04).

### Phase 7 — UI/UX & Scientific Usability
* **Task 7.1:** Add clear engineering units ($\text{mrad}$, $\text{m}^{-2/3}$, $\text{dB}$, $\text{px}$) to all sliders and tooltips across `ConfigPanel.tsx`.
* **Task 7.2:** Enhance 3D trajectory visualization with coordinate reference frames (ECEF / NED) and gimbal pointing vector cone.
* **Task 7.3:** Implement accessible color palettes and high-contrast indicators for tracking lock states.

### Phase 8 — Security Hardening
* **Task 8.1:** Add file size and MIME-type validation for MP4 video uploads in `src/api/server.py`.
* **Task 8.2:** Implement rate limiting on `/api/evaluate/*` execution endpoints.
* **Task 8.3:** Secure WebSocket endpoint with origin verification.

### Phase 9 — Testing & Automated Verification
* **Task 9.1:** Add end-to-end integration tests verifying FastAPI `/api/evaluate/benchmark-matrix` and `/api/evaluate/ai-scenario` responses.
* **Task 9.2:** Create automated Playwright / Puppeteer frontend smoke tests for critical user workflows.
* **Task 9.3:** Integrate benchmark scorecards into CI workflow with automated regression alerts.

### Phase 10 — Final System Polish & Packaging
* **Task 10.1:** Create unified one-click launcher script (`start_all.bat`) orchestrating backend, frontend, and desktop modes.
* **Task 10.2:** Generate comprehensive PDF/HTML export templates for SIH jury evaluation demonstrations.
* **Task 10.3:** Conduct end-to-end dry-run demonstration under simulated high-stress optical channel conditions.
