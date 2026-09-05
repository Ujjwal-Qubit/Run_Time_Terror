# Graph Report - external  (2026-09-05)

## Corpus Check
- 75 files · ~97,454 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 891 nodes · 2234 edges · 58 communities (46 shown, 5 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 265 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Manager Config
- Controller Appcontroller
- Detect Detection
- Simulation Disturbance
- Tracker Manager
- Track Tracker
- Manager Simulation
- Simulation Camera
- Frame Contracts
- Provider Frame
- Control Controller
- Strategy Interfaces
- Interface Interfaces
- Simulation Manager
- Tracking Pipeline
- Candidate Identifier
- Logging Engine
- Frame Provider
- Control Controller
- Simulation Provider
- Model Camera
- Tracker Manager
- Control Controller
- Foundation Contracts
- Frame Simulation
- Contracts Frame
- Controller Testptzcontrollerfirewall
- Controller Testptzcontrollergeometry
- Logging Engine
- Strategy Interfaces
- Temporal Tracker
- Centroid Estimator
- Centroid Estimator
- Centroid Estimator
- Centroid Estimator
- Foundation Testdefaults
- Truth Ground
- Centroid Tracker
- Control Controller
- Simulation Model
- Strategy Interfaces
- Centroid Estimator
- Centroid Estimator
- Centroid Tracker
- Centroid Estimator
- Centroid Estimator
- Engine Detection
- Frame Provider
- Control Controller
- Provider Frame
- Candidate Identifier

## God Nodes (most connected - your core abstractions)
1. `AppController` - 69 edges
2. `ProportionalDeadbandPTZController` - 61 edges
3. `IntensityWeightedCentroidEstimator` - 59 edges
4. `P0ThresholdDetector` - 59 edges
5. `SystemConfig` - 55 edges
6. `FramePacket` - 51 edges
7. `ConstantVelocityKalmanTracker` - 49 edges
8. `SimulationFrameProvider` - 44 edges
9. `MP4FrameProvider` - 40 edges
10. `DisturbanceEngine` - 40 edges

## Surprising Connections (you probably didn't know these)
- `run_benchmark()` --uses--> `SimulationFrameProvider`  [INFERRED]
  smoke_test_centroid_estimator.py → src/frame/simulation_provider.py
- `run_benchmark()` --uses--> `SimulationFrameProvider`  [INFERRED]
  smoke_test_detection_engine.py → src/frame/simulation_provider.py
- `run_smoke_test()` --uses--> `SimulationFrameProvider`  [INFERRED]
  smoke_test_ptz_controller.py → src/frame/simulation_provider.py
- `run_smoke_test()` --uses--> `MotionType`  [INFERRED]
  smoke_test_simulation.py → src/frame/data_contracts.py
- `run_benchmark()` --calls--> `SystemConfig`  [EXTRACTED]
  smoke_test_centroid_estimator.py → src/config/config_manager.py

## Import Cycles
- None detected.

## Communities (58 total, 5 thin omitted)

### Community 0 - "Manager Config"
Cohesion: 0.05
Nodes (21): ConfigManager, Any, Serialize to dictionary for JSON export., Deserialize from dictionary., Configuration Manager — Module 2 per Architecture v1.2. Responsibilities: -…, Return the current configuration., Return a deep copy for experiment reproducibility., Load configuration from a JSON scenario file. (+13 more)

### Community 1 - "Controller Appcontroller"
Cohesion: 0.05
Nodes (23): create_test_mp4(), Phase 5.3 FrameProvider Smoke Test. Demonstrates: 1. Simulation ->…, run_smoke_test(), AppController, ndarray, Unified entry point to obtain the next frame via the FrameProvider firewall.…, Execute a single simulation frame step directly (for simulation…, Stop the application. (+15 more)

### Community 2 - "Detect Detection"
Cohesion: 0.08
Nodes (23): DetectorConfig, Detection pipeline configuration., FramePacket, The fundamental data contract between FrameProvider and the tracker pipeline.…, make_test_frame(), Test detection across all valid PS beacon sizes and locations., PS Row 10: Minimum target size is 5x5 pixels., PS Row 10: Default target size is 10x10 pixels. (+15 more)

### Community 3 - "Simulation Disturbance"
Cohesion: 0.08
Nodes (23): Deterministic Simulation Engine Smoke Test. Runs 60 simulation frames (2.0…, run_smoke_test(), AtmosphericConfig, JitterConfig, NoiseConfig, PlatformMotionConfig, Camera jitter configuration., Platform motion configuration. (+15 more)

### Community 4 - "Tracker Manager"
Cohesion: 0.11
Nodes (21): Phase 5.5 Centroid Estimator Smoke Test & Performance Check. Measures: - Frames…, Phase 5.4 Detection Engine Smoke Test & Performance Check. Measures: - Frames…, Application Controller — Module 1 per Architecture v1.2 §4. Top-level…, LoggingConfig, Configuration Manager — Module 2 per Architecture v1.2 §4. Centralizes all…, Logging configuration., Simulation execution configuration., SimulationConfig (+13 more)

### Community 5 - "Track Tracker"
Cohesion: 0.09
Nodes (16): Temporal tracker configuration., TrackerConfig, CentroidResult, Result of centroid estimation. Per Architecture v1.2 §8.2 Stage 5. Sub-pixel…, Verifies Kalman initialization, state propagation, gating, and coasting., Stationary target should yield steady position and near-zero velocity., Target moving at 30 px/s in X, 15 px/s in Y should have velocity accurately…, When measurements cease, tracker must coast forward on velocity prediction with… (+8 more)

### Community 6 - "Manager Simulation"
Cohesion: 0.13
Nodes (17): MotionConfig, Beacon target configuration., Target motion configuration., TargetConfig, MotionType, Target motion patterns per PS Row 12., ndarray, Target Manager — Module 5 per Architecture v1.2 §4. Generates beacon spot(s)… (+9 more)

### Community 7 - "Simulation Camera"
Cohesion: 0.08
Nodes (10): ProjectionModel, Transform camera image pixel coordinates (IPC) back to world coordinates (WCS)., Convert pixel coordinates (IPC) to angular offset from optical axis center.…, Convert angular offset in degrees to pixel displacement from image center., Convert angular command to world coordinate displacement in pixels., Check if world coordinate falls within the camera viewport., Encapsulates all camera geometry and projection mathematics. Per Architecture…, Transform world coordinates (WCS) to camera image pixel coordinates (IPC).… (+2 more)

### Community 8 - "Frame Contracts"
Cohesion: 0.13
Nodes (21): Phase 5.6 Tracking Pipeline Smoke Test & Performance Check. Deterministic smoke…, run_smoke_test(), CandidateRegion, FrameSource, IdentificationResult, PlatformMotionType, Data contracts for the SIH 2026 FSOC Virtual Camera Tracking System. These…, A detected candidate region from candidate generation. Per Architecture v1.2… (+13 more)

### Community 9 - "Provider Frame"
Cohesion: 0.10
Nodes (12): run_benchmark(), run_benchmark(), MP4FrameProvider, MP4FrameProvider (Module 8 - Video Adapter). Responsibilities: - Sequentially…, Seek back to frame 0 and reset playback state., Release OpenCV video capture handle., create_synthetic_mp4(), Test the MP4 video adapter conforming to IFrameProvider. (+4 more)

### Community 10 - "Control Controller"
Cohesion: 0.13
Nodes (10): ProportionalDeadbandPTZController, P0 Baseline PTZ Controller. Control Pipeline: 1. Image-plane error relative to…, make_track(), Verify sign convention across all 4 quadrants: 1. Right of center (x > 320):…, Per P0 specification, ACQUIRING issues zero command (no premature actuation)., REACQUIRING uses the valid coasted tracker estimate to maintain corrective…, If tracker has no valid estimate during REACQUIRING, command is zero., Target exactly at optical axis center (320, 240) in a 640x480 frame. (+2 more)

### Community 11 - "Strategy Interfaces"
Cohesion: 0.10
Nodes (18): ABC, DetectionResult, Output contract of DetectionEngine (Module 9). Per Architecture v1.2 §4 Module…, Region of interest for adaptive ROI detection., ROI, ICandidateGenerator, ICentroidEstimator, IDetector (+10 more)

### Community 12 - "Interface Interfaces"
Cohesion: 0.09
Nodes (12): IFrameProvider, FrameProvider firewall interface. Architecture v1.2 §6. The tracker pipeline…, Nominal source update rate in Hz / frames per second., Source image dimensions as (width, height) in pixels., Return the next frame, or None if the source is exhausted. The returned…, Return True if no more frames are available., Return 'SIMULATION' or 'MP4_FILE'., Reset to the beginning of the source. (+4 more)

### Community 13 - "Simulation Manager"
Cohesion: 0.14
Nodes (9): Scene / virtual environment configuration., SceneConfig, ndarray, SceneManager (Module 4). Responsibilities: - Manage 2D global scene canvas in…, Reset canvas to clean background., Deterministically composite a target patch onto the background canvas. Args:…, SceneManager, Test 2D global canvas, coordinate management, and background generation. (+1 more)

### Community 14 - "Tracking Pipeline"
Cohesion: 0.12
Nodes (11): Tracking state machine configuration., StateConfig, Verifies state machine transitions, confirmation counters, and hysteresis., SEARCHING --(1 valid)--> ACQUIRING --(lock_confirm_frames valid)--> TRACKING, If measurement drops during ACQUIRING, reverts immediately to SEARCHING., TRACKING --(miss)--> REACQUIRING --(recover)--> TRACKING, REACQUIRING --(loss_confirm_frames misses)--> LOST, Confirm Acquisition time = t(TRACKING entry) - t(first observation considered).… (+3 more)

### Community 15 - "Candidate Identifier"
Cohesion: 0.15
Nodes (11): run_smoke_test(), IdentifierConfig, Beacon identification configuration., make_candidate(), In SEARCHING state, brighter, well-sized target beats faint distractor., When tracking, candidate closer to predicted position is preferred even if…, Inspect candidate_identifier.py AST to ensure no GroundTruth references exist., Verifies candidate ranking, scoring, and beacon selection. (+3 more)

### Community 16 - "Logging Engine"
Cohesion: 0.11
Nodes (9): LoggingEngine, Return current buffer size (for monitoring)., Logging Engine — Module 16. Responsibilities: - Buffer per-frame…, Create output directory and open CSV file., Buffer a per-frame telemetry record. This is called from the hot loop — must be…, Write buffered records to CSV. Called periodically or on demand., Write the aggregate metrics summary as JSON., Write the configuration snapshot used for this run. (+1 more)

### Community 17 - "Frame Provider"
Cohesion: 0.20
Nodes (9): Top-level system configuration aggregating all sub-configurations. This is the…, SystemConfig, Convenience factory creating a SimulationFrameProvider from SystemConfig., Verifies deterministic pipeline: SimulationFrameProvider -> P0ThresholdDetector…, TestCentroidPipelineIntegration, Test the simulation adapter conforming to IFrameProvider., TestSimulationFrameProvider, Verifies full integration: SimulationFrameProvider -> DetectionEngine (M9) ->… (+1 more)

### Community 18 - "Control Controller"
Cohesion: 0.15
Nodes (10): PTZConfig, Pan/tilt controller configuration., Error below deadband (4 px < 5 px) must produce zero command., Error exactly at deadband (5 px == 5 px) must produce zero command., Error strictly above deadband (5.1 px > 5.0 px) must produce nonzero command., Verify independent per-axis deadbanding: error_x = 2 px (<= 5 px deadband) ->…, Below rate limits, doubling error must double commanded angular velocity., Large error or high gain must saturate velocity at configured max speed. (+2 more)

### Community 19 - "Simulation Provider"
Cohesion: 0.18
Nodes (10): GroundTruthProvider, ndarray, Compute the actual intensity centroid of the rendered beacon on the clean pixel…, Clear recorded ground truth history., GroundTruthProvider (Module 14). Responsibilities: - Capture synchronized…, Capture and record a synchronized GroundTruth entry for a frame. Args:…, Independent state of the beacon target at a given simulation instant. Contains…, TargetState (+2 more)

### Community 20 - "Model Camera"
Cohesion: 0.12
Nodes (7): CameraModel, ndarray, CameraModel (Module 6). Responsibilities: - Maintain camera pointing pose…, Reset camera to initial position and angles., Directly set camera center in world coordinates., Apply PTZ angular shift to camera pose. Updates pan/tilt angles and moves…, Extract the camera viewport from the scene canvas. Args: scene_canvas: 2D numpy…

### Community 21 - "Tracker Manager"
Cohesion: 0.12
Nodes (7): Initialize the application with configuration and instantiate modules. Phase…, Closed-loop integration test: FrameProvider -> Detector -> Centroid ->…, TestPTZControllerClosedLoopIntegration, Evaluate tracking result and advance state machine. Args: track_result: Result…, Tracking State Manager (Module 13 - P0 Baseline)., Reset state machine to initial SEARCHING state., TrackingStateManager

### Community 22 - "Control Controller"
Cohesion: 0.15
Nodes (7): PTZ Controller — Module 14 per Architecture v1.2 §4, §11, §18.2.…, PTZCommand, Pan/tilt command from the PTZ controller. Per Architecture v1.2 §11.1., IPTZController, Strategy interface for PTZ control. Architecture v1.2 §11.1. Responsibility:…, Compute pan/tilt command. Args: track_result: Current track result (None if no…, Reset controller state.

### Community 23 - "Foundation Contracts"
Cohesion: 0.14
Nodes (6): Result from temporal tracking. Per Architecture v1.2 §8.2 Stage 6., TrackResult, Verify all required telemetry fields exist., Test all data contract enums and dataclasses., CentroidResult must preserve sub-pixel coordinates., TestDataContracts

### Community 24 - "Frame Simulation"
Cohesion: 0.14
Nodes (6): __getattr__(), Provides side-channel access to ground truth solely for MetricsEngine., Reset simulation provider and all underlying simulation modules., Step simulation and produce the next FramePacket. The returned image array is…, SimulationFrameProvider (Module 8 - Simulation Adapter). Connects: - Module 4:…, SimulationFrameProvider

### Community 25 - "Contracts Frame"
Cohesion: 0.22
Nodes (12): Namespace, AtmosphericCondition, NoiseType, Complete output from one tracker pipeline invocation. Aggregates all per-frame…, Atmospheric modes per PS Row 24., Noise types per PS Row 21., TrackerOutput, main() (+4 more)

### Community 26 - "Controller Testptzcontrollerfirewall"
Cohesion: 0.20
Nodes (8): Tracking state machine states per Architecture v1.2 §10.1. SEARCHING → No track…, TrackingState, Tests for Module 14 — PTZ Controller (src/control/ptz_controller.py). Verifies:…, Verify Module 14 has zero imports of GroundTruth or src.simulation., Verify PTZController only generates PTZCommand and does NOT actuate…, Measure PTZ compute execution latency over 1000 iterations., TestPTZControllerFirewall, TestPTZControllerPerformance

### Community 27 - "Controller Testptzcontrollergeometry"
Cohesion: 0.24
Nodes (7): CameraConfig, Virtual camera configuration., 640x480 resolution with 4°x3° FOV: scale is 4/640 = 0.00625 deg/px., 1280x720 resolution with 8°x4.5° FOV: scale is 8/1280 = 0.00625 deg/px., 800x600 resolution with 5°x5° square FOV (non-square pixel aspect ratio)., Verify controller directly consumes ProjectionModel.image_to_angles()., TestPTZControllerGeometry

### Community 28 - "Logging Engine"
Cohesion: 0.27
Nodes (7): MetricsSummary, Complete per-frame telemetry record for CSV/JSON logging. Combines tracker…, Aggregate metrics summary for a run. Per Stage 4 §7. All metric definitions are…, TelemetryRecord, Logging Engine — Module 16 per Architecture v1.2 §16. Provides per-frame…, Phase 5.1 Foundation Tests Tests cover: - Data contract enums and dataclasses -…, TestLoggingEngine

### Community 29 - "Strategy Interfaces"
Cohesion: 0.18
Nodes (6): ITracker, Strategy interface for temporal tracking stage. Architecture v1.2 §8.2 Stage 6.…, Update the track with a new centroid measurement (or None if no detection this…, Return the predicted position for the next frame. Used for ROI centering and…, Compute the adaptive ROI for the next frame. Falls back to full-frame during…, Reset tracker state (e.g., on simulation restart).

### Community 30 - "Temporal Tracker"
Cohesion: 0.20
Nodes (5): ndarray, Construct state transition matrix F(dt)., Construct process noise covariance matrix Q(dt). Continuous white noise…, Compute effective dt using incoming timestamps with safe bounding., Perform Kalman prediction and measurement update. Args: centroid: Observed sub-…

### Community 31 - "Centroid Estimator"
Cohesion: 0.20
Nodes (6): parametrize, Candidate region partially clipped at image boundaries must not cause indexing…, Verifies non-mutating guarantee and resolution agnosticism., The observed image must be read-only and bitwise unchanged after estimation., Estimator operates seamlessly across arbitrary sensor resolutions., TestImmutabilityAndResolution

### Community 32 - "Centroid Estimator"
Cohesion: 0.20
Nodes (6): Verifies defensive error handling for edge and degenerate conditions., A uniform ROI has zero weight above background; must return valid=False without…, A single bright pixel above background must return exact integer coordinates., Degenerate zero-size candidate bounding box must return valid=False., Candidate completely outside image bounds must handle gracefully., TestCentroidEdgeCases

### Community 33 - "Centroid Estimator"
Cohesion: 0.25
Nodes (5): make_flat_spot(), ndarray, Generate a flat-top circular or square spot. Returns (image_uint8,…, Verifies interface adherence and return types., TestCentroidContracts

### Community 34 - "Centroid Estimator"
Cohesion: 0.31
Nodes (5): make_gaussian_spot(), Verifies robustness under realistic sensor disturbances., Test a beacon that is heavily saturated at 255., Generate a synthetic frame with an analytically defined Gaussian spot at sub-…, TestCentroidRobustness

### Community 35 - "Foundation Testdefaults"
Cohesion: 0.22
Nodes (4): Verify defaults are correctly classified and valued., Verify order matches Architecture v1.2 §7.1., Engineering defaults should be separate from PS values., TestDefaults

### Community 36 - "Truth Ground"
Cohesion: 0.25
Nodes (5): GroundTruth, Ground truth record for a single frame. Per Architecture v1.2 §12.1b. Consumed…, Retrieve GroundTruth for a specific frame. Consumed by MetricsEngine., Retrieve all recorded GroundTruth entries in chronological order., Ground truth has world, ideal, and rendered positions.

### Community 37 - "Centroid Tracker"
Cohesion: 0.38
Nodes (4): CentroidConfig, Centroid estimation configuration., IntensityWeightedCentroidEstimator, Intensity-Weighted Centroid Estimator (Module 10 - P0 Baseline). Refines a…

### Community 38 - "Control Controller"
Cohesion: 0.33
Nodes (4): Any, Convert pixel coordinates to angular offset relative to the optical axis…, Compute rate-limited pan/tilt velocity and displacement commands. Args:…, Initialize the PTZ controller. Args: ptz_config: Controller tuning parameters…

### Community 39 - "Simulation Model"
Cohesion: 0.29
Nodes (4): CameraPose, Immutable camera pose representation in World Coordinate System (WCS)., Ground Truth Provider — Module 14 per Architecture v1.2 §4 and §12.1b. Collects…, Simulation domain — Modules 4, 5, 6, 7, and 14 per Architecture v1.2.

### Community 40 - "Strategy Interfaces"
Cohesion: 0.33
Nodes (4): IPreprocessor, Strategy interface for preprocessing stage. Architecture v1.2 §8.2 Stage 1.…, Preprocess the input image (or ROI sub-image). Args: image: numpy ndarray (H,…, Return human-readable name for logging/reporting.

### Community 41 - "Centroid Estimator"
Cohesion: 0.33
Nodes (4): Verifies non-quantized floating point centroid output., Test 5x5, 10x10, and 20x20 targets per PS specification., Test circular, square, and Gaussian profiles., TestSubPixelPrecision

### Community 42 - "Centroid Estimator"
Cohesion: 0.33
Nodes (4): Verifies local background estimation via perimeter median., A very bright central beacon must not inflate the perimeter background estimate., The estimated centroid should remain invariant across different uniform…, TestBackgroundSubtraction

### Community 43 - "Centroid Tracker"
Cohesion: 0.50
Nodes (3): ndarray, Estimate the local background intensity from the perimeter pixels of the ROI.…, Refine candidate detection to sub-pixel centroid coordinates. Args: frame:…

### Community 44 - "Centroid Estimator"
Cohesion: 0.50
Nodes (3): Verifies estimator accuracy and error convergence with increasing SNR., Higher peak signal above noise floor leads to equal or lower estimation error., TestAccuracyAndSNR

### Community 45 - "Centroid Estimator"
Cohesion: 0.50
Nodes (3): Verifies that Module 10 has ZERO access to ground truth., Inspect centroid_estimator.py AST to ensure no GroundTruth imports exist., TestGroundTruthFirewall

## Knowledge Gaps
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppController` connect `Controller Appcontroller` to `Manager Config`, `Detect Detection`, `Simulation Disturbance`, `Tracker Manager`, `Track Tracker`, `Manager Simulation`, `Provider Frame`, `Control Controller`, `Strategy Interfaces`, `Interface Interfaces`, `Simulation Manager`, `Candidate Identifier`, `Logging Engine`, `Frame Provider`, `Simulation Provider`, `Model Camera`, `Tracker Manager`, `Control Controller`, `Frame Simulation`, `Contracts Frame`, `Logging Engine`, `Strategy Interfaces`, `Truth Ground`, `Centroid Tracker`?**
  _High betweenness centrality (0.171) - this node is a cross-community bridge._
- **Why does `ProportionalDeadbandPTZController` connect `Control Controller` to `Controller Appcontroller`, `Tracker Manager`, `Control Controller`, `Candidate Identifier`, `Control Controller`, `Control Controller`, `Tracker Manager`, `Control Controller`, `Foundation Contracts`, `Controller Testptzcontrollerfirewall`, `Controller Testptzcontrollergeometry`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `IntensityWeightedCentroidEstimator` connect `Centroid Tracker` to `Controller Appcontroller`, `Detect Detection`, `Tracker Manager`, `Track Tracker`, `Frame Contracts`, `Provider Frame`, `Strategy Interfaces`, `Candidate Identifier`, `Frame Provider`, `Tracker Manager`, `Controller Testptzcontrollerfirewall`, `Centroid Estimator`, `Centroid Estimator`, `Centroid Estimator`, `Centroid Estimator`, `Centroid Estimator`, `Centroid Estimator`, `Centroid Tracker`, `Centroid Estimator`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `AppController` (e.g. with `ConfigManager` and `SystemConfig`) actually correct?**
  _`AppController` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `ProportionalDeadbandPTZController` (e.g. with `AppController` and `CameraConfig`) actually correct?**
  _`ProportionalDeadbandPTZController` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `IntensityWeightedCentroidEstimator` (e.g. with `AppController` and `TestAccuracyAndSNR`) actually correct?**
  _`IntensityWeightedCentroidEstimator` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `P0ThresholdDetector` (e.g. with `AppController` and `TestCentroidPipelineIntegration`) actually correct?**
  _`P0ThresholdDetector` has 14 INFERRED edges - model-reasoned connections that need verification._