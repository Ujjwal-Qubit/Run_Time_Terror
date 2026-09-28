# SIH 26169 — Assumption Prosecution & Epistemic Audit (`axiom`)

**Document ID**: `AUDIT-14-ASSUMPTIONS`  
**Target Repository**: `Ujjwal-Qubit/Run_Time_Error` (SIH 26169 Coarse Alignment FSOC)  
**Status**: COMPLETE / FORENSIC VERIFIED  
**Auditor**: Antigravity First-Principles Reconnaissance (`axiom` Framework)

---

## 1. Epistemic Classification Framework

Using the `axiom` skill methodology, every core assumption underpinning the architecture, algorithms, and validation of the SIH 26169 project is excavated and classified into one of four epistemic categories:
1. **Physical Fact (PF)**: Grounded in invariant laws of optics, kinematics, electromagnetism, or mathematics.
2. **Convention (C)**: Standard engineering practice or rule of thumb; alternatives exist and may be superior.
3. **Belief (B)**: Accepted as true without empirical proof or mathematical derivation in this context.
4. **Interest-Driven (ID)**: Motivated by development ease, hackathon demo appeal, time pressure, or checkbox compliance.

Each assumption is scored on:
- **Fragility ($1\text{--}5$)**: Likelihood of collapsing when exposed to operational real-world conditions ($1 = \text{bulletproof}, 5 = \text{collapses immediately}$).
- **Impact ($1\text{--}5$)**: Consequence to the FSOC mission if the assumption is violated ($1 = \text{negligible}, 5 = \text{catastrophic mission loss}$).
- **Risk Index**: $\text{Fragility} \times \text{Impact}$ (Scale $1\text{--}25$).

---

## 2. Exhaustive Assumption Register & Risk Scoring

| # | Assumption Description | Category | Fragility | Impact | Risk Index | Falsification / Physical Reality |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **A01** | The optical beacon is always inside the camera field of view ($640 \times 480$) at mission initialization. | **ID** | 5 | 5 | **25** | In real FSOC deployments, initial pointing uncertainty cones ($\pm 2^\circ\text{ to }\pm 10^\circ$) routinely exceed optical FOV. When violated, the system remains 100% frozen. |
| **A02** | A 4-feature Logistic Regression trained on 400 uniform random numbers satisfies the "AI-based tracking" requirement. | **ID** | 5 | 5 | **25** | Under real evaluation by ISRO scientists, a dummy 4-feature logistic classifier is exposed as checkbox AI theater, disqualifying the submission. |
| **A03** | Atmospheric turbulence can be modeled as a symmetric 2D Gaussian blur whose kernel scales with $C_n^2$. | **B** | 5 | 4 | **20** | Turbulence produces random wavefront phase distortions, speckle breakdown, beam wander, and deep log-normal intensity fades ($>30\text{ dB}$ drops), which completely break Gaussian models. |
| **A04** | Platform disturbance vibrations are uncorrelated additive white Gaussian noise (AWGN). | **B** | 4 | 4 | **16** | Spacecraft, aircraft, and naval platforms have colored disturbance spectra with sharp resonant peaks (reaction wheels, rotor frequencies, sea wave harmonics). |
| **A05** | Tracking 2D pixel coordinates $(u, v)$ with a linear Kalman filter is mathematically sufficient for 3D gimbal steering. | **C** | 4 | 4 | **16** | Gimbal kinematics are non-linear spherical transformations $(\text{Az}, \text{El})$. Near zenith or high elevations, gimbal lock and non-linear velocity scaling cause severe tracking loss. |
| **A06** | The laser beacon appears as the brightest contiguous blob in the sensor aperture. | **B** | 4 | 4 | **16** | Solar glints, cloud edge reflections, and terrestrial headlights are frequently brighter than a degraded laser beacon operating at $1550\text{ nm}$ or $850\text{ nm}$. |
| **A07** | Gimbal motors have zero backlash, zero friction, and instantaneous acceleration up to `max_velocity`. | **ID** | 4 | 4 | **16** | Physical gimbals have inertia, stiction, gear backlash, and motor torque limits. Uncompensated PID control with no anti-windup causes violent oscillation. |
| **A08** | A 454-test suite with a 100% pass rate proves compliance with ISRO Problem Statement 26169. | **ID** | 5 | 3 | **15** | Tests assert string existence and object instantiation (`assert ptz is not None`) rather than closed-loop physical convergence. |
| **A09** | AST static parsing of import statements guarantees evaluation integrity. | **ID** | 3 | 4 | **12** | Preventing coordinate imports does not validate tracker robustness when the simulation scenario itself is physically trivialized. |
| **A10** | A React 18 / Vite / Three.js web application is necessary for an embedded FSOC tracking terminal. | **ID** | 4 | 3 | **12** | Embedded flight terminals require deterministic, low-power, headless daemons or lightweight Qt UIs. The Node.js stack adds latency, bloat, and attack surface. |
| **A11** | Linear constant-velocity (CV) kinematics accurately represent FSOC target dynamics. | **C** | 3 | 4 | **12** | Mobile terminals (satellites in LEO, maneuvering UAVs, tactical vehicles) execute continuous angular acceleration, requiring an Interacting Multiple Model (IMM) filter. |
| **A12** | 30 FPS frame rate ($33.3\text{ ms}$ latency) is fast enough for coarse PAT disturbance rejection. | **C** | 3 | 4 | **12** | Under high-frequency platform vibration ($10\text{--}50\text{ Hz}$), a 30 Hz loop aliasing nyquist limit is only $15\text{ Hz}$. A coarse PAT loop should ideally run at $100\text{--}200\text{ Hz}$. |

---

## 3. Prosecution of the Top 3 Lethal Assumptions

### 3.1 Lethal Assumption A01: "Target is Pre-Acquired in the FOV"
- **Epistemic Class**: Interest-Driven (ID).
- **Why it was made**: It is vastly easier to write code for a tracker that already sees a target than to design a complete autonomous search-and-acquisition state machine with spiral scans, dwell times, and statistical false-alarm rejection.
- **Consequence of Reality**: When tested on any scenario where the target starts outside the $640 \times 480$ box, the system fails 100% of the time, proving it is not an "acquisition and tracking" system, but merely a "post-acquisition tracking" demo.

### 3.2 Lethal Assumption A02: "Checkbox AI is Sufficient"
- **Epistemic Class**: Interest-Driven (ID).
- **Why it was made**: The hackathon problem statement contains "AI-Based" in the title. The developers needed an ML model in the pipeline to claim compliance, so they trained a 4-feature Logistic Regression on random noise and left the 11-feature MLP turned off.
- **Consequence of Reality**: Evaluators inspecting the code will immediately recognize that machine learning plays zero functional role in the tracking solution.

### 3.3 Lethal Assumption A03: "Atmospheric Turbulence = Gaussian Blur"
- **Epistemic Class**: Belief (B) / Simplification.
- **Why it was made**: OpenCV provides `cv2.GaussianBlur` in a single line of C-accelerated code. Implementing Fourier split-step wave propagation with Kolmogorov phase screens requires significant optical physics knowledge.
- **Consequence of Reality**: The algorithm is never tested against real turbulence effects: beam breakup into multi-speckle clusters, severe centroid wander, and deep fading dropouts. When exposed to real atmospheric test bench data, the centroid tracker will fail catastrophically.
