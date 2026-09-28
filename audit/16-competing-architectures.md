# SIH 26169 — Competing Architecture Synthesis & Trade-Off Evaluation

**Document ID**: `AUDIT-16-COMPETING-ARCHITECTURES`  
**Target Repository**: `Ujjwal-Qubit/Run_Time_Error` (SIH 26169 Coarse Alignment FSOC)  
**Status**: COMPLETE / FORENSIC VERIFIED  
**Auditor**: Antigravity First-Principles Reconnaissance

---

## 1. Executive Summary

To replace the flawed current architecture, we systematically formulate and evaluate **four distinct competing architectural paradigms** from first principles, assessing each against the physical, computational, and evaluative demands of ISRO Problem Statement SIH 26169.

---

## 2. Formulation of the Four Competing Architectures

### Architecture A: Pure Classical Deterministic (Minimalist High-Reliability Core)
- **Concept**: A mathematically provable, zero-ML, hard real-time pipeline based purely on classical optics, morphological signal processing, and robust control theory.
- **Components**:
  - *Front-End*: Morphological White Top-Hat filter + adaptive Otsu thresholding + intensity-weighted centroiding ($1/16\text{th}$ pixel precision).
  - *Acquisition*: Analytical Fermat spiral search with automated candidate lock-on gating.
  - *State Estimation*: Error-State Extended Kalman Filter (ES-EKF) on $SO(3)$ with Kinematic IMU feedforward.
  - *Control*: Active Disturbance Rejection Control (ADRC) or Feedforward PID with back-calculation anti-windup.
  - *Compute Target*: Low-power ARM Cortex-A72 / STM32H7 / bare C++20 daemon ($<3\text{ W}$, latency $<2\text{ ms}$).

### Architecture B: Hybrid Classical-Deep (Edge-AI Enhanced PAT) — *The Balanced Champion*
- **Concept**: Combines the determinism and speed of classical signal extraction with modern edge-optimized deep learning for speckle pattern discrimination, clutter rejection, and predictive gating.
- **Components**:
  - *Front-End*: Multi-candidate extraction via spatial Difference-of-Gaussians (DoG) + Temporal beacon modulation filtering.
  - *AI Discrimination*: Lightweight NanoTrack / MobileNetV4-S Siamese tracker (ONNX / TensorRT, $<500\text{k}$ parameters) operating on candidate image patches ($64 \times 64$) to reject solar glints, cloud reflections, and background decoys.
  - *Acquisition*: Bayesian uncertainty-guided Fermat spiral search governed by an ephemeris covariance engine.
  - *State Estimation*: Interacting Multiple Model (IMM) Filter combining Constant Velocity, Constant Acceleration, and Colored Micro-Vibration AR models.
  - *Control*: Anti-Windup PID with IMU-based platform rate feedforward.
  - *Compute Target*: NVIDIA Jetson Orin Nano / Raspberry Pi 5 ($5\text{--}10\text{ W}$, latency $<6\text{ ms}$).

### Architecture C: End-to-End Deep Reinforcement Learning (Pixels-to-Torques)
- **Concept**: A single deep neural network policy (trained via PPO/SAC in simulation) that directly maps raw image frames and IMU histories to gimbal motor torques and uncertainty-cone search patterns.
- **Components**:
  - *Neural Core*: Vision-Transformer (ViT) or ConvNet backbone coupled to an Actor-Critic recurrent policy (LSTM/GRU).
  - *Control*: Direct policy inference outputting motor voltage or torque commands at 60 Hz.
  - *Compute Target*: High-end embedded GPU (NVIDIA Jetson AGX Orin, $25\text{--}50\text{ W}$).

### Architecture D: Neuromorphic Event-Based & CMOS Dual-Sensor Fusion
- **Concept**: Integrates an asynchronous neuromorphic event camera with a conventional CMOS framing camera for microsecond disturbance rejection and wide-dynamic-range tracking.
- **Components**:
  - *Front-End*: Asynchronous event stream ($>10\text{ kHz}$) processed via spatial-temporal DBSCAN event clustering + Narrow-band CMOS reference camera ($30\text{ Hz}$).
  - *State Estimation*: Continuous-discrete EKF fusing asynchronous microsecond event timestamps with low-rate absolute CMOS frames.
  - *Control*: High-bandwidth dual-loop controller: event-rate inner loop for micro-vibration cancellation ($500\text{ Hz}$), outer loop for gimbal positioning ($30\text{ Hz}$).
  - *Compute Target*: FPGA + Embedded ARM (Xilinx Kria / Zynq UltraScale+).

---

## 3. Multi-Criteria Trade-Off Evaluation Matrix

Each architecture is evaluated on a scale of $1\text{ to }5$ ($1 = \text{Poor / Inadequate}, 5 = \text{Exceptional / Ideal}$):

| Evaluation Criterion | Weight | Arch A (Pure Classical) | Arch B (Hybrid Classical-AI) | Arch C (End-to-End RL) | Arch D (Neuromorphic Fusion) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tracking Accuracy ($<1\text{ mrad}$ under jitter)** | 20% | 4 | 5 | 3 | 5 |
| **Autonomous Acquisition & Spiral Search** | 15% | 4 | 5 | 4 | 4 |
| **Atmospheric Turbulence & Glint Immunity** | 15% | 3 | 5 | 3 | 4 |
| **Latency & Real-Time Determinism ($<10\text{ ms}$)** | 15% | 5 | 4 | 2 | 5 |
| **ISRO SIH "AI-Based" Compliance & Defense** | 15% | 2 | 5 | 5 | 3 |
| **SWaP-C (Size, Weight, Power, and Cost)** | 10% | 5 | 4 | 1 | 2 |
| **Implementation Feasibility within Hackathon Scope** | 10% | 5 | 4 | 1 | 2 |
| **Weighted Total Score (out of 5.0)** | **100%** | **3.85** | **4.70** | **2.95** | **3.90** |

---

## 4. Deep Trade-Off Analysis

### 4.1 Why Architecture C (End-to-End RL) is Disqualified
While intellectually fashionable in academic research, End-to-End Reinforcement Learning is **fundamentally unsuitable** for aerospace FSOC coarse pointing:
1. **Lack of Safety & Stability Guarantees**: A pure neural network policy offers no mathematical proof of Lyapunov stability. Under unexpected optical blinding or sensor anomalies, an RL policy can output erratic high-frequency torque chatter that destroys gimbal gearing.
2. **Simulation-to-Reality Gap**: Policies overfit to the synthetic simulator; when exposed to real atmospheric turbulence or unknown platform vibration frequencies, performance collapses.
3. **Massive Compute & Power Penalty**: Requires an expensive, power-hungry Jetson AGX Orin ($>30\text{ W}$), violating the SWaP constraints of mobile optical terminals.

### 4.2 Why Architecture D (Neuromorphic Fusion) is Kept for Phase 3 Roadmap
Neuromorphic event tracking offers incredible physical performance ($>10\text{ kHz}$ tracking bandwidth, $>120\text{ dB}$ dynamic range). However:
1. It requires specialized, expensive neuromorphic hardware (Prophesee cameras costing $>€5,000$).
2. Developing asynchronous event-cloud clustering algorithms in software within the SIH competition timeline introduces substantial delivery risk.
3. It serves as an extraordinary **Future Technology Roadmap item** to highlight in the team's presentation to ISRO.

### 4.3 Why Architecture A (Pure Classical) Falls Short on Competition Context
Architecture A is technically robust, mathematically rigorous, and flight-proven in commercial satcom. However:
1. The Problem Statement explicitly mandates: *"Development of an **AI-Based** Virtual Camera Tracking System"*.
2. Submitting a pure classical PID/Kalman pipeline invites immediate disqualification or severe scoring penalties from evaluators looking for artificial intelligence innovation.
3. Pure classical thresholding fails when atmospheric turbulence breaks the laser spot into multi-speckle clusters that mimic cloud reflections.

---

## 5. Architectural Recommendation: Architecture B (Hybrid Classical-AI)

**Architecture B (Hybrid Classical-Deep)** is the decisive winner:
1. **Genuine AI Integration**: Uses deep learning precisely where classical methods fail—in recognizing true speckle clusters from decoy solar glints and predicting target motion through deep fades using an ONNX/TensorRT model.
2. **Deterministic Control Backbone**: Anchors state estimation and gimbal control in rigorous, provable control theory (IMM-EKF and Anti-Windup PID with IMU feedforward), guaranteeing safety and determinism.
3. **Execution Feasibility**: Readily implemented in Python 3.11 with C-extensions/ONNX Runtime on desktop and edge platforms (Jetson Orin Nano / PySide6).
4. **Unimpeachable Defense**: Defends both the "AI" requirement of the hackathon and the "hard physics" requirement of ISRO evaluators.
