# 01 — Problem Reconstruction From Zero

**Date:** 2026-09-28  
**Discipline:** First-Principles Assumption Auditor (`axiom`) & Scientific Protocol (`falsify`)  
**Scope:** SIH Problem Statement 26169 (Department of Space / ISRO)

---

## 1. The Core Problem: Reconstructed From Physics & Domain Reality

Free Space Optical Communication (FSOC) utilizes coherent laser beams with beam divergence angles typically on the order of tens to hundreds of microradians ($\mu\text{rad}$). In mobile environments (inter-satellite crosslinks, LEO-to-ground, UAV-to-ground, and maritime links), relative angular velocities between platforms range from several degrees per second to hundreds of microradians per second.

Pointing, Acquisition, and Tracking (PAT) operates in two sequential stages:
1. **Coarse Alignment (The Problem):** The optical terminal has an initial angular uncertainty (Uncertainty Cone) far wider than the communication beam. The terminal must search the field of regard, locate the remote optical beacon, acquire it on its focal plane array (FPA), and drive a 2-DOF Pan-Tilt (PTZ) gimbal mount to center the beacon on the optical axis within the capture range of the fine pointing mechanism.
2. **Fine Alignment:** Fast Steering Mirrors (FSM) or piezoelectric nutators refine the beam alignment from microradians down to sub-microradians for high-rate data transfer.

### ISRO's Software Benchmark Mandate
Hardware PAT testbeds require collimated optical benches, vibration tables, and vacuum/turbulence chambers. SIH Problem Statement 26169 explicitly asks for a software-based virtual camera testbed that emulates this coarse alignment problem:
- A large virtual scene ($\ge 2000 \times 2000\text{ px}$) representing the angular uncertainty field.
- A movable virtual camera ($640 \times 480\text{ px}$, $4^\circ \times 3^\circ\text{ FOV}$) representing the coarse sensor on a motorized gimbal.
- Moving beacon targets ($5\text{--}20\text{ px}$) moving along straight, circular, figure-8, and random trajectories.
- Disturbances: Platform angular drift ($\pm 20\text{ px}$), camera jitter ($\pm 20\text{ px}$), atmospheric attenuation (fog/haze/rain), and sensor noise (Gaussian, Poisson, Salt & Pepper).
- Performance targets: Acquisition $\le 2\text{ s}$, Reacquisition $\le 1\text{ s}$, RMSE $\le 10\text{ px}$, Loss rate $< 5\%$, Throughput $\ge 20\text{ FPS}$.

---

## 2. Irreducible Problem Decomposition

The coarse alignment problem mathematically decomposes into seven irreducible functions:

```text
[1. Uncertainty Search & Acquisition]
       │ Sweeps camera over field of regard (Spiral / Lissajous / Raster scan)
       ▼
[2. Optical Signal Extraction & Discrimination]
       │ Separates optical beacon from background clutter, shot noise, and sensor dead pixels
       ▼
[3. Sub-Pixel Centroid Localization]
       │ Determines intensity-weighted optical center of energy
       ▼
[4. State Estimation & Dynamic Filtering]
       │ Predicts position through latency, filters high-frequency sensor noise, estimates velocity
       ▼
[5. Closed-Loop Gimbal Servoing]
       │ Generates rate-limited angular velocity commands to null line-of-sight error
       ▼
[6. Target Retention & Out-of-FOV Reacquisition]
       │ Detects beam loss, coasts along state prediction, executes localized recovery search
       ▼
[7. Objective Performance Verification]
       │ Measures true angular error, lock retention, and throughput against known ground truth
```

---

## 3. The Minimal Technically Credible Solution

What is the smallest system that genuinely solves this problem?

1. **Deterministic 2D/3D Kinematic Engine:** Generates true beacon world coordinates and updates camera pose based on gimbal commands.
2. **Sensor Pipeline:** Generates optical beacon profile (Gaussian/Airy), applies noise, crops camera viewport.
3. **Acquisition FSM:**
   - **Mode A (Search):** Archimedean spiral or Lissajous gimbal scan across the uncertainty region.
   - **Mode B (Track):** Centroiding + Kalman filter + PID control to center the beacon.
   - **Mode C (Reacquire):** Localized expanding spiral centered at the last predicted velocity vector.
4. **Gimbal Controller:** Proportional-Integral-Derivative (PID) controller with velocity saturation ($5^\circ/\text{s}$) and acceleration limits.
5. **Headless & GUI Runner:** Clean single-window dashboard displaying sensor view, telemetry, and benchmark evaluation.

---

## 4. The "Platform Pivot" Fallacy: Sunk Cost vs. Requirement Alignment

The previous development team pivoted the project to define it as:
> *"LumiTrack is an Algorithm Evaluation Platform, not a standalone tracker. It allows developers to inject tracking algorithms as plugins..."*

### Forensic Deconstruction of This Decision:
1. **Did ISRO ask for an Algorithm Platform?**
   **No.** The Problem Statement is titled: *"Development of an AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile FSOC Terminals"*. Deliverable 1 is: *"A standalone executable application implementing the complete virtual camera tracking system"*.
2. **What was the consequence of the platform pivot?**
   Massive engineering effort was diverted into:
   - Building a dynamic plugin loader with JSON manifests (`PluginLoader`).
   - Abstract Syntax Tree (AST) firewalls checking for ground-truth leakage.
   - A dual-frontend architecture (PySide6 Qt GUI + React 18 Web UI + FastAPI server + WebSockets).
   - A 500-line natural language scenario parser called "AI Interpretation Engine".
3. **What was neglected as a result?**
   - **Target Acquisition Search was NEVER implemented.** When a beacon starts outside the camera FOV, the system outputs zero gimbal commands and sits idle forever.
   - **True AI/ML tracking was trivialized.** Rather than developing a deep vision detector or robust reinforcement learning gimbal controller, the team trained a 4-feature Logistic Regression on 400 uniform random numbers.
   - **Physical optics was replaced with flat array slicing.** No wave optics, no atmospheric phase screens, no line-of-sight angle math.

The project invested 80% of its complexity into platform scaffolding and 20% into the actual tracking science, while claiming the reverse in documentation.
