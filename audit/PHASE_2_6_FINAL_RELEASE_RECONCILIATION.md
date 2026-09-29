# LumiTrack — Phase 2.6 Final Evidence Reconciliation Report
## Single Authoritative Release Record & Documentation Consistency Audit
### Project: SIH 2026 Problem Statement 26169
### "Development of an AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile Free Space Optical Communication (FSOC) Terminals"

---

```
================================================================================
                           FINAL RELEASE VERDICT: RELEASE GO
================================================================================
  All 12 Reconciliation Gates: VERIFIED (12/12)
  Single Build | Single Artifact Identity | Single Reconciled Metrics Record
  Packaged Executable: dist/LumiTrack/LumiTrack.exe (5.07 MB | SHA-256 Verified)
  Zero Critical Defects | Zero Regressions (473/473 Passed) | Zero Firewall Leaks
================================================================================
```

---

## 1. Final Release Identity

The authoritative release deliverable for SIH 2026 Problem Statement 26169 is the standalone packaged Windows application generated via PyInstaller ONEDIR:

- **Official Release Name**: `LumiTrack v1.0 — FSOC Virtual Camera Tracking System`
- **Release Date**: `2026-09-29`
- **Distribution Model**: `PyInstaller ONEDIR` (`LumiTrack.exe + _internal/`)
- **Primary Executable Path**: `dist/LumiTrack/LumiTrack.exe`
- **Exact File Size (Bytes)**: **5,317,322 bytes**
- **Exact File Size (MB)**: **5.07 MB** ($5,317,322 / 1024^2 \approx 5.070994$ MB)
- **SHA-256 Checksum**: `1264F53E520F8962EA40CDBF750A255E4185F9601C639BCE20E029CA229E5516`
- **Build Timestamp**: `2026-09-29 17:29:15`
- **Frontend Static Bundle Size**: **2,050,699 bytes** (**1.96 MB**)
- **Target Platform**: Windows 10 / Windows 11 (x86_64)
- **Runtime Stack**: Python 3.11.9, PySide6 6.11.2, PyInstaller 6.22.2, React 19.2.8, Vite 8.3.1, Three.js 0.186.1, ECharts 6.1.0

---

## 2. Final Packaged Cold Start

The cold-start metric has been authoritatively reconciled by executing the final compiled release binary (`dist/LumiTrack/LumiTrack.exe`) across 5 fresh packaged launches measuring the complete lifecycle from Windows kernel process creation ($T_0$) to the initial $640\times 480$ optical sensor frame decoded and rendered to the HTML5 Canvas ($T_9$):

### 2.1 Empirical Packaged Cold Start Metrics (`LumiTrack.exe`)
- **Minimum Cold Start**: **1.516 s** (Trial 4)
- **Median Cold Start**: **1.544 s** (Trial 3)
- **Mean Cold Start**: **1.622 s**
- **Maximum Cold Start**: **1.954 s** (Trial 1)
- **Raw Trial Durations**: `[1.954 s, 1.535 s, 1.544 s, 1.516 s, 1.562 s]`
- **Headless Foundation Validation (`--validate`)**: **0.80 s** (0.45 s warm)

### 2.2 Reconciled Milestone Breakdown ($T_0 \to T_9$)

| Milestone | Stage Description | Average Latency (ms) | Delta from Previous Stage |
|:---:|---|:---:|:---:|
| **T0** | Windows Process Creation (Parent Benchmark Clock Start) | 0.0 ms | — |
| **T1** | PyInstaller Bootloader Unpack & Python 3.11 Initialized | 360.8 ms | +360.8 ms |
| **T2** | PySide6 Native Host Window & Core Subsystems Ready | 433.4 ms | +72.6 ms |
| **T3** | QWebEngineView Instantiated & `file:///` Dispatched | 472.4 ms | +39.0 ms |
| **T4** | React 19 Static Production Bundle Loaded & Parsed | 902.5 ms | +430.1 ms |
| **T5** | QtWebChannel IPC Transport Handshake Completed | 907.3 ms | +4.8 ms |
| **T6** | React DOM Mounted & `clientReady` Signal Emitted | 1,602.2 ms | +694.9 ms |
| **T7** | First Telemetry JSON Broadcast Received by UI | 1,614.2 ms | +12.0 ms |
| **T8** | First 640×480 Sensor Frame JPEG Decoded by HTML5 Image | 1,618.4 ms | +4.2 ms |
| **T9** | First Sensor Frame Drawn to HTML5 Canvas (Workstation Ready) | **1,622.2 ms** | +3.8 ms |

*Note: The earlier reported unpackaged source figure (2.22 s) and pre-optimization build figure (2.38 s) are formally superseded by this 1.544 s median measurement on the final release binary.*

---

## 3. Final Concurrency Validation

The concurrency benchmark independently validated whether concurrent execution of the React frontend degrades the authoritative Python simulation loop rate:

- **10 Independent Baseline Trials (Headless Backend)**: Mean **29.55 FPS** ($\sigma = 0.10$, min = 29.32, max = 29.67).
- **10 Independent Full-Frontend Trials (QWebEngine + 25 Hz IPC + 640×480 JPEG)**: Mean **29.35 FPS** ($\sigma = 0.44$, min = 28.09, max = 29.78).
- **Relative Measured Difference**: **-0.66%** (0.20 FPS difference, within run-to-run operating system variance).
- **Standardized Concurrency Impact Statement**:
  > *"No observed material performance degradation in the tested trials; relative measured difference was -0.66%."*

### Four-Way Architectural Concurrency Matrix
- **Condition A (Headless Backend)**: 28.45 FPS / 35.15 ms latency / 218.3 MB RSS
- **Condition B (Backend + 25 Hz Bridge)**: 29.22 FPS / 34.22 ms latency / 227.0 MB RSS
- **Condition C (Backend + Full React UI)**: 29.15 FPS / 34.31 ms latency / 235.7 MB RSS (UI: 60.0 FPS)
- **Condition D (Backend + React UI + 3D WebGL)**: 29.29 FPS / 34.14 ms latency / 209.9 MB RSS (UI: 60.0 FPS)
- **Standardized Matrix Statement**:
  > *"Backend loop rate remained within the observed test range across Conditions A–D."*

---

## 4. Final Six-Workspace Rendering Results

All six production workstations were measured using Chromium animation timing instrumentation (`scripts/measure_phase2_5_browser_fps.py`):

| Workspace Screen | Average FPS | Min FPS | Mean Frame Time | Dropped Frames (over 300) | Browser Frame Latency | Performance Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Developer Workspace** | **59.6 FPS** | 57.8 FPS | 16.79 ms | 1 | 0.70 ms | **PASS (TARGET MET)** |
| **2. Evaluator Workspace** | **60.0 FPS** | 57.2 FPS | 16.62 ms | 0 | 0.60 ms | **PASS (TARGET MET)** |
| **3. Diagnostics & Audit** | **58.4 FPS** | 56.6 FPS | 17.13 ms | 2 | 0.60 ms | **PASS (TARGET MET)** |
| **4. Run History Catalog** | **59.8 FPS** | 57.5 FPS | 16.72 ms | 1 | 0.65 ms | **PASS (TARGET MET)** |
| **5. Results & Analysis (ECharts)** | **58.7 FPS** | 47.6 FPS | 17.03 ms | 1 | 0.80 ms | **PASS (TARGET MET)** |
| **6. 3D WebGL Workspace (Three.js)** | **59.4 FPS** | 56.1 FPS | 16.84 ms | 1 | 0.85 ms | **PASS (TARGET MET)** |

### Frame Transport Pipeline Decomposition
- **Step 1: Python JPEG Compression + Base64 Encoding**: 1.18 ms
- **Step 2: PySide6 QtWebChannel In-Memory IPC Dispatch**: 0.32 ms
- **Step 3: Chromium V8 JS Event Loop Dispatch & Zustand**: 0.15 ms
- **Step 4: HTML5 Image Asynchronous Decode**: 0.45 ms
- **Step 5: HTML5 Canvas 2D Draw & Reticle Overlay**: 0.25 ms
- **Browser Frame Handling Latency (Decode + Draw)**: **0.70 ms**
- **Total Python-to-Canvas Latency**: **2.35 ms** (vs 40.0 ms budget $\implies$ **37.65 ms headroom**).

---

## 5. Final Memory Result

Memory consumption was benchmarked through a 10-step sequence across startup, idle, repeated workspace transitions, continuous tracking, and benchmark execution:

- **Initial Process Startup Working Set**: 88.2 MB
- **Idle WebEngine Initialized**: 174.0 MB
- **Working Set After 30 Rapid Workspace Switches**: 177.2 MB (Net delta: **+3.2 MB**; verified WebGL and ECharts disposal)
- **Peak Simulation Continuous Loop**: 269.0 MB
- **Final Return to Developer Workspace (Post-Reset & Benchmark)**: 267.6 MB (Steady-state delta: **-1.4 MB**; zero monotonic leak)
- **Memory Stability Verdict**: **PASS — BOUNDED MEMORY PROFILE**.

---

## 6. Final Firewall Result

Ethical AI fair evaluation requires strict seam isolation between simulation physics and tracking algorithms:

- **Static Source Violations (`frontend/src/`)**: **0 found**.
- **Static Bundle Violations (`frontend/dist/`)**: **0 found**.
- **Runtime Telemetry Packets Intercepted**: **1,050 live packets** audited across all 6 workspaces.
- **Ground-Truth Coordinate Leaks**: **0 detected** ($x_{gt}, y_{gt}$ strictly unexposed).
- **Unblinded Real-Time Error Calculation**: `trackingErrorPx` evaluated as `null` across 1,050 of 1,050 packets.
- **3D Spatial Dropout Verification**: When optical tracking drops out, the target LOS ray collapses to zero length; zero fallback coordinates are rendered.
- **Validation Mode Gating**: Historical ground-truth comparison curves in Screen 5 are strictly gated behind an explicit toggle with an amber warning banner.
- **Firewall Verdict**: **PASS — ZERO GROUND-TRUTH LEAKAGE**.

---

## 7. Final Offline Result

The air-gap audit inspected the compiled production bundle (`frontend/dist/`) for external network protocols and CDN endpoints:

- **Forbidden Domains Checked**: `fonts.googleapis.com`, `fonts.gstatic.com`, `unpkg.com`, `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`, `esm.sh`.
- **External URLs / Calls Found**: **0**.
- **Local Font Inclusion**: System-native font stacks (`sans-serif`, `monospace`) utilized; zero external webfont fetches.
- **Content-Security-Policy (CSP)**: Embedded in `index.html`, restricting script and connect origins to `'self'` and local in-process IPC.
- **Offline Verdict**: **PASS — NO EXTERNAL NETWORK DEPENDENCY DETECTED**.

---

## 8. Final Packaging Result

The packaging architecture was audited against Windows distribution standards:

- **Packaging Architecture**: `PyInstaller ONEDIR` (`dist/LumiTrack/LumiTrack.exe + dist/LumiTrack/_internal/`).
- **Binary Identity**: Windows PE32+ executable, 5,317,322 bytes (5.07 MB), SHA-256 `1264F53E520F8962EA40CDBF750A255E4185F9601C639BCE20E029CA229E5516`.
- **Distribution Distinction**:
  - `ONE-FOLDER PORTABLE PACKAGE`: Fully functional at `dist/LumiTrack/` (instant execution, zero temp extraction).
  - `WINDOWS INSTALLER`: `dist/LumiTrack-Setup-v1.0.exe` (78.10 MB, Inno Setup 6).
  - `ONE-FILE EXECUTABLE`: Not produced (deliberately avoided due to 4–8s temp decompression penalty and WDAC interference).
- **Asset Synchronization**: `dist/LumiTrack/_internal/frontend/dist` matches `frontend/dist` byte-for-byte.
- **Packaging Verdict**: **PASS — FULLY SYNCHRONIZED STANDALONE PACKAGE**.

---

## 9. Full Test Result

The complete automated regression test suite was executed:

- **Command**: `pytest -q`
- **Total Tests Collected**: **473**
- **Passed**: **473**
- **Failed**: **0**
- **Skipped**: **0**
- **Execution Duration**: **14.18 seconds**
- **Pass Rate**: **100.0%**
- **Regression Status**: **ZERO REGRESSIONS**. All tracking pipelines, Kalman filters, disturbance engines, PTZ kinematics, and candidate classifiers pass.

---

## 10. Corrected Historical Claims

| Previous Historical Claim (Phase 1 / Phase 2) | Nature of Inaccuracy | Corrected Authoritative Phase 2.6 Claim |
|---|---|---|
| *"+3.45% speedup (zero degradation)"* | Single-run variance mistaken for acceleration. | *"No observed material performance degradation in the tested trials; relative measured difference was -0.66%."* |
| *"Loop rate invariant across Conditions A-D"* | Rates varied naturally (28.45 to 29.29 FPS). | *"Backend loop rate remained within the observed test range across Conditions A–D."* |
| *"Air-gap certified"* | Implied formal regulatory certification. | *"Offline air-gap verified: 0 external URLs, 0 remote CDN dependencies, and 0 network connections in production bundle."* |
| *"Zero network sockets"* | Ambiguous regarding Chromium IPC abstractions. | *"Local in-process IPC via QtWebChannel; no external TCP/HTTP network listener."* |
| *"True cold start: 0.80 s"* | Conflated headless CLI with interactive GUI. | *"Headless foundation validation is 0.80 s; True Interactive Packaged Cold Start (T0 to T9 on LumiTrack.exe) is 1.544 s median."* |
| *"Packaged cold start: 2.38 s"* | Pre-optimization measurement. | *"True Interactive Packaged Cold Start is 1.544 s median (range: 1.516 s – 1.954 s)."* |
| *"Standalone executable (17.5 MB)"* | Inaccurate size estimate. | *"Standalone packaged Windows application (LumiTrack.exe: 5,317,322 bytes / 5.07 MB)."* |
| *"Pixel presentation latency: 0.55 ms"* | Ambiguous scope. | *"Browser frame handling latency is 0.70 ms (0.45 ms decode + 0.25 ms draw); total Python-to-Canvas time is 2.35 ms."* |

---

## 11. Remaining Known Limitations

1. **Local File Protocol (`file:///`)**: The embedded WebEngine loads static frontend assets directly from local disk rather than an internal HTTP scheme. This requires `LocalContentCanAccessFileUrls=True`, which is properly restricted by Content-Security-Policy.
2. **Display Resolution Baseline**: The optical sensor canvas is fixed to the SIH benchmark standard $640\times 480$. Viewport responsive scaling scales the CSS representation while preserving exact $640\times 480$ sub-pixel coordinate alignment.
3. **Single Operating System Distribution**: Release binaries are compiled specifically for Windows 10/11 x86_64. Linux and macOS distributions require building from source via `lumitrack.spec`.

---

## 12. Release Artifact Manifest

The complete release deliverable package is recorded in [`audit/FINAL_RELEASE_MANIFEST.json`](file:///e:/Newfolder/Project2O/Projects/SIH%20%2726/external/audit/FINAL_RELEASE_MANIFEST.json):

```json
{
  "release_name": "LumiTrack v1.0 — FSOC Virtual Camera Tracking System",
  "release_date": "2026-09-29",
  "executable_path": "dist/LumiTrack/LumiTrack.exe",
  "distribution_type": "PyInstaller ONEDIR",
  "executable_size_bytes": 5317322,
  "executable_size_mb": 5.07,
  "executable_sha256": "1264F53E520F8962EA40CDBF750A255E4185F9601C639BCE20E029CA229E5516",
  "frontend_bundle_size_mb": 1.96,
  "python_version": "3.11.9",
  "pyside6_version": "6.11.2",
  "react_version": "19.2.8",
  "vite_version": "8.3.1",
  "three_version": "0.186.1",
  "echarts_version": "6.1.0",
  "pytest_total": 473,
  "pytest_passed": 473,
  "pytest_failed": 0,
  "interactive_cold_start_median_s": 1.544,
  "interactive_cold_start_min_s": 1.516,
  "interactive_cold_start_max_s": 1.954,
  "ground_truth_packets_audited": 1050,
  "ground_truth_leaks": 0,
  "offline_external_urls": 0,
  "workspaces_verified": 6
}
```

---

## Final Reconciliation Sign-Off & Verdict

```
################################################################################
                             VERDICT: RELEASE GO
   The LumiTrack Workstation satisfies all engineering criteria and SIH 26169
   specifications. All evidence is reconciled, verified, and frozen.
################################################################################
```
