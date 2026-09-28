# 07 — Scientific & Domain Audit (FSOC Pointing, Acquisition & Tracking)

**Date:** 2026-09-28  
**Discipline:** Satellite / FSOC Domain Specialist & Scientific Reviewer (`falsify`)  
**Scope:** Physics, Optics, Dynamics, and Simulation Fidelity of LumiTrack

---

## 1. Domain Overview: Coarse Alignment in FSOC Links

In Free-Space Optical Communication, coarse alignment bridges the gap between wide initial positional uncertainty (typically $1^\circ\text{--}5^\circ$) and the sub-milliradian FOV required by fine-tracking optical sensors.

```text
[Initial Uncertainty Cone: ~2-5°] ──(Coarse Gimbal Scan: ±5-10°/s)──> [Coarse FOV: 4°×3°]
                                                                             │
                                                                  (Centroiding & Tracking: ≤ 10 px)
                                                                             │
                                                                             ▼
[Fine Tracking Mirror: < 0.1° / 1.7 mrad] <──(Coarse Handoff: ≤ 50 μrad)────+
```

---

## 2. Evaluation of Physical & Mathematical Formulations

### A. Optical Beacon Radiometry & Beam Profile
- **Current Implementation:**
  `TargetManager._generate_patch` produces a flat 2D square (`patch.fill(intensity)`), a hard-edged circle (`dist_sq <= r^2`), or a 2D Gaussian.
- **Physical Reality:**
  A laser beacon transmitted across tens to thousands of kilometers arrives as an expanded beam. When focused through an optical aperture of diameter $D$ at wavelength $\lambda = 1550\text{ nm}$, diffraction through a circular aperture yields an **Airy disk irradiance pattern**:
  $$I(\theta) = I_0 \left( \frac{2 J_1(\pi D \theta / \lambda)}{\pi D \theta / \lambda} \right)^2$$
  where $J_1(x)$ is the Bessel function of the first kind.
- **Scientific Verdict:** The 2D Gaussian profile (`shape="gaussian"`) is a respectable first-order paraxial approximation of the central Airy core, but the default `"square"` shape requested by SIH Row 9 is an unphysical synthetic artifact.

### B. Atmospheric Propagation & Turbulence
- **Current Implementation:**
  `DisturbanceEngine.apply_atmospheric_degradation` applies a scalar gain and bias:
  $$I_{\text{degraded}}(x, y) = \text{contrast} \cdot I(x, y) + \text{offset}$$
- **Physical Reality in Terrestrial & Low-Altitude FSOC:**
  Atmospheric turbulence arises from refractive index fluctuations ($C_n^2$) driven by thermal gradients. It induces three distinct phenomena:
  1. **Scintillation (Irradiance Fading):** Modeled by log-normal or Gamma-Gamma intensity distributions.
  2. **Beam Wander (Angular Jitter):** Spatial displacement of the beam centroid caused by turbulent eddies larger than the beam diameter.
  3. **Phase Aberrations (Spot Breakup / Blurring):** Described by the Fried parameter $r_0$. When $D > r_0$, the beacon breaks into multiple dynamic speckles.
- **Scientific Verdict:** The current scalar contrast reduction models uniform absorption/scattering (Beer-Lambert attenuation in haze/fog) but **completely omits turbulence-induced scintillation, phase distortion, and beam wander**.

### C. Spacecraft / Mobile Platform Micro-Vibrations (Jitter)
- **Current Implementation:**
  Sampled per-frame from an uncorrelated Gaussian distribution:
  $$j_x, j_y \sim \mathcal{N}\left(0, \left(\frac{\sigma_{\max}}{3}\right)^2\right)$$
- **Physical Reality in Satellite & Mobile Terminals:**
  Platform micro-vibrations are colored noise driven by mechanical rotating machinery (reaction wheels, control moment gyroscopes, solar array drive mechanisms, cryocoolers).
  Satellite jitter exhibits distinct **Power Spectral Density (PSD)** peaks at resonant structural frequencies (typically $10\text{ Hz}$, $40\text{--}60\text{ Hz}$, $120\text{ Hz}$, and $300\text{ Hz}$).
- **Scientific Verdict:** White Gaussian noise provides an adequate stress-test for Kalman filter measurement noise, but fails to model the colored, harmonic sinusoidal resonance characteristic of real satellite bus jitter.

### D. Sensor Noise & Photodetector Physics
- **Current Implementation:**
  - Poisson Noise: `rng.poisson(frame)` (Signal-dependent shot noise).
  - Gaussian Noise: $\mathcal{N}(0, \sigma^2)$ (Electronic readout / thermal Johnson noise).
  - Salt & Pepper Noise: Random impulse pixels set to $0$ or $255$ (Dead / hot pixels).
- **Scientific Verdict:** **Mathematically sound and physically justified.** The execution order (Poisson $\to$ Gaussian $\to$ S&P) correctly models the physical transduction cascade from photons to electron wells to readout circuits.

### E. Kinematics, Projection & Gimbal Dynamics
- **Current Implementation:**
  Linear scaling: $\Delta \theta = \Delta x \cdot (4.0^\circ / 640\text{ px}) = 0.00625^\circ/\text{px}$.
  PTZ control: Proportional deadband $\omega = K_p \theta$ clamped to $\pm 5^\circ/\text{s}$.
- **Physical Reality:**
  - Pinhole camera geometry requires perspective projection:
    $$\theta_x = \arctan\left(\frac{x - c_x}{f_x}\right), \quad \theta_y = \arctan\left(\frac{y - c_y}{f_y}\right)$$
    For narrow FOVs ($4^\circ \times 3^\circ$), $\arctan(\theta) \approx \theta$ holds to within $0.08\%$ error. Thus, linear FOV mapping is mathematically acceptable.
  - **Gimbal Mechanics:** Real motorized pan-tilt stages are second-order mechanical systems governed by torque and moment of inertia:
    $$J \ddot{\theta} + B \dot{\theta} = \tau$$
    They possess finite angular acceleration limits ($\ddot{\theta}_{\max} \approx 20\text{--}50^\circ/\text{s}^2$). The current code implements velocity clamping but ignores acceleration limits, permitting instantaneous step changes in velocity.

### F. The Missing Acquisition Pattern (The Core Domain Flaw)
In FSOC Pointing, Acquisition, and Tracking (PAT), the uncertainty in remote terminal line-of-sight exceeds the coarse camera FOV. To acquire the link, the master terminal must execute an **Acquisition Scan Pattern**:
- **Archimedean Spiral Scan:**
  $$r(t) = a + b \cdot \omega t, \quad \theta(t) = \omega t$$
  Ensures uniform spatial coverage of the uncertainty disk without angular blind spots.
- **Lissajous Scan:** Sinusoidal actuation along dual orthogonal axes with non-integer frequency ratios.
- **Current Implementation Status:** **Completely absent.** When in `SEARCHING` or `LOST` state, the gimbal velocity is clamped to zero. The system relies entirely on the target being initialized inside its FOV.

---

## 3. Simulation-to-Reality Gap Ledger

| Domain Parameter | LumiTrack Simulation Model | Real-World FSOC Terminal Hardware | Sim-to-Real Gap & Consequence |
|---|---|---|---|
| **World Geometry** | 2D pixel canvas ($2000 \times 2000\text{ px}$) | 3D inertial orbit / line-of-sight vector | Real target range, radial velocity, and ephemeris orbital curvature are abstracted into 2D Cartesian drift. |
| **Beacon Source** | 2D binary square or Gaussian patch | Collimated laser beam with Airy diffraction | Oversimplifies spatial energy distribution; ignores diffraction sidelobes. |
| **Turbulence** | Scalar contrast reduction & brightness offset | Spatio-temporal phase screens, scintillation, beam wander | Omits intensity fading spikes and speckle breakup that cause tracker loss. |
| **Jitter** | Uncorrelated white Gaussian pixel noise | Multi-harmonic structural vibration PSD | Fails to test tracker immunity against mechanical resonance frequencies. |
| **Acquisition** | Target spawned inside camera FOV | Target anywhere in wide uncertainty cone | **Critical Gap:** Tracker cannot perform autonomous link establishment from cold start. |
| **Gimbal Actuation** | Velocity-limited kinematic integration | Torque, inertia, back-EMF, acceleration limits | Instantaneous velocity steps unrealistic on physical stepper/BLDC motors. |
