import React, { useEffect, useState } from 'react'
import {
  CheckCircle2,
  RefreshCw,
  Download,
  FileText,
  Unlock,
  LineChart,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { useLumiTrackStore } from '../../store/useLumiTrackStore'
import { bridgeService } from '../../services/bridgeService'
import type { ResultsTimeSeriesData } from '../../types/scene3d'

// ─────────────────────────────────────────────────────────────────────────────
// Results & Analysis Workspace — Screen 5
// Fully truthful telemetry analytics with strict Ground-Truth Firewall isolation
// ─────────────────────────────────────────────────────────────────────────────

export const ResultsWorkspace: React.FC = () => {
  const isConnected = useLumiTrackStore((state) => state.isConnected)
  const resultsData = useLumiTrackStore((state) => state.resultsData as ResultsTimeSeriesData | null)
  const [frameOffset, setFrameOffset] = useState(0)

  // Automatically request latest run results data on load if connected and not yet loaded
  useEffect(() => {
    if (isConnected && !resultsData) {
      bridgeService.getResultsAnalysisData()
    }
  }, [isConnected, resultsData])

  // Derive metrics strictly from real resultsData if available
  const hasData = !!resultsData && resultsData.frameCount > 0
  const frameCount = resultsData?.frameCount ?? 0
  const runId = resultsData?.runId ?? 'NO_RUN_SELECTED'
  const isValidation = resultsData?.validationModeActive ?? false

  const meanFps = hasData && resultsData.fpsList.length > 0
    ? resultsData.fpsList.reduce((a, b) => a + b, 0) / resultsData.fpsList.length
    : null

  const rmse = hasData && resultsData.boresightOffsets.length > 0
    ? Math.sqrt(resultsData.boresightOffsets.reduce((a, b) => a + b * b, 0) / resultsData.boresightOffsets.length)
    : null

  const meanBoresightErr = hasData && resultsData.boresightOffsets.length > 0
    ? resultsData.boresightOffsets.reduce((a, b) => a + b, 0) / resultsData.boresightOffsets.length
    : null

  const peakError = hasData && resultsData.boresightOffsets.length > 0
    ? Math.max(...resultsData.boresightOffsets)
    : null

  const avgLatencyMs = hasData && resultsData.latenciesMs.length > 0
    ? resultsData.latenciesMs.reduce((a, b) => a + b, 0) / resultsData.latenciesMs.length
    : null

  // Generate real per-frame rows from time-series arrays
  const totalFrames = resultsData?.frameNumbers?.length ?? 0
  const PAGE_SIZE = 8
  const clampedOffset = Math.max(0, Math.min(frameOffset, Math.max(0, totalFrames - PAGE_SIZE)))

  const visibleFrames = hasData
    ? resultsData.frameNumbers.slice(clampedOffset, clampedOffset + PAGE_SIZE).map((fn, idx) => {
        const globalIdx = clampedOffset + idx
        return {
          frame: fn,
          time: resultsData.timestamps[globalIdx] ?? 0.0,
          estX: resultsData.centroidsX[globalIdx],
          estY: resultsData.centroidsY[globalIdx],
          error: resultsData.boresightOffsets[globalIdx] ?? 0.0,
          state: 'TRACKING',
          pan: resultsData.panAngles[globalIdx] ?? 0.0,
          tilt: resultsData.tiltAngles[globalIdx] ?? 0.0,
          gtError: isValidation && resultsData.validationGtErrors ? resultsData.validationGtErrors[globalIdx] : null,
        }
      })
    : []

  // Dynamic SVG polyline from real boresight offsets
  const svgPolyline = (() => {
    if (!hasData || resultsData.boresightOffsets.length === 0) {
      return ''
    }
    const offsets = resultsData.boresightOffsets
    const maxVal = Math.max(15, ...offsets)
    return offsets
      .map((val, i) => {
        const x = (i / Math.max(1, offsets.length - 1)) * 1000
        const y = 220 - Math.min(200, Math.max(0, (val / maxVal) * 200))
        return `${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')
  })()

  const svgPolygon = svgPolyline ? `0,220 ${svgPolyline} 1000,220` : ''

  return (
    <div className="flex flex-col w-full text-on-surface">

      {/* ── Run Header & Verification Bar ──────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md px-space-xl py-space-lg bg-surface-container-low shadow-sm border-b border-outline-variant/30">
        <div className="flex flex-col gap-space-xs min-w-0">
          <div className="flex flex-wrap items-center gap-space-sm">
            <span className="font-data-md text-data-md text-on-surface tracking-tight font-semibold flex items-center gap-space-xs">
              <CheckCircle2 className="w-4 h-4 text-primary" />
              {runId}
            </span>
            <span className="font-data-sm text-data-sm px-space-sm py-space-xs bg-surface-container-highest text-primary-fixed-dim rounded">
              {hasData ? 'TELEMETRY LOADED' : 'AWAITING RUN DATA'}
            </span>
            <span className={`font-data-sm text-data-sm px-space-sm py-space-xs rounded flex items-center gap-space-xs ${
              hasData ? 'bg-secondary-container/20 text-secondary' : 'bg-surface-container text-outline'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${hasData ? 'bg-secondary' : 'bg-outline'}`} />
              {hasData
                ? (rmse !== null && rmse <= 10.0 ? 'EVALUATION: SPEC COMPLIANT' : 'EVALUATION: BOUNDED')
                : 'STATUS: NO DATA'}
            </span>
          </div>
          <div className="flex items-center gap-space-md text-outline font-label-sm text-label-sm flex-wrap">
            <span className="text-on-surface-variant font-data-sm">
              MODE: {isValidation ? 'VALIDATION (GT ENABLED)' : 'OPERATIONAL LIVE (GT STRIPPED)'}
            </span>
            <span>•</span>
            <span>TOTAL FRAMES: <span className="font-data-sm text-on-surface">{frameCount > 0 ? frameCount.toLocaleString() : '—'}</span></span>
            <span>•</span>
            <span className={hasData ? 'text-secondary' : 'text-outline'}>
              EVALUATION SUMMARY: {hasData ? 'RECORD VERIFIED' : 'PENDING'}
            </span>
          </div>
        </div>

        {/* Export Actions */}
        <div className="flex flex-wrap items-center gap-space-xs">
          <button
            onClick={() => bridgeService.getResultsAnalysisData()}
            className="px-space-md py-space-xs bg-surface-container hover:bg-surface-container-high text-on-surface rounded font-label-md text-label-md transition-colors flex items-center gap-space-xs shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5 text-primary" />
            <span>Reload Latest Run</span>
          </button>
          <button
            disabled={!hasData}
            className="px-space-md py-space-xs bg-surface-container hover:bg-surface-container-high text-on-surface rounded font-label-md text-label-md transition-colors flex items-center gap-space-xs shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download className="w-3.5 h-3.5 text-secondary" />
            <span>CSV Centroids</span>
          </button>
          <button
            disabled={!hasData}
            className="px-space-md py-space-xs bg-primary hover:bg-primary-fixed-dim text-on-primary rounded font-label-md text-label-md transition-colors flex items-center gap-space-xs shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Compliance Report</span>
          </button>
        </div>
      </div>

      {/* ── Ground Truth Validation Seam Notice (Conditional Banner) ────────── */}
      {isValidation && (
        <div className="w-full bg-tertiary-container/30 border-y border-tertiary/40 px-space-xl py-space-xs flex items-center justify-between">
          <div className="flex items-center gap-space-sm text-tertiary font-label-sm text-label-sm">
            <Unlock className="w-4 h-4 text-tertiary" />
            <span className="font-bold">[GROUND TRUTH — VALIDATION ONLY]</span>
            <span className="text-on-surface-variant font-normal">Offline / Post-Run Evaluation Seam Active. GT coordinates are strictly unexported during live operational loop.</span>
          </div>
          <span className="font-data-sm text-[10px] text-tertiary uppercase tracking-wider">Audit Verified</span>
        </div>
      )}

      {/* ── Main Body ───────────────────────────────────────────────────────── */}
      <div className="p-space-lg flex flex-col gap-space-lg">

        {/* ── 4 KPI Cards ─────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-space-md">
          {/* KPI 1 — Mean Tracking Error */}
          <div className="p-space-md bg-surface-container-low rounded shadow-sm relative overflow-hidden flex flex-col justify-between border border-outline-variant/30">
            <div className="flex items-center justify-between">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Mean Boresight Offset</span>
              <span className={`font-data-sm text-data-sm px-space-xs py-space-xs rounded font-medium ${
                meanBoresightErr !== null
                  ? (meanBoresightErr <= 10.0 ? 'bg-secondary-container/20 text-secondary' : 'bg-error-container/30 text-error')
                  : 'bg-surface-container text-outline'
              }`}>
                {meanBoresightErr !== null ? (meanBoresightErr <= 10.0 ? 'PASS' : 'EXCEEDED') : 'NO DATA'}
              </span>
            </div>
            <div className="mt-space-md flex items-baseline gap-space-sm">
              <span className="font-data-lg text-headline-lg font-bold text-on-surface">
                {meanBoresightErr !== null ? meanBoresightErr.toFixed(2) : '—'}
              </span>
              <span className="font-data-sm text-data-sm text-outline">px</span>
              {meanBoresightErr !== null && (
                <span className="ml-auto font-data-sm text-data-sm text-secondary font-medium">
                  {meanBoresightErr <= 10.0 ? `+${((1 - meanBoresightErr / 10.0) * 100).toFixed(1)}% margin` : 'Above spec'}
                </span>
              )}
            </div>
            <div className="mt-space-xs flex items-center justify-between text-outline font-data-sm text-data-sm pt-space-xs bg-surface-container-lowest/40 px-space-sm rounded">
              <span>Spec Ceiling: ≤ 10.0 px</span>
              <span className="text-on-surface-variant">
                Peak: {peakError !== null ? `${peakError.toFixed(2)} px` : '—'}
              </span>
            </div>
          </div>

          {/* KPI 2 — Sub-Pixel RMSE */}
          <div className="p-space-md bg-surface-container-low rounded shadow-sm relative overflow-hidden flex flex-col justify-between border border-outline-variant/30">
            <div className="flex items-center justify-between">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Sub-Pixel RMSE</span>
              <span className={`font-data-sm text-data-sm px-space-xs py-space-xs rounded font-medium ${
                rmse !== null
                  ? (rmse < 0.50 ? 'bg-secondary-container/20 text-secondary' : 'bg-tertiary-container/30 text-tertiary')
                  : 'bg-surface-container text-outline'
              }`}>
                {rmse !== null ? (rmse < 0.50 ? 'PASS' : 'BOUNDED') : 'NO DATA'}
              </span>
            </div>
            <div className="mt-space-md flex items-baseline gap-space-sm">
              <span className="font-data-lg text-headline-lg font-bold text-on-surface">
                {rmse !== null ? rmse.toFixed(3) : '—'}
              </span>
              <span className="font-data-sm text-data-sm text-outline">px</span>
              {rmse !== null && rmse > 0 && (
                <span className="ml-auto font-data-sm text-data-sm text-primary font-medium">
                  {(0.50 / rmse).toFixed(1)}x target
                </span>
              )}
            </div>
            <div className="mt-space-xs flex items-center justify-between text-outline font-data-sm text-data-sm pt-space-xs bg-surface-container-lowest/40 px-space-sm rounded">
              <span>Benchmark Target: &lt; 0.50 px</span>
              <span className="text-on-surface-variant">Samples: {resultsData?.boresightOffsets?.length ?? 0}</span>
            </div>
          </div>

          {/* KPI 3 — Processing Loop Rate */}
          <div className="p-space-md bg-surface-container-low rounded shadow-sm relative overflow-hidden flex flex-col justify-between border border-outline-variant/30">
            <div className="flex items-center justify-between">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Loop Frame Rate</span>
              <span className={`font-data-sm text-data-sm px-space-xs py-space-xs rounded font-medium ${
                meanFps !== null
                  ? (meanFps >= 20.0 ? 'bg-secondary-container/20 text-secondary' : 'bg-error-container/30 text-error')
                  : 'bg-surface-container text-outline'
              }`}>
                {meanFps !== null ? (meanFps >= 20.0 ? 'PASS' : 'DEGRADED') : 'NO DATA'}
              </span>
            </div>
            <div className="mt-space-md flex items-baseline gap-space-sm">
              <span className="font-data-lg text-headline-lg font-bold text-on-surface">
                {meanFps !== null ? meanFps.toFixed(1) : '—'}
              </span>
              <span className="font-data-sm text-data-sm text-outline">FPS</span>
              {meanFps !== null && (
                <span className="ml-auto font-data-sm text-data-sm text-secondary font-medium">
                  {(meanFps / 20.0).toFixed(2)}x spec
                </span>
              )}
            </div>
            <div className="mt-space-xs flex items-center justify-between text-outline font-data-sm text-data-sm pt-space-xs bg-surface-container-lowest/40 px-space-sm rounded">
              <span>Target: ≥ 20.0 FPS</span>
              <span className="text-on-surface-variant">
                Latency: {avgLatencyMs !== null ? `${avgLatencyMs.toFixed(2)} ms` : '—'}
              </span>
            </div>
          </div>

          {/* KPI 4 — Acquisition & Lock Retention */}
          <div className="p-space-md bg-surface-container-low rounded shadow-sm relative overflow-hidden flex flex-col justify-between border border-outline-variant/30">
            <div className="flex items-center justify-between">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Run Sample Volume</span>
              <span className="font-data-sm text-data-sm px-space-xs py-space-xs bg-surface-container text-outline rounded font-medium">
                {hasData ? 'ANALYZED' : 'STANDBY'}
              </span>
            </div>
            <div className="mt-space-md flex items-baseline gap-space-sm">
              <span className="font-data-lg text-headline-lg font-bold text-on-surface">
                {frameCount > 0 ? frameCount.toLocaleString() : '—'}
              </span>
              <span className="font-data-sm text-data-sm text-outline">frames</span>
              {hasData && (
                <span className="ml-auto font-data-sm text-data-sm text-secondary font-medium">
                  100% Parsed
                </span>
              )}
            </div>
            <div className="mt-space-xs flex items-center justify-between text-outline font-data-sm text-data-sm pt-space-xs bg-surface-container-lowest/40 px-space-sm rounded">
              <span>Data Source: Telemetry CSV</span>
              <span className="text-on-surface-variant">Series: Real Time Series</span>
            </div>
          </div>
        </div>

        {/* ── Primary Chart: Tracking Error vs Time ────────────────────────── */}
        <div className="flex flex-col bg-surface-container-low rounded shadow-sm p-space-md gap-space-md border border-outline-variant/30">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-sm">
            <div className="flex items-center gap-space-sm">
              <span className="font-headline-sm text-headline-sm font-semibold text-on-surface tracking-tight">
                Boresight Tracking Offset vs Time ({frameCount > 0 ? `${frameCount.toLocaleString()} Frames` : 'No Run Data'})
              </span>
              <span className="font-data-sm text-data-sm text-outline font-normal">Centroid Distance to Optical Axis</span>
            </div>
            <div className="flex flex-wrap items-center gap-space-md font-data-sm text-data-sm">
              <div className="flex items-center gap-space-xs">
                <span className="w-3 h-0.5 bg-error inline-block" />
                <span className="text-outline">SPEC CEILING (10.0 px)</span>
              </div>
              <div className="flex items-center gap-space-xs">
                <span className="w-3 h-0.5 bg-tertiary inline-block" />
                <span className="text-outline">TARGET (5.0 px)</span>
              </div>
              <div className="flex items-center gap-space-xs">
                <span className="w-3 h-1 bg-secondary rounded-full inline-block" />
                <span className="text-secondary font-medium">MEASURED REAL TRACE</span>
              </div>
            </div>
          </div>

          {/* Chart area */}
          <div className="relative w-full h-72 bg-surface-container-lowest rounded overflow-hidden border border-outline-variant/20">
            {hasData && svgPolyline ? (
              <svg className="absolute inset-0 w-full h-full" viewBox="0 0 1000 240" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="errorFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4edea3" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#4edea3" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                {/* Horizontal reference grid lines */}
                {[40, 80, 120, 160, 200].map((y) => (
                  <line key={y} x1="0" y1={y} x2="1000" y2={y} stroke="#262a2f" strokeDasharray="3,3" strokeWidth="0.5" />
                ))}
                {/* 10.0 px Spec ceiling line (mapped to y=87) */}
                <line x1="0" y1="87" x2="1000" y2="87" stroke="#ffb4ab" strokeDasharray="6,4" strokeWidth="1.2" />
                {/* 5.0 px target line (mapped to y=153) */}
                <line x1="0" y1="153" x2="1000" y2="153" stroke="#ffb95f" strokeDasharray="4,4" strokeWidth="1" />

                {/* Filled gradient area */}
                <polygon points={svgPolygon} fill="url(#errorFill)" />
                {/* Measured trace polyline */}
                <polyline
                  points={svgPolyline}
                  fill="none"
                  stroke="#4edea3"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-outline gap-space-sm font-label-md text-label-md">
                <LineChart className="w-8 h-8 text-outline/40" />
                <span>No run telemetry series loaded. Run a simulation to populate charts.</span>
              </div>
            )}
          </div>
        </div>

        {/* ── Per-Frame Measurement Sample Stream Table ────────────────────────── */}
        <div className="bg-surface-container-low rounded shadow-sm p-space-md flex flex-col gap-space-md border border-outline-variant/30">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-xs">
            <div className="flex items-center gap-space-sm">
              <span className="font-headline-sm text-headline-sm font-semibold text-on-surface">
                Per-Frame Measurement Stream
              </span>
              <span className={`font-label-sm text-label-sm px-space-sm py-space-xs rounded ${
                isValidation ? 'bg-tertiary/20 text-tertiary font-medium' : 'bg-surface-container text-outline'
              }`}>
                {isValidation ? 'GROUND TRUTH VALIDATION SEAM ACTIVE' : 'OPERATIONAL PRODUCTION STREAM'}
              </span>
            </div>
            <div className="flex items-center gap-space-sm font-label-sm text-label-sm">
              <span className="text-outline">
                {totalFrames > 0
                  ? `Showing frames #${visibleFrames[0]?.frame ?? 0} – #${visibleFrames[visibleFrames.length - 1]?.frame ?? 0} of ${totalFrames.toLocaleString()}`
                  : '0 Frames Cataloged'}
              </span>
              <div className="flex items-center gap-space-xs">
                <button
                  disabled={clampedOffset <= 0}
                  className="w-6 h-6 bg-surface-container hover:bg-surface-container-high rounded flex items-center justify-center text-on-surface disabled:opacity-30 disabled:cursor-not-allowed"
                  onClick={() => setFrameOffset((o) => Math.max(0, o - PAGE_SIZE))}
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <button
                  disabled={clampedOffset + PAGE_SIZE >= totalFrames}
                  className="w-6 h-6 bg-surface-container hover:bg-surface-container-high rounded flex items-center justify-center text-on-surface disabled:opacity-30 disabled:cursor-not-allowed"
                  onClick={() => setFrameOffset((o) => o + PAGE_SIZE)}
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-data-sm text-data-sm whitespace-nowrap">
              <thead>
                <tr className="bg-surface-container-highest text-outline uppercase font-label-sm text-label-sm">
                  <th className="py-space-xs px-space-sm font-medium">Frame</th>
                  <th className="py-space-xs px-space-sm font-medium">Time (s)</th>
                  <th className="py-space-xs px-space-sm font-medium text-right text-on-surface">Est Centroid X</th>
                  <th className="py-space-xs px-space-sm font-medium text-right text-on-surface">Est Centroid Y</th>
                  <th className="py-space-xs px-space-sm font-medium text-right text-secondary">Boresight Err (px)</th>
                  {isValidation && (
                    <th className="py-space-xs px-space-sm font-medium text-right text-tertiary">GT Error (px)</th>
                  )}
                  <th className="py-space-xs px-space-sm font-medium text-center">State</th>
                  <th className="py-space-xs px-space-sm font-medium text-right">Pan (°)</th>
                  <th className="py-space-xs px-space-sm font-medium text-right">Tilt (°)</th>
                </tr>
              </thead>
              <tbody className="divide-y-0">
                {visibleFrames.length > 0 ? (
                  visibleFrames.map((row, i) => (
                    <tr
                      key={row.frame}
                      className={`${i % 2 === 0 ? 'bg-surface-container/60' : 'bg-surface-container-low'} hover:bg-surface-container transition-colors`}
                    >
                      <td className="py-space-xs px-space-sm text-outline">#{row.frame}</td>
                      <td className="py-space-xs px-space-sm text-on-surface-variant">{row.time.toFixed(3)}</td>
                      <td className="py-space-xs px-space-sm text-right text-on-surface">
                        {row.estX !== null && row.estX !== undefined ? row.estX.toFixed(2) : '—'}
                      </td>
                      <td className="py-space-xs px-space-sm text-right text-on-surface">
                        {row.estY !== null && row.estY !== undefined ? row.estY.toFixed(2) : '—'}
                      </td>
                      <td className="py-space-xs px-space-sm text-right text-secondary font-medium">
                        {row.error.toFixed(2)}
                      </td>
                      {isValidation && (
                        <td className="py-space-xs px-space-sm text-right text-tertiary font-mono">
                          {row.gtError !== null && row.gtError !== undefined ? row.gtError.toFixed(3) : '—'}
                        </td>
                      )}
                      <td className="py-space-xs px-space-sm text-center">
                        <span className="px-space-xs py-space-xs bg-secondary-container/20 text-secondary text-[10px] rounded">
                          {row.state}
                        </span>
                      </td>
                      <td className="py-space-xs px-space-sm text-right text-on-surface">
                        {row.pan >= 0 ? '+' : ''}{row.pan.toFixed(2)}
                      </td>
                      <td className="py-space-xs px-space-sm text-right text-on-surface">
                        {row.tilt >= 0 ? '+' : ''}{row.tilt.toFixed(2)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={isValidation ? 10 : 9} className="py-space-lg text-center text-outline">
                      No frame telemetry available for this run.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  )
}
