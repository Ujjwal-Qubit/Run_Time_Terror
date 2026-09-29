/**
 * LumiTrack — Phase 2 Frontend Typed Data Contracts
 * Enforces strict typing between Python QtWebChannel bridge and React.
 */

export type TrackingState =
  | 'SEARCHING'
  | 'COASTING'
  | 'CONVERGING'
  | 'TRACKING'
  | 'REACQUIRING'
  | 'LOST'
  | 'STANDBY'

export interface CentroidCoords {
  x: number | null
  y: number | null
}

export interface RegionOfInterest {
  x: number
  y: number
  width: number
  height: number
}

export interface SystemStatus {
  mode: 'SIMULATION' | 'MP4'
  isRunning: boolean
  isPaused: boolean
  activeAlgorithm: string
  activeScenario: string
  currentFrame: number
  simTime: number
  availableAlgorithms: string[]
  availableScenarios: string[]
  ptzEnabled: boolean
  trackingEnabled?: boolean
  backendFps: number
  targetSpeedPxS: number | null
  validationMode: boolean
}

export interface TrackingTelemetry {
  frameNumber: number
  timestamp: number
  trackingState: TrackingState
  centroid: CentroidCoords
  roi: RegionOfInterest | null
  confidence: number
  boresightOffsetPx: number | null
  trackingErrorPx: number | null // Strictly null during live tracking per ground-truth firewall
  processingLatencyMs: number
  algorithmFps: number
  panAngleDeg: number
  tiltAngleDeg: number
  cameraFovH: number
  cameraFovV: number
  cameraWidth: number
  cameraHeight: number
  ptzActive: boolean
  sendTimestamp?: number
}

export interface SensorFramePayload {
  frameNumber: number
  timestamp: number
  width: number
  height: number
  format: 'jpeg' | 'png'
  data: string // "data:image/jpeg;base64,..."
  sendTimestamp?: number
}
