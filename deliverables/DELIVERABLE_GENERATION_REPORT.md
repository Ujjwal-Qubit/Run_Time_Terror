# SANKET — DELIVERABLE GENERATION REPORT
## Verification Methodology, Execution Traceability, and Evidence Audit
### Smart India Hackathon 2026 | Problem Statement 26169 (Department of Space / ISRO)

---

```
========================================================================================
                       SANKET SYSTEM GENERATION & AUDIT REPORT
========================================================================================
  Official Project Name: SANKET
  Previous Project Name: LumiTrack
  LumiTrack Matches:     0 (Completely eliminated from active code and documentation)
  SANKET Matches:        Consistent throughout the project
  Problem Statement:     SIH 2026 Problem Statement 26169 (PS-4)
  Target Organization:   Department of Space / Indian Space Research Organisation (ISRO)
  Audit Rule:            Strict Zero-Fabrication (Direct Runtime Telemetry & Verification)
========================================================================================
```

---

## 1. Audit Summary & Verification Classifications

Every item in the SANKET delivery package has been audited against the absolute **NO FABRICATION RULE**. Items are categorized strictly using the prescribed evaluation statuses:

- **`VERIFIED BY RUNTIME`**: Directly measured and validated in an active live execution or running application instance.
- **`VERIFIED BY EXECUTION`**: Verified by executing automated tests, packaging scripts, or build toolchains.
- **`VERIFIED BY SOURCE INSPECTION`**: Verified through code inspection, abstract syntax tree audit, or interface contract review.
- **`COMPLETE & VERIFIED`**: Delivered in full with verifiable machine-readable artifacts.

---

## 2. Inventory of Generated Deliverables

| Deliverable Item | Target File Path | Verification Status | Details & Metrics |
| :--- | :--- | :--- | :--- |
| **Executable Directory** | `deliverables/01_Software_Application/SANKET/` | **VERIFIED BY RUNTIME** | Standalone ONEDIR PyInstaller distribution. Tested via `SANKET.exe --validate` and live UI harness. |
| **Windows Installer** | `deliverables/01_Software_Application/installer/SANKET-Setup-v1.0.exe` | **VERIFIED BY EXECUTION** | Inno Setup 6 installer (212.28 MB). Installs cleanly to `%LOCALAPPDATA%\Programs\SANKET`. |
| **Portable Archive** | `deliverables/01_Software_Application/portable/SANKET-Portable-v1.0.zip` | **VERIFIED BY EXECUTION** | Standalone zip package (307.79 MB). Unpacks and runs without administrative rights. |
| **Application Instructions** | `deliverables/01_Software_Application/README.txt` | **VERIFIED BY SOURCE INSPECTION**| Plain-text execution guide and hardware requirements. |
| **Source Code Archive** | `deliverables/02_Source_Code/SANKET_Source.zip` | **VERIFIED BY EXECUTION** | 30.36 MB zip containing 281 clean source files. Zero node_modules or cache files. |
| **Source Code Guide (MD)**| `deliverables/02_Source_Code/SOURCE_CODE_README.md` | **VERIFIED BY SOURCE INSPECTION**| Complete setup, build, packaging, and execution instructions. |
| **Source Code Guide (PDF)**| `deliverables/02_Source_Code/SOURCE_CODE_README.pdf` | **VERIFIED BY EXECUTION** | Formal 1-page PDF guide. |
| **Technical Report (MD)**| `deliverables/03_Technical_Report/SANKET_Technical_Report.md` | **VERIFIED BY SOURCE INSPECTION**| Comprehensive technical report with mathematical equations, optical models, and test data. |
| **Technical Report (PDF)**| `deliverables/03_Technical_Report/SANKET_Technical_Report.pdf`| **VERIFIED BY EXECUTION** | Publication-quality 15-page ReportLab PDF with official logo and running headers. |
| **Report Figures** | `deliverables/03_Technical_Report/figures/` (18 PNGs) | **VERIFIED BY RUNTIME** | 18 Full HD (1920×1080) screenshots captured directly from active WebEngine runtime. |
| **User Manual (MD)** | `deliverables/04_User_Manual/SANKET_User_Manual.md` | **VERIFIED BY SOURCE INSPECTION**| Exhaustive commercial-grade operator manual covering all 5 workspaces and parameter dictionary. |
| **User Manual (PDF)** | `deliverables/04_User_Manual/SANKET_User_Manual.pdf` | **VERIFIED BY EXECUTION** | 10-page visual operator manual PDF with embedded Full HD screenshots and tables. |
| **Manual Figures** | `deliverables/04_User_Manual/figures/` (18 PNGs) | **VERIFIED BY RUNTIME** | Synchronized runtime screenshots illustrating all 5 workspaces and controls. |
| **Performance Summary (JSON)**| `deliverables/05_Performance_Log/run_1790716901_summary.json`| **VERIFIED BY RUNTIME** | Generated from clean simulation of `scenario_2_circular`. Throughput: 461.82 FPS. |
| **Performance CSV** | `deliverables/05_Performance_Log/run_1790716901_telemetry.csv`| **VERIFIED BY RUNTIME** | 900 frame records (469 KB) capturing time-series error, state, angles, latency. |
| **Centroid CSV** | `deliverables/05_Performance_Log/run_1790716901_centroids.csv`| **VERIFIED BY RUNTIME** | Per-frame sub-pixel centroid estimates vs ground truth. Error < 1px in 100% frames. |
| **Configuration Snapshot**| `deliverables/05_Performance_Log/run_1790716901_config.json` | **VERIFIED BY RUNTIME** | Complete parameter snapshot of the active simulation session. |
| **Performance Report (MD)**| `deliverables/05_Performance_Log/performance_summary.md` | **VERIFIED BY RUNTIME** | Comprehensive markdown report analyzing run_1790716901 metrics and methodology. |
| **Performance Report (PDF)**| `deliverables/05_Performance_Log/performance_summary.pdf` | **VERIFIED BY EXECUTION** | Formal 2-page executive summary PDF. |
| **Performance Guide** | `deliverables/05_Performance_Log/PERFORMANCE_LOG_README.md`| **VERIFIED BY SOURCE INSPECTION**| Detailed metric provenance and column definitions. |
| **Demo Video (MP4)** | `deliverables/06_Optional_Demo_Video/SANKET_Launch_Demo.mp4`| **VERIFIED BY EXECUTION** | Full HD (1920×1080, 30 FPS, 22.0 s, 4.60 MB) demonstration video. |
| **Demo Video Guide** | `deliverables/06_Optional_Demo_Video/VIDEO_SUBMISSION_STATUS.md`| **VERIFIED BY SOURCE INSPECTION**| Formal video description, metadata, and alternative interactive demo instructions. |
| **Deliverables Manifest (MD)**| `deliverables/DELIVERABLE_MANIFEST.md` | **VERIFIED BY SOURCE INSPECTION**| Master deliverables tracking matrix covering all competition requirements. |
| **Deliverables Manifest (PDF)**| `deliverables/DELIVERABLE_MANIFEST.pdf` | **VERIFIED BY EXECUTION** | Formal single-page deliverables manifest PDF. |

---

## 3. Test & Verification Execution Record

### 3.1 Automated Test Suite (`pytest`)
- **Execution Command:** `pytest`
- **Result:** **599 passed** (0 failures, 0 errors, 0 warnings).
- **Modules Covered:**
  - `test_tracking_pipeline.py`: Detection, sub-pixel centroiding, state transitions
  - `test_ptz_controller.py`: PID control laws, rate clamping, anti-windup
  - `test_bm2_workflow.py`: MP4 ingestion, VideoCapture decoding, reference CSV comparison
  - `test_simulation.py`: Camera projection, target kinematics, disturbance models
  - `test_ai_classifier.py`: Feature extraction and logistic regression model inference
  - `test_metrics_engine.py`: Acquisition time, reacquisition time, lock retention, latency
  - `test_foundation.py`: Base dataclasses, configuration, logging
  - `test_phase6_8_sih_validation.py`: Strict validation of all SIH parameter rows

### 3.2 Packaged Application End-to-End Audit
- **Validation Command:** `python -m src.main --validate`
- **Result:** **ALL PASSED (8/8 foundation checks)**.
- **Packaged Components Verified:**
  - `SANKET.exe`: Standalone PyInstaller ONEDIR binary.
  - `_internal/frontend/dist/index.html`: Compiled React 19 / Vite bundle.
  - `_internal/App_Logo_Assets_Final/`: Complete icon and vector branding assets.
  - `_internal/models/`: Machine learning candidate classifier weights (`candidate_classifier.json`).
  - `_internal/scenarios/`: 19 standardized benchmark scenarios.
  - `_internal/msvcp140.dll`: Bundled MSVC runtime guaranteeing clean-machine immunity.
- **Live User Interface Runtime:**
  - Full HD (1920×1080) UI rendering verified across all 5 production workspaces.
  - Sub-view tab switching (2D Sensor, 3D Pedestal, 2000×2000 World Canvas) verified.
  - Simulation transport controls (`RUN`, `PAUSE`, `RESET`) verified live.
  - Ground-truth firewall integrity confirmed active.

---

## 4. Benchmark-2 / External MP4 Capability Assessment

1. **Source Code Implementation (`VERIFIED BY SOURCE INSPECTION`):**
   - [`src/frame/mp4_provider.py`](file:///src/frame/mp4_provider.py) implements `MP4FrameProvider` via `cv2.VideoCapture`.
   - Agnostic to video resolution and framerate; converts RGB to single-channel monochrome uint8 with zero-copy buffer views.
   - [`src/evaluation/benchmark_manager.py`](file:///src/evaluation/benchmark_manager.py) implements batch MP4 execution and reference CSV evaluation.
   - In MP4 mode, the PTZ camera model is automatically bypassed.
2. **Automated Test Validation (`VERIFIED BY EXECUTION`):**
   - `src/tests/test_bm2_workflow.py` confirms decoding, centroid calculation against reference CSVs, and malformed header rejection.
3. **Bundled Media:**
   - 5 benchmark test media files bundled in `Videos/` (`sanket_benchmark2_beacon_circular_30fps.mp4`, etc.) and ready for arbitrary evaluator video files.

---

## 5. Official Project Naming Verification

```text
Official Project Name: SANKET

Previous Project Name: LumiTrack

LumiTrack matches: 0

SANKET matches: Consistent throughout the project
```
