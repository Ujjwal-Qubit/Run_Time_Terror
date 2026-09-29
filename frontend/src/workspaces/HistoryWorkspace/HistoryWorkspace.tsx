import React, { useEffect, useState } from 'react'
import {
  RefreshCw,
  Search,
  FileText,
  BarChart2,
  FileCode,
  Table,
  SearchCode,
  Eye,
  FolderOpen,
  Sliders,
} from 'lucide-react'
import { useLumiTrackStore } from '../../store/useLumiTrackStore'
import { bridgeService } from '../../services/bridgeService'
import type { RunCatalogItem } from '../../types/history'

// ─────────────────────────────────────────────────────────────────────────────
// Run History & Artifact Catalog Workspace — Screen 4
// Stitch visual reconstruction with real filesystem run artifacts
// ─────────────────────────────────────────────────────────────────────────────

export const HistoryWorkspace: React.FC = () => {
  const isConnected = useLumiTrackStore((state) => state.isConnected)
  const runHistory = useLumiTrackStore((state) => state.runHistory)
  const selectedArtifact = useLumiTrackStore((state) => state.selectedArtifact)
  const setSelectedRunId = useLumiTrackStore((state) => state.setSelectedRunId)

  const [search, setSearch] = useState('')
  const [inspectedId, setInspectedId] = useState<string | null>(null)
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([])
  const [filterOutcome, setFilterOutcome] = useState<'ALL' | 'PASS' | 'FAIL'>('ALL')

  useEffect(() => {
    if (isConnected) {
      bridgeService.getRunHistory()
    }
  }, [isConnected])

  // Select initial run when history loads
  useEffect(() => {
    if (runHistory.length > 0 && !inspectedId) {
      setInspectedId(runHistory[0].runId)
      setSelectedRunId(runHistory[0].runId)
    }
  }, [runHistory, inspectedId, setSelectedRunId])

  const rows: RunCatalogItem[] = runHistory ?? []

  const filtered = rows.filter((r) => {
    if (filterOutcome === 'PASS' && !r.passedSihSpec) return false
    if (filterOutcome === 'FAIL' && r.passedSihSpec) return false
    if (!search.trim()) return true
    const q = search.toLowerCase()
    return r.runId.toLowerCase().includes(q)
  })

  const inspected = rows.find((r) => r.runId === inspectedId) ?? rows[0] ?? null

  const handleSelectRun = (r: RunCatalogItem) => {
    setInspectedId(r.runId)
    setSelectedRunId(r.runId)
    bridgeService.getResultsAnalysisData(r.runId)
  }

  const toggleSelectCheckbox = (runId: string) => {
    setSelectedRunIds((prev) =>
      prev.includes(runId) ? prev.filter((id) => id !== runId) : [...prev, runId]
    )
  }

  const handleDownloadArtifact = (path: string | null) => {
    if (!path) return
    bridgeService.getRunArtifact(path)
  }

  return (
    <div className="flex flex-col w-full text-on-surface select-none">
      {/* ── Context Bar ─────────────────────────────────────────────────────── */}
      <div className="w-full bg-surface-container-lowest px-space-md py-space-sm flex flex-wrap items-center justify-between gap-space-md shadow-sm border-b border-outline-variant/30">
        <div className="flex flex-wrap items-center gap-space-md">
          <div className="flex items-center gap-space-xs bg-surface-container-low px-space-sm py-space-xs rounded">
            <span className="font-label-sm text-label-sm text-outline">CATALOG PARTITION:</span>
            <span className="font-data-sm text-data-sm text-primary font-medium tracking-wide">
              SANKET SIMULATION RUNS
            </span>
          </div>
          <div className="flex items-center gap-space-xs">
            <span className={`w-1.5 h-1.5 rounded-full ${rows.length > 0 ? 'bg-secondary' : 'bg-outline'}`} />
            <span className="font-label-sm text-label-sm text-outline uppercase">INDEX STATE:</span>
            <span className="font-data-sm text-data-sm text-secondary">
              {rows.length > 0 ? `SYNCHRONIZED (${rows.length} Real Runs Cataloged)` : 'STANDBY (0 Runs)'}
            </span>
          </div>
          <div className="flex items-center gap-space-xs">
            <span className="font-label-sm text-label-sm text-outline uppercase">STORAGE ROOT:</span>
            <span className="font-data-sm text-data-sm text-on-surface-variant font-medium">/output</span>
          </div>
        </div>
        <div className="flex items-center gap-space-sm">
          <div className="flex items-center gap-space-xs bg-surface-container px-space-sm py-space-xs rounded">
            <span className="font-label-sm text-label-sm text-outline">ACTIVE RUN:</span>
            <span className="font-data-sm text-data-sm text-primary-fixed-dim font-medium truncate max-w-xs">
              {inspected?.runId ?? 'None Selected'}
            </span>
          </div>
          <button
            onClick={() => bridgeService.getRunHistory()}
            className="flex items-center gap-space-xs px-space-sm py-space-xs bg-surface-container-highest hover:bg-surface-bright rounded text-on-surface text-label-sm font-label-sm"
          >
            <RefreshCw className="w-3 h-3 text-primary" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Filter Bar ──────────────────────────────────────────────────────── */}
      <div className="w-full px-space-md py-space-md bg-surface-container-low flex flex-col gap-space-sm border-b border-outline-variant/30">
        <div className="flex flex-wrap items-center justify-between gap-space-md">
          {/* Search */}
          <div className="flex-1 min-w-[280px] max-w-xl relative">
            <Search className="absolute left-space-sm top-1/2 -translate-y-1/2 text-outline w-4 h-4 pointer-events-none" />
            <input
              className="w-full bg-surface-container text-on-surface placeholder:text-outline pl-8 pr-space-md py-space-xs rounded font-body-sm text-body-sm focus:outline-none focus:bg-surface-container-high transition-colors"
              placeholder="Search by Run ID..."
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          {/* Filter buttons */}
          <div className="flex flex-wrap items-center gap-space-xs">
            <button
              onClick={() => setFilterOutcome('ALL')}
              className={`px-space-sm py-space-xs rounded font-label-md text-label-md transition-colors ${
                filterOutcome === 'ALL'
                  ? 'bg-primary text-on-primary font-medium'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              All Runs ({rows.length})
            </button>
            <button
              onClick={() => setFilterOutcome('PASS')}
              className={`px-space-sm py-space-xs rounded font-label-md text-label-md transition-colors ${
                filterOutcome === 'PASS'
                  ? 'bg-secondary-container text-on-secondary-container font-medium'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              Compliant ({rows.filter((r) => r.passedSihSpec).length})
            </button>
            <button
              onClick={() => setFilterOutcome('FAIL')}
              className={`px-space-sm py-space-xs rounded font-label-md text-label-md transition-colors ${
                filterOutcome === 'FAIL'
                  ? 'bg-error-container text-on-error-container font-medium'
                  : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              Exceeded ({rows.filter((r) => !r.passedSihSpec).length})
            </button>
          </div>
          {/* Action Toolbar */}
          <div className="flex items-center gap-space-xs">
            <button
              onClick={() => {
                if (inspected?.summaryJsonPath) bridgeService.getRunArtifact(inspected.summaryJsonPath)
              }}
              disabled={!inspected}
              className="flex items-center gap-space-xs px-space-md py-space-xs bg-surface-container-highest hover:bg-surface-bright text-on-surface rounded font-label-md text-label-md transition-colors disabled:opacity-40"
            >
              <FileText className="w-3.5 h-3.5 text-primary" />
              <span>Inspect Summary</span>
            </button>
            <button
              onClick={() => {
                if (inspected) bridgeService.getResultsAnalysisData(inspected.runId)
              }}
              disabled={!inspected}
              className="flex items-center gap-space-xs px-space-md py-space-xs bg-primary text-on-primary font-medium rounded font-label-md text-label-md shadow-sm hover:bg-primary-fixed-dim transition-colors disabled:opacity-40"
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Analyze in Results</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── Run Table ───────────────────────────────────────────────────────── */}
      <div className="w-full overflow-x-auto bg-surface">
        <table className="w-full text-left whitespace-nowrap">
          <thead>
            <tr className="bg-surface-container-highest text-outline uppercase font-label-sm text-label-sm border-b border-outline-variant/30">
              <th className="py-space-sm px-space-md w-8">
                <input
                  type="checkbox"
                  checked={selectedRunIds.length === rows.length && rows.length > 0}
                  onChange={() => {
                    if (selectedRunIds.length === rows.length) setSelectedRunIds([])
                    else setSelectedRunIds(rows.map((r) => r.runId))
                  }}
                  className="rounded border-outline-variant/50 bg-surface-container-low text-primary focus:ring-0"
                />
              </th>
              <th className="py-space-sm px-space-md font-medium">Run ID</th>
              <th className="py-space-sm px-space-md font-medium">Timestamp</th>
              <th className="py-space-sm px-space-md font-medium text-right">Frames</th>
              <th className="py-space-sm px-space-md font-medium text-right">Duration (s)</th>
              <th className="py-space-sm px-space-md font-medium text-right">Mean FPS</th>
              <th className="py-space-sm px-space-md font-medium text-right">Centroid RMSE (px)</th>
              <th className="py-space-sm px-space-md font-medium text-right">Lock Retention</th>
              <th className="py-space-sm px-space-md font-medium text-center">Outcome</th>
              <th className="py-space-sm px-space-md font-medium text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/10 font-data-sm text-data-sm">
            {filtered.length > 0 ? (
              filtered.map((row) => {
                const isSelected = row.runId === inspectedId
                const isChecked = selectedRunIds.includes(row.runId)
                return (
                  <tr
                    key={row.runId}
                    onClick={() => handleSelectRun(row)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-surface-container-high border-l-2 border-primary'
                        : 'hover:bg-surface-container-low'
                    }`}
                  >
                    <td className="py-space-sm px-space-md" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSelectCheckbox(row.runId)}
                        className="rounded border-outline-variant/50 bg-surface-container-low text-primary focus:ring-0"
                      />
                    </td>
                    <td className="py-space-sm px-space-md font-medium text-on-surface">
                      <span className="font-mono">{row.runId}</span>
                    </td>
                    <td className="py-space-sm px-space-md text-on-surface-variant font-mono">
                      {row.timestamp}
                    </td>
                    <td className="py-space-sm px-space-md text-right font-mono">
                      {row.totalFrames.toLocaleString()}
                    </td>
                    <td className="py-space-sm px-space-md text-right font-mono">
                      {row.durationSeconds.toFixed(1)}
                    </td>
                    <td className="py-space-sm px-space-md text-right font-mono text-secondary">
                      {row.meanFps.toFixed(1)}
                    </td>
                    <td className="py-space-sm px-space-md text-right font-mono text-primary font-semibold">
                      {row.rmseCentroidPx.toFixed(3)}
                    </td>
                    <td className="py-space-sm px-space-md text-right font-mono">
                      {row.lockRetentionPct.toFixed(1)}%
                    </td>
                    <td className="py-space-sm px-space-md text-center">
                      <span
                        className={`px-space-sm py-space-xs rounded font-label-sm text-label-sm font-semibold uppercase tracking-wider ${
                          row.passedSihSpec
                            ? 'bg-secondary-container/20 text-secondary'
                            : 'bg-error-container/30 text-error'
                        }`}
                      >
                        {row.passedSihSpec ? 'COMPLIANT' : 'EXCEEDED'}
                      </span>
                    </td>
                    <td className="py-space-sm px-space-md text-center" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-center gap-space-xs">
                        {row.summaryJsonPath && (
                          <button
                            title="Inspect Summary JSON"
                            onClick={() => handleDownloadArtifact(row.summaryJsonPath)}
                            className="p-1 rounded hover:bg-surface-container-highest text-primary"
                          >
                            <FileCode className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {row.reportMdPath && (
                          <button
                            title="View Report Markdown"
                            onClick={() => handleDownloadArtifact(row.reportMdPath)}
                            className="p-1 rounded hover:bg-surface-container-highest text-secondary"
                          >
                            <FileText className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {row.telemetryCsvPath && (
                          <button
                            title="Load CSV Telemetry"
                            onClick={() => bridgeService.getResultsAnalysisData(row.runId)}
                            className="p-1 rounded hover:bg-surface-container-highest text-tertiary"
                          >
                            <Table className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })
            ) : (
              <tr>
                <td colSpan={10} className="py-space-xl text-center text-outline">
                  {rows.length === 0
                    ? 'No run summary artifacts detected in /output directory. Run a simulation or benchmark matrix.'
                    : 'No runs matched the specified search criteria.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ── Lower Workspace: Run Inspector & Artifacts ────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-md p-space-md bg-surface border-t border-outline-variant/30">
        {/* Focused Run Inspector (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-space-md bg-surface-container-low p-space-md rounded shadow-sm border border-outline-variant/30">
          <div className="flex items-center justify-between pb-space-xs border-b border-outline-variant/20">
            <div className="flex items-center gap-space-sm">
              <SearchCode className="w-4 h-4 text-primary" />
              <span className="font-headline-sm text-headline-sm text-on-surface">Focused Run Inspector</span>
              <span className="font-data-sm text-data-sm text-primary font-mono font-medium">
                {inspected?.runId ?? 'None Selected'}
              </span>
            </div>
            {inspected && (
              <span
                className={`font-label-sm text-label-sm px-space-xs py-space-xs rounded font-semibold uppercase ${
                  inspected.passedSihSpec
                    ? 'bg-secondary-container/20 text-secondary'
                    : 'bg-error-container/30 text-error'
                }`}
              >
                {inspected.passedSihSpec ? '100% SPEC PASS' : 'SPEC EXCEEDED'}
              </span>
            )}
          </div>

          {/* 6 Metric Bento Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-space-sm">
            {[
              {
                label: 'Centroid RMSE',
                value: inspected?.rmseCentroidPx !== undefined ? `${inspected.rmseCentroidPx.toFixed(3)} px` : '—',
                sub: 'Target ≤ 10.0 px',
                color: 'text-primary',
              },
              {
                label: 'Loop Frame Rate',
                value: inspected?.meanFps !== undefined ? `${inspected.meanFps.toFixed(1)} FPS` : '—',
                sub: 'Spec ≥ 20.0 FPS',
                color: 'text-secondary',
              },
              {
                label: 'Lock Retention',
                value: inspected?.lockRetentionPct !== undefined ? `${inspected.lockRetentionPct.toFixed(1)}%` : '—',
                sub: 'Spec ≥ 95.0%',
                color: 'text-secondary',
              },
              {
                label: 'Run Duration',
                value: inspected?.durationSeconds !== undefined ? `${inspected.durationSeconds.toFixed(1)} s` : '—',
                sub: 'Total elapsed',
                color: 'text-on-surface',
              },
              {
                label: 'Total Frames',
                value: inspected?.totalFrames !== undefined ? inspected.totalFrames.toLocaleString() : '—',
                sub: 'Frames analyzed',
                color: 'text-on-surface',
              },
              {
                label: 'Compliance Verdict',
                value: inspected ? (inspected.passedSihSpec ? 'PASSED' : 'FAILED') : '—',
                sub: 'Formal check',
                color: inspected?.passedSihSpec ? 'text-secondary' : 'text-error',
              },
            ].map(({ label, value, sub, color }) => (
              <div key={label} className="bg-surface-container p-space-sm rounded flex flex-col justify-between">
                <span className="font-label-sm text-label-sm text-outline uppercase">{label}</span>
                <div className="mt-space-xs">
                  <span className={`font-data-lg text-data-lg font-semibold ${color}`}>{value}</span>
                </div>
                <span className="font-data-sm text-data-sm text-outline mt-space-xs">{sub}</span>
              </div>
            ))}
          </div>

          {/* Filesystem Artifacts */}
          <div className="mt-space-xs flex flex-col gap-space-xs">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">
              Disk Artifacts for {inspected?.runId ?? 'Selected Run'}
            </span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-space-xs">
              {[
                {
                  Icon: Table,
                  name: 'telemetry.csv',
                  desc: 'Time-series sensor telemetry data',
                  path: inspected?.telemetryCsvPath,
                  color: 'text-primary',
                },
                {
                  Icon: FileCode,
                  name: 'summary.json',
                  desc: 'Aggregated run statistics',
                  path: inspected?.summaryJsonPath,
                  color: 'text-primary',
                },
                {
                  Icon: FileText,
                  name: 'performance_report.md',
                  desc: 'Formal markdown compliance report',
                  path: inspected?.reportMdPath,
                  color: 'text-secondary',
                },
                {
                  Icon: Sliders,
                  name: 'config.json',
                  desc: 'Scenario and simulator configuration',
                  path: inspected?.configJsonPath,
                  color: 'text-tertiary',
                },
              ].map(({ Icon, name, desc, path, color }) => {
                const exists = !!path
                return (
                  <div
                    key={name}
                    className="bg-surface-container p-space-sm rounded flex items-center justify-between group hover:bg-surface-container-high transition-colors"
                  >
                    <div className="flex items-center gap-space-sm min-w-0">
                      <Icon className={`w-4 h-4 ${exists ? color : 'text-outline/40'}`} />
                      <div className="flex flex-col min-w-0">
                        <span className="font-data-sm text-data-sm text-on-surface font-medium truncate">{name}</span>
                        <span className="font-label-sm text-label-sm text-outline truncate">{desc}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDownloadArtifact(path ?? null)}
                      className={`p-space-xs rounded text-outline transition-colors ${
                        exists
                          ? 'bg-surface-container-highest hover:bg-primary hover:text-on-primary text-on-surface'
                          : 'opacity-30 cursor-not-allowed'
                      }`}
                      title={exists ? `Load ${name}` : 'Not generated for this run'}
                      disabled={!exists}
                    >
                      <Eye className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Selected Artifact Content Viewer (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-space-md bg-surface-container-low p-space-md rounded shadow-sm border border-outline-variant/30">
          <div className="flex items-center justify-between pb-space-xs border-b border-outline-variant/20">
            <div className="flex items-center gap-space-sm">
              <FileText className="w-4 h-4 text-secondary" />
              <span className="font-headline-sm text-headline-sm text-on-surface">Artifact Inspector</span>
            </div>
            <span className="font-data-sm text-data-sm text-outline font-mono truncate max-w-xs">
              {selectedArtifact?.filename ?? 'No File Loaded'}
            </span>
          </div>

          {selectedArtifact ? (
            <div className="flex flex-col gap-space-sm h-full">
              <div className="flex items-center justify-between text-outline font-label-sm text-label-sm bg-surface-container px-space-sm py-space-xs rounded">
                <span>PATH: {selectedArtifact.path}</span>
                <span className="uppercase">{selectedArtifact.format}</span>
              </div>
              <pre className="flex-1 bg-surface-container-lowest p-space-md rounded font-mono text-[11px] leading-relaxed text-on-surface-variant overflow-auto max-h-[360px] border border-outline-variant/20 select-text">
                {selectedArtifact.content}
              </pre>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-space-xl text-center text-outline gap-space-sm min-h-[240px]">
              <FolderOpen className="w-9 h-9 text-outline/30" />
              <p className="font-body-sm text-body-sm max-w-xs">
                Select an artifact from the list (JSON, MD, or CSV) to inspect its full contents here.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
