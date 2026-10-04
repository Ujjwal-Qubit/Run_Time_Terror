import React from 'react'
import { Activity } from 'lucide-react'

interface TrackingErrorChartCardProps {
  errorHistory: number[]
  radialErr: number
  centroidRmse: string
}

export const TrackingErrorChartCard: React.FC<TrackingErrorChartCardProps> = ({
  errorHistory,
  radialErr,
  centroidRmse,
}) => {
  // Construct dynamic SVG waveform path from error history
  const points = errorHistory.length > 0 ? errorHistory : [0]
  const maxIdx = Math.max(1, points.length - 1)
  const pathD = points
    .map((val, idx) => {
      const x = (idx / maxIdx) * 600
      // Scale error: 0 px baseline is at y=60, 10 px ceiling is at y=16
      const clamped = Math.max(0, Math.min(14, val))
      const y = 60 - (clamped / 10.0) * 44
      return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  const fillD = `${pathD} L 600,72 L 0,72 Z`
  const lastPointY =
    points.length > 0
      ? 60 - (Math.max(0, Math.min(14, points[points.length - 1])) / 10.0) * 44
      : 60

  return (
    <div className="bg-surface-container-low rounded p-space-sm shadow-sm flex flex-col justify-between border border-outline-variant/40 select-none">
      <div className="flex items-center justify-between pb-space-xs mb-space-xs border-b border-outline-variant/30">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-tertiary" />
          <span className="font-label-sm text-label-sm font-semibold uppercase tracking-wider text-on-surface">
            Real-Time Tracking Error &amp; Jitter Dynamics
          </span>
          <span className="text-[10px] font-mono text-outline">
            (LAST 40 FRAMES)
          </span>
        </div>
        <div className="flex items-center gap-space-md font-mono text-[10px]">
          <span className="text-outline">
            SPEC CEILING: <strong className="text-error font-mono">10.0 px</strong>
          </span>
          <span className="text-outline">|</span>
          <span className="text-outline">
            CURRENT:{' '}
            <strong
              className={
                radialErr > 10.0
                  ? 'text-error font-mono font-bold'
                  : 'text-tertiary font-mono font-bold'
              }
            >
              {radialErr.toFixed(3)} px
            </strong>
          </span>
          <span className="text-outline">|</span>
          <span className="text-secondary font-semibold">
            RMSE: {centroidRmse} px
          </span>
        </div>
      </div>

      {/* The Waveform Canvas / SVG */}
      <div className="h-20 w-full bg-surface-container-lowest rounded relative overflow-hidden flex items-center px-2 py-1 border border-outline-variant/30">
        <svg
          className="w-full h-full"
          preserveAspectRatio="none"
          viewBox="0 0 600 72"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Horizontal Reference Lines */}
          <line
            x1="0"
            y1="16"
            x2="600"
            y2="16"
            stroke="#f43f5e"
            strokeWidth="1"
            strokeDasharray="4,4"
            opacity="0.85"
          />
          <line
            x1="0"
            y1="38"
            x2="600"
            y2="38"
            stroke="#253241"
            strokeWidth="0.75"
            strokeDasharray="2,4"
          />
          <line
            x1="0"
            y1="60"
            x2="600"
            y2="60"
            stroke="#1c242e"
            strokeWidth="0.75"
          />

          {/* Grid Vertical Lines */}
          {[100, 200, 300, 400, 500].map((gx) => (
            <line
              key={gx}
              x1={gx}
              y1="0"
              x2={gx}
              y2="72"
              stroke="#161f29"
              strokeWidth="0.6"
              strokeDasharray="2,4"
            />
          ))}

          {/* Dynamic Waveform Path */}
          <path
            d={pathD}
            fill="none"
            stroke={radialErr > 10.0 ? '#f43f5e' : '#4edea3'}
            strokeWidth="2"
            strokeLinecap="round"
          />
          <path
            d={fillD}
            fill={radialErr > 10.0 ? '#f43f5e' : '#4edea3'}
            fillOpacity="0.12"
          />
          <circle
            cx="600"
            cy={lastPointY}
            r="3.5"
            fill={radialErr > 10.0 ? '#f43f5e' : '#4edea3'}
          />
        </svg>

        <span className="absolute top-1 left-3 font-mono text-[9px] text-error font-semibold">
          -- 10.0 px PS-26169 SPEC CEILING
        </span>
        <span className="absolute top-1 right-3 font-mono text-[9px] text-outline">
          5.0 px NOMINAL
        </span>
        <span className="absolute bottom-1 left-3 font-mono text-[9px] text-outline">
          0.0 px (BORESIGHT CENTER)
        </span>
        <span className="absolute bottom-1 right-3 font-mono text-[9px] text-tertiary font-bold">
          {radialErr.toFixed(2)} px REALTIME
        </span>
      </div>

      <div className="mt-space-xs pt-space-xs flex items-center justify-between font-mono text-[10px] text-on-surface-variant">
        <span>
          CONVERGENCE:{' '}
          <strong className="text-tertiary">
            {radialErr <= 1.0
              ? 'SUB-PIXEL (ACQUIRED)'
              : radialErr <= 10.0
              ? 'IN-SPEC TRACKING'
              : 'OUT-OF-BOUNDS'}
          </strong>
        </span>
        <span>
          FILTER:{' '}
          <strong className="text-secondary font-mono">
            EXPONENTIAL MA (α=0.15)
          </strong>
        </span>
        <span>
          SAMPLING:{' '}
          <strong className="text-on-surface font-mono">
            30 Hz SYNCHRONOUS
          </strong>
        </span>
      </div>
    </div>
  )
}

export default TrackingErrorChartCard
