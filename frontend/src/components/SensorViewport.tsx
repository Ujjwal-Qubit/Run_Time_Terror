import React, { useRef, useEffect } from 'react'
import { Eye, Crosshair } from 'lucide-react'
import { useLumiTrackStore } from '../store/useLumiTrackStore'
import { perfService } from '../services/perfService'
import { bridgeService } from '../services/bridgeService'

export const SensorViewport: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const latestFrame = useLumiTrackStore((state) => state.latestFrame)
  const telemetry = useLumiTrackStore((state) => state.telemetry)
  const isConnected = useLumiTrackStore((state) => state.isConnected)
  const status = useLumiTrackStore((state) => state.status)

  // Track FPS and render performance locally
  const renderCountRef = useRef(0)
  const lastFpsTimeRef = useRef(performance.now())
  const renderedFpsRef = useRef(0)
  const firstFrameReportedRef = useRef(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Calculate local client FPS
    renderCountRef.current++
    const now = performance.now()
    if (now - lastFpsTimeRef.current >= 1000) {
      renderedFpsRef.current = Math.round(
        (renderCountRef.current * 1000) / (now - lastFpsTimeRef.current)
      )
      renderCountRef.current = 0
      lastFpsTimeRef.current = now
    }

    // If we have a frame image
    if (latestFrame && latestFrame.data) {
      const decodeStartTime = performance.now()
      const img = new Image()
      img.src = latestFrame.data.startsWith('data:')
        ? latestFrame.data
        : `data:image/${latestFrame.format};base64,${latestFrame.data}`

      img.onload = () => {
        const decodeEndTime = performance.now()
        const decodeMs = decodeEndTime - decodeStartTime
        const drawStartTime = performance.now()

        // 1. Draw raw sensor frame (640x480)
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

        // 2. Draw Boresight / Reticle (Camera Center at 320, 240)
        const cx = canvas.width / 2
        const cy = canvas.height / 2
        ctx.strokeStyle = 'rgba(6, 182, 212, 0.45)' // Cyan subtle
        ctx.lineWidth = 1

        // Center crosshair lines
        ctx.beginPath()
        ctx.moveTo(cx - 24, cy)
        ctx.lineTo(cx - 6, cy)
        ctx.moveTo(cx + 6, cy)
        ctx.lineTo(cx + 24, cy)
        ctx.moveTo(cx, cy - 24)
        ctx.lineTo(cx, cy - 6)
        ctx.moveTo(cx, cy + 6)
        ctx.lineTo(cx, cy + 24)
        ctx.stroke()

        // Center reticle ring
        ctx.beginPath()
        ctx.arc(cx, cy, 12, 0, 2 * Math.PI)
        ctx.stroke()

        // 3. Draw Region of Interest (ROI) if active
        if (telemetry.roi) {
          ctx.strokeStyle = 'rgba(245, 158, 11, 0.7)' // Amber
          ctx.lineWidth = 1.5
          ctx.setLineDash([4, 2])
          ctx.strokeRect(
            telemetry.roi.x,
            telemetry.roi.y,
            telemetry.roi.width,
            telemetry.roi.height
          )
          ctx.setLineDash([])

          // ROI Label
          ctx.fillStyle = 'rgba(245, 158, 11, 0.9)'
          ctx.font = '10px JetBrains Mono, monospace'
          ctx.fillText('ROI', telemetry.roi.x + 2, telemetry.roi.y - 3)
        }

        // 4. Draw Estimated Target Centroid
        if (
          telemetry.centroid &&
          telemetry.centroid.x !== null &&
          telemetry.centroid.y !== null
        ) {
          const tx = telemetry.centroid.x
          const ty = telemetry.centroid.y

          const isLocked = telemetry.trackingState === 'TRACKING'
          const reticleColor = isLocked ? '#22c55e' : '#38bdf8' // Green or Blue

          ctx.strokeStyle = reticleColor
          ctx.lineWidth = 2

          // Target lock box
          const boxSize = 16
          ctx.strokeRect(
            tx - boxSize / 2,
            ty - boxSize / 2,
            boxSize,
            boxSize
          )

          // Center crosshair
          ctx.beginPath()
          ctx.moveTo(tx - 12, ty)
          ctx.lineTo(tx + 12, ty)
          ctx.moveTo(tx, ty - 12)
          ctx.lineTo(tx, ty + 12)
          ctx.stroke()

          // Centroid text tag
          ctx.fillStyle = reticleColor
          ctx.font = '10px JetBrains Mono, monospace'
          ctx.fillText(
            `TGT (${tx.toFixed(1)}, ${ty.toFixed(1)})`,
            tx + 10,
            ty - 8
          )
        }

        // 5. Minimal Engineering HUD
        ctx.fillStyle = 'rgba(15, 23, 42, 0.75)'
        ctx.fillRect(8, 8, 160, 24)
        ctx.strokeStyle = 'rgba(51, 65, 85, 0.8)'
        ctx.strokeRect(8, 8, 160, 24)

        ctx.fillStyle = '#94a3b8'
        ctx.font = '10px JetBrains Mono, monospace'
        ctx.fillText(
          `FPA: ${canvas.width}x${canvas.height} | ${(img.src.length / 1024).toFixed(0)}KB`,
          14,
          24
        )

        const drawEndTime = performance.now()
        const drawMs = drawEndTime - drawStartTime
        perfService.recordFramePipeline(decodeMs, drawMs)

        if (!firstFrameReportedRef.current) {
          firstFrameReportedRef.current = true
          bridgeService.firstFramePresented(decodeMs, drawMs)
        }
      }
    } else {
      // Standby / No Signal state
      ctx.fillStyle = '#080d1a'
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      // Grid background
      ctx.strokeStyle = '#141e33'
      ctx.lineWidth = 1
      const step = 40
      for (let x = 0; x < canvas.width; x += step) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, canvas.height)
        ctx.stroke()
      }
      for (let y = 0; y < canvas.height; y += step) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(canvas.width, y)
        ctx.stroke()
      }

      // Center crosshair
      const cx = canvas.width / 2
      const cy = canvas.height / 2
      ctx.strokeStyle = '#1e293b'
      ctx.beginPath()
      ctx.moveTo(cx - 30, cy)
      ctx.lineTo(cx + 30, cy)
      ctx.moveTo(cx, cy - 30)
      ctx.lineTo(cx, cy + 30)
      ctx.stroke()

      // Standby text
      ctx.fillStyle = '#64748b'
      ctx.font = '13px JetBrains Mono, monospace'
      ctx.textAlign = 'center'
      ctx.fillText(
        isConnected
          ? status.isRunning
            ? 'STREAMING SENSOR FRAMES...'
            : 'SIMULATION STANDBY — CLICK [RUN]'
          : 'AWAITING PYSIDE6 BRIDGE CONNECTION...',
        cx,
        cy + 40
      )
      ctx.textAlign = 'start'
    }
  }, [latestFrame, telemetry, isConnected, status.isRunning])

  const stateColors: Record<string, string> = {
    SEARCHING: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
    COASTING: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    CONVERGING: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
    TRACKING: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    REACQUIRING: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
    LOST: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
  }

  return (
    <div className="flex-1 flex flex-col bg-workstation-900 border border-workstation-700/60 rounded-xl overflow-hidden shadow-2xl relative">
      {/* Viewport Header Bar */}
      <div className="h-10 bg-workstation-850 border-b border-workstation-700/60 px-4 flex items-center justify-between text-xs select-none">
        <div className="flex items-center gap-2 text-gray-300 font-medium">
          <Eye className="w-4 h-4 text-blue-400" />
          <span>Optical Sensor Focal Plane Array (FPA) — 640×480 Grayscale</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Tracking State Badge */}
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-gray-400">Lock State:</span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                stateColors[telemetry.trackingState] || stateColors.SEARCHING
              }`}
            >
              {telemetry.trackingState}
            </span>
          </div>

          <div className="h-4 w-px bg-workstation-700" />

          {/* Rendered Canvas FPS */}
          <div className="text-[11px] font-mono text-gray-400">
            Render: <span className="text-emerald-400 font-bold">{renderedFpsRef.current || 60} FPS</span>
          </div>
        </div>
      </div>

      {/* Main Sensor Canvas Container */}
      <div className="flex-1 flex items-center justify-center p-4 bg-workstation-950/80 overflow-hidden relative">
        <div className="relative border-2 border-workstation-700/80 rounded-lg shadow-inner overflow-hidden bg-black">
          <canvas
            ref={canvasRef}
            width={640}
            height={480}
            className="block max-w-full max-h-[calc(100vh-280px)] object-contain"
          />

          {/* Top-Right On-Screen Boresight HUD Indicator */}
          <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-sm border border-cyan-500/30 px-2 py-1 rounded text-[10px] font-mono text-cyan-300 flex items-center gap-1.5 pointer-events-none">
            <Crosshair className="w-3.5 h-3.5 text-cyan-400" />
            <span>BORESIGHT LOCK</span>
          </div>

          {/* Bottom-Left FOV HUD */}
          <div className="absolute bottom-3 left-3 bg-black/60 backdrop-blur-sm border border-workstation-700 px-2.5 py-1 rounded text-[10px] font-mono text-gray-300 pointer-events-none">
            <span>FOV: {telemetry.cameraFovH.toFixed(1)}° × {telemetry.cameraFovV.toFixed(1)}°</span>
          </div>

          {/* Bottom-Right Coordinates HUD */}
          <div className="absolute bottom-3 right-3 bg-black/60 backdrop-blur-sm border border-workstation-700 px-2.5 py-1 rounded text-[10px] font-mono text-gray-300 pointer-events-none">
            <span>
              Target:{' '}
              {telemetry.centroid && telemetry.centroid.x !== null
                ? `[${telemetry.centroid.x.toFixed(1)}, ${telemetry.centroid.y?.toFixed(1)}]`
                : 'NONE'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
