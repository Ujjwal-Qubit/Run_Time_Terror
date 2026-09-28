# 02 — System Reconstruction From Codebase Evidence

**Date:** 2026-09-28  
**Scope:** Reconstructing the actual runtime mechanics of LumiTrack from source code evidence.

---

## 1. Actual Runtime Execution Flows

### Flow 1: Interactive Closed-Loop Simulation
```text
[User clicks 'Start' on Qt GUI / Web UI]
  ↓
AppController.initialize() / start_background_loop()
  ↓
SimulationWorkerThread._run_loop() (Runs at 30 Hz clock)
  ↓
SimulationFrameProvider.get_next_frame()
  ├── TargetManager.step(dt) → Computes world kinematics (X, Y)
  ├── DisturbanceEngine.apply_geometric_disturbances() → Platform drift + Gaussian jitter
  ├── SceneManager.render() → Composites (10×10) patch onto 2000×2000 canvas
  ├── CameraModel.extract_viewport() → Crops 640×480 slice around (eff_cam_x, eff_cam_y)
  ├── GroundTruthProvider.capture() → Saves true coordinates into synchronized buffer
  ├── DisturbanceEngine.apply_atmospheric_degradation() → contrast * img + offset
  └── DisturbanceEngine.apply_pixel_noise() → Poisson, Gaussian, Salt & Pepper
  ↓
[Ground-Truth Firewall Barrier: public PublicFramePacket passed to algorithm]
  ↓
BaselineTracker.process_frame(PublicFramePacket)
  ├── Adaptive ROI lookup from Kalman prediction
  ├── P0ThresholdDetector.detect() → 3×3 median filter, box filter, connected components
  ├── AIClassifier.identify() → 4-feature Logistic Regression (0.6*AI + 0.4*Base score)
  ├── IntensityWeightedCentroidEstimator.estimate() → Sub-pixel (x, y) center of gravity
  ├── ConstantVelocityKalmanTracker.update() → Innovation gating, state update
  └── TrackingStateManager.update() → Hysteresis transitions (SEARCHING/ACQUIRING/TRACKING/LOST)
  ↓
ProportionalDeadbandPTZController.compute()
  ├── IF state != TRACKING: Returns PTZCommand(valid=False, delta_pan=0, delta_tilt=0)
  └── IF state == TRACKING: omega = clamp(K_p * angle, -5 deg/s, +5 deg/s)
  ↓
CameraModel.apply_pan_tilt(delta_pan, delta_tilt) [Updates camera world position]
  ↓
MetricsEngine.update() → Re-joins tracker output with GroundTruthProvider truth buffer
  ↓
VisualizationStateManager.broadcast() → UI VideoWidget & View3DWidget update
```

### Flow 2: Automated Benchmark-1 Matrix Execution
```text
BenchmarkManager.run_benchmark_matrix(subset="FULL")
  ↓
BenchmarkMatrixRunner.run_matrix() (Iterates over 19 scenario JSONs)
  ↓
EvaluationHarness.run_experiment()
  ├── Spawns headless simulation instance with deterministic seed
  ├── Executes max_frames (e.g. 100 frames)
  ├── Computes RMSE, Lock Retention %, Mean Latency, Algorithm FPS
  └── Writes output/matrix/ JSON, CSV, and Markdown scorecards
```

### Flow 3: Benchmark-2 MP4 Video Ingestion (PTZ Bypassed)
```text
EvaluationHarness.run_experiment(source_type="MP4", mp4_path=...)
  ↓
MP4FrameProvider.get_next_frame() (Decodes frames via cv2.VideoCapture)
  ↓
BaselineTracker.process_frame() (Tracks beacon in video)
  ↓
PTZ Controller is BYPASSED (No camera actuation)
  ↓
MetricsEngine:
  ├── IF reference_csv is provided: Computes RMSE against external truth
  └── IF reference_csv is NOT provided: Sets RMSE, error metrics to None / "N/A"
```

### Flow 4: "AI" Scenario Creation Workflow
```text
User enters text prompt: "Fast expanding spiral with dense fog"
  ↓
AIInterpretationEngine.interpret(prompt)
  ├── Regex keyword match: "spiral" → sets trajectory_type="SPIRAL"
  └── Regex keyword match: "fog" → sets atmospheric_condition="FOG"
  ↓
ScenarioSpecificationValidator.validate() → Checks if bounds <= 2000, speed <= 120 px/s
  ↓
Generated Scenario JSON saved with tag is_ai_generated=True
  ↓
Scenario executed in simulator via EvaluationHarness
```

---

## 2. Component Analysis & Reality Check

| Module | Documented Claim | Source Code Reality | Forensic Diagnosis |
|---|---|---|---|
| **M1: AppController** | Decoupled top-level orchestrator | God Class with 208 connections, 791 lines, handles Qt signals, threading, REST state | Over-coupled architectural bottleneck |
| **M2: ConfigManager** | Type-safe configuration | Dataclasses with `.to_dict()` and JSON serialization | Functional and correct |
| **M4: SceneManager** | Virtual optical environment | Flat 2D NumPy array (`np.full((2000, 2000), 30, uint8)`). Array indexing. | Functional, but zero physical optics |
| **M5: TargetManager** | Physics-informed beacon generation | Generates square, circle, or Gaussian 2D patches. Clamps spawn to center $\pm 150\text{ px}$. | Guaranteed in-FOV cheat |
| **M6: CameraModel** | Optical sensor & projection model | Linear scale factor ($4.0^\circ / 640\text{ px} = 0.00625^\circ/\text{px}$). 2D array cropping. | Oversimplified projection |
| **M7: DisturbanceEngine** | Physical turbulence & platform jitter | Uniform contrast scaling, random normal pixel shift, Poisson/Gaussian noise. | No wave optics or PSD jitter |
| **M8: FrameProvider** | Ground-truth isolation firewall | Immutable `FramePacket` dataclass stripping all truth metadata. | **Excellently engineered & leak-free** |
| **M9: DetectionEngine** | Adaptive threshold detector | 3×3 median filter + box filter background subtract + connected components. | Solid, robust classical CV |
| **M10: CentroidEstimator** | Sub-pixel centroid estimator | Intensity-weighted center-of-gravity with border median background subtract. | Standard, reliable classical method |
| **M11: CandidateIdentifier** | AI-augmented classification | 4-feature Logistic Regression on synthetic random samples (`lr_model.json`). | Toy ML / AI Theatre |
| **M12: TemporalTracker** | Constant-Velocity Kalman Filter | 4-state CV-KF ($x, y, v_x, v_y$) with innovation gating and adaptive ROI. | Mathematically sound |
| **M13: StateManager** | Tracking lifecycle FSM | SEARCHING → ACQUIRING → TRACKING → REACQUIRING → LOST. | Standard state machine |
| **M14: PTZController** | Proportional-Deadband gimbal servo | Commands zero velocity when not in TRACKING state. | **Fatal Design Flaw: Zero search pattern** |
| **M15: MetricsEngine** | Objective performance evaluation | Compares tracker sub-pixel centroids with GroundTruthProvider. | Honest and objective |
| **M17: BenchmarkManager** | End-to-end evaluation harness | Automates 19 scenarios (BM1) and MP4 playback (BM2). | Highly functional batch runner |
| **M19: View3DWidget** | 3D Orbital geometric visualization | QPainter 2D software projection of 3D wireframe axes and cone. | Visual cosmetic mockup |
| **Web Server (`server.py`)** | Enterprise client-server API | FastAPI + WebSockets running on port 8000. | Redundant second backend |
| **Web UI (`frontend/`)** | Modern evaluation cockpit | React 18 + Vite + Three.js web application. | Redundant second UI |
