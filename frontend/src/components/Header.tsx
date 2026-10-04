import React, { useState, useEffect } from 'react'
import { User } from 'lucide-react'
import { useSanketStore } from '../store/useSanketStore'

export const Header: React.FC = () => {
  const status = useSanketStore((state) => state.status)
  const telemetry = useSanketStore((state) => state.telemetry)

  const [istTime, setIstTime] = useState('14:28:09.412')

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      // IST is UTC + 5 hours 30 minutes
      const istDate = new Date(now.getTime() + (5.5 * 60 * 60 * 1000))
      const hours = String(istDate.getUTCHours()).padStart(2, '0')
      const minutes = String(istDate.getUTCMinutes()).padStart(2, '0')
      const seconds = String(istDate.getUTCSeconds()).padStart(2, '0')
      const millis = String(istDate.getUTCMilliseconds()).padStart(3, '0')
      setIstTime(`${hours}:${minutes}:${seconds}.${millis}`)
    }
    updateTime()
    const timer = setInterval(updateTime, 100)
    return () => clearInterval(timer)
  }, [])

  // Format SIM MET: +HH:MM:SS
  const formatSimMet = (sec: number) => {
    const s = Math.max(0, Math.floor(sec))
    const hrs = String(Math.floor(s / 3600)).padStart(2, '0')
    const mins = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
    const secs = String(s % 60).padStart(2, '0')
    return `+${hrs}:${mins}:${secs}.05`
  }

  const isTrackingLocked =
    status.isRunning &&
    status.trackingEnabled !== false &&
    (telemetry.trackingState === 'TRACKING' ||
      telemetry.trackingState === 'ACQUIRING' ||
      (telemetry.boresightOffsetPx !== null && telemetry.boresightOffsetPx <= 10.0))

  const trackingErrorDisplay =
    status.isRunning
      ? telemetry.trackingErrorPx !== null && telemetry.trackingErrorPx !== undefined
        ? `${telemetry.trackingErrorPx.toFixed(3)} px`
        : telemetry.boresightOffsetPx !== null && telemetry.boresightOffsetPx !== undefined
        ? `${telemetry.boresightOffsetPx.toFixed(3)} px`
        : '--'
      : '--'

  const currentRate =
    status.backendFps > 0
      ? status.backendFps.toFixed(1)
      : telemetry.algorithmFps > 0
      ? telemetry.algorithmFps.toFixed(1)
      : '--'

  return (
    <header className="fixed top-0 left-60 right-0 h-10 md:h-14 bg-surface-container-low border-b border-outline-variant z-40 px-space-md flex items-center justify-between select-none">
      {/* Left Station & Target Telemetry Strip */}
      <div className="flex items-center gap-space-md shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="font-label-sm text-label-sm font-bold text-on-surface tracking-wider font-mono">
            OGS-BLR-0482
          </span>
          <span className="text-[10px] font-label-sm bg-surface-container-high text-tertiary px-1.5 py-0.5 rounded border border-outline-variant flex items-center gap-1 font-mono font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse" />
            AIR-GAP
          </span>
        </div>

        <span className="text-outline-variant">|</span>

        <div className="flex items-center gap-1.5 font-label-sm text-label-sm">
          <span className="text-outline font-mono text-[10px]">TARGET:</span>
          <span className="text-primary font-semibold font-mono text-[11px]">
            LEO-SAT-921A [850nm NIR]
          </span>
        </div>

        <span className="text-outline-variant hidden md:inline">|</span>

        <div className="hidden md:flex items-center gap-1 font-label-sm text-label-sm">
          <span className="text-outline font-mono text-[10px]">ARENA:</span>
          <span className="text-secondary font-mono text-[11px]">2000×2000 px</span>
        </div>
      </div>

      {/* Right Telemetry, Time, Lock Status & Profile */}
      <div className="flex items-center gap-space-md shrink-0">
        <div className="flex flex-col items-end font-mono">
          <div className="font-label-sm text-[11px] text-on-surface flex items-center gap-1">
            <span className="text-secondary font-bold text-[9px] bg-secondary/15 px-1 rounded">IST</span>
            <span className="font-bold">{istTime}</span>
          </div>
          <div className="font-label-sm text-[10px] text-outline flex items-center gap-1">
            <span className="text-[9px]">SIM MET</span>
            <span className="text-primary font-semibold">{formatSimMet(status.simTime)}</span>
          </div>
        </div>

        <div className="h-7 w-px bg-outline-variant" />

        <div className="flex flex-col items-start font-mono">
          <div className="font-label-sm text-[11px] text-tertiary flex items-center gap-1 font-semibold">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isTrackingLocked ? 'bg-tertiary' : 'bg-outline'
              }`}
            />
            <span>{isTrackingLocked ? `LOCKED ${trackingErrorDisplay}` : 'SCAN / ACQ'}</span>
          </div>
          <div className="font-label-sm text-[10px] text-outline-variant">
            LOOP: <span className="text-secondary font-bold">{currentRate} Hz</span>
          </div>
        </div>

        <div className="w-7 h-7 rounded-full bg-surface-container-high border border-outline-variant flex items-center justify-center text-primary cursor-pointer hover:bg-surface-bright transition-colors">
          <User className="w-4 h-4 text-primary" />
        </div>
      </div>
    </header>
  )
}

export default Header
