> [!IMPORTANT]
> STITCH REFERENCE ONLY: ALL NUMERIC VALUES IN THIS DOCUMENT ARE DESIGN-MOCKUP VALUES AND MUST NOT BE TREATED AS PRODUCTION TELEMETRY.

# LUMITRACK — STITCH VISUAL SPECIFICATION & RECONSTRUCTION MATRIX
## Forensic Design Token Audit & Full Behavioral Architecture
### Project: SIH 2026 Problem Statement PS-26169
### Stitch Project: "LumiTrack Simulator Workstation UI"

---

## 1. Executive Summary & Design System Foundations

The visual source of truth is established from the approved Stitch workstation designs in project `projects/10140914770978016521`. The production application contains **EXACTLY FIVE** workspaces:
1. **Developer Workspace** (`1e3e9f6bb97248d1a6b0e4448548b4fa`) — integrates 2D Sensor View, 3D Pedestal Frustum, and 2000×2000 World Canvas sub-views
2. **Evaluator Workspace** (`01b0fe5f0fc642739d3fa5be67fd5bbf`)
3. **Diagnostics & Subsystem Audit** (`8946dde96e7e479e9aea0efac2c45d14`)
4. **Run History & Artifact Catalog** (`9191bab508644cc590da86420b51d1ff`)
5. **Results & Analysis** (`54f7555c797848fd80559409b655e854`)

*(Architectural Invariant: The Developer Workspace integrates the 3D Pedestal Frustum and 2000×2000 World Canvas as internal viewport sub-views [historically cataloged from Stitch prototype artboard `screen_6_3d.html`]. Exactly five production workspaces exist. There is NO standalone sixth workspace, no sixth route, and no sixth sidebar navigation item in the production release.)*

### 1.1 Color Grammar (Aerospace Dark Surface Tokens)

| Token Name | Hex Code | Semantic Role |
| :--- | :--- | :--- |
| `surface` / `background` | `#101418` | Deepest viewport base canvas / application ground |
| `surface-container-lowest` | `#0b0f12` | Sensor reticle canvas, sparkline backdrop, code viewer |
| `surface-container-low` | `#181c20` | Primary dock chassis, sidebar, panel containers |
| `surface-container` | `#1c2024` | Metric cards, sub-panels, input containers |
| `surface-container-high` | `#262a2f` | Card hover state, active header segments |
| `surface-container-highest`| `#313539` | Badges, slider track, inactive button states |
| `surface-bright` | `#363a3e` | Button hover focus |
| `outline` | `#8c909f` | Monospace unit labels, structural headers, inactive text |
| `outline-variant` | `#424754` | Crisp 1px structural dividing borders and reticles |
| `on-surface` | `#e0e3e8` | Primary high-readout alphanumeric telemetry |
| `on-surface-variant` | `#c2c6d6` | Secondary body labels and table cells |
| `primary` | `#adc6ff` | Selected state, Kalman telemetry, tracking indicators |
| `primary-container` | `#4d8eff` | Active primary buttons, ROI bracket bounding frame |
| `secondary` | `#4edea3` | Nominal status, locked indicators, spec pass highlights |
| `secondary-container` | `#00a572` | Active run button, success badges |
| `tertiary` | `#ffb95f` | Warning states, slew vector arrows, ground truth badges |
| `tertiary-container` | `#ca8100` | Warning badges, caution highlights |
| `error` | `#ffb4ab` | Spec violation, threshold ceiling line, degraded state |
| `error-container` | `#93000a` | Critical alarms, stress-test badges |

### 1.2 Typography Hierarchy

- **UI Grotesk (`Inter`)**: structural headers, buttons, navigation, metadata.
  - `headline-lg`: 20px / line-height 26px / 600 weight
  - `headline-md`: 16px / line-height 22px / 600 weight
  - `headline-sm`: 13px / line-height 18px / 600 weight
  - `body-lg`: 13px / line-height 18px / 400 weight
  - `body-md`: 12px / line-height 16px / 400 weight
  - `body-sm`: 11px / line-height 14px / 400 weight
  - `label-md`: 11px / line-height 14px / 500 weight
- **Precision Monospace (`JetBrains Mono`)**: real-time coordinates, rates, timestamps, errors.
  - `data-lg`: 14px / line-height 18px / 500 weight (28px for KPI display)
  - `data-md`: 12px / line-height 16px / 500 weight
  - `data-sm`: 11px / line-height 14px / 400 weight
  - `label-sm`: 10px / line-height 12px / 500 weight

### 1.3 Layout & Viewport Geometry

- Fixed Left Sidebar: width `w-60` (240px), left 0, top 0, bottom 0.
- Fixed Top Header: height `h-10` (40px), left 240px, right 0, top 0.
- Fixed Bottom Footer: height `h-7` (28px), left 240px, right 0, bottom 0.
- Main Central Workspace: padding-top `pt-10`, padding-bottom `pb-7`, left offset 240px (`pl-60`), fluid responsive width.

---

## 2. Shared Application Chrome Spec

### 2.1 Fixed Left Sidebar (`StitchSidebar`)
- **Branding Header**:
  - Logo icon: `satellite` (mint/blue `#adc6ff` on `#002e6a` 20x20 container)
  - Title: `LUMITRACK` (Inter 13px 600, tracking-wider)
  - Version: `v2.4.8` (JetBrains Mono 11px badge on `#313539`)
  - Subhead: `Software Simulator & Benchmark Harness` (Mono 10px `#8c909f` uppercase)
- **Core Workspaces Nav**:
  - `Developer Workspace` (`terminal` icon)
  - `Evaluator Workspace` (`check-square` icon, badge `19/19` in mint)
  - `Results & Analysis` (`bar-chart-2` icon)
  - `Diagnostics & Audit` (`shield` icon)
  - `Run History` (`folder` icon, badge with actual run count)
- **Quick-Jump Views Nav**:
  - `2D Sensor View (640×480)` (`video` icon)
  - `3D Pedestal Frustum` (`box` icon)
  - `2000×2000 World Canvas` (`grid` icon)
- **Operator & Security Footer**:
  - Avatar: User / Terminal icon in `#adc6ff` circle
  - Identity: `SIH Workstation` / `FSOC Terminal Lead`
  - Boundary Guard: `● SECURE / FIREWALL LOCKED` (mint pulse)

### 2.2 Fixed Top Header (`StitchHeader`)
- **Left**:
  - Scenario Selector Badge: `SCN: {scenario_name}` with layer icon
  - Algorithm Selector Badge: `{algorithm_name}` with subpixel badge
- **Center**:
  - Simulation Transport Controls: `RUN` (Secondary/green button with play icon), `PAUSE` (pause icon), `STOP` (stop icon), `+1 FR STEP` (step icon)
  - Rate Badge: `RATE: {backendFps} Hz`
- **Right**:
  - UTC Clock: `UTC HH:MM:SS.mmm`
  - SIM MET: `SIM MET +HH:MM:SS` (computed from `simTime`)
  - Tracking Status Badge: `LOCKED (100% SPEC)` (green) / `ACQUIRING` (amber) / `STANDBY` (muted)
  - Operator Avatar

### 2.3 Fixed Bottom Footer (`StitchFooter`)
- **Left**: `● FRAMEPROVIDER FIREWALL: LOCKED (ZERO LEAKAGE) | AST AUDIT: 0 LEAKS`
- **Center**: `LOOP: {fps} Hz | ACQ: {latency} s | RMSE: {rmse} px`
- **Right**: `✓ GROUND TRUTH: ISOLATED TO METRICS | TELEMETRY: VERIFIED`

---

## 3. Screen 1: Developer Workspace Spec

### 3.1 Top Context Strip
- Left: `● Primary Real-Time Simulation & Coarse Alignment` / `Loop Mode: Autonomous Fine-Tracking` / `HARNESS: ACTIVE`
- Right: `TARGET ID: BEACON [850nm]` | `LINK DISTANCE: {dist_km} km`

### 3.2 Left Viewport Column (8 / 12 cols = 66%)
- **Viewport Controls & Mode Ribbon**:
  - Active view switch: `2D Sensor View (640×480) ACTIVE`, `3D Pedestal Frustum`, `2000×2000 World Canvas`
  - Zoom & Display buttons: `FIT`, `1.0x`, `2.0x`, `GRID`, `RETICLE`
- **Optical Reticle / 640×480 Sensor Canvas Frame**:
  - Aspect ratio 4:3, dark canvas `#0b0f12`, subtle pixel grid texture
  - Boresight crosshairs: continuous & dashed reticle circles, sub-pixel tick marks
  - Real 640×480 frame render via `<img>` or `<canvas>` from backend base64 JPEG
  - Tracking ROI Box: 128×128 cyan bracket overlay anchored to real `telemetry.centroid` (or boresight default), header tag `ROI [128×128 LOCKED]`
  - Centroid reticle: Sub-pixel crosshair ring with live `(X.XX, Y.YY)` label
  - Motion breadcrumb trajectory trail
  - Estimated slew vector arrow
  - Boresight origin label `BORESIGHT (320.0, 240.0)`
  - Ground Truth Watermark: `[GROUND TRUTH — METRICS/VALIDATION ONLY]`
  - Real-Time HUD Overlay (Top-Left): `STATE: LOCKED`, `KALMAN: CONVERGED`, `RESIDUAL: dx, dy`
  - Real-Time HUD Overlay (Top-Right): `GIMBAL: Pan, Tilt`, `SLEW RATE: deg/s`, `FPA INTENS: DN / SNR`
  - Viewport Footer Status: `CCD EXPOSURE: 33.3ms • QUANT: 8-BIT MONO • BURST FIFO: NOMINAL • FOV: 4.00° × 3.00°`
- **Synchronized Viewport Minimap Thumbnails Dock**:
  - Minimap 1: `3D Pedestal Frustum PIP` with live AZ/EL angles and `EXPAND` button (switches to 3D tab)
  - Minimap 2: `World Canvas (2000×2000) PIP` with target X/Y coordinates and `EXPAND` button

### 3.3 Right Parameter Matrices Column (4 / 12 cols = 34%)
- **Simulator Control Matrix Header**: `tune` SIMULATOR CONTROL MATRIX, `HOT-RELOAD ON` badge
- **Section 1: Camera & Sensor FPA**:
  - Array Resolution: `640 × 480 px`
  - Field of View: `4.0° × 3.0°`
  - Integration (Exp): `33.3 ms` (interactive input)
  - Loop Frame Rate: live FPS
- **Section 2: Target Kinematics**:
  - Trajectory Pattern: buttons for `Linear`, `Circular`, `Figure-8` (selected), `Brownian`
  - Slew Velocity: slider `0 - 100 px/s` with live readout
  - Spot Gaussian Divergence: slider `2 - 25 px (FWHM)`
- **Section 3: Environmental Disturbances (SIH Stress Test)**:
  - Atmospheric Condition: `Clear`, `Haze`, `Fog (ACTIVE)`, `Rain`
  - Noise Injection Channels: checkboxes for `Gaussian Noise (σ = 12.5 DN)`, `Poisson Shot Noise`, `Salt & Pepper`
  - Platform Jitter & Linear Drift telemetry
- **Section 4: PTZ Servo Loop Parameters**:
  - Prop. Gain (Kp), Integral Gain (Ki), Deadband (px), Anti-Windup Clamping status

### 3.4 Bottom Horizon Strip (100% width)
- **Header**: `Horizon Performance Metrics & Specification Compliance`, `ALL 6 CRITICAL SPEC CHECKS PASSING`
- **6 KPI Metric Cards**:
  1. Frame Buffer: `001638 / 3600` (45.5% / PASS)
  2. Loop Rate: `62.7 Hz` (SPEC ≥ 20.0 Hz / 3.13x)
  3. Tracking Error: `3.54 px` (SPEC ≤ 10.0 px / PASS)
  4. Centroid RMSE: `0.028 px` (SUB-PIXEL VERIFIED / ±0.004)
  5. Acq Latency: `0.070 s` (SPEC ≤ 2.0 s / PASS)
  6. Target Loss: `0.00 %` (SPEC < 5.0% / 0 LOST)
- **120-Frame Real-Time Radial Tracking Error History Sparkline**:
  - SVG sparkline with grid lines, Spec ceiling line (10.0 px in error/red), and actual rolling error polyline (blue/mint)
  - Labels: `10.0 px CRITICAL SPEC LIMIT` vs `CURRENT: 3.54 px (STABLE CONVERGENCE)`

---

## 4. Screen 2: Evaluator Workspace Spec

### 4.1 Hero Compliance Banner
- Header: `Official Jury Console`, `DOC ID: ISRO-DoS-AUDIT-2025-04`, `AIRGAP SEAL SECURE`
- Title: `ISRO DoS Problem Statement PS-26169 Verification Audit`
- Description: `Autonomous Free-Space Optical Communication (FSOC) Beam Pointing, Acquisition & Tracking Benchmark.`
- Controls: `Execute Full Suite (19)`, `Run Selected (4)`, `Stop Batch`, `Export Compliance Dossier (.ZIP)`
- 4 Major KPI Cards:
  1. Benchmark Pass Rate: `100.0% (19/19 Scenarios)` with progress bar
  2. Mean Tracking Error: `3.54 px` (RMSE: `0.028 px`, Spec `≤ 10.0 px`)
  3. Target Loss Frequency: `0.00% (0 Total Drops)`, Spec `< 5.0%`
  4. Processing Throughput: `62.7 FPS` (Core: `898 FPS`, Spec `≥ 20.0 FPS`)

### 4.2 Workspace Tabs
- `Benchmark 1: Automated Scenario Suite (19/19 VERIFIED)`
- `Benchmark 2: Video Evaluator (PTZ BYPASS)`

### 4.3 Tab 1: Automated Scenario Suite
- Filter Suite buttons: `ALL (19)`, `HIGH JERK (5)`, `ATMOSPHERIC TURBULENCE (6)`, `LOW SNR / CLOUD (4)`, `FOV BOUNDARY (4)`
- Seed & Tolerance readouts
- Execution Matrix Table (19 scenarios):
  - Columns: Scenario ID, Motion Profile & Orbit Tier, Atmospheric & Noise Stack, Mean Err (px), Centroid RMSE, Acq Latency, Loss Rate, Status, Audit Actions
  - Pass badges, inspect telemetry log action, download vector action

### 4.4 Tab 2: Video Evaluator (Dual Column)
- Left (7 cols):
  - Video Viewport Simulator Canvas with simulated optical beacon, boresight crosshairs, 128×128 tracking ROI, sub-pixel centroid ring, HUD overlays (X/Y measured, ground truth, delta, centroid lock, frame match, pipeline).
  - Bottom stream progress overlay with timeline bar.
  - Video Evaluator Performance Row: `Standalone Core Speed 898.2 FPS`, `Ref CSV Discrepancy 0.393 px RMSE`, `Total Evaluated Frames 1,200 / 1,200`.
- Right (5 cols):
  - Interactive Markdown Compliance Report Preview: `# AUDIT VERIFICATION CERTIFICATE`, Executive Summary, Integrity & Isolation Audit.
  - Cryptographic SHA-256 Audit Seal: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` with Copy Hash button.
  - Official Jury Sign-Off Block: `Dr. G. Seshadri / Lead Optical Ground Station Evaluator`, `✓ DIGITALLY SIGNED`.
  - Actions: `Raw Markdown (.MD)` & `Generate Signed PDF`.

---

## 5. Screen 3: Diagnostics & Subsystem Audit Spec

### 5.1 Sub-Header
- Title: `Software Architecture & Subsystem Audit`, badges: `AIR-GAPPED SIL`, `BUILD 2.4.8-PROD`.
- Host Runtime: `Python 3.11.8 (C-ABI Vectorized NumPy/BLAS)`.
- Action: `EXECUTE FULL RE-AUDIT`.

### 5.2 Section 1: Ground-Truth Software Firewall Architecture
- 3-Tier Barrier Grid:
  1. `Simulation Domain (Unprivileged for Tracker)`: Synthetic world coordinates, turbulence seeds, pedestal slew true, flux coefficients. Marked with ground truth warning.
  2. `FrameProvider Firewall Contract (Mutable Pointers Stripped)`: Permitted Data Payload (uint8 mono 640×480 raster, hardware timestamp Δt, static intrinsic matrix K) vs Blocked Boundary Prohibitions (target beacon world coords, simulator truth state & noise seed). Read-only copy protected.
  3. `Perception & Tracker Core (Sandboxed Workspace)`: Calculated CoG centroid, discrepancy error, optical lock status, 0 oracle identifiers. Zero coordinate leakage verified.
- Formal Verification Badges: `AST Static Leak Audit (0 LEAKS FOUND)`, `Dynamic Poisoning Injection Test (PASSED)`.

### 5.3 Section 2: AI Candidate Classifier + 6-Stage Perception Chain
- Left: `AI Candidate Classifier (scikit-learn GBDT / MLP)`:
  - Metric summary: Precision `98.4%`, Recall `99.1%`, F1-Score `0.987`, FP Rate `1.2%`.
  - 6-Feature Extraction Vector bar chart: F1 Peak Intensity (95%), F2 Local Contrast (88%), F3 Area vs PSF (92%), F4 Compactness (94%), F5 Aspect Ratio (98%), F6 Boundary Sharpness (85%).
  - Cloud rejection test: `4,120 / 4,120 rejected (PASS 100.0%)`.
- Right: `6-Stage Perception & State Estimation Chain`:
  - 6 Node badges: `01 RAW FRAME (640×480)`, `02 ROI MASK (128×128)`, `03 AI CLASSIF (GBDT 99%)`, `04 SUB-PIXEL (CoG 3×3)`, `05 2D KALMAN (CV/CA 4-st)`, `06 PTZ SLEW (RATE-LIM)`.
  - Numerical readouts: Measurement Residuals (Innov ΔX, ΔY, NIS statistic), Covariance Matrix P (`diag([0.012, 0.012, 0.045, 0.045])`), Servo Output Az/El, Anti-windup clamping.

### 5.4 Section 3: Thread Loop Execution Budget & Horizontal Gantt Allocation
- Target: `16.00 ms (62.7 Hz)`, Total Duration: `8.95 ms`, Idle Slack: `7.05 ms (44.1% HEADROOM)`.
- Horizontal Gantt Bar: Ingest (2.10 ms / 13.1%), Extract & AI (4.20 ms / 26.3%), CoG (0.80 ms / 5.0%), Kalman (0.40 ms / 2.5%), PTZ (0.25 ms / 1.6%), Telemetry (1.20 ms / 7.5%), Idle Slack Headroom (7.05 ms / 44.1%).
- Real-time Subsystem Event Stream log table with timestamps and firewall status.

---

## 6. Screen 4: Run History & Artifact Catalog Spec

### 6.1 Partition & Filter Bar
- Partition: `OGS_BLR_ALPHA :: COARSE_ALIGN_V2`, DB Sync `48/48 Records Indexed`, Store `342.1 MB`, Active Session `SESSION_20260903_B`, SHA-256 seal.
- Search input by Run ID, Scenario, or Algorithm.
- Filters: `ALG`, `SCN`, `OUTCOME`, `RANGE`.
- Actions: `Export (.ZIP)`, `Compare Selected (2/3)`, `Purge Old`.

### 6.2 Run History Table
- Columns: Checkbox, Run Identifier, Timestamp (UTC), Algorithm & Version, Scenario/Input, Mean Error, RMSE, Acq Latency, Loss Rate, Throughput, Outcome badge, Actions (Inspect).
- Current run highlighted with active tag.

### 6.3 Focused Run Inspector & Artifact Catalog
- Header: `Focused Run Inspector: RUN_...`, synchronized with active log.
- 6 Metric Cards: Mean Tracking Error, Centroid RMSE, Acq Latency, Loop Throughput, Target Loss Rate, Total Processed frames.
- Genuine Filesystem Artifacts list:
  - `centroid_telemetry.csv` (14.2 MB, 2,400 rows, 14 cols)
  - `grand_summary.json` (128 KB, Metric Aggregates)
  - `compliance_report.md` (45 KB, Formal Spec Proof)
  - Download buttons for each file and full `.tar.gz`.

---

## 7. Screen 5: Results & Analysis Spec

### 7.1 Run Header & Action Bar
- Run ID, Scenario name, `COMPLETED [100% SPEC COMPLIANT]` badge, Algorithm version, AST hash, Total frames.
- Export buttons: `CSV Centroids`, `Grand Summary (.JSON)`, `Compliance Report (.MD)`.

### 7.2 4 KPI Engineering Summary Cards
- Mean Tracking Error: `3.54 px` (+64.6% margin, Spec `≤ 10.0 px`)
- Sub-Pixel RMSE (CoG): `0.028 px` (17.8x precision, Benchmark `< 0.50 px`)
- Processing Loop Rate: `62.7 FPS` (3.13x spec, Target `≥ 20.0 FPS`)
- Acquisition & Lock Retention: `0.070 s` (100.0% Locked, Spec `≤ 2.0 s`)

### 7.3 Primary Engineering Chart: Tracking Error vs Time
- 3,600 frames / 60.0 s duration.
- Vertical Disturbance Phase Zones: `Phase I: Slew Lock`, `Phase II: Fog Injected`, `Phase III: Nominal`, `Phase IV: Wind Gust 25m/s`, `Phase V: Jitter Spike 50Hz`, `Phase VI: Recovery`.
- Spec Ceiling line (10.0 px, red dashed), Target line (5.0 px, amber dashed), Measured Error curve (mint/green filled area).

### 7.4 Secondary Engineering Visualizations Row
- Left: `Dual-Axis PTZ Slew Rates (Azimuth / Elevation)` line chart with ±10.0°/s clamp limits, Max slew, duty cycle, anti-windup status.
- Right: `ΔX vs ΔY Residuals Polar Dispersion Target Scope`: Concentric rings (0.10 px, 0.50 px), 1σ Covariance Ellipse, scatter points, Kurtosis, Mean ΔX, ΔY.

### 7.5 Verified Per-Frame Telemetry Table
- Sample stream table with pagination controls: Frame, Time, True X (GT), True Y (GT), Est X, Est Y, Error (px), State (FINE), Pan (°), Tilt (°).

---

## 8. Developer Workspace — Integrated 3D / World View Specification
*(Integrated Sub-Views inside Screen 1: Developer Workspace — Not a standalone screen)*

- **Integrated Split View**: Left (7 cols / ~58%) 3D Optical Terminal Pedestal & Frustum + Right (5 cols / ~42%) 2000×2000 World Canvas.
- **Top Viewport Toolbar**: Tab buttons for switching between `2D Sensor View (640×480)`, `3D Pedestal Frustum`, and `2000×2000 World Canvas`.
- **Sub-View Controls**: Perspective toggle, Reset Orbit View, Frustum Ray toggle (ON/OFF), Trajectory Trail toggle (ALL/OFF), Canvas Grid toggle (100px/OFF).
- **Gimbal Orientation HUD overlay**: Azimuth (°), Elevation (°), Confidence (%), Latency (ms), Clamp status (±10.0°/s MAX).
- **Pedestal Wireframe**: Kinematic base cylinder, yoke, optical barrel, gimbal elevation pivot, camera FOV frustum pyramid with boresight axis and dynamic line-of-sight tracking ray.
- **2000×2000 World Simulation Canvas**:
  - Live Operational Mode: Displays estimated LOS vector, gimbal boresight footprint, and tracking status. Ground truth target coordinates are strictly scrubbed per Ground-Truth Software Firewall.
  - Validation Mode: Explicitly enables true target coordinates with prominent `[GROUND TRUTH — VALIDATION ONLY]` banner.

---

## 9. Data Contract & Truth Mapping Matrix

| Stitch Visual Element | Stitch Dummy/Fictional Value | Classification | Production Real Data Binding |
| :--- | :--- | :--- | :--- |
| Operator Avatar Name | `Dr. G. Seshadri` / `Dr. K. S. Rao` | `[DESIGN CONSTANT]` | `SIH 2026 Operator` / `FSOC Lead / LumiTrack` |
| Organization Header | `ISRO DoS Problem Statement PS-26169` | `[DESIGN CONSTANT]` | `ISRO DoS Problem Statement PS-26169` (Preserved) |
| Active Scenario Badge | `04_combined_stress_high.json` | `[REAL PRODUCTION BINDING]` | `status.activeScenario` |
| Active Algorithm Badge | `Subpixel_CoG + Anti-Windup PI v2.4.8` | `[REAL PRODUCTION BINDING]` | `status.activeAlgorithm` |
| Real-Time Loop Rate | `62.7 Hz` | `[REFERENCE MOCKUP VALUE]` | Live rate `status.backendFps` / `telemetry.algorithmFps` (defaults to `0.0 Hz` when idle) |
| Simulation MET Clock | `+02:44:18` | `[REAL PRODUCTION BINDING]` | Calculated from `status.simTime` |
| UTC Clock | `14:28:09.412` | `[REAL PRODUCTION BINDING]` | Live system UTC clock |
| Tracking State Badge | `LOCKED (100% SPEC)` | `[REAL PRODUCTION BINDING]` | Live `telemetry.trackingState` (`SEARCHING`, `CONVERGING`, `TRACKING`, `COASTING`, etc.) |
| 640×480 Sensor Feed | Static SVG placeholder | `[REAL PRODUCTION BINDING]` | Live HTML5 Canvas rendering `latestFrame.data` (JPEG base64) |
| Centroid Reticle X, Y | `(512.39, 384.22)` | `[REAL PRODUCTION BINDING]` | Live estimated `telemetry.centroid.x`, `telemetry.centroid.y` (displays `—` when unacquired) |
| Gimbal Pan / Tilt | `Pan -1.842° \| Tilt +0.725°` | `[REAL PRODUCTION BINDING]` | Live `telemetry.panAngleDeg`, `telemetry.tiltAngleDeg` |
| Tracking Error (px) | `3.54 px` | `[REFERENCE MOCKUP VALUE]` | Live `telemetry.trackingErrorPx` (strictly `NO DATA` during live tracking unless validation mode active) |
| Centroid RMSE | `0.028 px` | `[REFERENCE MOCKUP VALUE]` | Live `telemetry.boresightOffsetPx` (displays `NO DATA` when uncalculated) |
| Acq Latency | `0.070 s` | `[REFERENCE MOCKUP VALUE]` | Live `telemetry.processingLatencyMs / 1000` (displays `—` when idle) |
| Subsystem Statuses | Hardcoded cards | `[REAL PRODUCTION BINDING]` | `subsystems` array streamed from backend via QtWebChannel |
| Scenario Suite Table | Hardcoded 19 rows | `[DESIGN CONSTANT]` / `[REAL]` | 19 SIH standard scenarios; live execution stats bound to `latestBenchmarkResult` |
| Run History Catalog | Hardcoded 48 rows | `[REAL PRODUCTION BINDING]` | Dynamic `runHistory` from backend `/output` catalog (zero hardcoded mock rows) |
| Artifact Catalog Files | Hardcoded rows | `[REAL PRODUCTION BINDING]` | Genuine filesystem files fetched via `bridgeService.getRunArtifact(path)` |
| Performance Charts | Static SVGs | `[REAL PRODUCTION BINDING]` | Dynamic SVG / Canvas charts bound to real-time telemetry buffer and `resultsData` |
| Ground Truth Coordinates | Hardcoded world coords | `[VALIDATION ONLY]` | Blocked in operational live mode; rendered only under `[GROUND TRUTH — VALIDATION ONLY]` seam |

---
**Verification**: All design tokens, layout dimensions, classes, DOM hierarchies, and data bindings have been fully audited and cross-checked against Stitch MCP raw assets. The production implementation maintains high visual fidelity with 100% data truthfulness and zero fictional telemetry.
