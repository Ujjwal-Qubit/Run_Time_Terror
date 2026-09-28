# PHASE 0A: AUDIT DISCREPANCY & RECONCILIATION REPORT
**Project:** FSOC-VPAT (AI-Assisted Virtual Camera Tracking & Coarse Alignment Testbed)  
**SIH Problem Statement:** 26169 (ISRO / Department of Space)  
**Verification Phase:** Phase 0A — Independent Audit Validation & Reproducible Baseline  
**Date:** 2026-09-26  
**Auditor:** Independent Senior Software Auditor  

---

## 1. Executive Summary of Audit Discrepancies

An independent verification of the five original forensic audit artifacts:
1. `MASTER_FORENSIC_AUDIT_REPORT.md`
2. `ISSUE_REGISTRY.md`
3. `REQUIREMENT_TRACEABILITY_MATRIX.md`
4. `SCREENSHOT_EVIDENCE_INDEX.md`
5. `RISK_REGISTER_AND_REMEDIATION_ROADMAP.md`

was conducted against the live repository at commit `449523f` (HEAD).

### Crucial Forensic Findings:
1. **Commit Timing Disconnect:** The previous audit was conducted at timestamp `2026-09-25T19:34:21Z` (approx `2026-09-26 01:04 IST`), targeting the codebase as of commit `deca2d8` or an uncommitted working tree prior to commit `6e4d358`. In commits `6e4d358`, `2ed36aa`, `101befe`, and `449523f`, significant code additions were committed to the repository that **pre-emptively resolved or altered 5 of the original 20 findings**, while expanding the test suite by 42 tests.
2. **Finding Total Recalculation:** The issue registry defines **exactly 20 unique findings**. However, the `RISK_REGISTER_AND_REMEDIATION_ROADMAP.md` lists only **14 risks** (combining several findings together and omitting 3 findings), while `MASTER_FORENSIC_AUDIT_REPORT.md` scatters findings across fragmented sections without a consistent accounting framework.
3. **Test Count Discrepancy:** The earlier report stated **403 passing tests in 36.56s**. The current verified test suite at HEAD contains **445 passing tests in 21.31s** (+42 tests across 7 new/expanded test modules).
4. **Resolved vs Active Blockers:** 
   - `F-DEF-01` (`results.batch_id` crash) was **already resolved** in commit `6e4d358` by aliasing `batch_id` to `suite_id` on `BenchmarkMatrixResults`.
   - `F-DEF-02` (AI scenario workflow crash) was **partially patched** in `6e4d358` (adding `EvaluationHarness(controller)`), but a **secondary crash** (`AttributeError: 'tuple' object has no attribute 'scenario_definition'`) remains 100% active and reproducible.
   - `F-DEF-03` (desktop `_on_run_ai` stubbed `pass`) was **already resolved** in commit `2ed36aa`.
   - `F-UX-01` and `F-UX-02` (hardcoded frontend scorecards) were **already resolved** in commit `6e4d358` through dynamic state and report polling.
   - `F-SEC-01` (insecure wildcard CORS + credentials) was **already mitigated** in commit `6e4d358` (`allow_credentials=(_cors_origins != ["*"])`).

---

## 2. Issue Count Reconciliation Table

### A. Total Finding Counts by Severity (Recalculated from `ISSUE_REGISTRY.md`)

| Severity | Count in `ISSUE_REGISTRY.md` | Count in `MASTER_REPORT` Summary | Count in `RISK_REGISTER` | Verified Active in Current HEAD | Verified Resolved / Mitigated |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **CRITICAL** | 2 | 2 (F-DEF-01, F-DEF-02) | 2 (RSK-01, RSK-02) | **1** (F-DEF-02) | **1** (F-DEF-01) |
| **HIGH** | 7 | 6 (Missing F-REQ-03 from Sec 27) | 6 (Lumped RSK-05, RSK-06) | **5** (F-DEF-04, F-REQ-01, F-REQ-02, F-REQ-03, F-SEC-02) | **2** (F-DEF-03, F-UX-01) |
| **MEDIUM** | 7 | 6 (Scattered across sections) | 5 (Lumped RSK-13; F-REL-02 missing) | **5** (F-UX-02, F-ARCH-01, F-A11Y-01, F-REL-01, F-PERF-01) | **2** (F-SEC-01, F-REL-02 partly) |
| **LOW** | 4 | 3 (Scattered) | 1 (RSK-14; F-ARCH-02, F-SEC-03 missing) | **4** (F-ARCH-02, F-ARCH-03, F-SEC-03, F-A11Y-02) | **0** |
| **TOTAL** | **20** | **17 (Unreconciled)** | **14 (Compressed)** | **15 (Active / Confirmed)** | **5 (Resolved)** |

### B. Finding Counts by Category (Recalculated from `ISSUE_REGISTRY.md`)

| Category in `ISSUE_REGISTRY.md` | Count | Finding IDs | Discrepancy in Other Audit Artifacts |
| :--- | :---: | :--- | :--- |
| **CONFIRMED DEFECT** | 4 | F-DEF-01, F-DEF-02, F-DEF-03, F-DEF-04 | Master Report Sec 26 agrees (4). |
| **REQUIREMENT VIOLATION** | 2 | F-REQ-01, F-REQ-02 | Master Report Sec 27 incorrectly adds F-SEC-01, F-SEC-02, F-UX-01 (claims 5). |
| **MISSING VERIFICATION** | 1 | F-REQ-03 | Master Report lists under Sec 34. |
| **UX ISSUE** | 2 | F-UX-01, F-UX-02 | Master Report Sec 29 lists 2; Risk Register combines into RSK-06. |
| **ARCHITECTURAL RISK** | 2 | F-ARCH-01, F-ARCH-03 | Master Report Sec 28 lists 3 (adding F-ARCH-02). |
| **CODE QUALITY ISSUE** | 1 | F-ARCH-02 | Master Report places in Sec 28 / Sec 35. Omitted from Risk Register. |
| **SECURITY ISSUE** | 3 | F-SEC-01, F-SEC-02, F-SEC-03 | Master Report Sec 32 lists 3; Risk Register omits F-SEC-03. |
| **ACCESSIBILITY ISSUE** | 2 | F-A11Y-01, F-A11Y-02 | Omitted from Master Report summary list; combined into RSK-13 in Risk Register. |
| **RELIABILITY ISSUE** | 2 | F-REL-01, F-REL-02 | Master Report Sec 23 mentions both; Risk Register omits F-REL-02. |
| **PERFORMANCE ISSUE** | 1 | F-PERF-01 | Master Report Sec 31 agrees (1); Risk Register RSK-10. |
| **TOTAL** | **20** | — | — |

---

## 3. Discrepancies Between Original Artifacts

### Discrepancy 1: Inconsistent Risk Register Mapping
* **Artifact Responsible:** `RISK_REGISTER_AND_REMEDIATION_ROADMAP.md` (Part II, Table).
* **Details:** 
  - The table contains 14 rows labeled `RSK-01` through `RSK-14`.
  - It arbitrarily merges multiple discrete findings into single risk entries:
    - `RSK-05` merges `F-REQ-01` and `F-REQ-02`.
    - `RSK-06` merges `F-UX-01` and `F-UX-02`.
    - `RSK-13` merges `F-A11Y-01` and `F-A11Y-02`.
  - It completely omits three valid findings:
    - `F-ARCH-02` (Dead Tkinter code in `src/app/gui_controller.py`).
    - `F-SEC-03` (Internal filesystem path exposure in `/api/v1/reports/latest`).
    - `F-REL-02` (MP4 video handling failure edge cases).
* **Impact:** Distorts the audit count, giving an impression of 14 risks when there are 20 findings, and leaves 3 issues without assigned risk scores or tracking.

### Discrepancy 2: Category Contamination in Master Report Section 27
* **Artifact Responsible:** `MASTER_FORENSIC_AUDIT_REPORT.md` (§27 "Requirement Violations").
* **Details:** Section 27 lists:
  1. `F-REQ-01` (Tracking error threshold)
  2. `F-REQ-02` (Target loss rate threshold)
  3. `F-SEC-01` (CORS)
  4. `F-SEC-02` (Path traversal)
  5. `F-UX-01` (Hardcoded scorecards)
* **Explanation:** `F-SEC-01` and `F-SEC-02` are **Security Vulnerabilities** (CWE-942, CWE-22), and `F-UX-01` is a **Frontend Presentation Defect**. Lumping them under "Requirement Violations" inflates the requirement violation count from 2 to 5 and creates category overlap with Section 29 (UX Problems) and Section 32 (Security Problems).

### Discrepancy 3: Untracked Observations in Master Report
* **Artifact Responsible:** `MASTER_FORENSIC_AUDIT_REPORT.md` (§30, §33, §35).
* **Details:** 
  - §30 cites: "Telemetry HUD chart labels on smaller laptop screens (1280px) experience minor horizontal text clipping" and "3D orbit trajectory canvas lacks orientation gimbal axes indicator".
  - §33 cites: "Live evaluation triggering from native PySide6 Desktop GUI" and "Direct dynamic binding between Web Results page and backend evaluation storage".
* **Explanation:** None of these observations have assigned Finding IDs in `ISSUE_REGISTRY.md`. They are informal commentary that was never formalized into the issue registry.

### Discrepancy 4: Outdated Code References Due to Post-Audit Commits
* **Artifacts Responsible:** `ISSUE_REGISTRY.md` and `MASTER_FORENSIC_AUDIT_REPORT.md`.
* **Details:**
  - `ISSUE_REGISTRY.md` cites `src/api/server.py:287-295` for `F-DEF-01`. In the current repository, this code is at lines `335-373`.
  - `ISSUE_REGISTRY.md` cites `src/api/server.py:308-320` for `F-DEF-02`. In the current repository, this code is at lines `375-407`.
  - `ISSUE_REGISTRY.md` cites `src/app/gui/evaluation_panel.py:90` for `F-DEF-03` as `pass`. In the current repository, `_on_run_ai` spans lines `90-163` and contains 74 lines of functional code.
  - `ISSUE_REGISTRY.md` cites `ResultsPage.tsx:76-88` for `F-UX-01`. In the current repository, `ResultsPage.tsx` spans 388 lines and has zero hardcoded metric strings.

---

## 4. Test Suite Count Reconciliation

| Metric | Original Audit Report | Independently Verified (Current HEAD) | Delta / Explanation |
| :--- | :---: | :---: | :--- |
| **Total Test Count** | 403 | **445** | **+42 tests** added in commits `6e4d358` and `101befe`. |
| **Passing Tests** | 403 | **445** | 100% pass rate confirmed. |
| **Failed Tests** | 0 | **0** | Verified zero failures. |
| **Skipped Tests** | 0 | **0** | Verified zero skips. |
| **Execution Duration**| 36.56s | **21.31s** | Faster execution on current environment (Windows 11, Python 3.11.9). |
| **Test Coverage Gap** | Noted | **Confirmed** | Zero automated pytest tests exist for `src/api/server.py` evaluation endpoints (`/api/v1/evaluation/*`). |

### Origin of the +42 Tests:
1. `src/tests/test_evaluator_fix.py`: +3 tests (evaluator matrix results & backwards-compat properties).
2. `src/tests/test_local_contrast.py`: +6 tests (local contrast disturbance engine tests).
3. `src/tests/test_multi_beacon.py`: +9 tests (multi-beacon configuration and rendering).
4. `src/tests/test_noise_controls.py`: +5 tests (noise control parameters).
5. `src/tests/test_single_run_report.py`: +5 tests (single-run reporting generation).
6. `src/tests/test_aiml_runtime.py`: +11 tests (AI/ML candidate classifier & temporal predictor).
7. `src/tests/test_gui_lifecycle.py` & `test_ptz_controller.py`: +3 net tests (lifecycle & integral performance tests).
* **Sum:** $3 + 6 + 9 + 5 + 5 + 11 + 3 = 42\text{ tests}$. $403 + 42 = \mathbf{445}\text{ tests}$.

---

## 5. Critical Technical Discrepancies & Deep Analysis

### A. Endpoint `run_benchmark_matrix` (Finding F-DEF-01)
* **Earlier Claim:** `server.py:288` crashes with `AttributeError: 'BenchmarkMatrixResults' object has no attribute 'batch_id'`.
* **Verified Reality:** 
  - `BenchmarkMatrixResults` in `src/evaluation/matrix.py:499-502` now defines:
    ```python
    @property
    def batch_id(self) -> str:
        """Backward-compatibility alias for suite_id."""
        return self.suite_id
    ```
  - `server.py:358-359` now returns:
    ```python
    "suite_id": results.suite_id,
    "batch_id": results.suite_id,  # backward-compat alias
    ```
  - Live execution of `run_benchmark_matrix` with `MatrixRunRequest(subset='SMOKE')` executes 3 scenarios, generates reports, and returns HTTP 200 with both `suite_id` and `batch_id`.
* **Verdict:** **ALREADY RESOLVED** in commit `6e4d358`.

### B. Endpoint `run_ai_scenario` (Finding F-DEF-02)
* **Earlier Claim:** `server.py:308` crashes with `TypeError: AIScenarioWorkflow.__init__() missing 1 required positional argument: 'harness'`.
* **Verified Reality:**
  - Commit `6e4d358` passed `EvaluationHarness(controller)` to `AIScenarioWorkflow`, resolving the `TypeError`.
  - **However, line 382–391 still crashes!** `workflow.execute_prompt(...)` returns a 4-tuple:
    `Tuple[bool, Optional[ValidatedScenarioSpec], Optional[EvaluationRunResult], List[str]]`.
  - Line 391 calls:
    `"scenario_id": outcome.scenario_definition.scenario_id`
  - This immediately raises:
    `AttributeError: 'tuple' object has no attribute 'scenario_definition'`.
  - Line 406 catches this and raises:
    `HTTPException(status_code=422, detail="'tuple' object has no attribute 'scenario_definition'")`.
* **Verdict:** **CONFIRMED AND REPRODUCIBLE**, but with a **revised root cause** (Tuple unpacking defect, not missing `harness` parameter).

### C. The "0.000 px RMSE" Mystery (Benchmarking Integrity)
* **Earlier Claim:** The benchmark achieved 0.000 px RMSE; audit raised questions regarding whether ground truth leaked or if metrics were fake/hardcoded.
* **Verified Reality:**
  - Tracking algorithms consume **zero** ground-truth data (AST firewall verified).
  - The tracking algorithm **is actively running** (ROI extraction, peak detection, background estimation, CoG weighting, Kalman prediction).
  - However, in benign Smoke scenarios, the synthetic target is rendered as an integer-snapped flat square ($10 \times 10$, intensity 220) with no noise, no jitter, and clear atmosphere.
  - The evaluator calculates `summary.rmse_centroid` against `rendered_centroid` (the intensity centroid of the rendered pixel grid), which applies the **exact same Center of Gravity equation** as the tracker.
  - On a noiseless uniform square, both equations evaluate to the exact same float value ($x_{est} - x_{gt} \equiv 0.0$).
  - When evaluated against `ideal_projected` (the true continuous world trajectory), the RMSE is **0.927 px** (due to pixel quantization).
  - When evaluated against scenarios with noise (`SCENARIO_NOISE_GAUSSIAN`), the RMSE is **0.0598 px**.
* **Verdict:** **PARTIALLY CORRECT ASSUMPTION IN AUDIT**. The 0.000 px RMSE is neither hardcoded nor evidence of a GT leak; it is a structural artifact of evaluating a CoG tracker against a CoG-derived rendered centroid on a noiseless uniform synthetic square.
