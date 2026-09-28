# PHASE 0: TARGETED REMEDIATION PLAN & REGRESSION HARNESS SPECIFICATION
**Project:** FSOC-VPAT (AI-Assisted Virtual Camera Tracking & Coarse Alignment Testbed)  
**SIH Problem Statement:** 26169 (ISRO / Department of Space)  
**Verification Phase:** Phase 0A — Independent Audit Validation & Reproducible Baseline  
**Date:** 2026-09-26  
**Auditor:** Independent Senior Software Auditor  

---

## 1. Overview and Scope

Following the independent verification in Phase 0A, this remediation plan establishes the minimal, dependency-aware sequence of fixes required before beginning broader architectural refactoring.

**CRITICAL DIRECTIVE:** Phase 0A was strictly verification-only. Zero code was modified. The tasks outlined below define the exact scope for execution in **Phase 0B (Implementation)**.

### Target Objectives for Phase 0B:
1. **Critical API Correctness:** Fix the `run_ai_scenario` tuple unpacking crash (`F-DEF-02`).
2. **Security Hardening:** Eliminate the arbitrary path traversal vulnerability in scenario endpoints (`F-SEC-02`).
3. **Deployment Integrity:** Ensure `run_web.bat` and production static web serving work reliably (`F-ARCH-03`).
4. **Desktop GUI Completeness:** Wire the unattached Results Panel action buttons (`F-DEF-04`).
5. **Test & Metric Integrity (Phase 1 Gate):** Establish regression tests that enforce strict SIH PS 26169 thresholds ($\le 10.0\text{ px}$ RMSE, $< 5.0\%$ Loss).

```
[Task 0.1: Fix AI Scenario API] ─────┐
                                     ├──> [Phase 0 Verification & Regression Suite]
[Task 0.2: Path Traversal Jail] ─────┤
                                     │
[Task 0.3: run_web.bat & Static] ────┤
                                     │
[Task 0.4: Wire Desktop Buttons] ────┘
```

---

## 2. Detailed Remediation Tasks

### Task 0.1: Correct AI Scenario API Tuple Unpacking (`F-DEF-02`)
* **Severity:** CRITICAL
* **Target File:** `src/api/server.py` (lines 380–407)
* **Preconditions:** `src.evaluation.ai_scenario.AIScenarioWorkflow` and `EvaluationHarness` exist.
* **Exact Problem:**
  `workflow.execute_prompt(...)` returns a 4-tuple:
  `Tuple[bool, Optional[ValidatedScenarioSpec], Optional[EvaluationRunResult], List[str]]`.
  Line 391 calls `outcome.scenario_definition.scenario_id`, raising `AttributeError: 'tuple' object has no attribute 'scenario_definition'`.
* **Required Implementation:**
  1. Unpack the return value cleanly:
     ```python
     success, spec, eval_res, errors = workflow.execute_prompt(
         prompt=req.prompt,
         algorithm_name=algo,
         seed=req.seed,
         max_frames=req.max_frames,
         output_dir="output/ai_scenarios",
     )
     ```
  2. Populate response dictionary from unpacked variables:
     - `"scenario_id": spec.scenario_id if spec else "unknown"`
     - `"valid": bool(success)`
     - `"validation_errors": errors`
     - `"spec": spec.to_dict() if spec else {}`
     - `"evaluation": { ... } if eval_res else None`
     - `"report_path": eval_res.json_report_path if eval_res else None`
* **Regression Test Required:**
  - Create `src/tests/test_api_ai_scenario.py`.
  - Test `run_ai_scenario` with valid prompt (`"Circular target at 50 px/s in clear air"`) and assert:
    - HTTP 200 response.
    - `valid == True`.
    - `scenario_id` is a non-empty string.
    - `evaluation["algorithm_fps"] > 0`.
  - Test `run_ai_scenario` with invalid/rejected prompt and assert `valid == False` with populated `validation_errors`.

---

### Task 0.2: Remediate Path Traversal in Scenario Endpoints (`F-SEC-02`)
* **Severity:** HIGH
* **Target File:** `src/api/server.py` (lines 226–265)
* **Preconditions:** FastAPI router loaded.
* **Exact Problem:**
  Endpoints `/api/v1/scenarios/load`, `/api/v1/scenarios/save`, and `DELETE /api/v1/scenarios/{name}` concatenate untrusted input directly: `path = Path("scenarios") / name`, allowing directory escape via `../../`.
* **Required Implementation:**
  1. Create a safe path resolution helper:
     ```python
     def _resolve_safe_scenario_path(name: str) -> Path:
         base_dir = Path("scenarios").resolve()
         # Enforce safe basename: strip leading directories and ensure .json extension
         safe_name = Path(name).name
         if not safe_name.endswith(".json"):
             safe_name += ".json"
         resolved = (base_dir / safe_name).resolve()
         if not str(resolved).startswith(str(base_dir)):
             raise HTTPException(status_code=400, detail="Invalid scenario name / path traversal detected.")
         return resolved
     ```
  2. Apply `_resolve_safe_scenario_path` across `load_scenario`, `save_scenario`, and `delete_scenario`.
* **Regression Test Required:**
  - Create `src/tests/test_security_scenarios.py`.
  - Test `load_scenario("../../package.json")` -> assert raises HTTP 400.
  - Test `save_scenario(ScenarioSaveRequest(name="../../../tmp/malicious"))` -> assert raises HTTP 400.
  - Test `delete_scenario("../../important.json")` -> assert raises HTTP 400.
  - Test legitimate `load_scenario("matrix_01_linear")` -> assert resolves cleanly inside `scenarios/`.

---

### Task 0.3: Repair Production Web Launcher & Static Mounting (`F-ARCH-03`)
* **Severity:** MEDIUM
* **Target Files:**
  - `run_web.bat`
  - `src/main.py`
  - `src/api/server.py`
* **Preconditions:** Node.js, `npm`, and `frontend/package.json` installed.
* **Exact Problem:**
  `run_web.bat` opens `http://127.0.0.1:8000`, but FastAPI fails to mount static files because `frontend/dist` has not been built, returning HTTP 404.
* **Required Implementation:**
  1. Update `run_web.bat` to detect whether `frontend/dist` exists:
     - If not built, run `npm run build` in `frontend/` before launching Python, or:
     - Launch both Vite dev server (`npm run dev`) and FastAPI concurrently, providing a dual-mode developer script.
  2. In `src/main.py --web`, display explicit diagnostic output indicating whether static files are being served or if the user should connect via Vite dev server (`http://localhost:5173`).
* **Regression Test Required:**
  - Test that executing build creates `frontend/dist/index.html`.
  - Test that `GET /` on FastAPI server returns HTTP 200 with HTML contents when `frontend/dist` is present.

---

### Task 0.4: Connect PySide6 Results Panel Buttons (`F-DEF-04`)
* **Severity:** HIGH
* **Target File:** `src/app/gui/results_panel.py` (lines 46–53)
* **Preconditions:** PySide6 desktop GUI loaded.
* **Exact Problem:**
  `self.btn_refresh` and `self.btn_export` are added to the UI layout but lack `.clicked.connect(...)` signal bindings.
* **Required Implementation:**
  1. Define handler methods in `ResultsPanel`:
     ```python
     def _on_refresh_clicked(self):
         # Scan output/ directory for newest report and call self.load_results()
         pass

     def _on_export_clicked(self):
         # Open QFileDialog to save current results as markdown or PDF
         pass
     ```
  2. Bind signals in `__init__`:
     ```python
     self.btn_refresh.clicked.connect(self._on_refresh_clicked)
     self.btn_export.clicked.connect(self._on_export_clicked)
     ```
* **Regression Test Required:**
  - In `src/tests/test_gui_lifecycle.py`, add assertions verifying that `panel.btn_refresh.receivers(panel.btn_refresh.clicked) > 0` and `panel.btn_export.receivers(panel.btn_export.clicked) > 0`.

---

## 3. Phase 1 Preparation: Strict Metric & Threshold Integrity

While threshold modifications are strictly prohibited during Phase 0, the following preparation is documented for immediate implementation in Phase 1:

1. **Centroid RMSE Assertion (`F-REQ-01`):**
   - Update `src/tests/test_phase6_8_sih_validation.py:224`:
     ```python
     assert result.centroid_rmse <= 10.0, f"Tracking RMSE {result.centroid_rmse:.2f}px exceeds SIH limit (<=10px)"
     ```
   - *Feasibility Proof:* Under standard benchmark conditions, the tracking engine achieves 0.000 px to 0.060 px RMSE, far below 10.0 px. Restoring the strict SIH threshold will NOT break tests under nominal conditions.

2. **Target Loss Rate Assertion (`F-REQ-02`):**
   - Update `src/tests/test_phase6_8_sih_validation.py:245`:
     ```python
     assert result.target_loss_rate < 0.05, f"Target loss rate {result.target_loss_rate*100:.1f}% exceeds SIH limit (<5%)"
     ```
   - *Feasibility Proof:* Under standard evaluation, `target_loss_rate` is 0.0%, easily satisfying the strict $< 5\%$ limit.

3. **Dynamic Re-acquisition Test (`F-REQ-03`):**
   - Implement `test_req19_dynamic_occlusion_reacquisition` using `DisturbanceEngine.apply_occlusion(duration_s=1.0)`.
   - Assert measured `mean_reacquisition_time_s <= 1.0` (PS Row 19).

---

## 4. Verification Gate Criteria for Phase 0 Completion

Before Phase 0 can be declared complete and Phase 1 commenced, the following automated gate must pass:

1. `python -m pytest src/tests/test_api_ai_scenario.py` -> PASS (HTTP 200, valid AI scenario).
2. `python -m pytest src/tests/test_security_scenarios.py` -> PASS (Directory escape blocked).
3. `python -m pytest` -> 100% of tests pass (all 445 existing tests + new regression tests).
4. `git status` clean with zero unintended side effects across core tracking or simulation code.
