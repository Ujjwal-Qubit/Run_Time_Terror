# LumiTrack FSOC-VPAT — Forensic Issue Registry
**Project:** FSOC-VPAT — AI-Assisted Virtual Camera Tracking & Coarse Alignment Testbed  
**SIH Problem Statement:** 26169 (ISRO / Department of Space)  
**Audit Phase:** Forensic Baseline (Audit-First, Zero-Modification Phase)  
**Date:** 2026-09-26  

---

## Consolidated Finding Summary

| Finding ID | Category | Severity | Title | Affected Area | Confidence |
|---|---|---|---|---|---|
| **F-DEF-01** | CONFIRMED DEFECT | CRITICAL | FastAPI Matrix Endpoint Attribute Crash (`results.batch_id`) | Backend API | HIGH |
| **F-DEF-02** | CONFIRMED DEFECT | CRITICAL | FastAPI AI Scenario Missing Argument & Return Contract Crash | Backend API | HIGH |
| **F-DEF-03** | CONFIRMED DEFECT | HIGH | PySide6 Desktop GUI Evaluation Panel AI Button Stubbed (`pass`) | Desktop GUI | HIGH |
| **F-DEF-04** | CONFIRMED DEFECT | HIGH | PySide6 Desktop GUI Results Panel Actions Unwired | Desktop GUI | HIGH |
| **F-REQ-01** | REQUIREMENT VIOLATION | HIGH | Relaxation of SIH Tracking Error Assertion (<=25px vs <=10px) | Automated Tests | HIGH |
| **F-REQ-02** | REQUIREMENT VIOLATION | HIGH | Relaxation of SIH Target Loss Rate Assertion (<30% vs <5%) | Automated Tests | HIGH |
| **F-REQ-03** | MISSING VERIFICATION | HIGH | Superficial Verification of SIH Re-acquisition Time (<=1.0s) | Automated Tests | HIGH |
| **F-UX-01** | UX ISSUE | HIGH | Hardcoded Acquisition & Reacquisition Metric Strings in Web Results | Frontend UI | HIGH |
| **F-UX-02** | UX ISSUE | MEDIUM | Default Mock Scorecard Numbers Rendered When No Run Present | Frontend UI | HIGH |
| **F-ARCH-01** | ARCHITECTURAL RISK | MEDIUM | God Class Anti-Pattern in `AppController` (186 Graph Edges) | Core Architecture | HIGH |
| **F-ARCH-02** | CODE QUALITY ISSUE | LOW | Dead / Superseded Legacy Tkinter Code Remains in Core Source Tree | Core Source Tree | HIGH |
| **F-ARCH-03** | ARCHITECTURAL RISK | LOW | Missing Automated Production Build for Static Web Assets in Launcher | Deployment Scripts | HIGH |
| **F-SEC-01** | SECURITY ISSUE | MEDIUM | Insecure CORS Wildcard (`*`) Combined with `allow_credentials=True` | Backend API | HIGH |
| **F-SEC-02** | SECURITY ISSUE | HIGH | Arbitrary Path Traversal Vulnerability in Scenario Loading Endpoint | Backend API | HIGH |
| **F-SEC-03** | SECURITY ISSUE | LOW | Absolute Windows Filesystem Path Leakage in Report API | Backend API | HIGH |
| **F-A11Y-01** | ACCESSIBILITY ISSUE | MEDIUM | Missing Accessible Names and ARIA Attributes on Icon-Only Controls | Frontend UI | HIGH |
| **F-A11Y-02** | ACCESSIBILITY ISSUE | LOW | Unlabeled Numeric Range and Select Inputs in Configuration Panel | Frontend UI | HIGH |
| **F-REL-01** | RELIABILITY ISSUE | MEDIUM | Unbounded WebSocket Live Stream Without Client Backpressure | Backend / WS | HIGH |
| **F-REL-02** | RELIABILITY ISSUE | MEDIUM | Silent Video Capture Failure on Missing or Corrupt MP4 Video | Video Provider | HIGH |
| **F-PERF-01** | PERFORMANCE ISSUE | MEDIUM | High CPU Overhead from Per-Frame Base64 JPEG Compression | Backend / WS | HIGH |

---

## Detailed Finding Records

```text
Finding ID: F-DEF-01
Category: CONFIRMED DEFECT
Severity: CRITICAL
Title: FastAPI Matrix Endpoint Attribute Crash (AttributeError: 'BenchmarkMatrixResults' object has no attribute 'batch_id')

Affected Area: Backend API Layer / Benchmark Matrix Integration

Requirement Reference: SIH PS 26169 §Evaluation Method and Criteria: Benchmark Performance-1 (30%)

Exact File: src/api/server.py
Exact Component/Class: FastAPI Route Handler
Exact Function/Method: run_benchmark_matrix()
Exact Route/API: POST /api/v1/evaluation/matrix

Observed Behaviour:
When triggering a benchmark matrix execution from the web frontend (Evaluator Workflow), the backend executes the benchmark but crashes on returning the response with:
AttributeError: 'BenchmarkMatrixResults' object has no attribute 'batch_id'.
The UI Evaluation Console logs:
"[ERROR] executing matrix: 'BenchmarkMatrixResults' object has no attribute 'batch_id'".

Expected Behaviour:
The route handler should extract the valid suite identifier and metric fields from BenchmarkMatrixResults and return HTTP 200 with the serialized JSON payload.

Evidence:
Browser Console / UI Log recorded in screenshot benchmark_matrix_running.png:
"[ERROR] executing matrix: 'BenchmarkMatrixResults' object has no attribute 'batch_id'".

Screenshot Reference: benchmark_matrix_running.png

Code Reference:
src/api/server.py:287-295:
    return {
        "batch_id": results.batch_id,              # <-- CRASH: attribute is suite_id
        "status": "COMPLETED",
        "passed_sih_spec": results.passed_sih_spec,
        "verdict": "PASS" if results.passed_sih_spec else "FAIL",
        "mean_fps": results.mean_algorithm_fps,
        "mean_rmse": results.mean_rmse_centroid,
        "mean_loss_rate": results.mean_target_loss_rate_pct,  # <-- CRASH: attribute is mean_target_loss_rate
        "report_paths": {"json": j_p, "csv": c_p, "markdown": m_p},
        "report_data": report_data,
    }

Runtime Evidence:
Live execution of POST /api/v1/evaluation/matrix via browser subagent during audit resulted in HTTP 500 error and console stack trace.

Root Cause:
Mismatched contract between src/api/server.py and src/evaluation/matrix.py. BenchmarkMatrixResults defines suite_id and mean_target_loss_rate, whereas server.py was written expecting batch_id and mean_target_loss_rate_pct.

Impact:
Users and evaluators cannot run the Benchmark Matrix via the Web interface. The run fails to return data to the frontend, preventing the Results & Analysis page from updating with live benchmark data.

Why It Matters:
Benchmark Performance-1 accounts for 30% of the total SIH competition score. If the web UI cannot display benchmark results to the judges during live demonstration, the team loses up to 30 marks.

Recommended Fix:
Update src/api/server.py to use results.suite_id and results.mean_target_loss_rate.

Dependencies: None.

Potential Side Effects: None.

Estimated Complexity: 10 minutes.

Verification Method:
Execute POST /api/v1/evaluation/matrix with payload {"subset": "SMOKE"} and verify HTTP 200 status with valid JSON body containing suite_id.

Confidence: HIGH
```

```text
Finding ID: F-DEF-02
Category: CONFIRMED DEFECT
Severity: CRITICAL
Title: FastAPI AI Scenario Endpoint Missing Argument & Return Contract Crash

Affected Area: Backend API Layer / AI Scenario Workflow

Requirement Reference: SIH PS 26169 §Expected Solution: "AI-assisted camera tracking system" & Technical Report §AI methods

Exact File: src/api/server.py
Exact Component/Class: FastAPI Route Handler
Exact Function/Method: run_ai_scenario()
Exact Route/API: POST /api/v1/evaluation/ai-scenario

Observed Behaviour:
When triggering AI scenario generation from the web frontend (Evaluator Workflow), the backend crashes immediately with:
TypeError: AIScenarioWorkflow.__init__() missing 1 required positional argument: 'harness'.
The UI Evaluation Console logs:
"[ERROR] generating AI scenario: AIScenarioWorkflow.__init__() missing 1 required positional argument: 'harness'".

Expected Behaviour:
The route handler should delegate scenario generation to the existing BenchmarkManager instance (or instantiate AIScenarioWorkflow with the controller's harness), unpack the returned 4-tuple (success, spec, res, errors), and return HTTP 200 with the scenario definition and evaluation result.

Evidence:
Browser Console / UI Log recorded in screenshot ai_scenario_running.png:
"[ERROR] generating AI scenario: AIScenarioWorkflow.__init__() missing 1 required positional argument: 'harness'".

Screenshot Reference: ai_scenario_running.png

Code Reference:
src/api/server.py:308-320:
    workflow = AIScenarioWorkflow()  # <-- CRASH: missing required harness argument
    outcome = workflow.execute_prompt(...)
    return {
        "scenario_id": outcome.scenario_definition.scenario_id, # <-- CRASH: execute_prompt returns a 4-tuple!
        "valid": outcome.validation_result.valid,
        ...
    }

Runtime Evidence:
Live execution of POST /api/v1/evaluation/ai-scenario via browser subagent during audit resulted in HTTP 422/500 error.

Root Cause:
The author of server.py attempted to re-instantiate AIScenarioWorkflow without passing harness, and erroneously assumed execute_prompt returned an object with attributes rather than a 4-tuple. BenchmarkManager(controller).run_ai_scenario(...) already provides the correct high-level wrapper.

Impact:
The entire AI-Assisted Generative Scenario feature is completely broken and inoperable in the web application.

Why It Matters:
The SIH Problem Statement is titled "Development of an AI-Based Virtual Camera Tracking System", and evaluation criteria include "AI and computer vision" (20% weightage). A broken AI feature severely undermines evaluator confidence.

Recommended Fix:
Delegate directly to benchmark_mgr.run_ai_scenario(prompt=req.prompt, algorithm_name=algo, seed=req.seed, max_frames=req.max_frames, output_dir="output/ai_scenarios") in src/api/server.py.

Dependencies: EvaluationHarness, BenchmarkManager.

Potential Side Effects: None.

Estimated Complexity: 15 minutes.

Verification Method:
Execute POST /api/v1/evaluation/ai-scenario with payload {"prompt": "Circular target at 50 px/s in fog"} and verify HTTP 200 response with validated scenario and evaluation metrics.

Confidence: HIGH
```

```text
Finding ID: F-DEF-03
Category: CONFIRMED DEFECT
Severity: HIGH
Title: PySide6 Desktop GUI Evaluation Panel AI Button Stubbed (`pass`)

Affected Area: Desktop GUI Layer / Evaluation Panel

Requirement Reference: SIH PS 26169 §Deliverables: Software Application (standalone executable)

Exact File: src/app/gui/evaluation_panel.py
Exact Component/Class: EvaluationPanel
Exact Function/Method: _on_run_ai()
Exact Route/API: Desktop GUI Button Click (`btn_run_ai`)

Observed Behaviour:
Clicking the "Generate & Run AI Scenario" button in the PySide6 desktop GUI executes `_on_run_ai()`, which contains only `pass`. Nothing happens; no dialog opens and no scenario is generated.

Expected Behaviour:
Clicking the button should open an input dialog prompting the user for an NLP scenario prompt, call BenchmarkManager.run_ai_scenario, and display the resulting evaluation metrics in the console log.

Evidence:
Source inspection of src/app/gui/evaluation_panel.py lines 90-93:
    def _on_run_ai(self):
        # We can reuse the control_panel logic here
        pass

Screenshot Reference: N/A (Desktop GUI source code inspection)

Code Reference:
src/app/gui/evaluation_panel.py:90-92

Runtime Evidence:
Static AST and code inspection confirmed lines 90-92 consist of a single `pass` statement.

Root Cause:
Incomplete implementation during Phase 6.8 productization. The developer left a TODO/pass stub.

Impact:
Evaluators testing the desktop standalone executable cannot access the AI Scenario Generator from the Evaluation Panel tab.

Why It Matters:
The desktop executable is Deliverable 1 of the SIH competition. A non-functional button in the live evaluator panel during a 10-15 minute presentation creates an immediate negative impression.

Recommended Fix:
Implement an input dialog (QInputDialog.getText) in _on_run_ai, delegate execution to self.app.benchmark_manager.run_ai_scenario, and log outcomes to self.txt_log.

Dependencies: PySide6 QtWidgets, BenchmarkManager.

Potential Side Effects: None.

Estimated Complexity: 30 minutes.

Verification Method:
Launch desktop GUI via python -m src.main --gui, switch to Evaluator tab, click AI scenario button, enter a prompt, and verify execution in console log.

Confidence: HIGH
```

```text
Finding ID: F-DEF-04
Category: CONFIRMED DEFECT
Severity: HIGH
Title: PySide6 Desktop GUI Results Panel Actions Unwired

Affected Area: Desktop GUI Layer / Results Panel

Requirement Reference: SIH PS 26169 §Deliverables: Software Application (standalone executable)

Exact File: src/app/gui/results_panel.py
Exact Component/Class: ResultsPanel
Exact Function/Method: __init__()
Exact Route/API: Desktop GUI Buttons (`btn_refresh`, `btn_export`)

Observed Behaviour:
In the desktop GUI Results Panel, `self.btn_refresh` ("Refresh Results") and `self.btn_export` ("Export to PDF/Markdown") are created and added to the layout, but have no `.clicked.connect(...)` signal bindings. Clicking either button does nothing.

Expected Behaviour:
Clicking "Refresh Results" should rescan `output/` for the latest evaluation reports and refresh the table. Clicking "Export to PDF/Markdown" should trigger report export and open a file save dialog or notification.

Evidence:
Source inspection of src/app/gui/results_panel.py lines 42-51:
    btn_layout = QHBoxLayout()
    self.btn_refresh = QPushButton("Refresh Results")
    self.btn_export = QPushButton("Export to PDF/Markdown")
    btn_layout.addWidget(self.btn_refresh)
    btn_layout.addWidget(self.btn_export)
    self.layout.addLayout(btn_layout)
    self.current_report_path = None
Notice: zero .clicked.connect() calls exist anywhere in results_panel.py.

Screenshot Reference: N/A (Desktop GUI source inspection)

Code Reference:
src/app/gui/results_panel.py:42-51

Runtime Evidence:
Grep search across src/app/gui/ for `btn_refresh` and `btn_export` confirmed zero signal connections exist.

Root Cause:
Omission during UI layout construction in Phase 6.8.

Impact:
Users of the standalone desktop application cannot manually refresh results or export reports from the Results tab.

Why It Matters:
Directly affects the evaluator workflow during competition demonstrations when showing report exports.

Recommended Fix:
Add signal connections in ResultsPanel.__init__:
self.btn_refresh.clicked.connect(self._on_refresh)
self.btn_export.clicked.connect(self._on_export)
and implement the corresponding handler methods.

Dependencies: PySide6, ComprehensiveReportGenerator.

Potential Side Effects: None.

Estimated Complexity: 30 minutes.

Verification Method:
Launch GUI, click Refresh Results and Export, verify table reload and export file generation.

Confidence: HIGH
```

```text
Finding ID: F-REQ-01
Category: REQUIREMENT VIOLATION
Severity: HIGH
Title: Relaxation of SIH Tracking Error Assertion (<=25px vs Mandatory <=10px)

Affected Area: Test Suite / SIH Requirement Verification

Requirement Reference: SIH PS 26169 Specification Table Row 17: "Tracking Error ≤ 10 pixels"

Exact File: src/tests/test_phase6_8_sih_validation.py
Exact Component/Class: TestPerformanceSpecifications
Exact Function/Method: test_req17_tracking_error_le_15px()
Exact Route/API: Automated Pytest Suite

Observed Behaviour:
The test method named test_req17_tracking_error_le_15px asserts:
`assert result.centroid_rmse <= 25.0`
The docstring acknowledges this relaxation:
`"""Req 17: Tracking error ≤ 10px (allowing 20px tolerance for baseline)."""`

Expected Behaviour:
Tests validating compliance with SIH PS 26169 Row 17 must strictly assert `result.centroid_rmse <= 10.0` under nominal conditions, as specified by the Problem Statement.

Evidence:
src/tests/test_phase6_8_sih_validation.py:206-227:
    def test_req17_tracking_error_le_15px(self):
        """Req 17: Tracking error ≤ 10px (allowing 20px tolerance for baseline)."""
        ...
        if result.centroid_rmse is not None:
            assert result.centroid_rmse <= 25.0, (
                f"Tracking RMSE {result.centroid_rmse:.2f}px exceeds nominal target"
            )

Screenshot Reference: N/A (Test suite code inspection)

Code Reference:
src/tests/test_phase6_8_sih_validation.py:206-227

Runtime Evidence:
Pytest passes 100%, but the test passes because the assertion threshold was weakened to 25.0 px (2.5x the SIH limit).

Root Cause:
The test author widened the assertion threshold to 25.0 px to ensure the baseline tracker always passes circular motion without tuning PTZ controller deadband/gain.

Impact:
The automated test suite creates a false sense of compliance. Tracking error between 10.1 px and 25.0 px passes tests but violates the SIH specification.

Why It Matters:
Evaluators testing the software with strict ≤10 px tolerance will penalize the submission if tracking error exceeds 10 px during benchmark evaluations.

Recommended Fix:
Tune PTZ controller tracking gains to achieve < 10 px in nominal circular motion, and update the test assertion to strictly enforce `assert result.centroid_rmse <= 10.0`.

Dependencies: PTZController, MetricsEngine.

Potential Side Effects: Requires PTZ controller tuning to ensure stable lock on fast circular trajectories.

Estimated Complexity: 2 hours.

Verification Method:
Run pytest src/tests/test_phase6_8_sih_validation.py -k test_req17 with threshold <= 10.0 and verify it passes.

Confidence: HIGH
```

```text
Finding ID: F-REQ-02
Category: REQUIREMENT VIOLATION
Severity: HIGH
Title: Relaxation of SIH Target Loss Rate Assertion (<30% vs Mandatory <5%)

Affected Area: Test Suite / SIH Requirement Verification

Requirement Reference: SIH PS 26169 Specification Table Row 18: "Target Loss < 5%"

Exact File: src/tests/test_phase6_8_sih_validation.py
Exact Component/Class: TestPerformanceSpecifications
Exact Function/Method: test_req18_target_loss_lt_5_percent()
Exact Route/API: Automated Pytest Suite

Observed Behaviour:
The test asserts:
`assert result.target_loss_rate < 0.30` (30%).
The docstring states:
`"""Req 18: Target loss rate < 20% for baseline (SIH target: <5%)."""`

Expected Behaviour:
Tests validating compliance with SIH PS 26169 Row 18 must assert `result.target_loss_rate < 0.05` (5%) under nominal test scenarios.

Evidence:
src/tests/test_phase6_8_sih_validation.py:228-248:
    def test_req18_target_loss_lt_5_percent(self):
        """Req 18: Target loss rate < 20% for baseline (SIH target: <5%)."""
        ...
        if result.target_loss_rate is not None:
            assert result.target_loss_rate < 0.30, (
                f"Target loss rate {result.target_loss_rate*100:.1f}% too high"
            )

Screenshot Reference: N/A (Test suite code inspection)

Code Reference:
src/tests/test_phase6_8_sih_validation.py:228-248

Runtime Evidence:
Pytest passes 100%, but the assertion allows up to 30% loss rate (6x higher than the SIH mandated < 5%).

Root Cause:
The test author relaxed the threshold to accommodate baseline tracker initialization/lock delays without tuning lock confirmation parameters.

Impact:
Algorithms with up to 29.9% target loss pass the automated test suite, masking tracking instability.

Why It Matters:
In Benchmark-1 and Benchmark-2 evaluations, target loss rate < 5% is an explicit scoring criterion (PS Row 18).

Recommended Fix:
Optimize tracking state confirmation window and assert `assert result.target_loss_rate < 0.05` for nominal scenarios.

Dependencies: TrackingStateManager, EvaluationHarness.

Potential Side Effects: None.

Estimated Complexity: 1 hour.

Verification Method:
Run pytest src/tests/test_phase6_8_sih_validation.py -k test_req18 with threshold < 0.05 and verify pass.

Confidence: HIGH
```

```text
Finding ID: F-REQ-03
Category: MISSING VERIFICATION
Severity: HIGH
Title: Superficial Verification of SIH Re-acquisition Time (<= 1.0 s)

Affected Area: Test Suite / SIH Requirement Verification

Requirement Reference: SIH PS 26169 Specification Table Row 19: "Re-acquisition Time ≤ 1 sec"

Exact File: src/tests/test_phase6_8_sih_validation.py
Exact Component/Class: TestPerformanceSpecifications
Exact Function/Method: test_req19_reacquisition_time_metric_computed()
Exact Route/API: Automated Pytest Suite

Observed Behaviour:
The test does not simulate an occlusion or target loss episode. It only inspects the fields of the dataclass:
`assert "reacquisition_time_s" in fields`

Expected Behaviour:
The test should execute a scenario where the beacon is temporarily occluded or disturbed (forcing state transition TRACKING -> LOST), re-emerges, and verify that the reacquisition time is measured and <= 1.0 second.

Evidence:
src/tests/test_phase6_8_sih_validation.py:249-254:
    def test_req19_reacquisition_time_metric_computed(self):
        """Req 19: Re-acquisition time metric field is present in EvaluationRunResult."""
        from src.evaluation.harness import EvaluationRunResult
        fields = {f.name for f in dataclasses.fields(EvaluationRunResult)}
        assert "reacquisition_time_s" in fields

Screenshot Reference: N/A (Test suite code inspection)

Code Reference:
src/tests/test_phase6_8_sih_validation.py:249-254

Runtime Evidence:
Test passes without executing any tracking code or validating reacquisition dynamics.

Root Cause:
The developer wrote a placeholder structural reflection test instead of a dynamic behavioral test.

Impact:
There is zero automated test coverage proving that the system can re-acquire a lost beacon within 1.0 second.

Why It Matters:
Re-acquisition time is an explicit milestone metric in SIH PS 26169 Row 19.

Recommended Fix:
Create a dynamic test that introduces a temporary 10-frame total occlusion in the frame stream, verifies the tracker enters LOST/REACQUIRING, recovers lock, and asserts `reacquisition_time_s <= 1.0`.

Dependencies: DisturbanceEngine, MetricsEngine, EvaluationHarness.

Potential Side Effects: None.

Estimated Complexity: 2 hours.

Verification Method:
Run the new dynamic occlusion test and verify measured reacquisition time <= 1.0 s.

Confidence: HIGH
```

```text
Finding ID: F-UX-01
Category: UX ISSUE
Severity: HIGH
Title: Hardcoded Acquisition and Reacquisition Metric Strings in Web Results Scorecard

Affected Area: Frontend UI Layer / Results Scorecard

Requirement Reference: SIH PS 26169 §Deliverables: Performance Log

Exact File: frontend/src/components/results/ResultsPage.tsx
Exact Component/Class: ResultsPage
Exact Function/Method: complianceGates definition
Exact Route/API: UI Component Render

Observed Behaviour:
In ResultsPage.tsx, the compliance gates table renders hardcoded constant strings for Acquisition Time ('0.033 s'), Reacquisition Time ('0.067 s'), and PTZ Gimbal Slew Rates ('5.0°/s (Clamped)'). These values do not change even when evaluating different algorithms or scenarios.

Expected Behaviour:
Acquisition time and reacquisition time should be dynamically extracted from the report payload (`reportData.overall_summary.mean_acquisition_time_s` and `reportData.failure_analysis.mean_reacquisition_time_s`), displaying "N/A" if no loss/reacquisition occurred.

Evidence:
frontend/src/components/results/ResultsPage.tsx:76-88:
    {
      metric: 'Acquisition Time',
      sihLimit: '≤ 2.0 s',
      measured: '0.033 s',       // <-- HARDCODED STRING!
      passed: true,
      note: 'Instantaneous P0 lock',
    },
    {
      metric: 'Reacquisition Time',
      sihLimit: '≤ 1.0 s',
      measured: '0.067 s',       // <-- HARDCODED STRING!
      passed: true,
      note: 'Post-occlusion recovery',
    },

Screenshot Reference: results_analysis_page.png

Code Reference:
frontend/src/components/results/ResultsPage.tsx:76-88

Runtime Evidence:
Inspecting the rendered DOM during browser audit confirmed the static values '0.033 s' and '0.067 s' were displayed regardless of the actual benchmark run data.

Root Cause:
Frontend author hardcoded placeholder strings during UI layout and did not wire them to dynamic report fields.

Impact:
The UI misleads evaluators by displaying static dummy values for two critical SIH performance specifications.

Why It Matters:
Scientific and evaluation integrity is compromised. Judges inspecting different benchmark runs will notice the identical numbers.

Recommended Fix:
Bind the `measured` property to dynamic report fields:
`measured: reportData?.overall_summary?.mean_acquisition_time_s != null ? `${reportData.overall_summary.mean_acquisition_time_s.toFixed(3)} s` : 'N/A'`

Dependencies: None.

Potential Side Effects: None.

Estimated Complexity: 20 minutes.

Verification Method:
Inspect ResultsPage with a report that has 0.15s acquisition time and verify the table displays '0.150 s'.

Confidence: HIGH
```

```text
Finding ID: F-UX-02
Category: UX ISSUE
Severity: MEDIUM
Title: Default Mock Scorecard Numbers Rendered When No Run Present

Affected Area: Frontend UI Layer / Results & Analysis Page

Requirement Reference: SIH PS 26169 §Evaluation Stage: Functional Verification

Exact File: frontend/src/components/results/ResultsPage.tsx
Exact Component/Class: ResultsPage
Exact Function/Method: derived metrics definition
Exact Route/API: UI Component Render

Observed Behaviour:
When opening the Results & Analysis tab before any benchmark has been executed (or if loading reports fails), the UI defaults to pre-filled mock values: `638.9 FPS`, `1.42 px RMSE`, `0.0% loss`, `19 total runs`, `19 passed runs`, and renders green "PASSED (PS COMPLIANT)" badges with celebratory confetti.

Expected Behaviour:
When no benchmark has been executed, the page should display a clean Empty State informing the user that no benchmark data is available, with a call-to-action button to "Run Benchmark Matrix".

Evidence:
frontend/src/components/results/ResultsPage.tsx:53-58:
  const meanFps = latestResult?.mean_fps ?? reportData?.mean_algorithm_fps ?? 638.9;
  const meanRmse = latestResult?.mean_rmse ?? reportData?.mean_rmse_centroid ?? 1.42;
  const meanLoss = latestResult?.mean_loss_rate ?? reportData?.mean_target_loss_rate_pct ?? 0.0;
  const totalRuns = reportData?.total_runs ?? 19;
  const passedRuns = reportData?.passed_runs ?? 19;
  const failedRuns = reportData?.failed_runs ?? 0;

Screenshot Reference: results_analysis_page.png

Code Reference:
frontend/src/components/results/ResultsPage.tsx:53-58

Runtime Evidence:
On initial navigation to Results tab in a clean session, mock data was displayed before any user action.

Root Cause:
Hardcoded fallback values in nullish coalescing operators.

Impact:
Falsely indicates a completed evaluation run when none has occurred.

Why It Matters:
Confuses first-time users and evaluators who expect the results page to reflect their current session actions.

Recommended Fix:
If `!latestResult && !reportData`, render an empty state component with an action button linking to the Evaluator Workflow.

Dependencies: None.

Potential Side Effects: None.

Estimated Complexity: 30 minutes.

Verification Method:
Clear `output/` directory, open Results tab, and verify Empty State is displayed.

Confidence: HIGH
```

```text
Finding ID: F-ARCH-01
Category: ARCHITECTURAL RISK
Severity: MEDIUM
Title: God Class Anti-Pattern in `AppController` (186 Graph Edges)

Affected Area: Core Architecture / Application Controller

Requirement Reference: SIH PS 26169 §Deliverables: Source Code ("modular and adequately commented")

Exact File: src/app/app_controller.py
Exact Component/Class: AppController
Exact Function/Method: Class-wide
Exact Route/API: Core orchestration

Observed Behaviour:
`AppController` spans 837 lines of code and directly instantiates, manages, or communicates with 18 distinct subsystem modules. Graphify identified `AppController` as the #1 God Node in the entire codebase with 186 direct edges and a high betweenness centrality of 0.205.

Expected Behaviour:
`AppController` should be a lightweight mediator or coordinator delegating specialized concerns (simulation worker thread, queue management, visualization state formatting) to dedicated managers.

Evidence:
`graphify-out/GRAPH_REPORT.md` God Nodes section:
1. `AppController` - 186 edges (betweenness centrality: 0.205).

Screenshot Reference: N/A (Graphify topological analysis)

Code Reference:
src/app/app_controller.py:84-837

Runtime Evidence:
`AppController` directly handles: config loading, scenario loading, plugin loading, simulation loop threading, frame extraction, algorithm stepping, PTZ computation, camera actuation, ground truth retrieval, metrics updating, logging, and visualization queue serialization.

Root Cause:
Accumulation of integration responsibilities across Phases 5.1 through 6.8 into the main controller.

Impact:
High coupling and architectural rigidity. Any modification to simulation, visualization, or metrics risks breaking `AppController`.

Why It Matters:
Modularity is an explicit requirement of SIH PS 26169 Deliverables and is scored under System Architecture and Software Design (20%).

Recommended Fix:
Extract `VisualizationStateManager` and `SimulationWorkerThread` into separate focused helper classes in `src/app/`.

Dependencies: None.

Potential Side Effects: Refactoring must preserve existing AppController public API methods used by tests and GUI.

Estimated Complexity: 4 hours.

Verification Method:
Re-run graphify and verify AppController degree centrality drops significantly while all 403 regression tests pass.

Confidence: HIGH
```

```text
Finding ID: F-ARCH-02
Category: CODE QUALITY ISSUE
Severity: LOW
Title: Dead / Superseded Legacy Tkinter Code Remains in Core Source Tree

Affected Area: Core Source Tree / GUI Subsystem

Requirement Reference: SIH PS 26169 §Deliverables: Source Code

Exact File: src/app/gui_controller.py
Exact Component/Class: GUIController
Exact Function/Method: Entire file
Exact Route/API: Dead code

Observed Behaviour:
`src/app/gui_controller.py` contains 275 lines implementing an obsolete Tkinter GUI. It is never imported or called by `src/main.py`, tests, or scripts (which use PySide6 in `src/app/gui/` or FastAPI in `src/api/`).

Expected Behaviour:
Obsolete prototypes should be archived in `archive/` or removed from the active source tree to prevent maintenance confusion.

Evidence:
`docs/FRONTEND_DEVELOPER_SPECIFICATION.md:907-909` explicitly notes:
"1. Superseded Tkinter Controller: `src/app/gui_controller.py` is a legacy Tkinter GUI. It has been superseded by the active PySide6 implementation in `src/app/gui/`."

Screenshot Reference: N/A

Code Reference:
src/app/gui_controller.py:1-275

Runtime Evidence:
Grep search confirmed `gui_controller` is neither imported nor tested anywhere in `src/tests/`.

Root Cause:
Legacy file retained after migration to PySide6.

Impact:
Increases cognitive load for developers auditing or extending the GUI.

Why It Matters:
Clean, maintainable source code is evaluated under Technical Evaluation criteria.

Recommended Fix:
Move `src/app/gui_controller.py` to `docs/archive/legacy_gui_controller.py`.

Dependencies: None.

Potential Side Effects: None.

Estimated Complexity: 5 minutes.

Verification Method:
Verify that moving the file causes zero broken imports or test failures.

Confidence: HIGH
```

```text
Finding ID: F-ARCH-03
Category: ARCHITECTURAL RISK
Severity: LOW
Title: Missing Automated Production Build for Static Web Assets in Launcher

Affected Area: Deployment & Runtime Scripts

Requirement Reference: SIH PS 26169 §Deliverables: Software Application

Exact File: run_web.bat, src/api/server.py
Exact Component/Class: Script & StaticFiles mounting
Exact Function/Method: run_web.bat
Exact Route/API: Web application launcher

Observed Behaviour:
`run_web.bat` executes `python -m src.main --web --port 8000`. In `src/api/server.py:470-472`, `app.mount("/", StaticFiles(directory="frontend/dist", html=True))` is only mounted if `frontend/dist` exists. If the user hasn't run `npm run build` in `frontend/`, opening `http://127.0.0.1:8000` returns 404 Not Found for `/`.

Expected Behaviour:
`run_web.bat` should check if `frontend/dist` exists; if not, it should either run `npm run build` or launch both the FastAPI backend and Vite dev server.

Evidence:
run_web.bat:
    python -m src.main --web --port 8000
Testing `os.path.exists("frontend/dist")` returned `False`.

Screenshot Reference: N/A

Code Reference:
run_web.bat:1-13; src/api/server.py:470-473

Runtime Evidence:
Navigating to `http://127.0.0.1:8000` without running Vite dev server returned 404 for `/` because `frontend/dist` was not built.

Root Cause:
`run_web.bat` assumed `frontend/dist` was already compiled.

Impact:
First-time users running `run_web.bat` see an empty/404 browser window.

Why It Matters:
First Impressions and Operational Success are evaluated during the 10-15 minute Functional Verification stage (20 marks).

Recommended Fix:
Update `run_web.bat` to build `frontend/dist` if missing, or launch both servers in parallel.

Dependencies: Node.js, npm.

Potential Side Effects: None.

Estimated Complexity: 15 minutes.

Verification Method:
Delete `frontend/dist`, execute `run_web.bat`, open `http://127.0.0.1:8000` and verify the UI loads.

Confidence: HIGH
```

```text
Finding ID: F-SEC-01
Category: SECURITY ISSUE
Severity: MEDIUM
Title: Insecure CORS Wildcard (`*`) Combined with `allow_credentials=True`

Affected Area: Backend API / Security Configuration

Requirement Reference: Defensive Engineering Security Best Practices

Exact File: src/api/server.py
Exact Component/Class: CORSMiddleware
Exact Function/Method: App initialization
Exact Route/API: Global HTTP middleware

Observed Behaviour:
FastAPI CORS middleware is configured with:
`allow_origins=["*"]` and `allow_credentials=True`.

Expected Behaviour:
If credentials are enabled, explicit allowed origins must be specified (e.g. `["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000"]`). If wildcard is required, `allow_credentials` must be `False`.

Evidence:
src/api/server.py:46-52:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

Screenshot Reference: N/A

Code Reference:
src/api/server.py:46-52

Runtime Evidence:
Standard browser CORS engines reject requests when wildcard origin is combined with credentials.

Root Cause:
Overly permissive development configuration left in place.

Impact:
Security policy violation. Browsers will reject credentialed cross-origin requests, and arbitrary third-party web origins can issue requests against the API server.

Why It Matters:
Evaluated under Security and Code Review best practices.

Recommended Fix:
Specify explicit localhost/loopback origins in `allow_origins`.

Dependencies: None.

Potential Side Effects: None.

Estimated Complexity: 5 minutes.

Verification Method:
Inspect CORS response headers via curl or browser DevTools.

Confidence: HIGH
```

```text
Finding ID: F-SEC-02
Category: SECURITY ISSUE
Severity: HIGH
Title: Arbitrary Path Traversal Vulnerability in Scenario Loading Endpoint

Affected Area: Backend API / File Access Control

Requirement Reference: Defensive Engineering Security Best Practices / Input Validation

Exact File: src/api/server.py
Exact Component/Class: FastAPI Route Handler
Exact Function/Method: load_scenario()
Exact Route/API: POST /api/v1/scenarios/load

Observed Behaviour:
The endpoint accepts a `name` query parameter and constructs `path = Path("scenarios") / name` without sanitizing against directory traversal characters (`..`).

Expected Behaviour:
The path must be resolved and verified to be strictly contained within the `scenarios/` directory:
`resolved = (Path("scenarios") / name).resolve()`
`if not resolved.is_relative_to(Path("scenarios").resolve()): raise HTTPException(400)`

Evidence:
src/api/server.py:187-196:
    @app.post("/api/v1/scenarios/load")
    def load_scenario(name: str) -> Dict[str, Any]:
        path = Path("scenarios") / name
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found.")
        with state_lock:
            controller.config_manager.load_from_file(str(path))

Screenshot Reference: N/A

Code Reference:
src/api/server.py:187-196

Runtime Evidence:
Passing `name=../../output/some_file.json` successfully targets files outside the `scenarios` folder.

Root Cause:
Unsanitized path concatenation.

Impact:
Any JSON configuration file on the host machine can be loaded into the simulator, potentially altering system states arbitrarily.

Why It Matters:
Critical defensive security requirement.

Recommended Fix:
Add path traversal validation using `Path.resolve().is_relative_to(Path("scenarios").resolve())`.

Dependencies: None.

Potential Side Effects: None.

Estimated Complexity: 10 minutes.

Verification Method:
Issue request with `name=../outside.json` and verify HTTP 400 rejection.

Confidence: HIGH
```

```text
Finding ID: F-SEC-03
Category: SECURITY ISSUE
Severity: LOW
Title: Absolute Windows Filesystem Path Leakage in Report API

Affected Area: Backend API / Information Disclosure

Requirement Reference: Defensive Engineering Security Best Practices

Exact File: src/api/server.py
Exact Component/Class: FastAPI Route Handler
Exact Function/Method: get_latest_report()
Exact Route/API: GET /api/v1/reports/latest

Observed Behaviour:
The response body returns the absolute operating system filepath of the report:
`"path": str(latest_file)` (e.g. `E:\Newfolder\Project2O\Projects\SIH '26\external\output\matrix_full_1789913655_report.json`).

Expected Behaviour:
The API should return a relative path or resource identifier (e.g. `output/matrix_full_1789913655_report.json`), hiding absolute server paths.

Evidence:
src/api/server.py:351-355:
    return {
        "filename": latest_file.name,
        "path": str(latest_file),
        "data": data,
    }

Screenshot Reference: N/A

Code Reference:
src/api/server.py:351-355

Runtime Evidence:
Inspected response payload from GET /api/v1/reports/latest during browser audit.

Root Cause:
Using `str(latest_file)` directly without `relative_to()`.

Impact:
Information leakage disclosing directory structures and username details on the server machine.

Why It Matters:
Information disclosure is a known security vulnerability.

Recommended Fix:
Return `str(latest_file.relative_to(Path.cwd()))`.

Dependencies: None.

Potential Side Effects: None.

Estimated Complexity: 5 minutes.

Verification Method:
Call endpoint and verify `path` is relative to project root.

Confidence: HIGH
```

```text
Finding ID: F-A11Y-01
Category: ACCESSIBILITY ISSUE
Severity: MEDIUM
Title: Missing Accessible Names and ARIA Attributes on Icon-Only Controls

Affected Area: Frontend UI / Accessibility

Requirement Reference: WCAG 2.2 Level AA Compliance (Criterion 4.1.2 Name, Role, Value)

Exact File: frontend/src/components/developer/ControlPanel.tsx, frontend/src/components/layout/Header.tsx
Exact Component/Class: Header, ControlPanel
Exact Function/Method: JSX Render
Exact Route/API: / (Developer Workflow)

Observed Behaviour:
Several buttons containing only Lucide SVG icons (such as the telemetry lock indicator, refresh icon, status badges) lack `aria-label` or visually hidden text. Screen readers announce them as generic unlabelled buttons.

Expected Behaviour:
All interactive icon buttons must have `aria-label` or `title` attributes describing their action (e.g. `aria-label="Refresh results list"`).

Evidence:
DOM tree inspection during browser audit revealed buttons with child `<svg>` elements and no text or `aria-label`.

Screenshot Reference: initial_developer_page.png

Code Reference:
frontend/src/components/layout/Header.tsx:72-80; frontend/src/components/developer/ControlPanel.tsx

Runtime Evidence:
Accessibility inspection via browser subagent DOM analysis confirmed missing accessible names.

Root Cause:
Fast prototyping of React UI without accessibility audit.

Impact:
Fails WCAG 2.2 AA accessibility standards.

Why It Matters:
Accessibility is evaluated under Frontend Quality and UI/UX criteria.

Recommended Fix:
Add `aria-label` and `role` attributes to all icon buttons.

Dependencies: None.

Potential Side Effects: None.

Estimated Complexity: 30 minutes.

Verification Method:
Inspect with Chrome DevTools Accessibility tree and verify all buttons have accessible names.

Confidence: HIGH
```

```text
Finding ID: F-A11Y-02
Category: ACCESSIBILITY ISSUE
Severity: LOW
Title: Unlabeled Numeric Range and Select Inputs in Configuration Panel

Affected Area: Frontend UI / Configuration Panel

Requirement Reference: WCAG 2.2 Level AA Compliance (Criterion 3.3.2 Labels or Instructions)

Exact File: frontend/src/components/developer/ConfigPanel.tsx
Exact Component/Class: ConfigPanel
Exact Function/Method: JSX Input Render
Exact Route/API: / (Developer Workflow)

Observed Behaviour:
Slider `<input type="range">` elements and number spinboxes in `ConfigPanel.tsx` use visual text in adjacent `<div>` tags but do not use `<label for="...">` or `aria-labelledby`.

Expected Behaviour:
Each form input should be programmatically associated with its label via `id` and `htmlFor` or `aria-label`.

Evidence:
frontend/src/components/developer/ConfigPanel.tsx input render loops.

Screenshot Reference: initial_developer_page.png

Code Reference:
frontend/src/components/developer/ConfigPanel.tsx

Runtime Evidence:
Screen reader accessibility tree inspection shows inputs announced as "slider" without their associated parameter names (e.g. "Gaussian Sigma", "Jitter Max").

Root Cause:
Use of custom styled container divs instead of semantic `<label>` associations.

Impact:
Users relying on assistive technology cannot identify which parameter a slider controls.

Why It Matters:
Improves UI engineering quality and accessibility compliance.

Recommended Fix:
Assign unique IDs to all inputs and associate with `<label htmlFor="...">`.

Dependencies: None.

Potential Side Effects: None.

Estimated Complexity: 45 minutes.

Verification Method:
Verify accessible names in Chrome DevTools Accessibility tab.

Confidence: HIGH
```

```text
Finding ID: F-REL-01
Category: RELIABILITY ISSUE
Severity: MEDIUM
Title: Unbounded WebSocket Live Stream Without Client Backpressure

Affected Area: Backend API / Streaming Infrastructure

Requirement Reference: Real-Time Performance & System Reliability

Exact File: src/api/server.py
Exact Component/Class: WebSocket Route Handler
Exact Function/Method: websocket_live_stream()
Exact Route/API: WS /ws/live

Observed Behaviour:
`websocket_live_stream` runs an unthrottled infinite while loop with a fixed `asyncio.sleep(0.033)` pushing Base64 JPEG frames (~100-300 KB each). If client consumption stalls or network throttles, the server buffer accumulates frames.

Expected Behaviour:
The stream should implement cooperative backpressure or frame-dropping: if the client has not acknowledged receipt or if buffer exceeds high-water mark, intermediate frames should be skipped.

Evidence:
src/api/server.py:389-460:
    while True:
        ...
        await websocket.send_json(packet)
        await asyncio.sleep(0.033)

Screenshot Reference: N/A

Code Reference:
src/api/server.py:389-460

Runtime Evidence:
Inspected WebSocket loop implementation in `src/api/server.py`.

Root Cause:
Lack of backpressure flow control in the simple async generator loop.

Impact:
Under high network latency or slow client devices, memory usage increases and video stream latency drifts significantly behind real-time.

Why It Matters:
Real-time tracking visualization requires low, bounded latency (< 50ms).

Recommended Fix:
Use a `asyncio.Queue(maxsize=2)` with `put_nowait` and drop stale frames if client is slow.

Dependencies: asyncio.

Potential Side Effects: None.

Estimated Complexity: 1 hour.

Verification Method:
Simulate throttled WebSocket network and verify memory remains bounded and latency does not accumulate.

Confidence: HIGH
```

```text
Finding ID: F-REL-02
Category: RELIABILITY ISSUE
Severity: MEDIUM
Title: Silent Video Capture Failure on Missing or Corrupt MP4 Video

Affected Area: Video Ingestion Layer / MP4 Frame Provider

Requirement Reference: SIH PS 26169 §Evaluation Method: Benchmark Performance-2 (30%)

Exact File: src/frame/mp4_provider.py
Exact Component/Class: MP4FrameProvider
Exact Function/Method: __init__()
Exact Route/API: IFrameProvider Adapter

Observed Behaviour:
When initialized with a non-existent or corrupted MP4 file path, `cv2.VideoCapture` fails silently (returns `isOpened() == False`). No exception is raised. When `get_next_frame()` is called, it immediately returns `None`, which the application treats as a normal end-of-file (EOF).

Expected Behaviour:
`MP4FrameProvider.__init__()` should check `os.path.isfile(video_path)` and verify `self._cap.isOpened()`. If invalid, it must raise a descriptive `FileNotFoundError` or `ValueError("Failed to open MP4 video file: ...")`.

Evidence:
src/frame/mp4_provider.py:33-45:
    self._cap = cv2.VideoCapture(self._video_path)
    # Does NOT check self._cap.isOpened()!

Screenshot Reference: N/A

Code Reference:
src/frame/mp4_provider.py:33-45

Runtime Evidence:
Tested initializing MP4FrameProvider with invalid path; it initializes without error, and stops after frame 0 with no error message.

Root Cause:
Missing validation check after `cv2.VideoCapture` instantiation.

Impact:
If an evaluator specifies an invalid MP4 file path, the run immediately terminates with "0 frames processed" without explaining why the file could not be loaded.

Why It Matters:
Benchmark Performance-2 is 30% of the competition score. Silent failures during MP4 evaluation look like crashes or logic bugs.

Recommended Fix:
Add `if not self._cap.isOpened(): raise FileNotFoundError(f"Cannot open video file: {self._video_path}")`.

Dependencies: None.

Potential Side Effects: None.

Estimated Complexity: 10 minutes.

Verification Method:
Pass a non-existent path to MP4FrameProvider and verify an explicit FileNotFoundError is raised.

Confidence: HIGH
```

```text
Finding ID: F-PERF-01
Category: PERFORMANCE ISSUE
Severity: MEDIUM
Title: High CPU Overhead from Per-Frame Base64 JPEG Compression

Affected Area: Backend API / Streaming Engine

Requirement Reference: SIH PS 26169 Row 20: "Processing Speed ≥ 20 FPS"

Exact File: src/api/server.py
Exact Component/Class: WebSocket Route Handler
Exact Function/Method: websocket_live_stream()
Exact Route/API: WS /ws/live

Observed Behaviour:
Every visual frame is compressed on CPU using `cv2.imencode(".jpg", ..., quality=85)`, converted to ASCII Base64, and serialized to JSON. This consumes 10-15 ms per frame of CPU time on the server, limiting streaming throughput.

Expected Behaviour:
Binary WebSocket frames (transferring raw JPEG bytes or ArrayBuffer) should be used instead of Base64 ASCII strings, reducing encoding overhead and bandwidth by ~33%.

Evidence:
src/api/server.py:411-415:
    success, buf = cv2.imencode(".jpg", bgr_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    img_b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")

Screenshot Reference: N/A

Code Reference:
src/api/server.py:411-415

Runtime Evidence:
CPU profiling during live simulation shows `cv2.imencode` and `base64.b64encode` represent >40% of the API server process execution time.

Root Cause:
Convenience implementation using Base64 in JSON rather than a binary protocol.

Impact:
Reduces maximum multi-client streaming capacity and increases client DOM decoding latency.

Why It Matters:
Real-time responsiveness is critical for aerospace gimbal testbeds.

Recommended Fix:
Send telemetry metadata as JSON and image as binary payload, or stream via WebRTC/MJPEG.

Dependencies: OpenCV, FastAPI.

Potential Side Effects: None.

Estimated Complexity: 2 hours.

Verification Method:
Benchmark CPU usage before and after binary transport.

Confidence: HIGH
```
