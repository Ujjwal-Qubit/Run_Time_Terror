# SIH 2026 — Independent Technical Problem Analysis & Requirements Audit

> **Authoritative source:** [PS.md](file:///e:/Newfolder/Project2O/Projects/SIH%20'26/external/PS.md)
> **Analysis date:** 2026-09-03
> **Status:** Pre-architecture analysis only — no design, no code, no PRD/SRS

---

## 1. Understanding the Actual Engineering Problem

### What physical/engineering problem is being solved?

Free Space Optical Communication (FSOC) terminals on mobile platforms (satellites, UAVs) communicate via narrow laser beams. Before any data link can be established, the transmitter must physically *find* and *point at* the remote terminal. This is the Pointing, Acquisition, and Tracking (PAT) problem.

The PS specifically targets the **coarse alignment stage** of PAT. This is the first stage — locating the remote terminal's beacon within a camera's field of view and keeping it roughly centered. Fine alignment (sub-pixel, sub-arcsecond beam steering) is explicitly **out of scope**.

The actual engineering deliverable is **not** real hardware PAT. It is a **software simulator + tracking system** that allows algorithm development and validation for coarse alignment — without expensive optical hardware.

### What does "coarse alignment" mean in this context?

Coarse alignment means:
1. A camera observes the environment.
2. A beacon (bright spot) from the remote terminal appears somewhere in the scene.
3. The system must **detect** the beacon.
4. The system must **estimate its position** within the camera frame.
5. The system must **command a pan-tilt mechanism** to steer the camera so the beacon is continuously near the frame center.

The tracking error tolerance is **≤ 10 pixels** — this is coarse, not fine. The beacon is small (5–20 pixels), the FOV is narrow (default 4°×3°), and the resolution is 640×480.

### What role does the virtual camera play?

The virtual camera is a **software-rendered viewport** into a larger "screen" (≥ 2000×2000 pixels). The camera:
- Has a resolution of 640×480 pixels.
- Views only a small portion of the screen at any time (based on FOV and position).
- Is repositioned via simulated pan-tilt commands.
- Has its initial position at the **centre of the screen** (PS row 6).

The camera is the **sensor model** — it extracts a sub-image from the larger scene, applies noise/disturbances, and presents the result as a video frame to the tracking algorithm.

### What role does the moving optical beacon play?

The beacon is a small, bright, user-configurable spot (default 10×10 pixels, square) that moves within the 2000×2000 screen according to predefined motion patterns (straight line, circular, figure-of-8, random — mandatory; spiral, sinusoidal, user-defined — optional). It represents the **remote FSOC terminal** that the tracking system must acquire and follow.

### What does the tracking system ultimately control?

The tracking system controls the **virtual pan-tilt camera's pointing direction** — i.e., where the 640×480 viewport is positioned on the 2000×2000 screen. The goal is to keep the beacon centered (or near-centered) within that viewport.

### What is inside the scope?

- Virtual scene generation (2000×2000 screen with beacon)
- Beacon motion simulation (at least 4 patterns)
- Virtual camera model (640×480 viewport, FOV, monochrome)
- Noise and disturbance injection (noise types, jitter, atmospheric, platform motion)
- Beacon detection algorithm (AI-assisted / computer vision)
- Tracking algorithm (centroid estimation, error computation)
- PTZ control algorithm (repositioning the virtual camera)
- Real-time visualization (tracking overlay, performance stats)
- Performance logging (acquisition time, tracking error, loss rate, etc.)
- Ability to accept external MP4 video as input (bypass simulator, benchmark-2)
- Technical documentation and reporting

### What is explicitly outside the scope?

- Fine alignment / fine pointing mechanisms
- Actual optical hardware, real cameras, real pan-tilt units
- Real atmospheric propagation modeling (only contrast/brightness reduction)
- Communication link budget, modulation, encoding
- Multi-terminal networking
- Real-time embedded systems constraints
- The PS says nothing about latency constraints beyond processing speed ≥ 20 FPS

---

## 2. Complete Requirements Extraction

### A. Functional Requirements

| ID | Requirement | Source |
|---|---|---|
| FR-001 | Generate a configurable virtual environment | PS Line 72: "Generate a configurable virtual environment" |
| FR-002 | Generate one or more moving targets (beacon spots) | PS Line 73: "Generate one or more moving targets" |
| FR-003 | Implement a movable virtual camera (pan-tilt viewport) | PS Line 74: "Implement a movable virtual camera" |
| FR-004 | Detect the target beacon automatically | PS Line 75: "Detect the target beacon automatically" |
| FR-005 | Track the beacon continuously using computer vision | PS Line 76: "Track the beacon continuously using computer vision" |
| FR-006 | Control and reposition the virtual camera | PS Line 77: "Control and reposition the virtual camera" |
| FR-007 | Generate and introduce disturbances (atmospheric, platform, noise) in the virtual camera feed | PS Line 78: "Generate and introduce disturbances due to atmospheric turbulence, platform vibrations, camera motion, noise, etc., in the virtual camera feed" |
| FR-008 | Display tracking performance and statistics in real-time | PS Line 79: "Display tracking performance and statistics in real-time" |
| FR-009 | Support at least four target motion patterns: straight line, circular, figure-of-8, random | PS Line 46, Row 12 |
| FR-010 | Support selectable image noise types: salt & pepper, Gaussian, Poisson (one or more) | PS Line 58, Row 21 |
| FR-011 | Support atmospheric disturbance modes: clear, haze, fog, rain, low light | PS Line 61, Row 4 |
| FR-012 | Support platform motion with at least linear motion (mandatory) | PS Line 62, Row 5: "Default/Mandatory: Linear" |
| FR-013 | Software must accept external MP4 video files as input, bypassing the PTZ camera/simulator | PS Line 113: "take this video as an input to the coarse pointing system" |
| FR-014 | Automatically generate a performance report/log | PS Line 103: "automatically generating a performance report" |
| FR-015 | The application must be a standalone executable | PS Line 87: "A standalone executable application" |

### B. Parameter/Configuration Requirements

| ID | Requirement | Source |
|---|---|---|
| PC-001 | Screen size minimum 2000×2000 pixels, optionally user-defined | Row 1 |
| PC-002 | Camera type: monochrome FPA (mandatory), colour optional | Row 2 |
| PC-003 | Camera resolution: 640×480 pixels, optionally user-defined | Row 3 |
| PC-004 | Camera FOV: user-defined, default 4°×3° | Row 4 |
| PC-005 | Camera update rate: minimum 30 Hz | Row 5 |
| PC-006 | Initial camera position: centre of screen | Row 6 |
| PC-007 | Target type: beacon spot | Row 7 |
| PC-008 | Number of targets: 1 mandatory, multiple optional | Row 8 |
| PC-009 | Target shape: user-defined, default square | Row 9 |
| PC-010 | Target size: 5–20 × 5–20 pixels, user-defined, default 10×10 | Row 10 |
| PC-011 | Initial target location: user-defined, default random | Row 11 |
| PC-012 | Motion patterns: at least 4 mandatory + optional patterns | Row 12 |
| PC-013 | Max pan speed: 5–10 °/s, user-defined, default 5 °/s | Row 13 |
| PC-014 | Max tilt speed: 5–10 °/s, user-defined, default 5 °/s | Row 14 |
| PC-015 | PTZ update interval: ≥ 20 Hz | Row 15 |
| PC-016 | Salt & pepper noise: around 10% of image | Row 21 |
| PC-017 | Max noise standard deviation: 20 pixels — *[AMBIGUITY: likely means intensity value, not pixels — see §9]* | Row 22 |
| PC-018 | Max camera jitter: ±20 pixels/frame, user-defined | Row 23 |
| PC-019 | Atmospheric disturbance: user-defined contrast and brightness reduction | Row 24 |
| PC-020 | Platform motion: ±20 pixels/frame max, user-selectable | Row 25 |

### C. Performance Requirements

| ID | Requirement | Source |
|---|---|---|
| PR-001 | Acquisition time ≤ 2 seconds | Row 16 |
| PR-002 | Tracking error ≤ 10 pixels | Row 17 |
| PR-003 | Target loss < 5% | Row 18 |
| PR-004 | Re-acquisition time ≤ 1 second | Row 19 |
| PR-005 | Processing speed ≥ 20 FPS | Row 20 |

### D. Input Requirements

| ID | Requirement | Source |
|---|---|---|
| IR-001 | User-configurable simulation parameters (all rows marked "user-defined") | Multiple rows |
| IR-002 | External MP4 video files at 30 FPS as input for benchmark-2 | Line 113 |
| IR-003 | Benchmark scenarios provided by evaluators during benchmark-1 | Line 112 |

### E. Output Requirements

| ID | Requirement | Source |
|---|---|---|
| OR-001 | Real-time display of tracking performance and statistics | Line 79 |
| OR-002 | Automatically generated performance report: simulation duration, FPS, acquisition time, average and maximum tracking error, lock retention rate, processing time | Line 103 |
| OR-003 | Log of centroiding error (required for benchmark-1 evaluation) | Line 112 |
| OR-004 | GUI for the application | Line 111: evaluation includes "GUI" |

### F. Deliverables

| ID | Requirement | Source |
|---|---|---|
| DR-001 | Standalone executable application | Line 87 |
| DR-002 | Complete source code with proper documentation, modular and adequately commented | Line 91–92 |
| DR-003 | Technical report (10–15 pages): problem understanding, system architecture, software modules, tracking methods, AI methods, test methodology, performance analysis, future improvements | Line 95 |
| DR-004 | User manual: installation, operation, parameter configuration, GUI description | Line 98–99 |
| DR-005 | Performance log (auto-generated) | Line 103 |
| DR-006 | OPTIONAL: 3–5 minute video demonstration | Line 99 |

### G. Evaluation Requirements

| ID | Requirement | Source |
|---|---|---|
| ER-001 | Functional verification: demonstrate all mandatory functions in 10–15 min | Line 111 |
| ER-002 | Benchmark-1: execute evaluator-provided scenarios, produce centroiding error log and performance logs | Line 112 |
| ER-003 | Benchmark-2: process evaluator-provided MP4 videos, compare centroiding error with predefined values, report RMSE, acquisition time, re-acquisition time, lock retention rate, FPS | Line 113 |
| ER-004 | Technical evaluation: present approach, methods, architecture, design; demonstrate understanding, algorithm selection, AI/CV use, innovation, documentation, Q&A | Line 114 |

---

## 3. Complete Requirement Matrix

| ID | Requirement | Exact Source (PS Line/Row) | Mandatory/Optional | Parameter/Threshold | How It Can Be Tested | Priority |
|---|---|---|---|---|---|---|
| FR-001 | Generate configurable virtual environment | L72 | Mandatory | Screen ≥ 2000×2000 | Launch app, verify scene renders | Critical |
| FR-002 | Generate one or more moving targets | L73, Row 8 | 1 mandatory, multiple optional | Size 5–20px, 4+ motion patterns | Run each motion pattern, verify beacon moves correctly | Critical |
| FR-003 | Implement movable virtual camera | L74, Rows 1–6 | Mandatory | 640×480, FOV default 4°×3° | Verify viewport extracts correct sub-region | Critical |
| FR-004 | Detect target beacon automatically | L75 | Mandatory | — | Start simulation with beacon off-center; verify detection | Critical |
| FR-005 | Track beacon continuously (CV) | L76 | Mandatory | Error ≤ 10px, loss < 5% | Run standard scenario, measure error & loss | Critical |
| FR-006 | Control/reposition virtual camera | L77, Rows 13–15 | Mandatory | Pan/tilt ≤ 10°/s, update ≥ 20 Hz | Verify camera moves toward beacon, respects speed limits | Critical |
| FR-007 | Generate/introduce disturbances | L78, Rows 21–25 | Mandatory (at least noise + linear platform) | Per-disturbance params | Enable each disturbance, verify visual effect on feed | High |
| FR-008 | Display real-time tracking stats | L79 | Mandatory | — | Observe UI during tracking | High |
| FR-009 | 4+ motion patterns | Row 12 | Mandatory (4), optional (spiral, sinusoidal, user) | — | Select each pattern, verify correct trajectory | High |
| FR-010 | Selectable noise types | Row 21 | Mandatory (3 types) | S&P ~10%, σ ≤ 20, Poisson | Toggle each noise, verify visual effect | High |
| FR-011 | Atmospheric disturbance modes | Row 24 | Mandatory | 5 modes: clear/haze/fog/rain/low-light | Select each mode, verify contrast/brightness changes | High |
| FR-012 | Platform motion (linear mandatory) | Row 25 | Linear mandatory, others optional | ±20 px/frame max | Enable platform motion, verify camera shake | High |
| FR-013 | Accept external MP4 input | L113 | Mandatory (for benchmark-2) | 30 FPS MP4, full screen with noise & beacon | Load MP4, verify tracker processes it | Critical |
| FR-014 | Auto-generate performance report | L103 | Mandatory | Duration, FPS, acq. time, avg/max error, lock rate, proc. time | Run scenario, verify log file generated | Critical |
| FR-015 | Standalone executable | L87 | Mandatory | — | Verify runs without IDE/interpreter on clean machine | High |
| PR-001 | Acquisition time ≤ 2 s | Row 16 | Mandatory | 2 seconds max | Measure time from start to first lock | Critical |
| PR-002 | Tracking error ≤ 10 px | Row 17 | Mandatory | 10 pixels max | Compute error over run, verify ≤ 10 px avg | Critical |
| PR-003 | Target loss < 5% | Row 18 | Mandatory | 5% max frame loss | Count lost frames / total frames | Critical |
| PR-004 | Re-acquisition time ≤ 1 s | Row 19 | Mandatory | 1 second max | Introduce target loss, measure re-lock time | Critical |
| PR-005 | Processing speed ≥ 20 FPS | Row 20 | Mandatory | 20 FPS minimum | Measure actual processing frame rate | Critical |
| DR-001 | Standalone executable | L87 | Mandatory | — | Run on evaluator's machine | High |
| DR-002 | Source code + docs | L91–92 | Mandatory | Modular, commented | Code review | High |
| DR-003 | Technical report 10–15 pages | L95 | Mandatory | Prescribed content sections | Document review | High |
| DR-004 | User manual | L98–99 | Mandatory | Installation, operation, config, GUI | Document review | Medium |
| DR-005 | Performance log | L103 | Mandatory | Prescribed metrics | Verify log output | High |
| DR-006 | Demo video 3–5 min | L99 | Optional | — | Watch video | Low |
| ER-001 | Functional verification (20%) | L111 | Mandatory (evaluation) | All functions, operational success, GUI | 10–15 min live demo | Critical |
| ER-002 | Benchmark-1 (30%) | L112 | Mandatory (evaluation) | Centroiding error, perf logs | Run evaluator scenarios | Critical |
| ER-003 | Benchmark-2 (30%) | L113 | Mandatory (evaluation) | RMSE, acq/re-acq time, lock retention, FPS vs predefined values | Run evaluator MP4s | Critical |
| ER-004 | Technical evaluation (20%) | L114 | Mandatory (evaluation) | 7 sub-criteria | Presentation + Q&A | High |

---

## 4. MoSCoW Prioritization

### MUST HAVE (Directly Required by PS)

1. Virtual scene (≥ 2000×2000) with configurable beacon(s)
2. Movable virtual camera viewport (640×480, monochrome, configurable FOV)
3. Four mandatory motion patterns (straight line, circular, figure-of-8, random)
4. Beacon detection algorithm (AI/CV-assisted)
5. Continuous tracking with centroid estimation
6. PTZ control with speed constraints (pan/tilt ≤ 10 °/s, update ≥ 20 Hz)
7. Three noise types (salt & pepper, Gaussian, Poisson) — user-selectable
8. Atmospheric disturbance modes (clear, haze, fog, rain, low light)
9. Platform motion (linear mandatory)
10. Camera jitter
11. External MP4 video input mode (bypass simulator)
12. Real-time tracking visualization with stats overlay
13. Automatic performance log generation
14. Standalone executable
15. Source code, technical report, user manual
16. Meet all 5 performance thresholds (PR-001 through PR-005)

### SHOULD HAVE (Strongly Justified by Evaluation Criteria)

1. **Centroiding error logging** — explicitly evaluated in benchmark-1 and benchmark-2
2. **RMSE computation** — explicitly listed in benchmark-2 criteria
3. **Lock retention rate computation** — explicitly listed in benchmark-2
4. **Polished GUI** — evaluated as a sub-criterion in functional verification (20%)
5. **Additional motion patterns** (spiral, sinusoidal) — shows completeness
6. **Multiple target support** — listed as optional but demonstrates capability
7. **Colour camera mode** — listed as optional
8. **AI/ML-based approach** — explicitly evaluated under "AI and computer vision" in technical evaluation
9. **Innovation and novelty** — separate evaluation criterion
10. **Robust re-acquisition mechanism** — re-acquisition time is a benchmark metric

### COULD HAVE (Useful Enhancements)

1. User-defined custom motion patterns (trajectory editor)
2. Scenario save/load/replay functionality
3. Side-by-side ground truth visualization
4. Real-time error plots/graphs
5. Configurable camera resolution beyond 640×480
6. Advanced atmospheric models (turbulence scintillation)
7. Multiple beacon discrimination (selecting the correct one among decoys)
8. Frame-by-frame analysis mode
9. Batch scenario execution
10. Export results to CSV/JSON

### DO NOT NEED (Attractive but irrelevant to scoring)

1. ❌ Fine alignment / fine pointing simulation — explicitly out of scope
2. ❌ Real optical propagation models (beam divergence, link budget) — not evaluated
3. ❌ 3D scene rendering / realistic environment — the PS describes a 2D screen with a beacon spot
4. ❌ Network communication simulation — not part of the problem
5. ❌ Hardware-in-the-loop interfaces — pure software problem
6. ❌ Deep learning object detection trained on photorealistic data — the beacon is a simple geometric spot, not a complex object
7. ❌ Cloud deployment / web application — standalone executable is required
8. ❌ Multi-user / collaborative features — not evaluated

---

## 5. Numerical Specifications Analysis

| Parameter | Value | Mandatory / Suggested / Default | What It Represents | How It Affects the System | How a Judge Could Test It |
|---|---|---|---|---|---|
| **Screen Size** | ≥ 2000×2000 px | Minimum mandatory, user-definable | The total world/scene in which the beacon moves and the camera operates | Defines the spatial extent; camera viewport is a small window into this | Change screen size, verify beacon can move across full extent |
| **Camera Resolution** | 640×480 px | Suggested with optional user-defined | The viewport resolution — what the tracker algorithm "sees" | Fixed processing resolution; FOV-to-pixel mapping depends on this | Verify output frame is 640×480, verify detection still works |
| **Camera FOV** | 4°×3° default, user-defined | Default, not strictly mandatory | Angular field of view of the virtual camera | Determines the scale conversion: degrees ↔ pixels. Default: 4°/640 = 0.00625°/px ≈ 22.5 arcsec/px | Change FOV, verify the viewport scales correctly |
| **Camera Update Rate** | ≥ 30 Hz | Minimum mandatory | Rate at which the camera produces new frames | Simulator must generate ≥ 30 frames per second | Measure actual frame generation rate |
| **Target Size** | 5–20 × 5–20 px, default 10×10 | Range mandatory, default given | Beacon size in pixels on the screen | Smaller = harder to detect; this is the core detection challenge | Set to 5×5 with noise, verify detection still works |
| **Max Pan Speed** | 5–10 °/s, default 5 °/s | Range mandatory, default given | Maximum angular velocity of camera in azimuth | Limits how fast the camera can chase the beacon; must be enforced | Command rapid movement, verify camera does not exceed max speed |
| **Max Tilt Speed** | 5–10 °/s, default 5 °/s | Range mandatory, default given | Maximum angular velocity of camera in elevation | Same as pan speed for the vertical axis | Same as pan speed test |
| **PTZ Update Interval** | ≥ 20 Hz | Minimum mandatory | How often the PTZ controller can update camera position | Control loop runs at ≥ 20 Hz; separate from camera frame rate (30 Hz) | Measure PTZ command rate |
| **Acquisition Time** | ≤ 2 s | Maximum mandatory | Time from simulation start (or target appearance) to first successful lock | Critical benchmark metric | Start scenario, measure time to first valid track |
| **Tracking Error** | ≤ 10 px | Maximum mandatory | Distance between beacon centroid and camera center | Core tracking quality metric | Compute per-frame error, verify average/max ≤ 10 px |
| **Target Loss** | < 5% | Maximum mandatory | Percentage of frames where beacon is not being tracked | Robustness metric | Run long scenario with disturbances, count lost frames |
| **Re-acquisition Time** | ≤ 1 s | Maximum mandatory | Time to re-lock after losing the target | Tests recovery capability | Force target loss (e.g., temporary occlusion), measure re-lock time |
| **Processing Speed** | ≥ 20 FPS | Minimum mandatory | End-to-end processing rate of the tracking pipeline | Must maintain real-time performance | Measure actual processing FPS under various conditions |
| **S&P Noise** | ~10% of image | Suggested percentage | Fraction of pixels corrupted by salt-and-pepper noise | Degrades image quality; tests noise robustness | Enable S&P, verify ~10% pixel corruption, test tracking |
| **Max Noise σ** | 20 pixels | Maximum, user-defined | **AMBIGUITY**: likely means σ = 20 intensity levels for Gaussian noise (not spatial pixels) | Controls severity of Gaussian noise | Increase σ toward 20, verify tracking still works |
| **Max Camera Jitter** | ±20 px/frame | Maximum, user-defined | Random per-frame translational offset of the camera viewport | Simulates platform vibration; makes tracking harder | Enable jitter at max, verify tracking handles it |
| **Max Platform Motion** | ±20 px/frame | Maximum, user-selectable | Systematic low-frequency motion of the camera platform | Simulates platform drift; linear is mandatory | Enable platform motion, verify system compensates |

> [!WARNING]
> **"Max Standard Deviation of Noise: 20 pixels"** — The unit "pixels" for a standard deviation of noise is unconventional. In image processing, Gaussian noise σ is typically in intensity units (0–255 for 8-bit). This is an ambiguity that could mean: (a) σ = 20 intensity levels, (b) σ = 20 as a spatial displacement in pixels (which would be spatial jitter, not noise), or (c) a typo. The most likely interpretation is **(a) σ = 20 intensity levels** for Gaussian noise. Our system should allow this to be configurable regardless.

---

## 6. Disturbance Model Analysis

### 6.1 Salt-and-Pepper Noise

| Aspect | Detail |
|---|---|
| **PS requirement** | User-selectable; "around 10% of image" (Row 21) |
| **Parameter provided** | ~10% density |
| **Not specified** | Whether 10% is fixed or a maximum; whether it's purely random or spatially correlated |
| **Engineering assumption** | Standard i.i.d. salt-and-pepper: each pixel has 10% chance of being flipped to 0 or 255 |
| **Effect on tracking** | Creates bright/dark pixel outliers; could create false beacon detections if not filtered |
| **Testing** | Apply S&P at 10%, verify detection still works; test at higher densities as stress test |

### 6.2 Gaussian Noise

| Aspect | Detail |
|---|---|
| **PS requirement** | User-selectable; max σ = 20 (Row 22) |
| **Parameter provided** | Maximum standard deviation |
| **Not specified** | Mean (presumably 0), whether it's additive, whether it's per-channel or single-channel (monochrome) |
| **Engineering assumption** | Additive white Gaussian noise, zero mean, σ ∈ [0, 20] intensity levels |
| **Effect on tracking** | Reduces SNR of the beacon against background; makes centroiding less precise |
| **Testing** | Sweep σ from 0 to 20, measure tracking error degradation |

### 6.3 Poisson Noise

| Aspect | Detail |
|---|---|
| **PS requirement** | User-selectable (Row 21) |
| **Parameter provided** | None explicitly — Poisson noise is signal-dependent |
| **Not specified** | How to parameterize it; Poisson noise depends on photon count / intensity |
| **Engineering assumption** | Apply Poisson noise model where each pixel value is treated as the expected photon count; noise variance equals the signal intensity |
| **Effect on tracking** | Primarily affects low-light conditions; variance increases with brightness (unlike Gaussian) |
| **Testing** | Enable Poisson noise, verify noise is signal-dependent, test tracking in low-light mode |

### 6.4 Camera Jitter

| Aspect | Detail |
|---|---|
| **PS requirement** | ±20 pixels/frame maximum, user-defined (Row 23) |
| **Parameter provided** | Max amplitude |
| **Not specified** | Distribution (uniform? Gaussian?); correlation between frames; frequency content |
| **Engineering assumption** | Random per-frame translational displacement of the viewport, uniformly or Gaussian distributed with max ±20px |
| **Effect on tracking** | Beacon appears to jump between frames; centroid estimation must be robust to this |
| **Testing** | Enable jitter at max, measure tracking error vs. jitter amplitude |

### 6.5 Atmospheric Disturbance

| Aspect | Detail |
|---|---|
| **PS requirement** | 5 modes: Clear, Haze, Fog, Rain, Low light; user-defined contrast/brightness reduction (Row 24) |
| **Parameter provided** | Modes listed; effect described as "reduction in contrast and brightness" |
| **Not specified** | Specific attenuation values; whether scintillation is included; exact visual model |
| **Engineering assumption** | Each mode applies a configurable multiplicative contrast reduction and additive brightness offset. No complex atmospheric propagation model is required — the PS explicitly says "user-defined reduction." |
| **Effect on tracking** | Reduces beacon-to-background contrast; makes detection harder, especially in fog + low light |
| **Testing** | Select each mode with increasing severity; verify tracking degrades gracefully |

> [!IMPORTANT]
> The PS does **not** require a physics-based atmospheric model. It explicitly says "user-defined reduction in contrast and brightness." Implementing scintillation, beam wander, or Kolmogorov turbulence would be an **OPTIONAL ENHANCEMENT**, not a requirement.

### 6.6 Platform Motion

| Aspect | Detail |
|---|---|
| **PS requirement** | ±20 pixels/frame max; mandatory: linear; optional: circular, random, spiral, figure-of-8 (Row 25) |
| **Parameter provided** | Max amplitude, mandatory pattern |
| **Not specified** | Velocity profile (constant? sinusoidal?); whether it's additive to camera jitter or separate |
| **Engineering assumption** | Platform motion is a **low-frequency, systematic drift** of the camera position, distinct from jitter (which is high-frequency random). Linear platform motion = constant velocity drift in one direction. |
| **Effect on tracking** | Creates a moving baseline that the tracker must compensate for; combined with jitter, makes tracking significantly harder |
| **Testing** | Enable linear platform motion at max rate, verify tracking compensates; test with combined disturbances |

### 6.7 Combined Disturbances

The PS states disturbances are "user-selectable (one or more)" — meaning evaluators **will likely combine multiple disturbances simultaneously**. This is a critical stress test scenario.

---

## 7. Evaluation Methodology Analysis

### 7.1 Functional Verification — 20%

| Aspect | Detail |
|---|---|
| **What judges do** | Teams get 10–15 minutes to demonstrate the software live |
| **What they observe** | (1) All mandatory functions implemented, (2) Operational success — does it work?, (3) GUI quality |
| **Metrics that matter** | Completeness of features; stability; visual polish of GUI; ease of use |
| **Make-or-break** | Missing any mandatory function (e.g., no MP4 input, no noise injection) could be catastrophic. A crash during demo would be devastating. |
| **Failure modes** | Crash, missing features, ugly/non-functional GUI, inability to configure parameters, slow startup |
| **Architecture implications** | Need a robust, well-tested GUI; need to pre-plan the demo flow; need fail-safe error handling |

**Relative importance**: 20% — significant but not the largest component. This is essentially a "gate" — you must pass this to be competitive.

### 7.2 Benchmark Performance-1 — 30%

| Aspect | Detail |
|---|---|
| **What judges do** | Provide "few scenarios" (simulator parameter sets); teams must execute them |
| **What they observe** | (1) Successful execution, (2) Centroiding error log, (3) Auto-generated performance logs |
| **Metrics that matter** | Centroiding error (primary), plus all performance log metrics: duration, FPS, acquisition time, avg/max tracking error, lock retention rate, processing time |
| **Make-or-break** | The system must be able to **load and run evaluator-defined scenarios** — this implies a scenario configuration interface (file-based or GUI). Centroiding error must be logged per-frame. |
| **Failure modes** | Cannot load scenario; crash during scenario; centroiding error too high; performance log missing or incomplete; FPS drops below 20 |
| **Architecture implications** | Need a scenario configuration format (JSON/YAML/XML); need robust per-frame logging; need centroid accuracy comparable to ground truth |

> [!IMPORTANT]
> **INFERENCE**: The evaluators will provide scenario configurations. The system needs a **well-defined scenario input format** that evaluators can use. This should probably be documented in the user manual. If the evaluators cannot easily configure a scenario, scoring will suffer.

**Relative importance**: 30% — the largest share (tied with benchmark-2). This is where quantitative performance matters most.

### 7.3 Benchmark Performance-2 — 30%

| Aspect | Detail |
|---|---|
| **What judges do** | Provide MP4 video files at 30 FPS, "covering a complete screen with noise and moving beacon spot." Teams must process these videos by bypassing the simulator's PTZ camera. |
| **What they observe** | (1) Centroiding error compared with predefined error values (i.e., ground truth exists), (2) RMSE, acquisition/re-acquisition time, lock retention rate, FPS |
| **Metrics that matter** | Centroiding accuracy vs. ground truth; RMSE; temporal metrics |
| **Make-or-break** | The tracking pipeline must work on **external video input**, completely independent of the simulator. The beacon in the MP4 will have noise and disturbances already baked in. Ground truth centroids will be compared against our computed centroids. |
| **Failure modes** | Cannot load MP4; tracker fails on unfamiliar noise/beacon characteristics; centroiding error exceeds predefined thresholds; system too slow at 30 FPS |
| **Architecture implications** | The detection/tracking pipeline must be **decoupled** from the simulator. A clean input abstraction is needed: either "frames from simulator" or "frames from MP4 file." The tracker must be robust to unknown noise characteristics. |

> [!IMPORTANT]
> **INFERENCE**: The phrase "covering a complete screen" is critical. The MP4 videos likely show the **full scene** (the equivalent of the 2000×2000 screen), and the tracker must process these as if they were the camera feed. Since the PTZ camera is bypassed, the tracker receives the full-scene frames and must detect the beacon anywhere in the frame. This means the "camera viewport" concept does not apply — the tracker works directly on full-resolution frames.

> [!WARNING]
> **ALTERNATIVE INFERENCE**: "Covering a complete screen" could also mean the MP4 covers the camera viewport (640×480) with the beacon already in view — i.e., the PTZ has already acquired the target and the task is purely centroiding/tracking within the frame. This interpretation would make more sense for a "coarse pointing" benchmark since the PTZ is bypassed. **The PS is ambiguous on this point.**

**Relative importance**: 30% — tied for largest. This is the most challenging evaluation stage because it tests the tracker in isolation with unknown inputs.

### 7.4 Technical Evaluation — 20%

| Aspect | Detail |
|---|---|
| **What judges do** | Teams present their approach, architecture, algorithms, etc. |
| **What they observe** | 7 sub-criteria: (1) Problem understanding, (2) Architecture & design, (3) Algorithm selection, (4) AI/CV usage, (5) Innovation & novelty, (6) Documentation & presentation, (7) Q&A |
| **Metrics that matter** | Depth of understanding; quality of design decisions; appropriateness of algorithms; genuine AI/CV contribution; novelty; documentation quality; ability to defend decisions |
| **Make-or-break** | Using AI/CV superficially or incorrectly will score poorly. Having no innovation/novelty will cost points. Poor documentation will cost points. |
| **Failure modes** | Inability to explain design choices; no genuine AI contribution; copy-pasted architecture; poor technical report; unable to answer technical questions |
| **Architecture implications** | Must make deliberate, defensible algorithm choices; must genuinely use AI/CV (not just threshold-based detection); must have novel aspects; documentation must be thorough |

**Relative importance**: 20% — equal to functional verification. This is where intellectual depth matters.

### Aggregate Scoring Strategy

| Stage | Weight | Nature | Priority Implication |
|---|---|---|---|
| Functional Verification | 20% | Pass/fail gate | Must work reliably; focus on completeness and stability |
| Benchmark-1 | 30% | Quantitative performance | Optimize tracker performance; robust scenario loading |
| Benchmark-2 | 30% | Quantitative performance on unknown data | Tracker robustness and decoupled architecture |
| Technical Evaluation | 20% | Qualitative assessment | Depth, AI/CV contribution, innovation, documentation |

**60% of the score is quantitative benchmark performance.** This means tracker accuracy and robustness are overwhelmingly the most important factors.

---

## 8. Hidden Engineering Implications

> [!NOTE]
> All items in this section are labeled as **INFERENCE** — they are not explicit requirements but are strongly implied by the PS.

### 8.1 Ground-Truth Mechanism — INFERENCE

The simulator knows the exact beacon position at every frame (it generates it). The tracker computes an estimated position. To compute tracking error, centroiding error, and RMSE, the system needs **internal access to ground truth**. This must be computed within the simulator but **not** fed to the tracker — the tracker must work only from the camera image.

For benchmark-2, ground truth is provided externally by the evaluators ("predefined error values"). This means our system must **export centroids in a format comparable to evaluator ground truth**.

### 8.2 Deterministic/Reproducible Scenarios — INFERENCE

For benchmark-1, evaluators provide scenarios. If results are not reproducible, debugging and fair comparison are impossible. The simulator should support **seeded random number generation** so that identical parameters produce identical scenarios.

### 8.3 Tracker Independence from Simulator — INFERENCE

Benchmark-2 explicitly requires bypassing the PTZ camera and feeding MP4 directly to the tracker. This **mandates** that the tracker is architecturally independent of the simulator. It must consume frames from an abstract source (either the virtual camera or a video file).

### 8.4 MP4 Input Abstraction — INFERENCE

The system needs a **video source abstraction**: an interface that provides frames, regardless of whether they come from the simulator or an MP4 file. This is not optional — benchmark-2 requires it.

### 8.5 Detection vs. Tracking Separation — INFERENCE

The PS describes two phases: "acquire and detect" then "continuously track." These are logically distinct:
- **Detection (acquisition)**: Finding the beacon when its location is unknown.
- **Tracking**: Following a beacon whose approximate location is already known.

Separating these enables different algorithms for each phase and explicit state management (searching → acquired → tracking → lost → re-acquiring).

### 8.6 Frame-Level Performance Logging — INFERENCE

The performance metrics (centroiding error, tracking error, lock retention) must be computed per-frame to produce meaningful averages, maximums, and time-series. The performance logger must record per-frame data, not just aggregate statistics.

### 8.7 FOV-to-Pixel Mathematical Relationship — INFERENCE

The camera FOV (default 4°×3°) maps to the viewport resolution (640×480). The pan/tilt speeds are in °/s. To convert between angular commands and pixel movements on the 2000×2000 screen, a mathematically consistent projection model is needed.

- Default mapping: 4° / 640px = 0.00625 °/px
- Pan speed 5 °/s → 5 / 0.00625 = 800 px/s on the screen
- At 20 Hz update rate → 40 px per PTZ update
- At 30 Hz camera rate → ~26.7 px per frame

This relationship must be consistent and documented.

### 8.8 PTZ Velocity Constraints — INFERENCE

The PS specifies **maximum** pan and tilt speeds. This means the PTZ controller cannot instantly teleport the camera to a new position. The camera must **slew** at bounded velocity. This implies the control algorithm must generate velocity commands, not position jumps.

### 8.9 Acquisition and Re-acquisition State Machine — INFERENCE

The PS defines separate metrics for acquisition time (≤ 2s) and re-acquisition time (≤ 1s). This implies the system must have **explicit state handling**:
- **SEARCHING** → (beacon found) → **ACQUIRED/TRACKING**
- **TRACKING** → (beacon lost) → **LOST**
- **LOST** → (beacon found again) → **RE-ACQUIRED/TRACKING**

Timers for acquisition and re-acquisition must be tracked per-state-transition.

### 8.10 The "Screen" is NOT a Displayed Image — INFERENCE

The 2000×2000 "screen" is the **simulation world**. The camera viewport (640×480) is a small window into this world. The tracker only sees the viewport. The "screen" concept is internal to the simulator — the user sees the camera viewport (possibly alongside a bird's-eye view of the full screen for debugging/visualization).

---

## 9. Ambiguities and Unanswered Questions

### AMB-001: "Tracking Error ≤ 10 pixels" — what exactly is measured?

**Why it matters**: Is tracking error the Euclidean distance between beacon centroid and frame center? Or is it the Euclidean distance between estimated centroid and true centroid? These are different metrics.

**Sensible interpretation**: Tracking error = distance between estimated beacon centroid and the center of the camera viewport. This measures how well the PTZ keeps the beacon centered.

**Centroiding error** (mentioned in evaluation) = distance between estimated centroid and true centroid of the beacon. This measures detection/estimation accuracy.

**Recommendation**: Implement and log both. Keep the system flexible.

### AMB-002: "Max Standard Deviation of Noise: 20 pixels"

**Why it matters**: "Pixels" is not the standard unit for noise standard deviation. Gaussian noise σ is in intensity units. Camera jitter is in pixels.

**Sensible interpretation**: σ = 20 in intensity levels (0–255 scale for 8-bit monochrome). The "pixels" label is likely an error in the PS table or refers to the row numbering format.

**Recommendation**: Implement as intensity-level σ but allow configuration in case the evaluators mean something else.

### AMB-003: Exact camera projection model

**Why it matters**: The FOV-to-pixel mapping determines how angular PTZ commands translate to pixel shifts on the screen.

**Not defined**: Whether it's a simple linear (pinhole) projection or something else.

**Sensible interpretation**: Simple linear mapping. FOV 4° across 640 pixels → 0.00625 °/px. No lens distortion.

**Recommendation**: Use linear mapping as default but design the camera model to be replaceable.

### AMB-004: Beacon intensity/contrast relative to background

**Why it matters**: Beacon detectability depends on contrast. The PS does not specify beacon brightness, background brightness, or contrast ratio.

**Not defined**: Beacon intensity, background intensity, contrast ratio.

**Sensible interpretation**: The beacon is a bright spot on a dark background (typical for FSOC beacon detection). Make intensity and background configurable.

**Recommendation**: Allow user-configurable beacon intensity and background level. Default to high contrast.

### AMB-005: Target velocity limits

**Why it matters**: If the target moves faster than the camera can slew, the tracker will inevitably lose it. The PS does not specify maximum target speed.

**Not defined**: Maximum beacon velocity on the screen.

**Sensible interpretation**: Target velocity should be physically plausible — the camera must be able to track it. If max pan speed is 800 px/s (from §8.7), target speed should not vastly exceed this.

**Recommendation**: Make target velocity configurable. Ensure default scenarios are trackable.

### AMB-006: Whether ground truth is available during benchmark-2

**Why it matters**: Benchmark-2 compares centroiding error with "predefined error values." This means evaluators have ground truth. But does our system receive it?

**Sensible interpretation**: No — our system processes the MP4 blind. The evaluators compare our output centroids with their ground truth externally.

**Recommendation**: Our system must **export** per-frame centroid estimates in a standard format (CSV/log) that evaluators can compare.

### AMB-007: Benchmark scenario format

**Why it matters**: For benchmark-1, evaluators provide "scenarios." The format is unspecified.

**Not defined**: Whether scenarios are configuration files, verbal instructions, or GUI interactions.

**Sensible interpretation**: Likely parameter sets that the team enters into the GUI or loads as configuration files.

**Recommendation**: Support both GUI configuration and file-based scenario loading. Document the scenario format clearly.

### AMB-008: What "centroiding error" means precisely

**Why it matters**: It's evaluated in both benchmarks but not formally defined.

**Sensible interpretation**: Euclidean distance between the algorithm's estimated beacon centroid and the true beacon centroid, measured in pixels.

**Recommendation**: Use this definition. Log it per-frame.

### AMB-009: What "covering a complete screen" means in benchmark-2

**Why it matters**: Determines whether the MP4 shows the full 2000×2000 world or just the 640×480 viewport.

**Sensible interpretation**: The MP4 likely shows a full frame (possibly at a different resolution) with a beacon and noise. The tracker must find and track the beacon in these frames without PTZ control.

**Recommendation**: Design the tracker to handle arbitrary input resolutions. Do not hard-code 640×480.

### AMB-010: Whether the PTZ camera should have inertia/lag

**Why it matters**: Real pan-tilt mechanisms have inertia, acceleration limits, and settling time. The PS only specifies maximum speed.

**Not defined**: Acceleration limits, inertia, settling time.

**Sensible interpretation**: The PS only specifies max speed and update rate. A simple velocity-limited model (no inertia) is likely sufficient.

**Recommendation**: Implement simple velocity-limited PTZ as default. Optionally add inertia as an enhancement.

---

## 10. Potential Benchmark Attack Surfaces

### Scenarios Explicitly Implied by the PS

| # | Scenario | PS Basis | Risk Level |
|---|---|---|---|
| 1 | Very small beacon (5×5 px) | Row 10: size range 5–20 | **High** — detection at minimum size with noise is very challenging |
| 2 | High noise (σ = 20, S&P = 10%) | Rows 21–22 | **High** — combined noise severely degrades SNR |
| 3 | Low contrast (fog + low light) | Row 24 | **High** — beacon may be nearly invisible |
| 4 | Camera jitter at max (±20 px/frame) | Row 23 | **Medium** — motion blur equivalent at 20px is significant |
| 5 | Platform motion at max (±20 px/frame) | Row 25 | **Medium** — systematic drift compounds tracking difficulty |
| 6 | Combined disturbances (all at once) | PS says "one or more" user-selectable | **Critical** — the hardest test case |
| 7 | Fast target motion (near camera slew limit) | Implied by motion patterns | **High** — tests whether controller can keep up |
| 8 | Re-acquisition after loss | PR-004 requires ≤ 1s | **High** — tests state machine and recovery logic |
| 9 | Unknown MP4 input | Benchmark-2 | **Critical** — no control over input characteristics |

### Proposed Stress Tests (INFERENCE — not in PS)

| # | Scenario | Why It's Dangerous | Likelihood of Evaluator Using It |
|---|---|---|---|
| 10 | Target near FOV boundary | Tracker might oscillate or lose track | Medium |
| 11 | Target entering from outside FOV | Tests acquisition when target appears at edge | Medium |
| 12 | Multiple bright objects / false targets | Tests discrimination; PS mentions multiple targets as optional | Low–Medium |
| 13 | Temporary target disappearance (occlusion) | Tests loss detection and re-acquisition | Medium |
| 14 | Very rapid direction change (figure-of-8 at high speed) | Tests controller responsiveness | High |
| 15 | Low FPS processing bottleneck | If system slows below 20 FPS under combined disturbances | Medium |
| 16 | Different MP4 resolution than expected | Tests robustness of input handling | Medium |
| 17 | Beacon intensity variation over time (fading) | Tests adaptive thresholding | Low |
| 18 | Non-square beacon (if target shape is changed) | Tests shape-agnostic detection | Low |

---

## 11. Conceptual Feature Inventory

### Core Simulator
| Feature | Justification |
|---|---|
| 2D scene canvas (≥ 2000×2000) | **PS-required** (Row 1) |
| Configurable background | **Engineering recommendation** — needed for contrast control |
| Scene coordinate system | **PS-required** — implicit in all parameters |
| Simulation clock / time management | **PS-required** — needed for FPS, timing metrics |
| Scenario configuration loading | **Evaluation-driven** — benchmark-1 requires evaluator scenarios |
| Deterministic seeded randomness | **Engineering recommendation** — reproducibility |

### Target Generator
| Feature | Justification |
|---|---|
| Single beacon generation | **PS-required** (Row 7–8) |
| Configurable size (5–20px), shape, intensity | **PS-required** (Rows 9–10) |
| 4 mandatory motion patterns | **PS-required** (Row 12) |
| Configurable initial position | **PS-required** (Row 11) |
| Configurable target speed | **Engineering recommendation** — needed for meaningful scenarios |
| Multiple beacons | **PS-optional** (Row 8) |
| Additional motion patterns (spiral, sinusoidal) | **PS-optional** (Row 12) |
| User-defined trajectory | **Innovation opportunity** |

### Camera Model
| Feature | Justification |
|---|---|
| Viewport extraction from scene (640×480 from 2000×2000) | **PS-required** |
| FOV configuration with consistent angular-pixel mapping | **PS-required** (Row 4) |
| Monochrome rendering | **PS-required** (Row 2) |
| Camera position tracking (pan/tilt state) | **PS-required** |
| Initial position at center | **PS-required** (Row 6) |
| Colour mode | **PS-optional** (Row 2) |
| Configurable resolution | **PS-optional** (Row 3) |

### Disturbance Engine
| Feature | Justification |
|---|---|
| Salt & pepper noise | **PS-required** (Row 21) |
| Gaussian noise | **PS-required** (Row 21) |
| Poisson noise | **PS-required** (Row 21) |
| Camera jitter | **PS-required** (Row 23) |
| Atmospheric modes (clear/haze/fog/rain/low-light) | **PS-required** (Row 24) |
| Platform motion (linear mandatory) | **PS-required** (Row 25) |
| Combined disturbance stacking | **PS-required** — "one or more" user-selectable |
| Configurable parameters for all disturbances | **PS-required** — "user-defined" / "user-selectable" |
| Additional platform motion patterns | **PS-optional** (Row 25) |

### Detection / Tracking System
| Feature | Justification |
|---|---|
| Automatic beacon detection (acquisition) | **PS-required** (Line 75) |
| Continuous centroid tracking | **PS-required** (Line 76) |
| AI/CV-based approach | **Evaluation-driven** — "AI and computer vision" is a scoring criterion |
| State machine (searching/tracking/lost/re-acquiring) | **Engineering recommendation** — needed for acquisition/re-acquisition metrics |
| Centroid estimation | **PS-required** — centroiding error is evaluated |
| Noise-robust detection | **PS-required** — must work with all noise types |

### PTZ Control
| Feature | Justification |
|---|---|
| Velocity-limited pan/tilt control | **PS-required** (Rows 13–14) |
| Update rate ≥ 20 Hz | **PS-required** (Row 15) |
| Control algorithm (e.g., proportional, PID) | **Engineering recommendation** |
| Speed constraint enforcement | **PS-required** |

### Benchmarking
| Feature | Justification |
|---|---|
| Scenario loading and execution | **Evaluation-driven** (benchmark-1) |
| MP4 video input mode | **PS-required** (benchmark-2, Line 113) |
| Per-frame centroiding error logging | **Evaluation-driven** (benchmark-1 & 2) |
| RMSE computation | **Evaluation-driven** (benchmark-2) |
| Acquisition/re-acquisition time measurement | **PS-required** |
| Lock retention rate computation | **Evaluation-driven** |
| Performance log auto-generation | **PS-required** (Line 103) |

### Visualization
| Feature | Justification |
|---|---|
| Camera viewport display (primary view) | **PS-required** |
| Real-time tracking overlay (crosshair, bounding box) | **PS-required** (Line 79) |
| Real-time statistics display | **PS-required** (Line 79) |
| GUI with parameter controls | **Evaluation-driven** (GUI is scored) |
| Bird's-eye view of full scene | **Engineering recommendation** — debugging and demonstration |
| Real-time error plot | **Innovation opportunity** |

### Input/Output
| Feature | Justification |
|---|---|
| GUI parameter configuration | **PS-required** |
| File-based scenario loading | **Evaluation-driven** |
| Performance log file export | **PS-required** |
| Centroid log export | **Evaluation-driven** |
| Video file input (MP4) | **PS-required** |

### Experiment Management
| Feature | Justification |
|---|---|
| Scenario save/load | **Engineering recommendation** |
| Batch execution | **Innovation opportunity** |
| Result comparison | **Innovation opportunity** |

### AI/CV Capabilities
| Feature | Justification |
|---|---|
| ML-based beacon detection | **Evaluation-driven** — scored under "AI and computer vision" |
| Adaptive thresholding | **Engineering recommendation** |
| Noise-aware processing | **PS-required** — must handle all noise types |
| Motion prediction | **Innovation opportunity** |

### Optional Innovation Features
| Feature | Justification |
|---|---|
| Kalman filter / predictive tracking | **Innovation opportunity** — improves tracking through occlusion/noise |
| Multi-scale detection | **Innovation opportunity** — handles variable beacon sizes |
| Adaptive algorithm switching | **Innovation opportunity** — different strategies for different conditions |
| Hardware acceleration (GPU) | **Innovation opportunity** — ensures real-time performance |

---

## 12. Challenging the Obvious Solution

### The "Default" Approach

The naive approach is: "Use YOLO/SSD for detection + OpenCV template matching + PID controller." Let's critically examine this.

### Why Standard Object Detection (YOLO, SSD, etc.) is Questionable

| Issue | Explanation |
|---|---|
| **Target is 5–20 pixels** | YOLO/SSD are designed for objects that are typically 50–500+ pixels. A 5×5 pixel beacon is smaller than most detection network receptive fields. These models will likely **fail** on such small targets. |
| **No texture/shape complexity** | The beacon is a simple bright square on a dark background. Deep learning object detection is designed for complex, textured objects. Using a 50M-parameter model to find a bright square is engineering overkill with questionable reliability. |
| **Training data** | What would you train on? Simulated beacons? This is circular — you'd be training a model on data generated by your own simulator. |
| **Inference speed** | Heavy models may struggle to maintain ≥ 20 FPS on CPU-only systems. The PS requires a standalone executable — GPU availability is not guaranteed. |
| **Robustness to noise** | Standard detectors are not specifically trained for salt-and-pepper noise, Poisson noise, or extreme Gaussian noise. Fine-tuning is needed. |

### More Appropriate Algorithm Classes

#### For Detection (Acquisition Phase)

| Algorithm Class | Suitability | Considerations |
|---|---|---|
| **Intensity thresholding + blob detection** | High for high-contrast scenarios | Simple, fast, but fails under noise and low contrast |
| **Morphological filtering + connected components** | High | Effective noise rejection; fast |
| **Matched filtering / correlation** | High | Template is known (small bright square); robust to noise |
| **CFAR (Constant False Alarm Rate) detection** | Very high | Standard in radar/FSOC for detecting point targets in noise; statistically principled |
| **Wavelet-based detection** | Medium | Good for multi-scale; potentially overkill |
| **Lightweight CNN (custom, small)** | Medium | Could be effective if trained properly; adds AI criterion points |
| **Centroid-of-intensity (center of mass)** | High for tracking | Standard approach once beacon is roughly located |

#### For Tracking (Continuous Phase)

| Algorithm Class | Suitability | Considerations |
|---|---|---|
| **Centroid tracking (intensity-weighted center of mass)** | Very high | Standard for point-source tracking; fast; accurate |
| **Kalman filter** | Very high | Predicts next position; handles jitter and temporary loss; well-understood |
| **Extended Kalman / Unscented Kalman** | High | For non-linear motion models (figure-of-8, circular) |
| **Particle filter** | Medium | More robust to non-Gaussian noise; heavier computation |
| **Optical flow** | Medium | Can track motion between frames; complementary to centroid |
| **Mean-shift / CAMshift** | Low–Medium | Designed for larger objects; may not work well on 5-pixel targets |
| **Deep SORT / tracking-by-detection** | Low | Overkill for single point target |

#### For Control (PTZ)

| Algorithm Class | Suitability | Considerations |
|---|---|---|
| **Proportional control (P)** | Basic | Simple but may oscillate |
| **PID control** | High | Standard; well-tuned PID handles most scenarios |
| **Model Predictive Control (MPC)** | High | Can incorporate velocity constraints naturally; more sophisticated |
| **Feed-forward + feedback** | High | Use motion prediction for feed-forward, centroid error for feedback |
| **LQR** | Medium | Optimal linear control; may be overengineered for this application |

### Key Insight

The right approach for this problem is more akin to **astronomical point-source tracking** or **radar target tracking** than **computer vision object detection**. The algorithms used in astronomical CCD centroiding, satellite tracking, and radar signal processing are far more appropriate than consumer computer vision models.

That said, the evaluation criteria explicitly score "AI and computer vision" — so there should be a genuine AI/ML component. A hybrid approach is likely optimal:
- Classical signal processing for robust detection/centroiding
- ML/AI for adaptive noise handling, motion prediction, or algorithm selection
- This gives both reliability and evaluation points

> [!CAUTION]
> **Do not select the final algorithm yet.** This section identifies algorithm *classes* for evaluation. The final selection should be made after prototyping and benchmarking in a later stage.

---

## 13. Final Strategic Conclusion

### A. What the PS Definitely Requires

1. A working software simulator with a 2D scene (≥ 2000×2000), movable camera viewport (640×480), and configurable beacon.
2. Four mandatory beacon motion patterns.
3. Three noise types, five atmospheric modes, camera jitter, and linear platform motion — all user-configurable.
4. Automatic beacon detection and continuous centroid tracking.
5. PTZ control with velocity constraints (≤ 10 °/s) and ≥ 20 Hz update rate.
6. MP4 video input mode (bypass simulator).
7. Automatic performance logging with prescribed metrics.
8. Real-time visualization with tracking statistics.
9. Meeting all five performance thresholds: ≤ 2s acquisition, ≤ 10px error, < 5% loss, ≤ 1s re-acquisition, ≥ 20 FPS.
10. Standalone executable, source code, 10–15 page technical report, user manual.

### B. What We Should Build Beyond the Minimum

1. **Centroiding error log export** — explicitly scored but listed under evaluation, not deliverables.
2. **RMSE computation** — explicitly scored in benchmark-2.
3. **Polished, professional GUI** — scored in functional verification.
4. **Scenario file loading** — practically essential for benchmark-1.
5. **Kalman filter or predictive tracking** — significantly improves tracking performance and provides innovation points.
6. **Lightweight AI/ML component** — explicitly scored; must be genuine, not superficial.
7. **Multiple beacons and additional motion patterns** — demonstrates completeness.
8. **Bird's-eye view** for demonstration — impresses during functional verification.
9. **Frame-by-frame centroid logging** — needed for benchmark comparison.

### C. What We Should NOT Waste Time Building

1. ❌ **Deep learning object detection (YOLO, SSD, etc.)** for beacon detection — wrong tool for 5-pixel point targets.
2. ❌ **Realistic 3D rendering** — the PS describes a 2D screen; 3D adds complexity without scoring benefit.
3. ❌ **Physics-based atmospheric models** — the PS says "user-defined contrast and brightness reduction."
4. ❌ **Fine alignment / beam steering** — explicitly out of scope.
5. ❌ **Cloud/web deployment** — standalone executable is required.
6. ❌ **Multi-terminal communication simulation** — not evaluated.
7. ❌ **Complex lens distortion models** — not mentioned; simple linear projection suffices.
8. ❌ **Overly complex GUI frameworks** — functionality and clarity matter more than framework sophistication.

### D. Most Important Technical Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Detection failure at 5×5 px with combined noise | Cannot track what cannot be detected; benchmark failure | Use robust statistical detection (CFAR, matched filter); test extensively at minimum size + max noise |
| Processing speed drops below 20 FPS | Direct benchmark failure | Profile early; use efficient algorithms; avoid heavy ML inference on CPU |
| PTZ controller instability (oscillation, overshoot) | Poor tracking error, target loss | Tune control loop carefully; test with all motion patterns |
| MP4 input mode doesn't work with evaluator videos | 30% of score at risk | Test with varied MP4 formats, resolutions, codecs; make input handling robust |
| State machine failures (acquisition/re-acquisition) | Incorrect timing metrics | Implement explicit states with thorough testing |

### E. Most Important Benchmark Risks

| Risk | Impact |
|---|---|
| **Unknown MP4 characteristics** (benchmark-2) | 30% of score. We don't know the resolution, noise profile, beacon intensity, or motion pattern of evaluator videos. Our tracker must be fully adaptive. |
| **Unknown scenario parameters** (benchmark-1) | 30% of score. Evaluators may push parameters to extremes (min size, max noise, max jitter simultaneously). |
| **Centroiding accuracy vs. ground truth** | Both benchmarks compare our centroids against evaluator ground truth. If our centroid definition differs from theirs, systematic error results. |
| **Performance log format mismatch** | If our log format doesn't match what evaluators expect, scoring becomes difficult. |
| **Crash or failure during live demo** | 20% of score lost. Must be rock-solid. |

### F. Most Important Unanswered Questions

1. **What is the exact benchmark-2 MP4 format?** Resolution? Full scene or viewport? With or without ground truth file?
2. **What scenario configuration format will evaluators use for benchmark-1?**
3. **What is the precise definition of "centroiding error" vs. "tracking error"?**
4. **What does "20 pixels" mean for noise standard deviation — intensity levels or spatial?**
5. **What is the expected beacon contrast/intensity?**
6. **What is the maximum target velocity?**
7. **Does the standalone executable need to run on a specific OS?**
8. **Will evaluators have GPU-equipped machines?**

### G. Recommended Specification Order

```
1. Camera model & coordinate system     ← Foundation; everything depends on this
2. Scene & target generator             ← Needed before anything can be tested
3. Disturbance engine                   ← Determines the input difficulty
4. Detection algorithm                  ← Core capability #1
5. Centroid estimation                  ← Core capability #2
6. Tracking state machine              ← Acquisition/tracking/loss/re-acquisition
7. PTZ controller                      ← Closes the loop
8. Performance metrics & logging       ← Must be integrated early for testing
9. MP4 input mode                      ← Benchmark-2 requirement
10. GUI & visualization                ← For demo and usability
11. Scenario management                ← For benchmark-1
12. AI/ML integration                  ← For evaluation scoring
13. Innovation features                ← Polish and differentiation
14. Documentation & reports            ← In parallel throughout
```

> [!IMPORTANT]
> This analysis is complete. It is an independent technical review of the PS only. No architecture, PRD, SRS, or code has been produced. All inferences, recommendations, and assumptions are clearly labeled. This document should be reviewed by the team before proceeding to the architecture and design phase.
