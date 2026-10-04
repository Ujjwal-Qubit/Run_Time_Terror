/**
 * SANKET — Global Zustand Telemetry & Workspace State Store
 * High-performance atomic selector subscriptions to prevent re-render cascades.
 */

import { create } from 'zustand'
import type { SystemStatus, TrackingTelemetry, SensorFramePayload } from '../types/telemetry'
import type { SubsystemState } from '../types/diagnostics'
import type { RunCatalogItem, RunArtifactPayload } from '../types/history'
import type { BenchmarkProgress, BenchmarkResult } from '../types/benchmark'
import type { ResultsTimeSeriesData, ThreeDSceneOptions } from '../types/scene3d'
import type { BrowserPerformanceMetrics } from '../types/performance'

export type WorkspaceId = 'developer' | 'evaluator' | 'diagnostics' | 'history' | 'results'

interface SanketStoreState {
  // Navigation & Connection
  activeWorkspace: WorkspaceId
  activeDeveloperTab: '2d' | '3d' | 'world'
  isConnected: boolean
  
  // Real Core Data Slices
  status: SystemStatus
  telemetry: TrackingTelemetry
  latestFrame: SensorFramePayload | null
  
  // Workspace Specific Slices
  subsystems: SubsystemState[]
  runHistory: RunCatalogItem[]
  selectedRunId: string | null
  selectedArtifact: RunArtifactPayload | null
  benchmarkProgress: BenchmarkProgress
  latestBenchmarkResult: BenchmarkResult | null
  resultsData: ResultsTimeSeriesData | null
  scene3dOptions: ThreeDSceneOptions
  browserPerf: BrowserPerformanceMetrics

  // Actions
  setActiveWorkspace: (ws: WorkspaceId) => void
  setActiveDeveloperTab: (tab: '2d' | '3d' | 'world') => void
  setConnected: (connected: boolean) => void
  setStatus: (status: SystemStatus) => void
  setTelemetry: (telemetry: TrackingTelemetry) => void
  setLatestFrame: (frame: SensorFramePayload) => void
  setSubsystems: (subsystems: SubsystemState[]) => void
  setRunHistory: (history: RunCatalogItem[]) => void
  setSelectedRunId: (runId: string | null) => void
  setSelectedArtifact: (artifact: RunArtifactPayload | null) => void
  setBenchmarkProgress: (progress: BenchmarkProgress) => void
  setLatestBenchmarkResult: (result: BenchmarkResult | null) => void
  setResultsData: (data: ResultsTimeSeriesData | null) => void
  updateScene3dOptions: (partial: Partial<ThreeDSceneOptions>) => void
  updateBrowserPerf: (metrics: BrowserPerformanceMetrics) => void
}

const defaultStatus: SystemStatus = {
  mode: 'SIMULATION',
  isRunning: false,
  isPaused: false,
  activeAlgorithm: 'baseline_tracker',
  activeScenario: 'scenario_1_static.json',
  currentFrame: 0,
  simTime: 0.0,
  availableAlgorithms: ['baseline_tracker'],
  availableScenarios: ['scenario_1_static.json'],
  availableBenchmarkVideos: [
    'sanket_benchmark2_beacon_circular_30fps.mp4',
    'sanket_benchmark2_beacon_figure8_30fps.mp4',
    'sanket_benchmark2_beacon_random_30fps.mp4',
    'sanket_benchmark2_beacon_spiral_30fps.mp4',
    'sanket_benchmark2_beacon_straight_line_30fps.mp4',
  ],
  ptzEnabled: true,
  trackingEnabled: true,
  backendFps: 0.0,
  targetSpeedPxS: 20.0,
  validationMode: false,
}

const defaultTelemetry: TrackingTelemetry = {
  frameNumber: 0,
  timestamp: 0.0,
  trackingState: 'SEARCHING',
  centroid: { x: null, y: null },
  roi: null,
  confidence: 0.0,
  boresightOffsetPx: null,
  trackingErrorPx: null,
  processingLatencyMs: 0.0,
  algorithmFps: 0.0,
  panAngleDeg: 0.0,
  tiltAngleDeg: 0.0,
  cameraFovH: 4.0,
  cameraFovV: 3.0,
  cameraWidth: 640,
  cameraHeight: 480,
  ptzActive: true,
}

const defaultBenchmarkProgress: BenchmarkProgress = {
  status: 'IDLE',
  percent: 0,
  log: 'Ready to evaluate.',
}

const defaultScene3dOptions: ThreeDSceneOptions = {
  showGrid: true,
  showFovFrustum: true,
  showBoresightBeam: true,
  showTrajectoryTrail: true,
  showCoordinatesHUD: true,
  autoFollowTarget: false,
}

const defaultBrowserPerf: BrowserPerformanceMetrics = {
  renderFps: 60.0,
  minFps: 60.0,
  frameTimeMs: 16.6,
  droppedFrames: 0,
  browserDecodeTimeMs: 0.0,
  canvasDrawTimeMs: 0.0,
  totalBrowserPipelineMs: 0.0,
  telemetryReceiveHz: 25.0,
  telemetryDroppedCount: 0,
  lastTelemetryIntervalMs: 40.0,
}

export const useSanketStore = create<SanketStoreState>((set) => ({
  activeWorkspace: 'developer',
  activeDeveloperTab: '2d',
  isConnected: false,
  status: defaultStatus,
  telemetry: defaultTelemetry,
  latestFrame: null,
  subsystems: [],
  runHistory: [],
  selectedRunId: null,
  selectedArtifact: null,
  benchmarkProgress: defaultBenchmarkProgress,
  latestBenchmarkResult: null,
  resultsData: null,
  scene3dOptions: defaultScene3dOptions,
  browserPerf: defaultBrowserPerf,

  setActiveWorkspace: (activeWorkspace) => set({ activeWorkspace }),
  setActiveDeveloperTab: (activeDeveloperTab) => set({ activeDeveloperTab }),
  setConnected: (connected) => set({ isConnected: connected }),
  setStatus: (status) => set({ status }),
  setTelemetry: (telemetry) => set({ telemetry }),
  setLatestFrame: (latestFrame) => set({ latestFrame }),
  setSubsystems: (subsystems) => set({ subsystems }),
  setRunHistory: (runHistory) => set({ runHistory }),
  setSelectedRunId: (selectedRunId) => set({ selectedRunId }),
  setSelectedArtifact: (selectedArtifact) => set({ selectedArtifact }),
  setBenchmarkProgress: (benchmarkProgress) => set({ benchmarkProgress }),
  setLatestBenchmarkResult: (latestBenchmarkResult) => set({ latestBenchmarkResult }),
  setResultsData: (resultsData) => set({ resultsData }),
  updateScene3dOptions: (partial) =>
    set((state) => ({ scene3dOptions: { ...state.scene3dOptions, ...partial } })),
  updateBrowserPerf: (browserPerf) => set({ browserPerf }),
}))



declare global {
  interface Window {
    useSanketStore?: typeof useSanketStore
  }
}

if (typeof window !== 'undefined') {
  window.useSanketStore = useSanketStore
}
