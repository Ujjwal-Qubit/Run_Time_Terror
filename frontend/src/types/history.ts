/**
 * SANKET — Run History & Artifact Catalog Data Contracts (Screen 4)
 */

export interface RunCatalogItem {
  runId: string
  timestamp: string
  totalFrames: number
  durationSeconds: number
  meanFps: number
  rmseCentroidPx: number
  lockRetentionPct: number
  passedSihSpec: boolean
  reportMdPath: string | null
  summaryJsonPath: string | null
  telemetryCsvPath: string | null
  configJsonPath: string | null
}

export interface RunArtifactPayload {
  path: string
  filename: string
  format: 'json' | 'md' | 'csv' | string
  content: string
}
