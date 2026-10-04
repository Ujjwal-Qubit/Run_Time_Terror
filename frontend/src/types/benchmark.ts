/**
 * SANKET — Benchmark Evaluation Data Contracts (Screen 2: Evaluator Workspace)
 */

export interface ScenarioResultItem {
  id: string
  scenarioId?: string
  meanErr?: string
  rmse?: string
  acqLat?: string
  lossRate?: string
  status?: string
}

export interface BenchmarkProgress {
  status: 'IDLE' | 'RUNNING' | 'COMPLETED' | 'ERROR'
  percent: number
  log: string
  currentScenarioId?: string | null
  scenarioStatus?: 'RUNNING' | 'PASS' | 'FAIL' | 'READY' | string
  scenarioResult?: ScenarioResultItem
}

export interface BenchmarkResult {
  subset: string
  algorithm: string
  totalRuns: number
  successfulRuns: number
  failedRuns: number
  meanAlgorithmFps: number
  meanRmseCentroid: number | null
  meanTrackingError?: number
  meanAcqLatency?: number
  meanTargetLossRate?: number
  passedSihSpec: boolean
  reportMdPath?: string
  summaryJsonPath?: string
  scenarioResults?: ScenarioResultItem[]
}

export interface BenchmarkVideoMeta {
  filePath: string
  fileName: string
  fileSize: number
  width: number
  height: number
  fps: number
  totalFrames: number
  durationSeconds: number
}
