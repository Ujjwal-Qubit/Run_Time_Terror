// ============================================================
// LumiTrack TypeScript Type Definitions
// Canonical contract — derived from Python backend dataclasses.
// Do NOT add fields here that do not exist in the Python source.
// ============================================================

export interface AlgorithmInfo {
  name: string;
  version: string;
  description: string;
  author: string;
  api_version: string;
  dependencies: string[];
  metadata: Record<string, any>;
  status: 'Ready' | 'Active' | 'Error';
}

/**
 * SystemConfig mirrors the Python SystemConfig dataclass in
 * src/config/config_manager.py. Every field here maps 1-to-1
 * to a real backend attribute that the ConfigManager accepts.
 */
export interface SystemConfig {
  scene: {
    width: number;
    height: number;
    background_intensity: number;
  };
  camera: {
    width: number;
    height: number;
    fov_h_deg: number;
    fov_v_deg: number;
    update_rate_hz: number;
    /** World X coordinate of initial camera pointing (null = scene center) */
    initial_x: number | null;
    /** World Y coordinate of initial camera pointing (null = scene center) */
    initial_y: number | null;
  };
  target: {
    count: number;
    size: number;
    shape: 'square' | 'circle' | 'gaussian' | string;
    intensity: number;
    initial_position: string;
    initial_x: number | null;
    initial_y: number | null;
    /** Target speed in pixels/second */
    speed: number;
  };
  motion: {
    motion_type: 'STRAIGHT_LINE' | 'CIRCULAR' | 'FIGURE_8' | 'RANDOM' | 'SPIRAL' | 'SINUSOIDAL' | 'POLYGON' | 'ZIGZAG' | string;
    circle_radius: number;
    figure8_radius_x: number;
    figure8_radius_y: number;
    random_max_displacement: number;
    straight_line_angle_deg: number;
    spiral_r0: number;
    spiral_expansion_rate: number;
    sinusoidal_amplitude: number;
    sinusoidal_frequency: number;
    polygon_sides: number;
    polygon_radius: number;
    zigzag_width: number;
    zigzag_height: number;
    is_ai_generated: boolean;
    ai_prompt: string | null;
  };
  ptz: {
    max_pan_speed_deg_s: number;
    max_tilt_speed_deg_s: number;
    update_rate_hz: number;
    proportional_gain: number;
    deadband_px: number;
    integral_gain: number;
  };
  noise: {
    sp_enabled: boolean;
    sp_density: number;
    gaussian_enabled: boolean;
    gaussian_sigma: number;
    poisson_enabled: boolean;
    /** Exposure/photon scale for Poisson noise. 1.0 = standard, lower = noisier. */
    poisson_scale: number;
  };
  atmospheric: {
    condition: 'CLEAR' | 'HAZE' | 'FOG' | 'RAIN' | 'LOW_LIGHT' | string;
    /** Override contrast factor (null = use condition default) */
    contrast_factor: number | null;
    /** Override brightness offset (null = use condition default) */
    brightness_offset: number | null;
  };
  jitter: {
    enabled: boolean;
    max_px_per_frame: number;
  };
  platform_motion: {
    enabled: boolean;
    motion_type: 'NONE' | 'LINEAR' | 'SINUSOIDAL' | string;
    max_px_per_frame: number;
  };
  local_contrast: {
    enabled: boolean;
    amplitude: number;
    spatial_scale: number;
    num_blobs: number;
    min_beacon_margin: number;
  };
  simulation: {
    mode: 'SIMULATION' | 'MP4';
    duration_s: number | null;
    random_seed: number;
    mp4_path: string | null;
  };
  // Opaque sections — read-only from backend, not directly edited via ConfigPanel
  detector: Record<string, unknown>;
  identifier: Record<string, unknown>;
  centroid: Record<string, unknown>;
  tracker: Record<string, unknown>;
  state: Record<string, unknown>;
  logging: Record<string, unknown>;
  beacons: BeaconConfig[];
}

/** Single synthetic optical beacon configuration. */
export interface BeaconConfig {
  beacon_id: string;
  role: 'primary' | 'secondary';
  x: number | null;
  y: number | null;
  size: number;
  shape: string;
  intensity: number;
  speed: number;
  motion_type: string | null;
}

export interface VisualizationPacket {
  frame_number: number;
  timestamp: number;
  tracking_state: 'SEARCHING' | 'ACQUIRING' | 'TRACKING' | 'LOST' | 'REACQUIRING' | 'IDLE';
  lock_status: 'LOCKED' | 'ACQUIRING' | 'UNLOCKED';
  estimated_centroid: { x: number; y: number } | null;
  ground_truth: { x: number; y: number } | null;
  roi: { x: number; y: number; w: number; h: number } | null;
  pan_angle_deg: number;
  tilt_angle_deg: number;
  camera_fov: number;
  /**
   * Distance from estimated centroid to frame boresight (center).
   * This is boresight error, NOT ground-truth localization error.
   */
  tracking_error_px: number | null;
  fps: number;
  latency_ms: number;
  resolution: { width: number; height: number };
  image_base64: string;
}

export interface MatrixResult {
  /** Canonical identifier for this benchmark suite run */
  suite_id: string;
  /** Backward-compatibility alias for suite_id */
  batch_id?: string;
  status: string;
  passed_sih_spec: boolean;
  verdict: 'PASS' | 'FAIL';
  mean_fps: number;
  mean_rmse: number | null;
  /** Target loss rate as a fraction (0.0–1.0), not percentage */
  mean_loss_rate: number;
  report_paths: {
    json: string;
    csv: string;
    markdown: string;
  };
  report_data?: Record<string, any>;
}

export interface AIScenarioOutcome {
  scenario_id: string;
  valid: boolean;
  validation_errors: string[];
  spec: Record<string, any>;
  evaluation: {
    algorithm_fps: number | null;
    centroid_rmse: number | null;
    target_loss_rate: number | null;
    acquisition_time_s: number | null;
    passed_sih_spec: boolean;
  } | null;
  report_path: string;
}

export interface ReportItem {
  name: string;
  rel_path: string;
  type: string;
  size_bytes: number;
  mtime: number;
}
