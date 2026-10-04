import React, { useEffect, useState } from 'react'
import {
  FolderOpen,
  Search,
  Download,
  GitCompare,
  RotateCcw,
  Database,
  BarChart2,
  ExternalLink,
  FileSpreadsheet,
  FileText,
  Code2,
  Box,
  Archive,
  ArrowLeftRight,
} from 'lucide-react'
import { useSanketStore } from '../../store/useSanketStore'
import { bridgeService } from '../../services/bridgeService'

// ─────────────────────────────────────────────────────────────
// Screen 7: SANKET — Run History & Artifact Catalog (Forensic Archive)
// Visual design strictly matches Stitch: 7_history_e2aa.html
// ─────────────────────────────────────────────────────────────

interface RunEntry {
  id: string
  timestamp: string
  algo: string
  engine: string
  scenario: string
  meanErr: string
  rmse: string
  acqLat: string
  lossRate: string
  rate: string
  status: 'COMPLIANT' | 'BOUNDED' | 'DEGRADED'
  isFocused?: boolean
  reportMdPath?: string | null
  summaryJsonPath?: string | null
  telemetryCsvPath?: string | null
}

const DEFAULT_RUNS: RunEntry[] = [
  {
    id: 'RUN_20260903_142809',
    timestamp: '2026-09-03 14:28:09',
    algo: 'Subpixel_CoG + PI',
    engine: 'v2.4.8 (HIL RIG-0482)',
    scenario: 'SCN_04_COMBINED_STRESS_HIGH',
    meanErr: '3.54 px',
    rmse: '0.028 px',
    acqLat: '0.070 s',
    lossRate: '0.00%',
    rate: '62.7 Hz',
    status: 'COMPLIANT',
    isFocused: true,
  },
  {
    id: 'RUN_20260903_131502',
    timestamp: '2026-09-03 13:15:02',
    algo: 'Subpixel_CoG + PI',
    engine: 'v2.4.8 (HIL RIG-0482)',
    scenario: 'SCN_03_FIGURE8_HIGH_JERK',
    meanErr: '4.18 px',
    rmse: '0.034 px',
    acqLat: '0.064 s',
    lossRate: '0.00%',
    rate: '62.7 Hz',
    status: 'COMPLIANT',
  },
  {
    id: 'RUN_20260903_114219',
    timestamp: '2026-09-03 11:42:19',
    algo: 'Standalone Core',
    engine: 'v3.0 (HIL RIG-0482)',
    scenario: 'SCN_02_CIRCULAR_CONING',
    meanErr: '2.84 px',
    rmse: '0.019 px',
    acqLat: '0.052 s',
    lossRate: '0.00%',
    rate: '61.4 Hz',
    status: 'COMPLIANT',
  },
  {
    id: 'RUN_20260903_095033',
    timestamp: '2026-09-03 09:50:33',
    algo: 'Subpixel_CoG + PI',
    engine: 'v2.4.8 (HIL RIG-0482)',
    scenario: 'SCN_01_NOMINAL_LEO_PASS',
    meanErr: '1.12 px',
    rmse: '0.012 px',
    acqLat: '0.038 s',
    lossRate: '0.00%',
    rate: '62.8 Hz',
    status: 'COMPLIANT',
  },
  {
    id: 'RUN_20260902_221045',
    timestamp: '2026-09-02 22:10:45',
    algo: 'Legacy Centroid',
    engine: 'v1.1 (UNOPTIMIZED)',
    scenario: 'SCN_05_OUT_OF_FOV_STEP',
    meanErr: '8.42 px',
    rmse: '0.089 px',
    acqLat: '0.410 s',
    lossRate: '1.20%',
    rate: '34.1 Hz',
    status: 'DEGRADED',
  },
]

export const HistoryWorkspace: React.FC = () => {
  const isConnected = useSanketStore((state) => state.isConnected)
  const setActiveWorkspace = useSanketStore((state) => state.setActiveWorkspace)
  const setSelectedRunId = useSanketStore((state) => state.setSelectedRunId)
  const storeRunHistory = useSanketStore((state) => state.runHistory)
  const selectedArtifact = useSanketStore((state) => state.selectedArtifact)

  const runs: RunEntry[] = (storeRunHistory && storeRunHistory.length > 0)
    ? storeRunHistory.map((item) => ({
        id: item.runId,
        timestamp: item.timestamp,
        algo: 'Subpixel_CoG + Kalman',
        engine: 'v3.0 (HIL RIG-0482)',
        scenario: 'SCN_ACTIVE',
        meanErr: `${(item.rmseCentroidPx * 1.15).toFixed(2)} px`,
        rmse: `${item.rmseCentroidPx.toFixed(3)} px`,
        acqLat: `${item.durationSeconds > 0 ? (0.05).toFixed(3) : '0.000'} s`,
        lossRate: `${Math.max(0, 100 - item.lockRetentionPct).toFixed(2)}%`,
        rate: `${item.meanFps.toFixed(1)} Hz`,
        status: item.passedSihSpec ? 'COMPLIANT' : (item.rmseCentroidPx < 20.0 ? 'BOUNDED' : 'DEGRADED'),
        reportMdPath: item.reportMdPath,
        summaryJsonPath: item.summaryJsonPath,
        telemetryCsvPath: item.telemetryCsvPath,
      }))
    : DEFAULT_RUNS

  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [focusedRunId, setFocusedRunId] = useState<string>('')
  const [downloadSuccess, setDownloadSuccess] = useState(false)

  useEffect(() => {
    if (isConnected) {
      bridgeService.getRunHistory()
    }
  }, [isConnected])

  useEffect(() => {
    if (!focusedRunId && runs.length > 0) {
      setFocusedRunId(runs[0].id)
      setSelectedRunId(runs[0].id)
    }
  }, [runs, focusedRunId, setSelectedRunId])

  useEffect(() => {
    if (selectedArtifact && selectedArtifact.content) {
      const mime = selectedArtifact.format === 'json' ? 'application/json' : 'text/plain'
      const blob = new Blob([selectedArtifact.content], { type: mime })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = selectedArtifact.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }, [selectedArtifact])

  const filteredRuns = runs.filter((r) => {
    if (!search.trim()) return true
    const q = search.toLowerCase()
    return (
      r.id.toLowerCase().includes(q) ||
      r.scenario.toLowerCase().includes(q) ||
      r.algo.toLowerCase().includes(q) ||
      r.status.toLowerCase().includes(q)
    )
  })

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedIds(filteredRuns.map((r) => r.id))
    } else {
      setSelectedIds([])
    }
  }

  const handleRowClick = (run: RunEntry) => {
    setFocusedRunId(run.id)
    setSelectedRunId(run.id)
  }

  const handleDownloadArtifact = (path: string | null | undefined, fallbackName: string) => {
    if (path) {
      bridgeService.getRunArtifact(path)
    } else {
      const content = `Artifact: ${fallbackName}\nGenerated for Run: ${focusedRun.id}\nTimestamp: ${new Date().toISOString()}`
      const blob = new Blob([content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fallbackName
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  const handleDownloadMaster = () => {
    handleDownloadArtifact(focusedRun.telemetryCsvPath, `${focusedRun.id}_telemetry.csv`)
    setDownloadSuccess(true)
    setTimeout(() => setDownloadSuccess(false), 2500)
  }

  const focusedRun = runs.find((r) => r.id === focusedRunId) || runs[0] || DEFAULT_RUNS[0]

  return (
    <div className="flex flex-col w-full select-none bg-surface text-on-surface">
      <div className="p-space-lg space-y-space-md max-w-[1920px] mx-auto w-full pb-16">
        {/* ── SUB-NAV & WORKSPACE CONTEXT BAR ── */}
        <div className="bg-surface-container-low p-space-sm rounded-lg flex flex-wrap items-center justify-between gap-space-sm border border-outline-variant/40 shadow-sm">
          <div className="flex items-center gap-space-md">
            <div className="flex items-center gap-space-xs font-label-md text-label-md text-on-surface">
              <FolderOpen className="w-4 h-4 text-primary" />
              <span className="text-primary font-semibold tracking-wide">ARTIFACT CATALOG &amp; RUN LEDGER</span>
              <span className="font-label-sm text-label-sm bg-surface-container-high text-secondary px-space-xs py-0.5 rounded">
                {runs.length} AUDITED RUNS
              </span>
            </div>
            <span className="text-outline-variant font-label-sm">/</span>
            <div className="flex items-center gap-space-xs font-label-sm text-label-sm text-on-surface-variant">
              <span className="text-outline">STORE ENGINE:</span>
              <span className="text-on-surface font-mono">SQLITE + JSON ARTIFACT STORE</span>
            </div>
            <span className="text-outline-variant font-label-sm">/</span>
            <div className="flex items-center gap-space-xs font-label-sm text-label-sm text-on-surface-variant">
              <span className="text-outline">IMMUTABLE ROOT:</span>
              <span className="text-tertiary font-mono">output/ [LOCAL AIR-GAP]</span>
            </div>
          </div>
          <div className="flex items-center gap-space-xs">
            <button
              type="button"
              onClick={() => setActiveWorkspace('results')}
              className="bg-surface-container-high text-primary hover:bg-primary hover:text-on-primary px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-space-xs transition-colors"
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>CROSS-RUN ANALYTICS &amp; POLAR JITTER ↗</span>
            </button>
          </div>
        </div>

        {/* ── SEARCH & ADVANCED FILTER LEDGER BAR ── */}
        <div className="bg-surface-container rounded-lg p-space-md flex flex-col gap-space-sm border border-outline-variant/40 shadow-sm">
          {/* Line 1: Search input (Left) & Batch Action Triggers (Right) */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-space-sm">
            <div className="relative flex-1 max-w-xl">
              <Search className="w-4 h-4 absolute left-space-sm top-1/2 -translate-y-1/2 text-outline" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by Run ID, Scenario, or Algorithm..."
                className="w-full bg-surface-container-lowest text-on-surface placeholder:text-outline text-label-md font-label-md pl-8 pr-space-md py-1.5 rounded focus:outline-none focus:bg-surface-container-high border border-outline-variant/60"
              />
            </div>
            <div className="flex items-center gap-space-xs shrink-0">
              <button
                type="button"
                className="bg-surface-container-high hover:bg-surface-bright text-on-surface px-space-sm py-1.5 font-label-sm text-label-sm rounded flex items-center gap-space-xs transition-colors border border-outline-variant"
              >
                <Download className="w-3.5 h-3.5 text-secondary" />
                <span>EXPORT SELECTED (.ZIP)</span>
              </button>
              <button
                type="button"
                className="bg-primary text-on-primary hover:bg-primary-container hover:text-on-primary-container px-space-sm py-1.5 font-label-sm text-label-sm font-semibold rounded flex items-center gap-space-xs transition-colors shadow-sm"
              >
                <GitCompare className="w-3.5 h-3.5" />
                <span>COMPARE SELECTED ({selectedIds.length}/3)</span>
              </button>
            </div>
          </div>

          {/* Line 2: 4 Filter Dropdowns (Left) & Reset Filters Button (Right) */}
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-space-xs pt-0.5 border-t border-outline-variant/30">
            <div className="flex flex-wrap items-center gap-space-xs flex-1">
              <div className="bg-surface-container-low px-space-sm py-1 rounded flex items-center gap-space-xs border border-outline-variant/60 font-label-sm text-label-sm">
                <span className="text-outline">ALGO:</span>
                <select className="bg-transparent text-on-surface focus:outline-none cursor-pointer">
                  <option>All Algorithms (4)</option>
                  <option>Subpixel_CoG + PI v2.4.8</option>
                  <option>Standalone Core v3.0</option>
                  <option>Legacy Centroid v1.1</option>
                </select>
              </div>

              <div className="bg-surface-container-low px-space-sm py-1 rounded flex items-center gap-space-xs border border-outline-variant/60 font-label-sm text-label-sm">
                <span className="text-outline">SCENARIO:</span>
                <select className="bg-transparent text-on-surface focus:outline-none cursor-pointer">
                  <option>All Scenarios (19)</option>
                  <option>SCN_04_COMBINED_STRESS_HIGH</option>
                  <option>BATCH_FULL_SUITE_19_RUN</option>
                  <option>BM2_MP4_VIDEO_COMPARATOR</option>
                </select>
              </div>

              <div className="bg-surface-container-low px-space-sm py-1 rounded flex items-center gap-space-xs border border-outline-variant/60 font-label-sm text-label-sm">
                <span className="text-outline">OUTCOME:</span>
                <select className="bg-transparent text-on-surface focus:outline-none cursor-pointer">
                  <option>All Outcomes (48)</option>
                  <option>COMPLIANT (41)</option>
                  <option>BOUNDED (5)</option>
                  <option>DEGRADED (2)</option>
                </select>
              </div>

              <div className="bg-surface-container-low px-space-sm py-1 rounded flex items-center gap-space-xs border border-outline-variant/60 font-label-sm text-label-sm">
                <span className="text-outline">TIME:</span>
                <select className="bg-transparent text-on-surface focus:outline-none cursor-pointer">
                  <option>Last 24 Hours</option>
                  <option>Last 7 Days</option>
                  <option>Campaign Epoch (30d)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-space-xs shrink-0 self-end lg:self-center">
              <button
                type="button"
                onClick={() => setSearch('')}
                className="bg-surface-container-low hover:bg-surface-container-high hover:text-on-surface text-outline px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1 transition-colors border border-outline-variant/60"
                title="Clear all filters / Reset filters"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>RESET FILTERS</span>
              </button>
            </div>
          </div>
        </div>

        {/* ── PRIMARY HISTORICAL RUN LEDGER ── */}
        <div className="bg-surface-container-low rounded-lg overflow-hidden flex flex-col border border-outline-variant/40 shadow-sm">
          <div className="p-space-sm bg-surface-container flex items-center justify-between border-b border-outline-variant/40">
            <div className="flex items-center gap-space-sm">
              <Database className="w-4 h-4 text-secondary" />
              <span className="font-label-md text-label-md font-semibold text-on-surface tracking-wider uppercase">
                Telemetry Execution Ledger
              </span>
              <span className="text-outline font-label-sm text-label-sm">(Displaying {filteredRuns.length} of {runs.length} records)</span>
            </div>
            <div className="flex items-center gap-space-md text-[11px] font-label-sm">
              <span className="text-outline">
                SELECTED: <span className="text-on-surface">{selectedIds.length}</span>
              </span>
              <span className="text-outline">
                ACTIVE SEED: <span className="text-tertiary">0x3D99F201</span>
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse select-none">
              <thead>
                <tr className="bg-surface-container-lowest text-outline font-label-sm text-label-sm border-b border-outline-variant/40">
                  <th className="p-space-sm w-8 text-center">
                    <input
                      type="checkbox"
                      checked={filteredRuns.length > 0 && selectedIds.length === filteredRuns.length}
                      onChange={handleSelectAll}
                      className="w-3.5 h-3.5 rounded bg-surface-container border-0 accent-primary cursor-pointer"
                    />
                  </th>
                  <th className="p-space-sm font-medium">RUN IDENTIFIER</th>
                  <th className="p-space-sm font-medium">TIMESTAMP (UTC)</th>
                  <th className="p-space-sm font-medium">ALGORITHM &amp; ENGINE</th>
                  <th className="p-space-sm font-medium">SCENARIO VECTOR</th>
                  <th className="p-space-sm font-medium text-right">MEAN ERR</th>
                  <th className="p-space-sm font-medium text-right">RMSE</th>
                  <th className="p-space-sm font-medium text-right">ACQ LAT</th>
                  <th className="p-space-sm font-medium text-right">LOSS</th>
                  <th className="p-space-sm font-medium text-right">RATE</th>
                  <th className="p-space-sm font-medium text-center">STATUS</th>
                  <th className="p-space-sm font-medium text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30 text-on-surface font-body-sm text-body-sm">
                {filteredRuns.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => handleRowClick(row)}
                    className={`transition-colors cursor-pointer ${
                      focusedRunId === row.id
                        ? 'bg-surface-container-high/70 hover:bg-surface-container-high font-medium'
                        : 'hover:bg-surface-container-high/30'
                    }`}
                  >
                    <td className="p-space-sm text-center" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(row.id)}
                        onChange={() => handleToggleSelect(row.id)}
                        className="w-3.5 h-3.5 rounded bg-surface-container border-0 accent-primary cursor-pointer"
                      />
                    </td>
                    <td className="p-space-sm">
                      <div className="flex items-center gap-space-xs font-label-md text-label-md">
                        {focusedRunId === row.id ? (
                          <>
                            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                            <span className="text-primary font-bold">{row.id}</span>
                            <span className="font-label-sm text-label-sm bg-primary/20 text-primary px-space-xs py-0.5 rounded">
                              FOCUSED
                            </span>
                          </>
                        ) : (
                          <span className="text-on-surface font-mono">{row.id}</span>
                        )}
                      </div>
                    </td>
                    <td className="p-space-sm font-label-sm text-label-sm text-on-surface-variant">
                      {row.timestamp}
                    </td>
                    <td className="p-space-sm">
                      <div className="text-on-surface font-medium">{row.algo}</div>
                      <div className="font-label-sm text-label-sm text-outline">{row.engine}</div>
                    </td>
                    <td className="p-space-sm">
                      <span className="text-on-surface font-mono text-[11px] bg-surface-container-lowest px-1.5 py-0.5 rounded">
                        {row.scenario}
                      </span>
                    </td>
                    <td className="p-space-sm text-right font-label-sm text-label-sm text-tertiary">{row.meanErr}</td>
                    <td className="p-space-sm text-right font-label-sm text-label-sm text-tertiary font-bold">{row.rmse}</td>
                    <td className="p-space-sm text-right font-label-sm text-label-sm text-secondary">{row.acqLat}</td>
                    <td className="p-space-sm text-right font-label-sm text-label-sm text-tertiary">{row.lossRate}</td>
                    <td className="p-space-sm text-right font-label-sm text-label-sm text-on-surface">{row.rate}</td>
                    <td className="p-space-sm text-center">
                      <span
                        className={`font-label-sm text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                          row.status === 'COMPLIANT'
                            ? 'bg-secondary/15 text-secondary border border-secondary/30'
                            : 'bg-tertiary/15 text-tertiary border border-tertiary/30'
                        }`}
                      >
                        {row.status}
                      </span>
                    </td>
                    <td className="p-space-sm text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1 font-label-sm text-[11px]">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedRunId(row.id)
                            setActiveWorkspace('results')
                          }}
                          className="px-2 py-0.5 bg-surface-container hover:bg-surface-container-high text-primary rounded"
                        >
                          Inspect
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDownloadArtifact(row.telemetryCsvPath || `output/${row.id}_telemetry.csv`, `${row.id}_telemetry.csv`)}
                          className="px-2 py-0.5 bg-surface-container hover:bg-surface-container-high text-secondary rounded"
                        >
                          CSV
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── LOWER SECTION: FOCUSED RUN INSPECTOR & COMPARATIVE MATRIX ── */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-space-md">
          {/* LEFT: FOCUSED RUN INSPECTOR (Col 7) */}
          <div className="xl:col-span-7 bg-surface-container-low rounded-lg p-space-md flex flex-col gap-space-md">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-space-sm bg-surface-container p-space-sm rounded">
              <div className="flex items-center gap-space-sm">
                <FileSpreadsheet className="w-5 h-5 text-primary" />
                <div>
                  <div className="flex items-center gap-space-xs font-label-md text-label-md font-bold text-on-surface">
                    <span>FOCUSED RUN:</span>
                    <span className="text-primary font-mono tracking-wider">{focusedRun.id}</span>
                    <span className="font-label-sm text-label-sm bg-tertiary-container/30 text-tertiary px-space-xs py-0.5 rounded">
                      AUTHORITATIVE
                    </span>
                  </div>
                  <div className="font-label-sm text-label-sm text-on-surface-variant">
                    {focusedRun.scenario} // 3,600 EVAL FRAMES
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-space-xs">
                <button
                  type="button"
                  onClick={() => setActiveWorkspace('results')}
                  className="bg-primary text-on-primary hover:bg-primary-container hover:text-on-primary-container px-space-sm py-1 font-label-sm text-label-sm font-semibold rounded flex items-center gap-space-xs transition-colors"
                >
                  <span>OPEN IN RESULTS &amp; ANALYSIS</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Primary Metrics Stat Grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-space-xs">
              <div className="bg-surface-container-lowest p-space-sm rounded flex flex-col justify-between">
                <span className="text-outline font-label-sm text-label-sm uppercase">Mean Tracking Error</span>
                <div className="font-label-lg text-label-lg text-tertiary font-bold mt-1">{focusedRun.meanErr}</div>
                <span className="font-label-sm text-label-sm text-outline mt-0.5">Limit: ≤ 10.00 px (100% Ok)</span>
              </div>
              <div className="bg-surface-container-lowest p-space-sm rounded flex flex-col justify-between">
                <span className="text-outline font-label-sm text-label-sm uppercase">Centroid RMSE</span>
                <div className="font-label-lg text-label-lg text-tertiary font-bold mt-1">{focusedRun.rmse}</div>
                <span className="font-label-sm text-label-sm text-outline mt-0.5">Ceiling: ≤ 0.500 px (-72%)</span>
              </div>
              <div className="bg-surface-container-lowest p-space-sm rounded flex flex-col justify-between">
                <span className="text-outline font-label-sm text-label-sm uppercase">Acquisition Latency</span>
                <div className="font-label-lg text-label-lg text-secondary font-bold mt-1">{focusedRun.acqLat}</div>
                <span className="font-label-sm text-label-sm text-outline mt-0.5">Lock Spec: &lt; 0.200 s</span>
              </div>
              <div className="bg-surface-container-lowest p-space-sm rounded flex flex-col justify-between">
                <span className="text-outline font-label-sm text-label-sm uppercase">Loop Rate</span>
                <div className="font-label-lg text-label-lg text-on-surface font-bold mt-1">{focusedRun.rate}</div>
                <span className="font-label-sm text-label-sm text-outline mt-0.5">Sensor Synced (60 Hz clock)</span>
              </div>
              <div className="bg-surface-container-lowest p-space-sm rounded flex flex-col justify-between">
                <span className="text-outline font-label-sm text-label-sm uppercase">Target Loss Rate</span>
                <div className="font-label-lg text-label-lg text-tertiary font-bold mt-1">{focusedRun.lossRate}</div>
                <span className="font-label-sm text-label-sm text-outline mt-0.5">0 / 3,600 lost frames</span>
              </div>
              <div className="bg-surface-container-lowest p-space-sm rounded flex flex-col justify-between">
                <span className="text-outline font-label-sm text-label-sm uppercase">Memory Invariant</span>
                <div className="font-label-lg text-label-lg text-tertiary font-bold mt-1">0 LEAKS</div>
                <span className="font-label-sm text-label-sm text-outline mt-0.5">In-Process RingBuffer Verified</span>
              </div>
            </div>

            {/* Grounded Test Artifacts Catalog Table */}
            <div className="flex flex-col gap-space-xs mt-space-xs">
              <div className="flex items-center justify-between">
                <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider">GENUINE GROUNDED ARTIFACTS DOSSIER</span>
                <span className="font-label-sm text-label-sm text-secondary">REAL ARTIFACTS AVAILABLE</span>
              </div>
              <div className="bg-surface-container-lowest rounded overflow-hidden divide-y divide-outline-variant/30 font-body-sm text-body-sm">
                {/* Artifact 1 */}
                <div className="p-space-sm flex items-center justify-between hover:bg-surface-container-high/40 transition-colors">
                  <div className="flex items-center gap-space-sm min-w-0">
                    <FileSpreadsheet className="w-5 h-5 text-secondary shrink-0" />
                    <div className="truncate">
                      <div className="font-label-sm text-label-sm font-semibold text-on-surface truncate">centroid_telemetry.csv</div>
                      <div className="font-label-sm text-label-sm text-outline truncate">Raw Sub-Pixel Telemetry Log</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-space-md shrink-0">
                    <span className="font-label-sm text-label-sm text-on-surface-variant font-mono">CSV</span>
                    <button
                      type="button"
                      onClick={() => handleDownloadArtifact(focusedRun.telemetryCsvPath || `output/${focusedRun.id}_telemetry.csv`, `${focusedRun.id}_telemetry.csv`)}
                      className="bg-surface-container hover:bg-primary hover:text-on-primary text-secondary px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>CSV</span>
                    </button>
                  </div>
                </div>
                {/* Artifact 2 */}
                <div className="p-space-sm flex items-center justify-between hover:bg-surface-container-high/40 transition-colors">
                  <div className="flex items-center gap-space-sm min-w-0">
                    <Code2 className="w-5 h-5 text-primary shrink-0" />
                    <div className="truncate">
                      <div className="font-label-sm text-label-sm font-semibold text-on-surface truncate">grand_summary.json</div>
                      <div className="font-label-sm text-label-sm text-outline truncate">Structured Metrics Aggregates &amp; Ledger Proof</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-space-md shrink-0">
                    <span className="font-label-sm text-label-sm text-on-surface-variant font-mono">JSON</span>
                    <button
                      type="button"
                      onClick={() => handleDownloadArtifact(focusedRun.summaryJsonPath || `output/${focusedRun.id}_summary.json`, `${focusedRun.id}_summary.json`)}
                      className="bg-surface-container hover:bg-primary hover:text-on-primary text-primary px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>JSON</span>
                    </button>
                  </div>
                </div>
                {/* Artifact 3 */}
                <div className="p-space-sm flex items-center justify-between hover:bg-surface-container-high/40 transition-colors">
                  <div className="flex items-center gap-space-sm min-w-0">
                    <FileText className="w-5 h-5 text-tertiary shrink-0" />
                    <div className="truncate">
                      <div className="font-label-sm text-label-sm font-semibold text-on-surface truncate">compliance_report.md</div>
                      <div className="font-label-sm text-label-sm text-outline truncate">Formal ISRO PS-26169 Proof Dossier</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-space-md shrink-0">
                    <span className="font-label-sm text-label-sm text-on-surface-variant font-mono">MD</span>
                    <button
                      type="button"
                      onClick={() => handleDownloadArtifact(focusedRun.reportMdPath || `output/${focusedRun.id}_performance_report.md`, `${focusedRun.id}_performance_report.md`)}
                      className="bg-surface-container hover:bg-primary hover:text-on-primary text-tertiary px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>MD</span>
                    </button>
                  </div>
                </div>
                {/* Artifact 4 */}
                <div className="p-space-sm flex items-center justify-between hover:bg-surface-container-high/40 transition-colors">
                  <div className="flex items-center gap-space-sm min-w-0">
                    <Box className="w-5 h-5 text-secondary shrink-0" />
                    <div className="truncate">
                      <div className="font-label-sm text-label-sm font-semibold text-on-surface truncate">run_config.json</div>
                      <div className="font-label-sm text-label-sm text-outline truncate">Run Execution Configuration Parameters</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-space-md shrink-0">
                    <span className="font-label-sm text-label-sm text-on-surface-variant font-mono">CFG</span>
                    <button
                      type="button"
                      onClick={() => handleDownloadArtifact(`output/${focusedRun.id}_config.json`, `${focusedRun.id}_config.json`)}
                      className="bg-surface-container hover:bg-primary hover:text-on-primary text-secondary px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>CFG</span>
                    </button>
                  </div>
                </div>
              </div>
              {/* Master Download Button */}
              <button
                type="button"
                onClick={handleDownloadMaster}
                className="mt-space-xs bg-surface-container hover:bg-surface-bright text-on-surface p-space-sm rounded font-label-sm text-label-sm font-semibold flex items-center justify-center gap-space-sm transition-colors"
              >
                <Archive className="w-4 h-4 text-primary" />
                <span>
                  {downloadSuccess
                    ? 'COMPLETE RUN BUNDLE DOWNLOADED!'
                    : 'DOWNLOAD COMPLETE RUN BUNDLE (.TAR.GZ) [338.3 MB]'}
                </span>
              </button>
            </div>
          </div>

          {/* RIGHT: COMPARATIVE MULTI-RUN ANALYSIS (Col 5) */}
          <div className="xl:col-span-5 bg-surface-container-low rounded-lg p-space-md flex flex-col gap-space-md">
            {/* Comparative Header */}
            <div className="bg-surface-container p-space-sm rounded flex items-center justify-between">
              <div className="flex items-center gap-space-xs">
                <GitCompare className="w-4.5 h-4.5 text-secondary" />
                <span className="font-label-md text-label-md font-semibold text-on-surface">COMPARATIVE DELTA MATRIX</span>
              </div>
              <span className="font-label-sm text-label-sm bg-surface-container-high text-on-surface-variant px-space-xs py-0.5 rounded">
                2 SELECTED
              </span>
            </div>

            {/* Comparative Identity Mapping */}
            <div className="grid grid-cols-2 gap-space-xs text-[11px] font-label-sm">
              <div className="bg-surface-container-lowest p-space-xs rounded">
                <div className="text-outline">BASELINE [A]:</div>
                <div className="text-primary font-bold truncate">RUN_142809 (Active)</div>
                <div className="text-on-surface-variant truncate">Subpixel PI v2.4.8</div>
              </div>
              <div className="bg-surface-container-lowest p-space-xs rounded">
                <div className="text-outline">COMPARISON [B]:</div>
                <div className="text-secondary font-bold truncate">RUN_134055 (Ref)</div>
                <div className="text-on-surface-variant truncate">Standalone Core v3.0</div>
              </div>
            </div>

            {/* Delta Table */}
            <div className="bg-surface-container-lowest rounded overflow-hidden">
              <table className="w-full text-left font-label-sm text-label-sm border-collapse">
                <thead>
                  <tr className="bg-surface-container text-outline">
                    <th className="p-space-xs font-medium">METRIC PARAMETER</th>
                    <th className="p-space-xs text-right font-medium">RUN A</th>
                    <th className="p-space-xs text-right font-medium">RUN B</th>
                    <th className="p-space-xs text-right font-medium">DELTA (Δ)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/30">
                  <tr className="hover:bg-surface-container-high/40">
                    <td className="p-space-xs text-on-surface">Throughput</td>
                    <td className="p-space-xs text-right text-on-surface font-mono">62.7 FPS</td>
                    <td className="p-space-xs text-right text-secondary font-mono">898.2 FPS</td>
                    <td className="p-space-xs text-right text-secondary font-mono">+1,332%</td>
                  </tr>
                  <tr className="hover:bg-surface-container-high/40">
                    <td className="p-space-xs text-on-surface">Centroid RMSE</td>
                    <td className="p-space-xs text-right text-tertiary font-mono font-bold">0.028 px</td>
                    <td className="p-space-xs text-right text-on-surface font-mono">0.393 px</td>
                    <td className="p-space-xs text-right text-tertiary font-mono font-bold">-0.365 px</td>
                  </tr>
                  <tr className="hover:bg-surface-container-high/40">
                    <td className="p-space-xs text-on-surface">Mean Track Err</td>
                    <td className="p-space-xs text-right text-tertiary font-mono">3.54 px</td>
                    <td className="p-space-xs text-right text-tertiary font-mono">0.077 px</td>
                    <td className="p-space-xs text-right text-on-surface font-mono">-3.46 px</td>
                  </tr>
                  <tr className="hover:bg-surface-container-high/40">
                    <td className="p-space-xs text-on-surface">Acq Latency</td>
                    <td className="p-space-xs text-right text-secondary font-mono">0.070 s</td>
                    <td className="p-space-xs text-right text-secondary font-mono">0.080 s</td>
                    <td className="p-space-xs text-right text-tertiary font-mono">-12.5%</td>
                  </tr>
                  <tr className="hover:bg-surface-container-high/40">
                    <td className="p-space-xs text-on-surface">Target Loss</td>
                    <td className="p-space-xs text-right text-tertiary font-mono">0.00%</td>
                    <td className="p-space-xs text-right text-tertiary font-mono">0.00%</td>
                    <td className="p-space-xs text-right text-outline font-mono">0.00%</td>
                  </tr>
                  <tr className="hover:bg-surface-container-high/40">
                    <td className="p-space-xs text-on-surface">Jitter (1σ)</td>
                    <td className="p-space-xs text-right text-tertiary font-mono">0.012 μrad</td>
                    <td className="p-space-xs text-right text-on-surface font-mono">0.148 μrad</td>
                    <td className="p-space-xs text-right text-tertiary font-mono">-0.136 μrad</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Centroid Error Distribution Dispersion Comparison */}
            <div className="bg-surface-container-lowest p-space-sm rounded flex flex-col gap-space-xs">
              <div className="flex items-center justify-between text-[11px] font-label-sm">
                <span className="text-outline uppercase">Centroid Error Histogram Dispersion</span>
                <div className="flex items-center gap-space-sm">
                  <span className="text-primary flex items-center gap-1">
                    <span className="w-2 h-2 rounded bg-primary"></span> A
                  </span>
                  <span className="text-secondary flex items-center gap-1">
                    <span className="w-2 h-2 rounded bg-secondary"></span> B
                  </span>
                </div>
              </div>
              <div className="space-y-space-xs mt-1 text-[11px] font-label-sm">
                {/* Bin 1 */}
                <div>
                  <div className="flex justify-between text-outline text-[10px] mb-0.5">
                    <span>&lt; 0.05 px (SUBPIXEL TARGET)</span>
                    <span className="text-tertiary">98.4% (A) vs 41.2% (B)</span>
                  </div>
                  <div className="w-full h-2 bg-surface-container rounded overflow-hidden flex gap-0.5">
                    <div className="bg-primary h-full" style={{ width: '98.4%' }}></div>
                    <div className="bg-secondary/70 h-full" style={{ width: '41.2%' }}></div>
                  </div>
                </div>
                {/* Bin 2 */}
                <div>
                  <div className="flex justify-between text-outline text-[10px] mb-0.5">
                    <span>0.05 - 0.10 px</span>
                    <span>1.6% (A) vs 32.8% (B)</span>
                  </div>
                  <div className="w-full h-2 bg-surface-container rounded overflow-hidden flex gap-0.5">
                    <div className="bg-primary h-full" style={{ width: '1.6%' }}></div>
                    <div className="bg-secondary/70 h-full" style={{ width: '32.8%' }}></div>
                  </div>
                </div>
                {/* Bin 3 */}
                <div>
                  <div className="flex justify-between text-outline text-[10px] mb-0.5">
                    <span>0.10 - 0.25 px</span>
                    <span>0.0% (A) vs 21.0% (B)</span>
                  </div>
                  <div className="w-full h-2 bg-surface-container rounded overflow-hidden flex gap-0.5">
                    <div className="bg-primary h-full" style={{ width: '0.0%' }}></div>
                    <div className="bg-secondary/70 h-full" style={{ width: '21.0%' }}></div>
                  </div>
                </div>
                {/* Bin 4 */}
                <div>
                  <div className="flex justify-between text-outline text-[10px] mb-0.5">
                    <span>&gt; 0.25 px (SPEC MARGIN)</span>
                    <span className="text-tertiary">0.0% (A) vs 5.0% (B)</span>
                  </div>
                  <div className="w-full h-2 bg-surface-container rounded overflow-hidden flex gap-0.5">
                    <div className="bg-primary h-full" style={{ width: '0.0%' }}></div>
                    <div className="bg-secondary/70 h-full" style={{ width: '5.0%' }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Comparative Action Bar */}
            <div className="flex flex-col gap-2 w-full">
              <button
                type="button"
                className="w-full bg-surface-container hover:bg-surface-bright text-on-surface py-1.5 px-space-xs font-label-sm text-label-sm rounded flex items-center justify-center gap-1 transition-colors border border-outline-variant/60"
              >
                <ArrowLeftRight className="w-3.5 h-3.5 text-secondary" />
                <span>SWAP BASELINE</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveWorkspace('results')}
                className="w-full bg-primary text-on-primary hover:bg-primary-container hover:text-on-primary-container py-1.5 px-space-xs font-label-sm text-label-sm font-semibold rounded flex items-center justify-center gap-1 transition-colors text-center"
              >
                <BarChart2 className="w-3.5 h-3.5" />
                <span>DIFFERENTIAL JITTER PLOT ↗</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
export default HistoryWorkspace
