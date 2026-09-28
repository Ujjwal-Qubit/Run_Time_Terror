# LumiTrack — Manual Testing Guide
**Platform:** SIH 2026 / ISRO PS-4 · FSOC Coarse Alignment Testbed  
**Version:** Full UI + Backend Coverage  
**How to use:** Work through each section in order. Mark anything that behaves differently from the **Ideal Behaviour** note as a bug. You can paste the section ID + what you observed as a report.

---

> [!IMPORTANT]
> Before you start: make sure both the backend (Python FastAPI server) and frontend (Vite dev server) are running. The backend should be at `http://localhost:8000` and the frontend at `http://localhost:5173`. Open the browser console (F12) and keep it visible throughout the test — it will catch silent errors.

---

## PART 0 — App Launch & Global Shell

### 0.1 — Initial Page Load

**Steps:**
1. Open `http://localhost:5173` in a browser.
2. Wait 2–3 seconds for the page to fully initialize.

**Ideal Behaviour:**
- The page renders immediately with a dark aerospace-themed UI (dark navy/black background).
- The **Header** at the top shows `LumiTrack` branding with the `SIH 2026 / ISRO PS-4` orange badge.
- The sidebar on the left shows three tabs: **Developer**, **Evaluator**, **Results & Analysis**.
- The **Developer** tab is active by default (highlighted/selected in the sidebar).
- The header's center indicator shows `UUT: baseline_tracker` (or whatever the active algorithm is).
- The lock status badge reads `UNLOCKED [IDLE]` in red.
- The WebSocket status reads `LIVE FEED` in green (if backend is running) or `DISCONNECTED` in red (if backend is not running).
- In the browser console: NO red errors on load. There may be a few warnings, but no 404s or connection refused errors.

---

### 0.2 — Header Bar (Always Visible)

**Elements to check:**
| Element | Location | What to check |
|---|---|---|
| LumiTrack logo disc icon | Top-left | Static when sim is IDLE, spins (3s rotation loop) when sim is RUNNING |
| UUT badge | Top-center | Shows the currently active algorithm name |
| Lock status badge | Top-center | Shows `UNLOCKED [IDLE]` → `ACQUIRING [ACQUIRING]` → `LOCKED [TRACKING]` as simulation progresses |
| WebSocket indicator | Top-right | Green `LIVE FEED` = WS connected; Red `DISCONNECTED` = not connected |

**Ideal Behaviour for lock badge colours:**
- `UNLOCKED` → red background
- `ACQUIRING` → amber/yellow background
- `LOCKED` → green background with a pulsing glow animation

---

### 0.3 — Sidebar Navigation

**Steps:**
1. Click **Developer** tab → page content changes to the Developer workspace.
2. Click **Evaluator** tab → page content changes to the Evaluator workspace.
3. Click **Results & Analysis** tab → page content changes to Results workspace.
4. Click back to **Developer** — your previous state (2D/3D view selection) should be preserved within the session.

**Ideal Behaviour:**
- Exactly one tab is highlighted/active at a time.
- Switching tabs does NOT reset the simulation status, config, or algorithm selection.
- The sidebar does not scroll horizontally or overflow.

---

## PART 1 — Developer Tab

> This is the main simulation control workspace. It has a two-column layout: **left column** (Control Panel + Config Panel) and **right column** (Viewport + Telemetry HUD).

---

### 1.1 — Operation Mode Selection (BM1 vs BM2)

**Location:** Top of the Control Panel (left column).

**Steps:**
1. Verify the current mode is **BM1 (Simulation)** (button should appear highlighted/primary blue).
2. Click **BM2 (MP4 Video)**.
3. Observe: the Scenario Preset selector disappears and an MP4 path input appears.
4. Observe: the Configuration Panel (below) becomes semi-transparent (50% opacity) and all its fields become disabled.
5. Click **BM1 (Simulation)** again.
6. Observe: the Scenario Preset selector returns and Config Panel becomes active again.

**Ideal Behaviour:**
- Mode buttons are only clickable when the simulation is **IDLE**. During RUNNING or PAUSED, both buttons should be grayed out/disabled.
- The label above the mode buttons updates: `BM1 Closed-Loop` for Simulation, `BM2 Open-Loop` for MP4.
- BM2 disables the entire Config Panel since you're replaying a fixed video (no live parameter control).

---

### 1.2 — Scenario Preset (BM1 Mode Only)

**Location:** Below mode buttons, visible only in BM1 mode.

**Steps:**
1. Click the scenario dropdown (labelled "Scenario Preset:").
2. Check: does the dropdown show a list of `.json` files from the `scenarios/` directory?
3. Select a scenario (e.g., any option that appears).
4. Observe: the Config Panel fields (Camera, Target, Disturbances, PTZ) should update to reflect the loaded scenario values.
5. Select **"Default Parameters (Interactive)"** (the blank/first option).
6. Observe: config should revert to the default server-side configuration.

**Save Scenario:**
1. Modify any config value (e.g., change camera width to 800).
2. Click **Save** button next to the scenario dropdown.
3. A browser prompt appears — type a name like `my_test_01`.
4. Click OK.
5. Observe: the new scenario `my_test_01.json` appears in the dropdown list.

**Delete Scenario:**
1. Select `my_test_01` in the dropdown.
2. Click the **X** (delete) button.
3. A browser confirm dialog appears — click OK.
4. Observe: `my_test_01.json` disappears from the dropdown.

**Ideal Behaviour:**
- Scenario names are alphanumeric with underscores/hyphens only — special chars or path separators should be rejected by the backend.
- Saving with an empty name → browser prompt stays open (the save is cancelled).
- Delete is disabled when no scenario is selected (X button grayed out).
- Scenario save/load/delete all fire while status is IDLE. These controls are disabled during RUNNING/PAUSED.

---

### 1.3 — MP4 Video Path (BM2 Mode Only)

**Steps:**
1. Switch to BM2 mode.
2. In the MP4 path text field, type a path like `data/test_flight.mp4`.
3. Verify the field accepts the input without any error.
4. Click **Start** — the backend should attempt to open that file.

**Ideal Behaviour:**
- If the file does not exist, the Start button should surface an error alert (browser `alert()` dialog): `"Simulation start error: <message>"`.
- The path field is disabled during RUNNING/PAUSED.

---

### 1.4 — Algorithm Under Test (UUT) Selector

**Location:** "Algorithm Under Test (UUT)" panel inside the Control Panel.

**Steps:**
1. Click the algorithm dropdown.
2. Check: list should show at least `baseline_tracker (v...)` — plus any other plugins in the `src/plugins/` directory.
3. Select a different algorithm (if more than one is available).
4. Observe: the status badge next to the UUT label changes.
5. Observe: the header UUT badge also updates to the new algorithm name.

**Ideal Behaviour:**
- The badge to the right of the UUT label shows `READY` (green) when the algorithm loaded fine, or `ERROR` (red) with an error message when it failed to load.
- If an error occurred during loading, a red error box with a warning icon and the error message appears below the dropdown.
- The algorithm dropdown is **disabled** when simulation is RUNNING or PAUSED. You can only change algorithms when IDLE.
- Selecting an algorithm calls `POST /api/v1/algorithms/select` — watch the console for any 400/500 errors.

---

### 1.5 — Playback Controls (Start / Stop / Pause / Resume / Reset)

**Location:** Button row at the bottom of the Control Panel.

#### Test: Normal Start → Stop

1. Click **Start** (green button, Play icon).
2. **Expected:** Button becomes disabled immediately. Status changes to `RUNNING`.
3. In the header: lock disc icon starts spinning, status badge may transition to `ACQUIRING`.
4. The 2D Viewport starts rendering live frames (no longer idle grid).
5. Telemetry HUD at the bottom starts showing real numbers.
6. Click **Stop** (red button, Square icon).
7. **Expected:** Simulation halts. Status returns to `IDLE`. Viewport shows idle grid again.
8. Telemetry values return to dashes (`---`).

#### Test: Pause → Resume

1. Click **Start**.
2. Wait for simulation to be RUNNING with frames arriving.
3. Click **Pause**.
4. **Expected:** The Pause button disappears and is replaced by a **Resume** button. Status = `PAUSED`. Frames stop arriving. Telemetry values freeze.
5. Click **Resume**.
6. **Expected:** Resume button returns to Pause. Frames restart. Status = `RUNNING`.

#### Test: Reset

1. With simulation IDLE (after a Stop), click **Reset**.
2. **Expected:** The viewport canvas clears (any residual frame is erased). Packet state clears. Telemetry shows dashes.
3. The Reset button is **only** clickable when IDLE — it should be disabled during RUNNING or PAUSED.

**Ideal button states table:**

| Simulation State | Start | Stop | Pause/Resume | Reset |
|---|---|---|---|---|
| IDLE | ✅ Enabled | ❌ Disabled | Pause ❌ Disabled | ✅ Enabled |
| RUNNING | ❌ Disabled | ✅ Enabled | Pause ✅ Enabled | ❌ Disabled |
| PAUSED | ❌ Disabled | ✅ Enabled | Resume ✅ Enabled | ❌ Disabled |

> [!WARNING]
> If the Start button remains enabled after clicking, or the Stop button fires while already IDLE, that's a state machine bug.

---

## PART 2 — Configuration Panel (Tabbed)

> Located in the left column below the Control Panel. Has 4 tabs: **Camera**, **Target**, **Disturbances**, **PTZ**. Fields are disabled in BM2/MP4 mode.

### 2.1 — Camera Tab

**Fields and valid ranges:**

| Field | ID | Type | Valid Range | Ideal Step |
|---|---|---|---|---|
| Width (px) | `cam-width` | Number input | Positive integer (e.g. 320–1920) | 1 |
| Height (px) | `cam-height` | Number input | Positive integer (e.g. 240–1080) | 1 |
| Horizontal FOV (°) | `cam-fov-h` | Number input | 1–180 (degrees) | 0.1 |
| Vertical FOV (°) | `cam-fov-v` | Number input | 1–180 (degrees) | 0.1 |
| Frame Rate (Hz) | `cam-frame-rate` | Number input | 1–120 | 1 |

**Steps:**
1. Click the **Camera** tab (camera icon).
2. Change **Width** from default (e.g., 640) to `800`. Click somewhere else.
3. Observe: the backend is called immediately (`PUT /api/v1/config`). No page reload needed.
4. Start the simulation.
5. Observe: the 2D viewport canvas should now be 800 pixels wide (internally).
6. Change **FOV H** to `90` (degrees). The canvas overlays should adapt (FOV label in HUD changes).
7. Change **Frame Rate** to `5` Hz. Frames should arrive noticeably slower.
8. Change **Frame Rate** to `30` Hz. Frames should arrive faster.

**Ideal Behaviour:**
- Every change fires immediately to the backend (no "Apply" button needed — it says "Live Tuning Active" in the header).
- Values persist if you switch tabs and come back.
- In BM2 mode: all fields are greyed out (the whole Config Panel has 50% opacity) and should not accept input.

---

### 2.2 — Target Tab

**Fields:**

| Field | ID | Type | Valid Range | Notes |
|---|---|---|---|---|
| Beacon Size (px) | `target-size` | Number input | 5–20 | Physical size of the simulated optical beacon |
| Shape Profile | `target-shape` | Dropdown | `gaussian` / `circle` / `square` | Changes the rendered shape of the beacon |
| Intensity (0–255) | `target-intensity` | Number input | 0–255 | Brightness of the beacon in the frame |
| Speed (px/s) | `target-speed` | Number input | 0+ (step 5) | How fast the beacon moves across the frame |
| Motion Pattern | `target-motion` | Dropdown | See below | Controls the trajectory |

**Motion Pattern options:**
- `STRAIGHT_LINE` — target moves in a straight line
- `CIRCULAR` — circular orbit around scene center
- `FIGURE_8` — figure-eight trajectory
- `SPIRAL` — outward or inward spiral
- `SINUSOIDAL` — sinusoidal wave path
- `RANDOM` — random walk (stochastic)
- `POLYGON` — polygon path
- `ZIGZAG` — zigzag path

**Steps:**
1. Click the **Target** tab.
2. Set **Speed** to `150` px/s. Start the simulation. The target should visibly move faster across the 2D viewport.
3. Set **Speed** to `20` px/s. Target moves slowly.
4. Change **Motion Pattern** to `CIRCULAR`. The target should orbit the center.
5. Change **Motion Pattern** to `FIGURE_8`. The target should trace a figure-eight.
6. Change **Shape** to `square`. The beacon spot on the 2D frame should render as a square patch instead of a Gaussian blob.
7. Change **Intensity** to `50`. The beacon should appear dimmer.
8. Change **Intensity** to `240`. The beacon should appear bright/near-white.

**Ideal Behaviour:**
- All changes take effect on the **next frame** if the simulation is already running (live tuning).
- The target should remain within the frame for reasonable speed values. Very high speed + small frame may cause the tracker to lose it.

---

### 2.3 — Disturbances Tab

#### Section A: Atmospheric

| Field | ID | Options | Notes |
|---|---|---|---|
| Condition | `dist-condition` | `CLEAR` / `HAZE` / `FOG` / `RAIN` / `LOW_LIGHT` | Selects a preset atmospheric degradation profile |
| Contrast Factor (0–1) | `dist-contrast` | 0.0–1.0 (step 0.05) | Override contrast; empty = use condition default |

**Steps:**
1. Click the **Disturbances** tab.
2. Set condition to `CLEAR`. Run sim. Frame should look clean with high contrast.
3. Set condition to `FOG`. Frame should look washed out / low contrast.
4. Set condition to `RAIN`. Frame should have scattering artifacts visible.
5. Set condition to `LOW_LIGHT`. Frame should appear darker.
6. Set **Contrast Factor** to `0.2`. Frame should be even lower contrast regardless of condition.
7. Clear the Contrast Factor field (leave blank). System should revert to the condition's default contrast.

**Ideal Behaviour:**
- Changes take effect live during simulation.
- An empty Contrast Factor field sends `null` to the backend (condition default is used).

---

#### Section B: Sensor Noise

| Field | ID | Options | Notes |
|---|---|---|---|
| Noise Type | `dist-noise-type` | `None` / `Gaussian (σ)` / `Salt & Pepper` / `Poisson Shot Noise` | Selecting a type shows the corresponding parameter field |
| Gaussian Sigma (σ) | `dist-gaussian-sigma` | 0–50 (step 0.5) | Formal SIH range: 0–20. Values >20 are experimental headroom. |
| S&P Density | `dist-sp-density` | 0–1 (step 0.01) | Appears only when Salt & Pepper selected |
| Poisson Scale | `dist-poisson-scale` | 0.1–5 (step 0.1) | Appears only when Poisson selected |

**Steps:**
1. Set Noise Type to `None`. Frame should be clean (no pixel-level noise beyond target/atmos).
2. Set Noise Type to `Gaussian (σ)`. A **Gaussian Sigma** field appears. Set sigma to `10`. Frame should show visible grain/snow (tracking remains robust).
3. Increase sigma to `18`. Observe tracking degradation (candidate clustering noise peaks). At `20` (formal SIH ceiling), observe detection breakdown due to noise saturation. Values >20 are experimental stress limits.
4. Set Noise Type to `Salt & Pepper`. A **S&P Density** field appears. Set density to `0.05` (5%). Random white and black pixels should appear across the frame.
5. Set density to `0.3`. Heavy salt-and-pepper visible.
6. Set Noise Type to `Poisson Shot Noise`. A **Poisson Scale** field appears. Scale of `1.0` = standard shot noise.

**Ideal Behaviour:**
- Only one noise parameter field is shown at a time (it switches based on dropdown selection).
- Setting Noise Type to `None` hides the parameter field entirely.
- All three are mutually exclusive (only one can be enabled at once).

---

#### Section C: Geometric Disturbances

| Field | ID | Type | Range | Notes |
|---|---|---|---|---|
| Camera Jitter (px/frame) | `dist-jitter` | Slider | 0–20 (step 0.5) | Simulates camera platform vibration |
| Platform Drift (px/frame) | `dist-platform` | Slider | 0–30 (step 1) | Simulates slow platform motion / wind |

**Steps:**
1. Set **Camera Jitter** slider to `0`. Frame is stable.
2. Drag **Camera Jitter** to `5`. The entire frame should visibly jitter/shake each tick.
3. Drag **Camera Jitter** to `15`. Severe jitter — tracker may lose the target.
4. Drag **Camera Jitter** back to `0`. Jitter should stop immediately.
5. Set **Platform Drift** to `10`. The scene drifts slowly in a random direction each frame.
6. Set **Platform Drift** to `0`. Drift stops.
7. Verify: the live value readout next to each label (e.g., `5 px`, `10 px`) updates as you drag the slider.

**Ideal Behaviour:**
- Current value is displayed in cyan next to each slider label, updating in real time as you drag.
- Setting slider to `0` disables the disturbance on the backend (sets `enabled: false`).
- Any value > 0 automatically sets `enabled: true` on the backend.

---

#### Section D: Local Contrast Clutter

| Field | ID | Type | Notes |
|---|---|---|---|
| Enable checkbox | `dist-clutter-enable` | Checkbox | Enables background clutter blobs |
| Clutter Amplitude | `dist-clutter-amp` | Slider (0–150) | Appears only when enabled |

**Steps:**
1. Tick **Enable** checkbox.
2. Observe: **Clutter Amplitude** slider appears.
3. Set amplitude to `80`. Background should show blobs/patches of varying intensity — simulating IR background clutter.
4. Set amplitude to `150`. Maximum clutter.
5. Untick **Enable**. Slider disappears. Background returns to clean.

**Ideal Behaviour:**
- Slider only appears when the checkbox is checked.
- Value readout shows in amber/orange next to slider.

---

### 2.4 — PTZ Gimbal Tab

| Field | ID | Type | Range | Notes |
|---|---|---|---|---|
| Proportional Gain (Kp) | `ptz-kp` | Number | ≥0, step 0.5 | PI controller proportional gain |
| Integral Gain (Ki) | `ptz-ki` | Number | ≥0, step 0.1 | PI controller integral gain |
| Max Pan Speed (°/s) | `ptz-max-pan` | Number | 0–10, step 0.5 | Motor speed limit for pan axis |
| Max Tilt Speed (°/s) | `ptz-max-tilt` | Number | 0–10, step 0.5 | Motor speed limit for tilt axis |
| Deadband (px) | `ptz-deadband` | Number | ≥0, step 0.5 | Error within this radius is ignored (no correction) |
| Update Rate (Hz) | `ptz-rate` | Number | ≥1, step 1 | How often the PTZ controller updates |

**Steps:**
1. Click the **PTZ** tab.
2. Verify the info note at the bottom: `"Current controller: Proportional-Integral (PI). No derivative term (Kd) in this release."`
3. Set **Proportional Gain (Kp)** to `5`. Run simulation. Observe: the gimbal should react aggressively to tracking error — pan/tilt angles will change rapidly in the Telemetry HUD.
4. Set Kp to `0.5`. Observe: the gimbal responds sluggishly.
5. Set **Deadband** to `0`. The gimbal corrects even for 1-pixel offsets.
6. Set **Deadband** to `20`. The gimbal only corrects when the target is more than 20px off center.
7. Set **Max Pan Speed** to `1.0°/s`. The gimbal moves slowly — it will lag behind fast targets.
8. Set **Max Pan Speed** to `10.0°/s`. Fastest allowed pan rate.

**Ideal Behaviour:**
- Changes take effect live (no restart needed) since the PTZ controller reads config each cycle.
- The Telemetry HUD `GIMBAL PAN` and `GIMBAL TILT` fields update each frame to reflect the controller output.
- There is no Kd (derivative) field — this is by design. The info note confirms this.

---

## PART 3 — 2D HUD Viewport

> Located in the right column, accessed via the "2D HUD Sensor View" button tab.

### 3.1 — Idle State (Before Start)

**Steps:**
1. Make sure simulation is IDLE.
2. Look at the 2D viewport canvas.

**Ideal Behaviour:**
- The canvas shows a dark background with a subtle **cyan grid** (lines every 40px).
- A **white crosshair** reticle at the center of the canvas.
- Grey text in the middle: `OPTICAL SENSOR IDLE — CLICK START TO BEGIN ACQUISITION`
- No overlays, no HUD box, no tracking markers.

---

### 3.2 — Active State (During Simulation)

**Steps:**
1. Start the simulation (BM1 mode).
2. Watch the 2D viewport carefully.

**Ideal Behaviour — Frame rendering:**
- The canvas renders the actual simulated frame (grayscale/colour image with the optical beacon and any disturbances).
- The frame updates every time a new frame arrives (based on camera frame rate).

**Ideal Behaviour — Overlay elements (when Overlays: ON):**

| Overlay | Colour | Appears When | Description |
|---|---|---|---|
| Boresight reticle (crosshair) | White | Always | Fixed cross at frame center; indicates gimbal boresight |
| Deadband circle | White (20% opacity) | Always | Small circle (~10px radius) around center |
| ROI box | Cyan (`#00d2ff`) | When ROI is valid | Adaptive Region of Interest box around the tracked area |
| Estimated Centroid | Red crosshair + circle | When TRACKING / ACQUIRING / REACQUIRING | Sub-pixel position of the detected beacon |
| Laser vector line | Red dashed | When centroid valid | Dashed line from center to centroid |
| Ground Truth marker | Green 6×6 square | When GT data present | Debug overlay showing true beacon position |
| Target lock brackets | Green corner brackets | When `lock_status == LOCKED` | Corner bracket overlay on centroid position |
| In-frame HUD box | Dark translucent box, cyan border | Always when frame active | Top-left telemetry readout (FRAME, STATE, ERR, LATENCY, PTZ, FOV) |

**Steps for each overlay:**
1. While simulation is RUNNING, observe: **boresight reticle** (white cross) should always be at frame center.
2. Observe: **cyan ROI box** should appear around the detected beacon and follow it.
3. Observe: **red crosshair + circle** should sit at the estimated centroid of the beacon.
4. Toggle **GT Marker** button (top-right of viewport area) → green square should appear/disappear at the true target position.
5. Toggle **Overlays: ON/OFF** button → all overlays should disappear/reappear.
6. Confirm top-left HUD box shows correct live values for frame number, state, tracking error, latency, PTZ angles, and FOV.

---

### 3.3 — Frame Scale Slider

**Location:** Below the viewport toolbar, a slider labelled "Frame size" (40–100%).

**Steps:**
1. Drag the Frame Scale slider to `50%`.
2. Observe: the canvas shrinks to half its display size within the viewport area.
3. Drag to `100%`. Canvas is at full display size.

**Ideal Behaviour:**
- The canvas CSS width changes but internal resolution stays the same.
- Overlays remain correctly positioned regardless of display scale.

---

### 3.4 — Target Lock Indicator (TargetLock Component)

**Location:** Top-right corner of the 2D viewport (overlaid on the canvas area).

**Steps:**
1. Run simulation. Watch the lock indicator.
2. Initially it shows ACQUIRING state.
3. Once the tracker acquires the beacon: observe the lock indicator change.
4. If the target moves out of frame or is obscured, the state should revert to LOST/REACQUIRING.

**Ideal Behaviour:**
- When `lock_status === 'LOCKED'`: the indicator shows a green locked state with a pulsing glow.
- When `lock_status === 'ACQUIRING'`: amber/yellow state.
- When `lock_status === 'UNLOCKED'` or `'LOST'`: red state.

---

## PART 4 — 3D Geometric Orbital View

> Accessed via the "3D Geometric Orbital View" tab button in the Developer page.

**Steps:**
1. Click **3D Geometric Orbital View**.
2. Observe: the canvas switches to a 3D scene rendered via Three.js.
3. Try clicking and dragging on the 3D viewport → the camera should orbit.
4. Try scrolling → the camera should zoom in/out.
5. Start the simulation. The 3D view should show the gimbal/camera geometry updating in real time.

**Ideal Behaviour:**
- The 3D view shows a geometric representation of the PTZ camera platform and the target's position in 3D space.
- Pan angle and tilt angle from the telemetry packet drive the camera gimbal rotation visually.
- The view is interactive (orbit controls) even while simulation is running.
- Switching between 2D and 3D does not affect the simulation — both can be used interchangeably.

---

## PART 5 — Telemetry HUD Panel (Bottom Strip)

> Located below the viewport in the Developer page. Always visible.

**Fields (11 tiles):**

| Field Label | Source | Colour | Idle Value | Active Value |
|---|---|---|---|---|
| ALGORITHM | Active algorithm name | Cyan | `baseline_tracker` | Algorithm name |
| FRAME | `packet.frame_number` | White | `---` | Incrementing integer (0, 1, 2…) |
| STATE | `packet.tracking_state` | Green/Amber/Red | `IDLE` | `ACQUIRING` → `TRACKING` → `LOST` → `REACQUIRING` |
| LOCK STATUS | `packet.lock_status` | Green/Amber/Red | `UNLOCKED` | `ACQUIRING` → `LOCKED` |
| TRACKING ERROR | `packet.tracking_error_px` | Amber | `---` | Float in pixels (e.g. `3.42 px`) |
| CENTROID X | `packet.estimated_centroid.x` | Light | `---` | Float pixel position |
| CENTROID Y | `packet.estimated_centroid.y` | Light | `---` | Float pixel position |
| GIMBAL PAN | `packet.pan_angle_deg` | Blue | `0.00` | Degrees, can be negative |
| GIMBAL TILT | `packet.tilt_angle_deg` | Blue | `0.00` | Degrees, can be negative |
| THROUGHPUT | `packet.fps` | Green | `---` | Float FPS (e.g. `28.5 FPS`) |
| CORE LATENCY | `packet.latency_ms` | Cyan | `---` | Float milliseconds (e.g. `12.34 ms`) |

**Steps:**
1. With simulation IDLE: verify FRAME = `---`, STATE = `IDLE`, LOCK STATUS = `UNLOCKED`, all measurements = `---`.
2. Start simulation. Verify: FRAME starts incrementing, STATE transitions to ACQUIRING then TRACKING.
3. LOCK STATUS should go from `UNLOCKED` → `ACQUIRING` → `LOCKED` as the tracker settles.
4. TRACKING ERROR should decrease as the tracker homes in on the beacon.
5. CENTROID X and Y should reflect the beacon position in pixel coordinates.
6. GIMBAL PAN and TILT should change as the PTZ controller drives the gimbal.
7. THROUGHPUT should be close to the configured camera frame rate.
8. CORE LATENCY should be single-digit or low double-digit milliseconds for a well-performing algorithm.

**Ideal Behaviour:**
- Colour coding: STATE and LOCK STATUS are green when TRACKING/LOCKED, amber when ACQUIRING, red when LOST.
- ALGORITHM tile always shows the name even when IDLE.
- No tile shows `undefined`, `NaN`, or blank.

---

## PART 6 — Evaluator Tab

> Click **Evaluator** in the sidebar to switch to this tab.
> Layout: left column has two panels (Benchmark Matrix and AI Studio); right column is a live console log.

---

### 6.1 — Standard Benchmark Matrix (BM1 Matrix)

**Fields:**

| Field | Default | Options/Range |
|---|---|---|
| Evaluation Matrix Subset | `CORE` | `SMOKE (3 scenarios)` / `CORE (6)` / `DISTURBANCE (8)` / `FULL (19)` |
| Algorithm Under Test | Current active | Dropdown of available algorithms |
| Deterministic Seed | `42` | Any integer |
| Frames Per Scenario | `30` | Any positive integer |

**Steps:**
1. Set subset to **SMOKE** (fastest — 3 scenarios).
2. Set algorithm to `baseline_tracker`.
3. Set seed to `42`, frames to `30`.
4. Click **Run SMOKE Benchmark Suite**.
5. Observe: button changes to "Executing Matrix..." with a spinning loader. Button is disabled.
6. Observe: the right-side Console Log shows timestamped entries:
   - `Initiating Benchmark Matrix execution [Subset: SMOKE, UUT: baseline_tracker, Seed: 42]...`
   - A progress bar appears (0% → 15% → 45% → 100%).
   - `Evaluation Complete. Verdict: PASSED (PS 26169 Compliant)` or `FAILED CRITERIA`.
   - Metrics line: `Throughput=XX.X FPS, Centroid RMSE=X.XXX px, Loss Rate=X.X%`.
   - Report path: `Generated Report: output/...`
7. Once complete: button returns to enabled. The app **automatically switches to Results & Analysis tab**.
8. Go back to Evaluator. Run **CORE** subset (6 scenarios). Takes longer.
9. Run **FULL** subset (19 scenarios). This is the exhaustive test.

**Ideal Behaviour:**
- Each subset runs and returns a verdict.
- The progress bar smoothly fills (15% → 45% → 100%) — note: the jump from 15→45 is immediate on API call, 45→100 on completion. This is expected.
- After completion, the Results tab auto-opens.
- Running again with a different seed produces different scenario ordering but the same overall structure.
- Errors show in red in the console: `ERROR executing matrix: <message>`.

---

### 6.2 — AI-Assisted Generative Scenario Studio

**Fields:**
- **Textarea prompt:** Natural language description of a scenario.
- **Quick Preset buttons:** 3 preset prompts for one-click population.

**Steps:**
1. Click a **Quick Preset** (e.g., `"Sinusoidal target in dense fog with 6px jitter"`).
2. Observe: the textarea populates with that text.
3. Click **Generate & Run AI Scenario**.
4. Observe: button shows spinner + "Generating & Executing..."
5. Console logs: `Sending prompt to AI Scenario Interpretation Engine: "..."`
6. After completion:
   - If **valid:** A green panel appears with `✓ Scenario Accepted & Evaluated`, showing Scenario ID, trajectory type, speed, and atmospheric condition.
   - If **invalid:** A red panel with `✗ Validation Failed` and a list of rejected parameters.
   - Console logs the result with FPS, loss rate.

**Test invalid input:**
1. Type something physically impossible: `"Target moving at 9999 px/s through vacuum"`.
2. Run it. Expect the response to show validation errors (physical boundary rejection).

**Test quick presets:**
1. Click `"Fast spiral motion at 90 px/s with Poisson noise"` → textarea changes.
2. Click `"Random walk in heavy rain with platform drift"` → textarea changes again.

**Ideal Behaviour:**
- A valid scenario returns a structured spec with `scenario_id`, `motion_type`, `speed`, and `atmospheric.condition`.
- An invalid scenario returns a list of specific validation errors (not a generic error).
- The textarea is **disabled** while the AI is running.
- Empty prompt: the "Generate & Run AI Scenario" button is disabled (grey).

---

### 6.3 — Evaluation Console (Right Panel)

**Elements:**
- Live log stream of all benchmark/AI events.
- **Clear Console** button (top-right).

**Steps:**
1. Run a benchmark. Watch logs appear in real time.
2. Click **Clear Console**. All log entries disappear.
3. Run another benchmark. Fresh logs start appearing.

**Ideal Behaviour:**
- Log lines are colour-coded:
  - Red: lines containing `ERROR`
  - Green: lines containing `PASSED`
  - Blue/Cyan: lines containing `Initiating` or `Sending`
  - Default grey: all other lines
- Console autoscrolls to bottom as new entries arrive (no manual scrolling needed to see latest).
- Clearing does NOT affect the actual output reports or results.

---

## PART 7 — Results & Analysis Tab

> Click **Results & Analysis** in the sidebar.
> This tab auto-opens after a benchmark completes. It has two columns: left (scorecard + compliance gates + failure analysis), right (report file browser).

### 7.1 — No Data State

**Steps:**
1. Navigate to Results tab without having run any benchmark.
2. Observe: a centred "No Benchmark Data Available" panel should appear.
3. Click **Check for Reports**. If `output/` directory has old JSON reports, they should be fetched and displayed.

**Ideal Behaviour:**
- The empty state shows a database icon, explanation text, and the "Check for Reports" refresh button.
- No fake/placeholder values are shown. Everything is `N/A` or the empty-state message.

---

### 7.2 — SIH 26169 Evaluation Scorecard Header

**After running a benchmark:**

| Element | What to check |
|---|---|
| Verdict badge | Shows `PASSED (PS COMPLIANT)` (green) or `FAILED CRITERIA` (red) or `UNVERIFIED` (grey) |
| Card background | Green gradient for PASS, red gradient for FAIL, grey for unverified |
| Confetti animation | Fires on browser when result is `PASSED` — confetti bursts from screen center |
| THROUGHPUT KPI | Mean FPS across all scenarios (e.g., `28.5 FPS`) |
| CENTROID RMSE KPI | Mean tracking error in pixels (e.g., `2.341 px`) or `N/A` |
| LOSS RATE KPI | Mean target loss rate (e.g., `1.2%`) |
| RUN SUCCESS KPI | Fraction of runs that completed (e.g., `6/6 Passed`) |

**Ideal Behaviour:**
- Confetti fires **only** on confirmed PASS, never on FAIL or undefined.
- `N/A` is shown for any metric where the backend provides `null` — no fake numbers.
- The card border colour matches the verdict.

---

### 7.3 — Compliance Threshold Gates Table

**6 compliance gates (rows):**

| Metric | SIH Limit | Pass Condition |
|---|---|---|
| Processing Throughput (FPS) | ≥ 20.0 FPS | FPS ≥ 20.0 |
| Tracking Error (Centroid RMSE) | ≤ 10.0 px | RMSE ≤ 10.0 |
| Acquisition Time | ≤ 2.0 s | AcqTime ≤ 2.0 |
| Re-acquisition Time | ≤ 1.0 s | ReacqTime ≤ 1.0 |
| Target Loss Rate | < 5.0% | LossRate < 5.0% |
| PTZ Gimbal Slew Rates | Max 5°/s–10°/s | Config-enforced |

**Steps:**
1. After a benchmark run, view each row.
2. Verify: passing gates show a green `PASS` badge; failing gates show a red `FAIL` badge; missing data shows grey `N/A`.
3. The "PTZ Gimbal Slew Rates" row should **always** show `PASS` (it's enforced by config, not measured).

**Ideal Behaviour:**
- Table has correct columns: Benchmark Metric, SIH Required Limit, Measured Value, Verdict.
- The note column (below metric name) gives context: e.g., `"SIH PS-4 Core Hard Requirement"`.
- If RMSE is not available (no ground-truth reference), the note says `"No ground-truth reference — UNVERIFIED"` and verdict is `N/A`.

---

### 7.4 — Failure Analysis Panel

**Steps:**
1. After a run with zero failures: panel shows `✓ Zero fatal failures detected. All X evaluation runs completed within nominal limits.` (green text).
2. After a run with failures: panel shows `N runs failed out of X. Inspect logs in output/ for details.` (red text).
3. With no data at all: panel shows `No evaluation data available.` (muted text).

---

### 7.5 — Report Artifacts Browser (Right Panel)

**Steps:**
1. After running a benchmark, click **Refresh Results** button.
2. Observe: the right panel lists all files in `output/` directory.
3. Each entry shows: file name, size in KB, time (from `mtime`), and a badge (`JSON` / `CSV` / `MD`).

**Ideal Behaviour:**
- JSON files have blue icon, CSV files green icon, MD (Markdown) files orange icon.
- Badge label matches file type.
- Empty state message shows when no reports exist: `"No generated reports found yet."`
- Refresh button shows a spinner animation while loading.

---

## PART 8 — WebSocket Live Feed

> The WebSocket connects to `ws://localhost:8000/ws/live` and streams `VisualizationPacket` objects for every frame.

**Steps:**
1. Open browser DevTools (F12) → Network tab → filter by "WS".
2. Find the WebSocket connection to `/ws/live`.
3. Start the simulation.
4. Watch incoming messages: each should be a JSON object with the following fields:
   - `frame_number` (integer, incrementing)
   - `image_base64` (base64-encoded JPEG/PNG)
   - `tracking_state` (string: `ACQUIRING`, `TRACKING`, `LOST`, `REACQUIRING`)
   - `lock_status` (string: `UNLOCKED`, `ACQUIRING`, `LOCKED`)
   - `tracking_error_px` (float or null)
   - `estimated_centroid` (`{x, y}` or null)
   - `ground_truth` (`{x, y}` or null)
   - `pan_angle_deg`, `tilt_angle_deg` (floats)
   - `fps`, `latency_ms` (floats)
   - `roi` (`{x, y, w, h}` or null)
   - `camera_fov` (float)
   - `resolution` (`{width, height}`)

**Ideal Behaviour:**
- WebSocket connects immediately on app load (before Start is clicked).
- Packets arrive at approximately the configured camera frame rate.
- Disconnection (e.g., backend restart) → frontend shows `DISCONNECTED` in the header. It automatically tries to reconnect.
- Reconnection → header returns to `LIVE FEED` and the packet stream resumes.

---

## PART 9 — End-to-End Scenario Tests

These tests combine multiple features in a realistic workflow.

### Test E1 — Nominal Tracking (Clean Room)
1. Set mode to BM1.
2. Config: Camera 640×480, 30Hz, FOV 45°. Target: Gaussian, size 8, speed 50px/s, CIRCULAR. No noise, no jitter, CLEAR atmosphere. PTZ: Kp=3, Ki=0.5.
3. Start. Observe:
   - Within a few frames: STATE → `TRACKING`, LOCK STATUS → `LOCKED`.
   - Tracking error should be small (< 5 px ideally).
   - Gimbal angles should track the target's circular orbit.

### Test E2 — Aggressive Noise Stress
1. Enable **Gaussian Noise** with sigma = `18` *(backend enforces a hard PS limit of σ ≤ 20.0 — entering σ=25 will be rejected with an alert: `"Gaussian noise sigma (25) exceeds PS limit (20.0)"`)*.
2. Enable **Jitter** at `12` px/frame.
3. Start. Observe:
   - Tracker may enter ACQUIRING → LOST → REACQUIRING cycle.
   - Tracking error will be significantly higher (expect ~100+ px under max stress).
   - The algorithm's robustness is being tested here.

> [!NOTE]
> The σ ≤ 20.0 cap is a physical safety guardrail enforced by the backend, not a bug. Any value above 20 triggers a `400` error and an alert dialog. This is expected behaviour.

### Test E3 — Scenario Save & Load Round-Trip
1. Set a specific config (e.g., FOV 60°, FOG condition, SPIRAL motion, speed 80 px/s).
2. Save it as scenario `stress_fog_spiral`.
3. Change the config to something different.
4. Load `stress_fog_spiral` from the dropdown.
5. Verify: all config values are restored to the saved values.

### Test E4 — Full Evaluation Cycle
1. Go to Evaluator tab.
2. Run **SMOKE** benchmark with `baseline_tracker`, seed `42`, 30 frames.
3. After completion: app auto-switches to Results tab.
4. Verify the scorecard shows a verdict (PASS/FAIL).
5. Verify compliance gate table shows values.
6. Click Refresh Results in the report browser — verify output files are listed.

### Test E5 — AI Scenario with Physical Validation
1. Go to Evaluator → AI Studio.
2. Enter: `"Circular target at 20 px/s in CLEAR atmosphere with 2px jitter"`.
3. Click Generate & Run. Expected: `Scenario Accepted & Evaluated` (valid parameters).
4. Enter: `"Beacon at 5000 px/s"` (unrealistic speed).
5. Click Generate & Run. Expected: `Validation Failed` with specific error about speed limit.

---

## PART 10 — Known Architecture Notes

> These are design decisions — not bugs. Useful context while testing.

| Behaviour | Expected / By Design |
|---|---|
| Config panel disabled in BM2 mode | BM2 replays a fixed video; live-tuning doesn't apply |
| PTZ tab has no Kd field | This is a PI controller only; Kd is not implemented by design |
| WebSocket is display-only | Simulation lifecycle state (IDLE/RUNNING/PAUSED) is owned by the REST poll (every 1s), NOT by WebSocket packets. A stale packet does not reset the status. |
| Contrast Factor empty = null | Sending null lets the backend use the atmospheric condition's default contrast |
| Jitter/Platform sliders set enabled automatically | Setting slider > 0 enables the disturbance; slider = 0 disables it |
| Results tab auto-opens after benchmark | This is intended behaviour after `onBenchmarkComplete` fires |
| RMSE can show as N/A | Only when ground-truth is not available (e.g., some MP4 runs) |

---

## Bug Report Template

When you find something off, note it like this:

```
Section: <e.g., 1.5 — Playback Controls>
What I did: <exact steps>
What happened: <actual result>
What should have happened: <ideal behaviour from guide>
```

That way we can map it directly to the code and fix it. Good luck!
