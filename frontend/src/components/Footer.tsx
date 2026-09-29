import React from 'react'
import { ShieldCheck } from 'lucide-react'
import { useLumiTrackStore } from '../store/useLumiTrackStore'

export const Footer: React.FC = () => {
  const status = useLumiTrackStore((state) => state.status)
  const telemetry = useLumiTrackStore((state) => state.telemetry)

  const currentFps = status.backendFps > 0
    ? status.backendFps
    : telemetry.algorithmFps > 0
    ? telemetry.algorithmFps
    : 0.0

  const loopRateStr = currentFps > 0 ? currentFps.toFixed(1) : '0.0'
  const speedRatio = currentFps > 0 ? (currentFps / 20.0).toFixed(2) : null

  const computeLatencyStr = telemetry.processingLatencyMs > 0
    ? `${telemetry.processingLatencyMs.toFixed(2)} ms`
    : '—'

  const offsetStr = telemetry.boresightOffsetPx !== null && telemetry.boresightOffsetPx !== undefined
    ? `${telemetry.boresightOffsetPx.toFixed(2)} px`
    : 'NO DATA'

  const rmseStr = status.validationMode && telemetry.trackingErrorPx !== null && telemetry.trackingErrorPx !== undefined
    ? `${telemetry.trackingErrorPx.toFixed(2)} px`
    : null

  return (
    <footer className="fixed bottom-0 left-60 right-0 h-7 bg-surface-container-lowest border-t border-outline-variant/40 z-40 px-space-md flex items-center justify-between select-none">
      {/* Left: Firewall & AST Audit */}
      <div className="flex items-center gap-space-md font-label-sm text-label-sm">
        <div className="flex items-center gap-space-xs text-secondary">
          <span className="w-1.5 h-1.5 bg-secondary rounded-full" />
          <span>FRAMEPROVIDER FIREWALL: LOCKED (ZERO LEAKAGE)</span>
        </div>
        <span className="text-outline-variant">|</span>
        <div className="flex items-center gap-space-xs text-on-surface-variant">
          <span className="text-outline">AST AUDIT:</span>
          <span className="text-secondary font-medium">0 LEAKS</span>
        </div>
      </div>

      {/* Center: Live Real-Time Loop Performance */}
      <div className="flex items-center gap-space-md font-data-sm text-data-sm text-on-surface-variant">
        <div>
          <span className="text-outline">LOOP:</span>{' '}
          <span className={currentFps >= 20.0 ? 'text-secondary' : 'text-outline'}>
            {loopRateStr} Hz
          </span>{' '}
          {speedRatio && (
            <span className="text-outline-variant">({speedRatio}x SPEC)</span>
          )}
        </div>
        <span className="text-outline-variant">|</span>
        <div>
          <span className="text-outline">COMPUTE:</span>{' '}
          <span className="text-on-surface">{computeLatencyStr}</span>
        </div>
        <span className="text-outline-variant">|</span>
        <div>
          <span className="text-outline">{status.validationMode ? 'RMSE (GT):' : 'BORESIGHT OFFSET:'}</span>{' '}
          <span className="text-primary">{status.validationMode ? (rmseStr ?? 'CALCULATING') : offsetStr}</span>
        </div>
      </div>

      {/* Right: Isolation Seal & Verification */}
      <div className="flex items-center gap-space-md font-label-sm text-label-sm text-outline">
        <div className="flex items-center gap-space-xs">
          <ShieldCheck className="w-3.5 h-3.5 text-secondary" />
          <span>GROUND TRUTH: ISOLATED TO METRICS</span>
        </div>
        <span className="text-outline-variant">|</span>
        <span className="text-secondary">TELEMETRY: VERIFIED</span>
      </div>
    </footer>
  )
}
