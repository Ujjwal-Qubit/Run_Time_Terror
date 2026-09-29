import React, { useState, useEffect } from 'react'
import {
  Layers,
  Play,
  Pause,
  Square,
  Redo,
  User,
} from 'lucide-react'
import { useLumiTrackStore } from '../store/useLumiTrackStore'
import { bridgeService } from '../services/bridgeService'

export const Header: React.FC = () => {
  const status = useLumiTrackStore((state) => state.status)
  const telemetry = useLumiTrackStore((state) => state.telemetry)

  const [utcTime, setUtcTime] = useState('')

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      const hours = String(now.getUTCHours()).padStart(2, '0')
      const minutes = String(now.getUTCMinutes()).padStart(2, '0')
      const seconds = String(now.getUTCSeconds()).padStart(2, '0')
      const millis = String(now.getUTCMilliseconds()).padStart(3, '0')
      setUtcTime(`${hours}:${minutes}:${seconds}.${millis}`)
    }
    updateTime()
    const timer = setInterval(updateTime, 100)
    return () => clearInterval(timer)
  }, [])

  const handleStart = () => {
    bridgeService.run()
  }

  const handlePauseResume = () => {
    if (status.isPaused) {
      bridgeService.resume()
    } else {
      bridgeService.pause()
    }
  }

  const handleStop = () => {
    bridgeService.stop()
  }

  const handleStep = () => {
    bridgeService.step()
  }

  const handleAlgoChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    bridgeService.selectAlgorithm(e.target.value)
  }

  const handleScenarioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    bridgeService.selectScenario(e.target.value)
  }

  // Format SIM MET: +HH:MM:SS
  const formatSimMet = (sec: number) => {
    const s = Math.max(0, Math.floor(sec))
    const hrs = String(Math.floor(s / 3600)).padStart(2, '0')
    const mins = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
    const secs = String(s % 60).padStart(2, '0')
    return `+${hrs}:${mins}:${secs}`
  }

  const isTrackingLocked =
    telemetry.trackingState === 'TRACKING' ||
    telemetry.trackingState === 'CONVERGING' ||
    (telemetry.trackingErrorPx !== null && telemetry.trackingErrorPx <= 10.0)

  return (
    <header className="fixed top-0 left-60 right-0 h-10 bg-surface-container-low border-b border-outline-variant/40 z-40 px-space-md flex items-center justify-between select-none">
      {/* Left: Active Scenario & Algorithm Selection */}
      <div className="flex items-center gap-space-md">
        {/* Scenario Pill */}
        <div className="flex items-center gap-space-xs px-space-sm py-space-xs bg-surface-container rounded border border-outline-variant/30">
          <Layers className="text-primary w-3.5 h-3.5" />
          <span className="font-label-sm text-label-sm text-outline uppercase mr-0.5">SCN:</span>
          <select
            value={status.activeScenario}
            onChange={handleScenarioChange}
            disabled={status.isRunning}
            className="bg-transparent font-data-sm text-data-sm text-primary focus:outline-none cursor-pointer disabled:opacity-75 max-w-[210px] truncate"
          >
            {status.availableScenarios.length > 0 ? (
              status.availableScenarios.map((scn) => (
                <option key={scn} value={scn} className="bg-surface-container-low text-on-surface">
                  {scn}
                </option>
              ))
            ) : (
              <option value="04_combined_stress_high.json" className="bg-surface-container-low text-on-surface">
                04_combined_stress_high.json
              </option>
            )}
          </select>
          <span className="font-data-sm text-data-sm text-outline hidden sm:inline">[LEO Dynamic]</span>
        </div>

        {/* Algorithm Pill */}
        <div className="flex items-center gap-space-xs px-space-sm py-space-xs bg-surface-container-highest rounded border border-outline-variant/30">
          <select
            value={status.activeAlgorithm}
            onChange={handleAlgoChange}
            disabled={status.isRunning}
            className="bg-transparent font-data-sm text-data-sm text-on-surface-variant focus:outline-none cursor-pointer disabled:opacity-75 max-w-[240px] truncate"
          >
            {status.availableAlgorithms.length > 0 ? (
              status.availableAlgorithms.map((algo) => (
                <option key={algo} value={algo} className="bg-surface-container-low text-on-surface">
                  {algo}
                </option>
              ))
            ) : (
              <option value="Subpixel_CoG + Anti-Windup PI v2.4.8" className="bg-surface-container-low text-on-surface">
                Subpixel_CoG + Anti-Windup PI v2.4.8
              </option>
            )}
          </select>
        </div>
      </div>

      {/* Center: Playback Transport & Loop Rate */}
      <div className="flex items-center gap-space-xs">
        <div className="flex items-center bg-surface-container rounded border border-outline-variant/40 p-space-xs">
          <button
            type="button"
            onClick={handleStart}
            disabled={status.isRunning && !status.isPaused}
            className="flex items-center gap-space-xs px-space-sm py-space-xs bg-secondary-container text-on-secondary-container hover:bg-secondary hover:text-on-secondary disabled:opacity-40 rounded font-label-md text-label-md font-medium transition-colors"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>RUN</span>
          </button>
          <button
            type="button"
            onClick={handlePauseResume}
            disabled={!status.isRunning}
            className="flex items-center gap-space-xs px-space-sm py-space-xs text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface disabled:opacity-40 rounded font-label-md text-label-md transition-colors"
          >
            <Pause className="w-3.5 h-3.5 fill-current" />
            <span>{status.isPaused ? 'RESUME' : 'PAUSE'}</span>
          </button>
          <button
            type="button"
            onClick={handleStop}
            disabled={!status.isRunning}
            className="flex items-center gap-space-xs px-space-sm py-space-xs text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface disabled:opacity-40 rounded font-label-md text-label-md transition-colors"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>STOP</span>
          </button>
          <button
            type="button"
            onClick={handleStep}
            className="flex items-center gap-space-xs px-space-sm py-space-xs text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface rounded font-label-md text-label-md transition-colors"
          >
            <Redo className="w-3.5 h-3.5" />
            <span>+1 FR STEP</span>
          </button>
        </div>

        {/* Live Loop Rate Badge */}
        <div className="px-space-sm py-space-xs bg-surface-container rounded border border-outline-variant/30 flex items-center gap-space-xs">
          <span className="font-label-sm text-label-sm text-outline">RATE:</span>
          <span className="font-data-sm text-data-sm text-secondary font-medium">
            {(status.backendFps > 0 ? status.backendFps : telemetry.algorithmFps > 0 ? telemetry.algorithmFps : 0.0).toFixed(1)} Hz
          </span>
        </div>

        {/* Tracking ON/OFF Toggle */}
        <button
          type="button"
          onClick={() => {
            const next = !(status.trackingEnabled ?? true)
            useLumiTrackStore.getState().setStatus({ ...status, trackingEnabled: next })
            bridgeService.setTrackingEnabled(next)
          }}
          className={`flex items-center gap-space-xs px-space-sm py-space-xs rounded border font-label-md text-label-md transition-colors ${
            status.trackingEnabled !== false
              ? 'bg-secondary/15 text-secondary border-secondary/40 hover:bg-secondary/25'
              : 'bg-surface-container-high text-outline border-outline-variant/40 hover:text-on-surface'
          }`}
          title="Toggle Target Tracking Pipeline"
        >
          <span className={`w-2 h-2 rounded-full ${status.trackingEnabled !== false ? 'bg-secondary animate-pulse' : 'bg-outline'}`} />
          <span>TRACK: {status.trackingEnabled !== false ? 'ON' : 'OFF'}</span>
        </button>

        {/* PTZ ON/OFF Toggle */}
        <button
          type="button"
          onClick={() => {
            const next = !(status.ptzEnabled ?? true)
            useLumiTrackStore.getState().setStatus({ ...status, ptzEnabled: next })
            bridgeService.setPtzEnabled(next)
          }}
          className={`flex items-center gap-space-xs px-space-sm py-space-xs rounded border font-label-md text-label-md transition-colors ${
            status.ptzEnabled !== false
              ? 'bg-primary/15 text-primary border-primary/40 hover:bg-primary/25'
              : 'bg-surface-container-high text-outline border-outline-variant/40 hover:text-on-surface'
          }`}
          title="Toggle Pan-Tilt-Zoom Pedestal Actuation"
        >
          <span className={`w-2 h-2 rounded-full ${status.ptzEnabled !== false ? 'bg-primary animate-pulse' : 'bg-outline'}`} />
          <span>PTZ: {status.ptzEnabled !== false ? 'ON' : 'OFF'}</span>
        </button>
      </div>

      {/* Right: Telemetry Time, MET, Spec Status Badge, Avatar */}
      <div className="flex items-center gap-space-md">
        <div className="flex items-center gap-space-sm font-data-sm text-data-sm">
          <div className="flex items-center gap-space-xs">
            <span className="text-outline">UTC</span>
            <span className="text-on-surface">{utcTime || '—'}</span>
          </div>
          <span className="text-outline-variant">|</span>
          <div className="flex items-center gap-space-xs">
            <span className="text-outline">SIM MET</span>
            <span className="text-primary">{formatSimMet(status.simTime)}</span>
          </div>
        </div>

        {/* Lock Spec Status Badge */}
        <div
          className={`flex items-center gap-space-xs px-space-sm py-space-xs rounded border ${
            isTrackingLocked
              ? 'bg-secondary/15 text-secondary border-secondary/40'
              : 'bg-tertiary/15 text-tertiary border-tertiary/40'
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isTrackingLocked ? 'bg-secondary animate-pulse' : 'bg-tertiary'
            }`}
          />
          <span className="font-label-sm text-label-sm font-medium tracking-wide">
            {isTrackingLocked ? 'LOCKED (100% SPEC)' : 'ACQUIRING / SCAN'}
          </span>
        </div>

        {/* Profile Avatar */}
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
          <User className="text-on-primary w-4 h-4" />
        </div>
      </div>
    </header>
  )
}
