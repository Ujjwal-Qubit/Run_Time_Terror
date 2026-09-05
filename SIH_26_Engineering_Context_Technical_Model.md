# SIH '26 — Engineering Context & Technical Model
## Supporting Engineering Context for AntiGravity Architecture Phase

**Project:** AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile Free Space Optical Communication (FSOC) Terminals  
**Purpose of this document:** Preserve the engineering reasoning developed during the project discussion so AntiGravity can use it as **engineering context** during architecture design.

---

## 0. IMPORTANT STATUS OF THIS DOCUMENT

This document is **NOT an additional authoritative requirements document**.

Use the following hierarchy:

1. **Official SIH Problem Statement (`26169.pdf`) — absolute source of truth**
2. **Approved PRD (`PRD.md`) — agreed product requirements**
3. **This document — engineering context, reasoning, interpretations, and design guidance**
4. AntiGravity's own engineering recommendations

Do **not** convert statements in this document into official PS requirements unless the PS or PRD independently supports them.

For every point below, distinguish:

- **PS-CONFIRMED** — directly supported by the official PS
- **PRD-CONFIRMED** — established in the approved PRD
- **INFERENCE** — reasoned interpretation
- **RECOMMENDATION** — engineering recommendation
- **OPEN/AMBIGUOUS** — unresolved because the PS does not define it

The goal is to prevent earlier reasoning from becoming accidental specification.

---

# 1. CORE UNDERSTANDING OF THE PROBLEM

The system should be understood as a **software-in-the-loop coarse-pointing / virtual PAT laboratory**, rather than merely a simple "camera tracking demo."

The intended product combines:

- a configurable virtual environment,
- a moving optical beacon,
- a virtual camera,
- virtual pan/tilt pointing,
- disturbance/noise simulation,
- autonomous beacon detection,
- beacon identification/confirmation,
- centroid estimation,
- continuous tracking,
- PTZ control,
- acquisition and reacquisition logic,
- real-time performance measurement,
- automatic logging,
- benchmark execution,
- and an external MP4 tracking mode.

The core engineering objective is:

> Given only the camera imagery available to the coarse-pointing system, autonomously locate the intended optical beacon, estimate its image position, maintain lock as the beacon and/or platform moves under disturbances, and control the virtual camera toward the beacon while satisfying the PS performance limits.

For Benchmark-2, the tracking system must additionally operate directly on evaluator-provided MP4 video without depending on the virtual camera/PTZ simulation.

---

# 2. MOST IMPORTANT STRATEGIC INSIGHT: OPTIMIZE FOR THE EVALUATION

The PS evaluation structure means the architecture should be optimized around the quantitative benchmarks.

The scoring is approximately:

- **Functional Verification: 20%**
- **Benchmark Performance-1: 30%**
- **Benchmark Performance-2: 30%**
- **Technical Evaluation: 20%**

Therefore:

> **60% of the total score is quantitative benchmark performance.**

This means tracker robustness, centroiding accuracy, acquisition/reacquisition, lock retention, processing speed, benchmark logging, and MP4 compatibility should receive exceptionally high architectural priority.

Do not build a visually impressive simulator while treating the tracker as a secondary feature.

The architecture should make it easy to:

- benchmark multiple tracking approaches,
- profile latency,
- compare accuracy,
- reproduce scenarios,
- export per-frame estimates,
- diagnose failures,
- and optimize the tracker independently from the simulator.

---

# 3. BENCHMARK-2 IS A CRITICAL ARCHITECTURAL REQUIREMENT

One of the most important conclusions from the PS is that Benchmark-2 can bypass the virtual PTZ camera.

The evaluator will provide MP4 files at approximately 30 FPS and the software must take those videos as input to the coarse-pointing system.

Therefore:

## Required architectural consequence

The detection/tracking pipeline must be capable of accepting:

### Simulation input

`Virtual Camera → Frame → Tracker`

and:

### Benchmark-2 input

`MP4 Decoder → Frame → Tracker`

The tracker should not require:

- the scene canvas,
- simulator state,
- beacon generator state,
- virtual camera state,
- PTZ state,
- or ground truth.

This is an extremely important boundary.

The same tracker should ideally process both input sources.

Avoid creating a tracker that only works because the simulator provides hidden information.

---

# 4. GROUND TRUTH MUST BE ISOLATED FROM THE TRACKER

In simulation, the simulator knows the true beacon position.

That information is useful for:

- centroiding error calculation,
- tracking error calculation,
- benchmark validation,
- test generation,
- debugging,
- and performance analysis.

However, the tracker itself must **never receive ground truth**.

The intended conceptual data flow is:

```text
                    ┌──────────────────────┐
                    │   Ground Truth       │
                    │ True beacon position  │
                    └──────────┬───────────┘
                               │
                               ▼
                        Metrics / Logger

Camera image ───────────────► Tracker
                               │
                               ▼
                         Estimate
```

NOT:

```text
Ground Truth ──► Tracker ──► Estimate
```

Ground truth should be treated as an independent evaluation channel.

This is both a benchmark-integrity requirement and a useful architectural separation.

For MP4 mode, ground truth may not be available to the application at all. The system should therefore export its per-frame centroid estimates for external comparison.

---

# 5. THREE MAJOR COORDINATE/SPATIAL CONCEPTS

The engineering model uses multiple coordinate systems.

## 5.1 World / Scene Coordinates

The virtual scene has dimensions of at least:

`2000 × 2000 pixels`

The beacon has a true position in this scene:

`P_t = (x_t, y_t)`

The virtual camera has a position/orientation associated with its pointing direction.

## 5.2 Camera / Pointing Coordinates

The camera has a pointing state represented conceptually by:

- pan,
- tilt.

The camera looks at some region of the scene.

## 5.3 Image / Pixel Coordinates

The tracker receives a camera image, default:

`640 × 480 pixels`

The tracker estimates the beacon centroid:

`p_est = (x_est, y_est)`

The image center is:

`p_center = (W/2, H/2)`

For the default 640×480 frame:

`p_center = (320, 240)`

These coordinate systems must not be conflated.

---

# 6. CAMERA FOV AND PIXEL ANGULAR SCALE

The PS gives:

- default camera resolution: `640 × 480`
- default FOV: `4° × 3°`

A simple linear interpretation gives:

Horizontal angular scale:

`4° / 640 = 0.00625°/pixel`

Vertical angular scale:

`3° / 480 = 0.00625°/pixel`

Therefore, under this simple projection:

`10 pixels ≈ 0.0625°`

This is **mathematically derived engineering context**, not a PS-prescribed projection model.

The PS does not explicitly prescribe:

- pinhole projection,
- orthographic projection,
- exact world-to-camera transform,
- exact FOV-to-pixel mapping.

Therefore AntiGravity should treat the projection model as an architectural/implementation decision.

A modular camera model is preferred so the projection can be changed later if needed.

---

# 7. CAMERA AND PTZ RATES

The PS defines separate timing requirements:

- Camera update rate: **≥30 Hz**
- PTZ update rate: **≥20 Hz**
- Processing speed: **≥20 FPS**

These are not necessarily the same thing.

A useful conceptual interpretation is:

```text
Camera generates frames at >= 30 Hz
             ↓
Tracker processes at >= 20 FPS
             ↓
PTZ updates at >= 20 Hz
```

The exact synchronization strategy is an architectural decision.

The system should explicitly measure each rate independently where possible.

Do not assume:

`camera FPS = tracker FPS = PTZ update rate`

because the PS treats them as separate parameters.

---

# 8. PTZ SPEED TO IMAGE-MOTION RELATIONSHIP

Default PTZ speed:

- pan: `5°/s`
- tilt: `5°/s`

Using the default angular scale:

`0.00625°/pixel`

the theoretical image-axis equivalent is:

`5 / 0.00625 = 800 pixels/s`

At 30 Hz:

`800 / 30 ≈ 26.67 pixels/frame`

This is an approximate mathematical relationship under the simple linear FOV mapping.

It is useful when reasoning about whether the tracker and PTZ controller can keep up with target motion.

It is **not** an official PS requirement that the camera must move 26.67 pixels/frame.

The actual relationship depends on the selected camera projection and simulator model.

---

# 9. PHYSICAL / MATHEMATICAL TRACKING MODEL

A simplified conceptual model is:

World target:

`P_t(t)`

Camera position:

`P_c(t)`

Line of sight:

`d(t) = P_t(t) - P_c(t)`

The pointing controller seeks to reduce angular error between the camera optical axis and the target line of sight.

At the image level, the tracker estimates:

`p_est(t) = (x_est, y_est)`

and the camera center is:

`p_center = (W/2, H/2)`

The PTZ controller can therefore use image-space offset:

`e_x = x_est - W/2`

`e_y = y_est - H/2`

and map those offsets to pan/tilt commands.

The exact control law is intentionally **not decided yet**.

---

# 10. TWO DIFFERENT ERROR CONCEPTS MUST NOT BE CONFUSED

The PS mentions:

- **Tracking Error ≤10 pixels**
- **Centroiding error** in benchmark evaluation.

The PS does not clearly define either mathematical meaning.

We therefore proposed logging both.

## 10.1 Proposed Centroiding Error

Estimated beacon centroid versus true beacon centroid:

`CE = sqrt((x_est - x_true)^2 + (y_est - y_true)^2)`

This is a **proposed engineering definition**, not an official PS definition.

It is especially useful in simulation where ground truth is known.

## 10.2 Proposed Tracking Error

Estimated beacon centroid relative to camera/image center:

`TE = sqrt((x_est - x_center)^2 + (y_est - y_center)^2)`

Again, this is a **proposed interpretation** of "tracking error."

The architecture should keep these metrics separate and make their definitions replaceable.

Do not hard-code the proposed definitions into the tracker itself.

---

# 11. RMSE

Benchmark-2 explicitly mentions RMSE.

If centroiding error is represented per frame by `CE_i`, a proposed RMSE is:

`RMSE = sqrt((Σ CE_i²) / N)`

where:

- `N` = number of evaluated frames.

The exact evaluator convention should remain configurable/documented because the PS does not define the complete calculation procedure.

---

# 12. TARGET LOSS / LOCK RETENTION

The PS requires:

- Target loss `<5%`
- Lock retention rate in performance reporting.

A proposed relationship is:

`Target Loss Rate = (lost_frames / total_frames) × 100`

and:

`Lock Retention Rate = 100 - Target Loss Rate`

This is an engineering definition.

The architecture should capture per-frame tracking state so the exact aggregation can be changed if the evaluator defines it differently.

---

# 13. ACQUISITION AND REACQUISITION

The PS gives:

- acquisition ≤2 seconds,
- reacquisition ≤1 second.

These imply the system must distinguish at least:

- initial search/acquisition,
- established tracking,
- target loss,
- recovery/reacquisition.

A useful conceptual state machine is:

```text
SEARCHING
    ↓
ACQUIRING
    ↓
TRACKING
    ↓
LOST
    ↓
REACQUIRING
    ↓
TRACKING
```

This exact state naming is not mandatory.

The important architectural requirement is that the system can distinguish:

- initial acquisition time,
- target-loss events,
- reacquisition time,
- normal tracking.

Suggested timing:

### Initial acquisition

Start timer:

`simulation/video start`

Stop when:

`valid target lock is established`

### Reacquisition

Start timer:

`target loss declared`

Stop when:

`valid lock is re-established`

The exact definition of "valid lock" and "loss" remains ambiguous in the PS and should be configurable.

---

# 14. TARGET SIZE IS A MAJOR ALGORITHM CONSTRAINT

The beacon target can be as small as:

`5 × 5 pixels`

Default:

`10 × 10 pixels`

Maximum:

`20 × 20 pixels`

This is strategically important.

At 5×5 pixels, the target is extremely small.

Therefore the architecture should not assume a conventional object-detection problem where the target contains rich semantic features.

A large pretrained object detector such as YOLO/SSD may be computationally expensive and poorly matched to a tiny bright point-like target.

However, this does **not** mean AI/ML should be rejected.

The corrected position is:

- heavyweight generic object detection is likely inappropriate,
- classical signal-processing/CV methods may be highly effective,
- a lightweight AI/ML component may still be valuable,
- a hybrid architecture may be stronger,
- AI should have a genuine technical role if used.

Do not prematurely select the final algorithm.

---

# 15. DETECTION IS NOT THE SAME AS IDENTIFICATION

The PS wording is:

> autonomously detects, identifies, and continuously tracks a designated moving optical beacon.

Earlier reasoning missed the separate word **"identifies."**

Therefore the conceptual pipeline should be:

```text
Frame
 ↓
Candidate Detection
 ↓
Beacon Identification / Validation
 ↓
Centroid Estimation
 ↓
Tracking
```

Detection asks:

> "Is there a bright candidate here?"

Identification asks:

> "Is this candidate actually the beacon we intend to track?"

This distinction is particularly relevant under:

- salt-and-pepper noise,
- Gaussian noise,
- Poisson noise,
- atmospheric degradation,
- multiple targets,
- false bright artifacts.

Identification may use spatial/temporal/appearance/trajectory evidence.

The final method is not decided.

---

# 16. SUGGESTED TRACKING PIPELINE

A modular conceptual tracker:

```text
Input Frame
    ↓
Preprocessing
    ↓
Candidate Generation
    ↓
Candidate Detection
    ↓
Beacon Identification / Validation
    ↓
Centroid Estimation
    ↓
Temporal Tracking
    ↓
Confidence / State Decision
    ↓
Tracking Output
```

Each stage should be replaceable.

This allows future experimentation with:

- thresholding,
- connected components,
- blob detection,
- matched filtering,
- local maxima,
- temporal filtering,
- correlation,
- Kalman filtering,
- optical-flow-like methods where appropriate,
- lightweight ML,
- CNN classification,
- hybrid methods.

These are examples of possible approaches, not final algorithm choices.

---

# 17. HYBRID AI + CLASSICAL CV IS A STRONG DIRECTION

The architecture should support a genuine hybrid strategy.

One possible conceptual arrangement:

```text
Frame
  ↓
Fast classical candidate generation
  ↓
Small number of candidate regions
  ↓
AI/ML validation/classification
  ↓
Sub-pixel centroid estimator
  ↓
Temporal tracker
```

This can potentially provide:

- classical CV speed,
- AI-based false-positive rejection,
- precise centroiding,
- temporal robustness.

Another possible strategy is:

```text
Classical detector
      +
AI confidence/validation
      +
predictive temporal tracker
```

The final architecture should permit such combinations without making them mandatory.

---

# 18. WHY A MODULAR ALGORITHM INTERFACE MATTERS

Because 60% of the score comes from quantitative benchmarks, we should be able to compare algorithms objectively.

The architecture should allow:

```text
Scenario
   ↓
Same Frames
   ├── Algorithm A
   ├── Algorithm B
   ├── Algorithm C
   └── Hybrid
          ↓
Same Metrics
```

Compare:

- centroiding accuracy,
- RMSE,
- FPS,
- acquisition time,
- reacquisition time,
- lock retention,
- target loss.

This prevents choosing an algorithm based only on visual appearance.

The architecture should therefore expose a stable detector/tracker interface.

---

# 19. SIMULATION VS TRACKER SEPARATION

The simulator generates the environment.

The tracker should see only the resulting camera image.

Conceptually:

```text
SIMULATION DOMAIN
────────────────────────────────

Scene
 ↓
Beacon
 ↓
Motion
 ↓
Virtual Camera
 ↓
Disturbances
 ↓
Camera Frame
              │
              ▼
────────────────────────────────
TRACKER DOMAIN
              │
              ▼
Detection
 ↓
Identification
 ↓
Centroid
 ↓
Tracking
 ↓
PTZ command
```

The PTZ command then affects the simulator camera in simulation mode.

This creates a feedback loop:

```text
Beacon motion
     ↓
Camera image
     ↓
Tracker
     ↓
PTZ controller
     ↓
Camera pose
     ↓
New camera image
```

The feedback loop should not exist in the same way for Benchmark-2 MP4 mode because PTZ is bypassed.

---

# 20. SIMULATION LOOP CONCEPT

A complete conceptual simulation loop:

```text
1. Update simulation time
2. Update beacon trajectory
3. Update platform motion
4. Update camera pose
5. Generate clean camera image
6. Apply image/atmospheric disturbances
7. Produce camera frame
8. Run detector
9. Identify beacon
10. Estimate centroid
11. Update tracker state
12. Generate PTZ command
13. Apply PTZ constraints
14. Update camera
15. Compute metrics independently
16. Log telemetry
17. Update GUI
```

The exact execution/threading model is not yet decided.

---

# 21. DISTURBANCES SHOULD BE MODELED IN APPROPRIATE LAYERS

Not every disturbance should simply be "added to pixels."

There are conceptually different categories.

## 21.1 Geometry / Pose disturbances

Examples:

- platform motion,
- camera jitter.

These can affect camera pose or viewport position.

## 21.2 Appearance / Pixel disturbances

Examples:

- Gaussian noise,
- Poisson noise,
- salt-and-pepper noise.

These alter pixel values.

## 21.3 Atmospheric / visibility disturbances

Examples:

- Clear,
- Haze,
- Fog,
- Rain,
- Low light.

The PS describes these in terms of user-defined reductions in contrast and brightness.

Therefore a full atmospheric propagation simulator is unnecessary unless later justified.

---

# 22. DISTURBANCE ORDERING

The exact ordering should be an architectural decision, but a defensible conceptual pipeline is:

```text
Beacon / Scene Rendering
        ↓
Camera Geometry / Viewport
        ↓
Platform Motion / Camera Pose Effects
        ↓
Atmospheric Appearance Degradation
        ↓
Gaussian / Poisson / S&P Noise
        ↓
Final Tracker Input Frame
```

However, some effects may be implemented in different but equivalent layers depending on the simulator design.

AntiGravity should explicitly justify the ordering rather than treating it as arbitrary.

The important principle is:

> Distinguish effects that change camera geometry from effects that change image intensity.

---

# 23. COMBINED DISTURBANCES MATTER

The PS permits multiple noise types to be selected simultaneously.

The expected solution also calls for disturbances from multiple sources.

Therefore the architecture should support combinations such as:

```text
Gaussian
+
Poisson
+
Salt&Pepper
+
Jitter
+
Atmospheric degradation
+
Platform motion
```

Do not design each disturbance as mutually exclusive unless the PS requires it.

The tracker should be tested both:

- one disturbance at a time,
- and combinations.

Combined-disturbance robustness is likely to be important in evaluator scenarios.

---

# 24. CAMERA JITTER VS PLATFORM MOTION

The PS lists these separately:

- Camera jitter: max ±20 px/frame
- Platform motion: max ±20 px/frame

Therefore the architecture should maintain them as separate concepts.

The earlier interpretation that platform motion is necessarily "low-frequency systematic drift" and jitter is necessarily "high-frequency random" is only an engineering interpretation.

Do not encode that characterization as an official requirement.

Instead:

- platform motion should have its own trajectory/profile,
- jitter should have its own stochastic displacement model,
- both may affect apparent camera movement,
- their combined effect should be supported.

---

# 25. ATMOSPHERIC MODES

Required modes:

- Clear
- Haze
- Fog
- Rain
- Low light

The PS specifies user-defined reduction in:

- contrast,
- brightness.

It does **not** require a physically accurate atmospheric optics model.

Therefore the simulator can remain computationally lightweight.

"Clear" should logically represent the baseline/no-degradation condition unless the final design finds another defensible interpretation.

---

# 26. NOISE DETAILS

Required noise types:

1. Salt-and-pepper
2. Gaussian
3. Poisson

Salt-and-pepper:

- PS says around 10% of image.
- Treat this as an approximate suggested/default density, not an immutable threshold.

Gaussian:

- PS gives maximum standard deviation `20`.
- The PS calls the unit "pixels," which is ambiguous because σ for additive intensity noise is normally not a spatial pixel unit.

Do not silently resolve this ambiguity as an official interpretation.

Make the noise parameter configurable.

Poisson:

- signal-dependent shot noise is a reasonable model,
- but the PS only requires Poisson noise selection.

---

# 27. VIRTUAL ENVIRONMENT

The minimum scene size is:

`2000 × 2000 pixels`

This is not necessarily the same thing as the displayed GUI viewport.

The architecture should separate:

- scene/world representation,
- camera viewport,
- GUI visualization.

A bird's-eye view of the entire scene can be useful for demonstration and debugging, but it is not clearly mandated by the PS.

Do not assume the user must see the full 2000×2000 scene at all times.

---

# 28. CONFIGURABILITY

The simulator should expose the PS-defined parameters.

Important defaults/constraints include:

### Scene

- minimum 2000×2000
- user-defined beyond that if supported

### Camera

- monochrome mandatory
- colour optional
- default 640×480
- FOV default 4°×3°
- camera rate ≥30 Hz
- initial position at scene centre

### Beacon

- at least 1
- size 5–20 × 5–20 px
- default 10×10
- configurable shape
- configurable initial location
- default random location

### Motion

Mandatory:

- straight line
- circular
- figure-of-8
- random

Optional:

- spiral
- sinusoidal
- user-defined

### PTZ

- pan 5–10°/s, default 5
- tilt 5–10°/s, default 5
- update ≥20 Hz

### Disturbances

- S&P
- Gaussian
- Poisson
- camera jitter
- atmospheric modes
- platform motion

---

# 29. TARGET SPEED IS AN OPEN DESIGN PARAMETER

The PS defines motion patterns but does not clearly specify beacon velocity.

This means target speed should probably be configurable.

This is important because tracking feasibility depends on:

- target velocity,
- target size,
- FOV,
- frame rate,
- PTZ speed,
- disturbance level.

Do not assume an arbitrary target speed is an official requirement.

A sensible architecture should allow it to be configured and recorded in scenario metadata.

---

# 30. CAMERA PROJECTION MODEL IS AN ENGINEERING DECISION

The PS provides FOV and resolution but does not explicitly define a projection equation.

The architecture should isolate the projection model behind a camera abstraction.

Potential future implementations may include:

- simple linear mapping,
- pinhole-style angular projection,
- another model if required.

Do not hard-code projection assumptions into the tracker.

---

# 31. PTZ CONTROL MODEL

The PTZ controller receives tracker output, not ground truth.

A conceptual input:

```text
estimated beacon position
+
confidence/state
+
camera geometry
+
speed constraints
```

Output:

```text
pan command
+
tilt command
```

The controller should enforce:

- maximum pan velocity,
- maximum tilt velocity,
- update rate,
- saturation/bounds where applicable.

Potential future controllers include:

- proportional control,
- PID,
- predictive control,
- rate-limited proportional control.

The final controller should not be selected at the architecture stage without testing.

---

# 32. LOST-TARGET BEHAVIOR

When the target is lost, the system should not continue blindly commanding the PTZ based on stale measurements indefinitely.

A recovery strategy should be designed around:

- confidence,
- last known position,
- predicted position if available,
- search pattern,
- reacquisition timeout.

The exact strategy is not prescribed by the PS.

The architecture should therefore expose a recovery/search component or equivalent state behavior.

---

# 33. SEARCH / RECOVERY

A useful conceptual recovery sequence:

```text
TRACKING
   ↓
confidence drops
   ↓
LOST
   ↓
predict / search around last known region
   ↓
candidate detection
   ↓
identification
   ↓
valid lock
   ↓
TRACKING
```

The exact search pattern can later be optimized for the ≤1 sec reacquisition requirement.

---

# 34. CONFIDENCE SHOULD BE A FIRST-CLASS TRACKER OUTPUT

A useful tracker output is not merely `(x,y)`.

Conceptually:

```text
{
    estimated_centroid,
    confidence,
    state,
    timestamp,
    detection_valid
}
```

Confidence can help:

- prevent false positives,
- decide lock/loss,
- trigger reacquisition,
- drive PTZ behavior,
- support AI/CV fusion,
- log failure causes.

Confidence is an engineering recommendation, not an explicit PS requirement.

---

# 35. TEMPORAL INFORMATION IS IMPORTANT

The beacon is moving.

Therefore detection should not necessarily treat every frame as an independent image.

Temporal information can help:

- reject isolated noise spikes,
- predict target position,
- validate candidate identity,
- recover from temporary occlusion/noise,
- stabilize centroid estimates,
- reduce false locks.

Potential methods may include:

- temporal consistency,
- velocity estimation,
- Kalman-style prediction,
- candidate association.

Again, these are candidate approaches, not final algorithm decisions.

---

# 36. SUB-PIXEL CENTROIDING MAY MATTER

Benchmark-2 specifically compares centroiding error.

The beacon may be only 5–20 pixels wide.

Therefore a simple bounding-box center may not provide the best possible centroid estimate.

A more accurate centroid estimator could potentially use intensity-weighted methods or other sub-pixel estimation.

The architecture should isolate centroid estimation so it can be independently improved and benchmarked.

Do not force the detector's bounding-box center to be the final centroid.

---

# 37. METRICS MUST BE INDEPENDENT OF THE TRACKER

The tracker should output raw estimates/state.

The metrics engine should consume:

- estimates,
- timestamps,
- ground truth where legally/architecturally available,
- frame dimensions,
- state transitions.

This separation allows metric definitions to change without changing tracking algorithms.

For example:

```text
Tracker
  ↓
Telemetry
  ↓
Metrics Engine
  ↓
Metric Definitions
  ↓
Report
```

---

# 38. PER-FRAME TELEMETRY IS IMPORTANT

For benchmark analysis, store enough information to reconstruct performance.

Potential per-frame telemetry:

- frame number,
- timestamp,
- estimated x,
- estimated y,
- true x/y in simulation-only metrics channel,
- detection valid flag,
- tracking state,
- confidence,
- centroiding error,
- tracking error,
- PTZ command,
- camera pose,
- processing time.

Ground truth fields should never be exposed to the tracker.

---

# 39. PERFORMANCE LOGGING

The PS requires automatic performance reporting including:

- simulation duration,
- FPS,
- acquisition time,
- average tracking error,
- maximum tracking error,
- lock retention rate,
- processing time,
- etc.

Benchmark-2 additionally mentions:

- RMSE,
- acquisition,
- reacquisition,
- lock retention,
- FPS,
- centroiding error comparison.

Therefore logging should be designed as a first-class subsystem, not as GUI text printed at the end.

---

# 40. LOGGING MUST NOT DESTROY FPS

The application must process at least 20 FPS.

Therefore logging should not perform expensive synchronous operations for every frame if that causes tracker stalls.

A good architecture may use:

```text
Tracker
   ↓
In-memory telemetry buffer / queue
   ↓
Logger
   ↓
File
```

The exact implementation is an architecture decision.

---

# 41. BENCHMARK-1 WORKFLOW

Conceptually:

```text
Evaluator scenario
       ↓
Scenario configuration
       ↓
Simulation
       ↓
Camera + disturbances
       ↓
Tracker
       ↓
PTZ
       ↓
Metrics
       ↓
Centroiding error log
       ↓
Automatic performance report
```

The PS says evaluators will provide a few scenarios but does not define the delivery mechanism.

Therefore support for file-based scenario loading is an engineering recommendation, not a confirmed PS requirement.

GUI configuration should remain available.

---

# 42. BENCHMARK-2 WORKFLOW

Conceptually:

```text
Evaluator MP4
      ↓
Video decoder
      ↓
Frame stream
      ↓
Tracker
      ↓
Centroid estimates
      ↓
Metrics / telemetry
      ↓
Centroid export
      ↓
Performance report
```

No:

- virtual scene,
- virtual beacon generator,
- virtual camera,
- PTZ control

should be required.

This is one of the strongest architectural boundaries in the entire system.

---

# 43. BENCHMARK-2 MP4 AMBIGUITY

The PS says the MP4 files are:

> covering a complete screen with noise and moving beacon spot.

This remains ambiguous.

Possible interpretations include:

### A
The video shows the full simulated screen, possibly around 2000×2000.

### B
The video is simply a full-frame video at some resolution with the beacon visible.

### C
The video represents a complete spatial test where the beacon traverses the entire screen over time.

Do not assume which one is correct.

The tracker should therefore avoid hard-coded resolution assumptions and handle arbitrary reasonable input dimensions.

---

# 44. MP4 INPUT SHOULD BE RESOLUTION-AGNOSTIC

The simulator's default is 640×480.

Benchmark-2 may not necessarily use that exact resolution.

Therefore the tracker should derive:

- image dimensions,
- image center,
- ROI coordinates,
- scaling

from the actual input frame.

Avoid hard-coding:

`center = (320,240)`

inside the tracker.

Instead:

`center = (W/2,H/2)`

for the current input frame.

---

# 45. EXTERNAL MP4 SHOULD NOT USE SIMULATOR GROUND TRUTH

Even if the MP4 originated from our simulator, the production benchmark path should treat it as an external image source.

The tracker receives:

- pixels,
- timestamps/frame index.

It should not receive:

- original beacon coordinates,
- original motion parameters,
- original camera pose.

This maintains benchmark integrity and ensures the tracker solves the actual vision problem.

---

# 46. GUI IS SCORED

The GUI is part of functional verification.

It should allow evaluators to quickly:

- configure parameters,
- select disturbances,
- select motion,
- start/stop simulation,
- load MP4,
- see camera/tracking output,
- see real-time statistics,
- access results.

The goal is not maximum visual complexity.

The goal is:

> an evaluator should understand and operate the system quickly during the 10–15 minute demonstration.

---

# 47. POSSIBLE GUI INFORMATION ARCHITECTURE

A useful conceptual organization:

```text
Main Dashboard
├── Simulation / Benchmark Mode
├── Scene / Target Configuration
├── Camera / PTZ Configuration
├── Motion Configuration
├── Disturbance Configuration
├── Live Camera View
├── Tracking Status
├── Real-Time Metrics
├── Benchmark / MP4 Controls
└── Results / Logs
```

A bird's-eye scene view and live error graphs can be useful but are not necessarily mandatory.

---

# 48. STANDALONE EXECUTABLE

The PS requires a standalone executable.

Therefore the architecture should ultimately support packaging without:

- IDE,
- compiler,
- Python interpreter,
- development environment.

The exact platform is not specified.

Windows is a reasonable engineering target because it is a common desktop evaluation environment, but this is not PS-confirmed.

---

# 49. MODULAR CODE IS REQUIRED

The PS explicitly says:

> The code shall be modular and adequately commented.

This should influence architecture directly.

Avoid a monolithic simulation loop containing:

- rendering,
- detection,
- tracking,
- PTZ,
- metrics,
- GUI,
- logging.

Instead maintain clean module boundaries.

---

# 50. TESTABILITY SHOULD DRIVE THE ARCHITECTURE

Each major component should be independently testable.

Examples:

### Motion engine

Input:

`parameters + time`

Output:

`target position`

### Camera model

Input:

`scene + camera state`

Output:

`frame`

### Disturbance engine

Input:

`clean frame + configuration`

Output:

`disturbed frame`

### Detector

Input:

`frame`

Output:

`candidate(s)`

### Centroid estimator

Input:

`frame + candidate`

Output:

`centroid`

### Tracker

Input:

`candidate/centroid history`

Output:

`track state + estimate`

### PTZ controller

Input:

`tracking output`

Output:

`camera command`

### Metrics engine

Input:

`telemetry + ground truth when allowed`

Output:

`metrics`

This modularity will make optimization much easier.

---

# 51. SYNTHETIC DATA GENERATION

The simulator itself can become a valuable source of training/testing data.

Because it can control:

- target size,
- target position,
- motion,
- noise,
- atmosphere,
- jitter,
- platform motion,

it can generate labeled image sequences.

Potential future use:

- train a lightweight AI classifier,
- validate detection algorithms,
- perform robustness testing,
- create edge-case datasets,
- compare algorithms under identical conditions.

However, synthetic data generation is an engineering opportunity, not an official PS requirement.

---

# 52. DOMAIN RANDOMIZATION

A possible competitive enhancement is controlled randomization of:

- target position,
- intensity,
- size,
- noise,
- background,
- motion,
- atmospheric conditions,
- jitter.

This could improve the robustness of an AI component trained on simulator-generated data.

Again, this is optional and should not distract from the core benchmark requirements.

---

# 53. AUTOMATIC ALGORITHM COMPARISON

A strong internal development feature would allow:

```text
Scenario Set
    ↓
 ┌───────────────┐
 │ Algorithm A   │
 │ Algorithm B   │
 │ Algorithm C   │
 │ Hybrid        │
 └───────┬───────┘
         ↓
    Same Metrics
         ↓
 Comparison Report
```

This allows evidence-based selection of the final tracker.

Useful comparison metrics:

- RMSE,
- mean centroid error,
- maximum error,
- FPS,
- acquisition,
- reacquisition,
- target loss,
- lock retention.

---

# 54. ADAPTIVE / HYBRID TRACKING IS A POTENTIAL INNOVATION

A future architecture could allow different methods depending on state.

Example:

```text
SEARCHING
  → robust global candidate detector

TRACKING
  → fast local tracker

LOW CONFIDENCE
  → stronger validation / AI classifier

LOST
  → recovery/search detector
```

This may achieve better performance than running the most expensive algorithm on every frame.

Do not assume this is the final design.

The architecture should make it possible.

---

# 55. PREDICTIVE TRACKING IS A POTENTIAL INNOVATION

Because both target and camera are moving, prediction may help.

Possible conceptual flow:

```text
Current estimate
      ↓
Velocity estimate
      ↓
Predicted next position
      ↓
ROI / search region
      ↓
Detection
```

This can potentially reduce:

- search area,
- processing cost,
- reacquisition time,
- tracker jitter.

Again, do not hard-code a Kalman filter at this stage.

Design an extensible temporal-prediction interface if justified.

---

# 56. ADAPTIVE ROI IS A POTENTIAL PERFORMANCE OPTIMIZATION

Instead of processing the full frame during established tracking:

```text
Full-frame search
      ↓
Target found
      ↓
Local ROI around predicted position
      ↓
Fast tracking
```

On target loss:

```text
Local ROI fails
      ↓
Expand ROI
      ↓
Full-frame reacquisition
```

This could improve processing speed substantially while preserving recovery capability.

This is an engineering candidate, not a requirement.

---

# 57. DO NOT OVERBUILD THE PHYSICS

The PS is fundamentally asking for a virtual tracking system.

Avoid spending major development time on:

- detailed optical propagation,
- atmospheric turbulence physics,
- communication link budgets,
- 3D rendering,
- orbital mechanics,
- RF/optical link simulation,
- hardware interfaces.

The PS specifically describes atmospheric effects primarily as user-defined contrast/brightness reductions.

The core benchmark is the tracker.

---

# 58. DO NOT OVERBUILD THE SIMULATOR AT THE EXPENSE OF THE TRACKER

A beautiful simulator does not compensate for:

- centroiding error,
- tracking failure,
- low FPS,
- poor reacquisition,
- inability to process MP4.

Prioritize engineering effort approximately in this order:

1. Tracker accuracy/robustness
2. Benchmark-2 MP4 pipeline
3. Acquisition/reacquisition
4. Processing performance
5. Metrics/logging integrity
6. PTZ behavior
7. Mandatory simulator disturbances/features
8. GUI polish
9. Optional features

This is strategic prioritization based on the evaluation structure.

---

# 59. IMPORTANT FAILURE MODES TO DESIGN FOR

The architecture should explicitly consider:

- no candidate detected,
- multiple bright candidates,
- false positive caused by noise,
- target temporarily obscured/degraded,
- target leaves expected ROI,
- target reappears,
- excessive disturbance,
- tracker confidence collapse,
- PTZ saturation,
- PTZ oscillation,
- dropped frames,
- slow processing,
- invalid MP4,
- unsupported codec,
- unexpected resolution,
- malformed scenario configuration,
- GUI freeze,
- logger overload.

A robust application should degrade gracefully rather than crash.

---

# 60. PTZ CONTROL MUST NOT USE GROUND TRUTH

This deserves separate emphasis.

Correct:

```text
Tracker estimate
      ↓
PTZ controller
      ↓
Camera
```

Incorrect:

```text
True beacon position
      ↓
PTZ controller
```

The PTZ should behave as a consequence of the vision system.

Otherwise the simulator could appear to track correctly even if the vision system failed.

---

# 61. METRICS AND GROUND TRUTH CAN USE SIMULATOR DATA

This is different from PTZ/tracker access.

Correct:

```text
Simulator
 ├── Camera image ─────────────► Tracker
 │
 └── True beacon position ─────► Metrics
```

This is essential for development and internal validation.

---

# 62. PERFORMANCE THRESHOLDS SHOULD BE TESTED EARLY

Required thresholds:

- acquisition ≤2 s,
- tracking error ≤10 px,
- target loss <5%,
- reacquisition ≤1 s,
- processing ≥20 FPS.

Do not wait until the final demo to measure these.

The architecture should make continuous benchmarking possible from early development.

---

# 63. DEFAULTS VS REQUIREMENTS

Important distinction:

### Default values

Examples:

- 640×480 camera,
- 4°×3° FOV,
- 10×10 beacon,
- 5°/s PTZ,
- approximately 10% S&P noise.

### Hard constraints / thresholds

Examples:

- scene ≥2000×2000,
- camera ≥30 Hz,
- PTZ ≥20 Hz,
- acquisition ≤2s,
- error ≤10px,
- loss <5%,
- reacquisition ≤1s,
- processing ≥20 FPS.

Do not accidentally turn defaults into universal limits.

---

# 64. IMPORTANT PS AMBIGUITIES THAT MUST REMAIN VISIBLE

The architecture should not silently resolve these.

## A. Noise σ "20 pixels"

Unknown whether this means:

- intensity standard deviation,
- spatial interpretation,
- or simply imprecise wording.

## B. Tracking error

Unknown whether:

- beacon-to-frame-center error,
- estimated-vs-true centroid error,
- or another definition.

## C. Centroiding error

Used by the evaluator but not mathematically defined.

## D. Benchmark-2 "complete screen"

Unknown exact video framing/resolution interpretation.

## E. Benchmark-1 scenario delivery

Unknown whether:

- file,
- GUI parameters,
- verbal instructions,
- or another format.

## F. MP4 ground truth

Unknown whether evaluator supplies a ground-truth file.

## G. Target velocity

Not specified.

## H. OS

Not specified.

These should be represented as configurable/replaceable architectural assumptions wherever possible.

---

# 65. WHAT WE SHOULD NOT DO AT ARCHITECTURE STAGE

Do not prematurely lock:

- YOLO,
- SSD,
- a particular CNN,
- Kalman filter,
- PID,
- OpenCV,
- PyTorch,
- TensorFlow,
- Qt,
- Tkinter,
- a specific database,
- a specific file schema,

unless there is a compelling architectural reason.

The architecture should define interfaces first.

The next design/algorithm phase can make evidence-based selections.

---

# 66. WHAT THE ARCHITECTURE SHOULD ENABLE

The final architecture should make all of these possible:

### Core

- virtual scene
- moving beacon
- virtual camera
- PTZ
- disturbances
- detection
- identification
- centroiding
- tracking
- acquisition
- reacquisition
- metrics
- logging
- GUI

### Benchmark

- Benchmark-1 scenario execution
- Benchmark-2 MP4 processing
- direct tracker input
- centroid export
- RMSE
- performance reporting

### Engineering

- ground-truth isolation
- reproducibility
- algorithm replacement
- algorithm comparison
- profiling
- unit testing
- synthetic data generation

### Competitive

- AI/ML integration
- hybrid CV + AI
- adaptive ROI
- prediction
- adaptive algorithm switching
- robust recovery

---

# 67. RECOMMENDED HIGH-LEVEL ARCHITECTURAL BOUNDARIES

A strong conceptual decomposition is:

```text
┌──────────────────────────────────────────────────────────────┐
│                        APPLICATION                            │
│                         GUI / CLI                            │
└───────────────────────┬──────────────────────────────────────┘
                        │
              Configuration / Scenario
                        │
        ┌───────────────┴────────────────┐
        │                                │
        ▼                                ▼
┌───────────────────┐             ┌───────────────────┐
│ Simulation Domain │             │ External Video    │
│                   │             │ Input Domain      │
│ Scene             │             │                   │
│ Beacon            │             │ MP4 Decoder       │
│ Motion            │             │ Frame Provider    │
│ Camera            │             │                   │
│ Disturbances      │             └─────────┬─────────┘
└─────────┬─────────┘                       │
          │                                 │
          └──────────────┬──────────────────┘
                         ▼
                ┌───────────────────┐
                │  TRACKER DOMAIN   │
                │                   │
                │ Detection         │
                │ Identification    │
                │ Centroiding       │
                │ Tracking          │
                │ State/Confidence  │
                └─────────┬─────────┘
                          │
                 Simulation mode only
                          │
                          ▼
                ┌───────────────────┐
                │   PTZ Controller  │
                └─────────┬─────────┘
                          │
                          ▼
                    Virtual Camera

Ground Truth ───────────────────────────────► Metrics
Tracker Telemetry ─────────────────────────► Metrics
Metrics ────────────────────────────────────► Logger
Telemetry / Frames ─────────────────────────► Visualization
```

This is a conceptual boundary, not the final architecture.

---

# 68. ARCHITECTURE SHOULD BE TESTABLE IN ISOLATION

A recommended progression is:

```text
Component Unit Tests
        ↓
Pipeline Tests
        ↓
Synthetic Scenario Tests
        ↓
Combined Disturbance Tests
        ↓
Long-duration Tests
        ↓
Benchmark Simulation
        ↓
External MP4 Tests
        ↓
Packaged Executable Tests
```

This helps identify whether a failure originates in:

- simulator,
- detector,
- centroid estimator,
- tracker,
- PTZ,
- metrics,
- or GUI.

---

# 69. PERFORMANCE TESTING SHOULD INCLUDE STRESS CASES

Do not validate only the easy default case.

At minimum internally test combinations such as:

- 5×5 beacon,
- high noise,
- multiple disturbances,
- strong atmospheric degradation,
- maximum platform motion,
- maximum camera jitter,
- fast beacon movement,
- temporary target loss,
- arbitrary MP4 resolution.

The PS does not explicitly say every maximum must be simultaneously combined, so treat these as stress tests rather than assumed evaluator requirements.

---

# 70. ARCHITECTURAL NORTH STAR

The system should ultimately behave like this:

```text
             ┌───────────────┐
             │  Environment  │
             └───────┬───────┘
                     │
                Beacon moves
                     │
                     ▼
             ┌───────────────┐
             │ Virtual Camera│
             └───────┬───────┘
                     │
                Disturbances
                     │
                     ▼
             ┌───────────────┐
             │  Image Frame  │
             └───────┬───────┘
                     │
                     ▼
          ┌─────────────────────┐
          │ Detection + AI/CV   │
          └──────────┬──────────┘
                     │
                Identification
                     │
                  Centroid
                     │
                  Tracking
                     │
                     ▼
             ┌───────────────┐
             │ PTZ Controller│
             └───────┬───────┘
                     │
                 Camera moves
                     │
                     └──────► feedback loop

Meanwhile:

Ground Truth ───────► Metrics ─────► Reports
Tracker Telemetry ──► Metrics ─────► Logs
MP4 ────────────────► Same Tracker ─► Export
```

The central philosophy is:

> **Build the simulator to test the tracker, not the tracker to justify the simulator.**

---

# 71. FINAL GUIDANCE TO ANTIGRAVITY

Use this document to preserve the reasoning already developed by the team.

However:

- challenge it,
- correct it if necessary,
- distinguish facts from inference,
- do not treat it as another PS,
- do not blindly follow its proposed formulas,
- and explicitly identify any architectural consequences that are not actually supported by the PS/PRD.

Most importantly, the architecture must preserve these principles:

1. **Tracker independence from simulator**
2. **Benchmark-2 direct MP4 capability**
3. **Ground-truth isolation**
4. **Modular detector/centroid/tracker interfaces**
5. **AI/CV extensibility without forcing a heavyweight model**
6. **Independent metrics and logging**
7. **Explicit acquisition/loss/reacquisition states**
8. **Real-time performance ≥20 FPS**
9. **Camera ≥30 Hz and PTZ ≥20 Hz**
10. **Support for combined disturbances**
11. **Resolution-agnostic external video processing**
12. **Ability to compare multiple algorithms under identical scenarios**
13. **Architecture that supports future predictive/adaptive tracking**
14. **No premature final algorithm selection**
15. **Quantitative benchmark performance as the primary optimization target**

This engineering context should be treated as a bridge between the approved PRD and the architecture/design phase.
