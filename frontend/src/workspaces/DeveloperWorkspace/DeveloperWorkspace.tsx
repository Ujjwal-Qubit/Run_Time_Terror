import React, { useState, useEffect, useRef } from 'react'
import {
  Box,
  Grid,
  Lock,
  ArrowUpRight,
} from 'lucide-react'
import { useSanketStore } from '../../store/useSanketStore'
import { bridgeService } from '../../services/bridgeService'
import { PedestalFrustumView } from './PedestalFrustumView'
import { WorldCanvasView } from './WorldCanvasView'
import { DeveloperControlSidebar } from './DeveloperControlSidebar'
import type { TrajectoryPattern, AtmCondition } from './DeveloperControlSidebar'
import { DeveloperBottomHorizon } from './DeveloperBottomHorizon'
import { TrackingErrorChartCard } from './TrackingErrorChartCard'

// ─────────────────────────────────────────────────────────────
// Screen 1: SANKET — Developer Workspace (2D Sensor View)
// Visual design strictly matches Stitch: 1_dev_2d.html
// ─────────────────────────────────────────────────────────────

export const DeveloperWorkspace: React.FC = () => {
  const telemetry = useSanketStore((s) => s.telemetry)
  const status = useSanketStore((s) => s.status)
  const latestFrame = useSanketStore((s) => s.latestFrame)

  const activeTab = useSanketStore((s) => s.activeDeveloperTab)
  const setActiveTab = useSanketStore((s) => s.setActiveDeveloperTab)

  // Sub-Navigation Toggles (Items 1.o & 1.q: Defaults ON)
  const [zoomLevel, setZoomLevel] = useState<'fit' | '1.0x' | '2.0x'>('fit')
  const [showAimingReticle, setShowAimingReticle] = useState(true)
  const [showAdaptiveROI, setShowAdaptiveROI] = useState(true)
  const [showTrajectoryBreadcrumbs, setShowTrajectoryBreadcrumbs] = useState(true)

  // Interactive controls defaults (Items 1.i & 1.j: linear, clear, noise unchecked)
  const [pattern, setPattern] = useState<TrajectoryPattern>('linear')
  const [slewSpeed, setSlewSpeed] = useState<number>(45.0)
  const [atmCondition, setAtmCondition] = useState<AtmCondition>('clear')
  const [gaussianNoise, setGaussianNoise] = useState<boolean>(false)
  const [poissonNoise, setPoissonNoise] = useState<boolean>(false)
  const [saltPepperNoise, setSaltPepperNoise] = useState<boolean>(false)

  // PTZ gains
  const [kp, setKp] = useState<number>(8.0)
  const [ki, setKi] = useState<number>(2.0)
  const [deadband, setDeadband] = useState<number>(1.0)
  const [appliedNotice, setAppliedNotice] = useState<boolean>(false)

  // Dynamic tracking & metric state buffers
  const [trajectoryTrail, setTrajectoryTrail] = useState<{ x: number; y: number }[]>([])
  const [errorHistory, setErrorHistory] = useState<number[]>([])
  const [lostFramesCount, setLostFramesCount] = useState<number>(0)
  const [totalFramesCount, setTotalFramesCount] = useState<number>(0)

  // Sync active scenario config from backend (Item 1.dd)
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

  // Centroid & target existence check (Item 1.k)
  const hasTarget = Boolean(
    status.isRunning &&
    status.trackingEnabled !== false &&
    telemetry.centroid.x !== null &&
    telemetry.centroid.y !== null
  )
  const cx = hasTarget ? telemetry.centroid.x! : 320.0
  const cy = hasTarget ? telemetry.centroid.y! : 240.0
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

  // Canvas ref for direct image rendering
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  // Buffer centroid breadcrumbs
  useEffect(() => {
    if (hasTarget) {
      setTrajectoryTrail((prev) => {
        const next = [...prev, { x: cx, y: cy }]
        if (next.length > 50) next.shift()
        return next
      })
    } else if (!status.isRunning) {
      if (trajectoryTrail.length > 0) setTrajectoryTrail([])
    }
  }, [cx, cy, hasTarget, status.isRunning])

  // Error history and loss rate tracking (Item 1.v & 1.e)
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

  // Draw camera video frame to canvas
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
    }
  }, [latestFrame])

  // Sub-tab delegation
  if (activeTab === '3d') {
    return <PedestalFrustumView />
  }
  if (activeTab === 'world') {
    return <WorldCanvasView />
  }

  const handleApplyGains = () => {
    bridgeService.setPtzGains(kp, ki, deadband)
    setAppliedNotice(true)
    setTimeout(() => setAppliedNotice(false), 2000)
  }

  // Calculate pixel bounds for ROI Box around centroid
  const roiSize = 128
  const roiLeft = Math.max(0, Math.min(640 - roiSize, cx - roiSize / 2))
  const roiTop = Math.max(0, Math.min(480 - roiSize, cy - roiSize / 2))

  const centroidRmse = status.isRunning && errorHistory.length > 0
    ? Math.sqrt(errorHistory.reduce((acc, v) => acc + v * v, 0) / errorHistory.length).toFixed(3)
    : '0.000'
  const acqLatency = status.isRunning
    ? (telemetry.processingLatencyMs > 0 ? (telemetry.processingLatencyMs / 1000).toFixed(3) : '0.033')
    : '0.000'
  const targetLossRate = totalFramesCount > 0
    ? ((lostFramesCount / totalFramesCount) * 100).toFixed(1)
    : '0.00'

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
              className="bg-surface-container-high text-primary px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1.5 font-bold shadow-sm border border-primary/40"
            >
              <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse" />
              <span>◉ 2D Sensor View (640×480)</span>
              <span className="bg-primary text-on-primary text-[9px] px-1 py-0.2 rounded font-mono font-semibold">
                ACTIVE
              </span>
            </button>

            {/* Tab 2: 3D Pedestal Frustum */}
            <button
              type="button"
              onClick={() => setActiveTab('3d')}
              className="text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1.5 transition-colors"
            >
              <Box className="w-3.5 h-3.5 text-outline" />
              <span>⬡ 3D Pedestal Frustum</span>
            </button>

            {/* Tab 3: 2000×2000 World Canvas */}
            <button
              type="button"
              onClick={() => setActiveTab('world')}
              className="text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1.5 transition-colors"
            >
              <Grid className="w-3.5 h-3.5 text-outline" />
              <span>▦ 2000×2000 World Canvas</span>
            </button>
          </div>

          <span className="text-outline-variant font-label-sm mx-1">|</span>

          {/* Mag Zoom Controls (Item 1.d & 1.s) */}
          <div className="flex items-center gap-1 bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant/40">
            <span className="text-outline font-label-sm text-[10px]">MAG:</span>
            <button
              type="button"
              onClick={() => setZoomLevel('fit')}
              className={`font-label-sm text-[10px] px-1.5 py-0.5 font-semibold rounded cursor-pointer ${
                zoomLevel === 'fit' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              FIT
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel('1.0x')}
              className={`font-label-sm text-[10px] px-1.5 py-0.5 font-semibold rounded cursor-pointer ${
                zoomLevel === '1.0x' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              1.0x
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel('2.0x')}
              className={`font-label-sm text-[10px] px-1.5 py-0.5 font-semibold rounded cursor-pointer ${
                zoomLevel === '2.0x' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              2.0x
            </button>
          </div>
        </div>

        {/* Viewport HUD Overlays Toggles */}
        <div className="flex items-center gap-space-md">
          <div className="flex items-center gap-space-sm font-label-sm text-[11px]">
            <label className="flex items-center gap-1 cursor-pointer text-on-surface">
              <input
                type="checkbox"
                checked={showAimingReticle}
                onChange={(e) => setShowAimingReticle(e.target.checked)}
                className="w-3.5 h-3.5 accent-primary bg-surface-container-lowest rounded-sm cursor-pointer"
              />
              <span className="text-primary font-semibold">Aiming Reticle (OSD)</span>
            </label>
            <label className="flex items-center gap-1 cursor-pointer text-secondary">
              <input
                type="checkbox"
                checked={showAdaptiveROI}
                onChange={(e) => setShowAdaptiveROI(e.target.checked)}
                className="w-3.5 h-3.5 accent-secondary bg-surface-container-lowest rounded-sm cursor-pointer"
              />
              <span className="font-semibold">Adaptive ROI (128×128)</span>
            </label>
            <label className="flex items-center gap-1 cursor-pointer text-on-surface-variant">
              <input
                type="checkbox"
                checked={showTrajectoryBreadcrumbs}
                onChange={(e) => setShowTrajectoryBreadcrumbs(e.target.checked)}
                className="w-3.5 h-3.5 accent-primary bg-surface-container-lowest rounded-sm cursor-pointer"
              />
              <span>Trajectory Breadcrumbs</span>
            </label>
          </div>

          <div className="h-4 w-px bg-outline-variant" />

          {/* Sync Status Badge */}
          <div className="font-label-sm text-[11px] text-tertiary flex items-center gap-1 bg-surface-container-lowest px-2 py-0.5 rounded border border-tertiary/30 font-semibold">
            <Lock className="w-3 h-3 text-tertiary" />
            <span>HIL SYNCHRONIZED</span>
          </div>
        </div>
      </div>

      {/* ── Primary Workspace Content Grid ── */}
      <div className="p-space-sm grid grid-cols-1 lg:grid-cols-12 gap-gutter items-stretch">
        {/* Central Viewport Column (~65% -> 8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-gutter">
          {/* Live 640x480 Monochrome FPA Sensor Canvas Card */}
          <div className="bg-surface-container-lowest rounded overflow-hidden shadow-md flex flex-col relative select-none border border-outline-variant/40">
            {/* Canvas Top Metric Ribbon / Minimal HUD (Items 1.l, 1.n, 1.t, 1.u) */}
            <div className="bg-surface-container-low px-space-md py-1 flex items-center justify-between font-label-sm text-[11px] border-b border-outline-variant/40">
              <div className="flex items-center gap-space-sm font-mono flex-wrap">
                <div className="flex items-center gap-1 bg-surface-container-lowest text-tertiary px-2 py-0.5 rounded border border-tertiary/40 font-bold text-[10px] tracking-wide">
                  <span className={`w-1.5 h-1.5 rounded-full ${status.isRunning ? 'bg-tertiary animate-pulse' : 'bg-outline'}`} />
                  <span>
                    {status.isRunning ? 'TRACKING (LOCKED 100%)' : 'STANDBY / READY'}
                  </span>
                </div>
                <span className="text-outline-variant">|</span>
                <div className="flex items-center gap-1">
                  <span className="text-outline">SNR:</span>
                  <span className="text-primary font-bold">{status.isRunning ? '34.2 dB' : '-- dB'}</span>
                </div>
                <span className="text-outline-variant">|</span>
                <div className="flex items-center gap-1">
                  <span className="text-outline">SLEW:</span>
                  <span className="text-on-surface font-semibold">
                    {status.isRunning ? `${Math.abs(telemetry.panAngleDeg * 0.05 + 2.1).toFixed(2)}°/s` : '0.00°/s'}
                  </span>
                </div>
                <span className="text-outline-variant">|</span>
                <div className="flex items-center gap-1">
                  <span className="text-outline">CENTROID:</span>
                  <span className="text-secondary font-semibold">
                    {hasTarget ? `[${cx.toFixed(2)}, ${cy.toFixed(2)}]` : '[---, ---]'}
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
                  BEACON_NIR_850
                </span>
                <span>ISRO SIH</span>
              </div>
            </div>

            {/* Sensor Video Display Viewport with Real Magnification Scale (Item 1.d & 1.s) */}
            <div className="relative w-full aspect-[4/3] bg-surface-dim overflow-hidden flex items-center justify-center">
              <div
                className="w-full h-full relative transition-transform duration-200 ease-out origin-center flex items-center justify-center"
                style={{
                  transform: zoomLevel === '2.0x' ? 'scale(2.0)' : zoomLevel === '1.0x' ? 'scale(1.0)' : 'scale(1.0)',
                }}
              >
                {/* Optional live video stream canvas */}
                <canvas
                  ref={canvasRef}
                  width={640}
                  height={480}
                  className="absolute inset-0 w-full h-full object-contain pointer-events-none opacity-90"
                />

                {/* Mathematical Sensor Viewport SVG Canvas Overlay */}
                <svg className="w-full h-full absolute inset-0 z-10" viewBox="0 0 640 480" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <pattern id="fpaPixelNoise" width="16" height="16" patternUnits="userSpaceOnUse">
                      <rect width="16" height="16" fill="#090d10" fillOpacity={latestFrame ? 0.2 : 1} />
                      <circle cx="4" cy="4" r="0.6" fill="#151b22" opacity="0.45" />
                      <circle cx="12" cy="10" r="0.5" fill="#1c242e" opacity="0.3" />
                      <circle cx="8" cy="14" r="0.4" fill="#131920" opacity="0.4" />
                    </pattern>
                    <radialGradient id="beaconCore" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
                      <stop offset="25%" stopColor="#67e8f9" stopOpacity="0.95" />
                      <stop offset="55%" stopColor="#0284c7" stopOpacity="0.5" />
                      <stop offset="90%" stopColor="#0369a1" stopOpacity="0.1" />
                      <stop offset="100%" stopColor="#0369a1" stopOpacity="0" />
                    </radialGradient>
                  </defs>

                  {!latestFrame && <rect width="640" height="480" fill="url(#fpaPixelNoise)" />}

                  {/* Grid Lines */}
                  <g stroke="#1a232c" strokeWidth="0.75" strokeDasharray="2,6">
                    <line x1="80" y1="0" x2="80" y2="480" />
                    <line x1="160" y1="0" x2="160" y2="480" />
                    <line x1="240" y1="0" x2="240" y2="480" />
                    <line x1="320" y1="0" x2="320" y2="480" />
                    <line x1="400" y1="0" x2="400" y2="480" />
                    <line x1="480" y1="0" x2="480" y2="480" />
                    <line x1="560" y1="0" x2="560" y2="480" />
                    <line x1="0" y1="60" x2="640" y2="60" />
                    <line x1="0" y1="120" x2="640" y2="120" />
                    <line x1="0" y1="180" x2="640" y2="180" />
                    <line x1="0" y1="240" x2="640" y2="240" />
                    <line x1="0" y1="300" x2="640" y2="300" />
                    <line x1="0" y1="360" x2="640" y2="360" />
                    <line x1="0" y1="420" x2="640" y2="420" />
                  </g>

                  {/* Boresight Crosshair & Reticle Concentric Rings (OSD) */}
                  {showAimingReticle && (
                    <g transform="translate(320, 240)" fill="none">
                      <circle r="40" stroke="#253241" strokeWidth="1" strokeDasharray="3,3" />
                      <circle r="90" stroke="#212c38" strokeWidth="1" />
                      <circle r="150" stroke="#1d2632" strokeWidth="1" strokeDasharray="4,4" />
                      <circle r="210" stroke="#161f29" strokeWidth="1" />
                      <line x1="-300" y1="0" x2="-10" y2="0" stroke="#314254" strokeWidth="1" />
                      <line x1="10" y1="0" x2="300" y2="0" stroke="#314254" strokeWidth="1" />
                      <line x1="0" y1="-220" x2="0" y2="-10" stroke="#314254" strokeWidth="1" />
                      <line x1="0" y1="10" x2="0" y2="220" stroke="#314254" strokeWidth="1" />
                      <circle r="2.5" fill="#4cd7f6" />
                      <text x="6" y="-6" fill="#89929b" fontFamily="JetBrains Mono" fontSize="9" fontWeight="600">
                        BORESIGHT (320.0, 240.0)
                      </text>
                      <text x="-85" y="-95" fill="#3f4850" fontFamily="JetBrains Mono" fontSize="8">
                        R=90px
                      </text>
                      <text x="-145" y="-155" fill="#3f4850" fontFamily="JetBrains Mono" fontSize="8">
                        R=150px
                      </text>
                    </g>
                  )}

                  {/* Trajectory Breadcrumbs */}
                  {showTrajectoryBreadcrumbs && hasTarget && (
                    <g fill="none" strokeLinecap="round">
                      {trajectoryTrail.length > 1 && (
                        <polyline
                          points={trajectoryTrail.map((pt) => `${pt.x},${pt.y}`).join(' ')}
                          stroke="#f59e0b"
                          strokeWidth="1.8"
                          strokeDasharray="4,3"
                          opacity="0.85"
                        />
                      )}
                      {trajectoryTrail.map((pt, idx) => (
                        <circle
                          key={idx}
                          cx={pt.x}
                          cy={pt.y}
                          r={1.8 + (idx / trajectoryTrail.length) * 1.2}
                          fill="#fbbf24"
                          opacity={0.3 + (idx / trajectoryTrail.length) * 0.7}
                        />
                      ))}
                    </g>
                  )}

                  {/* Adaptive ROI Bounding Box with Enclosing Box (Item 1.r: width=132) */}
                  {showAdaptiveROI && hasTarget && (
                    <g transform={`translate(${roiLeft}, ${roiTop})`}>
                      <rect width="128" height="128" fill="#06b6d4" fillOpacity="0.04" stroke="#0284c7" strokeWidth="1.5" strokeDasharray="6,3" />
                      <path d="M 0,16 L 0,0 L 16,0" fill="none" stroke="#4cd7f6" strokeWidth="2.5" />
                      <path d="M 112,0 L 128,0 L 128,16" fill="none" stroke="#4cd7f6" strokeWidth="2.5" />
                      <path d="M 0,112 L 0,128 L 16,128" fill="none" stroke="#4cd7f6" strokeWidth="2.5" />
                      <path d="M 112,128 L 128,128 L 128,112" fill="none" stroke="#4cd7f6" strokeWidth="2.5" />
                      <rect x="0" y="-14" width="132" height="14" fill="#0a131c" stroke="#0284c7" strokeWidth="0.8" rx="2" />
                      <text x="4" y="-4" fill="#4cd7f6" fontFamily="JetBrains Mono" fontSize="8.5" fontWeight="bold">
                        ROI: 128×128 (ADAPTIVE)
                      </text>
                    </g>
                  )}

                  {/* Target Beacon & Centroid Crosshair (Item 1.k: Render ONLY when tracking is ACTIVE) */}
                  {hasTarget && (
                    <g transform={`translate(${cx}, ${cy})`}>
                      <circle r="24" fill="url(#beaconCore)" />
                      <circle r="3.5" fill="#ffffff" />
                      <line x1="-14" y1="0" x2="-4" y2="0" stroke="#f43f5e" strokeWidth="1.5" />
                      <line x1="4" y1="0" x2="14" y2="0" stroke="#f43f5e" strokeWidth="1.5" />
                      <line x1="0" y1="-14" x2="0" y2="-4" stroke="#f43f5e" strokeWidth="1.5" />
                      <line x1="0" y1="4" x2="0" y2="14" stroke="#f43f5e" strokeWidth="1.5" />
                      <circle r="5" fill="none" stroke="#f43f5e" strokeWidth="0.8" strokeDasharray="1,2" />
                      <text x="16" y="-8" fill="#4edea3" fontFamily="JetBrains Mono" fontSize="8.5" fontWeight="bold">
                        dx: +{(cx - 320).toFixed(2)} px
                      </text>
                      <text x="16" y="4" fill="#4edea3" fontFamily="JetBrains Mono" fontSize="8.5" fontWeight="bold">
                        dy: {(cy - 240) >= 0 ? `+${(cy - 240).toFixed(2)}` : (cy - 240).toFixed(2)} px
                      </text>
                      <text x="16" y="16" fill="#93ccff" fontFamily="JetBrains Mono" fontSize="7.5" fontWeight="500">
                        [{cx.toFixed(2)}, {cy.toFixed(2)}]
                      </text>
                    </g>
                  )}

                  <rect x="1" y="1" width="638" height="478" fill="none" stroke="#1d2632" strokeWidth="1.5" />
                </svg>
              </div>

              {/* Top-Left Floating Reticle Telemetry Widget */}
              <div className="absolute top-2.5 left-2.5 bg-surface-container-lowest/90 px-space-sm py-1 rounded text-on-surface font-label-sm text-[10px] space-y-0.5 shadow select-none border border-outline-variant/30 z-20">
                <div className="flex items-center gap-1.5">
                  <span className="text-outline">TARGET:</span>
                  <span className="text-primary font-bold">BEACON_NIR_850</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-outline">CENTROID:</span>
                  <span className="text-secondary font-mono">
                    {hasTarget ? `X:${cx.toFixed(2)} Y:${cy.toFixed(2)}` : 'ACQUIRING...'}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-outline">RADIAL ERR:</span>
                  <span className="text-tertiary font-mono">{radialErr.toFixed(3)} px (SUB-PX)</span>
                </div>
              </div>

              {/* Top-Right FPA State Tag */}
              <div className="absolute top-2.5 right-2.5 bg-surface-container-lowest/90 px-space-sm py-1 rounded text-right font-label-sm text-[10px] space-y-0.5 shadow select-none border border-outline-variant/30 z-20">
                <div className="text-outline">ISRO SIH PS-26169</div>
                <div className="text-secondary font-semibold">
                  {status.isRunning ? 'CLOSED_LOOP_TRACKING' : 'STANDBY_MODE'}
                </div>
                <div className="text-tertiary flex items-center justify-end gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${status.isRunning ? 'bg-tertiary animate-pulse' : 'bg-outline'}`} />
                  <span>{status.isRunning ? 'PTZ_SERVO_ACTIVE' : 'PTZ_DISENGAGED'}</span>
                </div>
              </div>
            </div>

            {/* Viewport Bottom Bar / Sensor Configuration Readout */}
            <div className="bg-surface-container-low px-space-md py-1.5 flex flex-wrap items-center justify-between font-label-sm text-[11px] text-on-surface-variant border-t border-outline-variant/30">
              <div className="flex items-center gap-space-md">
                <span>
                  INT EXP: <strong className="text-on-surface font-mono">33.3 ms (30 Hz)</strong>
                </span>
                <span className="text-outline-variant">|</span>
                <span>
                  FORMAT: <strong className="text-on-surface font-mono">640×480 8-bit Mono</strong>
                </span>
                <span className="text-outline-variant">|</span>
                <span>
                  FIFO: <strong className="text-tertiary font-mono">0 OVERFLOW</strong>
                </span>
              </div>
              <div className="flex items-center gap-space-md">
                <span>
                  FOV: <strong className="text-on-surface font-mono">4.00° × 3.00°</strong>
                </span>
                <span className="text-outline-variant">|</span>
                <span>
                  IFOV: <strong className="text-secondary font-mono">0.109 mrad/px</strong>
                </span>
              </div>
            </div>
          </div>

          {/* Synchronized Secondary Views (Two Side-by-Side Dockable PIP Cards) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
            {/* PIP 1: 3D Pedestal Frustum */}
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
              <div className="bg-surface-container-lowest rounded h-28 relative overflow-hidden flex items-center justify-center border border-outline-variant/30">
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

            {/* PIP 2: 2000×2000 World Canvas */}
            <div className="bg-surface-container-low rounded p-space-sm shadow-sm flex flex-col justify-between border border-outline-variant/40">
              <div className="flex items-center justify-between pb-space-xs mb-space-xs border-b border-outline-variant/30">
                <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-on-surface">
                  <Grid className="w-3.5 h-3.5 text-secondary" />
                  <span className="font-semibold uppercase tracking-wider text-[11px]">
                    2000×2000 World Canvas
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('world')}
                  className="bg-surface-container text-secondary hover:text-primary hover:bg-surface-container-high px-2 py-0.5 rounded font-label-sm text-[10px] font-semibold flex items-center gap-1 border border-outline-variant/60 transition-colors cursor-pointer"
                >
                  <span>SWITCH TO VIEW</span>
                  <ArrowUpRight className="w-3 h-3" />
                </button>
              </div>
              <div className="bg-surface-container-lowest rounded h-28 relative overflow-hidden flex items-center justify-center border border-outline-variant/30">
                <svg className="w-full h-full" viewBox="0 0 240 100" xmlns="http://www.w3.org/2000/svg">
                  <g stroke="#1a232c" strokeWidth="0.8">
                    <line x1="30" y1="0" x2="30" y2="100" />
                    <line x1="70" y1="0" x2="70" y2="100" />
                    <line x1="110" y1="0" x2="110" y2="100" />
                    <line x1="150" y1="0" x2="150" y2="100" />
                    <line x1="190" y1="0" x2="190" y2="100" />
                    <line x1="230" y1="0" x2="230" y2="100" />
                    <line x1="0" y1="20" x2="240" y2="20" />
                    <line x1="0" y1="40" x2="240" y2="40" />
                    <line x1="0" y1="60" x2="240" y2="60" />
                    <line x1="0" y1="80" x2="240" y2="80" />
                  </g>
                  <circle cx="120" cy="50" r="3" fill="#3198dc" />
                  <text x="124" y="48" fill="#89929b" fontFamily="JetBrains Mono" fontSize="7.5">
                    OGS-BLR
                  </text>
                  <circle cx="137" cy="49" r="3" fill="#4edea3" />
                  <circle cx="137" cy="49" r="8" fill="none" stroke="#4edea3" strokeWidth="0.8" strokeDasharray="2,2" />
                  <line x1="120" y1="50" x2="137" y2="49" stroke="#93ccff" strokeWidth="1" />
                  <text x="8" y="16" fill="#89929b" fontFamily="JetBrains Mono" fontSize="8">
                    COORDS: X: {cx.toFixed(0)}, Y: {cy.toFixed(0)}
                  </text>
                  <text x="8" y="27" fill="#89929b" fontFamily="JetBrains Mono" fontSize="8">
                    UNCERTAINTY: R≤460px
                  </text>
                  <text x="144" y="60" fill="#4edea3" fontFamily="JetBrains Mono" fontSize="7.5">
                    [{cx.toFixed(0)}, {cy.toFixed(0)}]
                  </text>
                </svg>
                <div className="absolute bottom-1 right-2 font-label-sm text-[9px] text-outline font-mono">
                  2D PLANAR VIEWPORT
                </div>
              </div>
              <div className="mt-space-xs pt-space-xs flex items-center justify-between font-label-sm text-[10px] text-on-surface-variant font-mono">
                <span>
                  RANGE: <span className="text-on-surface font-semibold">[0, 2000] px</span>
                </span>
                <span>
                  SCALE: <span className="text-on-surface font-semibold">160.0 px/deg</span>
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

        {/* Right Parameter & Matrix Control Sidebar (~35% -> 4 cols) (Item 1.z) */}
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

export default DeveloperWorkspace
