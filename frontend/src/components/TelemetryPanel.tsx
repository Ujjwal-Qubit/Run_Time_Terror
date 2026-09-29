import React from 'react'
import {
  Gauge,
  Target,
  Clock,
  Compass,
  Zap,
  Activity,
  Layers,
} from 'lucide-react'
import { useLumiTrackStore } from '../store/useLumiTrackStore'

export const TelemetryPanel: React.FC = () => {
  const telemetry = useLumiTrackStore((state) => state.telemetry)
  const status = useLumiTrackStore((state) => state.status)
  const browserPerf = useLumiTrackStore((state) => state.browserPerf)

  const trackingState = telemetry.trackingState
  const isLocked = trackingState === 'TRACKING'

  return (
    <div className="w-80 bg-workstation-900 border-l border-workstation-700/60 p-4 flex flex-col gap-3 shrink-0 overflow-y-auto select-none">
      {/* Panel Title */}
      <div className="flex items-center justify-between pb-2 border-b border-workstation-700/50">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-bold text-gray-200 uppercase tracking-wider">
            Live Telemetry HUD
          </span>
        </div>
        <span className="text-[10px] font-mono text-gray-400">
          Sync: 25Hz
        </span>
      </div>

      {/* Grid of Key Telemetry Cards */}
      <div className="grid grid-cols-2 gap-2.5">
        {/* Card 1: Algorithm FPS */}
        <div className="bg-workstation-850 p-2.5 rounded-lg border border-workstation-700 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400 text-[10px] uppercase font-semibold">
            <span>Algo Speed</span>
            <Gauge className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="mt-1 font-mono">
            <span className="text-xl font-bold text-white">
              {telemetry.algorithmFps > 0 ? telemetry.algorithmFps.toFixed(1) : '0.0'}
            </span>
            <span className="text-[10px] text-gray-400 ml-1">FPS</span>
          </div>
          <div className="text-[10px] text-gray-400 mt-0.5">
            Backend: {status.backendFps.toFixed(0)} FPS
          </div>
        </div>

        {/* Card 2: Latency */}
        <div className="bg-workstation-850 p-2.5 rounded-lg border border-workstation-700 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400 text-[10px] uppercase font-semibold">
            <span>Latency</span>
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="mt-1 font-mono">
            <span className="text-xl font-bold text-cyan-300">
              {telemetry.processingLatencyMs > 0
                ? telemetry.processingLatencyMs.toFixed(1)
                : '0.0'}
            </span>
            <span className="text-[10px] text-gray-400 ml-1">ms</span>
          </div>
          <div className="text-[10px] text-gray-400 mt-0.5">
            Budget: &lt;50ms
          </div>
        </div>

        {/* Card 3: Target Centroid */}
        <div className="bg-workstation-850 p-2.5 rounded-lg border border-workstation-700 col-span-2">
          <div className="flex items-center justify-between text-gray-400 text-[10px] uppercase font-semibold mb-1">
            <span>Estimated Centroid</span>
            <Target className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="grid grid-cols-2 gap-2 font-mono">
            <div className="bg-workstation-900/80 px-2 py-1 rounded border border-workstation-700/60">
              <span className="text-gray-400 text-[10px]">X: </span>
              <span className="text-white font-bold text-sm">
                {telemetry.centroid.x !== null ? telemetry.centroid.x.toFixed(2) : '---'}
              </span>
              <span className="text-gray-400 text-[10px] ml-1">px</span>
            </div>
            <div className="bg-workstation-900/80 px-2 py-1 rounded border border-workstation-700/60">
              <span className="text-gray-400 text-[10px]">Y: </span>
              <span className="text-white font-bold text-sm">
                {telemetry.centroid.y !== null ? telemetry.centroid.y.toFixed(2) : '---'}
              </span>
              <span className="text-gray-400 text-[10px] ml-1">px</span>
            </div>
          </div>
        </div>

        {/* Card 4: Tracking Error (Estimated / Offset) */}
        <div className="bg-workstation-850 p-2.5 rounded-lg border border-workstation-700 col-span-2">
          <div className="flex items-center justify-between text-gray-400 text-[10px] uppercase font-semibold mb-1">
            <span>Pointing Error (Offset)</span>
            <Zap className={`w-3.5 h-3.5 ${isLocked ? 'text-emerald-400' : 'text-amber-400'}`} />
          </div>
          <div className="flex items-center justify-between">
            <div className="font-mono">
              <span className="text-xl font-bold text-white">
                {telemetry.centroid.x !== null && telemetry.centroid.y !== null
                  ? Math.hypot(
                      telemetry.centroid.x - telemetry.cameraWidth / 2,
                      telemetry.centroid.y - telemetry.cameraHeight / 2
                    ).toFixed(2)
                  : 'N/A'}
              </span>
              <span className="text-[10px] text-gray-400 ml-1">px radial</span>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-gray-400">Lock Conf:</div>
              <div className="text-xs font-mono font-bold text-emerald-400">
                {(telemetry.confidence * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>

        {/* Card 5: PTZ Gimbal Angles */}
        <div className="bg-workstation-850 p-2.5 rounded-lg border border-workstation-700 col-span-2">
          <div className="flex items-center justify-between text-gray-400 text-[10px] uppercase font-semibold mb-1">
            <span>PTZ Gimbal Orientation</span>
            <Compass className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="grid grid-cols-2 gap-2 font-mono">
            <div className="bg-workstation-900/80 px-2.5 py-1.5 rounded border border-workstation-700/60">
              <div className="text-[10px] text-gray-400">Pan (Azimuth)</div>
              <div className="text-sm font-bold text-blue-300">
                {telemetry.panAngleDeg.toFixed(3)}°
              </div>
            </div>
            <div className="bg-workstation-900/80 px-2.5 py-1.5 rounded border border-workstation-700/60">
              <div className="text-[10px] text-gray-400">Tilt (Elevation)</div>
              <div className="text-sm font-bold text-blue-300">
                {telemetry.tiltAngleDeg.toFixed(3)}°
              </div>
            </div>
          </div>
          <div className="text-[10px] text-gray-400 mt-1 flex justify-between">
            <span>Actuation Slew:</span>
            <span className="text-emerald-400 font-semibold">
              {status.ptzEnabled ? 'CLOSED LOOP' : 'OPEN LOOP (OFF)'}
            </span>
          </div>
        </div>
      </div>

      {/* IPC Bridge Performance Diagnostics Card */}
      <div className="mt-auto bg-workstation-850/70 p-2.5 rounded-lg border border-workstation-700/50 text-[11px]">
        <div className="flex items-center gap-1.5 text-gray-300 font-semibold mb-1.5">
          <Layers className="w-3.5 h-3.5 text-purple-400" />
          <span>QtWebChannel IPC Health</span>
        </div>
        <div className="space-y-1 text-gray-400 font-mono text-[10px]">
          <div className="flex justify-between">
            <span>Frames Received:</span>
            <span className="text-gray-200">{status.currentFrame}</span>
          </div>
          <div className="flex justify-between">
            <span>Telemetry Rate:</span>
            <span className="text-emerald-400">~{browserPerf.telemetryReceiveHz.toFixed(1)} Hz</span>
          </div>
          <div className="flex justify-between">
            <span>Frame Format:</span>
            <span className="text-gray-200">JPEG Base64 (640x480)</span>
          </div>
          <div className="flex justify-between">
            <span>Airgap Security:</span>
            <span className="text-emerald-400">No Network Sockets</span>
          </div>
        </div>
      </div>
    </div>
  )
}
