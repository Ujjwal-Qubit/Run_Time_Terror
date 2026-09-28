# SIH 26169 — Critical Missing Capabilities Audit

**Document ID**: `AUDIT-11-MISSING-CAPABILITIES`  
**Target Repository**: `Ujjwal-Qubit/Run_Time_Error` (SIH 26169 Coarse Alignment FSOC)  
**Status**: COMPLETE / FORENSIC VERIFIED  
**Auditor**: Antigravity First-Principles Reconnaissance

---

## 1. Executive Summary

To transition the system from a synthetic Python toy demonstration to a viable, flight-grade coarse pointing, acquisition, and tracking (PAT) solution for Free Space Optical Communications (FSOC), ten fundamental capabilities must be developed. None of these ten capabilities exist in the current codebase.

---

## 2. Exhaustive Inventory of Missing Capabilities

### 2.1 Capability M1: Systematic Uncertainty Cone Acquisition Scan
- **The Gap**: When the optical beacon is outside the camera FOV (due to ephemeris error, GPS drift, or platform attitude uncertainty of $\pm 2^\circ\text{ to }\pm 5^\circ$), `PTZController` commands zero movement.
- **Physical Requirement**:
  - The system must execute an automated scan pattern over the uncertainty cone:
    - **Archimedean / Fermat Spiral Scan**: Optimal for circular or spherical uncertainty regions.
    - **Lissajous / Raster Scan**: Optimal for rectangular uncertainty regions (e.g. UAV flight corridors).
  - Scan velocity must match camera integration time to avoid motion blur smearing the beacon energy below detection threshold.
  - Scan must immediately halt and trigger lock-on upon beacon threshold crossing.

### 2.2 Capability M2: Coarse-to-Fine PAT Handover Protocol
- **The Gap**: FSOC terminals utilize a two-stage or three-stage pointing hierarchy:
  1. *Coarse PAT* (Gimbal / PTZ): Field of View $\pm 10^\circ$, accuracy $\approx 0.1\text{--}1.0\text{ mrad}$, bandwidth $5\text{--}20\text{ Hz}$.
  2. *Fine PAT* (Fast Steering Mirror / FSM or Piezo Tip-Tilt): Field of View $\pm 0.5^\circ$, accuracy $\approx 1\text{--}5\text{ }\mu\text{rad}$, bandwidth $500\text{--}2000\text{ Hz}$.
  3. *Optical Communication Receiver* (Single Mode Fiber coupling $\approx 10\text{ }\mu\text{m}$ core).
- **Physical Requirement**:
  - The virtual camera tracker is strictly the *coarse* stage. It must export a standardized handover telemetry packet (angle, angular velocity, confidence metric, jitter covariance) to initiate the fine-pointing FSM spiral scan.
  - The current codebase treats coarse tracking as the terminal objective and has no concept of handover criteria.

### 2.3 Capability M3: First-Principles Atmospheric Wavefront Propagation
- **The Gap**: The current simulator applies a 2D Gaussian blur with kernel size proportional to scalar $C_n^2$, and additive white Gaussian noise (AWGN).
- **Physical Requirement**:
  - Atmospheric turbulence does **not** act as a static blur. It introduces phase distortions across the receiving aperture described by Kolmogorov or von Kármán power spectra:
    $$\Phi_n(\kappa) = 0.033 C_n^2 (\kappa^2 + \kappa_0^2)^{-11/6} e^{-\kappa^2 / \kappa_m^2}$$
  - **Beam Wander**: Random deflection of the beacon centroid governed by $\sigma_{\text{wander}}^2 \approx 2.42 C_n^2 L^3 D^{-1/3}$.
  - **Scintillation (Intensity Fluctuations)**: Log-normal or Gamma-Gamma distributed intensity fading, causing catastrophic dropouts where beacon flux drops below sensor dark noise for $10\text{--}50\text{ ms}$.
  - A realistic simulator must compute multi-phase screen Fourier transforms (Split-Step Beam Propagation Method) to validate tracker stability under deep fades.

### 2.4 Capability M4: Non-Gaussian Colored Disturbance & Micro-Vibration PSD
- **The Gap**: In `src/simulator/disturbances.py`, platform vibration is modeled as i.i.d. Gaussian noise ($\mu=0, \sigma$).
- **Physical Requirement**:
  - Spacecraft and aerial platforms exhibit structured vibration power spectral densities (PSD):
    - **Spacecraft**: Reaction Wheel Assembly (RWA) harmonics ($30\text{--}450\text{ Hz}$), solar array drive mechanism steps ($0.1\text{--}2\text{ Hz}$).
    - **UAVs**: Rotor blade passing frequency ($80\text{--}150\text{ Hz}$) and airframe aeroelastic flutter ($5\text{--}25\text{ Hz}$).
    - **Naval / Maritime**: Sea-state 4/5 wave motion (Pierson-Moskowitz or JONSWAP spectrum, $0.05\text{--}0.3\text{ Hz}$).
  - These disturbances are colored and periodic. The tracker must model them as autoregressive (AR) or state-space colored noise models to test filter rejection.

### 2.5 Capability M5: Kinematic Feedforward & Multi-Model State Estimation (IMM-EKF)
- **The Gap**: `KalmanTracker` uses a simple linear 2D constant-velocity (CV) model on pixel coordinates $(x, y)$.
- **Physical Requirement**:
  - The camera is mounted on a rotating gimbal on a moving base. The tracking coordinates are inherently non-linear spherical coordinates $(\text{Azimuth}, \text{Elevation}, \text{Range})$.
  - Target maneuvers switch between constant velocity, constant acceleration, and coordinated turns.
  - The system requires an **Interacting Multiple Model (IMM)** filter combining:
    1. Constant Velocity (CV) model for steady orbits / tracks.
    2. Constant Acceleration (CA) model for thruster burns / evasive maneuvers.
    3. Kinematic IMU feedforward to cancel out base platform motion before the optical feedback loop even perceives the error (strapdown inertial stabilization).

### 2.6 Capability M6: Synchronous Beacon Modulation & Lock-In Detection
- **The Gap**: Detection is purely spatial thresholding of pixel brightness. Any bright terrestrial light, headlight, or solar glint is captured as a candidate.
- **Physical Requirement**:
  - Physical FSOC beacons are pulsed or square-wave modulated at frequency $f_{\text{beacon}}$ (or synchronized with camera exposure strobing).
  - By performing frame-to-frame difference imaging ($I_{\text{on}} - I_{\text{off}}$) or multi-frequency FFT on pixel time-series, background clutter, clouds, and solar glints are rejected by $>40\text{ dB}$, isolating the laser beacon even when $SNR < 0\text{ dB}$.

### 2.7 Capability M7: Hardware Abstraction Layer (HAL) for Physical Gimbals
- **The Gap**: `PTZController` modifies internal floating-point variables `sim.pan, sim.tilt`. There is zero interface to control real-world motorized gimbals.
- **Physical Requirement**:
  - Real FSOC coarse gimbals communicate over RS-422/RS-485 serial, CAN bus, or Ethernet using industry protocols:
    - **Pelco-D / Pelco-P**: Standard pan/tilt positioning protocol.
    - **Sony VISCA**: High-precision PTZ optical protocol.
    - **Direct Servo/Stepper Drivers**: Step/Direction pulses or CANopen (DS402 profile) with micro-radian optical encoder feedback.
  - An asynchronous HAL with driver interfaces is required for physical deployment.

### 2.8 Capability M8: Production Edge-Optimized Deep Learning Detector
- **The Gap**: The project contains a 4-feature Logistic Regression and an unused 11-feature MLP trained on 30 synthetic data points.
- **Physical Requirement**:
  - When atmospheric turbulence shatters the beacon into an irregular, flickering speckle pattern (broken speckle cloud), classical thresholding fails.
  - An edge-optimized deep learning model (e.g. NanoTrack, MobileNetV4-S, or a lightweight 1D temporal CNN) trained on real turbulence speckle sequences is required to output robust centroid probability heatmaps.
  - Model must compile to **TensorRT / ONNX Runtime** targeting embedded GPUs (NVIDIA Jetson Orin Nano, $\le 5\text{ W}$, latency $\le 5\text{ ms}$).

### 2.9 Capability M9: PID Anti-Windup, Derivative Filtering & Lead-Lag Compensation
- **The Gap**: Simple proportional-integral-derivative control with no anti-windup clamping, no high-frequency derivative filtering, and no dead-band management.
- **Physical Requirement**:
  - Real gimbal motors have physical inertia, gear backlash, friction, and torque limits.
  - High-gain derivative terms amplify sensor centroid noise; derivative low-pass filtering is mandatory.
  - Back-calculation anti-windup is essential to prevent massive overshoot following track loss recovery.

### 2.10 Capability M10: Deterministic Headless Core & Low-Latency Pipeline
- **The Gap**: Pipeline is tethered to PySide6 Qt GUI or FastAPI WebSocket server, running on Windows with non-deterministic timer jitter.
- **Physical Requirement**:
  - A standalone, headless C++20 or Rust / Cython core daemon capable of running as a systemd service on Linux (Ubuntu RT / Jetpack).
  - Hard real-time execution guarantees: frame grab $\to$ sub-pixel centroid $\to$ state filter $\to$ motor command in $\le 8.0\text{ ms}$ at 100 Hz.
