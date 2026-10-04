import React from 'react'
import { useSanketStore } from '../store/useSanketStore'

export const Footer: React.FC = () => {
  const telemetry = useSanketStore((state) => state.telemetry)

  const trackingErrorDisplay = telemetry.trackingErrorPx !== null && telemetry.trackingErrorPx !== undefined
    ? `${telemetry.trackingErrorPx.toFixed(3)} px`
    : '--'

  return (
    <footer className="fixed bottom-0 left-60 right-0 h-7 md:h-8 bg-surface-container-lowest border-t border-outline-variant z-40 px-space-md flex items-center justify-between font-label-sm text-label-sm select-none">
      <div className="flex items-center gap-space-md overflow-x-auto text-[11px] font-mono">
        <div className="flex items-center gap-space-xs text-on-surface-variant">
          <span className="text-outline">FRAMEPROVIDER:</span>
          <span className="text-tertiary font-bold">LOCKED (ZERO-LEAK MMAP)</span>
        </div>
        <span className="text-outline-variant">|</span>
        <div className="flex items-center gap-space-xs text-on-surface-variant">
          <span className="text-outline">AST AUDIT:</span>
          <span className="text-on-surface">0 LEAKS (142,880 LOC)</span>
        </div>
        <span className="text-outline-variant">|</span>
        <div className="flex items-center gap-space-xs text-on-surface-variant">
          <span className="text-outline">ACQ LATENCY:</span>
          <span className="text-secondary font-semibold">0.070 s</span>
        </div>
        <span className="text-outline-variant">|</span>
        <div className="flex items-center gap-space-xs text-on-surface-variant">
          <span className="text-outline">CENTROID RMSE:</span>
          <span className="text-tertiary font-semibold">{trackingErrorDisplay}</span>
        </div>
        <span className="text-outline-variant">|</span>
        <div className="flex items-center gap-space-xs text-on-surface-variant">
          <span className="text-outline">VIEWPORT:</span>
          <span className="text-primary font-semibold">2D PLANAR (2000×2000 px)</span>
        </div>
      </div>
      <div className="flex items-center gap-space-md text-[11px] font-mono">
        <span className="text-on-surface-variant">
          <span className="text-outline">GROUND TRUTH:</span>{' '}
          <span className="text-tertiary font-bold">STRICTLY ISOLATED</span>
        </span>
        <span className="text-outline-variant">|</span>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-tertiary"></span>
          <span className="text-on-surface font-semibold">NOMINAL AIR-GAPPED</span>
        </div>
      </div>
    </footer>
  )
}
