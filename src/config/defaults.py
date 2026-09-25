"""
Default parameter values for the SIH 2026 FSOC system.

CLASSIFICATION KEY — every parameter is classified as exactly one of:

  PS_DEFAULT     — Default value explicitly stated in the Problem Statement.
                   Example: "Camera Resolution: 640×480" (PS Row 3).

  PS_REQUIRED    — Hard limit or mandatory requirement from the PS.
                   Example: "Processing Speed ≥20 FPS" (PS Row 20).

  PS_CONFIGURABLE — PS says the parameter is "user-defined" or selectable.
                     The value here is the PS-suggested default if one exists,
                     otherwise an engineering default.

  ENGINEERING_DEFAULT — Value chosen by engineering judgment. NOT from the PS.
                        Example: Kalman filter process noise Q.

  PS_AMBIGUOUS   — Parameter where the PS wording is ambiguous or the units
                   are unclear. The value here is a provisional interpretation.
                   Example: "Max Standard Deviation of Noise: 20 pixels" —
                   units are ambiguous (intensity levels vs spatial pixels).

Sources:
  PS   = Official SIH Problem Statement (PS.md)
  PRD  = Approved Product Requirements Document (PRD.md)
  EC   = Engineering Context (SIH_26_Engineering_Context_Technical_Model.md)
  ARCH = Frozen Architecture v1.2 (system_architecture.md)
  ALGO = Algorithm Selection v1.0 (algorithm_selection_experimental_design.md)
"""


# ==========================================================================
# SCENE PARAMETERS
# ==========================================================================

# PS Row 1: "Screen Size (min.): 2000 x 2000 pixels"
SCENE_MIN_WIDTH = 2000                  # PS_REQUIRED — minimum screen width
SCENE_MIN_HEIGHT = 2000                 # PS_REQUIRED — minimum screen height
SCENE_DEFAULT_WIDTH = 2000              # PS_DEFAULT — default screen width
SCENE_DEFAULT_HEIGHT = 2000             # PS_DEFAULT — default screen height

# Background intensity is not specified by the PS.
SCENE_BACKGROUND_INTENSITY = 30        # ENGINEERING_DEFAULT — dark background


# ==========================================================================
# CAMERA PARAMETERS
# ==========================================================================

# PS Row 2: "Camera Type: Monochrome, Focal Plane Array"
CAMERA_IS_MONOCHROME = True             # PS_REQUIRED — mandatory monochrome

# PS Row 3: "Camera Resolution: 640 x 480 pixels"
CAMERA_DEFAULT_WIDTH = 640              # PS_DEFAULT
CAMERA_DEFAULT_HEIGHT = 480             # PS_DEFAULT

# PS Row 4: "Camera FOV: User-defined. Default: 4° x 3°"
CAMERA_DEFAULT_FOV_H_DEG = 4.0         # PS_DEFAULT
CAMERA_DEFAULT_FOV_V_DEG = 3.0         # PS_DEFAULT

# PS Row 5: "Camera update Rate: 30 Hz (min.)"
CAMERA_MIN_UPDATE_RATE_HZ = 30         # PS_REQUIRED — minimum camera rate
CAMERA_DEFAULT_UPDATE_RATE_HZ = 30     # PS_DEFAULT

# PS Row 6: "Initial Camera Position: Centre of the Screen"
# Derived: center of default scene = (1000, 1000)
CAMERA_INITIAL_X = None                 # PS_DEFAULT — computed as scene_w / 2
CAMERA_INITIAL_Y = None                 # PS_DEFAULT — computed as scene_h / 2


# ==========================================================================
# TARGET / BEACON PARAMETERS
# ==========================================================================

# PS Row 7: "Target Type: Beacon Spot"
# PS Row 8: "Number of Targets: 1, mandatory"
TARGET_COUNT = 1                        # PS_REQUIRED — minimum 1 mandatory

# PS Row 9: "Target Shape: User-defined. Default: Square"
TARGET_DEFAULT_SHAPE = "square"         # PS_DEFAULT

# PS Row 10: "Target Size: 5-20 x 5-20 pixels (user-defined). Default: 10 x 10"
TARGET_MIN_SIZE = 5                     # PS_REQUIRED — minimum target size
TARGET_MAX_SIZE = 20                    # PS_REQUIRED — maximum target size
TARGET_DEFAULT_SIZE = 10                # PS_DEFAULT

# PS Row 11: "Initial Target Location: User-defined. Default: Random"
TARGET_DEFAULT_INITIAL_POSITION = "random"  # PS_DEFAULT

# Target intensity is not defined by the PS.
TARGET_DEFAULT_INTENSITY = 220          # ENGINEERING_DEFAULT — bright beacon
TARGET_MIN_INTENSITY = 50              # ENGINEERING_DEFAULT — minimum visible

# Target speed is not defined by the PS (EC §29: "open design parameter").
TARGET_DEFAULT_SPEED = 50.0            # ENGINEERING_DEFAULT — pixels/second
                                        # PS_AMBIGUOUS — PS does not define speed


# ==========================================================================
# MOTION PARAMETERS
# ==========================================================================

# PS Row 12: "Motion: Selectable, at least four: Straight Line,
#             Circular, Figure of 8, Random"
# Optional: Spiral, Sinusoidal, User-defined
MOTION_MANDATORY_TYPES = [
    "STRAIGHT_LINE",
    "CIRCULAR",
    "FIGURE_8",
    "RANDOM",
]                                       # PS_REQUIRED

MOTION_OPTIONAL_TYPES = [
    "SPIRAL",
    "SINUSOIDAL",
    "USER_DEFINED",
]                                       # PS_CONFIGURABLE

# Motion geometry defaults — ENGINEERING_DEFAULT (PS does not specify these)
MOTION_CIRCLE_RADIUS = 200.0           # ENGINEERING_DEFAULT — pixels
MOTION_FIGURE8_RADIUS_X = 300.0        # ENGINEERING_DEFAULT — pixels
MOTION_FIGURE8_RADIUS_Y = 150.0        # ENGINEERING_DEFAULT — pixels
MOTION_RANDOM_MAX_DISPLACEMENT = 10.0  # ENGINEERING_DEFAULT — pixels/frame


# ==========================================================================
# PTZ / CAMERA MOTION CONSTRAINTS
# ==========================================================================

# PS Row 13: "Max. Pan Speed: 5-10 °/s (User-defined). Default: 5 °/s"
PTZ_MIN_PAN_SPEED_DEG_S = 5.0          # PS_CONFIGURABLE — lower bound
PTZ_MAX_PAN_SPEED_DEG_S = 10.0         # PS_REQUIRED — upper bound
PTZ_DEFAULT_PAN_SPEED_DEG_S = 5.0      # PS_DEFAULT

# PS Row 14: "Max. Tilt Speed: 5-10 °/s (User-defined). Default: 5 °/s"
PTZ_MIN_TILT_SPEED_DEG_S = 5.0         # PS_CONFIGURABLE
PTZ_MAX_TILT_SPEED_DEG_S = 10.0        # PS_REQUIRED
PTZ_DEFAULT_TILT_SPEED_DEG_S = 5.0     # PS_DEFAULT

# PS Row 15: "Update Interval: ≥ 20 Hz"
PTZ_MIN_UPDATE_RATE_HZ = 20            # PS_REQUIRED
PTZ_DEFAULT_UPDATE_RATE_HZ = 20        # PS_DEFAULT

# Dead-band and gain — ENGINEERING_DEFAULT (Tuned PI control law per SIH <= 10 px accuracy mandate)
PTZ_DEFAULT_PROPORTIONAL_GAIN = 8.0    # ENGINEERING_DEFAULT — proportional tracking gain
PTZ_DEFAULT_DEADBAND_PX = 1.0          # ENGINEERING_DEFAULT — tracking deadband in pixels
PTZ_DEFAULT_INTEGRAL_GAIN = 2.0        # ENGINEERING_DEFAULT — anti-lag integral action


# ==========================================================================
# PERFORMANCE SPECIFICATIONS
# ==========================================================================

# PS Row 16: "Acquisition Time: ≤ 2 sec"
PERFORMANCE_MAX_ACQUISITION_TIME_S = 2.0     # PS_REQUIRED

# PS Row 17: "Tracking Error: ≤ 10 pixels"
PERFORMANCE_MAX_TRACKING_ERROR_PX = 10.0     # PS_REQUIRED
# NOTE: PS_AMBIGUOUS — "tracking error" is not mathematically defined
# in the PS. Could be beacon-to-center or estimated-vs-true.

# PS Row 18: "Target Loss: < 5%"
PERFORMANCE_MAX_TARGET_LOSS_PCT = 5.0        # PS_REQUIRED

# PS Row 19: "Re-acquisition Time: ≤ 1 sec"
PERFORMANCE_MAX_REACQUISITION_TIME_S = 1.0   # PS_REQUIRED

# PS Row 20: "Processing Speed: ≥ 20 FPS"
PERFORMANCE_MIN_FPS = 20                     # PS_REQUIRED


# ==========================================================================
# DISTURBANCE / NOISE PARAMETERS
# ==========================================================================

# PS Row 21: "Image Noise: 1. Salt & Pepper (around 10% of image),
#             2. Gaussian & 3. Poisson. User Selectable (one or more)"
NOISE_SP_DEFAULT_DENSITY = 0.10         # PS_DEFAULT — "around 10%"
NOISE_SP_MIN_DENSITY = 0.0             # PS_CONFIGURABLE
NOISE_SP_MAX_DENSITY = 1.0             # PS_CONFIGURABLE

# PS Row 22: "Max. Standard Deviation of Noise: 20 pixels"
# PS_AMBIGUOUS — "pixels" is not a standard unit for noise σ.
# Could mean intensity levels (0–255 scale) or spatial pixels.
# Provisional interpretation: intensity levels on a 0–255 scale.
NOISE_GAUSSIAN_MAX_SIGMA = 20.0        # PS_AMBIGUOUS — units unclear
NOISE_GAUSSIAN_DEFAULT_SIGMA = 10.0    # ENGINEERING_DEFAULT

# Poisson noise — PS requires it but specifies no parameters.
NOISE_POISSON_ENABLED = False           # PS_CONFIGURABLE — user-selectable

# PS Row 23: "Max. Camera Jitter: ± 20 pixels / frame"
JITTER_MAX_PX_PER_FRAME = 20.0         # PS_REQUIRED — maximum jitter
JITTER_DEFAULT_PX_PER_FRAME = 5.0      # ENGINEERING_DEFAULT
JITTER_ENABLED = False                  # PS_CONFIGURABLE — user-selectable

# PS Row 24: "Atmospheric Disturbance: Clear, Haze, Fog, Rain, Low light"
# "User-defined reduction in contrast and brightness"
ATMOS_DEFAULT_CONDITION = "CLEAR"       # PS_DEFAULT (implicit baseline)

# Atmospheric degradation factors — ENGINEERING_DEFAULT
# PS says "user-defined reduction" but gives no specific values.
ATMOS_HAZE_CONTRAST_FACTOR = 0.7       # ENGINEERING_DEFAULT
ATMOS_HAZE_BRIGHTNESS_OFFSET = 10      # ENGINEERING_DEFAULT
ATMOS_FOG_CONTRAST_FACTOR = 0.4        # ENGINEERING_DEFAULT
ATMOS_FOG_BRIGHTNESS_OFFSET = 30       # ENGINEERING_DEFAULT
ATMOS_RAIN_CONTRAST_FACTOR = 0.6       # ENGINEERING_DEFAULT
ATMOS_RAIN_BRIGHTNESS_OFFSET = 15      # ENGINEERING_DEFAULT
ATMOS_LOW_LIGHT_CONTRAST_FACTOR = 0.5  # ENGINEERING_DEFAULT
ATMOS_LOW_LIGHT_BRIGHTNESS_OFFSET = -40  # ENGINEERING_DEFAULT

# PS Row 25: "Platform Motion: ± 20 pixels/frame (max.)"
# "Default/Mandatory: Linear. Optional: Circular, random, spiral, figure of 8"
PLATFORM_MOTION_MAX_PX_PER_FRAME = 20.0  # PS_REQUIRED
PLATFORM_MOTION_DEFAULT_PX_PER_FRAME = 5.0  # ENGINEERING_DEFAULT
PLATFORM_MOTION_MANDATORY_TYPE = "LINEAR"  # PS_REQUIRED
PLATFORM_MOTION_ENABLED = False         # PS_CONFIGURABLE


# ==========================================================================
# DETECTOR / ALGORITHM PARAMETERS (P0 Baseline)
# ==========================================================================
# All of these are ENGINEERING_DEFAULT — not from the PS.

# Local background estimation
DETECTOR_BG_KERNEL_SIZE = 51            # ENGINEERING_DEFAULT — pixels
DETECTOR_THRESHOLD_MULTIPLIER = 3.0     # ENGINEERING_DEFAULT — k * sigma
DETECTOR_THRESHOLD_OFFSET = 20          # ENGINEERING_DEFAULT — minimum offset

# Connected components filtering
DETECTOR_MIN_CANDIDATE_AREA = 4         # ENGINEERING_DEFAULT — pixels
DETECTOR_MAX_CANDIDATE_AREA = 500       # ENGINEERING_DEFAULT — pixels
DETECTOR_MIN_CANDIDATE_INTENSITY = 50   # ENGINEERING_DEFAULT

# Preprocessing & contrast
DETECTOR_MEDIAN_KERNEL_SIZE = 3         # ENGINEERING_DEFAULT — 3x3 median filter
DETECTOR_MIN_LOCAL_CONTRAST = 1.0       # ENGINEERING_DEFAULT — minimum contrast ratio

# Identification scoring weights
IDENTIFIER_INTENSITY_WEIGHT = 0.3       # ENGINEERING_DEFAULT
IDENTIFIER_SIZE_WEIGHT = 0.3            # ENGINEERING_DEFAULT
IDENTIFIER_CONTRAST_WEIGHT = 0.2        # ENGINEERING_DEFAULT
IDENTIFIER_PROXIMITY_WEIGHT = 0.2       # ENGINEERING_DEFAULT
IDENTIFIER_MIN_CONFIDENCE = 0.1         # ENGINEERING_DEFAULT — minimum score to select candidate

# Centroid estimation
CENTROID_BG_MARGIN = 5                  # ENGINEERING_DEFAULT — pixels around bbox
CENTROID_MIN_SIGNAL_WEIGHT = 1.0        # ENGINEERING_DEFAULT — minimum sum(w_i) for valid centroid
CENTROID_BG_METHOD = "annulus"          # ENGINEERING_DEFAULT — perimeter ring / annulus background



# ==========================================================================
# TRACKER PARAMETERS (P0 Baseline)
# ==========================================================================
# All ENGINEERING_DEFAULT.

# Kalman filter (constant-velocity model)
KALMAN_PROCESS_NOISE_POS = 1.0          # ENGINEERING_DEFAULT
KALMAN_PROCESS_NOISE_VEL = 5.0          # ENGINEERING_DEFAULT
KALMAN_MEASUREMENT_NOISE = 2.0          # ENGINEERING_DEFAULT
KALMAN_INITIAL_COVARIANCE_POS = 100.0   # ENGINEERING_DEFAULT
KALMAN_INITIAL_COVARIANCE_VEL = 1000.0  # ENGINEERING_DEFAULT

# Adaptive ROI
ROI_MIN_SIZE = 60                       # ENGINEERING_DEFAULT — pixels
ROI_MAX_SIZE = 300                      # ENGINEERING_DEFAULT — pixels
ROI_MARGIN_FACTOR = 3.0                 # ENGINEERING_DEFAULT — multiplier

# Candidate gating
GATE_MAX_DISTANCE = 120.0               # ENGINEERING_DEFAULT — pixels (robust tracking during camera motion)

# State machine thresholds
STATE_LOCK_THRESHOLD = 0.6              # ENGINEERING_DEFAULT
STATE_LOSS_THRESHOLD = 0.3              # ENGINEERING_DEFAULT
STATE_LOCK_CONFIRM_FRAMES = 3           # ENGINEERING_DEFAULT
STATE_LOSS_CONFIRM_FRAMES = 5           # ENGINEERING_DEFAULT
STATE_REACQUIRE_CONFIRM_FRAMES = 3      # ENGINEERING_DEFAULT


# ==========================================================================
# LOGGING / EXPERIMENT PARAMETERS
# ==========================================================================

LOG_CSV_ENABLED = True                  # ENGINEERING_DEFAULT
LOG_JSON_SUMMARY_ENABLED = True         # ENGINEERING_DEFAULT
LOG_OUTPUT_DIR = "output"               # ENGINEERING_DEFAULT


# ==========================================================================
# SIMULATION PARAMETERS
# ==========================================================================

# Simulation timing
SIM_DEFAULT_DURATION_S = 30.0           # ENGINEERING_DEFAULT
SIM_DEFAULT_RANDOM_SEED = 42           # ENGINEERING_DEFAULT — reproducibility


# ==========================================================================
# DISTURBANCE ORDERING (from Architecture v1.2 §7.1)
# ==========================================================================
# This is an ENGINEERING DECISION documented in the frozen architecture.
# Order: Platform motion → Jitter → Viewport → Atmospheric → Poisson →
#         Gaussian → S&P
DISTURBANCE_ORDER = [
    "platform_motion",      # 1. Geometric — shifts camera world position
    "camera_jitter",        # 2. Geometric — random offset to camera position
    # --- viewport extraction happens here (not a disturbance stage) ---
    "atmospheric",          # 3. Pixel — contrast/brightness reduction
    "poisson_noise",        # 4. Pixel — signal-dependent, applied first
    "gaussian_noise",       # 5. Pixel — additive, signal-independent
    "salt_and_pepper_noise",  # 6. Pixel — impulse, applied last
]                                       # ARCH §7.1 — engineering decision

# Extended pipeline order including optional Stage 4.5 local contrast
EXTENDED_DISTURBANCE_ORDER = [
    "platform_motion",
    "camera_jitter",
    "atmospheric",
    "local_contrast",
    "poisson_noise",
    "gaussian_noise",
    "salt_and_pepper_noise",
]


# ==========================================================================
# MULTI-BEACON PARAMETERS (NEW — Additive, non-breaking)
# ==========================================================================

# Primary beacon intensity margin: secondary must be at least this much
# dimmer than the primary to avoid dominance ambiguity.
BEACON_PRIMARY_MARGIN = 5               # ENGINEERING_DEFAULT — intensity units

# Maximum number of secondary (distractor) beacons
BEACON_MAX_SECONDARY = 5               # ENGINEERING_DEFAULT

# Default secondary beacon intensity step (relative to primary)
BEACON_SECONDARY_DEFAULT_INTENSITY = 160  # ENGINEERING_DEFAULT

# ==========================================================================
# CANDIDATE IDENTIFIER — HYSTERESIS / ANTI-SWITCHING PARAMETERS (NEW)
# ==========================================================================

# During TRACKING, a challenger must exceed the current target score by this
# margin for SWITCH_CONFIRMATION_FRAMES consecutive frames before a switch
# is confirmed. Prevents momentary noise-induced target switching.
IDENTIFIER_SWITCH_SCORE_MARGIN = 0.15  # ENGINEERING_DEFAULT — fraction of [0,1]
IDENTIFIER_SWITCH_CONFIRMATION_FRAMES = 3  # ENGINEERING_DEFAULT — frames

# ==========================================================================
# LOCAL CONTRAST DISTURBANCE PARAMETERS (NEW)
# ==========================================================================

# Local background clutter: spatially-varying additive intensity field
# applied after atmospheric degradation, before sensor noise.
LOCAL_CONTRAST_ENABLED = False                  # ENGINEERING_DEFAULT
LOCAL_CONTRAST_AMPLITUDE = 40.0                 # ENGINEERING_DEFAULT — intensity (0-120)
LOCAL_CONTRAST_SPATIAL_SCALE = 80.0             # ENGINEERING_DEFAULT — blob radius px
LOCAL_CONTRAST_NUM_BLOBS = 8                    # ENGINEERING_DEFAULT
LOCAL_CONTRAST_MIN_BEACON_MARGIN = 30           # ENGINEERING_DEFAULT — beacon must be
                                                # this much brighter than local background

# ==========================================================================
# POISSON NOISE SCALE (NEW — extends existing NoiseConfig)
# ==========================================================================

# Exposure scale multiplier for Poisson shot noise.
# 1.0 = standard photon statistics. < 1.0 = underexposure (more noise).
# > 1.0 = higher effective exposure (less noise, but rarely needed).
NOISE_POISSON_SCALE = 1.0              # ENGINEERING_DEFAULT

# ==========================================================================
# SINGLE-RUN REPORT
# ==========================================================================

SINGLE_RUN_REPORT_OUTPUT_DIR = "output/single_run"  # ENGINEERING_DEFAULT

