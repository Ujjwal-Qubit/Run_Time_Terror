/**
 * LumiTrack — Benchmark Evaluation Data Contracts (Screen 2: Evaluator Workspace)
 */

export interface BenchmarkProgress {
  status: 'IDLE' | 'RUNNING' | 'COMPLETED' | 'ERROR'
  percent: number
  log: string
}

export interface BenchmarkResult {
  subset: string
  algorithm: string
  totalRuns: number
  successfulRuns: number
  failedRuns: number
  meanAlgorithmFps: number
  meanRmseCentroid: number | null
  passedSihSpec: boolean
  reportMdPath?: string
  summaryJsonPath?: string
}
