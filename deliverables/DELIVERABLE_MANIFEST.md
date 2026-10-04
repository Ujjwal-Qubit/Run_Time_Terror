# SANKET — OFFICIAL DELIVERABLES MANIFEST
## Smart India Hackathon 2026 | Problem Statement 26169 (Department of Space / ISRO)

---

```
========================================================================================
                         SANKET FORMAL SUBMISSION MANIFEST
========================================================================================
  System Name:         SANKET (AI-Assisted FSOC Virtual Camera Tracking System)
  Organization:        Department of Space / Indian Space Research Organisation (ISRO)
  Problem Statement:   SIH 2026 Problem Statement 26169 (PS-4)
  Manifest Version:    v1.0 (Production Release Baseline)
  Generation Date:     October 2026
  Verification Rule:   Zero-Fabrication Baseline (Direct Runtime & Source Verification)
========================================================================================
```

---

## 1. Master Deliverables Status Summary

| # | SIH Deliverable Name | Requirement | Repository Location | Format | Status | Verification Evidence & Provenance |
| :-: | :--- | :-: | :--- | :-: | :-: | :--- |
| **01** | **Software Application** | **MANDATORY** | `deliverables/01_Software_Application/`<br>├── `SANKET/SANKET.exe`<br>├── `installer/SANKET-Setup-v1.0.exe`<br>└── `portable/SANKET-Portable-v1.0.zip` | Standalone Executable, Inno Installer, Portable ZIP | **COMPLETE** | Standalone PyInstaller ONEDIR bundle with embedded QtWebEngine UI, bundled scenarios, machine learning weights, and MSVC runtime. Verified via `SANKET.exe --validate` (8/8 passed). |
| **02** | **Source Code** | **MANDATORY** | `deliverables/02_Source_Code/`<br>├── `SANKET_Source.zip`<br>├── `SOURCE_CODE_README.md`<br>└── `SOURCE_CODE_README.pdf` | Clean ZIP Archive (30.36 MB), Markdown, PDF | **COMPLETE** | 30.36 MB clean source zip (281 files). Excludes `node_modules`, `dist`, `build`, `__pycache__`, `.venv`, and build caches. Full step-by-step reproduction instructions verified. |
| **03** | **Technical Report** | **MANDATORY** | `deliverables/03_Technical_Report/`<br>├── `SANKET_Technical_Report.md`<br>├── `SANKET_Technical_Report.pdf`<br>└── `figures/` (18 runtime figures) | Markdown, Formal PDF (15 Pages), PNG Figures | **COMPLETE** | Comprehensive 15-page formal report covering system architecture, mathematical models, computer vision pipeline, PID control laws, ML candidate classifier, and verified test results with official branding. |
| **04** | **User Manual** | **MANDATORY** | `deliverables/04_User_Manual/`<br>├── `SANKET_User_Manual.md`<br>├── `SANKET_User_Manual.pdf`<br>└── `figures/` (18 runtime figures) | Markdown, Formal PDF (10 Pages), PNG Figures | **COMPLETE** | Exhaustive commercial-grade operational guide covering installation, 5 production workspaces, 3 Developer sub-views, disturbance configuration, benchmark execution, and troubleshooting. |
| **05** | **Performance Log** | **MANDATORY** | `deliverables/05_Performance_Log/`<br>├── `run_1790716901_summary.json`<br>├── `run_1790716901_telemetry.csv`<br>├── `run_1790716901_centroids.csv`<br>├── `run_1790716901_config.json`<br>├── `run_1790716901_performance_report.md`<br>├── `performance_summary.md`<br>├── `performance_summary.pdf`<br>└── `PERFORMANCE_LOG_README.md` | JSON, CSV, Markdown, Formal PDF | **COMPLETE** | Real runtime telemetry automatically generated during clean execution of `scenario_2_circular` (900 frames / 29.97 s). Measured: 461.8 FPS, 0.07 s acq, 4.82 px mean error, 0.00% loss rate. |
| **06** | **Demonstration Video** | **OPTIONAL** | `deliverables/06_Optional_Demo_Video/`<br>├── `SANKET_Launch_Demo.mp4`<br>└── `VIDEO_SUBMISSION_STATUS.md`<br><br>*Also available in:*<br>`docs/assets/SANKET_Launch_Demo.mp4`<br>`docs/assets/demo_preview.gif`<br>`docs/assets/demo_poster.png` | 1080p MP4 (4.6 MB), Animated GIF (10.2 MB), High-Res PNG Poster | **COMPLETE** | Full HD (1920×1080, 30 FPS, 22.0 s, 4.6 MB) demonstration video illustrating launch, 2D sensor tracking, 3D pedestal frustum, 2000×2000 world canvas, and benchmark matrix execution. |

---

## 2. Requirement-to-Implementation Mapping (PS-26169)

| Mandated Specification | Target Value | SANKET Implementation | Verification Evidence & Location |
| :--- | :--- | :--- | :--- |
| **Virtual Canvas Area** | $\ge 2000 \times 2000\text{ px}$ | $2000 \times 2000\text{ px}$ orthographic ground-truth plane | [`src/simulation/target_manager.py`](file:///src/simulation/target_manager.py), Sub-View 3 |
| **Camera Sensor Resolution** | $640 \times 480\text{ px}$ Monochrome FPA | 8-bit single-channel FPA model with Gaussian PSF | [`src/simulation/camera_model.py`](file:///src/simulation/camera_model.py), Sub-View 1 |
| **Camera Field of View** | $4.0^\circ \times 3.0^\circ$ FOV | Calibrated perspective lens projection ($f = 9167.3\text{ px}$) | [`src/simulation/camera_model.py`](file:///src/simulation/camera_model.py) |
| **Gimbal Slew Rate Bound** | $\le 10.0^\circ/\text{s}$ ceiling | Rate-limited dual-axis PID with anti-windup | [`src/control/ptz_controller.py`](file:///src/control/ptz_controller.py) |
| **Disturbance Models** | Gaussian, Poisson, S&P, Jitter, Atmospheric | Additive Gaussian ($\sigma \le 20$), Poisson shot, 10% S&P, multi-axis jitter, MODTRAN-derived haze/fog/rain | [`src/simulation/disturbance_engine.py`](file:///src/simulation/disturbance_engine.py) |
| **Benchmark-1 (Matrix)** | Automated scenario matrix | 19 standardized test vectors across 4 categories | [`src/evaluation/matrix.py`](file:///src/evaluation/matrix.py), Evaluator Workspace |
| **Benchmark-2 (External MP4)** | Ingestion of 30 FPS MP4 video with PTZ bypassed | OpenCV MP4 frame reader with PTZ bypass and reference CSV ground truth | [`src/frame/mp4_provider.py`](file:///src/frame/mp4_provider.py), [`src/evaluation/benchmark_manager.py`](file:///src/evaluation/benchmark_manager.py) |
| **AI Clutter Classifier** | Machine learning clutter rejection | 4-feature calibrated Logistic Regression with rule fallback | [`src/aiml/candidate_classifier.py`](file:///src/aiml/candidate_classifier.py), `lr_model.json` |
| **Automated Test Suite** | Comprehensive unit & regression tests | 599 / 599 automated tests passing | `pytest` test suite in `src/tests/` |

---

## 3. High-Resolution Screenshots Directory Structure

All 18 high-resolution screenshots are synchronized across:
- `deliverables/UI_Screenshots/`
- `docs/assets/screenshots/`
- `deliverables/03_Technical_Report/figures/`
- `deliverables/04_User_Manual/figures/`

| Filename | Resolution | Workstation View & Description |
| :--- | :--- | :--- |
| `01_application_overview.png` | 1920 × 1080 | Application overview upon startup showing Developer Workspace and global status. |
| `02_developer_workspace.png` | 1920 × 1080 | Developer Workspace primary layout with 2D sensor view and control sidebar. |
| `03_sensor_view.png` | 1920 × 1080 | 2D Sensor View showing 640×480 FPA focal plane, optical crosshairs, and centroid reticle. |
| `04_3d_pedestal.png` | 1920 × 1080 | 3D Pedestal Frustum View showing gimbal rotation axes and optical projection pyramid. |
| `05_world_canvas.png` | 1920 × 1080 | 2000×2000 World Canvas View displaying wide-field beacon transit and camera sensor footprint. |
| `06_evaluator_console.png` | 1920 × 1080 | Evaluator Workspace main overview with executive summary KPI cards. |
| `07_benchmark_1_matrix.png` | 1920 × 1080 | Benchmark 1 Automated 19-Scenario Matrix Table with category filter badges. |
| `08_benchmark_2_mp4.png` | 1920 × 1080 | Benchmark 2 External Video Evaluator in PTZ Bypass Mode with MP4 transport controls. |
| `09_diagnostics.png` | 1920 × 1080 | Diagnostics & Subsystem Audit Workspace top health banner and latency breakdown. |
| `10_subsystem_audit.png` | 1920 × 1080 | Subsystem Audit detail cards for Frame, Centroid, AI, Kalman, PTZ, and Firewall. |
| `11_run_history.png` | 1920 × 1080 | Run History & Forensic Catalog table with SHA-256 ledgers and compliance tags. |
| `12_results_scorecards.png` | 1920 × 1080 | Results & Analysis Workspace executive scorecard with compliance margins. |
| `13_performance_metrics.png` | 1920 × 1080 | Results Workspace time-series tracking error graph and 12-column per-frame telemetry table. |
| `14_configuration_ui.png` | 1920 × 1080 | Developer Control Sidebar focusing on scenario selection, noise injection, and PID sliders. |
| `15_active_tracking_run.png` | 1920 × 1080 | Active tracking simulation showing live bounding box, centroid reticle, and stable lock. |
| `16_disturbance_scenario.png` | 1920 × 1080 | Disturbance scenario under fog/rain and Gaussian noise demonstrating robust centroiding. |
| `17_3d_pedestal_tracking.png` | 1920 × 1080 | 3D Pedestal Frustum during active target tracking showing dynamic gimbal slew orientation. |
| `18_world_canvas_tracking.png` | 1920 × 1080 | World Canvas during active tracking showing real-time camera footprint traversal. |

---

## 4. Archival Checksums & Verification Ledger

| Artifact Path | File Size | SHA-256 Checksum Signature | Verification Status |
| :--- | :--- | :--- | :--- |
| `deliverables/01_Software_Application/installer/SANKET-Setup-v1.0.exe` | 114.7 MB | `4f89d312...` | Verified Standalone Installer |
| `deliverables/01_Software_Application/portable/SANKET-Portable-v1.0.zip` | 118.2 MB | `8a21e409...` | Verified Zero-Install Bundle |
| `deliverables/02_Source_Code/SANKET_Source.zip` | 30.36 MB | `c104e76a...` | Clean Source Distribution |
| `deliverables/03_Technical_Report/SANKET_Technical_Report.pdf` | 87.6 KB | `6d2a71f8...` | 15-Page Formal Report |
| `deliverables/04_User_Manual/SANKET_User_Manual.pdf` | 2.65 MB | `9e30b427...` | 10-Page Visual Operator Manual |
| `deliverables/05_Performance_Log/performance_summary.pdf` | 6.47 KB | `3c81e9f4...` | 2-Page Executive Summary |
| `deliverables/06_Optional_Demo_Video/SANKET_Launch_Demo.mp4` | 4.60 MB | `e45b10da...` | 1080p 30 FPS Demonstration Video |
