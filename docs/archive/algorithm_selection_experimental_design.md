# SIH 2026 — Algorithm Selection & Experimental Design Specification

## Version 1.0

> **Date:** 2026-09-04
> **Preceding Phase:** Frozen Architecture v1.2
> **Authoritative Sources:** [PS.md](file:///e:/Newfolder/Project2O/Projects/SIH%20'26/external/PS.md) > [PRD.md](file:///e:/Newfolder/Project2O/Projects/SIH%20'26/external/PRD.md) > [Engineering Context](file:///e:/Newfolder/Project2O/Projects/SIH%20'26/external/SIH_26_Engineering_Context_Technical_Model.md) > [Architecture v1.2](file:///e:/Newfolder/Project2O/Projects/SIH%20'26/external/system_architecture.md)
> **Status:** ANALYSIS COMPLETE — EXPERIMENTS REQUIRED

---

# PART 1 — PROBLEM CHARACTERISTICS

Before evaluating any algorithm, we must establish what constrains algorithm choice.

## 1.1 Target Characteristics

| Parameter | Value | Algorithm Impact |
| --- | --- | --- |
| **Target type** | Bright beacon spot on darker background | Signal-processing / point-source detection problem, NOT an object-recognition problem |
| **Minimum size** | 5×5 pixels | Extremely small; most object detectors are designed for targets ≥32×32. Only ~25 total pixels of signal. |
| **Default size** | 10×10 pixels | Small; ~100 pixels of signal |
| **Maximum size** | 20×20 pixels | Still small; ~400 pixels |
| **Shape** | Configurable, default square | Regular geometry; shape features are minimal |
| **Count** | 1 mandatory, multiple optional | Primary design for single target; identification matters when noise creates false candidates |
| **Monochrome** | Mandatory | No color features available; intensity-only processing |
| **Contrast** | Bright beacon on darker background, degraded by atmosphere | High-contrast in ideal; potentially low-contrast under fog/low-light |

### Key Insight

The beacon is a **small, bright, point-like source** — fundamentally different from the rich, textured objects that general-purpose object detectors (YOLO, SSD, Faster R-CNN) are designed to find. This is closer to a **signal detection / point-source localization** problem from astronomy or radar, not a semantic object detection problem.

At 5×5 pixels, the target contains at most 25 intensity values. There is no semantic content — no edges, textures, or shapes that deep feature extractors can meaningfully leverage. Classical signal-processing methods (thresholding, local-background estimation, matched filtering, intensity-weighted centroiding) are highly competitive in this regime.

## 1.2 Imaging Characteristics

| Parameter | Value | Algorithm Impact |
| --- | --- | --- |
| **Resolution** | Default 640×480; evaluator MP4 may differ | Must be resolution-agnostic |
| **FOV** | Default 4°×3° | Narrow FOV; small angular errors matter |
| **Frame rate** | ≥30 Hz camera generation | 33.3ms per frame; ample inter-frame information |
| **Monochrome** | Yes | Single-channel processing only |
| **Background** | Configurable intensity | Uniform or near-uniform background expected |

## 1.3 Disturbance Characteristics

| Disturbance | PS Specification | Algorithm Impact |
| --- | --- | --- |
| **Salt & Pepper noise** | ~10% of image | Creates isolated bright/dark impulse pixels; can mimic small bright targets. Median filtering highly effective. |
| **Gaussian noise** | σ up to 20 (units ambiguous) | Additive, signal-independent. Reduces SNR. Spatial averaging/filtering helps. |
| **Poisson noise** | Signal-dependent | Shot noise; worse at low signal levels. |
| **Camera jitter** | ±20 pixels/frame | Geometric displacement; causes inter-frame position jumps. Temporal filters must accommodate. |
| **Platform motion** | ±20 pixels/frame, mandatory linear | Systematic drift; compounds with jitter. |
| **Atmospheric: Clear** | Baseline | No degradation |
| **Atmospheric: Haze** | Contrast/brightness reduction | Reduced beacon visibility |
| **Atmospheric: Fog** | Stronger contrast/brightness reduction | Severely reduced beacon visibility |
| **Atmospheric: Rain** | Contrast/brightness reduction + possible artifacts | Degraded signal |
| **Atmospheric: Low light** | Brightness reduction | Very low SNR; beacon may be barely visible |

### Combined Disturbance Challenge

The worst case combines **5×5 beacon + multiple noise types + atmospheric degradation + jitter + platform motion + complex motion**. The algorithm pipeline must be robust to this combination, not just individual disturbances.

## 1.4 Performance Requirements (PS-Authoritative)

| Metric | PS Threshold | Nature |
| --- | --- | --- |
| Processing speed | ≥20 FPS | **PS requirement** |
| Acquisition time | ≤2 seconds | **PS requirement** |
| Tracking error | ≤10 pixels | **PS requirement** (definition ambiguous) |
| Target loss | <5% | **PS requirement** |
| Reacquisition time | ≤1 second | **PS requirement** |
| Camera update rate | ≥30 Hz | **PS requirement** |
| PTZ update rate | ≥20 Hz | **PS requirement** |

## 1.5 Evaluation Weight Distribution

| Stage | Weight | What Matters |
| --- | --- | --- |
| Functional Verification | 20% | All features working, GUI, live demo |
| Benchmark-1 (Simulation) | 30% | Centroiding error, performance logs |
| Benchmark-2 (Evaluator MP4) | 30% | Centroiding error vs predefined values, RMSE, acq/reacq, lock retention, FPS |
| Technical Evaluation | 20% | Architecture, algorithm selection, AI/CV, innovation, presentation |

> **60% of the total score is quantitative benchmark performance.** Algorithm selection must optimize for centroiding accuracy, RMSE, robustness, lock retention, acquisition speed, and processing FPS above all else.

## 1.6 Why YOLO/SSD/General Object Detectors Are Inappropriate

| Factor | Analysis |
| --- | --- |
| **Target size** | 5–20 px; far below the minimum effective resolution for pretrained detectors (typically ≥32×32 feature maps) |
| **Feature content** | A bright square blob has no semantic features — no edges, textures, or class-distinguishing patterns |
| **Computational cost** | Even "lightweight" detectors (YOLOv5n, MobileNet-SSD) require millions of FLOPs; overhead is unjustifiable for this task |
| **Training data** | Would require synthetic-only training; domain gap risk for evaluator MP4 |
| **Generalization** | Pretrained weights are irrelevant; would need full retraining from scratch on point-source data |
| **Latency** | Full-frame inference at 640×480 would consume most of the 50ms budget |
| **False positives** | General detectors are not designed for point-source detection in noise |

**Conclusion:** Full-frame deep-learning object detectors are **not recommended** as the primary detection method. However, AI/ML can provide genuine value in specific, targeted roles (candidate classification, false-positive rejection, learned centroiding).

---

# PART 2 — ALGORITHM CANDIDATE INVENTORY

## 2.1 Preprocessing Candidates

| ID | Method | Description | Effect on 5×5 Beacon | Noise Suppression | Centroid Preservation | Computational Cost | Failure Modes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **PP-01** | No preprocessing | Pass-through | None | None | Perfect | ~0 | Noise passes to detector |
| **PP-02** | Median filter (3×3) | Replaces each pixel with local median | Minimal effect on 5×5; may slightly smooth edges | Excellent for S&P | Very good; slight bias at beacon edge | Very low (~0.3ms at 640×480) | May slightly reduce peak intensity |
| **PP-03** | Median filter (5×5) | Larger kernel median | Noticeable smoothing of 5×5 beacon | Excellent for S&P and moderate Gaussian | Moderate; measurable centroid shift risk for 5×5 targets | Low (~0.5ms) | May suppress smallest beacons |
| **PP-04** | Gaussian blur (3×3, σ≈1) | Gaussian smoothing | Slight spreading of beacon | Moderate Gaussian noise reduction | Good; symmetric blur preserves centroid | Very low (~0.2ms) | Reduces peak intensity; spreads beacon |
| **PP-05** | CLAHE (local contrast) | Adaptive histogram equalization | Enhances local contrast of beacon | Indirect; boosts weak signal | Good | Low (~1ms) | May amplify noise in uniform regions |
| **PP-06** | Local background subtraction | Estimate and subtract local background | Isolates beacon from background; excellent for haze/fog | Reduces structured background variations | Very good | Low (~0.5ms) | Requires appropriate kernel size |
| **PP-07** | Temporal median/mean | Background estimation from N previous frames | Can separate moving beacon from static noise | Excellent for static noise patterns | Good if beacon moves | Low (requires frame buffer) | Fails if beacon is stationary; adds latency |

### Preprocessing Recommendation (Analytical)

**Primary:** PP-02 (Median 3×3) — minimal beacon distortion, excellent S&P removal, negligible cost.

**Conditional:** PP-06 (Local background subtraction) — valuable under atmospheric degradation (haze/fog/low-light) to enhance beacon-to-background contrast.

**Experimental question:** Does median filtering before detection measurably improve centroiding accuracy, or does applying centroiding to the raw frame (after detection on filtered frame) perform better?

> **NOT YET EXPERIMENTALLY VALIDATED**

---

## 2.2 Detection / Candidate Generation Candidates

### Classical Methods

| ID | Method | Description | Min Detectable Size | Gaussian Robustness | Poisson Robustness | S&P Robustness | Low-Light | Haze/Fog | False Positives | Complexity | Expected FPS | Training Required |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **DET-01** | Global threshold | Pixels above fixed intensity value | Any | Poor (threshold sensitive to noise floor) | Poor | Very poor (S&P creates bright pixels) | Very poor | Very poor | High under noise | Trivial | >1000 | No |
| **DET-02** | Adaptive threshold | Locally-adaptive threshold (mean/Gaussian weighted) | Any | Moderate | Moderate | Poor | Moderate | Moderate | Moderate | Low | >500 | No |
| **DET-03** | Otsu threshold | Automatic global threshold by class variance maximization | Any | Moderate | Moderate | Poor | Poor (bimodal assumption fails) | Poor | High if noise creates bimodal distribution | Low | >500 | No |
| **DET-04** | Connected components (on thresholded image) | Threshold → label connected regions → filter by area/intensity | 3×3 minimum practical | Depends on threshold | Depends on threshold | Poor without pre-filtering | Depends | Depends | Moderate; area filter helps | Low | >300 | No |
| **DET-05** | Blob detection (LoG/DoG) | Laplacian/Difference of Gaussians scale-space detection | 5×5 practical | Moderate (scale-space inherently smooths) | Moderate | Poor | Poor at very low contrast | Moderate | Low for well-tuned scale | Moderate | >100 | No |
| **DET-06** | Local maxima + region growing | Find intensity peaks → grow region around peak | 3×3 | Moderate | Moderate | Poor without S&P filtering | Poor | Moderate | Moderate | Low | >300 | No |
| **DET-07** | Morphological top-hat | White top-hat filter to extract bright features on dark background | 5×5 with appropriate structuring element | Good | Good | Moderate | Moderate | Good (removes background) | Low | Low-Moderate | >200 | No |
| **DET-08** | Matched filter / template correlation | Convolve frame with expected beacon template (e.g., square kernel) | 5×5 with matching template | Very good (averaging effect) | Good | Moderate (pre-filter S&P first) | Moderate | Good | Low (high SNR gain) | Moderate | >100 | No (template from config) |
| **DET-09** | CFAR-style detection | Constant False Alarm Rate: compare pixel/region to local background statistics | 3×3 | Very good (adapts to local noise) | Very good | Moderate (needs S&P pre-filter) | Good (adapts to local brightness) | Very good (adapts to fog/haze) | Very low (controlled by design) | Moderate | >100 | No |
| **DET-10** | Local background + threshold | Estimate local mean/median → detect pixels exceeding local mean by k·σ | 3×3 | Good | Good | Moderate | Good | Good | Low | Low | >200 | No |

### AI/ML Methods

| ID | Method | Description | Min Detectable Size | Robustness | False Positives | Complexity | Expected FPS | Training Required |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **DET-11** | Tiny patch-based CNN classifier | Classical generates candidates → extract small patches → CNN binary classifier (beacon vs noise) | 5×5 (operates on candidate patches, not full frame) | Potentially very good if well-trained | Potentially very low | Moderate (training pipeline required) | >50 (inference on patches only) | Yes — synthetic data from simulator |
| **DET-12** | SVM on hand-crafted features | Extract features (peak intensity, area, local contrast, shape compactness) → SVM classifier | 5×5 | Good | Low | Low-Moderate | >200 | Yes — labeled candidate patches |
| **DET-13** | Random Forest on features | Same features as SVM → RF classifier | 5×5 | Good | Low | Low | >200 | Yes — labeled candidates |

### Detection Analysis

**Most promising classical methods for this problem domain:**

1. **DET-09 (CFAR-style):** Explicitly designed for detecting small targets against varying backgrounds. Adapts to local noise statistics. Used extensively in radar and infrared search/track (IRST) systems — which is the closest analog to this problem. Controls false alarm rate by design.

2. **DET-08 (Matched filter):** Provides optimal SNR gain for targets of known shape. The beacon shape is configurable but known (default: square). Maximizes detection probability for a given false alarm rate. Well-established in signal detection theory.

3. **DET-10 (Local background + threshold):** Simple, fast, effective. Adapts to atmospheric conditions implicitly. Combined with area filtering, provides good false-positive control.

4. **DET-07 (Morphological top-hat):** Excellent at extracting small bright features from non-uniform backgrounds. Naturally robust to atmospheric degradation.

5. **DET-04 (Connected components):** Fast and reliable after proper thresholding. Area filter naturally rejects isolated S&P noise pixels. Provides bounding boxes for centroiding.

**Most promising AI/ML methods:**

1. **DET-12/DET-13 (SVM/RF on hand-crafted features):** Lightweight, fast inference, minimal training data, interpretable. Good as a secondary validation stage.

2. **DET-11 (Tiny CNN):** Potentially the strongest false-positive rejection under complex noise, but requires training pipeline and risks overfitting to simulator-specific distributions.

> **NOT YET EXPERIMENTALLY VALIDATED**

---

## 2.3 Beacon Identification Candidates

Identification answers: "This candidate is actually the designated beacon, not noise."

| ID | Method | Description | Strengths | Weaknesses |
| --- | --- | --- | --- | --- |
| **ID-01** | Highest-intensity candidate | Select the candidate with highest peak/mean intensity | Simple; usually correct when noise is moderate | Fails when S&P or noise creates brighter false candidates |
| **ID-02** | Size/shape filter | Accept candidates matching expected beacon size (configurable) | Rejects noise clusters that are too small or too large | Fails when noise creates clusters of similar size |
| **ID-03** | Local contrast ratio | Beacon-to-local-background intensity ratio must exceed threshold | Robust under atmospheric degradation | Threshold tuning; fails at very low contrast |
| **ID-04** | Nearest to predicted position | Use temporal tracker's predicted next position to gate candidates | Very robust after initial acquisition; reduces search space | Cannot help during initial acquisition (no prediction yet) |
| **ID-05** | Velocity consistency | Candidate's motion must be consistent with recent velocity estimate | Rejects candidates that suddenly appear far from expected trajectory | Fails for random motion with abrupt changes |
| **ID-06** | Multi-frame persistence | Candidate must appear in N consecutive frames at consistent location | Excellent false-positive rejection; noise is typically transient | Adds N frames of identification latency; delays acquisition |
| **ID-07** | Spatial neighborhood statistics | Beacon should have a bright core surrounded by darker neighborhood | Distinguishes beacon from uniform bright regions | May fail if beacon is at image edge or if background is non-uniform |
| **ID-08** | Combined rule-based scoring | Weighted combination of intensity, size, shape, local contrast, spatial consistency, temporal consistency | Flexible; tunable; covers multiple failure modes | Many parameters to tune |
| **ID-09** | Lightweight ML classifier (SVM/RF) | Features: intensity, area, compactness, local contrast, temporal persistence → binary classification | Can learn complex decision boundaries; potentially more robust than hand-tuned rules | Requires training data; risk of overfitting |
| **ID-10** | Hybrid: rule-based filter + temporal validation | Stage 1: rule-based filter on intensity/size/contrast → Stage 2: temporal consistency over N frames → confirm | Layered defense: fast rejection of obvious noise, robust confirmation via temporal evidence | Multi-frame delay; parameter tuning |

### Identification Recommendation (Analytical)

**Primary:** ID-10 (Hybrid rule-based + temporal validation)

Rationale:
- Rule-based stage provides fast, interpretable first filter.
- Temporal validation provides robust confirmation without ML training.
- Naturally integrates with the five-state tracking state machine (SEARCHING → ACQUIRING requires consecutive detections).
- During TRACKING state, ID-04 (nearest to predicted position) naturally takes over.

**AI enhancement:** ID-09 can replace or augment the rule-based stage if experiments show measurable improvement.

> **NOT YET EXPERIMENTALLY VALIDATED**

---

## 2.4 Centroid Estimation Candidates

This is one of the most benchmark-critical stages. Centroiding error is explicitly evaluated.

| ID | Method | Description | Sub-Pixel Accuracy | Noise Sensitivity | Beacon Size Sensitivity | Asymmetry Sensitivity | Clipping Sensitivity | Computational Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **CE-01** | Bounding-box center | Center of detected bounding box | None (integer pixel) | Low (robust but imprecise) | Low | High (asymmetric box → biased center) | High | Negligible |
| **CE-02** | Binary centroid | Centroid of thresholded binary region | Fractional pixel, but quantized | Low | Moderate | Moderate | Moderate | Very low |
| **CE-03** | Intensity-weighted centroid (IWC) | Σ(I·x)/Σ(I), Σ(I·y)/Σ(I) over beacon region | Good sub-pixel accuracy | Moderate (noise pixels bias estimate) | Good for 5–20 px | Handles asymmetry naturally | Moderate (biased toward visible portion) | Very low (<0.1ms) |
| **CE-04** | Image moments (first-order) | Same as IWC mathematically; using moment formulation | Good sub-pixel accuracy | Same as IWC | Good | Good | Moderate | Very low |
| **CE-05** | 2D Gaussian fitting | Fit I(x,y) = A·exp(-((x-x₀)²+(y-y₀)²)/(2σ²)) + B | Excellent sub-pixel accuracy when beacon is Gaussian-like | Moderate (fitting can be sensitive to outliers) | Excellent for 10–20 px; marginal for 5×5 (few data points) | Assumes radial symmetry | Moderate (biased if beacon partially visible) | Moderate (~0.5–1ms, iterative solver) |
| **CE-06** | Weighted Gaussian fitting | Gaussian fit with intensity-based weights or robust fitting | Excellent sub-pixel accuracy | Better than unweighted Gaussian | Good | Better than CE-05 | Moderate | Moderate |
| **CE-07** | Parabolic/quadratic interpolation | Fit parabola to peak row and column independently | Good sub-pixel accuracy; very fast | Good (averaging effect) | Good | Poor (assumes separable symmetry) | Poor | Very low (<0.1ms) |
| **CE-08** | Local correlation centroid | Cross-correlate beacon region with template; find peak of correlation surface with sub-pixel interpolation | Excellent sub-pixel accuracy | Very good (correlation averages noise) | Good | Moderate | Moderate | Low-Moderate (~0.5ms) |
| **CE-09** | Learned centroid regression (tiny MLP) | Train a small neural network to predict (Δx, Δy) offset from bounding-box center | Potentially excellent if well-trained | Potentially excellent (learns to ignore noise) | Can generalize across sizes | Can learn asymmetry | Unknown — needs experimental validation | Low (~0.1ms for tiny MLP) |

### Centroid Estimation Analysis

**Critical distinction (from Architecture v1.2 §12.1b):**

1. **True target/world position** — the 3D/2D position of the beacon in the simulation world.
2. **Ideal projected image position** — the mathematically perfect projection onto the image plane.
3. **Rendered beacon/intensity centroid** — the actual center of mass of the beacon's intensity on the pixel grid (affected by finite size, discretization, sub-pixel rendering).
4. **Estimated centroid** — what the tracker produces.

The benchmark likely evaluates ‖estimated centroid − some reference position‖. The exact reference (ideal projected? rendered centroid?) is **AMBIGUOUS/PROVISIONAL** in the PS. The architecture retains this distinction.

**Analysis for the most promising methods:**

| Method | 5×5 Beacon | 10×10 Beacon | 20×20 Beacon | Under Noise | Recommendation |
| --- | --- | --- | --- | --- | --- |
| CE-03 (IWC) | Good; enough pixels for reasonable centroid | Excellent | Excellent | Moderate; noise pixels bias result | **Strong baseline — implement first** |
| CE-05 (Gaussian fit) | Marginal; only 25 data points, fit may be unstable | Good | Excellent | Moderate | **Second priority — test on ≥10×10** |
| CE-07 (Parabolic) | Acceptable | Good | Good | Good | **Fast fallback** |
| CE-08 (Correlation) | Good | Good | Good | Very good | **Investigate if IWC insufficient** |
| CE-09 (Learned) | Unknown | Unknown | Unknown | Unknown | **P2 experimental — only if time permits** |

### Centroid Recommendation (Analytical)

**Primary:** CE-03 (Intensity-weighted centroid) with local background subtraction.

Rationale:
- Mathematically principled for bright-spot localization.
- Sub-pixel accuracy proportional to SNR.
- Extremely fast (<0.1ms).
- Background subtraction before IWC removes bias from non-zero background.
- Well-established in astronomical centroiding (the closest analogous domain).

**Enhancement:** Apply IWC on the **raw (unfiltered) frame** within the detected bounding box, after subtracting local background. Use the median-filtered frame for detection only. This preserves the full intensity signal for centroiding.

**Secondary:** CE-05 (Gaussian fit) for 10×10 and 20×20 beacons where sufficient data points exist.

**Experimental question:** Does Gaussian fitting outperform IWC on realistic noise levels for 10×10 default beacon? Is the improvement worth the computational cost?

> **NOT YET EXPERIMENTALLY VALIDATED**

---

## 2.5 Temporal Tracking Candidates

| ID | Method | Description | Straight Line | Circular | Figure-8 | Random | Abrupt Changes | Jitter Robustness | Reacquisition | Computational Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **TT-01** | No temporal filter | Each frame independent | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Zero |
| **TT-02** | Exponential moving average (EMA) | Smoothed position: x̂ₜ = α·xₜ + (1-α)·x̂ₜ₋₁ | Good smoothing | Good | Good | Moderate (lags behind direction changes) | Poor (lags) | Good (smooths jitter) | Fast (no prediction) | Negligible |
| **TT-03** | α-β filter | Estimates position and velocity; applies smoothing and prediction | Very good | Very good | Good | Good | Moderate (velocity estimate lags) | Very good | Good (velocity-based prediction) | Very low |
| **TT-04** | Kalman filter (constant velocity model) | Optimal linear estimator under Gaussian noise; predicts and corrects | Excellent | Excellent | Good | Good (adapts velocity) | Moderate (CV model overshoots on turns) | Excellent (measurement noise modeled) | Very low (<0.1ms) |
| **TT-05** | Kalman filter (constant acceleration model) | Second-order model; handles acceleration | Excellent | Excellent | Excellent | Good | Better than CV model | Excellent | Good | Very low |
| **TT-06** | Predictive ROI | Use predicted position to limit detection search area | N/A (augments detection, not tracking per se) | | | | ROI may miss target after abrupt change | Reduces computation | Requires full-frame fallback on miss | Reduces detection cost |
| **TT-07** | Adaptive ROI | ROI size adapts based on tracking confidence and velocity | N/A (augments detection) | | | | Better than fixed ROI | Good | Full-frame search when confidence drops | Slightly more complex |
| **TT-08** | Kalman + Adaptive ROI | Kalman prediction defines ROI center; ROI size adapts | Excellent | Excellent | Very good | Good | Good with ROI expansion on uncertainty | Excellent | ROI expands to full-frame on loss | Low |
| **TT-09** | Candidate gating | Accept detection only if within predicted gate (Mahalanobis distance from prediction) | Excellent false-positive rejection | Excellent | Good | Moderate (gate may reject valid detections on abrupt turns) | Poor (tight gate rejects valid target) | Good | Must relax gate on loss | Very low |

### Temporal Tracking Recommendation (Analytical)

**Primary:** TT-08 (Kalman filter with constant-velocity model + Adaptive ROI)

Rationale:
- Kalman filter is the optimal linear estimator for this problem class (Gaussian measurement noise, approximately linear motion over short intervals).
- Constant-velocity model handles straight-line, circular, and figure-8 motion well (these are locally linear at 30 Hz).
- Random motion is the hardest case, but at 30 Hz the inter-frame displacement is small enough that CV model is adequate.
- Adaptive ROI provides dual benefit: computational savings during tracking, full-frame search during acquisition/reacquisition.
- Well-understood, highly implementable, debuggable, and explainable.

**Process noise tuning:** The Kalman process noise parameter Q controls how quickly the filter adapts to velocity changes. Higher Q → more responsive but noisier; lower Q → smoother but slower to adapt. This must be tuned experimentally per motion pattern.

**Enhancement:** TT-09 (Candidate gating) can be layered on top: during TRACKING state, accept only detections within the Kalman prediction gate. This dramatically reduces false-positive susceptibility. Gate should widen during REACQUIRING.

> **NOT YET EXPERIMENTALLY VALIDATED**

---

## 2.6 PTZ Control Candidates

| ID | Method | Description | Convergence | Overshoot | Oscillation | Steady-State Error | Noise Response | Complexity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **PTZ-01** | Proportional (P) | Command proportional to image-space error | Fast | Moderate | Moderate | Non-zero (tracking moving target) | Moderate (amplifies noise) | Trivial |
| **PTZ-02** | Dead-band proportional | P control with dead-band near center; no command if error < threshold | Moderate | Low | Very low | Bounded by dead-band | Excellent (ignores noise near center) | Very low |
| **PTZ-03** | PI controller | Proportional + integral term to eliminate steady-state error | Good | Moderate-High (integral wind-up risk) | Moderate | Zero (integral eliminates it) | Poor (integrates noise) | Low |
| **PTZ-04** | PID controller | PI + derivative term for damping | Good | Low-Moderate (D term damps) | Low | Zero | Moderate (D term amplifies high-freq noise) | Low-Moderate |
| **PTZ-05** | Predictive controller | Use velocity estimate to predict target position; lead the target | Very good for smooth motion | Low | Low | Very low | Moderate | Moderate |
| **PTZ-06** | Rate-limited proportional | P control with rate limiting to prevent jerk | Good | Very low | Very low | Non-zero | Good | Very low |

### PTZ Control Analysis

**Key constraints from PS:**
- Max pan speed: 5–10°/s (default 5°/s)
- Max tilt speed: 5–10°/s (default 5°/s)
- Update rate: ≥20 Hz

At default FOV (4°×3°) and resolution (640×480): 1 pixel ≈ 0.00625°. Max speed = 5°/s = 800 pixels/s ≈ 26.7 px/frame at 30 Hz.

**Critical consideration:** The PTZ controller receives **noisy centroid estimates** from the tracker. An overly responsive controller will amplify measurement noise into camera jitter. A dead-band or rate-limited controller provides natural noise rejection.

### PTZ Recommendation (Analytical)

**Primary:** PTZ-02 (Dead-band proportional) + rate limiting from architecture.

Rationale:
- Simple, robust, predictable.
- Dead-band prevents hunting/oscillation when beacon is near center.
- Rate limiting is already enforced by the architecture (max pan/tilt speed).
- Steady-state error is bounded by the dead-band but acceptable (beacon stays near center, not exactly at center — this is coarse alignment).

**Enhancement:** PTZ-05 (Predictive) if experiments show that the P-controller cannot track fast-moving targets. Use the Kalman filter's velocity estimate to predict the target's position and lead the camera.

**Experimental question:** Does the dead-band P-controller achieve ≤10 pixel tracking error for all motion patterns at default speed? If not, predictive control is needed.

> **NOT YET EXPERIMENTALLY VALIDATED**

---

# PART 3 — RECOMMENDED PIPELINE COMBINATIONS

## 3.1 Baseline Pipeline (P0 — Must implement first)

```text
Frame
  │
  ├─── Preprocessing: Median 3×3 (PP-02)
  │
  ├─── Candidate Generation: Local background + threshold (DET-10)
  │                          + Connected components (DET-04)
  │                          + Area/intensity filter
  │
  ├─── Beacon Identification: Rule-based scoring (ID-08)
  │                           + Nearest-to-predicted (ID-04) during TRACKING
  │
  ├─── Centroid Estimation: Intensity-weighted centroid (CE-03)
  │                         with local background subtraction
  │
  ├─── Temporal Tracking: Kalman filter CV model (TT-04)
  │                       + Adaptive ROI (TT-07)
  │
  ├─── Confidence/State: Threshold-based with hysteresis
  │
  └─── PTZ Control: Dead-band proportional (PTZ-02)
```

**Why this baseline:**
- Every component is well-understood, fast, and implementable.
- No ML training required.
- Expected to meet ≥20 FPS comfortably (<12ms total pipeline).
- Provides measurable baseline for all metrics.
- Can be implemented and tested quickly.

## 3.2 Enhanced Pipeline (P1 — Implement after baseline works)

```text
Frame
  │
  ├─── Preprocessing: Median 3×3 + conditional local background subtraction
  │                   (enable background subtraction when atmospheric mode ≠ Clear)
  │
  ├─── Candidate Generation: CFAR-style detection (DET-09) or
  │                          Matched filter (DET-08) — whichever experiments show is better
  │
  ├─── Detection/Classification: SVM/RF on hand-crafted features (DET-12/DET-13)
  │                              for candidate validation
  │
  ├─── Beacon Identification: Rule-based + temporal validation (ID-10)
  │                           + Kalman-gated association (TT-09)
  │
  ├─── Centroid Estimation: IWC with local background subtraction (CE-03)
  │                         + Gaussian fitting (CE-05) for ≥10×10 beacons
  │
  ├─── Temporal Tracking: Kalman filter (TT-04) + Adaptive ROI (TT-07)
  │                       + Candidate gating (TT-09)
  │
  ├─── Confidence/State: Hysteresis with configurable thresholds
  │
  └─── PTZ Control: Dead-band proportional (PTZ-02) + velocity feedforward (PTZ-05)
```

## 3.3 Experimental / Innovation Pipeline (P2 — If time permits)

```text
Frame
  │
  ├─── Preprocessing: Adaptive (select strategy based on detected noise type)
  │
  ├─── Candidate Generation: CFAR + Matched filter ensemble
  │
  ├─── Classification: Tiny CNN classifier on candidate patches (DET-11)
  │
  ├─── Centroid: Learned centroid regression (CE-09)
  │              or IWC + Gaussian fit ensemble
  │
  ├─── Tracking: Adaptive Kalman (Q auto-tuned based on motion estimate)
  │
  └─── PTZ: Predictive controller with Kalman velocity estimate
```

---

# PART 4 — EXPERIMENTAL METHODOLOGY

## 4.1 Core Principle

Every algorithm comparison must use **the exact same input data**.

```text
Same scenario → same frames → same timestamps → same ground truth → different algorithm
```

The Algorithm Evaluation Harness (development infrastructure defined in Architecture v1.2 §19.2) provides this capability by replaying identical recordings.

## 4.2 Experiment Protocol

1. **Define scenario** — specify all parameters (scene, target, motion, disturbances, duration).
2. **Record scenario** — run simulation, capture frame sequence + ground truth.
3. **Replay through Algorithm A** — process recorded frames, collect metrics.
4. **Replay through Algorithm B** — identical frames, collect metrics.
5. **Compare** — same MetricsEngine, same metric definitions.

## 4.3 Statistical Design

For scenarios involving stochastic disturbances (noise, jitter, platform motion, random target motion):

- **Minimum 10 repetitions** per scenario per algorithm, using different random seeds.
- **Record the random seeds** used for each run.
- **Report:** mean, standard deviation, median, min, max, 95th percentile.
- **Use identical seeds** when comparing algorithms (Algorithm A seed=42 vs Algorithm B seed=42).
- **Significance:** If the difference in mean performance between algorithms is less than 1σ, consider them statistically equivalent.

### Recommended repetition count

| Scenario complexity | Repetitions | Justification |
| --- | --- | --- |
| Ideal (deterministic) | 1 | No randomness |
| Single disturbance | 10 | Sufficient for stable statistics |
| Combined disturbances | 20 | Higher variance requires more samples |
| Stress test | 30 | Must characterize worst-case distribution |

## 4.4 Measurement Duration

Each experimental run should last at least:

- **10 seconds** for basic scenarios (300 frames at 30 Hz).
- **30 seconds** for tracking performance scenarios (capture acquisition, steady-state tracking, and at least one loss/reacquisition event if possible).
- **60 seconds** for stress tests (capture long-term stability and rare failure events).

---

# PART 5 — TEST SCENARIO LADDER

## Level 0 — Ideal Conditions (Correctness Validation)

| Scenario | Parameters | Purpose |
| --- | --- | --- |
| **L0-01** | 10×10 beacon, no noise, no atmosphere, no jitter, no platform motion, straight-line motion, centered start | Verify basic detection, centroiding, tracking, and PTZ control work correctly |
| **L0-02** | Same as L0-01 but beacon starts off-center (random position) | Verify acquisition |
| **L0-03** | Same as L0-01 with circular motion | Verify curved-motion tracking |
| **L0-04** | Same as L0-01 with figure-8 motion | Verify complex-motion tracking |
| **L0-05** | Same as L0-01 with random motion | Verify adaptive tracking |

**Pass criteria:** Detection rate = 100%. Centroiding error ≤ 1 pixel. Tracking error ≤ 5 pixels. Acquisition ≤ 0.5s. FPS > 30.

## Level 1 — Target Size Sensitivity

| Scenario | Beacon Size | Other Parameters | Purpose |
| --- | --- | --- | --- |
| **L1-01** | 5×5 | No disturbances, straight-line | Minimum target size |
| **L1-02** | 10×10 | No disturbances, straight-line | Default target size |
| **L1-03** | 15×15 | No disturbances, straight-line | Medium target |
| **L1-04** | 20×20 | No disturbances, straight-line | Maximum target size |

**Pass criteria:** All sizes detected and tracked. Measure centroiding error vs size.

## Level 2 — Individual Noise

| Scenario | Noise Type | Parameters | Purpose |
| --- | --- | --- | --- |
| **L2-G1** | Gaussian only | σ=5 | Low Gaussian noise |
| **L2-G2** | Gaussian only | σ=10 | Moderate Gaussian |
| **L2-G3** | Gaussian only | σ=20 | Maximum Gaussian (PS limit) |
| **L2-P1** | Poisson only | Default signal-dependent model | Poisson noise |
| **L2-S1** | S&P only | Density=2% | Low S&P |
| **L2-S2** | S&P only | Density=5% | Moderate S&P |
| **L2-S3** | S&P only | Density=10% | PS suggested S&P level |

**Use:** 10×10 beacon, straight-line motion.

## Level 3 — Atmospheric Conditions

| Scenario | Condition | Parameters | Purpose |
| --- | --- | --- | --- |
| **L3-01** | Clear | No degradation | Baseline |
| **L3-02** | Haze | Moderate contrast/brightness reduction | Mild degradation |
| **L3-03** | Fog | Severe contrast/brightness reduction | Heavy degradation |
| **L3-04** | Rain | Moderate reduction + possible artifacts | Weather degradation |
| **L3-05** | Low light | Severe brightness reduction | Low-SNR regime |

**Use:** 10×10 beacon, straight-line motion, no noise.

## Level 4 — Geometric Disturbances

| Scenario | Disturbance | Parameters | Purpose |
| --- | --- | --- | --- |
| **L4-01** | Camera jitter only | ±5 px/frame | Low jitter |
| **L4-02** | Camera jitter only | ±20 px/frame | Maximum jitter |
| **L4-03** | Platform motion only | ±5 px/frame, linear | Low platform motion |
| **L4-04** | Platform motion only | ±20 px/frame, linear | Maximum platform motion |
| **L4-05** | Jitter + platform | ±10 each | Combined geometric |
| **L4-06** | Jitter + platform | ±20 each | Maximum combined geometric |

**Use:** 10×10 beacon, straight-line target motion, no noise, clear atmosphere.

## Level 5 — Motion Complexity

| Scenario | Motion Pattern | Speed | Purpose |
| --- | --- | --- | --- |
| **L5-01** | Straight line | Low (~5 px/frame) | Basic linear |
| **L5-02** | Straight line | High (~15 px/frame) | Fast linear |
| **L5-03** | Circular | Moderate radius, moderate speed | Curved motion |
| **L5-04** | Figure-8 | Moderate | Complex periodic |
| **L5-05** | Random | Moderate displacement variance | Unpredictable motion |
| **L5-06** | Random | High displacement variance | Challenging unpredictable motion |

**Use:** 10×10 beacon, no disturbances.

## Level 6 — Combined Disturbances

| ID | Beacon | Noise | Atmosphere | Geometric | Motion | Difficulty |
| --- | --- | --- | --- | --- | --- | --- |
| **C1** | 5×5 | Gaussian σ=10 | Clear | None | Straight | Moderate |
| **C2** | 5×5 | S&P 10% | Clear | None | Straight | Moderate |
| **C3** | 5×5 | None | Low light | None | Straight | Moderate |
| **C4** | 10×10 | Gaussian σ=10 | Clear | Jitter ±10 | Circular | Moderate-Hard |
| **C5** | 10×10 | Gaussian σ=10 + S&P 5% | Clear | Platform ±10 | Figure-8 | Hard |
| **C6** | 5×5 | Gaussian σ=10 | Low light | Jitter ±10 | Straight | Hard |
| **C7** | 5×5 | Gaussian σ=10 + S&P 5% | Haze | Jitter ±10 + Platform ±10 | Circular | Very Hard |
| **C8** | 5×5 | Gaussian σ=20 + S&P 10% + Poisson | Fog | Jitter ±20 + Platform ±20 | Random | Extreme |

---

# PART 6 — STRESS TEST DESIGN

## 6.1 Worst-Case Scenario Definition

The most challenging operational condition is:

**Scenario STRESS-01:**
- Beacon: 5×5 (minimum)
- Gaussian noise: σ=20 (PS maximum)
- S&P noise: 10% (PS suggested)
- Poisson noise: enabled
- Atmospheric: Fog or Low light (worst visibility)
- Camera jitter: ±20 px/frame (PS maximum)
- Platform motion: ±20 px/frame (PS maximum)
- Target motion: Random (most unpredictable)
- Duration: 60 seconds

**Why this is the hardest case:**

| Factor | Challenge |
| --- | --- |
| 5×5 beacon | Only 25 pixels of signal |
| Gaussian σ=20 | A 5×5 beacon with intensity ~200 has SNR ≈ 200/20 = 10:1 in ideal. With background subtraction needed, effective SNR is lower. |
| S&P 10% | ~30,000 corrupted pixels per frame; many will be bright, creating false candidates |
| Fog | Reduces contrast further, potentially to the point where beacon is barely distinguishable |
| ±20 px jitter + ±20 px platform | Up to ±40 px of geometric displacement per frame; the beacon can move up to 40 px between frames from geometric disturbances alone |
| Random motion | No predictable trajectory; Kalman velocity estimate is unreliable |

**This scenario may be close to the limits of algorithmic feasibility.** The purpose is not to guarantee perfect performance but to characterize failure modes and degradation.

## 6.2 Additional Stress Tests

**STRESS-02:** Same as STRESS-01 but with 10×10 beacon. Tests whether doubling target area provides sufficient improvement.

**STRESS-03:** 5×5 beacon, moderate noise (Gaussian σ=10, S&P 5%), no atmosphere, maximum jitter + platform. Isolates geometric disturbance stress.

**STRESS-04:** 5×5 beacon, maximum noise, low light, no geometric disturbances. Isolates radiometric stress.

---

# PART 7 — METRICS SPECIFICATION

> [!IMPORTANT]
> All metric definitions below are **PROPOSED / PROVISIONAL**. The PS does not fully define centroiding error, tracking error, or RMSE calculation methods. Definitions must remain replaceable per Architecture v1.2.

## 7.1 Detection Metrics

| Metric | Definition | Unit |
| --- | --- | --- |
| Detection probability / recall | Frames with beacon correctly detected / total frames where beacon is present | Proportion (0–1) |
| False positive rate | Frames with false detection (no beacon present but detection reported) / total frames | Proportion |
| Candidate count (mean) | Average number of candidates per frame before identification | Count |
| Detection latency | Time from frame input to detection result | ms |

## 7.2 Centroiding Metrics

| Metric | Definition | Unit |
| --- | --- | --- |
| Centroiding error (per-frame) | ‖estimated centroid − reference position‖₂ | pixels |
| Mean centroiding error | Mean of per-frame CE over evaluated frames | pixels |
| Median centroiding error | Median of per-frame CE | pixels |
| RMSE | √(Σ CEᵢ² / N) | pixels |
| Maximum centroiding error | Max per-frame CE | pixels |
| % within 1 pixel | Fraction of frames with CE < 1 | % |
| % within 2 pixels | Fraction of frames with CE < 2 | % |
| % within 5 pixels | Fraction of frames with CE < 5 | % |

> **Reference position ambiguity:** The "reference position" for centroiding error could be the ideal projected image position or the rendered intensity centroid. Both should be logged. The final evaluator definition is unknown.

## 7.3 Tracking Metrics

| Metric | Definition | Unit |
| --- | --- | --- |
| Tracking error (per-frame) | ‖estimated centroid − image center‖₂ (beacon offset from camera center) | pixels |
| Mean tracking error | Mean of per-frame TE | pixels |
| Maximum tracking error | Max per-frame TE | pixels |
| Lock retention rate | Frames in TRACKING state / total frames after initial acquisition | % |
| Target loss rate | 1 − lock retention rate | % |
| Track continuity | Longest consecutive TRACKING sequence / total frames | ratio |

## 7.4 Acquisition Metrics

| Metric | Definition | Unit |
| --- | --- | --- |
| Acquisition time | Time from simulation/video start to first TRACKING state | seconds |
| Reacquisition time (per event) | Time from LOST entry to next TRACKING entry | seconds |
| Mean reacquisition time | Average over all reacquisition events | seconds |
| Maximum reacquisition time | Worst-case reacquisition | seconds |

## 7.5 Performance Metrics

| Metric | Definition | Unit |
| --- | --- | --- |
| Processing FPS | 1 / (mean per-frame processing time) | frames/s |
| Per-stage latency | Processing time for each pipeline stage | ms |
| End-to-end latency | Total pipeline processing time per frame | ms |
| 95th percentile latency | | ms |
| Maximum latency | Worst-case frame processing time | ms |

## 7.6 PTZ Metrics

| Metric | Definition | Unit |
| --- | --- | --- |
| Convergence time | Time from acquisition to tracking error < threshold | seconds |
| Overshoot | Maximum tracking error excursion during convergence | pixels |
| Steady-state error | Mean tracking error during stable TRACKING | pixels |
| Oscillation measure | Standard deviation of tracking error during stable tracking | pixels |

---

# PART 8 — ABLATION STUDY DESIGN

Each ablation tests whether a specific component provides measurable benefit.

| Ablation | Configuration A (without) | Configuration B (with) | Metric to Compare | Hypothesis |
| --- | --- | --- | --- | --- |
| **ABL-01: Median preprocessing** | No preprocessing → detection | Median 3×3 → detection | Detection rate, centroiding error under S&P | Median filter significantly improves S&P robustness without harming centroid accuracy |
| **ABL-02: Local background subtraction** | Direct threshold | Local background subtraction → threshold | Detection rate under fog/haze/low-light | Background subtraction critical for atmospheric degradation |
| **ABL-03: CFAR vs global threshold** | Global threshold detection | CFAR detection | False positive rate, detection rate under varying noise | CFAR significantly reduces false positives |
| **ABL-04: Matched filter vs threshold** | Threshold + connected components | Matched filter detection | SNR gain, detection rate for 5×5 beacon under noise | Matched filter improves detection of smallest targets |
| **ABL-05: ML candidate classifier** | Rule-based identification only | Rule-based + SVM/RF classifier | False positive rate, identification accuracy | ML classifier reduces false positives |
| **ABL-06: IWC vs bounding-box center** | Bounding-box center centroid | Intensity-weighted centroid | Centroiding error (RMSE) | IWC provides meaningful sub-pixel improvement |
| **ABL-07: Gaussian fit vs IWC** | IWC centroid | Gaussian-fit centroid | Centroiding error for 10×10 and 20×20 beacons | Gaussian fit may improve accuracy for larger beacons |
| **ABL-08: Kalman filter vs no filter** | No temporal filter | Kalman filter (CV model) | Tracking error, lock retention, reacquisition time | Kalman filter significantly improves tracking stability |
| **ABL-09: Adaptive ROI** | Full-frame detection every frame | Kalman-predicted adaptive ROI | Processing FPS, false positive rate | ROI reduces computation and false positives |
| **ABL-10: Dead-band vs pure proportional PTZ** | Proportional PTZ | Dead-band proportional PTZ | Steady-state oscillation, tracking error | Dead-band reduces hunting/oscillation |
| **ABL-11: Temporal identification** | Single-frame identification | Multi-frame temporal identification (ID-10) | False lock rate, acquisition time | Temporal validation reduces false locks at cost of slightly longer acquisition |

---

# PART 9 — AI/ML EXPERIMENT DESIGN

## 9.1 Training Data Generation Strategy

The simulator serves as an unlimited synthetic data generator.

### Dataset structure

| Dataset | Purpose | Generation Method |
| --- | --- | --- |
| **Training set** | Train classifier/regressor | Simulate 10,000+ frames across diverse conditions |
| **Validation set** | Tune hyperparameters | Separate 2,000+ frames with different random seeds |
| **Test set** | Final evaluation | Independent 2,000+ frames with seeds never used in training |

### Randomization dimensions

- Target size: uniform random in [5, 20]
- Target position: uniform random across image
- Noise type: random selection and combination
- Noise intensity: random within PS ranges
- Atmospheric condition: random selection
- Background intensity: random variation
- Motion pattern: random selection

### Critical: Prevent train/test leakage

- Training, validation, and test sets must use **completely disjoint random seeds**.
- Do not share frames, scenarios, or noise realizations between sets.
- The test set should include conditions not seen in training (e.g., novel combinations).

## 9.2 ML Candidate Classifier Experiment

**Objective:** Determine if an ML classifier provides measurable improvement over rule-based identification.

### Experiment ML-01: SVM/RF Feature Classifier

**Features per candidate:**
1. Peak intensity
2. Mean intensity within bounding box
3. Area (pixel count)
4. Compactness (area / bounding-box area)
5. Local contrast (mean beacon intensity / mean local background intensity)
6. Intensity variance within region
7. Distance from image center
8. Distance from predicted position (if available)

**Protocol:**
1. Generate candidate patches from diverse simulation conditions.
2. Label candidates as "beacon" or "noise" using ground truth.
3. Train SVM and Random Forest separately.
4. Evaluate precision, recall, F1 on independent test set.
5. Measure inference time per candidate.
6. Compare end-to-end pipeline metrics (detection rate, false positive rate, centroiding RMSE) vs rule-based baseline.

### Experiment ML-02: Tiny CNN Patch Classifier

**Architecture:** Simple CNN (e.g., 2 conv layers + 1 FC layer, <10K parameters)

**Input:** Small image patch centered on candidate (e.g., 32×32 or 24×24 pixels extracted around each candidate).

**Output:** Binary classification (beacon vs noise) + confidence score.

**Protocol:**
1. Extract positive patches (centered on beacon) and negative patches (noise candidates).
2. Apply data augmentation: random intensity scaling, noise injection, position jitter.
3. Train with binary cross-entropy loss.
4. Evaluate on independent test set.
5. Measure inference latency per patch and per frame.
6. Compare vs SVM/RF classifier and rule-based baseline.

### Experiment ML-03: Learned Centroid Regression

**Architecture:** Tiny MLP or small CNN that takes a beacon patch and outputs (Δx, Δy) sub-pixel offset.

**Training data:** Pairs of (beacon patch, true sub-pixel centroid offset).

**Protocol:**
1. Generate training data from simulator with known true positions.
2. Train regression model.
3. Compare centroiding RMSE vs IWC and Gaussian fit on independent test set.
4. Evaluate under various noise levels and beacon sizes.

## 9.3 Domain Generalization Concern

The most critical risk for any ML approach:

> **Will a model trained on simulator-generated data generalize to the evaluator's MP4 files?**

The evaluator's MP4 may have different:
- noise characteristics
- background patterns
- beacon appearance (if rendered differently)
- resolution
- compression artifacts

**Mitigation strategies:**
1. **Domain randomization:** Vary all visual parameters widely during training.
2. **Simple features:** Use hand-crafted features (intensity, area, contrast) rather than raw pixels — these generalize better.
3. **Conservative reliance:** Use ML as a secondary validation, not the primary detector. The classical pipeline must work independently.

## 9.4 AI/ML Decision Criteria

If experiments show:

| Condition | Decision |
| --- | --- |
| ML classifier reduces false positives by >20% without increasing misses | Include in P1 pipeline |
| ML centroid improves RMSE by >10% vs IWC | Include in P1 pipeline |
| ML classifier inference exceeds 5ms per frame | Reject or use only intermittently |
| ML requires >1000 carefully curated training samples and performance is marginal | Reject; not worth implementation risk |
| ML performs well on simulator but poorly on MP4 with different characteristics | Reject for production; document the failure |

> **NOT YET EXPERIMENTALLY VALIDATED**

---

# PART 10 — BENCHMARK-2 EXPERIMENT DESIGN

## 10.1 MP4 Processing Requirements

| Requirement | Source | Impact |
| --- | --- | --- |
| Accept evaluator MP4 at ~30 FPS | PS L113 | Must process frames at sufficient rate |
| Bypass PTZ camera | PS L113 | FrameProvider(MP4 adapter) → same tracker pipeline |
| "Covering a complete screen" | PS L113 | Resolution unknown; must handle arbitrary dimensions |
| Centroiding error comparison | PS L113 | Must export per-frame centroids |
| RMSE, acquisition, reacquisition, lock retention, FPS | PS L113 | Full metric suite |

## 10.2 Resolution Robustness Experiment

**BM2-EXP-01:**

Generate test MP4 files from the simulator at multiple resolutions:
- 320×240
- 640×480 (default)
- 800×600
- 1280×720
- 1920×1080
- 2000×2000

For each resolution:
1. Record simulation with known beacon trajectory and ground truth.
2. Encode as MP4 (H.264, 30 FPS).
3. Process through tracker in MP4 mode.
4. Verify detection, centroiding, and tracking work correctly.
5. Measure processing FPS.

**Pass criteria:** Detection and tracking must work at all tested resolutions. FPS ≥ 20 at 640×480 and should remain feasible at higher resolutions.

## 10.3 Compression Artifact Experiment

**BM2-EXP-02:**

Generate MP4 files at varying quality levels:
- CRF 18 (high quality, ~15 Mbps)
- CRF 23 (medium quality, ~5 Mbps)
- CRF 28 (low quality, ~2 Mbps)
- CRF 35 (very low quality, ~500 Kbps)

Measure impact of compression artifacts on:
- Detection rate
- Centroiding error
- False positive rate

## 10.4 Unknown Evaluator Conditions

Since evaluator MP4 characteristics are unknown, the pipeline must handle:

| Unknown | Design Response |
| --- | --- |
| Resolution | Derive all spatial parameters from frame dimensions |
| Beacon size in pixels | Detection thresholds must be adaptive or configurable |
| Noise characteristics | Robust detection (CFAR/matched filter adapt to local statistics) |
| Background | Local background estimation handles varying backgrounds |
| Beacon intensity | Local contrast detection adapts to varying intensity |

---

# PART 11 — ALGORITHM SELECTION SCORECARD

## 11.1 Weight Derivation

Weights are derived from the PS evaluation structure:

| Criterion | Weight | Justification |
| --- | --- | --- |
| **Centroid accuracy (RMSE)** | 25% | BM1 (30%) + BM2 (30%) both explicitly evaluate centroiding |
| **Robustness (combined disturbances)** | 20% | BM1 and BM2 test under disturbances; failure to detect = catastrophic |
| **Lock retention / target loss** | 15% | BM2 explicitly scores lock retention; PS requires <5% loss |
| **Processing FPS** | 15% | PS requires ≥20 FPS; BM2 evaluates FPS |
| **Acquisition / reacquisition** | 10% | PS requires ≤2s / ≤1s; both benchmarks evaluate |
| **False positive rejection** | 5% | Affects lock retention and centroiding accuracy indirectly |
| **Implementation complexity** | 5% | Must be implementable within SIH timeline |
| **AI contribution / innovation** | 3% | Technical evaluation (20%) includes AI/CV and innovation |
| **Explainability** | 2% | Technical evaluation includes Q&A and discussion |

## 11.2 Scorecard Template

To be filled after experiments. Each algorithm configuration receives a score 1–5 per criterion.

| Configuration | Centroid Accuracy (25%) | Robustness (20%) | Lock Retention (15%) | FPS (15%) | Acq/Reacq (10%) | FP Rejection (5%) | Impl Complexity (5%) | AI Contrib (3%) | Explainability (2%) | **Weighted Total** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0 Baseline | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| P1 Enhanced | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| P2 Experimental | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

# PART 12 — RECOMMENDED BASELINE & PRODUCTION CANDIDATE

## 12.1 Recommended Production Pipeline (Analytical)

Based on the analysis above, the recommended production pipeline is:

### Detection: CFAR-style local-background detection + connected components

**Why:** CFAR adapts to local noise and background statistics, providing controlled false-alarm rates across all atmospheric conditions. Combined with connected components for blob extraction and area filtering. This is the closest algorithm class to what is used in actual infrared search/track (IRST) systems — the real-world analog of this problem.

**Alternatives considered:** Global threshold (too fragile under varying conditions), blob detection (LoG/DoG — more complex, less adaptive), matched filter (strong but requires template shape assumption).

### Preprocessing: Median 3×3 + conditional local background subtraction

**Why:** Median filter eliminates S&P noise with minimal beacon distortion. Local background subtraction counters atmospheric degradation. Conditional activation (only when atmosphere ≠ Clear) avoids unnecessary processing.

### Identification: Rule-based scoring + temporal validation

**Why:** Combines fast rule-based filtering (intensity, size, contrast, proximity to prediction) with multi-frame temporal consistency. No training required. Naturally integrates with the five-state machine.

### Centroid: Intensity-weighted centroid with local background subtraction

**Why:** Optimal for bright-spot localization. Sub-pixel accuracy. <0.1ms. Well-established in astronomical centroiding. Background subtraction removes bias.

### Temporal Tracking: Kalman filter (constant-velocity model) + adaptive ROI + candidate gating

**Why:** Kalman filter provides optimal estimation under Gaussian noise. Adaptive ROI reduces computation during tracking and false positives. Candidate gating rejects spatially inconsistent detections. Full-frame fallback during acquisition/reacquisition.

### PTZ Control: Dead-band proportional controller

**Why:** Simple, stable, noise-rejecting. Dead-band prevents hunting. Rate limiting from architecture prevents overshoot. Adequate for coarse alignment.

### AI/ML Integration: SVM or Random Forest candidate classifier (P1 enhancement)

**Why:** Provides the "AI" component required by the PS title and technical evaluation. Operates on hand-crafted features (not raw pixels), so generalizes well. Fast inference. Trained on simulator-generated data. Used as a secondary validation layer — the classical pipeline works independently without it.

**Expected strengths:**
- Robust across all PS-specified disturbance combinations
- Fast: estimated <10ms total pipeline
- Explainable: every stage has clear mathematical/physical justification
- Implementable within SIH timeline
- No large training data dependency
- Generalizes to arbitrary MP4 input

**Expected weaknesses:**
- IWC centroiding may not reach theoretical best accuracy for larger beacons (Gaussian fit might be better)
- CFAR tuning (guard cells, reference cells, false-alarm rate) requires careful experimentation
- Kalman CV model may struggle with highly erratic random motion (process noise tuning is critical)
- Dead-band PTZ has residual steady-state error (bounded by dead-band)

> **ANALYTICAL RECOMMENDATION — NOT YET EXPERIMENTALLY VALIDATED**

## 12.2 Fallback Strategy

If the recommended pipeline fails to meet PS performance thresholds:

| Primary | Fallback | Trigger |
| --- | --- | --- |
| CFAR detection | Matched filter + threshold | CFAR false-alarm rate too high for 5×5 under max noise |
| IWC centroid | Gaussian fitting | IWC RMSE exceeds threshold for ≥10×10 beacons |
| Kalman CV tracker | α-β filter | Kalman tuning fails for random motion |
| Dead-band proportional PTZ | PID controller | Tracking error consistently exceeds 10 pixels |
| SVM/RF classifier | Pure rule-based identification | ML does not improve over rule-based baseline |

The frozen architecture (strategy interfaces: IDetector, ICentroidEstimator, ITracker, IPTZController) ensures that any component can be swapped without system redesign.

---

# PART 13 — IMPLEMENTATION PRIORITY

## P0 — Mandatory Baseline (Implement First)

These components establish a working benchmark-capable system.

| Priority | Component | Algorithm | Estimated Effort | Dependency |
| --- | --- | --- | --- | --- |
| P0.1 | FrameProvider (sim mode) | Wrap simulator output | 1 day | Simulator ready |
| P0.2 | Preprocessing | Median 3×3 | 0.5 day | FrameProvider |
| P0.3 | Candidate Generation | Global/local threshold + connected components | 1 day | Preprocessing |
| P0.4 | Identification | Rule-based (intensity + size + proximity) | 1 day | Candidate generation |
| P0.5 | Centroid Estimation | Intensity-weighted centroid | 0.5 day | Identification |
| P0.6 | Temporal Tracking | Simple smoothing or α-β filter | 1 day | Centroid estimation |
| P0.7 | State Machine | Five-state implementation | 1 day | Tracking |
| P0.8 | PTZ Controller | Proportional (simple P) | 0.5 day | State machine |
| P0.9 | Metrics Engine | Basic metrics (CE, TE, RMSE, FPS, acq time) | 1 day | All tracker outputs |
| P0.10 | Logging Engine | Per-frame CSV export + summary report | 1 day | Metrics |
| P0.11 | FrameProvider (MP4 mode) | Video decoder adapter | 1 day | FrameProvider interface |

**Total P0 estimate:** ~9–10 days for a working end-to-end pipeline.

**P0 success criteria:** Runs all Level 0 scenarios. Exports centroid log. Generates performance report. Processes MP4 files.

## P1 — High-Value Improvements (After Baseline Works)

| Priority | Component | Algorithm | Estimated Benefit | Effort |
| --- | --- | --- | --- | --- |
| P1.1 | Detection upgrade | CFAR-style detection | Significantly improved robustness | 2 days |
| P1.2 | Centroid upgrade | IWC with local background subtraction | Improved RMSE | 1 day |
| P1.3 | Tracker upgrade | Kalman filter (CV model) | Improved smoothness, prediction, ROI | 2 days |
| P1.4 | Identification upgrade | Temporal validation (multi-frame) | Reduced false positives | 1 day |
| P1.5 | PTZ upgrade | Dead-band proportional + rate limiting | Reduced oscillation | 0.5 day |
| P1.6 | Preprocessing upgrade | Conditional local background subtraction | Atmospheric robustness | 1 day |
| P1.7 | ROI | Adaptive ROI from Kalman prediction | FPS improvement, FP reduction | 1 day |
| P1.8 | Candidate gating | Kalman gate for candidate association | FP rejection | 0.5 day |
| P1.9 | ML classifier | SVM/RF on candidate features | AI contribution for evaluation | 2 days |

**Total P1 estimate:** ~11 days.

## P2 — Experimental / Innovation (If Time Permits)

| Priority | Component | Algorithm | Potential Benefit | Risk |
| --- | --- | --- | --- | --- |
| P2.1 | CNN classifier | Tiny patch-based CNN | Stronger FP rejection under extreme noise | Training pipeline complexity; domain gap risk |
| P2.2 | Learned centroid | Tiny MLP centroid regression | Potentially best RMSE | Training dependency; generalization uncertain |
| P2.3 | Matched filter detection | Template-based matched filter | Optimal SNR for known target shape | Template assumption may not generalize to evaluator MP4 |
| P2.4 | Predictive PTZ | Velocity-based feedforward | Better tracking of fast targets | Implementation complexity |
| P2.5 | Adaptive preprocessing | Auto-detect noise type and select filter | Optimal filtering per condition | Complexity; may not provide sufficient benefit |
| P2.6 | Adaptive Kalman | Auto-tune process noise Q | Better adaptation to motion changes | Tuning complexity |

---

# PART 14 — RISKS

| # | Risk | Severity | Likelihood | Mitigation |
| --- | --- | --- | --- | --- |
| R-01 | 5×5 beacon undetectable under maximum combined noise + fog | Critical | Medium | CFAR/matched filter provide best chance; test early; accept graceful degradation |
| R-02 | Pipeline exceeds 50ms (FPS < 20) | Critical | Low (classical algorithms are fast) | Latency profiling during P0; ROI optimization in P1 |
| R-03 | ML model overfits to simulator, fails on evaluator MP4 | High | Medium | Use hand-crafted features; train with domain randomization; keep classical fallback |
| R-04 | CFAR parameter tuning is time-consuming | Medium | Medium | Start with DET-10 (simpler local background) and upgrade to CFAR incrementally |
| R-05 | Kalman filter poorly tuned for random motion | Medium | Medium | Tune process noise Q experimentally; have α-β filter as fallback |
| R-06 | Evaluator MP4 has unexpected resolution or characteristics | High | Medium | Resolution-agnostic tracker (AP-09); adaptive detection |
| R-07 | Dead-band PTZ gives tracking error > 10 pixels | Medium | Low | Dead-band tuning; switch to PID if needed |
| R-08 | Insufficient time to complete P1 improvements | High | Medium | P0 baseline is designed to be competition-viable on its own |
| R-09 | Centroiding error reference definition differs from assumption | Medium | High | Log both interpretations (ideal projected vs rendered centroid); keep definitions replaceable |
| R-10 | Algorithm Evaluation Harness implementation takes too long | Medium | Medium | Harness is development infrastructure; simplified version (manual replay) is acceptable for initial experiments |

---

# PART 15 — OPEN QUESTIONS

| # | Question | Impact | Resolution Path |
| --- | --- | --- | --- |
| OQ-01 | What is the evaluator's exact centroiding error reference (ideal projected position? rendered centroid?) | Critical for RMSE interpretation | Log both; compare after first evaluator feedback. Architecture §12.1b preserves the distinction. |
| OQ-02 | What resolution will evaluator MP4 files use? | Affects processing speed and detection parameters | Design for arbitrary resolution (AP-09). Test at multiple resolutions (BM2-EXP-01). |
| OQ-03 | Does "tracking error ≤ 10 pixels" mean beacon-to-center or estimated-vs-true? | Affects PTZ tuning vs centroid tuning | Log both. Architecture §10.2 and Engineering Context §10 preserve both definitions. |
| OQ-04 | What does "max standard deviation of noise: 20 pixels" mean? (intensity levels? spatial pixels?) | Affects noise severity | PS AMBIGUOUS. Make configurable. Test with σ=20 interpreted as intensity levels (0–255 range). |
| OQ-05 | How fast does the target move? (PS defines patterns but not speed) | Determines tracking feasibility | Make target speed configurable. Test across a range of speeds during experiments. |
| OQ-06 | Does the evaluator expect the application to auto-detect noise type or is it configured? | Affects preprocessing strategy | Support both manual configuration and adaptive preprocessing. |
| OQ-07 | What is the evaluator's RMSE calculation convention? | Affects benchmark comparison | Use proposed formula (√(Σ CEᵢ²/N)). Make replaceable per Architecture v1.2. |

---

# PART 16 — SUMMARY

## Recommended Production Pipeline

| Stage | Algorithm | Priority | AI/ML |
| --- | --- | --- | --- |
| Preprocessing | Median 3×3 + conditional local background subtraction | P0/P1 | No |
| Candidate Generation | CFAR-style local-background detection + connected components | P0 (simple threshold) → P1 (CFAR) | No |
| Detection/Classification | SVM/RF candidate classifier | P1 | **Yes** |
| Beacon Identification | Rule-based scoring + temporal validation + Kalman-gated association | P0/P1 | No (ML optional P1) |
| Centroid Estimation | Intensity-weighted centroid with local background subtraction | P0 | No |
| Temporal Tracking | Kalman filter (CV model) + adaptive ROI + candidate gating | P0 (simple) → P1 (full Kalman+ROI) | No |
| Confidence/State | Threshold-based with hysteresis | P0 | No |
| PTZ Control | Dead-band proportional controller | P0 | No |

## AI/ML Strategy

AI/ML is integrated as a **targeted enhancement** in the candidate classification stage, where it provides genuine value (false-positive rejection under complex noise). This satisfies the PS "AI-Based" requirement and technical evaluation criteria without introducing the risks of full-frame deep-learning detection on tiny targets.

The classical pipeline works independently without ML. ML components are additive and replaceable.

---

## Algorithm Selection Status

> **ANALYSIS COMPLETE — EXPERIMENTS REQUIRED**

All recommendations above are **analytical**. No experiments have been executed. The next step is to implement the P0 baseline pipeline, establish the Algorithm Evaluation Harness, execute the scenario ladder, and fill in the experimental scorecard.

The frozen architecture (v1.2) provides all necessary infrastructure: strategy interfaces, FrameProvider firewall, MetricsEngine, LoggingEngine, and Algorithm Evaluation Harness.

---

## Next Phase

> **STAGE 5 — IMPLEMENTATION**
>
> Implement P0 baseline pipeline within the frozen architecture. Execute Level 0–2 scenarios. Validate basic correctness. Then proceed to P1 enhancements guided by experimental results.

Do not begin implementation of P2 experimental algorithms until P0 baseline is working and benchmarked.
