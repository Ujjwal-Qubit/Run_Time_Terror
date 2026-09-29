import React from 'react'
import {
  Terminal,
  CheckSquare,
  BarChart2,
  Shield,
  FolderOpen,
  Video,
  Box,
  Grid,
  User,
} from 'lucide-react'
import { useLumiTrackStore, type WorkspaceId } from '../store/useLumiTrackStore'
import { bridgeService } from '../services/bridgeService'

export const Sidebar: React.FC = () => {
  const isConnected = useLumiTrackStore((state) => state.isConnected)
  const activeWorkspace = useLumiTrackStore((state) => state.activeWorkspace)
  const setActiveWorkspace = useLumiTrackStore((state) => state.setActiveWorkspace)
  const setActiveDeveloperTab = useLumiTrackStore((state) => state.setActiveDeveloperTab)
  const runHistory = useLumiTrackStore((state) => state.runHistory)

  const handleNavClick = (id: WorkspaceId) => {
    setActiveWorkspace(id)
    if (id === 'diagnostics') {
      bridgeService.getSubsystemDiagnostics()
    } else if (id === 'history') {
      bridgeService.getRunHistory()
    } else if (id === 'results') {
      bridgeService.getResultsAnalysisData()
    }
  }

  const handleQuickJump = (tab: '2d' | '3d' | 'world') => {
    setActiveWorkspace('developer')
    setActiveDeveloperTab(tab)
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-surface-container-low border-r border-outline-variant/40 z-50 flex flex-col justify-between select-none">
      <div className="flex flex-col">
        {/* Brand & App Title */}
        <div className="p-space-md border-b border-outline-variant/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-sm">
              <img src="/app_logo_transparent.svg" alt="SANKET Logo" className="w-6 h-6 object-contain" />
              <span className="font-headline-sm text-headline-sm font-semibold tracking-wider text-on-surface">
                SANKET
              </span>
            </div>
            <span className="font-data-sm text-data-sm px-space-xs py-space-xs bg-surface-container-highest text-primary rounded border border-outline-variant/30">
              v1.0
            </span>
          </div>
          <div className="font-label-sm text-label-sm tracking-tight text-outline mt-space-xs uppercase">
            Software Simulator &amp; Benchmark Harness
          </div>
        </div>

        {/* Section 1: Core Workspaces */}
        <div className="px-space-md pt-space-md pb-space-xs">
          <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">
            Core Workspaces
          </span>
        </div>
        <nav className="flex flex-col gap-space-xs px-space-sm">
          {/* Developer Workspace */}
          <button
            type="button"
            onClick={() => handleNavClick('developer')}
            className={`w-full flex items-center justify-between px-space-md py-space-sm rounded transition-colors text-left group ${
              activeWorkspace === 'developer'
                ? 'bg-surface-container text-primary border-l-2 border-primary font-medium'
                : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
            }`}
          >
            <div className="flex items-center gap-space-md">
              <Terminal
                className={`w-4 h-4 ${
                  activeWorkspace === 'developer' ? 'text-primary' : 'text-outline group-hover:text-on-surface'
                }`}
              />
              <span className="font-label-md text-label-md">Developer Workspace</span>
            </div>
          </button>

          {/* Evaluator Workspace */}
          <button
            type="button"
            onClick={() => handleNavClick('evaluator')}
            className={`w-full flex items-center justify-between px-space-md py-space-sm rounded transition-colors text-left group ${
              activeWorkspace === 'evaluator'
                ? 'bg-surface-container text-primary border-l-2 border-primary font-medium'
                : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
            }`}
          >
            <div className="flex items-center gap-space-md">
              <CheckSquare
                className={`w-4 h-4 ${
                  activeWorkspace === 'evaluator' ? 'text-primary' : 'text-outline group-hover:text-on-surface'
                }`}
              />
              <span className="font-label-md text-label-md">Evaluator Workspace</span>
            </div>
            <span className="font-data-sm text-data-sm px-space-xs py-space-xs bg-secondary/10 text-secondary border border-secondary/30 rounded">
              19/19
            </span>
          </button>

          {/* Results & Analysis */}
          <button
            type="button"
            onClick={() => handleNavClick('results')}
            className={`w-full flex items-center justify-between px-space-md py-space-sm rounded transition-colors text-left group ${
              activeWorkspace === 'results'
                ? 'bg-surface-container text-primary border-l-2 border-primary font-medium'
                : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
            }`}
          >
            <div className="flex items-center gap-space-md">
              <BarChart2
                className={`w-4 h-4 ${
                  activeWorkspace === 'results' ? 'text-primary' : 'text-outline group-hover:text-on-surface'
                }`}
              />
              <span className="font-label-md text-label-md">Results &amp; Analysis</span>
            </div>
          </button>

          {/* Diagnostics & Subsystem Audit */}
          <button
            type="button"
            onClick={() => handleNavClick('diagnostics')}
            className={`w-full flex items-center justify-between px-space-md py-space-sm rounded transition-colors text-left group ${
              activeWorkspace === 'diagnostics'
                ? 'bg-surface-container text-primary border-l-2 border-primary font-medium'
                : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
            }`}
          >
            <div className="flex items-center gap-space-md">
              <Shield
                className={`w-4 h-4 ${
                  activeWorkspace === 'diagnostics' ? 'text-primary' : 'text-outline group-hover:text-on-surface'
                }`}
              />
              <span className="font-label-md text-label-md">Diagnostics &amp; Audit</span>
            </div>
          </button>

          {/* Run History */}
          <button
            type="button"
            onClick={() => handleNavClick('history')}
            className={`w-full flex items-center justify-between px-space-md py-space-sm rounded transition-colors text-left group ${
              activeWorkspace === 'history'
                ? 'bg-surface-container text-primary border-l-2 border-primary font-medium'
                : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
            }`}
          >
            <div className="flex items-center gap-space-md">
              <FolderOpen
                className={`w-4 h-4 ${
                  activeWorkspace === 'history' ? 'text-primary' : 'text-outline group-hover:text-on-surface'
                }`}
              />
              <span className="font-label-md text-label-md">Run History</span>
            </div>
            <span className="font-data-sm text-data-sm px-space-xs py-space-xs bg-surface-container-highest text-on-surface-variant rounded border border-outline-variant/30">
              {runHistory.length}
            </span>
          </button>
        </nav>

        {/* Section 2: Quick-Jump Views */}
        <div className="px-space-md pt-space-lg pb-space-xs">
          <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">
            Quick-Jump Views
          </span>
        </div>
        <div className="flex flex-col gap-space-xs px-space-sm">
          <button
            type="button"
            onClick={() => handleQuickJump('2d')}
            className="flex items-center gap-space-md px-space-md py-space-sm text-on-surface-variant hover:bg-surface-container hover:text-on-surface rounded transition-colors group text-left"
          >
            <Video className="w-4 h-4 text-outline group-hover:text-on-surface" />
            <span className="font-label-md text-label-md">2D Sensor View (640×480)</span>
          </button>

          <button
            type="button"
            onClick={() => handleQuickJump('3d')}
            className="flex items-center gap-space-md px-space-md py-space-sm text-on-surface-variant hover:bg-surface-container hover:text-on-surface rounded transition-colors group text-left"
          >
            <Box className="w-4 h-4 text-outline group-hover:text-on-surface" />
            <span className="font-label-md text-label-md">3D Pedestal Frustum</span>
          </button>

          <button
            type="button"
            onClick={() => handleQuickJump('world')}
            className="flex items-center gap-space-md px-space-md py-space-sm text-on-surface-variant hover:bg-surface-container hover:text-on-surface rounded transition-colors group text-left"
          >
            <Grid className="w-4 h-4 text-outline group-hover:text-on-surface" />
            <span className="font-label-md text-label-md">2000×2000 World Canvas</span>
          </button>
        </div>
      </div>

      {/* Operator & Security Footer */}
      <div className="p-space-md border-t border-outline-variant/30 bg-surface-container-lowest/60">
        <div className="flex items-center gap-space-md">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
            <User className="text-on-primary w-4 h-4" />
          </div>
          <div className="flex flex-col min-w-0 flex-1">
            <span className="font-label-md text-label-md text-on-surface font-medium truncate">
              SIH 2026 Operator
            </span>
            <span className="font-label-sm text-label-sm text-outline truncate">
              FSOC Lead / SANKET
            </span>
          </div>
        </div>
        <div className="mt-space-sm pt-space-xs border-t border-outline-variant/20 flex items-center gap-space-xs">
          <span
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
              isConnected ? 'bg-secondary animate-pulse' : 'bg-tertiary'
            }`}
          />
          <span className="font-label-sm text-label-sm text-secondary truncate">
            {isConnected ? 'SECURE / AIRGAP SIL ACTIVE' : 'LOCAL SIMULATION ENGINE'}
          </span>
        </div>
      </div>
    </aside>
  )
}
