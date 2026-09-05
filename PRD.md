# SIH 2026 — Product Requirements Document (PRD)

## AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile FSOC Terminals

> **Version:** 1.0
> **Date:** 2026-09-03
> **Authoritative Source:** [PS.md](file:///e:/Newfolder/Project2O/Projects/SIH%20'26/external/PS.md)
> **Preceding Analysis:** [analysis.md](file:///e:/Newfolder/Project2O/Projects/SIH%20'26/external/analysis.md)
> **Status:** PRD — awaiting team approval before architecture phase

---

# PART 1 — Requirements Reconciliation

## 1.1 Correct Interpretations (CONFIRMED)

The following conclusions from the previous analysis are directly supported by the PS:

- The system is a **software simulator + tracker**, not real hardware (PS L14, L25, L29).
- The "screen" is the simulation world (≥ 2000×2000); the camera viewport (640×480) is a window into it (PS Row 1, Row 3).
- The beacon is a small configurable bright spot (5–20 px) (PS Row 10).
- Four motion patterns are mandatory; additional patterns are optional (PS Row 12).
- Three noise types are required, all user-selectable (PS Row 21).
- Five atmospheric modes are required (PS Row 24).
- Platform motion with linear pattern is mandatory (PS Row 25).
- PTZ speeds are bounded (5–10 °/s range, default 5) (PS Rows 13–14).
- MP4 input mode is required for benchmark-2 (PS L113).
- Performance log must be auto-generated (PS L103).
- Application must be standalone executable (PS L87).
- 60% of score is quantitative benchmarks.

## 1.2 Unsupported Assumptions

| Item | Previous Claim | PS Evidence | Correction |
|---|---|---|---|
| "Camera jitter" is mandatory | Listed as MUST HAVE | PS Row 23 says "User-defined" — it is a configurable disturbance. The PS does not explicitly say it is mandatory, but it appears in the disturbance table alongside the other mandatory items. | **PARTIALLY SUPPORTED** — camera jitter appears as a disturbance parameter. PS L78 says "Generate and introduce disturbances due to... camera motion, noise, etc." which covers jitter. Treat as mandatory to implement, user-selectable to enable. |
| "The tracker must be architecturally independent of the simulator" | Stated as INFERENCE 8.3 | PS L113 says "bypass its PTZ camera and take this video as an input to the coarse pointing system." | **CONFIRMED** as operational requirement. The PS explicitly requires the coarse pointing (detection/tracking) pipeline to work without the PTZ simulator. The exact architectural pattern is an engineering choice, but the functional requirement is explicit. |
| "FOV-to-pixel mapping: 4°/640 = 0.00625°/px" | Stated as INFERENCE 8.7 | PS gives FOV as "user-defined, default 4°×3°" and resolution as 640×480. The math follows. But the PS does not state how the virtual camera should project. | **INFERENCE** — the calculation is mathematically correct given the defaults, but the PS does not prescribe a projection model. Keep this as an engineering decision, not a requirement. |
| "Scenario file loading is practically essential for benchmark-1" | Stated as evaluation-driven | PS L112 says "Each team will be given few scenarios" but does not define how. Scenarios could be verbal instructions, GUI parameter entry, or files. | **INFERENCE** — reasonable but not PS-mandated. The PS is ambiguous on the delivery method of benchmark-1 scenarios. |
| "State machine with explicit states is needed" | Stated as INFERENCE 8.9 | PS separately defines acquisition time (Row 16) and re-acquisition time (Row 19), implying the system must distinguish initial acquisition from re-acquisition. | **INFERENCE** — the PS requires measuring both metrics, which implies the system must detect the difference. The specific mechanism (state machine) is an engineering choice. |
| Platform motion is "low-frequency systematic drift" distinct from jitter | Stated as INFERENCE | PS Row 25 lists platform motion patterns (linear, circular, etc.) with ±20 px/frame max. PS Row 23 lists camera jitter separately at ±20 px/frame. | **INFERENCE** — the PS lists them as separate parameters, so they are distinct disturbances. The characterisation as "low-frequency systematic" vs "high-frequency random" is an engineering interpretation, not PS-specified. |

## 1.3 Ambiguities

| Item | PS Wording | Why Ambiguous | Status |
|---|---|---|---|
| "Max Standard Deviation of Noise: 20 pixels" | PS Row 22 (line 59) | "pixels" is not a standard unit for noise σ. Could mean intensity levels (0–255) or spatial pixels. | **AMBIGUOUS** — preserve in design; make configurable |
| "Tracking Error ≤ 10 pixels" | PS Row 17 | Not defined whether this is beacon-to-frame-center distance or estimated-vs-true centroid distance. | **AMBIGUOUS** — implement and log both interpretations |
| "Covering a complete screen" in benchmark-2 | PS L113 | Could mean: (a) the MP4 shows the full 2000×2000 scene, or (b) the MP4 shows a full-frame video with beacon visible, or (c) the beacon sweeps across the entire screen during the video. | **AMBIGUOUS** — do not resolve; design tracker to handle arbitrary resolutions |
| Benchmark-1 scenario delivery format | PS L112: "given few scenarios" | No specification of whether scenarios are config files, verbal, or GUI-driven. | **AMBIGUOUS** — support both GUI and file-based configuration |
| Beacon intensity / background level | Not specified anywhere | Contrast ratio is undefined; atmospheric modes describe "reduction" but no baseline. | **AMBIGUOUS** — make both configurable |
| Target velocity / speed | Not specified | PS defines motion patterns but not the speed of the beacon along those patterns. | **AMBIGUOUS** — make configurable |
| "Centroiding error" definition | PS L112, L113 — used but not defined | No mathematical definition provided. | **AMBIGUOUS** — propose definition, label it |
| Camera update rate (30 Hz) vs PTZ update rate (20 Hz) vs processing speed (20 FPS) | PS Rows 5, 15, 20 | Three separate rates. The PS does not clarify if the camera generates frames at 30 Hz while the processing pipeline only needs to achieve 20 FPS. | **AMBIGUOUS** — the camera generates at ≥30 Hz; the tracker must process at ≥20 FPS; the PTZ updates at ≥20 Hz |

## 1.4 Corrections

| Item | Previous Interpretation | Correction | Reason |
|---|---|---|---|
| Analysis §4 "DO NOT NEED" #6: "Deep learning object detection trained on photorealistic data" | Stated as a blanket DO NOT NEED | **Partially overclaimed.** The PS title says "AI-Based" and evaluation criteria explicitly include "AI and computer vision." While heavy models like YOLO/SSD are likely inappropriate for 5px targets, dismissing all DL detection is too strong. A lightweight custom CNN or ML classifier could be appropriate. | The analysis correctly identified the *inappropriateness of large pretrained detectors* but should not have categorically rejected all deep learning. |
| Analysis §8.10: "The Screen is NOT a Displayed Image" | Stated as INFERENCE — user only sees viewport | **Partially overclaimed.** The PS does not say what the user sees. For functional verification (20%), judges evaluate GUI. A bird's-eye view of the full scene is not required but could be very helpful for demonstration. The previous analysis correctly labeled this as inference but some language was too definitive. | The PS does not prescribe what the GUI must show beyond "Display tracking performance and statistics in real-time" (L79). |
| Analysis §5: "Camera Resolution: 640×480 — Suggested with optional user-defined" | Called it "suggested" | **Correction**: PS Row 3 uses "Suggested Value" as a column header, but 640×480 is the primary value. "Optional: User-defined" means the user may change it. The 640×480 is the **default**, not merely a suggestion. | Column header semantics — "Suggested Value" is the column name for all rows, not an indicator of optionality. |
| Analysis: S&P noise "around 10%" treated as configurable | Treated 10% as a suggested density | **Correction**: The PS says "around 10% of image" — this is the suggested density value, not a minimum or maximum. The user may configure it differently. | The word "around" indicates an approximate default, not a strict threshold. |

## 1.5 Missing Requirements

| Item | PS Source | What Was Missed |
|---|---|---|
| "Identifies" the target | PS L29: "autonomously detects, **identifies**, and continuously tracks" | The previous analysis covered detect and track but did not separately address "identifies." This could mean the system must confirm the detected object is indeed the beacon (vs. noise artifact or false target), especially relevant for multi-target scenarios. |
| "AI methods (if used)" in technical report | PS L95 | The technical report must document AI methods "if used." This implies AI is not strictly mandatory in the implementation — it is scored if present. The PS title says "AI-Based" but the report clause uses "if used." |
| Modular code requirement | PS L91: "The code shall be modular and adequately commented" | The previous analysis listed this under deliverables but did not extract it as a separate non-functional requirement about code quality. |
| GUI described in user manual | PS L99: "GUI description" in user manual | The user manual must describe the GUI — this is a deliverable requirement. |

## 1.6 Reconciliation Summary Table

| Item | Previous Interpretation | PS Evidence | Status | Correct Interpretation |
|---|---|---|---|---|
| Screen = simulation world, camera = viewport | 2000×2000 screen, 640×480 viewport | Rows 1, 3 | **CONFIRMED** | Correct |
| 4 mandatory motion patterns | Straight, circular, fig-8, random | Row 12 | **CONFIRMED** | Correct |
| Monochrome mandatory, colour optional | Rows 2 | Row 2 | **CONFIRMED** | Correct |
| Single target mandatory, multiple optional | Row 8 | Row 8 | **CONFIRMED** | Correct |
| PTZ speed constraints | 5–10°/s, default 5 | Rows 13–14 | **CONFIRMED** | Correct |
| MP4 input bypasses PTZ | L113 | L113 | **CONFIRMED** | Correct |
| Standalone executable | L87 | L87 | **CONFIRMED** | Correct |
| 5 performance thresholds | Rows 16–20 | Rows 16–20 | **CONFIRMED** | Correct |
| Camera jitter as mandatory | Listed as MUST HAVE | L78, Row 23 | **PARTIALLY SUPPORTED** | Must implement; user-selectable to enable |
| Tracker architectural independence | INFERENCE | L113 functional requirement | **CONFIRMED (functional)** | Functional separation required; architectural pattern is engineering choice |
| Noise σ = intensity levels | INFERENCE | PS says "20 pixels" | **AMBIGUOUS** | Preserve ambiguity; make configurable |
| Tracking error = beacon-to-center | INFERENCE | PS Row 17 — not defined | **AMBIGUOUS** | Log both interpretations |
| MP4 shows full scene | INFERENCE | PS says "covering a complete screen" | **AMBIGUOUS** | Handle arbitrary resolutions |
| Scenario file loading needed | INFERENCE | PS L112 — format undefined | **INFERENCE** | Support both GUI and file input |
| State machine for acq/re-acq | INFERENCE | PS Rows 16, 19 — separate metrics | **INFERENCE** | Must distinguish states; mechanism is engineering choice |
| AI/DL categorically rejected | Analysis §4 DO NOT NEED #6 | PS title: "AI-Based"; Eval: "AI and computer vision" | **INCORRECT** | AI/ML is evaluated; appropriate AI is needed |
| "Identifies" target | Not addressed | PS L29: "identifies" | **MISSING** | Must include target identification/confirmation capability |
| Code modularity | Mentioned in deliverables | PS L91: "modular and adequately commented" | **MISSING (as NFR)** | Add as non-functional requirement |

---

# PART 2 — Product Vision

## Product Definition

> A standalone software application that simulates a virtual camera tracking environment for Free Space Optical Communication (FSOC) coarse alignment, enabling autonomous detection, identification, and continuous tracking of a moving optical beacon within a configurable 2D scene with disturbances, while measuring and logging performance against defined benchmarks — including the ability to process external MP4 video files independently of the simulation engine.

## Product Objective

Deliver a complete, evaluation-ready software system that:
1. **Simulates** a virtual FSOC coarse alignment environment with configurable scene, beacon, camera, disturbances, and motion.
2. **Detects and tracks** a moving beacon autonomously using AI-assisted computer vision techniques.
3. **Controls** a virtual pan-tilt camera to maintain the beacon near frame center.
4. **Measures** and **logs** tracking performance against defined metrics.
5. **Processes** external MP4 video files for benchmark evaluation independently of the simulator.
6. **Demonstrates** all capabilities through a functional GUI with real-time statistics.

## Primary Users

| User | Role | Primary Needs |
|---|---|---|
| **SIH Evaluators** | Score the solution across 4 evaluation stages | Quick setup, scenario loading, MP4 input, clear performance output, stable operation |
| **Development Team** | Build, test, and validate the system | Configurable parameters, reproducible scenarios, debugging views, performance profiling |
| **Testing/Validation Team** | Verify performance against PS thresholds | Benchmark execution, metrics computation, automated logging, ground truth comparison |

## Primary Use Cases

| UC | Use Case | User | Justification |
|---|---|---|---|
| UC-01 | Run simulation with configurable parameters and observe beacon tracking | Dev team, evaluators | PS L72–79 (expected solution), Eval L111 (functional verification) |
| UC-02 | Test tracking under controlled disturbances (noise, jitter, atmosphere, platform) | Dev team, evaluators | PS L78, Rows 21–25 |
| UC-03 | Load and execute evaluator-defined scenarios | Evaluators | PS L112 (benchmark-1) |
| UC-04 | Process evaluator-provided MP4 files with tracker only | Evaluators | PS L113 (benchmark-2) |
| UC-05 | Review auto-generated performance logs and metrics | Evaluators, dev team | PS L103, L112, L113 |
| UC-06 | Configure and compare tracking under different parameter sets | Dev team | PS L29 (functional objective — algorithm development) |
| UC-07 | Demonstrate full system during 10–15 min live demo | Evaluators | PS L111 (functional verification) |

---

# PART 3 — Product Scope

## IN SCOPE

| Area | Description | PS Source |
|---|---|---|
| Virtual environment generation | 2D scene canvas ≥ 2000×2000 pixels with configurable parameters | L72, Row 1 |
| Beacon / target generation | Configurable beacon spot(s) with motion patterns | L73, Rows 7–12 |
| Virtual camera (PTZ) | Monochrome viewport (640×480) with FOV, pan/tilt control, speed constraints | L74, Rows 1–6, 13–15 |
| Disturbance engine | Noise (S&P, Gaussian, Poisson), camera jitter, atmospheric modes, platform motion | L78, Rows 21–25 |
| Beacon detection | Autonomous AI/CV-based detection | L75, L29 |
| Beacon identification | Confirmation that detected object is the beacon | L29 ("identifies") |
| Continuous tracking | CV-based centroid tracking | L76 |
| Camera control | Reposition camera to keep beacon centered | L77 |
| Real-time visualization | Display tracking status, performance, statistics | L79 |
| Performance logging | Auto-generated report with prescribed metrics | L103 |
| MP4 video input | Accept external MP4, bypass PTZ, run tracker | L113 |
| GUI | User interface for configuration, control, and observation | L111 (evaluation criterion) |
| Deliverables | Executable, source code, technical report, user manual, performance log | L83–103 |

## OUT OF SCOPE

| Area | Reason |
|---|---|
| Fine alignment / fine pointing | PS L12: coarse alignment only; fine alignment is the next stage |
| Real hardware interfaces | PS L14: software-based virtual tracking |
| Physics-based atmospheric propagation | PS Row 24: "user-defined reduction in contrast and brightness" |
| Communication link simulation | Not mentioned in PS |
| 3D scene rendering | PS describes a 2D screen with a beacon spot |
| Multi-platform networking | Not mentioned |
| Real-time embedded constraints | PS is software; no embedded system requirements |
| Lens distortion models | Not mentioned |

## OPTIONAL / FUTURE

| Area | PS Basis | Justification |
|---|---|---|
| Colour camera mode | Row 2: "Optional: Colour" | PS-listed optional feature |
| User-defined camera resolution | Row 3: "Optional: User-defined" | PS-listed optional feature |
| Multiple targets | Row 8: "multiple optional" | PS-listed optional feature |
| Additional motion patterns (spiral, sinusoidal, user-defined) | Row 12: "Optional" | PS-listed optional feature |
| Additional platform motion patterns (circular, random, spiral, fig-8) | Row 25: "Optional" | PS-listed optional feature |
| User-defined screen size beyond 2000×2000 | Row 1: "Optional: User-defined" | PS-listed optional feature |
| Demo video (3–5 min) | L99: "may also be provided as an optional deliverable" | PS-listed optional deliverable |

---

# PART 4 — Product Feature Specification

## 4.1 Virtual Environment

### FEAT-ENV-001: Scene Canvas

| Field | Value |
|---|---|
| **Feature ID** | FEAT-ENV-001 |
| **Feature Name** | Scene Canvas |
| **Description** | Generate a 2D scene of configurable size (minimum 2000×2000 pixels) that serves as the world in which the beacon moves and the camera operates. |
| **Source** | PS Row 1 (L34), L72 |
| **Priority** | Must |
| **User Interaction** | Configure screen dimensions at startup or via GUI |
| **Inputs** | Screen width, screen height (≥ 2000×2000) |
| **Outputs** | Rendered scene canvas (internal data structure) |
| **Configurable Parameters** | Screen width, screen height |
| **Acceptance Criteria** | Scene canvas is created at specified dimensions; beacon and camera operate within bounds |
| **Dependencies** | None |
| **Benchmark Relevance** | Functional Verification, Benchmark-1 |

### FEAT-ENV-002: Scene Background

| Field | Value |
|---|---|
| **Feature ID** | FEAT-ENV-002 |
| **Feature Name** | Scene Background |
| **Description** | Render the scene background. The PS does not specify background characteristics; a uniform dark background is the minimal requirement for beacon contrast. |
| **Source** | INFERENCE — required for beacon visibility; atmospheric modes (Row 24) modify contrast/brightness relative to a baseline |
| **Priority** | Must |
| **User Interaction** | Configure background level (if exposed) |
| **Inputs** | Background intensity level |
| **Outputs** | Background pixels in the scene |
| **Configurable Parameters** | Background intensity (RECOMMENDATION — not PS-mandated) |
| **Acceptance Criteria** | Background renders; atmospheric modes can modify it |
| **Dependencies** | FEAT-ENV-001 |
| **Benchmark Relevance** | Functional Verification |

---

## 4.2 Virtual Camera

### FEAT-CAM-001: Camera Viewport

| Field | Value |
|---|---|
| **Feature ID** | FEAT-CAM-001 |
| **Feature Name** | Camera Viewport Extraction |
| **Description** | Extract a viewport of configurable resolution (default 640×480) from the scene canvas, representing what the virtual camera "sees." |
| **Source** | PS Row 3, L74 |
| **Priority** | Must |
| **User Interaction** | Configure resolution (default 640×480) |
| **Inputs** | Camera position (pan/tilt state), scene canvas, resolution, FOV |
| **Outputs** | Camera frame (image at configured resolution) |
| **Configurable Parameters** | Resolution width, resolution height |
| **Acceptance Criteria** | Viewport correctly extracts the sub-region corresponding to current camera position and FOV |
| **Dependencies** | FEAT-ENV-001 |
| **Benchmark Relevance** | All stages |

### FEAT-CAM-002: Camera Type

| Field | Value |
|---|---|
| **Feature ID** | FEAT-CAM-002 |
| **Feature Name** | Camera Type (Monochrome / Colour) |
| **Description** | Camera operates in monochrome mode (mandatory). Optional colour mode. |
| **Source** | PS Row 2 |
| **Priority** | Must (mono), Could (colour) |
| **User Interaction** | Select camera type |
| **Inputs** | Type selection |
| **Outputs** | Monochrome or colour frame |
| **Configurable Parameters** | Camera type (mono/colour) |
| **Acceptance Criteria** | Default output is single-channel monochrome; colour mode produces 3-channel output |
| **Dependencies** | FEAT-CAM-001 |
| **Benchmark Relevance** | Functional Verification |

### FEAT-CAM-003: Camera FOV

| Field | Value |
|---|---|
| **Feature ID** | FEAT-CAM-003 |
| **Feature Name** | Field of View Configuration |
| **Description** | Camera FOV is user-defined with a default of 4°×3°. FOV determines how much of the scene canvas is visible in the viewport. |
| **Source** | PS Row 4 |
| **Priority** | Must |
| **User Interaction** | Enter FOV in degrees (horizontal × vertical) |
| **Inputs** | FOV_H, FOV_V (degrees) |
| **Outputs** | Viewport scaling factor applied to scene extraction |
| **Configurable Parameters** | FOV horizontal (default 4°), FOV vertical (default 3°) |
| **Acceptance Criteria** | Changing FOV changes the portion of scene visible in viewport; default 4°×3° is applied when not specified |
| **Dependencies** | FEAT-CAM-001 |
| **Benchmark Relevance** | Functional Verification, Benchmark-1 |

### FEAT-CAM-004: Camera Update Rate

| Field | Value |
|---|---|
| **Feature ID** | FEAT-CAM-004 |
| **Feature Name** | Camera Frame Generation Rate |
| **Description** | Camera generates frames at a minimum of 30 Hz. |
| **Source** | PS Row 5: "30 Hz (min.)" |
| **Priority** | Must |
| **User Interaction** | None (system-enforced minimum) |
| **Inputs** | None |
| **Outputs** | Frames at ≥ 30 Hz |
| **Configurable Parameters** | None (minimum enforced) |
| **Acceptance Criteria** | Measured frame generation rate ≥ 30 Hz |
| **Dependencies** | FEAT-CAM-001 |
| **Benchmark Relevance** | All stages |

### FEAT-CAM-005: Initial Camera Position

| Field | Value |
|---|---|
| **Feature ID** | FEAT-CAM-005 |
| **Feature Name** | Initial Camera Position |
| **Description** | Camera starts at the centre of the screen at simulation start. |
| **Source** | PS Row 6: "Centre of the Screen" |
| **Priority** | Must |
| **User Interaction** | None (fixed initial condition) |
| **Inputs** | Screen dimensions |
| **Outputs** | Camera positioned at (screen_width/2, screen_height/2) |
| **Configurable Parameters** | None |
| **Acceptance Criteria** | At frame 0, viewport is centered on the scene canvas |
| **Dependencies** | FEAT-ENV-001, FEAT-CAM-001 |
| **Benchmark Relevance** | Benchmark-1 (scenario execution) |

---

## 4.3 Beacon / Target Generator

### FEAT-TGT-001: Beacon Spot Generation

| Field | Value |
|---|---|
| **Feature ID** | FEAT-TGT-001 |
| **Feature Name** | Beacon Spot Generation |
| **Description** | Generate a beacon spot on the scene canvas with configurable size, shape, and position. |
| **Source** | PS Rows 7–11, L73 |
| **Priority** | Must (1 target), Could (multiple) |
| **User Interaction** | Configure target count (≥1), size, shape, initial position |
| **Inputs** | Count, size (W×H px), shape, initial position |
| **Outputs** | Beacon rendered on scene canvas |
| **Configurable Parameters** | Count (default 1), size (default 10×10, range 5–20), shape (default square), initial position (default random) |
| **Acceptance Criteria** | Beacon appears at configured size/shape/position on scene; minimum 1 beacon mandatory |
| **Dependencies** | FEAT-ENV-001 |
| **Benchmark Relevance** | All stages |

---

## 4.4 Target Motion Engine

### FEAT-MOT-001: Mandatory Motion Patterns

| Field | Value |
|---|---|
| **Feature ID** | FEAT-MOT-001 |
| **Feature Name** | Mandatory Motion Patterns |
| **Description** | Implement at least four selectable motion patterns for the beacon: straight line, circular, figure-of-8, random. |
| **Source** | PS Row 12: "Selectable, at least four: Straight Line, Circular, Figure of 8, Random" |
| **Priority** | Must |
| **User Interaction** | Select motion pattern from dropdown/menu |
| **Inputs** | Pattern selection, motion speed/parameters |
| **Outputs** | Per-frame beacon position updates |
| **Configurable Parameters** | Pattern type, speed (RECOMMENDATION — PS does not specify speed parameter but it is required to control motion) |
| **Acceptance Criteria** | Each pattern produces visually correct trajectory; beacon moves continuously within scene bounds |
| **Dependencies** | FEAT-TGT-001, FEAT-ENV-001 |
| **Benchmark Relevance** | Functional Verification, Benchmark-1 |

### FEAT-MOT-002: Optional Motion Patterns

| Field | Value |
|---|---|
| **Feature ID** | FEAT-MOT-002 |
| **Feature Name** | Optional Motion Patterns |
| **Description** | Additional motion patterns: spiral, sinusoidal, user-defined. |
| **Source** | PS Row 12: "Optional: Spiral, Sinusoidal, User-defined" |
| **Priority** | Should |
| **User Interaction** | Select optional pattern; user-defined may allow trajectory specification |
| **Inputs** | Pattern selection, parameters |
| **Outputs** | Per-frame beacon position updates |
| **Configurable Parameters** | Pattern type, pattern-specific parameters |
| **Acceptance Criteria** | Each implemented optional pattern produces correct trajectory |
| **Dependencies** | FEAT-MOT-001 |
| **Benchmark Relevance** | Functional Verification (demonstrates completeness), Technical Evaluation (innovation) |

---

## 4.5 Disturbance & Noise Engine

### FEAT-DST-001: Salt & Pepper Noise

| Field | Value |
|---|---|
| **Feature ID** | FEAT-DST-001 |
| **Feature Name** | Salt & Pepper Noise |
| **Description** | Apply salt-and-pepper noise to the camera frame. PS suggests approximately 10% of image. |
| **Source** | PS Row 21: "Salt & Pepper (around 10% of image)" |
| **Priority** | Must |
| **User Interaction** | Enable/disable; configure density |
| **Inputs** | Noise density (default ~10%) |
| **Outputs** | Noisy camera frame |
| **Configurable Parameters** | Noise density (% of pixels affected) |
| **Acceptance Criteria** | When enabled, approximately the configured percentage of pixels are set to minimum or maximum intensity |
| **Dependencies** | FEAT-CAM-001 |
| **Benchmark Relevance** | Functional Verification, Benchmark-1 |

### FEAT-DST-002: Gaussian Noise

| Field | Value |
|---|---|
| **Feature ID** | FEAT-DST-002 |
| **Feature Name** | Gaussian Noise |
| **Description** | Apply additive Gaussian noise to the camera frame. Max σ = 20 (unit ambiguous — see §5). |
| **Source** | PS Row 21 (type), Row 22 (max σ) |
| **Priority** | Must |
| **User Interaction** | Enable/disable; configure σ |
| **Inputs** | Standard deviation σ (max 20) |
| **Outputs** | Noisy camera frame |
| **Configurable Parameters** | σ (0 to 20) |
| **Acceptance Criteria** | When enabled, frame pixels have additive noise with configured σ |
| **Dependencies** | FEAT-CAM-001 |
| **Benchmark Relevance** | Functional Verification, Benchmark-1 |

### FEAT-DST-003: Poisson Noise

| Field | Value |
|---|---|
| **Feature ID** | FEAT-DST-003 |
| **Feature Name** | Poisson Noise |
| **Description** | Apply Poisson (shot) noise to the camera frame. Signal-dependent: variance equals signal intensity. |
| **Source** | PS Row 21 |
| **Priority** | Must |
| **User Interaction** | Enable/disable |
| **Inputs** | Camera frame (noise is signal-dependent) |
| **Outputs** | Noisy camera frame |
| **Configurable Parameters** | Enable/disable (Poisson noise has no separate σ parameter; PS provides none) |
| **Acceptance Criteria** | When enabled, pixel values exhibit shot-noise characteristics; brighter regions have proportionally more noise |
| **Dependencies** | FEAT-CAM-001 |
| **Benchmark Relevance** | Functional Verification, Benchmark-1 |

### FEAT-DST-004: Camera Jitter

| Field | Value |
|---|---|
| **Feature ID** | FEAT-DST-004 |
| **Feature Name** | Camera Jitter |
| **Description** | Apply random per-frame translational displacement to the camera viewport. Max ±20 pixels/frame. |
| **Source** | PS Row 23, L78 |
| **Priority** | Must |
| **User Interaction** | Enable/disable; configure amplitude |
| **Inputs** | Max jitter amplitude (pixels/frame) |
| **Outputs** | Camera viewport position offset |
| **Configurable Parameters** | Max amplitude (default unspecified, max ±20 px/frame) |
| **Acceptance Criteria** | When enabled, viewport position has random frame-to-frame offset within configured bounds |
| **Dependencies** | FEAT-CAM-001 |
| **Benchmark Relevance** | Functional Verification, Benchmark-1 |

### FEAT-DST-005: Atmospheric Disturbance Modes

| Field | Value |
|---|---|
| **Feature ID** | FEAT-DST-005 |
| **Feature Name** | Atmospheric Disturbance |
| **Description** | Five atmospheric modes: Clear, Haze, Fog, Rain, Low light. Each applies user-defined reduction in contrast and brightness to the camera frame. |
| **Source** | PS Row 24 |
| **Priority** | Must |
| **User Interaction** | Select mode; configure contrast/brightness reduction levels |
| **Inputs** | Mode selection, reduction parameters |
| **Outputs** | Modified camera frame with reduced contrast/brightness |
| **Configurable Parameters** | Atmospheric mode, contrast reduction factor, brightness reduction factor |
| **Acceptance Criteria** | Each mode visually reduces contrast and/or brightness of the camera frame; "clear" mode applies no degradation |
| **Dependencies** | FEAT-CAM-001 |
| **Benchmark Relevance** | Functional Verification, Benchmark-1 |

### FEAT-DST-006: Platform Motion

| Field | Value |
|---|---|
| **Feature ID** | FEAT-DST-006 |
| **Feature Name** | Platform Motion |
| **Description** | Simulate platform-level motion that shifts the camera position systematically. Linear pattern is mandatory; other patterns optional. Max ±20 pixels/frame. |
| **Source** | PS Row 25 |
| **Priority** | Must (linear), Could (other patterns) |
| **User Interaction** | Enable/disable; select pattern; configure amplitude |
| **Inputs** | Pattern type, max amplitude |
| **Outputs** | Camera position offset per frame |
| **Configurable Parameters** | Enable/disable, pattern (default: linear), amplitude (max ±20 px/frame) |
| **Acceptance Criteria** | Linear motion produces consistent directional drift; amplitude does not exceed configured maximum |
| **Dependencies** | FEAT-CAM-001 |
| **Benchmark Relevance** | Functional Verification, Benchmark-1 |

### FEAT-DST-007: Combined Disturbances

| Field | Value |
|---|---|
| **Feature ID** | FEAT-DST-007 |
| **Feature Name** | Combined Disturbance Stacking |
| **Description** | All disturbances must be combinable — user may enable one or more simultaneously. |
| **Source** | PS Row 21: "User Selectable (one or more)"; L78 lists multiple disturbance types together |
| **Priority** | Must |
| **User Interaction** | Toggle each disturbance independently |
| **Inputs** | Enable/disable state for each disturbance |
| **Outputs** | Frame with all enabled disturbances applied |
| **Configurable Parameters** | Per-disturbance enable/disable and parameters |
| **Acceptance Criteria** | Multiple disturbances can be active simultaneously without conflict |
| **Dependencies** | FEAT-DST-001 through FEAT-DST-006 |
| **Benchmark Relevance** | Benchmark-1 (evaluators will likely combine disturbances) |

---

## 4.6 Detection Engine

### FEAT-DET-001: Automatic Beacon Detection

| Field | Value |
|---|---|
| **Feature ID** | FEAT-DET-001 |
| **Feature Name** | Automatic Beacon Detection |
| **Description** | Autonomously detect the beacon spot within the camera frame without manual intervention. |
| **Source** | PS L29: "autonomously detects"; L75: "Detect the target beacon automatically" |
| **Priority** | Must |
| **User Interaction** | None during operation (fully autonomous) |
| **Inputs** | Camera frame (with disturbances applied) |
| **Outputs** | Detected beacon position (pixel coordinates) or no-detection flag |
| **Configurable Parameters** | None specified by PS (algorithm parameters are implementation-level) |
| **Acceptance Criteria** | Beacon is detected within the acquisition time threshold (≤ 2s) under all mandatory disturbance conditions |
| **Dependencies** | FEAT-CAM-001, FEAT-DST-* |
| **Benchmark Relevance** | All stages |

### FEAT-DET-002: Beacon Identification

| Field | Value |
|---|---|
| **Feature ID** | FEAT-DET-002 |
| **Feature Name** | Beacon Identification / Confirmation |
| **Description** | Confirm that a detected bright region is the actual beacon and not a noise artifact. |
| **Source** | PS L29: "identifies" |
| **Priority** | Must |
| **User Interaction** | None (autonomous) |
| **Inputs** | Detection candidate(s) |
| **Outputs** | Confirmed/rejected beacon identification |
| **Configurable Parameters** | None specified |
| **Acceptance Criteria** | False positives from noise do not cause persistent incorrect tracking |
| **Dependencies** | FEAT-DET-001 |
| **Benchmark Relevance** | Benchmark-1, Benchmark-2 |

---

## 4.7 Centroid Estimation

### FEAT-CEN-001: Centroid Computation

| Field | Value |
|---|---|
| **Feature ID** | FEAT-CEN-001 |
| **Feature Name** | Centroid Estimation |
| **Description** | Estimate the sub-pixel centroid position of the detected beacon within the camera frame. |
| **Source** | PS L22: "Estimate the position"; L112: "Log of Centroiding error"; L113: "Centroiding error" |
| **Priority** | Must |
| **User Interaction** | None |
| **Inputs** | Camera frame, detected beacon region |
| **Outputs** | Estimated centroid (x, y) in pixel coordinates |
| **Configurable Parameters** | None specified |
| **Acceptance Criteria** | Centroiding error (estimated centroid vs. true centroid) meets benchmark thresholds |
| **Dependencies** | FEAT-DET-001 |
| **Benchmark Relevance** | Benchmark-1, Benchmark-2 (primary metric) |

---

## 4.8 Tracking Engine

### FEAT-TRK-001: Continuous Tracking

| Field | Value |
|---|---|
| **Feature ID** | FEAT-TRK-001 |
| **Feature Name** | Continuous Beacon Tracking |
| **Description** | Continuously track the beacon across frames using computer vision. |
| **Source** | PS L76: "Track the beacon continuously using computer vision" |
| **Priority** | Must |
| **User Interaction** | None during operation |
| **Inputs** | Sequence of camera frames |
| **Outputs** | Per-frame beacon position estimate; tracking state (locked/lost) |
| **Configurable Parameters** | None specified |
| **Acceptance Criteria** | Tracking error ≤ 10 px; target loss < 5% |
| **Dependencies** | FEAT-DET-001, FEAT-CEN-001 |
| **Benchmark Relevance** | All stages |

---

## 4.9 Acquisition & Re-acquisition

### FEAT-ACQ-001: Initial Acquisition

| Field | Value |
|---|---|
| **Feature ID** | FEAT-ACQ-001 |
| **Feature Name** | Initial Target Acquisition |
| **Description** | When the simulation starts, the system must locate and lock onto the beacon within the performance threshold. |
| **Source** | PS Row 16: "Acquisition Time ≤ 2 sec"; L21: "Acquire and detect the remote terminal or beacon" |
| **Priority** | Must |
| **User Interaction** | None |
| **Inputs** | Camera frames from simulation start |
| **Outputs** | Transition from "searching" to "tracking" state; timestamp recorded |
| **Configurable Parameters** | None |
| **Acceptance Criteria** | Time from simulation start to first valid track ≤ 2 seconds |
| **Dependencies** | FEAT-DET-001, FEAT-TRK-001 |
| **Benchmark Relevance** | Benchmark-1, Benchmark-2 |

### FEAT-ACQ-002: Re-acquisition After Loss

| Field | Value |
|---|---|
| **Feature ID** | FEAT-ACQ-002 |
| **Feature Name** | Target Re-acquisition |
| **Description** | When the tracker loses the beacon, re-detect and re-lock within the performance threshold. |
| **Source** | PS Row 19: "Re-acquisition Time ≤ 1 sec" |
| **Priority** | Must |
| **User Interaction** | None |
| **Inputs** | Camera frames after target loss event |
| **Outputs** | Transition from "lost" to "tracking" state; timestamp recorded |
| **Configurable Parameters** | None |
| **Acceptance Criteria** | Time from loss detection to re-lock ≤ 1 second |
| **Dependencies** | FEAT-DET-001, FEAT-TRK-001 |
| **Benchmark Relevance** | Benchmark-1, Benchmark-2 |

---

## 4.10 PTZ Controller

### FEAT-PTZ-001: Pan-Tilt Control

| Field | Value |
|---|---|
| **Feature ID** | FEAT-PTZ-001 |
| **Feature Name** | Virtual Pan-Tilt Camera Control |
| **Description** | Control the virtual camera's pointing direction (pan and tilt) to keep the beacon near frame center, respecting speed constraints. |
| **Source** | PS L77, Rows 13–15 |
| **Priority** | Must |
| **User Interaction** | Configure max pan/tilt speeds |
| **Inputs** | Tracking error (beacon offset from center), max speed limits |
| **Outputs** | Camera position update commands |
| **Configurable Parameters** | Max pan speed (5–10 °/s, default 5), max tilt speed (5–10 °/s, default 5) |
| **Acceptance Criteria** | Camera moves toward beacon; speed never exceeds configured maximum; update rate ≥ 20 Hz |
| **Dependencies** | FEAT-TRK-001, FEAT-CAM-001 |
| **Benchmark Relevance** | All stages |

### FEAT-PTZ-002: PTZ Update Rate

| Field | Value |
|---|---|
| **Feature ID** | FEAT-PTZ-002 |
| **Feature Name** | PTZ Update Interval |
| **Description** | PTZ controller updates camera position at ≥ 20 Hz. |
| **Source** | PS Row 15: "≥ 20 Hz" |
| **Priority** | Must |
| **User Interaction** | None (system-enforced minimum) |
| **Inputs** | None |
| **Outputs** | Position updates at ≥ 20 Hz |
| **Configurable Parameters** | None |
| **Acceptance Criteria** | Measured PTZ update rate ≥ 20 Hz |
| **Dependencies** | FEAT-PTZ-001 |
| **Benchmark Relevance** | Benchmark-1 |

---

## 4.11 Simulation Engine

### FEAT-SIM-001: Simulation Loop

| Field | Value |
|---|---|
| **Feature ID** | FEAT-SIM-001 |
| **Feature Name** | Simulation Loop |
| **Description** | Core simulation loop that coordinates scene update (beacon motion), camera frame capture, disturbance application, detection/tracking, PTZ control, metrics computation, and visualization — all at the required rates. |
| **Source** | Implicit in all PS requirements; combines L72–79 |
| **Priority** | Must |
| **User Interaction** | Start/stop/pause simulation |
| **Inputs** | All configuration parameters |
| **Outputs** | Running simulation with real-time output |
| **Configurable Parameters** | All parameters defined in the specification table |
| **Acceptance Criteria** | Simulation runs stably; all subsystems execute at required rates |
| **Dependencies** | All FEAT-* |
| **Benchmark Relevance** | All stages |

---

## 4.12 External Video / MP4 Input

### FEAT-MP4-001: MP4 Video Ingestion

| Field | Value |
|---|---|
| **Feature ID** | FEAT-MP4-001 |
| **Feature Name** | MP4 Video File Input |
| **Description** | Accept external MP4 video files at 30 FPS as input. The software must bypass the PTZ camera/simulator and feed video frames directly to the detection/tracking pipeline. |
| **Source** | PS L113: "Each team will be given a few video files (.mp4) @30 fps... The software needs to bypass its PTZ camera and take this video as an input to the coarse pointing system." |
| **Priority** | Must |
| **User Interaction** | Load/browse MP4 file via GUI |
| **Inputs** | MP4 file path |
| **Outputs** | Frames fed to tracker; performance metrics computed |
| **Configurable Parameters** | File path |
| **Acceptance Criteria** | MP4 loads successfully; frames are processed by the tracker without PTZ; metrics are produced |
| **Dependencies** | FEAT-DET-001, FEAT-CEN-001, FEAT-TRK-001 |
| **Benchmark Relevance** | Benchmark-2 (30%) |

---

## 4.13 Benchmark Engine

### FEAT-BEN-001: Benchmark-1 Scenario Execution

| Field | Value |
|---|---|
| **Feature ID** | FEAT-BEN-001 |
| **Feature Name** | Evaluator Scenario Execution |
| **Description** | Accept and execute evaluator-defined simulation scenarios. The PS does not define the scenario format. The system should support easy parameter configuration (at minimum via GUI). |
| **Source** | PS L112: "Each team will be given few scenarios" |
| **Priority** | Must |
| **User Interaction** | Enter scenario parameters via GUI (and optionally via config file) |
| **Inputs** | Scenario parameters (to be defined by evaluators) |
| **Outputs** | Simulation run with centroiding error log and performance log |
| **Configurable Parameters** | All simulation parameters (to accommodate any scenario) |
| **Acceptance Criteria** | Any combination of PS-defined parameters can be configured and executed |
| **Dependencies** | FEAT-SIM-001, FEAT-LOG-001, FEAT-MET-001 |
| **Benchmark Relevance** | Benchmark-1 (30%) |

### FEAT-BEN-002: Benchmark-2 MP4 Processing

| Field | Value |
|---|---|
| **Feature ID** | FEAT-BEN-002 |
| **Feature Name** | MP4 Benchmark Processing |
| **Description** | Process evaluator-provided MP4 files and produce centroiding error log and performance metrics for comparison against evaluator ground truth. |
| **Source** | PS L113 |
| **Priority** | Must |
| **User Interaction** | Load MP4, run tracker, export results |
| **Inputs** | MP4 file |
| **Outputs** | Per-frame centroid estimates, centroiding error log (if ground truth provided), RMSE, acquisition time, re-acquisition time, lock retention rate, FPS |
| **Configurable Parameters** | File path |
| **Acceptance Criteria** | Tracker processes MP4 and produces all required metrics |
| **Dependencies** | FEAT-MP4-001, FEAT-MET-001, FEAT-LOG-001 |
| **Benchmark Relevance** | Benchmark-2 (30%) |

---

## 4.14 Performance Metrics

### FEAT-MET-001: Metrics Computation

| Field | Value |
|---|---|
| **Feature ID** | FEAT-MET-001 |
| **Feature Name** | Performance Metrics Engine |
| **Description** | Compute all required performance metrics: simulation duration, FPS, acquisition time, average and maximum tracking error, lock retention rate, processing time, centroiding error, RMSE. |
| **Source** | PS L103, L112, L113 |
| **Priority** | Must |
| **User Interaction** | Metrics displayed in real-time and exported in logs |
| **Inputs** | Per-frame tracking data, timing data, ground truth (when available) |
| **Outputs** | Computed metrics values |
| **Configurable Parameters** | None |
| **Acceptance Criteria** | All metrics listed in PS L103 and evaluation criteria (L112, L113) are correctly computed |
| **Dependencies** | FEAT-TRK-001, FEAT-CEN-001 |
| **Benchmark Relevance** | All stages |

---

## 4.15 Logging

### FEAT-LOG-001: Automatic Performance Log

| Field | Value |
|---|---|
| **Feature ID** | FEAT-LOG-001 |
| **Feature Name** | Automatic Performance Report Generation |
| **Description** | Automatically generate a performance report containing: simulation duration, FPS, acquisition time, average and maximum tracking error, lock retention rate, processing time. |
| **Source** | PS L103: "The software should be capable of automatically generating a performance report containing simulation duration, FPS, acquisition time, average and maximum tracking error, lock retention rate, processing time, etc." |
| **Priority** | Must |
| **User Interaction** | Auto-generated at end of simulation/benchmark run; optionally exportable |
| **Inputs** | Computed metrics from FEAT-MET-001 |
| **Outputs** | Performance report file |
| **Configurable Parameters** | Output file path (RECOMMENDATION) |
| **Acceptance Criteria** | Report is generated automatically; contains all prescribed metrics |
| **Dependencies** | FEAT-MET-001 |
| **Benchmark Relevance** | Benchmark-1 (explicitly evaluated), Benchmark-2 |

### FEAT-LOG-002: Centroiding Error Log

| Field | Value |
|---|---|
| **Feature ID** | FEAT-LOG-002 |
| **Feature Name** | Centroiding Error Log |
| **Description** | Log per-frame centroiding error for benchmark evaluation. |
| **Source** | PS L112: "Log of Centroiding error" |
| **Priority** | Must |
| **User Interaction** | Auto-generated during benchmark run |
| **Inputs** | Per-frame estimated centroid, ground truth centroid (from simulator or evaluator) |
| **Outputs** | Log file with per-frame centroiding error values |
| **Configurable Parameters** | Output format (RECOMMENDATION) |
| **Acceptance Criteria** | Per-frame centroiding error is logged and exportable |
| **Dependencies** | FEAT-CEN-001 |
| **Benchmark Relevance** | Benchmark-1 (30%), Benchmark-2 (30%) |

---

## 4.16 Real-Time Visualization

### FEAT-VIS-001: Tracking Visualization

| Field | Value |
|---|---|
| **Feature ID** | FEAT-VIS-001 |
| **Feature Name** | Real-Time Tracking Display |
| **Description** | Display the camera viewport with tracking overlays (detected position marker, tracking state indicator) and performance statistics in real-time. |
| **Source** | PS L79: "Display tracking performance and statistics in real-time" |
| **Priority** | Must |
| **User Interaction** | Observe during simulation |
| **Inputs** | Camera frame, tracking state, metrics |
| **Outputs** | Visual display with overlays and statistics |
| **Configurable Parameters** | None specified |
| **Acceptance Criteria** | Tracking overlay is visible; statistics update in real-time; display does not lag behind simulation |
| **Dependencies** | FEAT-TRK-001, FEAT-MET-001 |
| **Benchmark Relevance** | Functional Verification (20%) |

---

## 4.17 GUI

### FEAT-GUI-001: Application GUI

| Field | Value |
|---|---|
| **Feature ID** | FEAT-GUI-001 |
| **Feature Name** | Graphical User Interface |
| **Description** | Provide a GUI for parameter configuration, simulation control (start/stop), disturbance selection, MP4 file loading, and observation of tracking visualization and statistics. |
| **Source** | PS L111: evaluation criterion includes "GUI"; L99: user manual describes "GUI description" |
| **Priority** | Must |
| **User Interaction** | All primary user interactions go through the GUI |
| **Inputs** | User actions (configure, start, stop, load file) |
| **Outputs** | Configured simulation, visual feedback |
| **Configurable Parameters** | All user-configurable parameters exposed in the GUI |
| **Acceptance Criteria** | All mandatory parameters can be configured through the GUI; simulation can be started/stopped; MP4 can be loaded; evaluators can operate it within 10–15 minutes |
| **Dependencies** | All FEAT-* |
| **Benchmark Relevance** | Functional Verification (20%) — GUI is a scored criterion |

---

## 4.18 Scenario Management

### FEAT-SCN-001: Scenario Configuration

| Field | Value |
|---|---|
| **Feature ID** | FEAT-SCN-001 |
| **Feature Name** | Scenario Configuration |
| **Description** | Allow users to configure complete simulation scenarios — all parameters for scene, target, camera, disturbances, and motion — through the GUI. Optionally support file-based loading. |
| **Source** | PS L112 (benchmark-1 implies scenario input); PS Rows 1–25 (configurable parameters) |
| **Priority** | Must (GUI config), Should (file-based loading) |
| **User Interaction** | Configure all parameters via GUI; optionally load from file |
| **Inputs** | Parameter values |
| **Outputs** | Configured simulation ready to run |
| **Configurable Parameters** | All PS-defined parameters |
| **Acceptance Criteria** | Any valid combination of PS parameters can be entered and the simulation runs |
| **Dependencies** | FEAT-GUI-001, FEAT-SIM-001 |
| **Benchmark Relevance** | Benchmark-1 (30%) |

---

## 4.19 Experiment Management

### FEAT-EXP-001: Scenario Save/Load

| Field | Value |
|---|---|
| **Feature ID** | FEAT-EXP-001 |
| **Feature Name** | Scenario Save and Load |
| **Description** | Save configured scenarios to file and reload them later. Supports reproducibility and quick benchmark setup. |
| **Source** | RECOMMENDATION — not PS-required but strongly supports Benchmark-1 efficiency |
| **Priority** | Should |
| **User Interaction** | Save/load buttons in GUI |
| **Inputs** | Scenario parameter set |
| **Outputs** | Saved scenario file; loaded scenario configuration |
| **Configurable Parameters** | File path |
| **Acceptance Criteria** | Saved scenario can be reloaded and produces same simulation configuration |
| **Dependencies** | FEAT-SCN-001 |
| **Benchmark Relevance** | Benchmark-1 |

---

## 4.20 AI / ML Capabilities

### FEAT-AI-001: AI/CV-Assisted Detection and Tracking

| Field | Value |
|---|---|
| **Feature ID** | FEAT-AI-001 |
| **Feature Name** | AI/Computer Vision Integration |
| **Description** | The system must use AI and/or computer vision techniques for beacon detection and tracking. The PS title specifies "AI-Based" and the evaluation explicitly scores "AI and computer vision." |
| **Source** | PS Title (L5): "AI-Based"; PS L68: "AI-assisted camera tracking system"; PS L76: "using computer vision"; PS L114: evaluation includes "AI and computer vision" |
| **Priority** | Must (CV), Should (ML/AI — PS L95 says "AI methods (if used)" suggesting it is scored but not strictly mandatory in implementation) |
| **User Interaction** | None during operation |
| **Inputs** | Camera frames |
| **Outputs** | Detection/tracking decisions influenced by AI/CV |
| **Configurable Parameters** | None specified |
| **Acceptance Criteria** | The system demonstrably uses computer vision for tracking; AI/ML component can be explained and defended during technical evaluation |
| **Dependencies** | FEAT-DET-001, FEAT-TRK-001 |
| **Benchmark Relevance** | Technical Evaluation (20%) — explicitly scored |

> [!NOTE]
> **Nuance on "AI"**: PS L95 says "AI methods (if used)" in the technical report requirements. PS L68 says "AI-assisted." PS title says "AI-Based." The evaluation scores "AI and computer vision" together. The system **must** use computer vision. The inclusion of genuine AI/ML is **strongly encouraged** by the evaluation criteria but the PS itself treats AI as "if used" in the report. Our position: use AI/ML genuinely where it adds value, and be prepared to defend the choice.

---

## 4.21 Export / Reporting

### FEAT-EXP-002: Centroid Export

| Field | Value |
|---|---|
| **Feature ID** | FEAT-EXP-002 |
| **Feature Name** | Per-Frame Centroid Export |
| **Description** | Export per-frame estimated centroid positions in a standard format for external comparison with evaluator ground truth. |
| **Source** | PS L113: "Comparison of Centroiding error with predefined error values" — implies centroid output must be comparable to external values |
| **Priority** | Must |
| **User Interaction** | Auto-generated or export button |
| **Inputs** | Per-frame centroid data |
| **Outputs** | File with per-frame (frame_number, x, y) data |
| **Configurable Parameters** | Output format (RECOMMENDATION: CSV) |
| **Acceptance Criteria** | File is generated; contains per-frame centroid data; format is documented |
| **Dependencies** | FEAT-CEN-001 |
| **Benchmark Relevance** | Benchmark-2 (30%) |

---

## 4.22 Application Packaging

### FEAT-PKG-001: Standalone Executable

| Field | Value |
|---|---|
| **Feature ID** | FEAT-PKG-001 |
| **Feature Name** | Standalone Executable Application |
| **Description** | Package the application as a standalone executable that runs without requiring a development environment. |
| **Source** | PS L87: "A standalone executable application" |
| **Priority** | Must |
| **User Interaction** | Double-click to launch |
| **Inputs** | None |
| **Outputs** | Running application |
| **Configurable Parameters** | None |
| **Acceptance Criteria** | Application launches on a clean machine without IDE/interpreter installation (assuming standard OS and runtimes) |
| **Dependencies** | All FEAT-* |
| **Benchmark Relevance** | Functional Verification (20%) |

---

# PART 5 — Numerical & Physical Specifications

| # | Parameter | PS Value | Unit | Nature | Product Req ID | Acceptance Test |
|---|---|---|---|---|---|---|
| 1 | Screen Size | ≥ 2000 × 2000 | pixels | Minimum; optionally user-defined | FEAT-ENV-001 | Verify scene dimensions ≥ 2000×2000 |
| 2 | Camera Type | Monochrome (FPA) | — | Mandatory; colour optional | FEAT-CAM-002 | Output frame is single-channel |
| 3 | Camera Resolution | 640 × 480 | pixels | Default; optionally user-defined | FEAT-CAM-001 | Viewport produces 640×480 frames |
| 4 | Camera FOV | User-defined, default 4° × 3° | degrees | Default, user-configurable | FEAT-CAM-003 | FOV changes alter viewport coverage correctly |
| 5 | Camera Update Rate | ≥ 30 | Hz | Minimum | FEAT-CAM-004 | Measure frame generation rate ≥ 30 Hz |
| 6 | Initial Camera Position | Centre of screen | — | Fixed | FEAT-CAM-005 | Viewport centered at frame 0 |
| 7 | Target Type | Beacon spot | — | Fixed | FEAT-TGT-001 | Beacon renders as bright spot |
| 8 | Number of Targets | 1 (mandatory) | — | Mandatory; multiple optional | FEAT-TGT-001 | At least 1 beacon present |
| 9 | Target Shape | User-defined, default square | — | Default, configurable | FEAT-TGT-001 | Default beacon is square |
| 10 | Target Size | 5–20 × 5–20, default 10×10 | pixels | Range; user-defined | FEAT-TGT-001 | Beacon renders at configured size |
| 11 | Initial Target Location | User-defined, default random | — | Default random; configurable | FEAT-TGT-001 | Target starts at configured or random position |
| 12 | Motion Patterns | ≥ 4: Straight, Circular, Fig-8, Random | — | Mandatory (4); optional (spiral, sinusoidal, user-defined) | FEAT-MOT-001 | Each pattern produces correct trajectory |
| 13 | Max Pan Speed | 5–10, default 5 | °/s | Range; user-defined | FEAT-PTZ-001 | Camera pan speed never exceeds configured max |
| 14 | Max Tilt Speed | 5–10, default 5 | °/s | Range; user-defined | FEAT-PTZ-001 | Camera tilt speed never exceeds configured max |
| 15 | PTZ Update Interval | ≥ 20 | Hz | Minimum | FEAT-PTZ-002 | PTZ updates at ≥ 20 Hz |
| 16 | Acquisition Time | ≤ 2 | seconds | Maximum | FEAT-ACQ-001 | Measured acquisition time ≤ 2s |
| 17 | Tracking Error | ≤ 10 | pixels | Maximum | FEAT-TRK-001 | Measured tracking error ≤ 10 px |
| 18 | Target Loss | < 5 | % | Maximum | FEAT-TRK-001 | Lost frames / total frames < 5% |
| 19 | Re-acquisition Time | ≤ 1 | seconds | Maximum | FEAT-ACQ-002 | Re-lock time ≤ 1s after each loss |
| 20 | Processing Speed | ≥ 20 | FPS | Minimum | NFR-PERF-001 | End-to-end processing FPS ≥ 20 |
| 21 | S&P Noise Density | ~10% of image | % of pixels | Suggested default | FEAT-DST-001 | ~10% pixels corrupted when enabled at default |
| 22 | Max Noise σ | 20 | **AMBIGUOUS: "pixels" in PS** | Maximum; user-defined | FEAT-DST-002 | Noise σ configurable up to 20 |
| 23 | Max Camera Jitter | ±20 | pixels/frame | Maximum; user-defined | FEAT-DST-004 | Jitter amplitude ≤ configured max |
| 24 | Atmospheric Modes | Clear, Haze, Fog, Rain, Low light | — | 5 modes; user-defined reduction | FEAT-DST-005 | Each mode applies contrast/brightness changes |
| 25 | Max Platform Motion | ±20 | pixels/frame | Maximum; user-selectable | FEAT-DST-006 | Amplitude ≤ configured max |

---

# PART 6 — Functional Requirements

> All requirements are PS-sourced unless otherwise noted. Each requirement is atomic, testable, and implementation-neutral.

**FR-001 — Virtual Environment Generation**
The system shall generate a 2D virtual environment (scene canvas) of at least 2000×2000 pixels, with the size optionally configurable by the user.

**FR-002 — Beacon Spot Generation**
The system shall generate at least one beacon spot (target) on the scene canvas with configurable size (5–20 × 5–20 pixels, default 10×10), shape (default square), and initial position (default random).

**FR-003 — Multiple Target Support**
The system shall optionally support generation and display of multiple beacon targets simultaneously.

**FR-004 — Camera Viewport**
The system shall implement a virtual camera that extracts a viewport of configurable resolution (default 640×480) from the scene canvas, based on the camera's current pan/tilt position and FOV (default 4°×3°).

**FR-005 — Camera Type**
The system shall operate the virtual camera in monochrome mode by default, with optional colour mode.

**FR-006 — Camera Frame Rate**
The system shall generate camera frames at a minimum rate of 30 Hz.

**FR-007 — Camera Initial Position**
The system shall initialize the virtual camera at the centre of the scene canvas at the start of each simulation.

**FR-008 — Beacon Motion**
The system shall support at least four selectable beacon motion patterns: straight line, circular, figure-of-8, and random.

**FR-009 — Optional Motion Patterns**
The system shall optionally support additional motion patterns including spiral, sinusoidal, and user-defined trajectories.

**FR-010 — Salt & Pepper Noise**
The system shall be able to apply salt-and-pepper noise to the camera feed, with user-configurable density (PS suggests approximately 10%).

**FR-011 — Gaussian Noise**
The system shall be able to apply Gaussian noise to the camera feed, with user-configurable standard deviation (maximum 20, unit as per PS).

**FR-012 — Poisson Noise**
The system shall be able to apply Poisson (shot) noise to the camera feed.

**FR-013 — Noise Selection**
The system shall allow the user to select and enable one or more noise types simultaneously.

**FR-014 — Camera Jitter**
The system shall be able to apply random per-frame camera jitter to the viewport position, with user-configurable maximum amplitude (up to ±20 pixels/frame).

**FR-015 — Atmospheric Disturbance**
The system shall support five atmospheric disturbance modes: Clear, Haze, Fog, Rain, and Low light, each applying user-defined reduction in contrast and brightness to the camera feed.

**FR-016 — Platform Motion**
The system shall simulate platform motion affecting the camera position, with at least a mandatory linear pattern. Maximum amplitude is ±20 pixels/frame, user-selectable.

**FR-017 — Optional Platform Motion Patterns**
The system shall optionally support additional platform motion patterns: circular, random, spiral, figure-of-8.

**FR-018 — Combined Disturbances**
The system shall allow the user to enable one or more disturbances simultaneously (noise, jitter, atmospheric, platform motion).

**FR-019 — Automatic Beacon Detection**
The system shall autonomously detect the beacon spot within the camera viewport without manual intervention.

**FR-020 — Beacon Identification**
The system shall identify detected bright regions as the actual beacon versus noise artifacts.

**FR-021 — Centroid Estimation**
The system shall estimate the centroid position of the detected beacon within the camera frame.

**FR-022 — Continuous Tracking**
The system shall continuously track the beacon across frames using computer vision techniques.

**FR-023 — Pan-Tilt Camera Control**
The system shall control the virtual camera's pan and tilt to reposition it toward the beacon, with user-configurable maximum speeds (pan: 5–10°/s, default 5; tilt: 5–10°/s, default 5).

**FR-024 — PTZ Speed Enforcement**
The system shall enforce the configured maximum pan and tilt speeds — the camera shall not move faster than the configured limits.

**FR-025 — PTZ Update Rate**
The system shall update the PTZ camera position at a minimum rate of 20 Hz.

**FR-026 — Real-Time Statistics Display**
The system shall display tracking performance and statistics in real-time during simulation.

**FR-027 — Automatic Performance Log**
The system shall automatically generate a performance report containing: simulation duration, FPS, acquisition time, average and maximum tracking error, lock retention rate, and processing time.

**FR-028 — Centroiding Error Log**
The system shall log centroiding error data during benchmark runs.

**FR-029 — MP4 Video Input**
The system shall accept external MP4 video files (at 30 FPS) as input, bypassing the virtual PTZ camera and feeding frames directly to the coarse pointing (detection/tracking) pipeline.

**FR-030 — Standalone Executable**
The application shall be packaged as a standalone executable.

**FR-031 — GUI**
The system shall provide a graphical user interface for parameter configuration, simulation control, MP4 file loading, and observation of tracking and statistics.

**FR-032 — Computer Vision Usage**
The system shall use computer vision techniques for beacon tracking, as specified by the PS.

---

# PART 7 — Non-Functional Requirements

## Performance — PS-Required

**NFR-PERF-001**: The system shall process frames at a minimum rate of 20 FPS (end-to-end tracking pipeline).
*Source: PS Row 20*

**NFR-PERF-002**: The system shall achieve initial target acquisition within 2 seconds.
*Source: PS Row 16*

**NFR-PERF-003**: The system shall maintain tracking error ≤ 10 pixels.
*Source: PS Row 17*

**NFR-PERF-004**: The system shall maintain target loss rate below 5%.
*Source: PS Row 18*

**NFR-PERF-005**: The system shall re-acquire the target within 1 second after loss.
*Source: PS Row 19*

## Accuracy — Evaluation-Driven

**NFR-ACC-001**: The system shall compute centroiding error accurately enough to compare favorably with evaluator ground truth values.
*Source: PS L113 — "Comparison of Centroiding error with predefined error values"*

**NFR-ACC-002**: The system shall compute RMSE of centroiding error.
*Source: PS L113*

## Real-Time Behaviour — PS-Required

**NFR-RT-001**: Statistics and tracking overlays shall update in real-time during simulation (no perceptible lag).
*Source: PS L79*

## Reliability — Engineering Recommendation

**NFR-REL-001** *(RECOMMENDATION)*: The system shall not crash during a 10–15 minute demonstration session under any user-configurable parameter combination.

**NFR-REL-002** *(RECOMMENDATION)*: The system shall handle invalid or edge-case MP4 files gracefully (e.g., wrong codec, unexpected resolution) with an error message rather than a crash.

## Robustness — Evaluation-Driven

**NFR-ROB-001**: The system shall maintain detection and tracking performance under all mandatory disturbance types (noise, jitter, atmospheric, platform motion) individually and in combination.
*Source: PS Rows 21–25, L78; implied by benchmark evaluation*

## Usability — Evaluation-Driven

**NFR-USE-001**: The GUI shall be operable by evaluators within a 10–15 minute session for demonstration and scenario configuration.
*Source: PS L111*

**NFR-USE-002**: The user manual shall describe installation, operation, parameter configuration, and GUI usage.
*Source: PS L98–99*

## Portability — Engineering Recommendation

**NFR-PORT-001** *(RECOMMENDATION)*: The standalone executable should run on Windows (most common evaluation platform for SIH). The PS does not specify the OS.

## Standalone Execution — PS-Required

**NFR-STAND-001**: The application shall run as a standalone executable without requiring an IDE, compiler, or interpreter.
*Source: PS L87*

## Reproducibility — Engineering Recommendation

**NFR-REPRO-001** *(RECOMMENDATION)*: The system should support deterministic scenario execution when using the same parameters and random seed. This is not PS-required but supports fair benchmarking.

## Logging — PS-Required

**NFR-LOG-001**: The system shall automatically generate performance logs without manual user intervention.
*Source: PS L103*

## Maintainability / Code Quality — PS-Required

**NFR-CODE-001**: The source code shall be modular and adequately commented.
*Source: PS L91: "The code shall be modular and adequately commented"*

## Documentation — PS-Required

**NFR-DOC-001**: A technical report (10–15 pages) shall be produced covering: problem understanding, system architecture, software modules, tracking methods, AI methods (if used), test methodology, performance analysis, and future improvements.
*Source: PS L95*

**NFR-DOC-002**: A user manual shall be produced covering: installation, operation, parameter configuration, and GUI description.
*Source: PS L98–99*

---

# PART 8 — Benchmark Requirements

## 8.1 Benchmark Performance-1 (30%)

### What the PS states
> *"Each team will be given few scenarios."* (L112)
> Evaluation: (1) Execution of the scenario, (2) Log of Centroiding error, (3) Automatically generated performance logs.

### Requirements

**BM1-001**: The system shall be able to configure and execute simulation scenarios defined by the evaluators.

**BM1-002**: The system shall produce a log of centroiding error during scenario execution.

**BM1-003**: The system shall automatically generate performance logs (duration, FPS, acquisition time, avg/max tracking error, lock retention rate, processing time) during scenario execution.

**BM1-004**: The system's GUI shall allow evaluators to configure all mandatory simulation parameters quickly enough to execute "few scenarios" within the evaluation time window.

**BM1-005** *(RECOMMENDATION)*: The system should support loading scenario configurations from a file format to accelerate benchmark setup.

**BM1-006** *(RECOMMENDATION)*: The system should handle edge-case scenario parameters (e.g., minimum target size, maximum noise) without crashing.

### Key Risks
- Unknown scenario parameters; evaluators may push to extremes
- Centroiding error format may differ from evaluator expectations
- Slow GUI configuration could waste evaluation time

---

## 8.2 Benchmark Performance-2 (30%)

### What the PS states
> *"Each team will be given a few video files (.mp4) @30 fps, covering a complete screen with noise and moving beacon spot. The software needs to bypass its PTZ camera and take this video as an input to the coarse pointing system."* (L113)
> Evaluation: (1) Comparison of Centroiding error with predefined error values, (2) Performance w.r.t. various parameters like RMSE, acquisition and re-acquisition time, Lock retention rate, FPS, etc.

### Requirements

**BM2-001**: The system shall accept MP4 video files at 30 FPS as input.

**BM2-002**: When processing MP4 input, the system shall bypass the virtual PTZ camera and simulator, feeding video frames directly to the detection/tracking pipeline.

**BM2-003**: The system shall produce per-frame centroid estimates when processing MP4 input.

**BM2-004**: The system shall compute and log: centroiding error (if ground truth is available), RMSE, acquisition time, re-acquisition time, lock retention rate, and FPS during MP4 processing.

**BM2-005**: The system shall export centroid estimates in a format suitable for external comparison with evaluator ground truth.

> [!WARNING]
> **PRESERVED AMBIGUITY**: The PS says MP4 videos are "covering a complete screen with noise and moving beacon spot." This could mean:
> - (A) The MP4 shows the full simulation screen (e.g., 2000×2000 or similar large resolution) — the tracker must detect the beacon anywhere in the frame.
> - (B) The MP4 is a full-frame video at some resolution with the beacon always visible — the tracker must centroid the beacon.
> - (C) The MP4 represents a complete test covering the full screen over time — i.e., the beacon traverses the entire screen during the video.
>
> **We do not resolve this ambiguity.** The tracker must handle arbitrary input resolutions and beacon positions.

**BM2-006**: The system shall handle MP4 files of arbitrary resolution and characteristics without crashing.

**BM2-007**: Since the PTZ is bypassed in benchmark-2, the tracker shall operate without issuing or depending on PTZ commands during MP4 processing.

### Key Risks
- Unknown MP4 resolution, codec, noise characteristics
- Beacon appearance may differ from simulator-generated beacons
- No ground truth provided to the system — evaluators compare externally
- Centroid format mismatch with evaluator expectations

---

# PART 9 — Measurement & Metrics Specification

| # | Metric | Definition | Required Data | Frequency | Aggregation | PS-Required | Ambiguous |
|---|---|---|---|---|---|---|---|
| 1 | **Centroiding Error** | **PROPOSED DEFINITION**: Euclidean distance between estimated beacon centroid and true beacon centroid. `CE = √((x_est - x_true)² + (y_est - y_true)²)` | Estimated centroid, true centroid | Per-frame | Mean, Max, RMSE | Yes (L112, L113) | Yes — PS does not define precisely |
| 2 | **Tracking Error** | **PROPOSED DEFINITION**: Euclidean distance between estimated beacon centroid and the center of the camera viewport. `TE = √((x_est - x_center)² + (y_est - y_center)²)` | Estimated centroid, viewport center | Per-frame | Mean, Max | Yes (Row 17: "≤ 10 pixels") | Yes — PS does not define precisely |
| 3 | **X Error** | Horizontal component of centroiding or tracking error. `ΔX = x_est - x_ref` | Same as parent metric | Per-frame | Mean, Max | No (not explicitly) | — |
| 4 | **Y Error** | Vertical component of centroiding or tracking error. `ΔY = y_est - y_ref` | Same as parent metric | Per-frame | Mean, Max | No (not explicitly) | — |
| 5 | **RMSE** | Root Mean Square Error of centroiding error over all frames. `RMSE = √(Σ CE²/N)` | All per-frame centroiding errors | End of run | Single value | Yes (L113) | No |
| 6 | **Acquisition Time** | Time from simulation start (or first frame of MP4) to the first frame where the tracker reports a valid lock on the beacon. | Frame timestamps, tracker state transitions | Per-acquisition event | Single value (first acquisition) | Yes (Row 16: "≤ 2 sec") | Partially — "valid lock" not defined |
| 7 | **Re-acquisition Time** | Time from the frame where the tracker reports target loss to the frame where it reports re-lock. | Frame timestamps, tracker state transitions | Per-loss-event | Mean, Max | Yes (Row 19: "≤ 1 sec") | Partially — "loss" not defined |
| 8 | **Target Loss Rate** | Percentage of frames where the beacon is not being tracked (tracker is in "lost" state). `TLR = (lost_frames / total_frames) × 100` | Per-frame tracker state | End of run | Single value (%) | Yes (Row 18: "< 5%") | Partially — "not being tracked" not defined |
| 9 | **Lock Retention Rate** | Complement of target loss rate. `LRR = 100 - TLR` or percentage of frames where beacon is successfully tracked. | Per-frame tracker state | End of run | Single value (%) | Yes (L103, L113) | No — inverse of target loss |
| 10 | **FPS (Processing Speed)** | Frames processed per second by the tracking pipeline. `FPS = total_frames / total_processing_time` | Frame count, wall-clock processing time | End of run; also real-time | Mean, instantaneous | Yes (Row 20: "≥ 20 FPS"; L103; L113) | No |
| 11 | **Processing Time** | Total wall-clock time for a simulation/benchmark run. | Wall-clock start/end timestamps | End of run | Single value | Yes (L103) | No |
| 12 | **Simulation Duration** | Duration of the simulated scenario (which may differ from processing time if system runs faster/slower than real-time). | Simulation clock | End of run | Single value | Yes (L103) | Partially — difference from processing time unclear |

---

# PART 10 — Configuration Requirements

## PS-Required Configuration

### Camera Configuration
| Parameter | Range | Default | PS Source |
|---|---|---|---|
| Camera resolution | User-defined | 640×480 | Row 3 |
| Camera FOV (H×V) | User-defined | 4°×3° | Row 4 |
| Camera type (mono/colour) | Mono or Colour | Monochrome | Row 2 |

### Target Configuration
| Parameter | Range | Default | PS Source |
|---|---|---|---|
| Number of targets | ≥ 1 | 1 | Row 8 |
| Target size (W×H) | 5–20 × 5–20 px | 10×10 | Row 10 |
| Target shape | User-defined | Square | Row 9 |
| Initial target position | User-defined | Random | Row 11 |
| Motion pattern | ≥ 4 selectable | — | Row 12 |

### PTZ / Camera Motion Configuration
| Parameter | Range | Default | PS Source |
|---|---|---|---|
| Max pan speed | 5–10 °/s | 5 °/s | Row 13 |
| Max tilt speed | 5–10 °/s | 5 °/s | Row 14 |

### Noise Configuration
| Parameter | Range | Default | PS Source |
|---|---|---|---|
| S&P noise enable | On/Off | — | Row 21 |
| S&P noise density | User-defined | ~10% | Row 21 |
| Gaussian noise enable | On/Off | — | Row 21 |
| Gaussian noise σ | 0–20 | — | Row 22 |
| Poisson noise enable | On/Off | — | Row 21 |

### Atmospheric Configuration
| Parameter | Options | Default | PS Source |
|---|---|---|---|
| Atmospheric mode | Clear, Haze, Fog, Rain, Low light | — | Row 24 |
| Contrast reduction | User-defined | — | Row 24 |
| Brightness reduction | User-defined | — | Row 24 |

### Platform Motion Configuration
| Parameter | Range | Default | PS Source |
|---|---|---|---|
| Platform motion enable | On/Off | — | Row 25 |
| Platform motion pattern | Linear (mandatory) + optional | Linear | Row 25 |
| Platform motion amplitude | 0 to ±20 px/frame | — | Row 25 |

### Jitter Configuration
| Parameter | Range | Default | PS Source |
|---|---|---|---|
| Camera jitter enable | On/Off | — | Row 23 |
| Camera jitter amplitude | 0 to ±20 px/frame | — | Row 23 |

## Recommended Configuration (Not PS-Required)

| Parameter | Rationale |
|---|---|
| Screen size (≥ 2000×2000) | PS Row 1 says "Optional: User-defined"; useful for experimentation |
| Background intensity | Needed for contrast control; PS-implicit |
| Beacon intensity | PS does not specify but contrast depends on it |
| Target speed | PS does not specify but essential for meaningful motion |
| Random seed | For reproducibility |
| Simulation duration | PS does not specify run length |

## Optional Configuration

| Parameter | Rationale |
|---|---|
| Additional motion patterns | PS Row 12 optional |
| Additional platform patterns | PS Row 25 optional |
| Colour mode parameters | PS Row 2 optional |

---

# PART 11 — Input / Output Contract

## Simulation Input (Simulator Configuration)

| Input | Type | Source |
|---|---|---|
| Screen dimensions | Integer pair | User/config |
| Camera parameters (resolution, FOV, type) | Structured config | User/config |
| Target parameters (count, size, shape, position, motion, speed) | Structured config | User/config |
| PTZ parameters (max pan/tilt speed) | Numeric | User/config |
| Disturbance parameters (noise types/params, jitter, atmosphere, platform) | Structured config | User/config |
| Simulation duration / stop condition | Numeric / event | User/config |

## Tracker Input

| Input | Type | Source |
|---|---|---|
| Camera frame (image) | 2D array (monochrome or colour) | Virtual camera OR MP4 file |
| Frame timestamp | Numeric | Simulation clock OR video timestamp |

> The tracker must **not** receive ground truth, scene canvas, or beacon position directly.

## Tracker Output

| Output | Type | Consumer |
|---|---|---|
| Detected beacon position (estimated centroid) | (x, y) pixel coordinates | PTZ controller, metrics engine, logger |
| Tracking state | Enum: SEARCHING, TRACKING, LOST | PTZ controller, metrics engine, logger |
| Detection confidence | Numeric (RECOMMENDATION) | Logger |

## PTZ Controller Output

| Output | Type | Consumer |
|---|---|---|
| Camera position update (pan, tilt) | Angular or pixel offset | Camera model |

## Benchmark-1 Input

| Input | Type | Source |
|---|---|---|
| Scenario parameters | Parameter set (format unknown) | Evaluators |

## MP4 / Benchmark-2 Input

| Input | Type | Source |
|---|---|---|
| MP4 video file | .mp4 file at 30 FPS | Evaluators |

## Performance Output

| Output | Type | Consumer |
|---|---|---|
| Performance report | File (auto-generated) | Evaluators, user |
| Centroiding error log | File (per-frame data) | Evaluators |
| Per-frame centroid export | File (frame, x, y) | Evaluators (for external comparison) |
| Real-time statistics | GUI display | User, evaluators |

---

# PART 12 — Ground Truth & Evaluation Integrity

## What Ground Truth Exists

| Context | Ground Truth Available | Source |
|---|---|---|
| **Simulation mode** | Yes — the simulator knows the exact beacon position at every frame because it generates the scene | Internal to simulator |
| **MP4 mode** | No — ground truth is held by evaluators, not by our system | PS L113: "predefined error values" are evaluator-side |

## Access Rules

| Component | Allowed Access to Ground Truth | Rationale |
|---|---|---|
| **Tracker (detection/tracking engine)** | **NO** | The tracker must operate purely from camera frame imagery. Feeding ground truth to the tracker would invalidate all benchmarks. |
| **Metrics engine** | **YES (simulation mode)** | Needs ground truth to compute centroiding error, tracking error |
| **Performance logger** | **YES (via metrics engine)** | Logs computed metrics |
| **PTZ controller** | **NO** | Must respond only to tracker output |

> [!IMPORTANT]
> **ENGINEERING RECOMMENDATION**: Ground truth must be architecturally isolated from the tracker. In simulation mode, ground truth flows from the scene generator to the metrics engine but never enters the detection/tracking pipeline. This prevents accidental cheating and ensures benchmark integrity.

## Export Requirements

In **MP4 mode**, there is no internal ground truth. The system must export per-frame centroid estimates so evaluators can compare externally. The export format should be documented in the user manual.

---

# PART 13 — Acceptance Criteria

## Product-Level Definition of Done

The application is considered functionally complete when ALL of the following are verified:

### Functional Requirements Pass

| Test | Criterion |
|---|---|
| AC-FR-01 | Scene canvas renders at ≥ 2000×2000 pixels |
| AC-FR-02 | Beacon spot appears with configurable size (tested at 5×5, 10×10, 20×20) |
| AC-FR-03 | All 4 mandatory motion patterns produce correct trajectories |
| AC-FR-04 | Camera viewport correctly extracts 640×480 from scene |
| AC-FR-05 | Camera starts at centre of screen |
| AC-FR-06 | Each noise type (S&P, Gaussian, Poisson) visually alters the frame |
| AC-FR-07 | All 5 atmospheric modes produce visible contrast/brightness changes |
| AC-FR-08 | Camera jitter produces visible frame-to-frame displacement |
| AC-FR-09 | Platform motion (linear) produces visible systematic drift |
| AC-FR-10 | Multiple disturbances can be combined simultaneously |
| AC-FR-11 | Beacon is detected automatically (no manual click/input) |
| AC-FR-12 | Tracking maintains lock across frames |
| AC-FR-13 | PTZ camera moves toward beacon and respects speed limits |
| AC-FR-14 | Real-time statistics are displayed during simulation |
| AC-FR-15 | MP4 file loads and tracker processes it without PTZ |
| AC-FR-16 | Performance report is auto-generated with all prescribed metrics |
| AC-FR-17 | Centroiding error log is produced |
| AC-FR-18 | GUI allows configuration of all mandatory parameters |
| AC-FR-19 | Application runs as standalone executable |

### Performance Requirements Pass

| Test | Criterion | Threshold |
|---|---|---|
| AC-PR-01 | Acquisition time | ≤ 2 seconds (default parameters) |
| AC-PR-02 | Tracking error | ≤ 10 pixels (default parameters) |
| AC-PR-03 | Target loss rate | < 5% (default parameters) |
| AC-PR-04 | Re-acquisition time | ≤ 1 second (default parameters) |
| AC-PR-05 | Processing speed | ≥ 20 FPS |
| AC-PR-06 | Camera frame rate | ≥ 30 Hz |
| AC-PR-07 | PTZ update rate | ≥ 20 Hz |

### Benchmark-1 Requirements Pass

| Test | Criterion |
|---|---|
| AC-BM1-01 | Can configure and run a scenario with evaluator-specified parameters |
| AC-BM1-02 | Centroiding error log is produced during scenario |
| AC-BM1-03 | Performance log is auto-generated with all metrics |

### Benchmark-2 Requirements Pass

| Test | Criterion |
|---|---|
| AC-BM2-01 | MP4 file loads successfully |
| AC-BM2-02 | Tracker processes MP4 without PTZ involvement |
| AC-BM2-03 | Per-frame centroid estimates are produced and exportable |
| AC-BM2-04 | RMSE, acquisition time, re-acquisition time, lock retention rate, FPS are computed |

### GUI Requirements Pass

| Test | Criterion |
|---|---|
| AC-GUI-01 | All mandatory parameters are configurable through GUI |
| AC-GUI-02 | Simulation can be started and stopped via GUI |
| AC-GUI-03 | MP4 file can be loaded via GUI |
| AC-GUI-04 | Real-time statistics are visible during operation |
| AC-GUI-05 | GUI is responsive and does not freeze during simulation |

### Logging Requirements Pass

| Test | Criterion |
|---|---|
| AC-LOG-01 | Performance report file is auto-generated |
| AC-LOG-02 | Report contains: duration, FPS, acquisition time, avg/max tracking error, lock retention rate, processing time |
| AC-LOG-03 | Centroiding error log is auto-generated during benchmarks |

### Standalone Execution Pass

| Test | Criterion |
|---|---|
| AC-EXE-01 | Application launches on a clean Windows machine without IDE/interpreter |
| AC-EXE-02 | No compilation step required by the user |

---

# PART 14 — Traceability Matrix

| Req ID | Requirement | PS Source | Evaluation Stage | Feature | Acceptance Test |
|---|---|---|---|---|---|
| FR-001 | Virtual environment ≥ 2000×2000 | L72, Row 1 | FV, BM1 | FEAT-ENV-001 | AC-FR-01 |
| FR-002 | Beacon generation (1 target) | L73, Rows 7–10 | FV, BM1 | FEAT-TGT-001 | AC-FR-02 |
| FR-003 | Multiple targets (optional) | Row 8 | FV | FEAT-TGT-001 | — (optional) |
| FR-004 | Camera viewport 640×480 | L74, Rows 3–4 | All | FEAT-CAM-001 | AC-FR-04 |
| FR-005 | Camera monochrome | Row 2 | FV | FEAT-CAM-002 | AC-FR-04 |
| FR-006 | Camera ≥ 30 Hz | Row 5 | All | FEAT-CAM-004 | AC-PR-06 |
| FR-007 | Camera initial centre | Row 6 | BM1 | FEAT-CAM-005 | AC-FR-05 |
| FR-008 | 4 motion patterns | Row 12 | FV, BM1 | FEAT-MOT-001 | AC-FR-03 |
| FR-009 | Optional motion patterns | Row 12 | FV, TE | FEAT-MOT-002 | — (optional) |
| FR-010 | S&P noise | Row 21 | FV, BM1 | FEAT-DST-001 | AC-FR-06 |
| FR-011 | Gaussian noise | Rows 21–22 | FV, BM1 | FEAT-DST-002 | AC-FR-06 |
| FR-012 | Poisson noise | Row 21 | FV, BM1 | FEAT-DST-003 | AC-FR-06 |
| FR-013 | Noise selection (one or more) | Row 21 | FV, BM1 | FEAT-DST-007 | AC-FR-10 |
| FR-014 | Camera jitter | Row 23, L78 | FV, BM1 | FEAT-DST-004 | AC-FR-08 |
| FR-015 | Atmospheric modes | Row 24 | FV, BM1 | FEAT-DST-005 | AC-FR-07 |
| FR-016 | Platform motion (linear) | Row 25 | FV, BM1 | FEAT-DST-006 | AC-FR-09 |
| FR-017 | Optional platform patterns | Row 25 | FV | FEAT-DST-006 | — (optional) |
| FR-018 | Combined disturbances | Row 21, L78 | FV, BM1 | FEAT-DST-007 | AC-FR-10 |
| FR-019 | Auto beacon detection | L29, L75 | All | FEAT-DET-001 | AC-FR-11 |
| FR-020 | Beacon identification | L29 | BM1, BM2 | FEAT-DET-002 | AC-FR-11 |
| FR-021 | Centroid estimation | L112, L113 | BM1, BM2 | FEAT-CEN-001 | AC-BM2-03 |
| FR-022 | Continuous tracking (CV) | L76 | All | FEAT-TRK-001 | AC-FR-12 |
| FR-023 | PTZ control | L77, Rows 13–14 | All | FEAT-PTZ-001 | AC-FR-13 |
| FR-024 | PTZ speed enforcement | Rows 13–14 | BM1 | FEAT-PTZ-001 | AC-FR-13 |
| FR-025 | PTZ ≥ 20 Hz | Row 15 | BM1 | FEAT-PTZ-002 | AC-PR-07 |
| FR-026 | Real-time stats display | L79 | FV | FEAT-VIS-001 | AC-FR-14 |
| FR-027 | Auto performance log | L103 | BM1, BM2 | FEAT-LOG-001 | AC-LOG-01, AC-LOG-02 |
| FR-028 | Centroiding error log | L112 | BM1, BM2 | FEAT-LOG-002 | AC-LOG-03 |
| FR-029 | MP4 input (bypass PTZ) | L113 | BM2 | FEAT-MP4-001 | AC-BM2-01, AC-BM2-02 |
| FR-030 | Standalone executable | L87 | FV | FEAT-PKG-001 | AC-EXE-01 |
| FR-031 | GUI | L111, L99 | FV | FEAT-GUI-001 | AC-GUI-01–05 |
| FR-032 | Computer vision usage | L76 | TE | FEAT-AI-001 | Technical evaluation |
| NFR-PERF-001 | ≥ 20 FPS | Row 20 | BM1, BM2 | FEAT-MET-001 | AC-PR-05 |
| NFR-PERF-002 | Acq ≤ 2s | Row 16 | BM1, BM2 | FEAT-ACQ-001 | AC-PR-01 |
| NFR-PERF-003 | Error ≤ 10px | Row 17 | BM1, BM2 | FEAT-TRK-001 | AC-PR-02 |
| NFR-PERF-004 | Loss < 5% | Row 18 | BM1, BM2 | FEAT-TRK-001 | AC-PR-03 |
| NFR-PERF-005 | Re-acq ≤ 1s | Row 19 | BM1, BM2 | FEAT-ACQ-002 | AC-PR-04 |
| NFR-CODE-001 | Modular code | L91 | TE | — | Code review |
| NFR-DOC-001 | Tech report 10–15pp | L95 | TE | — | Document review |
| NFR-DOC-002 | User manual | L98–99 | TE | — | Document review |

**Legend**: FV = Functional Verification, BM1 = Benchmark-1, BM2 = Benchmark-2, TE = Technical Evaluation

---

# PART 15 — Priority Model

## P0 — Critical for SIH Evaluation

Failure in any of these directly causes major score loss.

| Requirement | Why P0 | Evaluation Impact |
|---|---|---|
| FR-004 (Camera viewport) | Cannot operate without it | All (100%) |
| FR-019 (Auto detection) | Core functionality | All (100%) |
| FR-022 (Continuous tracking) | Core functionality | All (100%) |
| FR-023 (PTZ control) | Core functionality | FV (20%), BM1 (30%) |
| FR-029 (MP4 input) | Benchmark-2 requires it | BM2 (30%) |
| FR-027 (Performance log) | Directly evaluated | BM1 (30%), BM2 (30%) |
| FR-028 (Centroiding error log) | Directly evaluated | BM1 (30%), BM2 (30%) |
| NFR-PERF-001–005 (All performance thresholds) | Directly measured in benchmarks | BM1+BM2 (60%) |
| FR-030 (Standalone executable) | Cannot demo without it | FV (20%) |
| FR-031 (GUI) | Directly scored | FV (20%) |

## P1 — Important for Competitiveness

| Requirement | Why P1 | Evaluation Impact |
|---|---|---|
| FR-008 (4 motion patterns) | Mandatory feature; completeness evaluated | FV (20%) |
| FR-010–012 (3 noise types) | Mandatory feature; disturbance evaluation | FV (20%), BM1 (30%) |
| FR-015 (Atmospheric modes) | Mandatory feature | FV (20%), BM1 (30%) |
| FR-016 (Platform motion — linear) | Mandatory feature | FV (20%), BM1 (30%) |
| FR-014 (Camera jitter) | Disturbance feature | FV (20%), BM1 (30%) |
| FR-018 (Combined disturbances) | Evaluators will likely combine | BM1 (30%) |
| FEAT-AI-001 (AI/CV integration) | Scored in technical evaluation | TE (20%) |
| NFR-DOC-001 (Tech report) | Scored in technical evaluation | TE (20%) |
| NFR-DOC-002 (User manual) | Required deliverable | TE (20%) |
| NFR-CODE-001 (Modular code) | Required deliverable | TE (20%) |
| FR-026 (Real-time stats) | Mandatory PS feature | FV (20%) |

## P2 — Enhancement

| Requirement | Why P2 |
|---|---|
| FR-003 (Multiple targets) | PS says optional |
| FR-009 (Optional motion patterns) | PS says optional |
| FR-017 (Optional platform patterns) | PS says optional |
| FR-005 colour mode | PS says optional |
| FEAT-EXP-001 (Scenario save/load) | Convenience; not scored directly |
| Demo video | PS says optional |

### Scoring Rationale

The priority model reflects the PS evaluation weights:
- **60% quantitative** (BM1 + BM2): Tracker performance, centroiding accuracy, logging, and MP4 input are overwhelmingly important.
- **20% functional gate** (FV): All mandatory features must work; GUI must be functional.
- **20% qualitative** (TE): AI/CV usage, innovation, architecture, documentation.

---

# PART 16 — Product Risks

| Risk | Cause | Impact | Likelihood | Mitigation | Requirements Affected |
|---|---|---|---|---|---|
| R-01: Detection failure at 5×5 px beacon with high noise | Small target + noise combination | Cannot track; benchmark failure | High | Use noise-robust detection algorithms; test at extremes early | FR-019, NFR-PERF-002, NFR-PERF-004 |
| R-02: Processing speed below 20 FPS | Computationally expensive detection/tracking algorithm | Direct benchmark failure on FPS metric | Medium | Profile algorithms early; prioritize efficient implementations; avoid heavy ML on CPU | NFR-PERF-001 |
| R-03: Unknown MP4 characteristics break tracker | Evaluator MP4 has different resolution, noise, or beacon appearance than expected | 30% score at risk (BM2) | High | Design tracker to handle arbitrary input; no hard-coded assumptions | FR-029, BM2-001–007 |
| R-04: PTZ controller instability | Oscillation, overshoot, or hunting around beacon | High tracking error, potential target loss | Medium | Careful control tuning; test with all motion patterns | FR-023, NFR-PERF-003 |
| R-05: Centroiding error format mismatch | Our centroid definition/format differs from evaluator expectations | Invalid benchmark comparison | Medium | Document centroid definition clearly; use standard format (CSV with frame, x, y) | FEAT-CEN-001, FEAT-LOG-002 |
| R-06: Application crash during live demo | Edge-case parameter combination, MP4 loading failure, or unhandled exception | 20% score at risk (FV) | Medium | Extensive testing; error handling; graceful degradation | NFR-REL-001 |
| R-07: Evaluator cannot configure scenarios quickly | Poor GUI design or slow parameter entry | Wasted evaluation time; scenario not completed | Medium | Intuitive GUI; support file-based config loading | FR-031, BM1-004 |
| R-08: Combined disturbances cause tracker failure | All disturbances active simultaneously at maximum parameters | Tracking collapses under combined stress | High | Test combined disturbance scenarios extensively; design adaptive algorithms | FR-018, NFR-ROB-001 |
| R-09: Re-acquisition failure | Tracker cannot re-detect beacon after loss within 1 second | Fails NFR-PERF-005; high target loss rate | Medium | Implement explicit re-acquisition strategy with wider search | FEAT-ACQ-002 |
| R-10: Standalone executable fails on evaluator machine | Missing dependencies, wrong OS version, runtime issues | Cannot demo; FV score lost | Low-Medium | Test on clean machines; bundle all dependencies; document requirements | FR-030 |

---

# PART 17 — Open Questions

## Questions Answerable from the PS

| # | Question | Answer from PS |
|---|---|---|
| Q-01 | Is AI/ML strictly mandatory in the implementation? | **Partially**: PS title says "AI-Based"; L68 says "AI-assisted"; L95 says "AI methods (if used)"; evaluation scores "AI and computer vision." CV is mandatory; AI/ML is strongly scored but the report clause suggests it may not be strictly required in implementation. |
| Q-02 | Is colour camera mode mandatory? | **No**: PS Row 2: "Optional: Colour" |
| Q-03 | Are multiple targets mandatory? | **No**: PS Row 8: "1, mandatory; multiple optional" |
| Q-04 | What atmospheric parameters are required? | **Modes**: Clear, Haze, Fog, Rain, Low light. **Effect**: "User-defined reduction in contrast and brightness" (PS Row 24). No specific attenuation values are given. |
| Q-05 | Is the demo video mandatory? | **No**: PS L99: "may also be provided as an optional deliverable" |

## Questions Requiring Clarification from SIH/Organizers

| # | Question | Why It Matters | Impact if Unanswered |
|---|---|---|---|
| Q-06 | What is the resolution and format of benchmark-2 MP4 files? | Determines input handling requirements | Must design for arbitrary resolutions |
| Q-07 | What does "covering a complete screen" mean in benchmark-2? | Determines whether MP4 shows full scene or viewport | Must handle both interpretations |
| Q-08 | How will benchmark-1 scenarios be delivered? (File? Verbal? GUI entry?) | Determines scenario input mechanism | Support both GUI and file |
| Q-09 | What is the exact format expected for centroiding error comparison? | Determines log/export format | Document and standardize our format |
| Q-10 | What does "20 pixels" mean for noise standard deviation? | Determines noise calibration | Make configurable |
| Q-11 | What OS will evaluators use? | Determines build target | Target Windows; test on other OS if possible |
| Q-12 | Will evaluators provide ground truth files alongside benchmark-2 MP4s? | Determines whether system computes centroiding error in MP4 mode | Export centroids for external comparison |
| Q-13 | Is there a maximum beacon velocity constraint? | Determines whether scenarios will always be physically trackable | Make speed configurable; test at high speeds |

## Questions Safely Handled by Configurable Design

| # | Question | Design Strategy |
|---|---|---|
| Q-14 | Exact beacon intensity/contrast | Make configurable (beacon intensity, background level) |
| Q-15 | Exact noise σ units | Allow σ configuration; interpret as intensity by default |
| Q-16 | Target velocity | Make configurable; default to trackable speeds |
| Q-17 | Camera projection model | Use linear (pinhole); make modular for replacement |
| Q-18 | PTZ inertia/acceleration | Use simple velocity-limited model; optionally add inertia |
| Q-19 | Jitter distribution (uniform vs Gaussian) | Make configurable |
| Q-20 | Platform motion velocity profile | Make configurable |

---

# PART 18 — Final Product Definition

> **Our final product is** a standalone desktop application that simulates a 2D virtual environment for FSOC coarse alignment, featuring a configurable beacon target that moves according to selectable motion patterns within a ≥2000×2000 pixel scene, observed through a 640×480 monochrome virtual camera with configurable FOV. The application autonomously detects, identifies, and continuously tracks the beacon using AI-assisted computer vision, controls a virtual pan-tilt camera to maintain lock, injects user-configurable disturbances (noise, jitter, atmospheric degradation, platform motion), displays real-time tracking statistics, and automatically generates performance logs. It also accepts external MP4 video files for independent tracker evaluation without the simulator's PTZ camera. All parameters, performance thresholds, and evaluation metrics are as specified by the ISRO/DoS problem statement for SIH 2026.

## Core Product

A complete virtual camera tracking system with integrated simulation environment, AI/CV-based beacon detection and tracking, PTZ control, disturbance engine, performance measurement, and MP4 benchmark capability — packaged as a standalone executable with GUI.

## Mandatory Features

1. Scene canvas ≥ 2000×2000 with beacon generation (5–20 px, configurable)
2. Virtual camera viewport (640×480, monochrome, FOV default 4°×3°, starting at centre)
3. Four motion patterns (straight, circular, figure-of-8, random)
4. Three noise types (S&P, Gaussian, Poisson) — user-selectable, combinable
5. Five atmospheric modes (clear, haze, fog, rain, low light) with contrast/brightness reduction
6. Camera jitter (±20 px/frame max)
7. Platform motion — linear mandatory (±20 px/frame max)
8. Autonomous beacon detection and identification
9. Centroid estimation and continuous CV-based tracking
10. PTZ control with speed constraints (5–10°/s, ≥20 Hz update)
11. Performance thresholds: ≤2s acquisition, ≤10px error, <5% loss, ≤1s re-acquisition, ≥20 FPS
12. Real-time tracking visualization with statistics
13. Auto-generated performance log (duration, FPS, acquisition time, avg/max error, lock retention, processing time)
14. Centroiding error log
15. MP4 video input mode (bypass PTZ)
16. GUI for configuration, control, and observation
17. Standalone executable

## Competitive Features (Should Have)

1. AI/ML-based detection or tracking component (scored in technical evaluation)
2. Per-frame centroid export in standard format (needed for benchmark-2 comparison)
3. RMSE computation (scored in benchmark-2)
4. Polished, intuitive GUI (scored in functional verification)
5. File-based scenario loading (accelerates benchmark-1)
6. Additional motion patterns (spiral, sinusoidal)
7. Multiple target support
8. Innovation features (predictive tracking, adaptive algorithm selection, etc.)

## Optional Features (Could Have)

1. Colour camera mode
2. User-defined camera resolution
3. Additional platform motion patterns
4. Scenario save/load
5. Demo video (3–5 min)
6. Bird's-eye scene view
7. Real-time error plots

## Explicit Exclusions

1. ❌ Fine alignment / fine pointing simulation
2. ❌ Real hardware interfaces or hardware-in-the-loop
3. ❌ Physics-based atmospheric propagation modeling
4. ❌ Communication link simulation
5. ❌ 3D scene rendering
6. ❌ Multi-platform networking
7. ❌ Cloud/web deployment

## Success Criteria

The product is successful when:
1. All 32 functional requirements pass acceptance tests
2. All 5 performance thresholds are met under default parameters
3. Benchmark-1: can execute evaluator scenarios and produce required logs
4. Benchmark-2: can process evaluator MP4 files and produce required metrics
5. GUI is functional, stable, and operable within 10–15 minutes
6. Technical report, user manual, and source code are delivered
7. AI/CV approach is genuine, defensible, and demonstrably useful
8. Application runs as standalone executable on evaluator's machine

---

> [!IMPORTANT]
> **This PRD is now complete.** It defines WHAT must be built, not HOW. The next step is architecture and detailed design, which should be conducted as a separate phase after this PRD is reviewed and approved by the team. No code, no class diagrams, no algorithm selections have been made. All ambiguities from the PS are preserved and labeled. All inferences and recommendations are clearly distinguished from official requirements.
