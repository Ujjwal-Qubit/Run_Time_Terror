import React from 'react'
import { Activity } from 'lucide-react'
import { useSanketStore } from '../../store/useSanketStore'

interface DeveloperBottomHorizonProps {
  radialErr: number
  loopRate: string
  frameNum: number
  centroidRmse: string
  acqLatency: string
  targetLossRate: string
  errorHistory?: number[]
}

export const DeveloperBottomHorizon: React.FC<DeveloperBottomHorizonProps> = ({
  radialErr,
  loopRate,
  frameNum,
  centroidRmse,
  acqLatency,
  targetLossRate,
}) => {
  const status = useSanketStore((s) => s.status)

  return (
    <div className="px-space-sm pb-14 pt-space-xs w-full select-none">
      <div className="bg-surface-container-low rounded p-space-sm shadow-md border border-outline-variant/40">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-sm pb-space-xs border-b border-outline-variant/30 font-mono text-[10px]">
          <div className="flex items-center gap-space-md">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-tertiary" />
              <span className="font-headline-sm text-headline-sm font-bold tracking-tight text-on-surface font-sans">
                PERFORMANCE HORIZON
              </span>
            </div>
            <div className="font-label-sm text-[10px] text-tertiary bg-surface-container-high px-2 py-0.5 rounded font-mono font-semibold">
              {status.isRunning ? 'CLOSED_LOOP ACTIVE' : 'SYSTEM STANDBY / READY'}
            </div>
          </div>

          <div className="flex items-center gap-space-sm flex-wrap text-outline">
            <span>SERVO: <strong className="text-secondary">1000 Hz HIL</strong></span>
            <span>•</span>
            <span>FIREWALL: <strong className="text-tertiary">GT STRIPPED</strong></span>
            <span>•</span>
            <span>LATENCY: <strong className="text-on-surface">{acqLatency} s</strong></span>
            <span>•</span>
            <span>SPEC: <strong className="text-tertiary">PS-26169 COMPLIANT</strong></span>
          </div>
        </div>

        {/* Dynamic KPIs 1-6 (Item 1.e, 1.f, 1.u) */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-gutter pt-space-xs">
          {/* KPI 1 */}
          <div className="bg-surface-container-lowest p-space-xs rounded border border-outline-variant/20">
            <div className="font-label-sm text-[10px] text-outline truncate uppercase">
              01. Frame Buffer
            </div>
            <div className="font-label-lg text-label-lg font-bold text-on-surface font-mono mt-0.5">
              {String(frameNum).padStart(6, '0')}
            </div>
            <div className="flex items-center justify-between text-[10px] font-label-sm mt-0.5">
              <span className="text-outline">/ 3600 frames</span>
              <span className="text-secondary font-mono font-semibold">
                {((frameNum / 3600) * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* KPI 2 */}
          <div className="bg-surface-container-lowest p-space-xs rounded border border-outline-variant/20">
            <div className="font-label-sm text-[10px] text-outline truncate uppercase">
              02. Loop Rate
            </div>
            <div className="font-label-lg text-label-lg font-bold text-tertiary font-mono mt-0.5">
              {loopRate} Hz
            </div>
            <div className="flex items-center justify-between text-[10px] font-label-sm mt-0.5">
              <span className="text-outline">Spec: ≥20 Hz</span>
              <span className={`font-mono font-semibold ${parseFloat(loopRate) >= 20.0 ? 'text-tertiary' : 'text-outline'}`}>
                {parseFloat(loopRate) >= 20.0 ? 'PASS' : status.isRunning ? 'WARN' : 'READY'}
              </span>
            </div>
          </div>

          {/* KPI 3 */}
          <div className="bg-surface-container-lowest p-space-xs rounded border border-outline-variant/20">
            <div className="font-label-sm text-[10px] text-outline truncate uppercase">
              03. Tracking Error
            </div>
            <div className={`font-label-lg text-label-lg font-bold font-mono mt-0.5 ${radialErr <= 10.0 ? 'text-tertiary' : 'text-error'}`}>
              {radialErr.toFixed(2)} px
            </div>
            <div className="flex items-center justify-between text-[10px] font-label-sm mt-0.5">
              <span className="text-outline">Spec: ≤10.0 px</span>
              <span className={`font-mono font-semibold ${radialErr <= 10.0 ? 'text-tertiary' : 'text-error'}`}>
                {radialErr <= 10.0 ? 'PASS' : 'FAIL'}
              </span>
            </div>
          </div>

          {/* KPI 4 */}
          <div className="bg-surface-container-lowest p-space-xs rounded border border-outline-variant/20">
            <div className="font-label-sm text-[10px] text-outline truncate uppercase">
              04. Centroid RMSE
            </div>
            <div className="font-label-lg text-label-lg font-bold text-secondary font-mono mt-0.5">
              {centroidRmse} px
            </div>
            <div className="flex items-center justify-between text-[10px] font-label-sm mt-0.5">
              <span className="text-outline">Sub-pixel</span>
              <span className="text-secondary font-semibold font-mono">
                {parseFloat(centroidRmse) < 1.0 ? 'VERIFIED' : 'ACTIVE'}
              </span>
            </div>
          </div>

          {/* KPI 5 */}
          <div className="bg-surface-container-lowest p-space-xs rounded border border-outline-variant/20">
            <div className="font-label-sm text-[10px] text-outline truncate uppercase">
              05. Acq Latency
            </div>
            <div className="font-label-lg text-label-lg font-bold text-tertiary font-mono mt-0.5">
              {acqLatency} s
            </div>
            <div className="flex items-center justify-between text-[10px] font-label-sm mt-0.5">
              <span className="text-outline">Spec: ≤2.00 s</span>
              <span className={`font-mono font-semibold ${parseFloat(acqLatency) <= 2.0 ? 'text-tertiary' : 'text-error'}`}>
                {parseFloat(acqLatency) <= 2.0 ? 'PASS' : 'FAIL'}
              </span>
            </div>
          </div>

          {/* KPI 6 */}
          <div className="bg-surface-container-lowest p-space-xs rounded border border-outline-variant/20">
            <div className="font-label-sm text-[10px] text-outline truncate uppercase">
              06. Target Loss Rate
            </div>
            <div className={`font-label-lg text-label-lg font-bold font-mono mt-0.5 ${parseFloat(targetLossRate) < 5.0 ? 'text-tertiary' : 'text-error'}`}>
              {targetLossRate}%
            </div>
            <div className="flex items-center justify-between text-[10px] font-label-sm mt-0.5">
              <span className="text-outline">Spec: &lt;5.0%</span>
              <span className={`font-mono font-semibold ${parseFloat(targetLossRate) < 5.0 ? 'text-tertiary' : 'text-error'}`}>
                {parseFloat(targetLossRate) < 5.0 ? 'PASS' : 'FAIL'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
