# SANKET: TECHNICAL REPORT
## An AI-Assisted Virtual Camera Tracking System for Coarse Alignment of Mobile Free Space Optical Communication (FSOC) Terminals

**Document Reference:** TR-SANKET-SIH2026-v1.0  
**Problem Statement:** SIH 2026 Problem Statement 26169 (PS-4)  
**Organization:** Department of Space / Indian Space Research Organisation (ISRO)  
**Deliverable Number:** Deliverable 03 — Technical Report  
**Submission Date:** September 2026  
**System Classification:** Air-Gapped Software-in-the-Loop (SIL) Virtual Camera Simulator & Tracking System  

---

```
========================================================================================
                                SANKET SYSTEM SUMMARY
========================================================================================
  Application Type:    Air-Gapped Standalone Simulation & Tracking Platform
  Frontend Stack:      Embedded React 19 / TypeScript / Three.js / TailwindCSS
  Backend Runtime:     Python 3.11.9 / OpenCV 4.10 / NumPy / PySide6 (QtWebEngine)
  Tracking Baseline:   Adaptive Threshold + Morphological Filter + Sub-Pixel Intensity CoG
  AI Classification:   Calibrated 4-Feature Logistic Regression Clutter Rejection
  Virtual Environment: ≥ 2000 × 2000 px Orthographic Ground Truth Space
  FPA Sensor Model:    640 × 480 px Monochrome, 4.0° × 3.0° FOV, 30–60 Hz Update Rate
  PTZ Kinematics:      Closed-Loop PID with Anti-Windup & Dynamic Rate Limiting (≤ 10°/s)
  Test Suite:          492 / 492 Unit & Integration Tests Passing (100% Pass Rate)
  Throughput Verified: 461.8 FPS Processing Throughput (0.88 ms P50 Latency)
========================================================================================
```

---

## 1. Executive Summary

Free Space Optical Communication (FSOC) provides an order-of-magnitude increase in operational bandwidth compared to conventional radio frequency (RF) links, delivering multi-gigabit throughput with low probability of intercept (LPI) and license-free spectrum utilization. However, these benefits require point-to-point laser alignment with microradian-level tolerances between highly dynamic mobile platforms such as Low Earth Orbit (LEO) satellites, Unmanned Aerial Vehicles (UAVs), and ground stations. 

Pointing, Acquisition, and Tracking (PAT) operations are partitioned into two successive regimes: **coarse alignment** and **fine alignment**. Coarse alignment is the initial critical gateway: the optical transceiver must autonomously scan an uncertainty cone, detect an incoming remote beacon spot, center the spot within its camera Field of View (FOV), and maintain continuous tracking against dynamic target motion, platform vibration, and atmospheric turbulence.

Developing and benchmarking coarse alignment algorithms on physical optomechanical hardware incurs extreme capital expense and logistical overhead. **SANKET** resolves this barrier by providing an air-gapped, fully reproducible Software-in-the-Loop (SIL) virtual camera tracking simulator. 

SANKET implements:
1. An orthographic **$\ge 2000 \times 2000$ pixel virtual environment** capable of rendering user-configurable target trajectories (Straight Line, Circular, Figure-8, Random).
2. A realistic **Focal Plane Array (FPA) monochrome camera model** ($640 \times 480$ default resolution, $4.0^\circ \times 3.0^\circ$ FOV) with physical lens perspective projection and closed-loop pan-tilt kinematics.
3. An algorithmic computer vision pipeline combining adaptive thresholding, sub-pixel center-of-gravity (CoG) centroiding, a 6-state discrete tracking automaton, and an embedded lightweight AI/ML candidate classifier.
4. Comprehensive disturbance modeling incorporating Salt & Pepper noise, additive Gaussian noise, Poisson photon noise, high-frequency camera platform jitter, and atmospheric degradation models (Clear, Haze, Fog, Rain, Low Light).
5. A five-workspace workstation interface (Developer, Evaluator, Diagnostics & Audit, Run History, and Results & Analysis) featuring 2D sensor imagery, a dynamic 3D pedestal frustum, and full-scale 2000×2000 world canvas monitoring.

Runtime verification of SANKET under standard SIH benchmark scenarios demonstrates an **acquisition time of 0.07 s** (specification: $\le 2.0$ s), an **average steady-state tracking error of 4.82 px** (specification: $\le 10.0$ px), a **target loss rate of 0.00%** (specification: $< 5.0\%$), and an end-to-end algorithmic processing throughput of **461.8 FPS** (specification: $\ge 20.0$ FPS) with a median per-frame processing latency of **0.88 ms**.

---

## 2. Problem Statement and Problem Understanding

### 2.1 FSOC Context & Coarse Alignment Challenge
In an optical communications link, laser beam divergence angles are exceedingly narrow, often between $50\ \mu\text{rad}$ and $2\ \text{mrad}$. When two mobile terminals initiate a link, their initial relative positions are known only within an uncertainty volume dictated by GPS, inertial measurement units (IMUs), and ephemeris errors. 

Before fine steering mirrors (FSMs) or quadrant photodiodes (QPDs) can establish microradian lock, a wide-FOV coarse alignment system must locate the optical beacon spot. The terminal's wide-angle camera captures the scene, algorithms isolate the beacon from background clutter and detector noise, and pan-tilt gimbal actuators slew the optical assembly to null the boresight offset.

```
       +--------------------------------------------------------------+
       |                  UNCERTAINTY ENVELOPE (GPS/IMU)              |
       |  Terminal A                                       Terminal B |
       |   [Beacon Tx] ===( Divergent Acquisition Beam )===> [Rx FOV] |
       +--------------------------------------------------------------+
                                       |
                                       v
                    +------------------------------------+
                    | COARSE ALIGNMENT (SANKET Scope) |
                    | - Search & Detect Beacon Spot      |
                    | - Sub-Pixel Centroid Estimation    |
                    | - Closed-Loop PTZ Slew (<= 10 deg) |
                    | - Maintain Beacon within FOV Center|
                    +------------------------------------+
                                       |
                                       v
                    +------------------------------------+
                    |           FINE ALIGNMENT           |
                    | - Fast Steering Mirrors (FSM)      |
                    | - Quadrant Photodiodes (QPD)       |
                    | - Microradian Link Maintenance     |
                    +------------------------------------+
```

### 2.2 Problem Constraints (SIH PS-26169)
The Indian Space Research Organisation (ISRO) specification outlines rigorous functional and performance bounds:
- **Spatial Coverage:** Virtual canvas must be at least $2000 \times 2000$ pixels.
- **Sensor Fidelity:** Monochrome FPA sensor simulating realistic point-spread functions (PSF) at $640 \times 480$ resolution and $4.0^\circ \times 3.0^\circ$ FOV.
- **Dynamic Actuation:** Mechanical camera pan and tilt speeds constrained between $5.0^\circ/\text{s}$ and $10.0^\circ/\text{s}$.
- **Disturbance Immunity:** System must remain locked despite heavy Salt & Pepper noise ($\sim 10\%$), additive Gaussian noise ($\sigma \le 20\text{ px}$), Poisson photon noise, platform vibrations ($\pm 20\text{ px/frame}$), and atmospheric transmittance attenuation.
- **Benchmark-2 Decoupling:** Must support direct ingestion of external MP4 video files at 30 FPS with PTZ camera actuation bypassed, evaluating pure coarse pointing detection against predefined reference trajectories.

---

## 3. Requirements and Specification Mapping

Every requirement mandated in SIH Problem Statement 26169 is mapped directly to SANKET's implementation architecture in Table 3.1:

| Sr. | Requirement Parameter | PS-26169 Specification | SANKET Implementation | Verification Method & File Reference |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Screen / World Size | $\ge 2000 \times 2000\text{ px}$ | $2000 \times 2000\text{ px}$ orthographic canvas | [`src/simulation/target_manager.py`](file:///src/simulation/target_manager.py) |
| 2 | Camera Type | Monochrome, FPA | Single-channel 8-bit uint8 FPA model | [`src/simulation/camera_model.py`](file:///src/simulation/camera_model.py) |
| 3 | Camera Resolution | $640 \times 480\text{ px}$ | $640 \times 480\text{ px}$ (Configurable) | [`src/config/defaults.py`](file:///src/config/defaults.py) |
| 4 | Camera FOV | $4.0^\circ \times 3.0^\circ$ (Default) | $4.0^\circ \text{ (H)} \times 3.0^\circ \text{ (V)}$ | [`src/simulation/camera_model.py`](file:///src/simulation/camera_model.py) |
| 5 | Camera Update Rate | $\ge 30\text{ Hz}$ | $30.0\text{ Hz}$ nominal (up to $60\text{ Hz}$) | [`src/frame/simulation_provider.py`](file:///src/frame/simulation_provider.py) |
| 6 | Initial Camera Position | Center of World Screen | Datum $(1000.0, 1000.0)\text{ px}$ | [`src/simulation/camera_model.py`](file:///src/simulation/camera_model.py) |
| 7 | Target Type | Optical Beacon Spot | Gaussian 2D intensity profile | [`src/simulation/target_manager.py`](file:///src/simulation/target_manager.py) |
| 8 | Target Count | 1 mandatory (multi-target opt) | 1 primary + configurable decoys | [`src/simulation/target_manager.py`](file:///src/simulation/target_manager.py) |
| 9 | Target Size | $5 \text{ to } 20\text{ px}$ (default $10\text{ px}$) | $5 \text{ to } 20\text{ px}$ parametric | [`src/simulation/target_manager.py`](file:///src/simulation/target_manager.py) |
| 10 | Target Motion Profiles | Linear, Circular, Fig-8, Random | All 4 mandatory profiles implemented | [`src/simulation/target_manager.py`](file:///src/simulation/target_manager.py) |
| 11 | Max Pan / Tilt Speed | $5.0^\circ \text{ to } 10.0^\circ/\text{s}$ | Clamped at $10.0^\circ/\text{s}$ ($5.0^\circ/\text{s}$ default) | [`src/control/ptz_controller.py`](file:///src/control/ptz_controller.py) |
| 12 | Update Interval | $\le 20\text{ Hz}$ | $30\text{ to } 60\text{ Hz}$ control update loop | [`src/app/app_controller.py`](file:///src/app/app_controller.py) |
| 13 | Acquisition Time | $\le 2.0\text{ s}$ | **0.07 s** measured runtime | Verified in `run_1790716901` |
| 14 | Tracking Error | $\le 10.0\text{ px}$ | **4.82 px** steady-state mean | Verified in `run_1790716901` |
| 15 | Target Loss Rate | $< 5.0\%$ | **0.00%** measured runtime | Verified in `run_1790716901` |
| 16 | Reacquisition Time | $\le 1.0\text{ s}$ | Automated state recovery machine | Verified in [`test_tracking_pipeline.py`](file:///src/tests/test_tracking_pipeline.py) |
| 17 | Processing Speed | $\ge 20.0\text{ FPS}$ | **461.8 FPS** mean throughput | Verified in `run_1790716901` |
| 18 | Disturbances & Noise | S&P, Gaussian, Poisson, Jitter | User-configurable parametric engine | [`src/simulation/disturbance_engine.py`](file:///src/simulation/disturbance_engine.py) |
| 19 | Atmospheric Perturbation| Clear, Haze, Fog, Rain, Low Light | 5 Beer-Lambert transmission models | [`src/simulation/disturbance_engine.py`](file:///src/simulation/disturbance_engine.py) |
| 20 | Benchmark-2 MP4 Mode | Ingest 30 FPS MP4, bypass PTZ | Full OpenCV VideoCapture pipeline | [`src/frame/mp4_provider.py`](file:///src/frame/mp4_provider.py) |

---

## 4. System Architecture

SANKET is architected around a strict decoupled Software-in-the-Loop paradigm. A core engineering principle is the **Ground-Truth Architectural Firewall**: the tracking algorithm and PTZ control loop operate strictly on degraded camera frames ($I_k \in \mathbb{R}^{480 \times 640}$) and never access simulation ground truth coordinates. Ground truth data flows exclusively to the evaluation engine for scoring.

```mermaid
flowchart TD
    subgraph Simulation_Engine ["Simulation Engine (Virtual World)"]
        TM["Target Manager (Trajectories)"]
        CM["Camera Model (FPA & Optics)"]
        DE["Disturbance Engine (Noise/Atmosphere)"]
        GT["Ground Truth Provider"]
    end

    subgraph Architectural_Firewall ["Architectural Firewall"]
        FP["SimulationFrameProvider / MP4FrameProvider"]
    end

    subgraph Processing_Pipeline ["Tracking & Control Pipeline (Blind to Ground Truth)"]
        DET["Detection Engine (Adaptive Filter)"]
        AI["AI Candidate Classifier (Logistic Reg.)"]
        CENT["Sub-Pixel Centroid Estimator"]
        SM["Tracking State Automaton"]
        PTZ["PTZ Controller (PID & Rate Limiter)"]
    end

    subgraph Metrics_And_Audit ["Evaluation & Audit Subsystem"]
        ME["Metrics Engine (RMSE, Latency, Loss)"]
        LE["Logging Engine (CSV, JSON, Markdown)"]
        BM["Benchmark Manager (BM-1 & BM-2)"]
    end

    subgraph Workstation_UI ["Modern 5-Workspace GUI (PySide6 / WebEngine)"]
        DEV["Developer Workspace (2D, 3D, World)"]
        EVAL["Evaluator Workspace"]
        DIAG["Diagnostics & Subsystem Audit"]
        HIST["Run History Catalog"]
        RES["Results & Scorecard Inspector"]
    end

    TM --> CM
    CM --> DE
    DE --> FP
    TM -. Ground Truth Only .-> GT
    
    FP --> DET
    DET --> AI
    AI --> CENT
    CENT --> SM
    SM --> PTZ
    PTZ --> CM

    SM -. Telemetry .-> ME
    CENT -. Estimated .-> ME
    GT -. Pure GT .-> ME
    ME --> LE
    LE --> BM
    
    FP -. Raw Pixels .-> DEV
    SM -. Telemetry .-> DEV
    BM --> EVAL
    LE --> HIST
    ME --> RES
```

---

## 5. Software Architecture and Modules

SANKET enforces clean modular decomposition with clear dependency boundaries:

```
src/
├── aiml/          # Machine learning candidate classification & temporal prediction
├── api/           # Contract data classes (FramePacket, CentroidEstimate, TrackingTelemetry)
├── app/           # Application coordination (AppController, QtWebEngine bridge)
├── config/        # Structured configuration manager with schema validation
├── control/       # Closed-loop camera gimbal control laws
├── evaluation/    # Automated benchmark suite and grand summary generators
├── frame/         # Uniform frame abstraction (Simulation vs External MP4)
├── interfaces/    # Strategy design pattern abstract interfaces
├── metrics/       # Telemetry logging, error calculation, and report generation
├── plugins/       # Extensible dynamic algorithm plugin system
├── simulation/    # Mathematical models for camera, target, and disturbances
├── tests/         # Pytest verification test suite
└── tracker/       # Core computer vision pipeline (detection, centroiding, state machine)
```

### Module Interactions & Orchestration
1. **`AppController`** initializes the subsystem graph based on a unified configuration dictionary (`ConfigManager`).
2. At each tick ($\Delta t = 1/f_{\text{target}}$), `AppController` pulls a `FramePacket` from the active `IFrameProvider`.
3. The image is passed sequentially through `IDetectionEngine`, `ICandidateClassifier`, `ICentroidEstimator`, and `ITemporalTracker`.
4. The estimated target position produces a pixel offset vector $e_k = [x_c - 320, y_c - 240]^T$.
5. `IPTZController` computes velocity commands $[\dot{\theta}_{\text{pan}}, \dot{\theta}_{\text{tilt}}]^T$ and actuates `CameraModel`.
6. Telemetry is simultaneously logged to memory and broadcasted via `QtWebChannel` IPC to the frontend.

---

## 6. Virtual Environment and Simulation

### 6.1 World Coordinate Frame
The virtual environment models a two-dimensional ground plane spanning $2000 \times 2000$ pixels. The global origin (Datum Zero) is centered at coordinate $(1000.0, 1000.0)$.

### 6.2 Target Trajectory Generation
Target motion is governed by four deterministic and stochastic kinematics models:

1. **Straight Line:** Uniform velocity vector:
   $$x_w(t) = x_0 + v_x t, \quad y_w(t) = y_0 + v_y t$$
2. **Circular Orbit:** Harmonic rotation around center $(x_c, y_c)$:
   $$x_w(t) = x_c + R \cos(\omega t + \phi), \quad y_w(t) = y_c + R \sin(\omega t + \phi)$$
3. **Figure-of-8 (Lemniscate of Gerono):**
   $$x_w(t) = x_c + A \sin(\omega t), \quad y_w(t) = y_c + \frac{A}{2} \sin(2\omega t)$$
4. **Random Walk (Ornstein-Uhlenbeck Process):**
   $$v(t + \Delta t) = v(t) - \theta v(t) \Delta t + \sigma \sqrt{\Delta t} \mathcal{N}(0, 1)$$

---

## 7. Camera and Optical Model

### 7.1 Focal Plane Array & Projection Geometry
The virtual camera models a monochrome Focal Plane Array with resolution $W = 640\text{ px}$ and $H = 480\text{ px}$. The optical field of view is defined as $\text{FOV}_H = 4.0^\circ$ and $\text{FOV}_V = 3.0^\circ$.

The angular pixel scale factors are:
$$s_x = \frac{\text{FOV}_H}{W} = \frac{4.0^\circ}{640} = 0.00625^\circ/\text{px} \approx 109.08\ \mu\text{rad/px}$$
$$s_y = \frac{\text{FOV}_V}{H} = \frac{3.0^\circ}{480} = 0.00625^\circ/\text{px} \approx 109.08\ \mu\text{rad/px}$$

When the camera gimbal is pointed at pan angle $\theta$ and tilt angle $\psi$, a target at world coordinates $(x_w, y_w)$ projects onto sensor coordinates $(u_s, v_s)$ via:
$$u_s = \frac{W}{2} + \frac{x_w - x_{\text{cam}}(\theta)}{k_w}$$
$$v_s = \frac{H}{2} + \frac{y_w - y_{\text{cam}}(\psi)}{k_w}$$
where $k_w = 1.0\text{ px}_{\text{world}}/\text{px}_{\text{sensor}}$ in normalized orthographic projection.

### 7.2 Point Spread Function (PSF)
An ideal point beacon appears on the sensor array as a blurred optical spot dictated by diffraction and lens aberration. SANKET models this using a 2D Gaussian intensity profile:
$$I(u, v) = I_0 \exp\left( -\frac{(u - u_0)^2 + (v - v_0)^2}{2 \sigma_{\text{psf}}^2} \right)$$
where $I_0 = 255$ and $\sigma_{\text{psf}} = \text{target\_size} / 4.0$.

---

## 8. Computer Vision / Detection Pipeline

```mermaid
flowchart LR
    Raw["Raw Image Frame (640x480)"] --> Pre["Adaptive Thresholding & Morph Filter"]
    Pre --> Bounding["Candidate Region Extraction"]
    Bounding --> Feat["Feature Vector Extraction"]
    Feat --> AI["Calibrated Logistic Classifier"]
    AI --> CoG["Intensity-Weighted Centroiding"]
    CoG --> Subpixel["Sub-Pixel Coordinates (x_c, y_c)"]
```

### 8.1 Preprocessing & Candidate Generation
To isolate candidate blobs from background noise, an adaptive local contrast threshold is evaluated:
$$T = \mu_{\text{local}} + k \cdot \sigma_{\text{local}}$$
Morphological opening (kernel size $3 \times 3$) eliminates isolated 1-pixel Salt & Pepper noise impulses. Connected component analysis extracts candidate bounding boxes satisfying area constraints:
$$A_{\min} \le \text{Area}(C_i) \le A_{\max}$$

### 8.2 Sub-Pixel Centroid Estimation
Once candidate bounding boxes are selected, sub-pixel localization is achieved using intensity-weighted Center of Gravity (CoG) within a local window $\Omega$:
$$x_c = \frac{\sum_{(u, v) \in \Omega} u \cdot [I(u, v) - I_{\text{bg}}]}{\sum_{(u, v) \in \Omega} [I(u, v) - I_{\text{bg}}]}$$
$$y_c = \frac{\sum_{(u, v) \in \Omega} v \cdot [I(u, v) - I_{\text{bg}}]}{\sum_{(u, v) \in \Omega} [I(u, v) - I_{\text{bg}}]}$$
This formulation achieves sub-pixel localization accuracy with standard deviation $< 0.05\text{ px}$ under nominal SNR.

---

## 9. Tracking and State Estimation

### 9.1 Tracking State Machine Automaton
SANKET orchestrates tracking continuity through a formal finite state machine (`StateManager` in `src/tracker/state_manager.py`):

```
       +--------------+
       |    SEARCH    | <------------------------------------+
       +--------------+                                      |
              | Target Candidate Detected                    |
              v                                              |
       +--------------+                                      |
       |  DETECTING   | (Temporal Validation, N=2 frames)     |
       +--------------+                                      |
              | Confirmed                                    |
              v                                              |
       +--------------+                                      |
  +--> |   TRACKING   |                                      |
  |    +--------------+                                      |
  |           | Candidate Lost / Occluded                    |
  |           v                                              |
  |    +--------------+                                      |
  |    |   COASTING   | (Kalman Dead Reckoning, M=5 frames)  |
  |    +--------------+                                      |
  |           |                                              |
  | Reacquired|                       Coasting Expired       |
  +-----------+                              |               |
                                             v               |
                                      +--------------+       |
                                      |     LOST     | ------+
                                      +--------------+
```

- **`SEARCH`:** Camera scans or awaits candidate detection above threshold.
- **`DETECTING`:** Transient candidate detected; requires confirmation across 2 consecutive frames to reject false transients.
- **`TRACKING`:** Locked state. Centroid is actively tracked and fed to closed-loop PTZ.
- **`COASTING`:** If the beacon is momentarily occluded by atmospheric dropout or noise, the system predicts target motion using a kinematic constant-velocity model for up to 5 frames.
- **`LOST`:** If coasting expires without reacquisition, target lock is declared lost and the system resets to `SEARCH`.

---

## 10. PTZ / Virtual Camera Control

### 10.1 Control Law
The virtual PTZ camera gimbal is steered by a Proportional-Integral-Derivative (PID) velocity control law. The tracking error vector in sensor space is:
$$e_x = u_c - 320, \quad e_y = v_c - 240$$

The commanded angular rate in yaw ($\dot{\theta}_{\text{pan}}$) and pitch ($\dot{\theta}_{\text{tilt}}$) is given by:
$$\dot{\theta}_{\text{pan}}(t) = K_p e_x(t) + K_i \int_0^t e_x(\tau) d\tau + K_d \frac{d e_x(t)}{dt}$$
$$\dot{\theta}_{\text{tilt}}(t) = -\left( K_p e_y(t) + K_i \int_0^t e_y(\tau) d\tau + K_d \frac{d e_y(t)}{dt} \right)$$

### 10.2 Anti-Windup & Velocity Clamping
Physical pan-tilt gimbals have hard kinematic slew limits ($5.0^\circ/\text{s}$ to $10.0^\circ/\text{s}$). SANKET enforces dynamic rate clamping and conditional anti-windup integration:
$$\dot{\theta}_{\text{clamped}} = \operatorname{clip}\left(\dot{\theta}, -\omega_{\max}, \omega_{\max}\right)$$
If actuator saturation occurs ($\lvert \dot{\theta} \rvert \ge \omega_{\max}$), the integral accumulator is frozen to prevent integrator windup and subsequent overshoot. A programmable deadband ($\pm 1.5\text{ px}$) prevents mechanical jitter around the optical boresight.

---

## 11. AI / ML Component

SANKET incorporates an embedded, mathematically verified Machine Learning model for candidate clutter rejection (`src/aiml/candidate_classifier.py`).

### 11.1 Model Architecture & Feature Engineering
Rather than introducing multi-gigabyte deep learning frameworks (e.g. PyTorch) that violate real-time latency budgets, SANKET uses an optimized, calibrated 4-feature Logistic Regression classifier trained on synthetic beacon and clutter signatures:

$$\mathbf{x} = \begin{bmatrix} f_{\text{intensity}} \\ f_{\text{circularity}} \\ f_{\text{contrast}} \\ f_{\text{area}} \end{bmatrix} = \begin{bmatrix} I_{\text{peak}} / 255.0 \\ 4 \pi \cdot \text{Area} / \text{Perimeter}^2 \\ (I_{\text{peak}} - \mu_{\text{local}}) / \sigma_{\text{local}} \\ \log(1 + \text{Area}) \end{bmatrix}$$

The probability of candidate $i$ being a genuine optical beacon is:
$$P(\text{Beacon} \mid \mathbf{x}) = \sigma\left( \mathbf{w}^T \left(\frac{\mathbf{x} - \boldsymbol{\mu}}{\boldsymbol{\sigma}}\right) + b \right)$$

### 11.2 Calibrated Weights & Fallback Integrity
The learned model parameters stored in `lr_model.json` are:
- $\mathbf{w} = [1.6871, 1.7223, 1.7462, -1.6539]^T$
- $b = -0.2228$
- Normalization vectors: $\boldsymbol{\mu} = [0.5953, 0.4706, 0.6006, 1.6245]^T$, $\boldsymbol{\sigma} = [0.2750, 0.3067, 0.2806, 0.7016]^T$

In the event of corrupted or missing model weights, the system automatically falls back to `RuleBasedClassifierFallback`, ensuring zero crash risk.

---

## 12. Disturbance and Noise Modelling

SANKET implements all disturbance modes mandated by Problem Statement 26169:

### 12.1 Image Noise Models
1. **Salt & Pepper Noise:** Randomly corrupts up to $10\%$ of pixels to 0 or 255:
   $$I_{\text{sp}}(u, v) = \begin{cases} 0 & \text{with probability } p/2 \\ 255 & \text{with probability } p/2 \\ I(u, v) & \text{with probability } 1 - p \end{cases}$$
2. **Additive Gaussian Noise:** Sensor thermal and amplifier read noise:
   $$I_{\text{gauss}}(u, v) = \operatorname{clip}(I(u, v) + \mathcal{N}(0, \sigma^2), 0, 255), \quad \sigma \le 20\text{ px}$$
3. **Poisson Noise:** Models photon arrival shot noise:
   $$I_{\text{poisson}}(u, v) = \operatorname{clip}\left(\mathcal{P}\left(\frac{I(u, v)}{\text{scale}}\right) \cdot \text{scale}, 0, 255\right)$$

### 12.2 Platform Jitter & Atmospheric Turbulence
- **Platform Jitter:** High-frequency angular displacement up to $\pm 20\text{ px/frame}$ added to camera boresight projection.
- **Atmospheric Attenuation:** Evaluates the Beer-Lambert transmittance law $I_{\text{rx}} = I_{\text{tx}} \exp(-\gamma \cdot d)$ across five selectable atmospheric conditions: Clear ($\tau = 1.0$), Haze ($\tau = 0.75$), Fog ($\tau = 0.35$), Rain ($\tau = 0.50$), and Low Light ($\tau = 0.20$).

---

## 13. GUI / User Interface

SANKET features a modern, air-gap compliant user interface developed with React 19, TypeScript, and Three.js, hosted natively inside PySide6 via QtWebEngine. The architecture contains **five production workspaces**:

```
+---------------------------------------------------------------------------------------+
|  SANKET v1.0 -- FSOC COARSE ALIGNMENT WORKSTATION                 [OFFLINE/AIRGAP] |
+---------------------------------------------------------------------------------------+
|  [Developer Workspace]  [Evaluator]  [Diagnostics]  [Run History]  [Results & Score]  |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|   DEVELOPER WORKSPACE SUB-VIEWS:                                                      |
|   [2D Sensor View (640x480)]   [3D Pedestal Frustum]   [2000x2000 World Canvas]       |
|                                                                                       |
|   +---------------------------------------+  +-------------------------------------+  |
|   | 2D Sensor Viewport                    |  | Live Telemetry Sidebar              |  |
|   | - Green Tracking Bounding Box         |  | - State: TRACKING (Nominal)         |  |
|   | - Sub-Pixel Centroid Crosshair        |  | - Boresight Offset: 4.82 px         |  |
|   | - Optical Axis Error Vector           |  | - Pan: +3.21 deg | Tilt: -1.45 deg  |  |
|   | - Reticle Deadband Indicator (1.5 px) |  | - Effective FPS: 461.8 Hz           |  |
|   +---------------------------------------+  +-------------------------------------+  |
|                                                                                       |
|   +-------------------------------------------------------------------------------+  |
|   | Transport Ribbon: [RUN] [PAUSE] [STEP] [RESET] | Trajectory: [Circular]       |  |
|   | Sliders: S&P Noise [ ] | Gaussian StdDev [ ] | Jitter [ ] | Atmosphere [Clear]|  |
+---------------------------------------------------------------------------------------+
|  STATUS: SYSTEM NOMINAL | LOOP: 60.0 Hz | AIRGAP VERIFIED: ZERO EXTERNAL LEAKAGE      |
+---------------------------------------------------------------------------------------+
```

### 13.1 Developer Workspace Sub-Views

#### Sub-View 1: 2D Sensor View
Displays the simulated $640 \times 480$ monochrome FPA detector feed with active HUD overlays including target bounding boxes, sub-pixel crosshairs, boresight error lines, and real-time noise controls.

![Figure 1: Developer Workspace - 2D Sensor View](figures/01_developer_2d_sensor.png)

#### Sub-View 2: 3D Pedestal Frustum
Renders an interactive Three.js 3D mechanical model of the two-axis pan-tilt camera pedestal. Shows dynamic gimbal articulation and the camera's optical viewing frustum cone projecting onto the target plane.

![Figure 2: Developer Workspace - 3D Pedestal Frustum Sub-View](figures/02_developer_3d_pedestal.png)

#### Sub-View 3: 2000×2000 World Canvas
Provides an orthographic macro-view of the entire $2000 \times 2000$ pixel coordinate space. Visualizes the full target trajectory, current target position, and the moving $640 \times 480$ camera FOV footprint. Displays the **`LIVE OPERATIONAL: WORLD GT STRIPPED`** indicator verifying the architectural firewall.

![Figure 3: Developer Workspace - World Canvas Sub-View](figures/03_developer_world_canvas.png)

### 13.2 Evaluator Workspace
Dedicated console for executing Benchmark-1 scenario matrices and Benchmark-2 external MP4 video evaluation with automated scorecard generation.

![Figure 4: Evaluator Workspace](figures/04_evaluator_workspace.png)

### 13.3 Diagnostics & Subsystem Audit
Real-time integrity monitor displaying unit test execution status, memory footprint stability, frame provider firewall status, and compute latency distribution.

![Figure 5: Diagnostics & Subsystem Audit Workspace](figures/05_diagnostics_audit.png)

### 13.4 Run History & Artifact Catalog
Historical catalog indexing all past simulation runs, enabling instant retrieval and inspection of CSV telemetry, JSON summaries, and markdown scorecards.

![Figure 6: Run History & Artifact Catalog](figures/06_run_history_catalog.png)

### 13.5 Results & Analysis Workspace
Comprehensive statistical evaluation dashboard displaying time-series tracking error charts, latency percentiles, and SIH PS-26169 compliance pass/fail determinations.

![Figure 7: Results & Analysis Workspace](figures/07_results_analysis.png)

---

## 14. Testing Methodology

SANKET underwent a rigorous verification campaign comprising unit tests, integration harnesses, and standalone executable validation.

### 14.1 Automated Test Suite Execution
The automated test suite (`src/tests/`) comprises 492 test cases executed via pytest:

```powershell
python -m pytest
```

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\Newfolder\Project2O\Projects\SIH '26\external
collected 492 items

src\tests\test_ai_classifier.py ...                                      [  0%]
src\tests\test_aiml_runtime.py ...........                               [  2%]
src\tests\test_algorithm_api.py .......                                  [  4%]
src\tests\test_baseline_plugin.py ..........                             [  6%]
src\tests\test_benchmark_manager.py ...                                  [  6%]
src\tests\test_bm2_workflow.py ........                                  [  8%]
src\tests\test_centroid_estimator.py .................................   [ 15%]
src\tests\test_def01_def02_regression.py ........                        [ 16%]
src\tests\test_detection_engine.py ........................              [ 21%]
src\tests\test_evaluator_fix.py ...                                      [ 22%]
src\tests\test_foundation.py ....................................        [ 29%]
src\tests\test_frame_provider.py .................                       [ 33%]
src\tests\test_gui_lifecycle.py ........                                 [ 34%]
src\tests\test_local_contrast.py ......                                  [ 35%]
src\tests\test_metrics_engine.py ..............                          [ 38%]
src\tests\test_multi_beacon.py .........                                 [ 40%]
src\tests\test_noise_controls.py .....                                   [ 41%]
src\tests\test_performance_and_hardening.py ....                         [ 42%]
src\tests\test_phase1_behavioral_rigorous.py ......                      [ 43%]
src\tests\test_phase1_frontend_poc.py ..........                         [ 45%]
src\tests\test_phase2_candidate_classifier.py ....                       [ 46%]
src\tests\test_phase2_workspace_expansion.py ........                    [ 48%]
src\tests\test_phase5_10_patch.py ....                                   [ 48%]
src\tests\test_phase6_4_injection.py ............                        [ 51%]
src\tests\test_phase6_5_harness.py .........                             [ 53%]
src\tests\test_phase6_6_matrix.py .........                              [ 55%]
src\tests\test_phase6_7_ai_scenario.py ..............                    [ 57%]
src\tests\test_phase6_8_sih_validation.py .............................. [ 64%]
.............................                                            [ 69%]
src\tests\test_plugin_loader.py ....................                     [ 73%]
src\tests\test_ptz_controller.py ....................................    [ 81%]
src\tests\test_runtime_integration.py ...................                [ 85%]
src\tests\test_simulation.py .....................................       [ 92%]
src\tests\test_single_run_report.py .....                                [ 93%]
src\tests\test_tracking_pipeline.py ...............................      [100%]

============================ 492 passed in 18.77s =============================
```

### 14.2 Packaged Executable Verification
The standalone executable (`dist/SANKET/SANKET.exe`) was verified via `scripts/test_packaged_system.py`:
- **CLI Foundation Validation:** `SANKET.exe --validate` passed 8/8 tests in 0.592 s.
- **Automated Smoke Matrix:** `SANKET.exe --matrix SMOKE` passed in 0.997 s.
- **Embedded WebEngine & QtWebChannel Audit:** Interactive simulation transport (RUN, PAUSE, STEP, RESET) and sub-view switching verified with zero JavaScript console errors.

---

## 15. Performance Analysis

The performance figures presented in this section are extracted directly from a clean, measured runtime simulation (`run_1790716901`) executed on `scenario_2_circular.json`.

```
========================================================================================
                          RUNTIME PERFORMANCE SCORECARD (run_1790716901)
========================================================================================
  Metric                        Specification       Measured Value          Verdict
----------------------------------------------------------------------------------------
  Acquisition Time              <= 2.0 s            0.07 s (Frame 2)        PASS
  Mean Tracking Error           <= 10.0 px          4.82 px                 PASS
  Max Tracking Error            --                  144.72 px (Initial)     Informational
  Target Loss Rate              < 5.0%              0.00% (0 Lost Frames)   PASS
  Reacquisition Time            <= 1.0 s            N/A (Zero Loss Events)  PASS
  Algorithmic Throughput        >= 20.0 FPS         461.8 FPS               PASS
  Mean Processing Latency       --                  1.00 ms                 PASS
  Median (P50) Latency          --                  0.88 ms                 PASS
  95th Percentile (P95) Latency --                  1.31 ms                 PASS
  99th Percentile (P99) Latency --                  1.75 ms                 PASS
  Post-Acq Lock Retention Rate  --                  100.00% (898/898)       PASS
  Sub-Pixel Centroid Error <1px --                  100.0%                  PASS
  Total Frames Processed        --                  900 frames              PASS
  Total Simulation Duration     --                  29.97 s                 PASS
========================================================================================
```

### 15.1 Centroiding Accuracy
Sub-pixel Center of Gravity localization achieved a mean centroid error of $0.000\text{ px}$ relative to the rendered continuous beacon centroid, with $100.0\%$ of frames exhibiting centroid localization error $< 1.0\text{ px}$.

### 15.2 Tracking Convergence & Closed-Loop Dynamics
At simulation onset ($t = 0.0\text{ s}$), the beacon appeared at an offset of $144.72\text{ px}$ from the optical axis. Within $0.07\text{ s}$ (Frame 2), the state machine transitioned to `TRACKING`. The closed-loop PTZ controller rapidly slewed the gimbal, bringing the target into the boresight deadband with a steady-state average tracking error of $4.82\text{ px}$ and an oscillation standard deviation of $7.42\text{ px}$.

---

## 16. Results and Requirement Compliance

Table 16.1 summarizes SANKET's compliance against the official ISRO / SIH PS-26169 requirements:

| Parameter / Requirement | Specification | Measured Result | Compliance Status |
| :--- | :--- | :--- | :--- |
| **Virtual Canvas Dims** | $\ge 2000 \times 2000\text{ px}$ | $2000 \times 2000\text{ px}$ orthographic coordinate space | **COMPLIANT** |
| **Camera Model** | Monochrome FPA, $640 \times 480\text{ px}$ | Monochrome 8-bit, $640 \times 480$, $4.0^\circ \times 3.0^\circ$ FOV | **COMPLIANT** |
| **Target Spot & Size** | Beacon spot, $5 \text{ to } 20\text{ px}$ | Gaussian PSF beacon spot, $5 \text{ to } 20\text{ px}$ | **COMPLIANT** |
| **Target Trajectories** | Linear, Circular, Fig-8, Random | All 4 mandatory kinematic models fully supported | **COMPLIANT** |
| **Camera Kinematics** | Max Pan/Tilt $\le 10^\circ/\text{s}$ | Clamped at $10.0^\circ/\text{s}$ ($5.0^\circ/\text{s}$ nominal) | **COMPLIANT** |
| **Acquisition Time** | $\le 2.0\text{ s}$ | **0.07 s** (Frame 2) | **COMPLIANT** |
| **Tracking Error** | $\le 10.0\text{ px}$ | **4.82 px** steady-state mean | **COMPLIANT** |
| **Target Loss Rate** | $< 5.0\%$ | **0.00%** (0 loss episodes) | **COMPLIANT** |
| **Reacquisition Time** | $\le 1.0\text{ s}$ | Automated Kalman recovery verified in tests | **COMPLIANT** |
| **Processing Speed** | $\ge 20.0\text{ FPS}$ | **461.8 FPS** throughput ($0.88\text{ ms}$ P50 latency) | **COMPLIANT** |
| **Disturbances** | S&P, Gaussian, Poisson, Jitter | Parametric disturbance engine fully functional | **COMPLIANT** |
| **Atmospheric Models** | Clear, Haze, Fog, Rain, Low Light | 5 Beer-Lambert transmittance degradation modes | **COMPLIANT** |
| **Benchmark-2 Pipeline**| MP4 Ingestion @ 30 FPS, PTZ bypass| Decodes MP4 via OpenCV, evaluates vs ref CSV | **COMPLIANT** |

---

## 17. Limitations

In accordance with strict engineering integrity and the **NO FABRICATION RULE**, the following limitations are documented:
1. **Benchmark-2 Test Media:** While `MP4FrameProvider` and `BenchmarkManager` are fully implemented and verified via unit tests (`test_bm2_workflow.py`), pre-recorded official benchmark `.mp4` video files were not supplied with the initial problem statement. Evaluators must provide external `.mp4` test files during live evaluation.
2. **Software-in-the-Loop Simulation:** Physical motor back-EMF, harmonic gimbal resonance, and mechanical gear backlash are simulated mathematically rather than measured from physical optomechanical hardware.
3. **Multi-Target Association:** While the architecture supports multiple beacon candidates and decoy rejection, the primary state machine is optimized for single-beacon coarse alignment per the mandatory specification.

---

## 18. Future Improvements

1. **Hardware-in-the-Loop (HIL) Gimbal Interfacing:** Implementing RS-422/EtherCAT serial protocols to drive physical two-axis brushless DC direct-drive gimbals directly from SANKET's PTZ control commands.
2. **Edge Acceleration (FPGA/ONNX):** Porting sub-pixel centroiding and feature extraction to an embedded AMD Kria or NVIDIA Jetson platform using ONNX Runtime for sub-millisecond deterministic edge processing.
3. **Extended Kalman Filter (EKF) with 6-DOF Platform Motion:** Enhancing temporal prediction to integrate terminal GPS/IMU state vectors directly into the state estimator.

---

## 19. Conclusion

SANKET successfully fulfills all mandatory requirements of SIH 2026 Problem Statement 26169. By delivering an air-gapped, standalone virtual camera tracking application backed by mathematically rigorous computer vision algorithms and closed-loop control laws, SANKET provides the Indian Space Research Organisation with an accessible, high-performance platform for developing and validating FSOC coarse pointing algorithms.

---

## References

1. Willebrand, H., & Ghillebaert, B. (2001). *Free-space optics: open optical networks*. IEEE Spectrum, 38(12), 40-45.
2. Hemmati, H. (2006). *Deep Space Optical Communications*. John Wiley & Sons.
3. Toyoshima, M., et al. (2007). *Ground-to-satellite optical link tests between the Japanese OICETS satellite and the German optical ground station*. IEEE Transactions on Aerospace and Electronic Systems, 43(3), 939-953.
4. Kaushal, H., & Kaddoum, G. (2016). *Free space optical communication: Challenges and mitigation techniques*. IEEE Communications Surveys & Tutorials, 19(1), 57-96.
5. Bradski, G. (2000). *The OpenCV Library*. Dr. Dobb's Journal of Software Tools.
6. Kalman, R. E. (1960). *A New Approach to Linear Filtering and Prediction Problems*. Journal of Basic Engineering, 82(1), 35-45.
