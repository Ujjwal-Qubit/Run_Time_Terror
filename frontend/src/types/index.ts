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
    initial_pan_deg: number;
    initial_tilt_deg: number;
  };
  target: {
    size: number;
    shape: 'square' | 'circle' | 'gaussian';
    intensity: number;
    initial_x: number;
    initial_y: number;
  };
  motion: {
    motion_type: 'STRAIGHT_LINE' | 'CIRCULAR' | 'FIGURE_8' | 'RANDOM' | 'SPIRAL' | 'SINUSOIDAL';
    speed: number;
    direction_deg: number;
  };
  atmospheric: {
    condition: 'CLEAR' | 'HAZE' | 'FOG' | 'RAIN' | 'LOW_LIGHT';
    transmittance: number;
    blur_sigma: number;
  };
  noise: {
    gaussian_enabled: boolean;
    gaussian_sigma: number;
    sp_enabled: boolean;
    sp_density: number;
    poisson_enabled: boolean;
    poisson_peak: number;
  };
  jitter: {
    enabled: boolean;
    max_px_per_frame: number;
  };
  platform_motion: {
    enabled: boolean;
    motion_type: 'NONE' | 'LINEAR' | 'SINUSOIDAL';
    max_px_per_frame: number;
  };
  ptz: {
    kp: number;
    ki: number;
    kd: number;
    deadband_px: number;
    max_speed_deg_per_s: number;
  };
  simulation: {
    mode: 'SIMULATION' | 'MP4';
    duration_s: number | null;
    random_seed: number;
    mp4_path?: string;
  };
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
  tracking_error_px: number | null;
  fps: number;
  latency_ms: number;
  resolution: { width: number; height: number };
  image_base64: string;
}

export interface MatrixResult {
  batch_id: string;
  status: string;
  passed_sih_spec: boolean;
  verdict: 'PASS' | 'FAIL';
  mean_fps: number;
  mean_rmse: number | null;
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
