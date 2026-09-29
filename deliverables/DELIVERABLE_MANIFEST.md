# SANKET — OFFICIAL DELIVERABLES MANIFEST
## SIH 2026 Problem Statement 26169 (Department of Space / ISRO)

**System Name:** SANKET — AI-Assisted Free-Space Optical Communication (FSOC) Tracking System  
**Organization:** Department of Space / Indian Space Research Organisation (ISRO)  
**Manifest Generated:** 2026-09-30 03:33 UTC+05:30  
**Verification Baseline:** Strict Non-Fabrication Rule, Direct Source Inspection & Runtime Execution  

---

## Deliverables Status Summary Matrix

| # | Deliverable Name | Required? | File / Folder Location | Status | Verification Evidence & Provenance |
| :-: | :--- | :-: | :--- | :--- | :--- |
| **01** | **Software Application** | **MANDATORY** | `deliverables/01_Software_Application/`<br>├── `SANKET/SANKET.exe`<br>├── `installer/SANKET-Setup-v1.0.exe`<br>└── `portable/SANKET-Portable-v1.0.zip` | **COMPLETE** | Standalone PyInstaller ONEDIR package. Embedded QtWebEngine GUI, bundled scenarios, models, official logo branding, and MSVC runtime. Verified via `SANKET.exe --validate` (8/8 passed) and standalone setup installation. |
| **02** | **Source Code** | **MANDATORY** | `deliverables/02_Source_Code/`<br>├── `SANKET_Source.zip`<br>└── `SOURCE_CODE_README.md` | **COMPLETE** | 26.53 MB clean source zip (281 files). Excludes `node_modules`, `dist`, `build`, `__pycache__`, `.venv`, and build caches. Full reproduction instructions verified. |
| **03** | **Technical Report** | **MANDATORY** | `deliverables/03_Technical_Report/`<br>├── `SANKET_Technical_Report.md`<br>├── `SANKET_Technical_Report.pdf`<br>└── `figures/` (10 real runtime figures) | **COMPLETE** | Comprehensive 14-page formal report covering system architecture, mathematical models, computer vision pipeline, PID control laws, ML candidate classifier, and verified test results with official branding. |
| **04** | **User Manual** | **MANDATORY** | `deliverables/04_User_Manual/`<br>├── `SANKET_User_Manual.md`<br>└── `figures/` (10 real runtime figures) | **COMPLETE** | 26-section operational guide covering installation, 5 production workspaces, 3 Developer sub-views, disturbance configuration, benchmark execution, and troubleshooting. |
| **05** | **Performance Log** | **MANDATORY** | `deliverables/05_Performance_Log/`<br>├── `run_1790716901_summary.json`<br>├── `run_1790716901_telemetry.csv`<br>├── `run_1790716901_centroids.csv`<br>├── `run_1790716901_config.json`<br>├── `run_1790716901_performance_report.md`<br>└── `PERFORMANCE_LOG_README.md` | **COMPLETE** | Real runtime telemetry automatically generated during clean execution of `scenario_2_circular` (900 frames / 29.97 s). Measured: 461.8 FPS, 0.07 s acq, 4.82 px mean error. |
| **06** | **Demonstration Video** | **OPTIONAL** | `deliverables/06_Optional_Demo_Video/`<br>└── `VIDEO_SUBMISSION_STATUS.md` | **NOT AVAILABLE (READY FOR LIVE DEMO)** | Marked unavailable due to absence of audio recording and video capture hardware in automated agent environment. Standalone executable is fully verified for live evaluator demonstration. |

---

## Benchmark Capability & Feature Audit

| Subsystem / Feature | Required Specification | Implementation Status | Evidence & Limitations |
| :--- | :--- | :--- | :--- |
| **Benchmark-1 (Scenarios)** | Automated evaluation of predefined motion scenarios with centroid error logging | **COMPLETE** | Fully implemented in `BenchmarkManager` (`src/evaluation/benchmark_manager.py`). Bundled scenarios: `scenario_1_static`, `scenario_2_circular`, `scenario_3_figure8`, `scenario_4_fog_gaussian`. |
| **Benchmark-2 (External MP4)** | Ingestion of 30 FPS MP4 video with PTZ bypassed and comparison against reference CSV | **COMPLETE WITH LIMITATION** | Software implementation complete (`src/frame/mp4_provider.py`, `src/evaluation/benchmark_manager.py`). 8 unit tests passed (`test_bm2_workflow.py`). **Limitation:** Repository contains no pre-recorded `.mp4` test media; ready for external input from evaluators. |
| **AI Clutter Classifier** | Machine learning model to reject noise candidates | **COMPLETE** | Calibrated 4-feature Logistic Regression model (`lr_model.json`, `src/aiml/candidate_classifier.py`) with seamless rule-based fallback. |
| **5 Production Workspaces** | Developer, Evaluator, Diagnostics, History, Results | **COMPLETE** | Verified via interactive QtWebEngine automated harness. Zero JavaScript errors. |
| **Developer Sub-Views** | 2D Sensor, 3D Pedestal, 2000×2000 World Canvas | **COMPLETE** | Integrated seamlessly in Developer Workspace with full cross-tab synchronization and ground-truth firewall. |
| **Automated Test Suite** | Comprehensive unit & integration testing | **COMPLETE** | 492 / 492 tests passing in 19.39 s (`pytest`). |
