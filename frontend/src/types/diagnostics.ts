/**
 * SANKET — Subsystem Health Diagnostics Data Contracts (Screen 3: Diagnostics Workspace)
 */

export type SubsystemStatus = 'READY' | 'RUNNING' | 'ACTIVE' | 'IDLE' | 'BUSY' | 'CONNECTED' | 'OPTIMAL' | 'DEGRADED' | 'WARNING' | 'ERROR' | 'ENFORCED'

export interface SubsystemState {
  id: string
  name: string
  domain: string
  status: SubsystemStatus
  rateHz: number
  latencyMs: number
  errorCount: number
  details: string
}
