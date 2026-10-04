import React, { useState, useEffect } from 'react'
import {
  Video,
  Box,
  Grid,
  ArrowUpRight,
  Lock,
} from 'lucide-react'
import { useSanketStore } from '../../store/useSanketStore'
import { bridgeService } from '../../services/bridgeService'
import { DeveloperControlSidebar } from './DeveloperControlSidebar'
import type { TrajectoryPattern, AtmCondition } from './DeveloperControlSidebar'
import { DeveloperBottomHorizon } from './DeveloperBottomHorizon'
import { TrackingErrorChartCard } from './TrackingErrorChartCard'

// ─────────────────────────────────────────────────────────────
// Screen 3: SANKET — Developer Workspace (2000×2000 World Canvas)
// Full Bird's-Eye View with High-Fidelity 2000x2000 Planar Space
// ─────────────────────────────────────────────────────────────

export const WorldCanvasView: React.FC = () => {
  const telemetry = useSanketStore((s) => s.telemetry)
  const status = useSanketStore((s) => s.status)
  const setActiveTab = useSanketStore((s) => s.setActiveDeveloperTab)

  // Top Mode Bar Toggles & Zoom
  const [worldZoom, setWorldZoom] = useState<'fit' | '0.5x' | '1.0x' | '2.0x'>('fit')
  const [canvasGrid, setCanvasGrid] = useState<boolean>(true)
  const [showEnvelope, setShowEnvelope] = useState<boolean>(true)
  const [showFovOverlay, setShowFovOverlay] = useState<boolean>(true)
  const [trajTrail, setTrajTrail] = useState<boolean>(true)

  // Interactive cursor tracking in world coordinates (0..2000, 0..2000)
  const [cursorPos, setCursorPos] = useState({ x: 1000.0, y: 1000.0 })

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = Math.max(0, Math.min(2000, Math.round(((e.clientX - rect.left) / rect.width) * 2000)))
    const y = Math.max(0, Math.min(2000, Math.round(((e.clientY - rect.top) / rect.height) * 2000)))
    setCursorPos({ x, y })
  }

  // Sidebar parameters & controls state
  const [pattern, setPattern] = useState<TrajectoryPattern>('linear')
  const [slewSpeed, setSlewSpeed] = useState<number>(45.0)
  const [atmCondition, setAtmCondition] = useState<AtmCondition>('clear')
  const [gaussianNoise, setGaussianNoise] = useState<boolean>(false)
  const [poissonNoise, setPoissonNoise] = useState<boolean>(false)
  const [saltPepperNoise, setSaltPepperNoise] = useState<boolean>(false)
  const [kp, setKp] = useState<number>(8.0)
  const [ki, setKi] = useState<number>(2.0)
  const [deadband, setDeadband] = useState<number>(1.0)
  const [appliedNotice, setAppliedNotice] = useState<boolean>(false)

  // Metric buffers
  const [errorHistory, setErrorHistory] = useState<number[]>([])
  const [lostFramesCount, setLostFramesCount] = useState<number>(0)
  const [totalFramesCount, setTotalFramesCount] = useState<number>(0)

  // Sync active scenario config from backend
  useEffect(() => {
    if (status.activeScenarioConfig) {
      const cfg = status.activeScenarioConfig
      if (cfg.pattern) setPattern(cfg.pattern as TrajectoryPattern)
      if (cfg.speed !== undefined) setSlewSpeed(cfg.speed)
      if (cfg.condition) setAtmCondition(cfg.condition as AtmCondition)
      if (cfg.gaussian !== undefined) setGaussianNoise(cfg.gaussian)
      if (cfg.poisson !== undefined) setPoissonNoise(cfg.poisson)
      if (cfg.saltPepper !== undefined) setSaltPepperNoise(cfg.saltPepper)
      if (cfg.kp !== undefined) setKp(cfg.kp)
      if (cfg.ki !== undefined) setKi(cfg.ki)
      if (cfg.deadband !== undefined) setDeadband(cfg.deadband)
    }
  }, [status.activeScenarioConfig])

  const radialErr = status.isRunning
    ? (telemetry.boresightOffsetPx ?? telemetry.trackingErrorPx ?? 0.0)
    : 0.0
  const loopRate = (
    status.isRunning
      ? status.backendFps > 0
        ? status.backendFps
        : telemetry.algorithmFps > 0
        ? telemetry.algorithmFps
        : 30.0
      : 0.0
  ).toFixed(1)
  const frameNum = status.isRunning ? (telemetry.frameNumber || status.currentFrame) : 0

  useEffect(() => {
    if (status.isRunning) {
      setErrorHistory((prev) => {
        const next = [...prev, radialErr]
        if (next.length > 40) next.shift()
        return next
      })
      setTotalFramesCount((c) => c + 1)
      if (telemetry.trackingState === 'LOST') {
        setLostFramesCount((c) => c + 1)
      }
    } else {
      if (errorHistory.length > 0) setErrorHistory([])
      if (lostFramesCount > 0) setLostFramesCount(0)
      if (totalFramesCount > 0) setTotalFramesCount(0)
    }
  }, [telemetry.frameNumber, status.isRunning])

  const centroidRmse = status.isRunning && errorHistory.length > 0
    ? Math.sqrt(errorHistory.reduce((acc, v) => acc + v * v, 0) / errorHistory.length).toFixed(3)
    : '0.000'
  const acqLatency = status.isRunning
    ? (telemetry.processingLatencyMs > 0 ? (telemetry.processingLatencyMs / 1000).toFixed(3) : '0.033')
    : '0.000'
  const targetLossRate = totalFramesCount > 0
    ? ((lostFramesCount / totalFramesCount) * 100).toFixed(1)
    : '0.00'

  const handleApplyGains = () => {
    bridgeService.setPtzGains(kp, ki, deadband)
    setAppliedNotice(true)
    setTimeout(() => setAppliedNotice(false), 2000)
  }

  // Camera geometry constants (2000x2000 scene canvas, 640x480 viewport)
  // Optical Ground Station (OGS-BLR) center origin at (1000, 1000)
  const SCENE_CENTER_X = 1000.0
  const SCENE_CENTER_Y = 1000.0
  const PX_PER_DEG_H = 160.0 // 640 px / 4.0 deg
  const PX_PER_DEG_V = 160.0 // 480 px / 3.0 deg

  const pan = telemetry.panAngleDeg ?? 0.0
  const tilt = telemetry.tiltAngleDeg ?? 0.0
  const camWorldX = SCENE_CENTER_X + pan * PX_PER_DEG_H
  const camWorldY = SCENE_CENTER_Y + tilt * PX_PER_DEG_V

  // FPA Viewport (640x480) footprint upper-left corner
  const fpaX = camWorldX - 320
  const fpaY = camWorldY - 240

  const hasCentroid = Boolean(
    status.isRunning &&
    telemetry.centroid?.x !== null && telemetry.centroid?.x !== undefined &&
    telemetry.centroid?.y !== null && telemetry.centroid?.y !== undefined
  )
  const hasTarget = hasCentroid
  const deltaX = hasCentroid ? (telemetry.centroid.x! - 320.0) : 0.0
  const deltaY = hasCentroid ? (telemetry.centroid.y! - 240.0) : 0.0

  const tgtWorldX = camWorldX + deltaX
  const tgtWorldY = camWorldY + deltaY

  // Velocity vector arrow direction in world space
  const velHeadingDeg = 35 - pan * 0.5
  const velHeadingRad = (velHeadingDeg * Math.PI) / 180
  const velLen = 65
  const velVecX = Math.cos(velHeadingRad) * velLen
  const velVecY = Math.sin(velHeadingRad) * velLen

  // 100-point FIFO buffer for real dynamic trajectory trail in world space
  const [trajectoryTrail, setTrajectoryTrail] = useState<{ x: number; y: number }[]>([])

  useEffect(() => {
    if (status.isRunning && hasCentroid) {
      setTrajectoryTrail((prev) => {
        const next = [...prev, { x: tgtWorldX, y: tgtWorldY }]
        if (next.length > 100) next.shift()
        return next
      })
    } else if (!status.isRunning) {
      if (trajectoryTrail.length > 0) setTrajectoryTrail([])
    }
  }, [telemetry.frameNumber, status.isRunning, hasCentroid, tgtWorldX, tgtWorldY])

  return (
    <div className="flex flex-col w-full bg-surface text-on-surface">
      {/* ── Sub-Navigation / Local Viewport Selector Strip ── */}
      <div className="w-full bg-surface-container-low px-space-md py-space-xs flex flex-wrap items-center justify-between gap-space-sm shadow-sm select-none border-b border-outline-variant/30">
        <div className="flex items-center gap-space-sm">
          <div className="flex items-center bg-surface-container-lowest p-0.5 rounded border border-outline-variant/60">
            {/* Tab 1: 2D Sensor View */}
            <button
              type="button"
              onClick={() => setActiveTab('2d')}
              className="text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Video className="w-3.5 h-3.5 text-outline" />
              <span>◉ 2D Sensor View (640×480)</span>
            </button>

            {/* Tab 2: 3D Pedestal Frustum */}
            <button
              type="button"
              onClick={() => setActiveTab('3d')}
              className="text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Box className="w-3.5 h-3.5 text-outline" />
              <span>⬡ 3D Pedestal Frustum</span>
            </button>

            {/* Tab 3: 2000×2000 World Canvas */}
            <button
              type="button"
              onClick={() => setActiveTab('world')}
              className="bg-surface-container-high text-primary px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1.5 font-bold shadow-sm border border-primary/40 cursor-pointer"
            >
              <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse" />
              <Grid className="w-3.5 h-3.5 text-primary" />
              <span>2000×2000 World Canvas</span>
              <span className="bg-primary text-on-primary text-[9px] px-1 py-0.2 rounded font-mono font-semibold">
                ACTIVE
              </span>
            </button>
          </div>

          <span className="text-outline-variant font-label-sm mx-1">|</span>

          {/* Zoom Switchers */}
          <div className="flex items-center gap-1 bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant/40">
            <span className="text-outline font-label-sm text-[10px]">ZOOM:</span>
            {(['fit', '0.5x', '1.0x', '2.0x'] as const).map((z) => (
              <button
                key={z}
                type="button"
                onClick={() => setWorldZoom(z)}
                className={`font-label-sm text-[10px] px-1.5 py-0.5 font-semibold rounded cursor-pointer ${
                  worldZoom === z ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {z === 'fit' ? 'FIT' : z}
              </button>
            ))}
          </div>
        </div>

        {/* Viewport World Element Toggles */}
        <div className="flex items-center gap-space-md font-label-sm text-[11px]">
          <label className="flex items-center gap-1 cursor-pointer text-on-surface">
            <input
              type="checkbox"
              checked={canvasGrid}
              onChange={(e) => setCanvasGrid(e.target.checked)}
              className="w-3.5 h-3.5 accent-primary bg-surface-container-lowest rounded-sm cursor-pointer"
            />
            <span className="font-semibold">Grid (100px)</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer text-secondary">
            <input
              type="checkbox"
              checked={showEnvelope}
              onChange={(e) => setShowEnvelope(e.target.checked)}
              className="w-3.5 h-3.5 accent-secondary bg-surface-container-lowest rounded-sm cursor-pointer"
            />
            <span className="font-semibold">Uncertainty Env (R=460px)</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer text-primary">
            <input
              type="checkbox"
              checked={showFovOverlay}
              onChange={(e) => setShowFovOverlay(e.target.checked)}
              className="w-3.5 h-3.5 accent-primary bg-surface-container-lowest rounded-sm cursor-pointer"
            />
            <span className="font-semibold">FOV Footprint (640×480)</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer text-tertiary">
            <input
              type="checkbox"
              checked={trajTrail}
              onChange={(e) => setTrajTrail(e.target.checked)}
              className="w-3.5 h-3.5 accent-tertiary bg-surface-container-lowest rounded-sm cursor-pointer"
            />
            <span className="font-semibold">Trajectory Trail</span>
          </label>

          <div className="h-4 w-px bg-outline-variant" />

          {/* Firewall Badge */}
          <div className="font-label-sm text-[11px] text-tertiary flex items-center gap-1 bg-surface-container-lowest px-2 py-0.5 rounded border border-tertiary/30 font-semibold">
            <Lock className="w-3 h-3 text-tertiary" />
            <span>LIVE OPERATIONAL: WORLD GT STRIPPED</span>
          </div>
        </div>
      </div>

      {/* ── Primary Workspace Content Grid ── */}
      <div className="p-space-sm grid grid-cols-1 lg:grid-cols-12 gap-gutter items-stretch">
        {/* Central 2000x2000 Canvas Column (~65% -> 8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-gutter">
          <div className="bg-surface-container-lowest rounded overflow-hidden shadow-md flex flex-col relative select-none border border-outline-variant/40">
            {/* Top Metric Ribbon */}
            <div className="bg-surface-container-low px-space-md py-1 flex items-center justify-between font-label-sm text-[11px] border-b border-outline-variant/40">
              <div className="flex items-center gap-space-sm font-mono flex-wrap">
                <div className="flex items-center gap-1 bg-surface-container-lowest text-tertiary px-2 py-0.5 rounded border border-tertiary/40 font-bold text-[10px] tracking-wide">
                  <span className={`w-1.5 h-1.5 rounded-full ${status.isRunning ? 'bg-tertiary animate-pulse' : 'bg-outline'}`} />
                  <span>
                    {status.isRunning ? 'GLOBAL WCS TRACKING' : 'WCS STANDBY'}
                  </span>
                </div>
                <span className="text-outline-variant">|</span>
                <div className="flex items-center gap-1">
                  <span className="text-outline">TARGET WCS:</span>
                  <span className="text-primary font-bold">
                    {hasTarget ? `[${tgtWorldX.toFixed(0)}, ${tgtWorldY.toFixed(0)}] px` : '[---, ---]'}
                  </span>
                </div>
                <span className="text-outline-variant">|</span>
                <div className="flex items-center gap-1">
                  <span className="text-outline">CAM BORESIGHT:</span>
                  <span className="text-secondary font-semibold">
                    [{camWorldX.toFixed(0)}, {camWorldY.toFixed(0)}] px
                  </span>
                </div>
                <span className="text-outline-variant">|</span>
                <div className="flex items-center gap-1">
                  <span className="text-outline">RADIAL ERR:</span>
                  <span className={`font-bold ${radialErr <= 10.0 ? 'text-tertiary' : 'text-error'}`}>
                    {radialErr.toFixed(3)} px
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-space-sm font-mono text-[10px] text-outline shrink-0">
                <span className="bg-surface-container-high px-1.5 py-0.5 rounded text-secondary font-semibold">
                  2000×2000 SCENE
                </span>
                <span>OGS-BLR</span>
              </div>
            </div>

            {/* Scalable Bird's-Eye Viewport Container (Item 5) */}
            <div
              className="relative w-full h-[580px] bg-[#070b0e] overflow-hidden flex items-center justify-center select-none cursor-crosshair"
              onMouseMove={handleCanvasMouseMove}
            >
              <div
                className="relative w-full h-full flex items-center justify-center transition-transform duration-200 origin-center"
                style={{
                  transform:
                    worldZoom === '0.5x'
                      ? 'scale(0.5)'
                      : worldZoom === '2.0x'
                      ? 'scale(1.4)'
                      : worldZoom === 'fit'
                      ? 'scale(0.92)'
                      : 'scale(1.0)',
                }}
              >
                <svg
                  className="absolute inset-0 w-full h-full pointer-events-none"
                  viewBox="0 0 2000 2000"
                  preserveAspectRatio="xMidYMid meet"
                >
                  <defs>
                    <pattern height="100" id="world-grid-100" patternUnits="userSpaceOnUse" width="100">
                      <path d="M 100 0 L 0 0 0 100" fill="none" stroke="#424754" strokeOpacity="0.45" strokeWidth="0.6" />
                    </pattern>
                    <pattern height="500" id="world-grid-500" patternUnits="userSpaceOnUse" width="500">
                      <rect fill="url(#world-grid-100)" height="500" width="500" />
                      <path d="M 500 0 L 0 0 0 500" fill="none" stroke="#8c909f" strokeOpacity="0.35" strokeWidth="1.2" />
                    </pattern>
                    <radialGradient cx="48%" cy="46%" id="fogHazeGrad" r="32%">
                      <stop offset="0%" stopColor="#ca8100" stopOpacity="0.18" />
                      <stop offset="60%" stopColor="#ca8100" stopOpacity="0.06" />
                      <stop offset="100%" stopColor="#ca8100" stopOpacity="0" />
                    </radialGradient>
                    <radialGradient cx="50%" cy="50%" id="spotPSFGrad" r="50%">
                      <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
                      <stop offset="30%" stopColor="#4edea3" stopOpacity="0.8" />
                      <stop offset="70%" stopColor="#4edea3" stopOpacity="0.2" />
                      <stop offset="100%" stopColor="#4edea3" stopOpacity="0" />
                    </radialGradient>
                  </defs>

                  {/* Background 2000x2000 Grid */}
                  <rect fill={canvasGrid ? 'url(#world-grid-500)' : '#070b0e'} height="2000" width="2000" />

                  {/* Atmospheric Perturbation Overlays */}
                  {atmCondition === 'fog' && (
                    <g>
                      <circle cx="960" cy="920" fill="url(#fogHazeGrad)" r="380" />
                      <text fill="#ca8100" fontFamily="JetBrains Mono" fontSize="22" fontWeight="500" opacity="0.8" x="680" y="880">
                        [FOG INTERSECT QUADRANT II (r0: 0.08)]
                      </text>
                    </g>
                  )}
                  {atmCondition === 'rain' && (
                    <g>
                      <circle cx="1000" cy="1000" fill="rgba(77, 142, 255, 0.08)" r="480" />
                      <text fill="#4d8eff" fontFamily="JetBrains Mono" fontSize="22" fontWeight="500" opacity="0.8" x="720" y="880">
                        [RAIN ATTENUATION: 3.8 dB/km (4.2 mm/hr)]
                      </text>
                    </g>
                  )}
                  {atmCondition === 'haze' && (
                    <g>
                      <circle cx="1000" cy="1000" fill="rgba(255, 185, 95, 0.06)" r="420" />
                      <text fill="#ffb95f" fontFamily="JetBrains Mono" fontSize="22" fontWeight="500" opacity="0.8" x="740" y="880">
                        [OPTICAL HAZE SCATTERING: MODERATE]
                      </text>
                    </g>
                  )}

                  {/* Center Datum Zero Crosshair Axes */}
                  <line stroke="#8c909f" strokeDasharray="6,6" strokeOpacity="0.4" strokeWidth="1.2" x1="1000" x2="1000" y1="0" y2="2000" />
                  <line stroke="#8c909f" strokeDasharray="6,6" strokeOpacity="0.4" strokeWidth="1.2" x1="0" x2="2000" y1="1000" y2="1000" />

                  {/* Coordinate Axis Ticks & Labels */}
                  <g fill="#8c909f" fontFamily="JetBrains Mono" fontSize="24" opacity="0.5">
                    <text x="205" y="1025">X:200</text>
                    <text x="405" y="1025">X:400</text>
                    <text x="605" y="1025">X:600</text>
                    <text x="805" y="1025">X:800</text>
                    <text fill="#adc6ff" fontWeight="bold" x="1010" y="1025">1000 [CTR]</text>
                    <text x="1205" y="1025">X:1200</text>
                    <text x="1405" y="1025">X:1400</text>
                    <text x="1605" y="1025">X:1600</text>
                    <text x="1805" y="1025">X:1800</text>
                    <text x="1015" y="215">Y:200</text>
                    <text x="1015" y="415">Y:415</text>
                    <text x="1015" y="615">Y:600</text>
                    <text x="1015" y="815">Y:800</text>
                    <text x="1015" y="1215">Y:1200</text>
                    <text x="1015" y="1415">Y:1400</text>
                    <text x="1015" y="1615">Y:1600</text>
                    <text x="1015" y="1815">Y:1800</text>
                  </g>

                  {/* Optical Ground Station Central Origin Datum */}
                  <g transform="translate(1000, 1000)">
                    <circle r="7" fill="#0284c7" />
                    <circle r="22" fill="none" stroke="#0284c7" strokeWidth="1.2" strokeDasharray="5,4" />
                    <text x="16" y="-10" fill="#93ccff" fontFamily="JetBrains Mono" fontSize="20" fontWeight="bold">
                      OGS-BLR ORIGIN (1000, 1000)
                    </text>
                  </g>

                  {/* Uncertainty Envelope (R=460px | Acq <= 2.0s) */}
                  {showEnvelope && (
                    <g id="uncertainty-envelope">
                      <circle cx="1000" cy="1000" fill="rgba(202, 129, 0, 0.04)" opacity="0.75" r="460" stroke="#ffb95f" strokeDasharray="8,6" strokeWidth="2.5" />
                      <circle cx="1000" cy="1000" fill="#ffb95f" r="4" />
                      <text fill="#ffb95f" fontFamily="JetBrains Mono" fontSize="26" fontWeight="bold" letterSpacing="1" x="1015" y="565">
                        UNCERTAINTY ENVELOPE (R=460px | Acq ≤ 2.0s)
                      </text>
                      <g opacity="0.6" stroke="#ffb95f" strokeWidth="1">
                        <line strokeDasharray="4,3" x1="1000" x2="1325" y1="1000" y2="675" />
                        <circle cx="1325" cy="675" fill="#ffb95f" r="5" />
                        <text fill="#ffddb8" fontFamily="JetBrains Mono" fontSize="22" x="1335" y="670">
                          Radius 460.0 px (3σ Max Bounds)
                        </text>
                      </g>
                    </g>
                  )}

                  {/* Dynamic Target Trajectory Trail in World Space */}
                  {trajTrail && trajectoryTrail.length >= 2 && (
                    <g id="world-trajectory-trail">
                      <polyline
                        points={trajectoryTrail.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')}
                        fill="none"
                        opacity="0.6"
                        stroke="#f59e0b"
                        strokeDasharray="6,4"
                        strokeWidth="3"
                      />
                      {trajectoryTrail.slice(-15).map((pt, idx) => (
                        <circle
                          key={idx}
                          cx={pt.x}
                          cy={pt.y}
                          fill="#fbbf24"
                          opacity={0.3 + (idx / 15) * 0.7}
                          r={4 + (idx / 15) * 3}
                        />
                      ))}
                    </g>
                  )}

                  {/* Camera FPA Viewport (640×480 px) Ground Projection Footprint */}
                  {showFovOverlay && (
                    <g id="fpa-viewport-footprint">
                      <rect
                        fill="rgba(77, 142, 255, 0.06)"
                        height="480"
                        rx="4"
                        stroke="#4d8eff"
                        strokeWidth="2.5"
                        width="640"
                        x={fpaX}
                        y={fpaY}
                      />
                      {/* Corner Brackets */}
                      <g stroke="#adc6ff" strokeWidth="4">
                        <line x1={fpaX} x2={fpaX + 40} y1={fpaY} y2={fpaY} />
                        <line x1={fpaX + 2} x2={fpaX + 2} y1={fpaY - 2} y2={fpaY + 38} />
                        <line x1={fpaX + 640} x2={fpaX + 600} y1={fpaY} y2={fpaY} />
                        <line x1={fpaX + 638} x2={fpaX + 638} y1={fpaY - 2} y2={fpaY + 38} />
                        <line x1={fpaX} x2={fpaX + 40} y1={fpaY + 480} y2={fpaY + 480} />
                        <line x1={fpaX + 2} x2={fpaX + 2} y1={fpaY + 482} y2={fpaY + 442} />
                        <line x1={fpaX + 640} x2={fpaX + 600} y1={fpaY + 480} y2={fpaY + 480} />
                        <line x1={fpaX + 638} x2={fpaX + 638} y1={fpaY + 482} y2={fpaY + 442} />
                      </g>
                      {/* Footprint Header Label */}
                      <text fill="#adc6ff" fontFamily="JetBrains Mono" fontSize="24" fontWeight="bold" x={fpaX + 14} y={fpaY + 31}>
                        FPA VIEWPORT [640×480 px] CTR: ({camWorldX.toFixed(0)}, {camWorldY.toFixed(0)})
                      </text>
                      {/* Boresight Crosshair Axes */}
                      <line
                        stroke="#4d8eff"
                        strokeDasharray="4,4"
                        strokeOpacity="0.4"
                        strokeWidth="1.5"
                        x1={camWorldX}
                        x2={camWorldX}
                        y1={fpaY}
                        y2={fpaY + 480}
                      />
                      <line
                        stroke="#4d8eff"
                        strokeDasharray="4,4"
                        strokeOpacity="0.4"
                        strokeWidth="1.5"
                        x1={fpaX}
                        x2={fpaX + 640}
                        y1={camWorldY}
                        y2={camWorldY}
                      />
                    </g>
                  )}

                  {/* Target Beacon Spot & Heading Vector in World Space */}
                  {hasTarget && (
                    <g id="beacon-target-world">
                      <circle cx={tgtWorldX} cy={tgtWorldY} fill="url(#spotPSFGrad)" r="32" />
                      <circle cx={tgtWorldX} cy={tgtWorldY} fill="#ffffff" r="5" />
                      {/* Heading / Slew Vector */}
                      <line
                        stroke="#ffb95f"
                        strokeLinecap="round"
                        strokeWidth="3.5"
                        x1={tgtWorldX}
                        x2={tgtWorldX + velVecX}
                        y1={tgtWorldY}
                        y2={tgtWorldY + velVecY}
                      />
                      <polygon
                        fill="#ffb95f"
                        points={`${tgtWorldX + velVecX},${tgtWorldY + velVecY} ${tgtWorldX + velVecX - 14},${tgtWorldY + velVecY - 9} ${tgtWorldX + velVecX - 9},${tgtWorldY + velVecY + 9}`}
                      />
                      <text fill="#4edea3" fontFamily="JetBrains Mono" fontSize="24" fontWeight="bold" x={tgtWorldX + 22} y={tgtWorldY - 26}>
                        {status.validationMode ? 'BEACON [GT VALIDATION]' : 'BEACON [850nm]'} ({tgtWorldX.toFixed(0)}, {tgtWorldY.toFixed(0)})
                      </text>
                    </g>
                  )}

                  <rect x="2" y="2" width="1996" height="1996" fill="none" stroke="#1d2632" strokeWidth="2.5" />
                </svg>
              </div>

              {/* Top-Left HUD Overlay (Item 5: Restored Bird's-Eye HUD) */}
              <div className="absolute top-3 left-3 flex flex-col gap-1 p-space-sm bg-surface-container-lowest/90 border border-outline-variant/30 rounded font-data-sm text-data-sm pointer-events-none select-none z-20 shadow-lg">
                <div className="flex items-center gap-space-sm">
                  <span className="text-primary font-medium flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                    CANVAS_WORLD // SIM_ENGINE [CALIBRATED]
                  </span>
                </div>
                <div className="flex items-center gap-space-sm text-[11px] text-tertiary font-mono font-semibold">
                  <span>LIVE OPERATIONAL: WORLD GT STRIPPED</span>
                </div>
                <div className="flex items-center gap-space-sm text-[11px]">
                  <span className="text-outline">WORLD DIMS:</span>
                  <span className="text-on-surface font-mono">2000 × 2000 px (4,000,000 px²)</span>
                </div>
                <div className="flex items-center gap-space-sm text-[11px]">
                  <span className="text-outline">ORIGIN:</span>
                  <span className="text-on-surface font-medium font-mono">(1000.0, 1000.0) [DATUM ZERO]</span>
                </div>
                <div className="flex items-center gap-space-sm text-[11px]">
                  <span className="text-outline">CURSOR POS:</span>
                  <span className="text-secondary font-medium font-mono">
                    X: {cursorPos.x.toFixed(1)}, Y: {cursorPos.y.toFixed(1)}
                  </span>
                </div>
              </div>
            </div>

            {/* Viewport Bottom Configuration Bar */}
            <div className="bg-surface-container-low px-space-md py-1.5 flex flex-wrap items-center justify-between font-label-sm text-[11px] text-on-surface-variant border-t border-outline-variant/30">
              <div className="flex items-center gap-space-md">
                <span>
                  WORLD RESOLUTION: <strong className="text-on-surface font-mono">2000 × 2000 px</strong>
                </span>
                <span className="text-outline-variant">|</span>
                <span>
                  STATION COORDS: <strong className="text-on-surface font-mono">12.97° N, 77.59° E</strong>
                </span>
                <span className="text-outline-variant">|</span>
                <span>
                  ACQ BOUNDARY: <strong className="text-tertiary font-mono">R=460 px (2.0s)</strong>
                </span>
              </div>
              <div className="flex items-center gap-space-md">
                <span>
                  ANGULAR SCALE: <strong className="text-secondary font-mono">160.0 px/deg</strong>
                </span>
              </div>
            </div>
          </div>

          {/* Synchronized PIP Cards: 2D Sensor View & 3D Pedestal Frustum (Item 7) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
            {/* PIP 1: 2D Sensor View */}
            <div className="bg-surface-container-low rounded p-space-sm shadow-sm flex flex-col justify-between border border-outline-variant/40">
              <div className="flex items-center justify-between pb-space-xs mb-space-xs border-b border-outline-variant/30">
                <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-on-surface">
                  <Video className="w-3.5 h-3.5 text-primary" />
                  <span className="font-semibold uppercase tracking-wider text-[11px]">
                    2D Sensor View (640×480)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('2d')}
                  className="bg-surface-container text-secondary hover:text-primary hover:bg-surface-container-high px-2 py-0.5 rounded font-label-sm text-[10px] font-semibold flex items-center gap-1 border border-outline-variant/60 transition-colors cursor-pointer"
                >
                  <span>SWITCH TO VIEW</span>
                  <ArrowUpRight className="w-3 h-3" />
                </button>
              </div>
              <div className="bg-surface-container-lowest rounded h-28 relative overflow-hidden flex items-center justify-center border border-outline-variant/30 select-none">
                <svg className="w-full h-full" viewBox="0 0 320 110" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <radialGradient cx="50%" cy="50%" id="miniPipFpaWorld" r="50%">
                      <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
                      <stop offset="30%" stopColor="#4edea3" stopOpacity="0.85" />
                      <stop offset="70%" stopColor="#0284c7" stopOpacity="0.3" />
                      <stop offset="100%" stopColor="#0284c7" stopOpacity="0" />
                    </radialGradient>
                  </defs>
                  {/* Grid Lines */}
                  <g stroke="#1a232c" strokeWidth="0.8" strokeDasharray="3,3">
                    <line x1="80" y1="0" x2="80" y2="110" />
                    <line x1="160" y1="0" x2="160" y2="110" />
                    <line x1="240" y1="0" x2="240" y2="110" />
                    <line x1="0" y1="28" x2="320" y2="28" />
                    <line x1="0" y1="55" x2="320" y2="55" />
                    <line x1="0" y1="82" x2="320" y2="82" />
                  </g>
                  {/* Boresight Crosshair & Reticle Circles */}
                  <circle cx="160" cy="55" r="25" fill="none" stroke="#253241" strokeWidth="1" strokeDasharray="2,2" />
                  <circle cx="160" cy="55" r="45" fill="none" stroke="#1e293b" strokeWidth="0.8" />
                  <line x1="150" y1="55" x2="170" y2="55" stroke="#4cd7f6" strokeWidth="1.2" />
                  <line x1="160" y1="45" x2="160" y2="65" stroke="#4cd7f6" strokeWidth="1.2" />
                  {/* Dynamic Centroid Marker */}
                  {(() => {
                    const spotX = telemetry.centroid?.x !== null && telemetry.centroid?.x !== undefined
                      ? 160 + ((telemetry.centroid.x - 320) / 320) * 120
                      : 160
                    const spotY = telemetry.centroid?.y !== null && telemetry.centroid?.y !== undefined
                      ? 55 + ((telemetry.centroid.y - 240) / 240) * 45
                      : 55
                    return (
                      <g>
                        <circle cx={spotX} cy={spotY} r="12" fill="url(#miniPipFpaWorld)" />
                        <circle cx={spotX} cy={spotY} r="2.5" fill="#ffffff" />
                        <rect x={spotX - 8} y={spotY - 8} width="16" height="16" fill="none" stroke="#4edea3" strokeWidth="1" />
                        <text x={spotX + 11} y={spotY - 4} fill="#4edea3" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold">
                          {status.isRunning ? 'LOCKED' : 'STANDBY'}
                        </text>
                      </g>
                    )
                  })()}
                  <text x="8" y="14" fill="#8c909f" fontFamily="JetBrains Mono" fontSize="8">
                    FPA 640×480 @ 8-bit
                  </text>
                  <text x="8" y="104" fill="#4cd7f6" fontFamily="JetBrains Mono" fontSize="8">
                    ΔR: {radialErr.toFixed(2)} px
                  </text>
                  <text x="245" y="104" fill="#ffb95f" fontFamily="JetBrains Mono" fontSize="8">
                    SNR: 34.2 dB
                  </text>
                </svg>
              </div>
              <div className="mt-space-xs pt-space-xs flex items-center justify-between font-label-sm text-[10px] text-on-surface-variant font-mono">
                <span>FORMAT: 640×480 8-bit Mono</span>
                <span>RATE: 30.0 FPS</span>
              </div>
            </div>

            {/* PIP 2: 3D Pedestal Frustum */}
            <div className="bg-surface-container-low rounded p-space-sm shadow-sm flex flex-col justify-between border border-outline-variant/40">
              <div className="flex items-center justify-between pb-space-xs mb-space-xs border-b border-outline-variant/30">
                <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-on-surface">
                  <Box className="w-3.5 h-3.5 text-primary" />
                  <span className="font-semibold uppercase tracking-wider text-[11px]">
                    3D Pedestal Frustum
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('3d')}
                  className="bg-surface-container text-secondary hover:text-primary hover:bg-surface-container-high px-2 py-0.5 rounded font-label-sm text-[10px] font-semibold flex items-center gap-1 border border-outline-variant/60 transition-colors cursor-pointer"
                >
                  <span>SWITCH TO VIEW</span>
                  <ArrowUpRight className="w-3 h-3" />
                </button>
              </div>
              <div className="bg-surface-container-lowest rounded h-28 relative overflow-hidden flex items-center justify-center border border-outline-variant/30 select-none">
                <svg className="w-full h-full" viewBox="0 0 240 100" xmlns="http://www.w3.org/2000/svg">
                  <ellipse cx="120" cy="78" rx="80" ry="18" fill="none" stroke="#253241" strokeWidth="1" />
                  <ellipse cx="120" cy="78" rx="50" ry="11" fill="none" stroke="#1d2632" strokeWidth="0.8" strokeDasharray="2,3" />
                  <path d="M 112,78 L 120,54 L 128,78 Z" fill="#182330" stroke="#314254" strokeWidth="1" />
                  <circle cx="120" cy="54" r="4.5" fill="#0284c7" />
                  <line x1="120" y1="54" x2="162" y2="28" stroke="#4cd7f6" strokeWidth="2.5" strokeLinecap="round" />
                  <polygon points="156,22 172,32 168,36 152,26" fill="#0369a1" stroke="#4cd7f6" strokeWidth="1" />
                  <line x1="166" y1="29" x2="225" y2="12" stroke="#4edea3" strokeWidth="1.2" strokeDasharray="3,2" />
                  <circle cx="225" cy="12" r="2.5" fill="#4edea3" />
                  <path d="M 120,78 A 70 15 0 0 1 170 82" fill="none" stroke="#f43f5e" strokeWidth="1.2" strokeDasharray="2,2" />
                  <polygon points="172,82 166,79 168,85" fill="#f43f5e" />
                  <text x="8" y="16" fill="#89929b" fontFamily="JetBrains Mono" fontSize="8">
                    GIMBAL AZ: {(telemetry.panAngleDeg || 0.0).toFixed(2)}°
                  </text>
                  <text x="8" y="27" fill="#89929b" fontFamily="JetBrains Mono" fontSize="8">
                    GIMBAL EL: {(telemetry.tiltAngleDeg || 0.0).toFixed(2)}°
                  </text>
                  <text x="175" y="24" fill="#4edea3" fontFamily="JetBrains Mono" fontSize="7.5">
                    LOS VECTOR
                  </text>
                </svg>
                <div className="absolute bottom-1 right-2 font-label-sm text-[9px] text-outline font-mono">
                  LIMITS: AZ ±270° | EL -5°~+95°
                </div>
              </div>
              <div className="mt-space-xs pt-space-xs flex items-center justify-between font-label-sm text-[10px] text-on-surface-variant font-mono">
                <span>
                  AZ: <span className="text-on-surface font-semibold">{(telemetry.panAngleDeg || 0.0).toFixed(1)}°</span>
                </span>
                <span>
                  EL: <span className="text-on-surface font-semibold">{(telemetry.tiltAngleDeg || 0.0).toFixed(1)}°</span>
                </span>
              </div>
            </div>
          </div>

          {/* Dynamic Real-Time Tracking Error Oscillogram Card (Issue 2) */}
          <TrackingErrorChartCard
            errorHistory={errorHistory}
            radialErr={radialErr}
            centroidRmse={centroidRmse}
          />
        </div>

        {/* Right Parameter & Matrix Control Sidebar (Item 1.x & 1.z) */}
        <div className="lg:col-span-4 flex flex-col h-full min-h-0">
          <DeveloperControlSidebar
            pattern={pattern}
            setPattern={setPattern}
            slewSpeed={slewSpeed}
            setSlewSpeed={setSlewSpeed}
            atmCondition={atmCondition}
            setAtmCondition={setAtmCondition}
            gaussianNoise={gaussianNoise}
            setGaussianNoise={setGaussianNoise}
            poissonNoise={poissonNoise}
            setPoissonNoise={setPoissonNoise}
            saltPepperNoise={saltPepperNoise}
            setSaltPepperNoise={setSaltPepperNoise}
            kp={kp}
            setKp={setKp}
            ki={ki}
            setKi={setKi}
            deadband={deadband}
            setDeadband={setDeadband}
            appliedNotice={appliedNotice}
            handleApplyGains={handleApplyGains}
          />
        </div>
      </div>

      {/* ── Bottom Performance Telemetry Horizon Dock (Item 1.e, 1.f, 1.u, 1.v) ── */}
      <DeveloperBottomHorizon
        radialErr={radialErr}
        loopRate={loopRate}
        frameNum={frameNum}
        centroidRmse={centroidRmse}
        acqLatency={acqLatency}
        targetLossRate={targetLossRate}
        errorHistory={errorHistory}
      />
    </div>
  )
}

export default WorldCanvasView
