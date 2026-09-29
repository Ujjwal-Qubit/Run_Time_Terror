/**
 * LumiTrack — 3D Scene Graph Contracts (Developer Workspace Integrated Sub-Views)
 */

export type ThreeDSceneMode = 'LIVE' | 'VALIDATION'

export interface ThreeDSceneOptions {
  showGrid: boolean
  showFovFrustum: boolean
  showBoresightBeam: boolean
  showTrajectoryTrail: boolean
  showCoordinatesHUD: boolean
  autoFollowTarget: boolean
}

export interface ResultsTimeSeriesData {
  runId: string
  frameCount: number
  timestamps: number[]
  frameNumbers: number[]
  centroidsX: (number | null)[]
  centroidsY: (number | null)[]
  panAngles: number[]
  tiltAngles: number[]
  latenciesMs: number[]
  fpsList: number[]
  boresightOffsets: number[]
  validationGtErrors: (number | null)[] | null
  validationModeActive: boolean
}
