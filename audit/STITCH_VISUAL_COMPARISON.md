# LUMITRACK — STITCH VISUAL COMPARISON AUDIT
## Multi-Resolution Forensic UI/UX Rebuilding Analysis
### Project: SIH 2026 Problem Statement PS-26169
### Stitch Reference Project: "LumiTrack Simulator Workstation UI"

---

## 1. Executive Summary

This forensic visual audit compares the production React/TypeScript frontend implementation of the **five approved workstations** against the approved Stitch UI design sources:
- `screen_1_developer.html` (Developer Workspace)
- `screen_2_evaluator.html` (Evaluator Workspace)
- `screen_3_diagnostics.html` (Diagnostics & Subsystem Audit)
- `screen_4_history.html` (Run History & Artifact Catalog)
- `screen_5_results.html` (Results & Analysis)

**Critical Architectural Invariant**:
- **EXACTLY FIVE SCREENS**: There are no additional screens, no sixth navigation route, and no standalone 3D workspace. The 3D optical terminal pedestal and 2000×2000 world canvas visualizations are directly embedded inside the **Developer Workspace** as synchronized viewport tabs, matching the primary operational workflow of the approved Stitch design.

---

## 2. Multi-Resolution Display Matrix Evaluation

The application shell and workstations were evaluated across standard engineering workstation resolutions:

| Viewport Resolution | Layout Behavior | Sidebar Mode | Viewport Aspect | Density & Usability |
| :--- | :--- | :--- | :--- | :--- |
| **1280 × 720** (HD) | Compact grid, horizontal scroll on dense tables | Fixed 240px (`w-60`) | 4:3 Sensor fit, 2-col stack | Dense aerospace layout, zero element truncation |
| **1366 × 768** (Laptop) | Fluid 12-column grid layout | Fixed 240px (`w-60`) | 4:3 Sensor 480px, right shelf fit | Optimal viewing for field deployment laptops |
| **1600 × 900** (Workstation) | 8/4 split on Developer, full bento grids | Fixed 240px (`w-60`) | Full 640×480 sensor canvas + minimaps | High readability, all HUD overlays non-overlapping |
| **1920 × 1080** (FHD / Primary) | Full desktop engineering workstation | Fixed 240px (`w-60`) | 580px max height canvas + 3D split | High visual fidelity matching Stitch layout specifications |

---

## 3. Screen-by-Screen Detailed Visual Forensic Comparison

### 3.1 Screen 1: Developer Workspace

| Dimension | Stitch Reference (`screen_1_developer.html`) | Production React Implementation (`DeveloperWorkspace.tsx`) | Match Assessment |
| :--- | :--- | :--- | :--- |
| **Sidebar & Chrome** | 240px width (`w-60`), `#181c20`, terminal icon, active blue bar | Fixed `w-60`, `#181c20`, `bg-surface-container` highlight, active left border | **HIGH VISUAL FIDELITY** |
| **Top Subhead Ribbon** | Primary Real-Time Simulation subhead, target ID, link distance | Subhead layout, dynamic active scenario & algorithm, live heartbeat dot | **STITCH LAYOUT RECONSTRUCTED** |
| **Viewport Tabs** | 2D Sensor View, 3D Pedestal Frustum, 2000×2000 World Canvas | Integrated 3-tab switch (`activeTab`: `'2d'` \| `'3d'` \| `'world'`) | **INTEGRATED SUB-VIEWS (No Screen 6)** |
| **2D Sensor Canvas** | 640×480 FPA, reticle crosshair, sub-pixel ROI bracket, HUDs | HTML5 Canvas + SVG reticle + dynamic ROI anchored to live centroid | **HIGH VISUAL FIDELITY** |
| **HUD Telemetry** | Top-left (State, Kalman, Conf), Top-right (Gimbal, FOV, FPA) | Live telemetry overlays using JetBrains Mono, real pan/tilt/error values | **REAL DATA BOUND** |
| **Minimaps Dock** | 3D Pedestal Frustum PIP (left) + 2000×2000 World Canvas PIP (right) | Dual SVG interactive minimaps with EXPAND buttons switching active tab | **HIGH VISUAL FIDELITY** |
| **3D Split Viewport** | 60% 3D Frustum (pedestal, LOS, ray) + 40% World Canvas | Available in 3D tab: Full SVG pedestal model, gimbal HUD, orbit controls | **SUB-VIEW INTEGRATED** |
| **Right Control Matrix**| 4 panels: Camera & FPA, Target Kinematics, Disturbances, PTZ Loop | 4 dense panels with live algorithm/scenario selectors, sliders, toggles | **STITCH LAYOUT RECONSTRUCTED** |
| **Bottom Horizon Strip**| 6 KPI bento cards + 120-frame real-time error sparkline | 6 real-data cards (Frame, FPS, Error, RMSE, Latency, Loss) + SVG sparkline | **REAL DATA BOUND** |

### 3.2 Screen 2: Evaluator Workspace

| Dimension | Stitch Reference (`screen_2_evaluator.html`) | Production React Implementation (`EvaluatorWorkspace.tsx`) | Match Assessment |
| :--- | :--- | :--- | :--- |
| **Hero Compliance Banner** | Benchmark Evaluator Console, DOC ID, 4 action buttons, 4 major KPI cards | Full hero header, action buttons trigger real benchmark runs via bridge | **STITCH LAYOUT RECONSTRUCTED** |
| **KPI Strip Truthfulness**| Pass Rate, Mean Error, Loss Frequency, Processing Throughput | Binds to `latestBenchmarkResult`. Displays `AWAITING RUN` when unexecuted | **TRUTHFUL DATA BINDING** |
| **Workspace Navigation** | Benchmark 1 (Scenario Suite) vs Benchmark 2 (Video Evaluator) | Tab switcher with state preservation, matching styling and badge chips | **HIGH VISUAL FIDELITY** |
| **Scenario Matrix** | 19 scenarios table with filtering (Jerk, Turbulence, Cloud, FOV) | 19-scenario matrix table with category filtering and interactive rows | **STITCH LAYOUT RECONSTRUCTED** |
| **Video Evaluator View** | Left video viewport (7 cols) + Right signed summary (5 cols) | High-fidelity split layout with SHA-256 seal and verification block | **HIGH VISUAL FIDELITY** |

### 3.3 Screen 3: Diagnostics & Subsystem Audit

| Dimension | Stitch Reference (`screen_3_diagnostics.html`) | Production React Implementation (`DiagnosticsWorkspace.tsx`) | Match Assessment |
| :--- | :--- | :--- | :--- |
| **Sub-Header Status** | Software Architecture title, Air-Gapped SIL, Python runtime chip | Title, badges, Python 3.11 C-ABI runtime chip, Re-Audit action button | **HIGH VISUAL FIDELITY** |
| **Firewall Architecture**| 3-Tier Barrier Grid: Simulation Domain → Firewall → Tracker Core | 3-tier card layout with permitted vs prohibited payload definitions | **STITCH LAYOUT RECONSTRUCTED** |
| **Hardware Truthfulness**| No fake kernel DMA or physical register addresses | Pure software architecture: FrameProvider boundary, ring buffers, AST audit | **AIRGAP VERIFIED** |
| **AI Classifier Section**| 4-KPI summary (Precision/Recall/F1/FP) + 6-feature horizontal bars | Exact 4-KPI grid + 6-feature weight bars with DN/ratio/gradient readouts | **STITCH LAYOUT RECONSTRUCTED** |
| **Perception Chain** | 6-stage pipeline node badges + Kalman innovation matrices | 6 pipeline step nodes + innovation readouts ΔX, ΔY, NIS statistic | **HIGH VISUAL FIDELITY** |
| **Execution Budget** | 16 ms budget target with 7-phase horizontal Gantt bar + event log | Gantt bar with Ingest/Extract/CoG/KF/PTZ/Telemetry/Idle Headroom | **STITCH LAYOUT RECONSTRUCTED** |

### 3.4 Screen 4: Run History & Artifact Catalog

| Dimension | Stitch Reference (`screen_4_history.html`) | Production React Implementation (`HistoryWorkspace.tsx`) | Match Assessment |
| :--- | :--- | :--- | :--- |
| **Partition Context Bar**| Partition chip, DB Sync chip, Store size, Active Session, SHA-256 | Context bar with live catalog counts, `/output` storage root, refresh button | **STITCH LAYOUT RECONSTRUCTED** |
| **Filter Toolbar** | Search input, ALG/SCN/OUTCOME/RANGE filter chips, action buttons | Real-time search filter, outcome toggle (All/Compliant/Exceeded), Inspect | **HIGH VISUAL FIDELITY** |
| **Run History Table** | 10-column table with run ID, timestamp, frames, FPS, RMSE, outcome | Dynamic table bound to real `runHistory` from backend `/output` catalog | **TRUTHFUL DATA BINDING** |
| **Focused Run Inspector**| 6-metric bento grid + disk artifacts grid (CSV, JSON, MD, Config) | Full 6-metric card inspector bound to selected run + artifact action icons | **HIGH VISUAL FIDELITY** |
| **Artifact Inspector** | Right panel with preview of selected artifact contents | Integrated syntax-highlighted pre-viewer displaying actual JSON/MD files | **REAL DATA BOUND** |

### 3.5 Screen 5: Results & Analysis

| Dimension | Stitch Reference (`screen_5_results.html`) | Production React Implementation (`ResultsWorkspace.tsx`) | Match Assessment |
| :--- | :--- | :--- | :--- |
| **Run Header Bar** | Run ID, SCN badge, completion badge, frame counter, export buttons | Dynamic run header, Reload Latest button, CSV and Report download buttons | **STITCH LAYOUT RECONSTRUCTED** |
| **GT Validation Banner** | Prominent ground-truth banner when validation mode is enabled | Visible `[GROUND TRUTH — VALIDATION ONLY]` banner only during validation | **TRUTHFUL DATA BINDING** |
| **4 KPI Summary Cards** | Mean Tracking Error, Sub-Pixel RMSE, Processing Loop Rate, Volume | Dynamic values computed from time-series; displays `NO DATA` when empty | **TRUTHFUL DATA BINDING** |
| **Tracking Error Chart** | Time-series chart with phase zone bands, spec ceiling, measured error | SVG chart plotting real boresight offsets with 10px ceiling and 5px target | **HIGH VISUAL FIDELITY** |
| **Per-Frame Stream Table**| Frame, Time, Est X/Y, Boresight Err, State, Pan, Tilt, GT Error | Paginated per-frame measurement stream table; GT unexported in live mode | **TRUTHFUL DATA BINDING** |

---

## 4. Typography & Iconography Conformance

1. **Font Grammar**:
   - `Inter` applied globally for UI text, labels, and buttons.
   - `JetBrains Mono` applied for coordinates, timestamps, frame counters, metrics, and code blocks.
   - System/local fallbacks (`ui-sans-serif`, `Consolas`, `monospace`) configured to guarantee offline rendering without internet access.
2. **Iconography**:
   - All iconography systematically migrated to local SVG vector components (`lucide-react`).
   - Zero remote network dependencies (`fonts.googleapis.com` or Google Web Fonts CDN completely eliminated).
   - Zero text-ligature rendering defects offline.

---

## 5. Audit Verdict

All **FIVE** approved production screens conform to the visual architecture, layout density, color grammar, and control hierarchy of the approved Stitch designs with high visual fidelity while operating strictly on real LumiTrack backend telemetry and enforcing verifiable ground-truth firewall isolation.
