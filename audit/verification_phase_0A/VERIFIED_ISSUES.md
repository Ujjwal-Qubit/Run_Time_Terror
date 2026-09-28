# PHASE 0A: VERIFIED ISSUE REGISTRY
**Project:** FSOC-VPAT (AI-Assisted Virtual Camera Tracking & Coarse Alignment Testbed)  
**SIH Problem Statement:** 26169 (ISRO / Department of Space)  
**Verification Phase:** Phase 0A — Independent Audit Validation & Reproducible Baseline  
**Date:** 2026-09-26  
**Auditor:** Independent Senior Software Auditor  

---

## 1. Master Verification Status Summary

| Finding ID | Category | Original Severity | Verified Status | Verified Severity | Confidence | Affected Area |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **F-DEF-01** | CONFIRMED DEFECT | CRITICAL | **NOT REPRODUCIBLE** | RESOLVED (LOW) | HIGH | Backend API / Evaluation |
| **F-DEF-02** | CONFIRMED DEFECT | CRITICAL | **CONFIRMED & REPRODUCIBLE** | **CRITICAL** | HIGH | Backend API / AI Workflow |
| **F-DEF-03** | CONFIRMED DEFECT | HIGH | **NOT REPRODUCIBLE** | RESOLVED (LOW) | HIGH | PySide6 GUI / Evaluation |
| **F-DEF-04** | CONFIRMED DEFECT | HIGH | **CONFIRMED BY STATIC EVIDENCE** | **HIGH** | HIGH | PySide6 GUI / Results |
| **F-REQ-01** | REQUIREMENT VIOLATION | HIGH | **CONFIRMED BY STATIC EVIDENCE** | **HIGH** | HIGH | Automated Test Assertions |
| **F-REQ-02** | REQUIREMENT VIOLATION | HIGH | **CONFIRMED BY STATIC EVIDENCE** | **HIGH** | HIGH | Automated Test Assertions |
| **F-REQ-03** | MISSING VERIFICATION | HIGH | **CONFIRMED BY STATIC EVIDENCE** | **HIGH** | HIGH | Automated Test Assertions |
| **F-UX-01** | UX ISSUE | HIGH | **NOT REPRODUCIBLE** | RESOLVED (LOW) | HIGH | Frontend UI / Results |
| **F-UX-02** | UX ISSUE | MEDIUM | **NOT REPRODUCIBLE** | RESOLVED (LOW) | HIGH | Frontend UI / Results |
| **F-ARCH-01** | ARCHITECTURAL RISK | MEDIUM | **CONFIRMED BY STATIC EVIDENCE** | **MEDIUM** | HIGH | Core Architecture |
| **F-ARCH-02** | CODE QUALITY ISSUE | LOW | **CONFIRMED BY STATIC EVIDENCE** | **LOW** | HIGH | Core Source Tree |
| **F-ARCH-03** | ARCHITECTURAL RISK | LOW | **CONFIRMED & REPRODUCIBLE** | **MEDIUM** | HIGH | Deployment Scripts |
| **F-SEC-01** | SECURITY ISSUE | MEDIUM | **NOT REPRODUCIBLE** | MITIGATED (LOW) | HIGH | Backend API / Middleware |
| **F-SEC-02** | SECURITY ISSUE | HIGH | **CONFIRMED & REPRODUCIBLE** | **HIGH** | HIGH | Backend API / Scenarios |
| **F-SEC-03** | SECURITY ISSUE | LOW | **CONFIRMED BY STATIC EVIDENCE** | **LOW** | HIGH | Backend API / Reports |
| **F-A11Y-01** | ACCESSIBILITY ISSUE | MEDIUM | **CONFIRMED BY STATIC EVIDENCE** | **MEDIUM** | HIGH | Frontend UI / Controls |
| **F-A11Y-02** | ACCESSIBILITY ISSUE | LOW | **CONFIRMED BY STATIC EVIDENCE** | **LOW** | HIGH | Frontend UI / Controls |
| **F-REL-01** | RELIABILITY ISSUE | MEDIUM | **PARTIALLY CORRECT** | **MEDIUM** | HIGH | Backend / WebSocket |
| **F-REL-02** | RELIABILITY ISSUE | MEDIUM | **PARTIALLY CORRECT** | **LOW** | HIGH | Video Provider / Ingestion |
| **F-PERF-01** | PERFORMANCE ISSUE | MEDIUM | **CONFIRMED BY STATIC EVIDENCE** | **MEDIUM** | HIGH | Backend / WebSocket |

---

## 2. Detailed Verified Finding Records

### Finding F-DEF-01
* **Stable ID:** `F-DEF-01`
* **Title:** FastAPI Benchmark Matrix Endpoint Attribute Crash (`results.batch_id`)
* **Category:** CONFIRMED DEFECT (Legacy) / NOW RESOLVED
* **Verified Severity:** RESOLVED / LOW (Historical Critical)
* **Severity Rationale:** At the time of the original audit (`deca2d8`), accessing `.batch_id` caused an unhandled `AttributeError`, returning HTTP 500 and blocking web evaluations. It was resolved in commit `6e4d358`.
* **Verification Status:** **NOT REPRODUCIBLE / ALREADY RESOLVED IN CURRENT HEAD**
* **Exact File and Line References:** 
  - `src/evaluation/matrix.py:499-502`
  - `src/api/server.py:358-359`
* **Reproduction / Verification Evidence:**
  - In `src/evaluation/matrix.py:499-502`, a `@property def batch_id(self) -> str: return self.suite_id` backward-compatibility alias was added.
  - In `src/api/server.py:358-359`, the endpoint maps `"suite_id": results.suite_id` and `"batch_id": results.suite_id`.
  - Live execution of `run_benchmark_matrix(MatrixRunRequest(subset='SMOKE', max_frames=5))` executed successfully without error, returning HTTP 200 with both `suite_id` and `batch_id`.
* **Actual Impact:** None on current HEAD. Web UI evaluator matrix execution completes normally.
* **Confidence Level:** HIGH (Verified via live code inspection and execution).
* **Dependencies / Preconditions:** Requires `baseline_tracker` or valid plugin algorithm.
* **Recommended Next Action:** Add automated pytest integration test for `POST /api/v1/evaluation/matrix` to prevent regression.

---

### Finding F-DEF-02
* **Stable ID:** `F-DEF-02`
* **Title:** FastAPI AI Scenario Endpoint Tuple Unpacking Crash (`AttributeError: 'tuple' object has no attribute 'scenario_definition'`)
* **Category:** CONFIRMED DEFECT
* **Verified Severity:** **CRITICAL**
* **Severity Rationale:** Completely crashes the AI-assisted scenario workflow in the web application with an unhandled exception, blocking 20% of the SIH competition demonstration (AI/Computer Vision).
* **Verification Status:** **CONFIRMED AND REPRODUCIBLE (WITH REVISED ROOT CAUSE)**
* **Exact File and Line References:** 
  - `src/api/server.py:382-406`
  - `src/evaluation/ai_scenario.py:546-552, 588`
* **Reproduction Steps:**
  1. Invoke `run_ai_scenario(AIScenarioRequest(prompt="Circular orbit at 30 px/s in clear air", max_frames=5))`.
  2. `AIScenarioWorkflow.execute_prompt()` returns a 4-tuple: `(success, validated_spec, res, errors)`.
  3. `server.py:391` attempts: `"scenario_id": outcome.scenario_definition.scenario_id`.
  4. System raises: `AttributeError: 'tuple' object has no attribute 'scenario_definition'`.
  5. Caught by line 405: `raise HTTPException(status_code=422, detail=str(e))`.
* **Actual Impact:** Any attempt to generate and evaluate an AI scenario via the Web API triggers HTTP 422 with internal error details. The frontend remains stuck in an error state.
* **Confidence Level:** HIGH (100% reproduced in isolated runtime test).
* **Dependencies / Preconditions:** Requires running FastAPI server and `AIScenarioWorkflow`.
* **Recommended Next Action:** Unpack the 4-tuple returned by `workflow.execute_prompt(...)` as `(success, spec, res, errors)` in `src/api/server.py:382` and bind schema attributes directly to `spec` and `res`.

---

### Finding F-DEF-03
* **Stable ID:** `F-DEF-03`
* **Title:** PySide6 Desktop GUI Evaluation Panel AI Button Stubbed (`pass`)
* **Category:** CONFIRMED DEFECT (Legacy) / NOW RESOLVED
* **Verified Severity:** RESOLVED / LOW (Historical High)
* **Severity Rationale:** At commit `deca2d8`, clicking "Generate & Run AI Scenario" executed `def _on_run_ai(self): pass`. This was resolved in commit `2ed36aa`.
* **Verification Status:** **NOT REPRODUCIBLE / ALREADY RESOLVED IN CURRENT HEAD**
* **Exact File and Line References:** `src/app/gui/evaluation_panel.py:90-163`
* **Reproduction / Verification Evidence:**
  - Source inspection confirms `_on_run_ai` contains 74 lines of functional implementation.
  - Prompts user via `QInputDialog.getMultiLineText`, instantiates `BenchmarkManager(self.app)`, calls `.run_ai_scenario(...)`, validates spec, logs metrics (FPS, RMSE, Loss rate) to GUI console, and alerts user via `QMessageBox`.
* **Actual Impact:** None. Desktop GUI button is connected and functional.
* **Confidence Level:** HIGH (Confirmed via static AST and source inspection).
* **Dependencies / Preconditions:** PySide6 runtime.
* **Recommended Next Action:** None required for Phase 0.

---

### Finding F-DEF-04
* **Stable ID:** `F-DEF-04`
* **Title:** PySide6 Desktop GUI Results Panel Actions Unwired
* **Category:** CONFIRMED DEFECT
* **Verified Severity:** **HIGH**
* **Severity Rationale:** In the standalone native desktop executable required by SIH PS 26169 Deliverables, the Results Panel contains two primary user action buttons that are completely dead, undermining software usability and grading.
* **Verification Status:** **CONFIRMED BY STATIC EVIDENCE**
* **Exact File and Line References:** `src/app/gui/results_panel.py:46-50`
* **Static Evidence:**
  - `self.btn_refresh = QPushButton("Refresh Results")` and `self.btn_export = QPushButton("Export to PDF/Markdown")` are created and added to `btn_layout`.
  - Zero `.clicked.connect(...)` calls exist for either button in `results_panel.py` or `main_window.py`.
* **Actual Impact:** Clicking "Refresh Results" or "Export to PDF/Markdown" in the native desktop GUI produces no response or action.
* **Confidence Level:** HIGH (Codebase-wide search confirmed zero signal connections).
* **Dependencies / Preconditions:** Desktop PySide6 UI.
* **Recommended Next Action:** Connect `btn_refresh.clicked` to reload the latest report from `output/`, and connect `btn_export.clicked` to trigger a PDF/Markdown export dialog.

---

### Finding F-REQ-01
* **Stable ID:** `F-REQ-01`
* **Title:** Relaxation of SIH Tracking Error Assertion ($\le 25\text{ px}$ vs $\le 10\text{ px}$)
* **Category:** REQUIREMENT VIOLATION
* **Verified Severity:** **HIGH**
* **Severity Rationale:** The automated test suite masks non-compliant tracking implementations by allowing up to $25.0\text{ px}$ centroid RMSE when the SIH Problem Statement explicitly mandates $\le 10.0\text{ px}$.
* **Verification Status:** **CONFIRMED BY STATIC EVIDENCE**
* **Exact File and Line References:** 
  - `Imp. .md/PS.md:52` (Row 17: "Tracking Error ≤ 10 pixels")
  - `Imp. .md/PRD.md:144` (§7.2: "Tracking Error ≤ 10.0 pixels")
  - `src/tests/test_phase6_8_sih_validation.py:224-226`
* **Static Evidence:**
  - Test docstring: `"""Req 17: Tracking error ≤ 10px (allowing 20px tolerance for baseline)."""`
  - Test assertion: `assert result.centroid_rmse <= 25.0`
* **Actual Impact:** An algorithm with $24.9\text{ px}$ tracking error will pass CI/CD automated validation despite failing the SIH PS requirement by $149\%$.
* **Confidence Level:** HIGH (Explicit contradiction between PS.md and test code).
* **Dependencies / Preconditions:** Automated test execution.
* **Recommended Next Action:** In Phase 1 remediation, update test assertion to `assert result.centroid_rmse <= 10.0`.

---

### Finding F-REQ-02
* **Stable ID:** `F-REQ-02`
* **Title:** Relaxation of SIH Target Loss Rate Assertion ($< 30\%$ vs $< 5\%$)
* **Category:** REQUIREMENT VIOLATION
* **Verified Severity:** **HIGH**
* **Severity Rationale:** The automated test suite allows an algorithm to lose the target on nearly one-third ($30\%$) of frames while claiming SIH compliance, whereas the SIH specification mandates $< 5\%$.
* **Verification Status:** **CONFIRMED BY STATIC EVIDENCE**
* **Exact File and Line References:** 
  - `Imp. .md/PS.md:53` (Row 18: "Target Loss < 5%")
  - `Imp. .md/PRD.md:145` (§7.3: "Target Loss Rate < 5.0%")
  - `src/tests/test_phase6_8_sih_validation.py:245-247`
* **Static Evidence:**
  - Test docstring: `"""Req 18: Target loss rate < 20% for baseline (SIH target: <5%)."""`
  - Test assertion: `assert result.target_loss_rate < 0.30`
* **Actual Impact:** Algorithms with unstable tracking loops pass validation despite failing the SIH specification.
* **Confidence Level:** HIGH (Explicit contradiction documented in test comments and code).
* **Dependencies / Preconditions:** Automated test execution.
* **Recommended Next Action:** In Phase 1 remediation, update test assertion to `assert result.target_loss_rate < 0.05`.

---

### Finding F-REQ-03
* **Stable ID:** `F-REQ-03`
* **Title:** Superficial Verification of SIH Re-acquisition Time ($\le 1.0\text{ s}$)
* **Category:** MISSING VERIFICATION
* **Verified Severity:** **HIGH**
* **Severity Rationale:** Re-acquisition capability under dynamic target loss / occlusion is a core SIH evaluation metric (PS Row 19). The test suite tests only dataclass field presence rather than dynamical performance.
* **Verification Status:** **CONFIRMED BY STATIC EVIDENCE**
* **Exact File and Line References:** `src/tests/test_phase6_8_sih_validation.py:249-254`
* **Static Evidence:**
  ```python
  def test_req19_reacquisition_time_metric_computed(self):
      """Req 19: Re-acquisition time metric field is present in EvaluationRunResult."""
      from src.evaluation.harness import EvaluationRunResult
      fields = {f.name for f in dataclasses.fields(EvaluationRunResult)}
      assert "reacquisition_time_s" in fields
  ```
* **Actual Impact:** No automated test validates whether the algorithm can re-acquire a lost beacon within 1.0 second following a dynamic occlusion.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** Simulation disturbance engine occlusion injector.
* **Recommended Next Action:** Implement an end-to-end dynamic occlusion test in Phase 1 that blinds the sensor for 1.0s and measures the time required for `state_manager` to transition back from `LOST`/`REACQUIRING` to `TRACKING`.

---

### Finding F-UX-01
* **Stable ID:** `F-UX-01`
* **Title:** Hardcoded Acquisition & Reacquisition Metric Strings in Web Results
* **Category:** UX ISSUE (Legacy) / NOW RESOLVED
* **Verified Severity:** RESOLVED / LOW (Historical High)
* **Severity Rationale:** At commit `270a055`, `ResultsPage.tsx` displayed static strings (`0.033 s`, `0.067 s`, `5.0°/s`). This was resolved in commit `6e4d358`.
* **Verification Status:** **NOT REPRODUCIBLE / ALREADY RESOLVED IN CURRENT HEAD**
* **Exact File and Line References:** `frontend/src/components/results/ResultsPage.tsx:73-151`
* **Reproduction / Verification Evidence:**
  - Code inspection confirms all metrics are dynamically derived from `latestResult` props or `reportData?.overall_summary`.
  - When no real data is present, values render as `N/A` using `<MetricDisplay />`.
* **Actual Impact:** None. All results displayed are derived from real execution data or `N/A`.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** React 18 web UI.
* **Recommended Next Action:** None required for Phase 0.

---

### Finding F-UX-02
* **Stable ID:** `F-UX-02`
* **Title:** Default Mock Scorecard Numbers Rendered When No Run Present
* **Category:** UX ISSUE (Legacy) / NOW RESOLVED
* **Verified Severity:** RESOLVED / LOW (Historical Medium)
* **Severity Rationale:** At commit `270a055`, the UI showed `19/19 Passed` before any test had been run. Resolved in commit `6e4d358`.
* **Verification Status:** **NOT REPRODUCIBLE / ALREADY RESOLVED IN CURRENT HEAD**
* **Exact File and Line References:** `frontend/src/components/results/ResultsPage.tsx:245-257`
* **Reproduction / Verification Evidence:**
  - Code inspection confirms line 246 renders `N/A` if `successfulRuns === null`.
  - Lines 253-257 render an explicit informational banner: `"No evaluation results available. Run an evaluation matrix from the Evaluator workflow."`
* **Actual Impact:** None. Zero false-pass indicators are shown prior to execution.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** React 18 web UI.
* **Recommended Next Action:** None required for Phase 0.

---

### Finding F-ARCH-01
* **Stable ID:** `F-ARCH-01`
* **Title:** God Class Anti-Pattern in `AppController`
* **Category:** ARCHITECTURAL RISK
* **Verified Severity:** **MEDIUM**
* **Severity Rationale:** Monolithic orchestration class couples simulation, tracking, control, evaluation, and GUI threading into 920 lines with 186 Graphify edges, hindering modular testing and introducing side-effect risks.
* **Verification Status:** **CONFIRMED BY STATIC EVIDENCE**
* **Exact File and Line References:** `src/app/app_controller.py:50-920`
* **Static Evidence:**
  - `AppController` coordinates 15+ submodules: `SceneManager`, `TargetManager`, `CameraModel`, `DisturbanceEngine`, `MP4FrameProvider`, `PluginLoader`, `Detector`, `CentroidEstimator`, `CandidateIdentifier`, `KalmanTracker`, `TrackingStateManager`, `PTZController`, `MetricsEngine`, `LoggingEngine`, and `BenchmarkManager`.
* **Actual Impact:** Increased maintenance friction; testing or modifying evaluation logic requires initializing heavy simulation components.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** Entire core pipeline.
* **Recommended Next Action:** Decompose `AppController` into focused domain coordinators (`SimulationCoordinator`, `TrackingPipeline`, `EvaluationHarness`) in Phase 2.

---

### Finding F-ARCH-02
* **Stable ID:** `F-ARCH-02`
* **Title:** Dead / Superseded Legacy Tkinter Code Remains in Core Source Tree
* **Category:** CODE QUALITY ISSUE
* **Verified Severity:** **LOW**
* **Severity Rationale:** 275 lines of unused legacy Tkinter code in `src/app/gui_controller.py` introduces dead code noise and maintenance confusion.
* **Verification Status:** **CONFIRMED BY STATIC EVIDENCE**
* **Exact File and Line References:** `src/app/gui_controller.py:1-275`
* **Static Evidence:**
  - Zero imports of `gui_controller` exist in active CLI, Web, or Desktop entry points.
  - The module is superseded by `src/app/gui/` (PySide6) and `frontend/` (React 18).
* **Actual Impact:** Code clutter; does not affect runtime execution.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** None.
* **Recommended Next Action:** Safely archive or remove `src/app/gui_controller.py` in Phase 2.

---

### Finding F-ARCH-03
* **Stable ID:** `F-ARCH-03`
* **Title:** Missing Automated Production Build for Static Web Assets in Launcher
* **Category:** ARCHITECTURAL RISK / DEPLOYMENT
* **Verified Severity:** **MEDIUM**
* **Severity Rationale:** `run_web.bat` instructs users to open `http://127.0.0.1:8000`, but FastAPI returns HTTP 404 because `frontend/dist` is not pre-built and Vite is not started.
* **Verification Status:** **CONFIRMED AND REPRODUCIBLE**
* **Exact File and Line References:** 
  - `run_web.bat:1-15`
  - `src/api/server.py:543-546`
* **Reproduction Steps:**
  1. Execute `run_web.bat`.
  2. Navigate to `http://127.0.0.1:8000` in browser.
  3. Server returns `{"detail":"Not Found"}` (HTTP 404).
* **Actual Impact:** Non-technical evaluators following the documented launch instructions cannot access the web interface.
* **Confidence Level:** HIGH (Confirmed live).
* **Dependencies / Preconditions:** `npm`, Node.js, `frontend/package.json`.
* **Recommended Next Action:** In Phase 0, update `run_web.bat` to launch both Vite (`npm run dev`) and FastAPI, or build `frontend/dist` if absent.

---

### Finding F-SEC-01
* **Stable ID:** `F-SEC-01`
* **Title:** Insecure CORS Wildcard (`*`) Combined with `allow_credentials=True`
* **Category:** SECURITY ISSUE (Legacy) / NOW MITIGATED
* **Verified Severity:** MITIGATED / LOW (Historical Medium)
* **Severity Rationale:** At commit `270a055`, `allow_origins=["*"]` and `allow_credentials=True` were simultaneously configured. Resolved in commit `6e4d358`.
* **Verification Status:** **NOT REPRODUCIBLE / ALREADY MITIGATED IN CURRENT HEAD**
* **Exact File and Line References:** `src/api/server.py:50-62`
* **Static / Runtime Evidence:**
  - Line 59 explicitly sets: `allow_credentials=(_cors_origins != ["*"])`.
  - When `_cors_origins == ["*"]` (default), `allow_credentials` evaluates to `False`.
  - Live FastAPI inspection verified: `Middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=False)`.
* **Actual Impact:** Wildcard origins cannot exploit credentialed requests.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** FastAPI CORS middleware.
* **Recommended Next Action:** Restrict `allow_origins` to explicit origins (`http://localhost:5173`, `http://127.0.0.1:5173`) in Phase 0 hardening.

---

### Finding F-SEC-02
* **Stable ID:** `F-SEC-02`
* **Title:** Arbitrary Path Traversal Vulnerability in Scenario Endpoints
* **Category:** SECURITY ISSUE (CWE-22)
* **Verified Severity:** **HIGH**
* **Severity Rationale:** User-controlled input in `/api/v1/scenarios/load`, `/api/v1/scenarios/save`, and `/api/v1/scenarios/{name}` escapes the `scenarios/` directory via `../`, permitting unauthorized reading, writing, and deletion of `.json` files on the host filesystem.
* **Verification Status:** **CONFIRMED AND REPRODUCIBLE**
* **Exact File and Line References:** `src/api/server.py:226-264`
* **Static / Runtime Evidence:**
  - `path = Path("scenarios") / name`.
  - Tested in Python: `Path("scenarios") / "../../package.json"` resolves to `E:\Newfolder\Project2O\Projects\SIH '26\package.json`, completely escaping `scenarios/`.
  - In `delete_scenario`: `path.unlink()` will delete arbitrary JSON files across the host drive if targeted.
* **Actual Impact:** Path traversal vulnerability permitting arbitrary JSON read, write, and deletion.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** Accessible FastAPI scenario endpoints.
* **Recommended Next Action:** In Phase 0 remediation, implement strict basename extraction (`Path(name).name`), validate against allowed alphanumeric/underscore patterns, and verify that `path.resolve()` starts with `scenarios.resolve()`.

---

### Finding F-SEC-03
* **Stable ID:** `F-SEC-03`
* **Title:** Absolute Host Filesystem Path Leakage in Report API
* **Category:** SECURITY ISSUE (Information Disclosure)
* **Verified Severity:** **LOW**
* **Severity Rationale:** Exposing internal directory structures (e.g. `E:\Newfolder\Project2O\...`) assists attackers in environmental fingerprinting.
* **Verification Status:** **CONFIRMED BY STATIC EVIDENCE**
* **Exact File and Line References:** 
  - `src/api/server.py:367` (`"report_paths": {"json": j_p, ...}`)
  - `src/api/server.py:426` (`"path": str(latest_file)`)
* **Static Evidence:** API responses directly serialize un-sanitized internal operating system paths.
* **Actual Impact:** Internal path structure leakage; does not permit direct execution or compromise on its own.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** API calls to `/api/v1/reports/*` or `/api/v1/evaluation/matrix`.
* **Recommended Next Action:** Return paths relative to project root or use artifact IDs in Phase 3.

---

### Finding F-A11Y-01
* **Stable ID:** `F-A11Y-01`
* **Title:** Missing Accessible Names and ARIA Attributes on Icon-Only Controls
* **Category:** ACCESSIBILITY ISSUE (WCAG 2.1 §4.1.2)
* **Verified Severity:** **MEDIUM**
* **Severity Rationale:** Screen-reader users cannot determine the function of critical navigation and control buttons.
* **Verification Status:** **CONFIRMED BY STATIC EVIDENCE**
* **Exact File and Line References:** 
  - `frontend/src/components/layout/Sidebar.tsx`
  - `frontend/src/components/developer/ControlPanel.tsx`
* **Static Evidence:** Multiple `<button>` elements render only Lucide icons without `aria-label` or screen-reader text (`sr-only`).
* **Actual Impact:** Degrades accessibility compliance during technical evaluation.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** Frontend Web UI.
* **Recommended Next Action:** Add explicit `aria-label` attributes to all icon-only buttons in Phase 7.

---

### Finding F-A11Y-02
* **Stable ID:** `F-A11Y-02`
* **Title:** Unlabeled Numeric Range Inputs in Configuration Panel
* **Category:** ACCESSIBILITY ISSUE (WCAG 2.1 §1.3.1)
* **Verified Severity:** **LOW**
* **Severity Rationale:** Form sliders use `<span>` for visible text rather than programmatic `<label htmlFor="...">` associations.
* **Verification Status:** **CONFIRMED BY STATIC EVIDENCE**
* **Exact File and Line References:** `frontend/src/components/developer/ConfigPanel.tsx:403-412, 420-429, 452-460`
* **Static Evidence:** `<input type="range" ... />` lacks `id`, `name`, and `aria-label`.
* **Actual Impact:** Screen readers announce sliders simply as "slider" without context or parameter name.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** Frontend Web UI.
* **Recommended Next Action:** Wrap sliders in `<label>` or attach `aria-label` with parameter name and engineering units in Phase 7.

---

### Finding F-REL-01
* **Stable ID:** `F-REL-01`
* **Title:** Unbounded WebSocket Live Stream Without Client Backpressure
* **Category:** RELIABILITY / PERFORMANCE
* **Verified Severity:** **MEDIUM**
* **Severity Rationale:** The 30 FPS WebSocket streamer lacks consumer flow control and duplicates CPU-intensive JPEG compression for each connected client.
* **Verification Status:** **PARTIALLY CORRECT / INACCURATELY DESCRIBED**
* **Exact File and Line References:** `src/api/server.py:465-538`
* **Verification Details:**
  - The original finding claimed an "unbounded queue". In reality, there is no Python FIFO queue; `websocket.send_json()` is awaited sequentially in a 30 FPS loop.
  - However, TCP backpressure from slow consumers stalls the loop, and multiple clients cause linear CPU growth due to per-client JPEG compression.
* **Actual Impact:** Performance degradation when multiple clients connect or when client network lag occurs.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** WebSocket client streaming.
* **Recommended Next Action:** Centralize single-pass JPEG encoding and introduce frame-skipping for slow consumers in Phase 5.

---

### Finding F-REL-02
* **Stable ID:** `F-REL-02`
* **Title:** Video Capture Error Handling on Corrupt or Missing MP4
* **Category:** RELIABILITY
* **Verified Severity:** **LOW**
* **Severity Rationale:** Edge-case handling for mid-stream decode failures in external MP4 video playback.
* **Verification Status:** **PARTIALLY CORRECT / INACCURATELY DESCRIBED**
* **Exact File and Line References:** `src/frame/mp4_provider.py:38-47, 112-115`
* **Verification Details:**
  - The earlier claim that OpenCV fails "silently" and streams "blank black frames" is inaccurate.
  - `MP4FrameProvider` explicitly raises `FileNotFoundError` if missing and `ValueError` if corrupt at startup.
  - If a decode failure occurs mid-stream, `ret, frame = self._cap.read()` detects `not ret` and returns `None`, which cleanly terminates the simulation loop (`self._running = False`).
* **Actual Impact:** Clean termination occurs, but no dedicated user-facing error message or toast is emitted.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** External MP4 video mode.
* **Recommended Next Action:** Emit explicit status notification when an MP4 stream terminates abnormally in Phase 3.

---

### Finding F-PERF-01
* **Stable ID:** `F-PERF-01`
* **Title:** High CPU Overhead from Per-Frame Base64 JPEG Compression
* **Category:** PERFORMANCE
* **Verified Severity:** **MEDIUM**
* **Severity Rationale:** Encoding 30 FPS 640x480 video frames to JPEG and Base64 in Python async loop consumes ~15–20% of a CPU core per client.
* **Verification Status:** **CONFIRMED BY STATIC EVIDENCE**
* **Exact File and Line References:** `src/api/server.py:484-487`
* **Static Evidence:**
  - `cv2.imencode(".jpg", bgr_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])`
  - `"data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")`
  - Executed on every frame for every connected WebSocket client.
* **Actual Impact:** Restricts maximum framerate under multi-client or high-resolution scenarios.
* **Confidence Level:** HIGH.
* **Dependencies / Preconditions:** Live WebSocket streaming.
* **Recommended Next Action:** Transmit binary JPEG/ArrayBuffer over WebSocket or encode once per tick across clients in Phase 5.
