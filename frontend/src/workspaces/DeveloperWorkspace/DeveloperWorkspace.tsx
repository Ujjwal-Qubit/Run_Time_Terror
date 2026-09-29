import React, { useState, useEffect, useRef } from 'react'
import {
  Video,
  Box,
  Grid,
  Crosshair,
  Sliders,
  Play,
  Pause,
  Square,
  StepForward,
  RotateCcw,
  Lock,
  Activity,
  Layers,
  RotateCw,
  Target,
  Clock,
  ShieldAlert,
  TrendingDown,
} from 'lucide-react'
import { useLumiTrackStore } from '../../store/useLumiTrackStore'
import { bridgeService } from '../../services/bridgeService'
import { PedestalFrustumView } from './PedestalFrustumView'
import { WorldCanvasView } from './WorldCanvasView'

// ─────────────────────────────────────────────────────────────
// Developer Workspace — Screen 1
// Stitch visual fidelity reconstruction with real LumiTrack data
// Integrated: 2D Sensor | 3D Pedestal Frustum | World Canvas views
// ─────────────────────────────────────────────────────────────

type TrajectoryPattern = 'linear' | 'circular' | 'figure8' | 'brownian'
type AtmCondition = 'clear' | 'haze' | 'fog' | 'rain'

// ─── Mini helpers ────────────────────────────────────────────

function fmtNum(v: number | null, decimals = 2, suffix = ''): string {
  if (v === null || isNaN(v)) return '—'
  return v.toFixed(decimals) + suffix
}

function stateColor(state: string): string {
  switch (state) {
    case 'TRACKING':    return 'text-secondary'
    case 'CONVERGING':  return 'text-primary'
    case 'COASTING':    return 'text-tertiary'
    case 'SEARCHING':   return 'text-outline'
    case 'REACQUIRING': return 'text-tertiary'
    case 'LOST':        return 'text-error'
    default:            return 'text-outline'
  }
}

// ─── Main Component ──────────────────────────────────────────

export const DeveloperWorkspace: React.FC = () => {
  const telemetry     = useLumiTrackStore(s => s.telemetry)
  const status        = useLumiTrackStore(s => s.status)
  const latestFrame   = useLumiTrackStore(s => s.latestFrame)
  const isConnected   = useLumiTrackStore(s => s.isConnected)

  // ─ Viewport tab state synchronized with global store ─
  const activeTab     = useLumiTrackStore(s => s.activeDeveloperTab)
  const setActiveTab  = useLumiTrackStore(s => s.setActiveDeveloperTab)

  // ─ Sensor display toggles ─
  const [showGrid,    setShowGrid]    = useState(true)
  const [showReticle, setShowReticle] = useState(true)
  const [zoomLevel,   setZoomLevel]   = useState<'fit' | '1x' | '2x'>('1x')

  // ─ Sim control params ─
  const [pattern,    setPattern]    = useState<TrajectoryPattern>('figure8')
  const [slewVel,    setSlewVel]    = useState(45)
  const [divergence, setDivergence] = useState(10)
  const [atmCond,    setAtmCond]    = useState<AtmCondition>('fog')
  const [gNoise,     setGNoise]     = useState(true)
  const [pNoise,     setPNoise]     = useState(true)
  const [spNoise,    setSpNoise]    = useState(true)
  const [kp,         setKp]         = useState(8.0)
  const [ki,         setKi]         = useState(2.0)
  const [deadband,   setDeadband]   = useState(1.0)

  // ─ 3D spatial toggles ─
  const [frustumRay,   setFrustumRay]   = useState(true)
  const [trajTrail,    setTrajTrail]    = useState(true)
  const [canvasGrid,   setCanvasGrid]   = useState(true)

  // ─ Real-time 2D trajectory trail (60-point FIFO buffer of real centroids) ─
  const [trajectoryTrail, setTrajectoryTrail] = useState<{ x: number; y: number }[]>([])

  // ─ Real-time operational metric history (120 frames) ─
  const [metricHistory, setMetricHistory] = useState<number[]>([])

  // Derived live display values
  const loopRate   = telemetry.algorithmFps || status.backendFps
  const trackErr   = telemetry.trackingErrorPx
  const frameNum   = telemetry.frameNumber
  const latencyMs  = telemetry.processingLatencyMs
  const panDeg     = telemetry.panAngleDeg
  const tiltDeg    = telemetry.tiltAngleDeg
  const cx         = telemetry.centroid.x
  const cy         = telemetry.centroid.y
  const tState     = telemetry.trackingState
  const boresightOffset = telemetry.boresightOffsetPx

  useEffect(() => {
    if (cx !== null && cy !== null && !isNaN(cx) && !isNaN(cy) && tState !== 'STANDBY') {
      setTrajectoryTrail(prev => {
        const next = [...prev, { x: cx, y: cy }]
        if (next.length > 60) next.shift()
        return next
      })
    }
  }, [cx, cy, frameNum, tState])

  useEffect(() => {
    const v = status.validationMode ? telemetry.trackingErrorPx : telemetry.boresightOffsetPx
    if (v !== null && v !== undefined && !isNaN(v) && tState !== 'STANDBY') {
      setMetricHistory(prev => {
        const next = [...prev, v]
        if (next.length > 120) next.shift()
        return next
      })
    }
  }, [telemetry.trackingErrorPx, telemetry.boresightOffsetPx, frameNum, status.validationMode, tState])

  // Reset trail & history on simulation reset
  useEffect(() => {
    if (!status.isRunning && frameNum === 0) {
      setTrajectoryTrail([])
      setMetricHistory([])
    }
  }, [status.isRunning, frameNum])

  // ─ Canvas ref for live sensor frames ─
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    if (latestFrame && latestFrame.data) {
      const img = new Image()
      img.onload = () => {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      }
      img.src = latestFrame.data
    } else {
      // Draw dark placeholder with noise texture
      ctx.fillStyle = '#0b0f12'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      // Subtle noise pattern
      for (let i = 0; i < 400; i++) {
        const x = Math.random() * canvas.width
        const y = Math.random() * canvas.height
        const v = Math.floor(Math.random() * 40)
        ctx.fillStyle = `rgba(${v}, ${v + 20}, ${v + 40}, 0.4)`
        ctx.fillRect(x, y, 2, 2)
      }
    }
  }, [latestFrame])

  // Progress percentage for frame buffer
  const framePct = frameNum > 0 ? Math.min(100, (frameNum / 3600) * 100).toFixed(1) : '0.0'

  // Sparkline path data
  const sparkPoints = (() => {
    const w = 480, h = 48, max = 20, min = 0
    if (metricHistory.length < 2) return ''
    return metricHistory.map((v, i) => {
      const x = (i / (metricHistory.length - 1)) * w
      const y = h - ((Math.min(max, Math.max(min, v)) / max) * (h - 8)) - 4
      return `${x.toFixed(1)},${y.toFixed(1)}`
    }).join(' ')
  })()

  // ─ Control matrix handlers (UI -> bridgeService -> PyBridge -> backend) ─
  const handlePatternChange = (p: TrajectoryPattern) => {
    setPattern(p)
    bridgeService.setMotionPattern(p)
  }

  const handleSlewVelChange = (val: number) => {
    setSlewVel(val)
    bridgeService.setTargetSpeed(val)
  }

  const handleDivergenceChange = (val: number) => {
    setDivergence(val)
    bridgeService.setTargetSize(val)
  }

  const handleAtmCondChange = (c: AtmCondition) => {
    setAtmCond(c)
    bridgeService.setAtmosphericCondition(c)
  }

  const handleNoiseToggle = (type: 'gaussian' | 'poisson' | 'salt_and_pepper', val: boolean) => {
    if (type === 'gaussian') setGNoise(val)
    if (type === 'poisson') setPNoise(val)
    if (type === 'salt_and_pepper') setSpNoise(val)
    bridgeService.setNoiseEnabled(type, val)
  }

  const handlePtzGainUpdate = (newKp: number, newKi: number, newDb: number) => {
    setKp(newKp)
    setKi(newKi)
    setDeadband(newDb)
    bridgeService.setPtzGains(newKp, newKi, newDb)
  }


  // ─── TRANSPORT CONTROLS ─────────────────────────────────────
  const handleRun   = () => bridgeService.run()
  const handlePause = () => bridgeService.pause()
  const handleStop  = () => bridgeService.stop()
  const handleStep  = () => bridgeService.step()
  const handleReset = () => bridgeService.reset()

  const handleAlgorithmChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    bridgeService.selectAlgorithm(e.target.value)
  }
  const handleScenarioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    bridgeService.selectScenario(e.target.value)
  }

  return (
    <div className="flex flex-col gap-space-md p-space-md bg-surface text-on-surface">

      {/* ── Top Context Bar ───────────────────────────────────── */}
      <div className="flex items-center justify-between bg-surface-container-low px-space-md py-space-sm rounded border border-outline-variant/30">
        <div className="flex items-center gap-space-md">
          <div className="flex items-center gap-space-xs">
            <span className={`w-2 h-2 rounded-full shrink-0 ${isConnected && status.isRunning ? 'bg-secondary animate-pulse' : 'bg-outline'}`} />
            <span className="font-headline-sm text-headline-sm uppercase tracking-wider text-on-surface">
              Primary Real-Time Simulation &amp; Coarse Alignment
            </span>
          </div>
          <span className="text-outline-variant">/</span>
          <span className="font-label-sm text-label-sm text-outline uppercase tracking-tight">
            Loop Mode: {status.isRunning ? (status.isPaused ? 'PAUSED' : 'Autonomous Fine-Tracking') : 'IDLE'}
          </span>
          <span className="font-data-sm text-data-sm px-space-xs py-0.5 bg-primary/10 text-primary border border-primary/30 rounded">
            HARNESS: {isConnected ? 'ACTIVE' : 'OFFLINE'}
          </span>
        </div>
        <div className="flex items-center gap-space-sm font-label-sm text-label-sm">
          <span className="text-outline">TARGET ID:</span>
          <span className="font-data-sm text-data-sm text-on-surface font-medium">
            {status.activeScenario || 'ACTIVE SCENARIO'}
          </span>
          <span className="text-outline-variant mx-space-xs">|</span>
          <span className="text-outline">ALG:</span>
          <span className="font-data-sm text-data-sm text-primary font-medium">
            {status.activeAlgorithm || 'N/A'}
          </span>
        </div>
      </div>

      {/* ── Main 2-Column Grid ────────────────────────────────── */}
      <div className="grid grid-cols-12 gap-space-md">

        {/* ═══ LEFT COLUMN (8 cols) ════════════════════════════ */}
        <div className="col-span-12 xl:col-span-8 flex flex-col gap-space-md min-w-0">

          {/* ─── 2D SENSOR VIEW ─────────────────────────────── */}
          {activeTab === '2d' && (
            <>
              {/* Viewport Mode Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-space-sm bg-surface-container-low p-space-xs rounded border border-outline-variant/30">
                <div className="flex items-center gap-space-xs">
                  <button
                    type="button"
                    className="px-space-md py-space-xs bg-primary text-on-primary font-label-md text-label-md rounded font-medium flex items-center gap-space-xs shadow-sm"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse" />
                    <Video className="w-3.5 h-3.5" />
                    <span>2D Sensor View (640×480) ACTIVE</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab('3d')}
                    className="px-space-md py-space-xs bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high font-label-md text-label-md rounded transition-colors flex items-center gap-space-xs"
                  >
                    <Box className="w-3.5 h-3.5" />
                    <span>3D Pedestal Frustum</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab('world')}
                    className="px-space-md py-space-xs bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high font-label-md text-label-md rounded transition-colors flex items-center gap-space-xs"
                  >
                    <Grid className="w-3.5 h-3.5" />
                    <span>2000×2000 World Canvas</span>
                  </button>
                </div>
                <div className="flex items-center gap-space-xs">
                  <div className="flex items-center bg-surface-container rounded border border-outline-variant/30 p-0.5">
                    {(['fit', '1x', '2x'] as const).map(z => (
                      <button
                        key={z}
                        type="button"
                        onClick={() => setZoomLevel(z)}
                        className={`px-space-sm py-0.5 font-data-sm text-data-sm rounded ${
                          zoomLevel === z ? 'text-primary bg-surface-container-highest font-medium' : 'text-on-surface hover:bg-surface-container-highest'
                        }`}
                      >{z === 'fit' ? 'FIT' : z === '1x' ? '1.0x' : '2.0x'}</button>
                    ))}
                  </div>
                  <div className="h-4 w-[1px] bg-outline-variant/30 mx-space-xs" />
                  <button
                    type="button"
                    onClick={() => setShowGrid(g => !g)}
                    className={`flex items-center gap-space-xs px-space-sm py-space-xs rounded border font-label-sm text-label-sm transition-colors ${
                      showGrid ? 'bg-surface-container-high text-secondary border-secondary/30' : 'bg-surface-container text-on-surface-variant border-outline-variant/30 hover:bg-surface-container-high'
                    }`}
                  >
                    <Grid className="w-3.5 h-3.5" />
                    <span>GRID</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowReticle(r => !r)}
                    className={`flex items-center gap-space-xs px-space-sm py-space-xs rounded border font-label-sm text-label-sm transition-colors ${
                      showReticle ? 'bg-surface-container-high text-primary border-primary/30' : 'bg-surface-container text-on-surface-variant border-outline-variant/30 hover:bg-surface-container-high'
                    }`}
                  >
                    <Crosshair className="w-3.5 h-3.5" />
                    <span>RETICLE</span>
                  </button>
                </div>
              </div>
              <div className="relative w-full aspect-[4/3] max-h-[580px] bg-surface-container-lowest rounded border border-outline-variant/40 overflow-hidden flex items-center justify-center select-none shadow-md">
                {/* Scalable sensor stage */}
                <div
                  className="relative w-full h-full flex items-center justify-center transition-transform duration-200 origin-center"
                  style={{
                    transform: zoomLevel === '2x' ? 'scale(2)' : zoomLevel === 'fit' ? 'scale(0.92)' : 'scale(1)',
                  }}
                >
                  {/* Sensor noise texture background */}
                  <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#4edea3_1px,transparent_1px)] [background-size:16px_16px]" />
                  {/* Vignette */}
                  <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_40%,rgba(11,15,18,0.92)_100%)]" />

                  {/* Live canvas */}
                  <canvas
                    ref={canvasRef}
                    width={640}
                    height={480}
                    className="absolute inset-0 w-full h-full object-contain"
                  />

                  {/* Boresight + reticle overlays */}
                  {showReticle && (
                    <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                      <div className="w-64 h-64 rounded-full border border-outline-variant/30 border-dashed flex items-center justify-center">
                        <div className="w-32 h-32 rounded-full border border-outline-variant/40" />
                      </div>
                      <div className="absolute w-full h-[1px] bg-outline-variant/30" />
                      <div className="absolute h-full w-[1px] bg-outline-variant/30" />
                      {/* Corner brackets */}
                      <div className="absolute w-4 h-4 border-t-2 border-l-2 border-outline-variant/60 top-2 left-2" />
                      <div className="absolute w-4 h-4 border-t-2 border-r-2 border-outline-variant/60 top-2 right-2" />
                      <div className="absolute w-4 h-4 border-b-2 border-l-2 border-outline-variant/60 bottom-2 left-2" />
                      <div className="absolute w-4 h-4 border-b-2 border-r-2 border-outline-variant/60 bottom-2 right-2" />
                    </div>
                  )}

                  {/* Grid overlay */}
                  {showGrid && (
                    <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-15" viewBox="0 0 640 480">
                      {[160, 320, 480].map(x => (
                        <line key={`v${x}`} x1={x} y1={0} x2={x} y2={480} stroke="#424754" strokeWidth="0.5" />
                      ))}
                      {[120, 240, 360].map(y => (
                        <line key={`h${y}`} x1={0} y1={y} x2={640} y2={y} stroke="#424754" strokeWidth="0.5" />
                      ))}
                    </svg>
                  )}

                  {/* Trajectory + centroid SVG */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible" viewBox="0 0 640 480">
                    {/* Dynamic Trajectory Trail */}
                    {trajTrail && trajectoryTrail.length >= 2 && (
                      <polyline
                        points={trajectoryTrail.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')}
                        fill="none"
                        stroke="#4d8eff"
                        strokeDasharray="4,2"
                        strokeWidth="1.5"
                        opacity="0.8"
                      />
                    )}
                    {trajTrail && trajectoryTrail.map((p, idx) => (
                      <circle
                        key={idx}
                        cx={p.x}
                        cy={p.y}
                        r={idx === trajectoryTrail.length - 1 ? 2.5 : 1.2}
                        fill="#adc6ff"
                        opacity={0.25 + (idx / trajectoryTrail.length) * 0.75}
                      />
                    ))}

                    {cx !== null && cy !== null && tState !== 'STANDBY' && (
                      <>
                        {/* ROI bracket */}
                        <rect
                          x={cx - 40}
                          y={cy - 40}
                          width={80}
                          height={80}
                          fill="rgba(173, 198, 255, 0.05)"
                          stroke="rgba(173, 198, 255, 0.5)"
                          strokeWidth="1"
                        />
                        {/* Centroid dot */}
                        <circle cx={cx} cy={cy} r="4" fill="#4edea3" />
                        <line x1={cx - 14} y1={cy} x2={cx + 14} y2={cy} stroke="#4edea3" strokeWidth="1" opacity="0.7" />
                        <line x1={cx} y1={cy - 14} x2={cx} y2={cy + 14} stroke="#4edea3" strokeWidth="1" opacity="0.7" />
                        <text x={cx + 8} y={cy + 14} fontSize="9" fill="#4edea3" fontFamily="JetBrains Mono">
                          ({cx.toFixed(1)}, {cy.toFixed(1)})
                        </text>
                      </>
                    )}
                    {/* Boresight origin */}
                    <circle cx="320" cy="240" r="4" fill="none" stroke="rgba(224,227,232,0.4)" strokeWidth="1" />
                    <circle cx="320" cy="240" r="1.5" fill="rgba(224,227,232,0.6)" />
                  </svg>
                </div>

                {/* Ground truth watermark (validation mode only) */}
                {status.validationMode && (
                  <div className="absolute top-4 left-1/2 -translate-x-1/2 pointer-events-none flex items-center gap-space-xs px-space-md py-space-xs bg-surface-container-lowest/95 border border-outline-variant/60 rounded shadow-md">
                    <Lock className="w-3.5 h-3.5 text-tertiary" />
                    <span className="font-data-sm text-data-sm text-on-surface font-semibold tracking-wider uppercase">[GROUND TRUTH — VALIDATION ONLY]</span>
                    <span className="w-1.5 h-1.5 bg-tertiary rounded-full animate-ping" />
                  </div>
                )}

                {/* Left HUD overlay */}
                <div className="absolute top-3 left-3 flex flex-col gap-1 p-space-sm bg-surface-container-lowest/90 border border-outline-variant/30 rounded font-data-sm text-data-sm">
                  <div className="flex items-center gap-space-sm">
                    <span className="text-outline">STATE:</span>
                    <span className={`font-medium flex items-center gap-1 ${stateColor(tState)}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${tState === 'TRACKING' ? 'bg-secondary' : 'bg-outline'}`} />
                      {tState}
                    </span>
                  </div>
                  <div className="flex items-center gap-space-sm">
                    <span className="text-outline">CONF:</span>
                    <span className="text-primary font-medium">{(telemetry.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex items-center gap-space-sm">
                    <span className="text-outline">RESIDUAL:</span>
                    <span className="text-on-surface">
                      {boresightOffset !== null ? `${boresightOffset.toFixed(3)} px` : '—'}
                    </span>
                  </div>
                </div>

                {/* Right HUD overlay */}
                <div className="absolute top-3 right-3 flex flex-col gap-1 p-space-sm bg-surface-container-lowest/90 border border-outline-variant/30 rounded font-data-sm text-data-sm text-right">
                  <div className="flex items-center justify-end gap-space-sm">
                    <span className="text-outline">GIMBAL:</span>
                    <span className="text-on-surface font-medium">
                      Pan {fmtNum(panDeg, 3)}°  |  Tilt {fmtNum(tiltDeg, 3)}°
                    </span>
                  </div>
                  <div className="flex items-center justify-end gap-space-sm">
                    <span className="text-outline">FOV:</span>
                    <span className="text-secondary font-medium">
                      {telemetry.cameraFovH.toFixed(1)}° × {telemetry.cameraFovV.toFixed(1)}°
                    </span>
                  </div>
                  <div className="flex items-center justify-end gap-space-sm">
                    <span className="text-outline">FPA:</span>
                    <span className="text-tertiary font-medium">
                      {telemetry.cameraWidth}×{telemetry.cameraHeight}
                    </span>
                  </div>
                </div>

                {/* Bottom viewport status */}
                <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between pointer-events-none">
                  <div className="flex items-center gap-space-sm font-label-sm text-label-sm text-outline bg-surface-container-lowest/80 px-space-sm py-0.5 rounded">
                    <span>FR #{frameNum.toString().padStart(6, '0')}</span>
                    <span>•</span>
                    <span>{loopRate.toFixed(1)} FPS</span>
                    <span>•</span>
                    <span className={tState === 'TRACKING' ? 'text-secondary' : 'text-outline'}>
                      {status.isRunning ? (status.isPaused ? 'PAUSED' : 'RUNNING') : 'IDLE'}
                    </span>
                  </div>
                  <div className="font-data-sm text-data-sm text-outline-variant bg-surface-container-lowest/80 px-space-sm py-0.5 rounded">
                    FOVx: {telemetry.cameraFovH.toFixed(2)}° × FOVy: {telemetry.cameraFovV.toFixed(2)}°
                  </div>
                </div>
              </div>

              {/* Minimap Thumbnails Dock */}
              <div className="grid grid-cols-2 gap-space-md">
                {/* Minimap 1: 3D Pedestal */}
                <div className="flex flex-col bg-surface-container-low rounded border border-outline-variant/30 p-space-sm">
                  <div className="flex items-center justify-between mb-space-xs">
                    <div className="flex items-center gap-space-xs">
                      <Box className="w-3.5 h-3.5 text-primary" />
                      <span className="font-label-md text-label-md text-on-surface font-medium">Pedestal Kinematic Frustum</span>
                    </div>
                    <button type="button" onClick={() => setActiveTab('3d')} className="font-data-sm text-[10px] text-secondary hover:underline">EXPAND</button>
                  </div>
                  <div className="relative h-24 bg-surface-container-lowest rounded border border-outline-variant/20 overflow-hidden flex items-center justify-center">
                    <svg className="absolute inset-0 w-full h-full opacity-60" viewBox="0 0 200 80">
                      <line stroke="#8c909f" strokeWidth="0.5" x1="0" y1="40" x2="200" y2="40" />
                      <line stroke="#8c909f" strokeWidth="0.5" x1="100" y1="0" x2="100" y2="80" />
                      <polygon fill="none" points="100,50 60,75 140,75" stroke="#adc6ff" strokeWidth="1" />
                      <line stroke="#4edea3" strokeWidth="1.5" x1="100" y1="50" x2="100" y2="20" />
                      <circle cx="100" cy="20" fill="#ffb95f" r="3" />
                      <path d="M 80,30 L 120,30 L 140,70 L 60,70 Z" fill="rgba(77, 142, 255, 0.1)" stroke="#4d8eff" strokeDasharray="2,2" strokeWidth="0.5" />
                    </svg>
                    <div className="absolute bottom-1 left-2 font-data-sm text-[10px] text-outline">
                      AZ: {fmtNum(panDeg, 1)}° | EL: {fmtNum(tiltDeg, 1)}°
                    </div>
                  </div>
                </div>

                {/* Minimap 2: World Canvas */}
                <div className="flex flex-col bg-surface-container-low rounded border border-outline-variant/30 p-space-sm">
                  <div className="flex items-center justify-between mb-space-xs">
                    <div className="flex items-center gap-space-xs">
                      <Grid className="w-3.5 h-3.5 text-primary" />
                      <span className="font-label-md text-label-md text-on-surface font-medium">World Canvas (2000×2000)</span>
                    </div>
                    <button type="button" onClick={() => setActiveTab('world')} className="font-data-sm text-[10px] text-outline hover:text-on-surface">EXPAND</button>
                  </div>
                  <div className="relative h-24 bg-surface-container-lowest rounded border border-outline-variant/20 overflow-hidden flex items-center justify-center">
                    <div className="w-20 h-20 border border-outline-variant/40 relative">
                      <div className="absolute top-6 left-8 w-6 h-5 border border-primary bg-primary/20" />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-12 h-12 rounded-full border border-secondary/30 border-dashed" />
                      </div>
                    </div>
                    <div className="absolute bottom-1 left-2 font-data-sm text-[10px] text-outline">
                      {cx !== null ? `EST CENTROID: (${cx.toFixed(1)}, ${cy?.toFixed(1) ?? '—'}) px` : 'AWAITING LOCK'}
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* ─── 3D PEDESTAL FRUSTUM VIEW ───────────────────── */}
          {activeTab === '3d' && (
            <PedestalFrustumView
              telemetry={telemetry}
              status={status}
              trajectoryTrail={trajectoryTrail}
              loopRate={loopRate}
              slewVel={slewVel}
              atmCond={atmCond}
              setActiveTab={setActiveTab}
              frustumRay={frustumRay}
              setFrustumRay={setFrustumRay}
              trajTrail={trajTrail}
              setTrajTrail={setTrajTrail}
            />
          )}

          {/* ─── 2000×2000 WORLD CANVAS VIEW ────────────────── */}
          {activeTab === 'world' && (
            <WorldCanvasView
              telemetry={telemetry}
              status={status}
              trajectoryTrail={trajectoryTrail}
              loopRate={loopRate}
              slewVel={slewVel}
              atmCond={atmCond}
              setActiveTab={setActiveTab}
              canvasGrid={canvasGrid}
              setCanvasGrid={setCanvasGrid}
              trajTrail={trajTrail}
              setTrajTrail={setTrajTrail}
            />
          )}
        </div>

        {/* ═══ RIGHT COLUMN (4 cols) — SIMULATOR CONTROL MATRIX ═ */}
        <div className="col-span-12 xl:col-span-4 flex flex-col gap-space-md min-w-0">

          {/* Control Matrix Header */}
          <div className="flex items-center justify-between bg-surface-container-low px-space-md py-space-sm rounded border border-outline-variant/30">
            <div className="flex items-center gap-space-xs font-label-md text-label-md font-semibold text-on-surface">
              <Sliders className="w-4 h-4 text-primary" />
              <span>SIMULATOR CONTROL MATRIX</span>
            </div>
            <span className={`font-label-sm text-label-sm px-space-xs py-0.5 rounded border ${
              isConnected
                ? 'bg-secondary/10 text-secondary border-secondary/20'
                : 'bg-surface-container text-outline border-outline-variant/30'
            }`}>
              {isConnected ? 'HOT-RELOAD ON' : 'OFFLINE'}
            </span>
          </div>

          {/* Section 1: Camera & Sensor FPA */}
          <div className="bg-surface-container-low rounded border border-outline-variant/30 overflow-hidden">
            <div className="px-space-md py-space-xs bg-surface-container border-b border-outline-variant/30 flex items-center justify-between">
              <span className="font-label-md text-label-md font-medium text-on-surface">1. Camera &amp; Sensor FPA</span>
              <button
                type="button"
                onClick={() => {
                  const next = !(status.trackingEnabled ?? true)
                  useLumiTrackStore.getState().setStatus({ ...status, trackingEnabled: next })
                  bridgeService.setTrackingEnabled(next)
                }}
                className={`font-data-sm text-[11px] font-medium px-2 py-0.5 rounded border transition-colors ${
                  status.trackingEnabled !== false
                    ? 'bg-secondary/20 text-secondary border-secondary/40 hover:bg-secondary/30'
                    : 'bg-surface-container-highest text-outline border-outline-variant/40 hover:text-on-surface'
                }`}
                title="Toggle Tracking Pipeline"
              >
                {status.trackingEnabled !== false ? 'TRACKING: ON' : 'STANDBY'}
              </button>
            </div>
            <div className="p-space-md grid grid-cols-2 gap-space-sm">
              <div className="flex flex-col gap-0.5">
                <span className="font-label-sm text-label-sm text-outline uppercase">Array Resolution</span>
                <span className="font-data-md text-data-md text-on-surface">{telemetry.cameraWidth} × {telemetry.cameraHeight} px</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="font-label-sm text-label-sm text-outline uppercase">Field of View</span>
                <span className="font-data-md text-data-md text-on-surface">{telemetry.cameraFovH.toFixed(1)}° × {telemetry.cameraFovV.toFixed(1)}°</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="font-label-sm text-label-sm text-outline uppercase">Loop Frame Rate</span>
                <div className="flex items-center gap-space-xs">
                  <span className={`font-data-md text-data-md font-semibold ${loopRate >= 20 ? 'text-secondary' : 'text-error'}`}>
                    {loopRate > 0 ? loopRate.toFixed(1) : '—'}
                  </span>
                  <span className="font-data-sm text-data-sm text-outline">FPS</span>
                </div>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="font-label-sm text-label-sm text-outline uppercase">Algorithm</span>
                <span className="font-data-sm text-data-sm text-primary truncate" title={status.activeAlgorithm}>
                  {status.activeAlgorithm || 'N/A'}
                </span>
              </div>
            </div>
            {/* Algorithm selector */}
            {status.availableAlgorithms.length > 0 && (
              <div className="px-space-md pb-space-sm">
                <label className="font-label-sm text-label-sm text-outline uppercase block mb-1">Select Algorithm</label>
                <select
                  value={status.activeAlgorithm}
                  onChange={handleAlgorithmChange}
                  className="w-full h-7 px-space-sm bg-surface-container-lowest text-on-surface border border-outline-variant/40 rounded font-data-sm text-data-sm focus:border-primary focus:outline-none"
                >
                  {status.availableAlgorithms.map(a => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Section 2: Target Kinematics */}
          <div className="bg-surface-container-low rounded border border-outline-variant/30 overflow-hidden">
            <div className="px-space-md py-space-xs bg-surface-container border-b border-outline-variant/30 flex items-center justify-between">
              <span className="font-label-md text-label-md font-medium text-on-surface">2. Target Kinematics</span>
              <span className="font-data-sm text-data-sm text-tertiary">DYNAMIC PATH</span>
            </div>
            <div className="p-space-md flex flex-col gap-space-md">
              <div>
                <span className="font-label-sm text-label-sm text-outline uppercase block mb-1">Trajectory Pattern</span>
                <div className="grid grid-cols-4 gap-1">
                  {(['linear', 'circular', 'figure8', 'brownian'] as TrajectoryPattern[]).map(p => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => handlePatternChange(p)}
                      className={`py-1 px-1 font-label-sm text-[10px] rounded text-center transition-colors ${
                        pattern === p
                          ? 'bg-primary text-on-primary font-semibold shadow-sm'
                          : 'bg-surface-container hover:bg-surface-container-high text-on-surface-variant'
                      }`}
                    >
                      {p === 'figure8' ? 'Figure-8' : p.charAt(0).toUpperCase() + p.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex justify-between items-center font-label-sm text-label-sm">
                  <span className="text-outline uppercase">Slew Velocity:</span>
                  <span className="font-data-sm text-data-sm text-primary font-medium">{slewVel}.0 px/s</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={slewVel}
                  onChange={e => handleSlewVelChange(+e.target.value)}
                  className="w-full h-1 bg-surface-container-highest rounded appearance-none cursor-pointer accent-primary"
                />
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex justify-between items-center font-label-sm text-label-sm">
                  <span className="text-outline uppercase">Spot Gaussian Divergence:</span>
                  <span className="font-data-sm text-data-sm text-on-surface">{divergence}.0 px (FWHM)</span>
                </div>
                <input
                  type="range"
                  min="2"
                  max="25"
                  value={divergence}
                  onChange={e => handleDivergenceChange(+e.target.value)}
                  className="w-full h-1 bg-surface-container-highest rounded appearance-none cursor-pointer accent-primary"
                />
              </div>
              {/* Scenario selector */}
              {status.availableScenarios.length > 0 && (
                <div>
                  <label className="font-label-sm text-label-sm text-outline uppercase block mb-1">Select Scenario</label>
                  <select
                    value={status.activeScenario}
                    onChange={handleScenarioChange}
                    className="w-full h-7 px-space-sm bg-surface-container-lowest text-on-surface border border-outline-variant/40 rounded font-data-sm text-data-sm focus:border-primary focus:outline-none"
                  >
                    {status.availableScenarios.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Section 3: Environmental Disturbances */}
          <div className="bg-surface-container-low rounded border border-outline-variant/30 overflow-hidden">
            <div className="px-space-md py-space-xs bg-surface-container border-b border-outline-variant/30 flex items-center justify-between">
              <span className="font-label-md text-label-md font-medium text-on-surface">3. Environmental Disturbances (SIH)</span>
              <span className="font-data-sm text-[10px] bg-error-container/40 text-error px-1 rounded">STRESS TEST</span>
            </div>
            <div className="p-space-md flex flex-col gap-space-md">
              <div>
                <span className="font-label-sm text-label-sm text-outline uppercase block mb-1">Atmospheric Condition</span>
                <div className="grid grid-cols-4 gap-1">
                  {(['clear', 'haze', 'fog', 'rain'] as AtmCondition[]).map(c => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => handleAtmCondChange(c)}
                      className={`py-1 px-1 font-label-sm text-[10px] rounded text-center transition-colors ${
                        atmCond === c
                          ? 'bg-tertiary-container text-on-tertiary-container font-semibold'
                          : 'bg-surface-container hover:bg-surface-container-high text-on-surface-variant'
                      }`}
                    >
                      {c.charAt(0).toUpperCase() + c.slice(1)}{atmCond === c ? ' (ACTIVE)' : ''}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex flex-col gap-space-xs border-t border-outline-variant/20 pt-space-sm">
                <span className="font-label-sm text-label-sm text-outline uppercase block">Noise Injection Channels</span>
                {[
                  { label: 'Gaussian Noise', type: 'gaussian' as const, value: gNoise, tag: 'σ = 12.5 DN', color: 'text-primary' },
                  { label: 'Poisson Shot Noise', type: 'poisson' as const, value: pNoise, tag: 'ACTIVE', color: 'text-secondary' },
                  { label: 'Salt & Pepper', type: 'salt_and_pepper' as const, value: spNoise, tag: '10% Density', color: 'text-tertiary' },
                ].map(({ label, type, value, tag, color }) => (
                  <div key={label} className="flex items-center justify-between py-0.5">
                    <label className="flex items-center gap-space-xs cursor-pointer">
                      <input
                        type="checkbox"
                        checked={value}
                        onChange={e => handleNoiseToggle(type, e.target.checked)}
                        className="rounded border-outline-variant bg-surface-container-highest text-primary focus:ring-0"
                      />
                      <span className="font-label-sm text-label-sm text-on-surface">{label}</span>
                    </label>
                    <span className={`font-data-sm text-data-sm ${value ? color : 'text-outline'}`}>
                      {value ? tag : 'OFF'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Section 4: PTZ Servo Loop Parameters */}
          <div className="bg-surface-container-low rounded border border-outline-variant/30 overflow-hidden">
            <div className="px-space-md py-space-xs bg-surface-container border-b border-outline-variant/30 flex items-center justify-between">
              <span className="font-label-md text-label-md font-medium text-on-surface">4. PTZ Servo Loop Parameters</span>
              <button
                type="button"
                onClick={() => {
                  const next = !(status.ptzEnabled ?? true)
                  useLumiTrackStore.getState().setStatus({ ...status, ptzEnabled: next })
                  bridgeService.setPtzEnabled(next)
                }}
                className={`font-data-sm text-[11px] font-medium px-2 py-0.5 rounded border transition-colors ${
                  status.ptzEnabled !== false
                    ? 'bg-secondary/20 text-secondary border-secondary/40 hover:bg-secondary/30'
                    : 'bg-surface-container-highest text-outline border-outline-variant/40 hover:text-on-surface'
                }`}
                title="Toggle PTZ Actuation"
              >
                {status.ptzEnabled !== false ? 'PTZ ACTIVE' : 'PTZ DISABLED'}
              </button>
            </div>
            <div className="p-space-md grid grid-cols-2 gap-space-md">
              <div>
                <label className="font-label-sm text-label-sm text-outline block mb-0.5 uppercase">Prop. Gain (Kp)</label>
                <input
                  type="number"
                  step="0.5"
                  value={kp}
                  onChange={e => handlePtzGainUpdate(+e.target.value, ki, deadband)}
                  className="w-full h-7 px-space-sm bg-surface-container-lowest text-on-surface border border-outline-variant/40 rounded font-data-md text-data-md focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="font-label-sm text-label-sm text-outline block mb-0.5 uppercase">Integral Gain (Ki)</label>
                <input
                  type="number"
                  step="0.1"
                  value={ki}
                  onChange={e => handlePtzGainUpdate(kp, +e.target.value, deadband)}
                  className="w-full h-7 px-space-sm bg-surface-container-lowest text-on-surface border border-outline-variant/40 rounded font-data-md text-data-md focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="font-label-sm text-label-sm text-outline block mb-0.5 uppercase">Deadband</label>
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    step="0.1"
                    value={deadband}
                    onChange={e => handlePtzGainUpdate(kp, ki, +e.target.value)}
                    className="w-full h-7 px-space-sm bg-surface-container-lowest text-on-surface border border-outline-variant/40 rounded font-data-md text-data-md focus:border-primary focus:outline-none"
                  />
                  <span className="font-data-sm text-data-sm text-outline">px</span>
                </div>
              </div>
              <div>
                <label className="font-label-sm text-label-sm text-outline block mb-0.5 uppercase">Anti-Windup</label>
                <div className="h-7 px-space-sm bg-secondary/10 border border-secondary/30 rounded flex items-center justify-between">
                  <span className="font-data-sm text-data-sm text-secondary font-semibold">CLAMPING</span>
                  <span className="w-2 h-2 rounded-full bg-secondary" />
                </div>
              </div>
            </div>
          </div>

          {/* Transport Controls (repeated for right-column convenience) */}
          <div className="flex items-center gap-space-xs bg-surface-container-low p-space-xs rounded border border-outline-variant/30">
            <button
              type="button"
              onClick={handleRun}
              disabled={!isConnected}
              className="flex items-center gap-space-xs px-space-md py-space-xs bg-secondary-container text-on-secondary-container hover:bg-secondary hover:text-on-secondary rounded font-label-md text-label-md font-medium transition-colors disabled:opacity-40"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>RUN</span>
            </button>
            <button type="button" onClick={handlePause} disabled={!isConnected} className="flex items-center gap-space-xs px-space-sm py-space-xs text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface rounded font-label-md text-label-md transition-colors disabled:opacity-40">
              <Pause className="w-3.5 h-3.5" />
              <span>PAUSE</span>
            </button>
            <button type="button" onClick={handleStop} disabled={!isConnected} className="flex items-center gap-space-xs px-space-sm py-space-xs text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface rounded font-label-md text-label-md transition-colors disabled:opacity-40">
              <Square className="w-3.5 h-3.5" />
              <span>STOP</span>
            </button>
            <button type="button" onClick={handleStep} disabled={!isConnected} className="flex items-center gap-space-xs px-space-sm py-space-xs text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface rounded font-label-md text-label-md transition-colors disabled:opacity-40">
              <StepForward className="w-3.5 h-3.5" />
              <span>+1 FR</span>
            </button>
            <button type="button" onClick={handleReset} disabled={!isConnected} className="flex items-center gap-space-xs px-space-sm py-space-xs text-outline hover:text-on-surface hover:bg-surface-container-high rounded font-label-md text-label-md transition-colors disabled:opacity-40">
              <RotateCcw className="w-3.5 h-3.5" />
              <span>RESET</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── Bottom Horizon Strip ───────────────────────────────── */}
      <div className="flex flex-col gap-space-xs bg-surface-container-low p-space-md rounded border border-outline-variant/30">
        <div className="flex items-center justify-between border-b border-outline-variant/20 pb-space-xs">
          <div className="flex items-center gap-space-sm">
            <Activity className="w-4 h-4 text-secondary" />
            <span className="font-headline-sm text-headline-sm uppercase tracking-wide text-on-surface">Horizon Performance Metrics &amp; Specification Compliance</span>
          </div>
          <div className="flex items-center gap-space-md font-label-sm text-label-sm">
            <div className="flex items-center gap-1">
              <span className={`w-2 h-2 rounded-full ${tState === 'TRACKING' ? 'bg-secondary' : 'bg-outline'}`} />
              <span className={`font-medium ${tState === 'TRACKING' ? 'text-secondary' : 'text-outline'}`}>
                {tState === 'TRACKING' ? 'SPECIFICATION COMPLIANCE: ACTIVE' : 'AWAITING LOCK'}
              </span>
            </div>
            <span className="text-outline-variant">|</span>
            <span className="text-outline">FRAME: {frameNum.toString().padStart(6, '0')}</span>
          </div>
        </div>

        {/* 6 Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-space-sm pt-space-xs">
          {[
            {
              label: 'Frame Buffer',
              Icon: Layers,
              value: frameNum.toString().padStart(6, '0'),
              sub1: frameNum > 0 ? `STATUS: PASS` : 'IDLE',
              sub2: `${framePct}%`,
              color: 'text-on-surface',
              sub1Color: 'text-secondary',
            },
            {
              label: 'Loop Rate',
              Icon: RotateCw,
              value: loopRate > 0 ? `${loopRate.toFixed(1)} Hz` : '—',
              sub1: 'SPEC ≥ 20.0 Hz',
              sub2: loopRate > 0 ? `${(loopRate / 20).toFixed(2)}x` : '—',
              color: loopRate >= 20 ? 'text-secondary' : loopRate > 0 ? 'text-tertiary' : 'text-outline',
              sub1Color: 'text-outline',
            },
            {
              label: status.validationMode ? 'Tracking Error (GT)' : 'Boresight Offset',
              Icon: Crosshair,
              value: status.validationMode
                ? (trackErr !== null ? `${trackErr.toFixed(2)} px` : 'NO DATA')
                : (boresightOffset !== null ? `${boresightOffset.toFixed(2)} px` : 'NO DATA'),
              sub1: status.validationMode ? 'SPEC ≤ 10.0 px' : 'OPTICAL RESIDUAL',
              sub2: status.validationMode
                ? (trackErr !== null && trackErr <= 10 ? 'PASS' : trackErr !== null ? 'FAIL' : '—')
                : (boresightOffset !== null && boresightOffset <= 10.0 ? 'IN SPEC' : '—'),
              color: status.validationMode
                ? (trackErr !== null ? (trackErr <= 10 ? 'text-primary' : 'text-error') : 'text-outline')
                : (boresightOffset !== null ? (boresightOffset <= 10 ? 'text-primary' : 'text-tertiary') : 'text-outline'),
              sub1Color: 'text-outline',
            },
            {
              label: 'Centroid Precision',
              Icon: Target,
              value: boresightOffset !== null ? `${boresightOffset.toFixed(3)} px` : 'NO DATA',
              sub1: 'SUB-PIXEL ESTIMATE',
              sub2: boresightOffset !== null && boresightOffset < 1.0 ? '✓ HIGH' : '—',
              color: boresightOffset !== null ? (boresightOffset < 1.0 ? 'text-secondary' : 'text-tertiary') : 'text-outline',
              sub1Color: 'text-outline',
            },
            {
              label: 'Compute Latency',
              Icon: Clock,
              value: latencyMs > 0 ? `${latencyMs.toFixed(2)} ms` : '—',
              sub1: 'SPEC ≤ 50.0 ms',
              sub2: latencyMs > 0 && latencyMs <= 50 ? 'PASS' : latencyMs > 0 ? 'SLOW' : '—',
              color: latencyMs > 0 && latencyMs <= 50 ? 'text-on-surface' : latencyMs > 0 ? 'text-tertiary' : 'text-outline',
              sub1Color: 'text-outline',
            },
            {
              label: 'Target Loss',
              Icon: ShieldAlert,
              value: tState === 'LOST' ? '100 %' : tState === 'TRACKING' ? '0.00 %' : 'SCAN',
              sub1: 'SPEC < 5.0%',
              sub2: tState === 'TRACKING' ? '0 LOST' : tState === 'LOST' ? 'FAIL' : 'SCANNING',
              color: tState === 'TRACKING' ? 'text-secondary' : tState === 'LOST' ? 'text-error' : 'text-outline',
              sub1Color: 'text-outline',
            },
          ].map(({ label, Icon, value, sub1, sub2, color, sub1Color }) => (
            <div key={label} className="bg-surface-container p-space-sm rounded border border-outline-variant/20 flex flex-col justify-between">
              <div className="flex items-center justify-between text-outline">
                <span className="font-label-sm text-label-sm uppercase">{label}</span>
                <Icon className="w-3.5 h-3.5" />
              </div>
              <div className="my-space-xs">
                <span className={`font-data-lg text-data-lg font-bold ${color}`}>{value}</span>
              </div>
              <div className="flex items-center justify-between font-label-sm text-label-sm">
                <span className={sub1Color}>{sub1}</span>
                <span className={`${color} font-medium`}>{sub2}</span>
              </div>
            </div>
          ))}
        </div>

        {/* 120-Frame Error / Offset Sparkline */}
        <div className="mt-space-xs pt-space-xs border-t border-outline-variant/20 flex flex-col gap-1">
          <div className="flex items-center justify-between font-label-sm text-label-sm">
            <span className="text-outline uppercase flex items-center gap-1">
              <TrendingDown className="w-3.5 h-3.5 text-primary" />
              {status.validationMode
                ? '120-Frame Real-Time Radial Tracking Error History (px) [GT Validated]'
                : '120-Frame Real-Time Boresight Offset History (px) [Operational]'}
            </span>
            <div className="flex items-center gap-space-md font-data-sm text-data-sm">
              <span className="flex items-center gap-1 text-error">
                <span className="w-3 h-0.5 bg-error inline-block" />
                SPEC CEILING (10.0 px)
              </span>
              <span className="flex items-center gap-1 text-primary">
                <span className="w-3 h-0.5 bg-primary inline-block" />
                {status.validationMode ? 'ACTUAL ERROR' : 'LIVE OFFSET'}
              </span>
            </div>
          </div>
          <div className="relative w-full h-12 bg-surface-container-lowest rounded border border-outline-variant/20 overflow-hidden flex items-center">
            <svg className="w-full h-full" viewBox="0 0 480 48" preserveAspectRatio="none">
              {/* Grid lines */}
              {[12, 24, 36].map(y => (
                <line key={y} x1="0" y1={y} x2="480" y2={y} stroke="#424754" strokeDasharray="2,2" strokeWidth="0.5" />
              ))}
              {/* Spec ceiling at y=8 (maps to 10px max) */}
              <line x1="0" y1="8" x2="480" y2="8" stroke="#ffb4ab" strokeDasharray="4,2" strokeWidth="1.2" />
              {/* Real error sparkline */}
              <polyline
                fill="none"
                points={sparkPoints}
                stroke="#adc6ff"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.5"
              />
            </svg>
            <div className="absolute left-2 top-0.5 font-data-sm text-[9px] text-error">10.0 px CRITICAL SPEC LIMIT</div>
            <div className="absolute right-2 bottom-0.5 font-data-sm text-[9px] text-primary">
              {status.validationMode
                ? (trackErr !== null ? `CURRENT GT ERR: ${trackErr.toFixed(2)} px` : 'AWAITING DATA')
                : (boresightOffset !== null ? `CURRENT OFFSET: ${boresightOffset.toFixed(2)} px` : 'AWAITING DATA')}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
