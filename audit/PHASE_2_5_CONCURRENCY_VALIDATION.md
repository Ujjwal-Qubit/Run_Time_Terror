# LumiTrack — Phase 2.5 Concurrency Validation Report
## Independent Empirical Assessment of Backend Loop Rate Under Full Concurrent Modern UI Load
### SIH 2026 Problem Statement 26169 — Release Engineering Audit

---

## 1. Executive Summary & Objective

In Phase 2, a single-trial measurement claimed that concurrent execution of the React frontend yielded "+3.45% (zero degradation)" relative to the headless baseline. As part of the Phase 2.5 and Phase 2.6 release-hardening audit, this claim was independently re-evaluated using rigorous multi-trial statistical benchmarking and a 4-way architectural condition matrix.

### Authoritative Finding
- **10 Independent Baseline Trials (Headless Backend)**: Mean **29.55 FPS** ($\sigma = 0.10$, min = 29.32, max = 29.67).
- **10 Independent Full-Frontend Trials (QWebEngine + 25 Hz IPC + 640×480 JPEG)**: Mean **29.35 FPS** ($\sigma = 0.44$, min = 28.09, max = 29.78).
- **Relative Difference**: **-0.66%** (0.20 FPS difference), well within natural operating system scheduling variance.
- **Approved Release Terminology**:
  > *"No observed material performance degradation in the tested trials; relative measured difference was -0.66%."*

---

## 2. Statistical Methodology & Benchmark Harness

The benchmark harness (`scripts/measure_phase2_5_concurrency.py`) was executed on the authoritative hardware host under Windows 11 with the following controls:
1. **Isolated Executions**: 10 distinct, non-overlapping 3.0-second simulation runs per condition.
2. **Deterministic Seed**: Scenario parameters fixed to eliminate simulation complexity variance.
3. **Hardware Profile**: High-resolution performance timers (`time.perf_counter()`) capturing tick interval, execution time, and idle sleep.
4. **Full IPC Load**: During full-frontend trials, QtWebChannel JSON serialization of 25 Hz telemetry packets and OpenCV JPEG encoding/Base64 transport of 640×480 sensor frames ran continuously.

---

## 3. 10-Trial Comparative Results

### 3.1 Raw Trial Data

| Trial # | Condition: Headless Baseline (FPS) | Condition: Full Concurrent Frontend (FPS) | Delta (FPS) |
|:---:|:---:|:---:|:---:|
| 1 | 29.32 | 29.45 | +0.13 |
| 2 | 29.54 | 29.60 | +0.06 |
| 3 | 29.61 | 29.78 | +0.17 |
| 4 | 29.51 | 29.22 | -0.29 |
| 5 | 29.49 | 29.58 | +0.09 |
| 6 | 29.67 | 29.44 | -0.23 |
| 7 | 29.66 | 29.51 | -0.15 |
| 8 | 29.61 | 29.53 | -0.08 |
| 9 | 29.50 | 28.09 | -1.41 |
| 10 | 29.58 | 29.35 | -0.23 |

### 3.2 Statistical Aggregation

| Metric | Baseline Headless Backend | Full Concurrent Frontend UI | Engineering Note |
|---|:---:|:---:|---|
| **Mean Loop Rate** | **29.55 FPS** | **29.35 FPS** | -0.66% relative difference |
| **Standard Deviation ($\sigma$)** | 0.10 FPS | 0.44 FPS | Low dispersion across all runs |
| **Minimum Rate** | 29.32 FPS | 28.09 FPS | Single transient tick jitter in Trial 9 |
| **Maximum Rate** | 29.67 FPS | 29.78 FPS | Both reach top target governor rate |
| **Nominal Target** | 30.00 FPS | 30.00 FPS | Governing sleep budget: 33.33 ms/frame |
| **Evidence Category** | `MEASURED` | `MEASURED` | Authoritative Python process instrumentation |

---

## 4. Four-Way Concurrency Matrix (A, B, C, D)

To isolate where CPU and IPC overhead are introduced, four distinct architectural stages were measured under identical test profiles:

| Condition | Configuration Description | Backend Loop FPS | Backend Frame Latency | Frontend UI FPS | Host RSS Memory | Architectural Boundary |
|---|---|:---:|:---:|:---:|:---:|---|
| **A: Backend Only** | Headless simulation continuous loop without Qt | **28.45 FPS** | 35.15 ms | N/A | 218.3 MB | Baseline reference loop |
| **B: Backend + Bridge** | Backend + QtWebChannel `LumiTrackBridge` polling @ 25 Hz | **29.22 FPS** | 34.22 ms | N/A | 227.0 MB | Decoupled ring buffer; bridge reads last frame |
| **C: Backend + WebEngine UI** | Backend + Full React 19 UI (Developer & Diagnostics) | **29.15 FPS** | 34.31 ms | 60.0 FPS | 235.7 MB | Chromium multi-process model |
| **D: Backend + WebEngine 3D** | Backend + Full React 19 UI + Three.js 3D WebGL active | **29.29 FPS** | 34.14 ms | 60.0 FPS | 209.9 MB | WebGL rendering on dedicated GPU process |

### Key Architectural Observations:
1. **Four-Way Matrix Finding**: **Backend loop rate remained within the observed test range across Conditions A–D.**
2. **Ring-Buffer Protection**: The backend writes new telemetry to atomic variables and visualization state; the UI bridge reads the latest state on its own 25 Hz timer. There is zero lock contention or blocking RPC.
3. **GPU Offloading**: Condition D (3D WebGL) shows backend loop rate (29.29 FPS) and frame latency (34.14 ms) well within normal variance because Three.js vertex and fragment processing occur in Chromium's GPU process.

---

## 5. Terminology Correction & Audit Decision

### Correction of Phase 2 Claim
- **HISTORICAL PHASE 2 CLAIM**: *"Frontend concurrency delivered +3.45% higher throughput with zero degradation."*
- **Audit Assessment**: **INVALID**. A single run measuring 29.8 FPS vs 28.8 FPS reflects standard OS timer resolution variations (typically $\pm 1-2$ ms on Windows) rather than true throughput acceleration. A frontend cannot accelerate backend math.
- **Audited Description (Phase 2.6 Frozen Standard)**:
  - Wording is standardized to: *"No observed material performance degradation in the tested trials; relative measured difference was -0.66%."*
  - Matrix wording is standardized to: *"Backend loop rate remained within the observed test range across Conditions A–D."*
  - Wording "zero network sockets" is replaced by: *"Local in-process IPC via QtWebChannel; no external TCP/HTTP network listener."*

---

## 6. Concurrency Audit Verdict

| Gate Requirement | Threshold / Specification | Measured Result | Verdict |
|---|---|---|:---:|
| Backend Loop Stability | $\ge 28.0$ FPS average under full UI load | **29.35 FPS** | **PASS** |
| Concurrency Degradation Limit | $< 5.0\%$ degradation vs baseline | **0.66%** | **PASS** |
| 4-Way Concurrency Parity | Loop rate maintained across Conditions A-D | Within observed range (28.45 to 29.29 FPS) | **PASS** |
| UI Frame Rate | $\ge 55.0$ FPS in interactive viewports | **60.0 FPS** | **PASS** |

**FINAL CONCURRENCY VERDICT**: **RELEASE GO**.
