import React, { useState } from 'react'
import {
  Video,
  Box,
  Grid,
  Maximize2,
} from 'lucide-react'
import type { SystemStatus, TrackingTelemetry } from '../../types/telemetry'

interface WorldCanvasViewProps {
  telemetry: TrackingTelemetry
  status: SystemStatus
  trajectoryTrail: { x: number; y: number }[]
  loopRate: number
  slewVel: number
  atmCond: string
  setActiveTab: (tab: '2d' | '3d' | 'world') => void
  canvasGrid: boolean
  setCanvasGrid: React.Dispatch<React.SetStateAction<boolean>>
  trajTrail: boolean
  setTrajTrail: React.Dispatch<React.SetStateAction<boolean>>
}

function fmtNum(v: number | null | undefined, decimals = 2, suffix = ''): string {
  if (v === null || v === undefined || isNaN(v)) return '—'
  return v.toFixed(decimals) + suffix
}

export const WorldCanvasView: React.FC<WorldCanvasViewProps> = ({
  telemetry,
  status,
  trajectoryTrail,
  loopRate,
  slewVel,
  atmCond,
  setActiveTab,
  canvasGrid,
  setCanvasGrid,
  trajTrail,
  setTrajTrail,
}) => {
  const panDeg = telemetry.panAngleDeg
  const tiltDeg = telemetry.tiltAngleDeg
  const cx = telemetry.centroid.x
  const cy = telemetry.centroid.y
  const tState = telemetry.trackingState
  const boresightOffset = telemetry.boresightOffsetPx

  // Ribbon toggles
  const [showEnvelope, setShowEnvelope] = useState(true)
  const [showFovOverlay, setShowFovOverlay] = useState(true)
  const [worldZoom, setWorldZoom] = useState<'fit' | '0.5x' | '1.0x' | '2.0x'>('1.0x')

  // Interactive cursor tracking in canvas coordinates (0..2000, 0..2000)
  const [cursorPos, setCursorPos] = useState({ x: 1042.0, y: 984.0 })

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = Math.max(0, Math.min(2000, Math.round(((e.clientX - rect.left) / rect.width) * 2000)))
    const y = Math.max(0, Math.min(2000, Math.round(((e.clientY - rect.top) / rect.height) * 2000)))
    setCursorPos({ x, y })
  }

  // Real kinematics calculations in 2000x2000 world coordinate space
  // Origin (Datum Zero) is at (1000, 1000)
  // Camera boresight projection on ground moves with pan and tilt
  const camWorldX = 1000 + (panDeg ?? 0) * 35.0
  const camWorldY = 1000 - (tiltDeg ?? 0) * 35.0

  // FPA Viewport (640x480) footprint upper-left corner
  const fpaX = camWorldX - 320
  const fpaY = camWorldY - 240

  // Estimated target world position derived from camera boresight + estimated optical centroid
  // When target is at center of sensor (320, 240), target world position matches boresight center
  const targetOffNormX = cx !== null ? cx - 320 : 0
  const targetOffNormY = cy !== null ? cy - 240 : 0

  const tgtWorldX = cx !== null ? camWorldX + targetOffNormX : 1052.4
  const tgtWorldY = cy !== null ? camWorldY + targetOffNormY : 984.2

  // Velocity vector arrow direction
  const velHeadingDeg = 35 - (panDeg ?? 0) * 0.5
  const velHeadingRad = (velHeadingDeg * Math.PI) / 180
  const velLen = 65
  const velVecX = Math.cos(velHeadingRad) * velLen
  const velVecY = -Math.sin(velHeadingRad) * velLen

  // Trajectory points in world space
  const worldTrailPoints = trajectoryTrail.map(p => {
    const wx = camWorldX + (p.x - 320)
    const wy = camWorldY + (p.y - 240)
    return `${wx.toFixed(1)},${wy.toFixed(1)}`
  }).join(' ')

  return (
    <div className="flex flex-col gap-space-md min-w-0">
      {/* ── Viewport Controls & Mode Ribbon ── */}
      <div className="flex flex-wrap items-center justify-between gap-space-sm bg-surface-container-low p-space-xs rounded border border-outline-variant/30">
        <div className="flex items-center gap-space-xs">
          <button
            type="button"
            onClick={() => setActiveTab('2d')}
            className="px-space-md py-space-xs bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high font-label-md text-label-md rounded transition-colors flex items-center gap-space-xs"
          >
            <Video className="w-3.5 h-3.5" />
            <span>2D Sensor View (640×480)</span>
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
            className="px-space-md py-space-xs bg-primary text-on-primary font-label-md text-label-md rounded font-medium flex items-center gap-space-xs shadow-sm"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-secondary shrink-0 animate-pulse" />
            <Grid className="w-3.5 h-3.5" />
            <span>2000×2000 World Canvas ACTIVE</span>
          </button>
        </div>

        <div className="flex items-center gap-space-xs">
          {/* Grid Toggle */}
          <button
            type="button"
            onClick={() => setCanvasGrid(g => !g)}
            className={`flex items-center gap-space-xs px-space-sm py-0.5 rounded border font-data-sm text-[11px] transition-colors ${
              canvasGrid
                ? 'bg-surface-container text-on-surface font-medium border-outline-variant/30'
                : 'bg-surface-container text-outline border-outline-variant/20'
            }`}
          >
            <span className="text-outline">Grid:</span>
            <span className={canvasGrid ? 'text-on-surface font-medium' : 'text-outline'}>
              {canvasGrid ? '100 px' : 'OFF'}
            </span>
          </button>

          {/* Uncertainty Envelope Toggle */}
          <button
            type="button"
            onClick={() => setShowEnvelope(e => !e)}
            className={`flex items-center gap-space-xs px-space-sm py-0.5 border font-data-sm text-[11px] rounded transition-colors ${
              showEnvelope
                ? 'bg-tertiary-container/30 border-tertiary-container text-tertiary'
                : 'bg-surface-container border-outline-variant/30 text-outline'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${showEnvelope ? 'bg-tertiary' : 'bg-outline'}`} />
            <span>Envelope: R≤460px {showEnvelope ? 'ACTIVE' : 'OFF'}</span>
          </button>

          {/* Trajectory Trail Toggle */}
          <button
            type="button"
            onClick={() => setTrajTrail(t => !t)}
            className={`px-space-sm py-0.5 rounded border font-data-sm text-[11px] transition-colors ${
              trajTrail
                ? 'bg-surface-container text-primary border-primary/30 font-medium'
                : 'bg-surface-container text-outline border-outline-variant/30'
            }`}
          >
            <span>Trail: {trajTrail ? 'Live (60)' : 'OFF'}</span>
          </button>

          {/* FOV Overlay Toggle */}
          <button
            type="button"
            onClick={() => setShowFovOverlay(f => !f)}
            className={`px-space-sm py-0.5 border font-data-sm text-[11px] rounded transition-colors ${
              showFovOverlay
                ? 'bg-secondary/10 border-secondary/30 text-secondary font-medium'
                : 'bg-surface-container border-outline-variant/30 text-outline'
            }`}
          >
            <span>FOV Overlay: {showFovOverlay ? 'ON' : 'OFF'}</span>
          </button>

          {/* Atmosphere Badge */}
          <div className="px-space-sm py-0.5 bg-tertiary-container text-on-tertiary-container font-data-sm text-[11px] rounded font-medium">
            <span>Atmosphere: {atmCond.charAt(0).toUpperCase() + atmCond.slice(1)} ACTIVE</span>
          </div>

          <div className="h-4 w-[1px] bg-outline-variant/30 mx-space-xs" />

          {/* Zoom Level Switchers */}
          <div className="flex items-center bg-surface-container rounded border border-outline-variant/30 p-0.5">
            {(['fit', '0.5x', '1.0x', '2.0x'] as const).map(z => (
              <button
                key={z}
                type="button"
                onClick={() => setWorldZoom(z)}
                className={`px-space-sm py-0.5 font-data-sm text-data-sm rounded transition-colors ${
                  worldZoom === z
                    ? 'text-primary bg-surface-container-highest font-medium'
                    : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest'
                }`}
              >
                {z === 'fit' ? 'Fit' : z}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── World Canvas Viewport Frame ── */}
      <div
        className="relative w-full h-[520px] bg-surface-container-lowest rounded border border-outline-variant/40 overflow-hidden flex items-center justify-center select-none shadow-md cursor-crosshair"
        onMouseMove={handleCanvasMouseMove}
      >
        {/* Scalable Canvas Layer */}
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
            <rect fill={canvasGrid ? 'url(#world-grid-500)' : '#0b0f12'} height="2000" width="2000" />

            {/* Atmospheric Perturbation Overlays */}
            {atmCond === 'fog' && (
              <>
                <circle cx="960" cy="920" fill="url(#fogHazeGrad)" r="380" />
                <text fill="#ca8100" fontFamily="JetBrains Mono" fontSize="22" fontWeight="500" opacity="0.8" x="680" y="880">
                  [FOG INTERSECT QUADRANT II (r0: 0.08)]
                </text>
              </>
            )}
            {atmCond === 'rain' && (
              <>
                <circle cx="1000" cy="1000" fill="rgba(77, 142, 255, 0.08)" r="480" />
                <text fill="#4d8eff" fontFamily="JetBrains Mono" fontSize="22" fontWeight="500" opacity="0.8" x="720" y="880">
                  [RAIN ATTENUATION: 3.8 dB/km (4.2 mm/hr)]
                </text>
              </>
            )}
            {atmCond === 'haze' && (
              <>
                <circle cx="1000" cy="1000" fill="rgba(255, 185, 95, 0.06)" r="420" />
                <text fill="#ffb95f" fontFamily="JetBrains Mono" fontSize="22" fontWeight="500" opacity="0.8" x="740" y="880">
                  [OPTICAL HAZE SCATTERING: MODERATE]
                </text>
              </>
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

            {/* Uncertainty Envelope (R=460px) */}
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
                  points={worldTrailPoints}
                  fill="none"
                  opacity="0.5"
                  stroke="#4edea3"
                  strokeDasharray="6,6"
                  strokeWidth="2.5"
                />
                {trajectoryTrail.slice(-10).map((pt, idx) => {
                  const wx = camWorldX + (pt.x - 320)
                  const wy = camWorldY + (pt.y - 240)
                  return (
                    <circle
                      key={idx}
                      cx={wx}
                      cy={wy}
                      fill="#4edea3"
                      opacity={0.3 + (idx / 10) * 0.7}
                      r={3.5 + idx * 0.2}
                    />
                  )
                })}
              </g>
            )}

            {/* Camera FPA Viewport (640×480 px) Ground Projection Footprint */}
            {showFovOverlay && (
              <g id="fpa-viewport-footprint">
                {/* 640x480 Footprint Rectangle */}
                <rect
                  fill="rgba(77, 142, 255, 0.05)"
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
                  <line x1={fpaX + 642} x2={fpaX + 602} y1={fpaY} y2={fpaY} />
                  <line x1={fpaX + 640} x2={fpaX + 640} y1={fpaY - 2} y2={fpaY + 38} />
                  <line x1={fpaX} x2={fpaX + 40} y1={fpaY + 480} y2={fpaY + 480} />
                  <line x1={fpaX + 2} x2={fpaX + 2} y1={fpaY + 482} y2={fpaY + 442} />
                  <line x1={fpaX + 642} x2={fpaX + 602} y1={fpaY + 480} y2={fpaY + 480} />
                  <line x1={fpaX + 640} x2={fpaX + 640} y1={fpaY + 482} y2={fpaY + 442} />
                </g>
                {/* Footprint Header Label */}
                <text fill="#adc6ff" fontFamily="JetBrains Mono" fontSize="24" fontWeight="bold" x={fpaX + 14} y={fpaY + 31}>
                  FPA VIEWPORT [640×480 px] CTR: ({camWorldX.toFixed(0)}, {camWorldY.toFixed(0)})
                </text>
                {/* Boresight Crosshair Axes */}
                <line
                  stroke="#4d8eff"
                  strokeDasharray="4,4"
                  strokeOpacity="0.35"
                  strokeWidth="1.2"
                  x1={camWorldX}
                  x2={camWorldX}
                  y1={fpaY}
                  y2={fpaY + 480}
                />
                <line
                  stroke="#4d8eff"
                  strokeDasharray="4,4"
                  strokeOpacity="0.35"
                  strokeWidth="1.2"
                  x1={fpaX}
                  x2={fpaX + 640}
                  y1={camWorldY}
                  y2={camWorldY}
                />
              </g>
            )}

            {/* Target Beacon Spot & Heading Vector in World Space */}
            {tState !== 'STANDBY' && (
              <g id="beacon-target-world">
                <circle cx={tgtWorldX} cy={tgtWorldY} fill="url(#spotPSFGrad)" r="28" />
                <circle cx={tgtWorldX} cy={tgtWorldY} fill="#ffffff" r="4" />
                {/* Heading / Slew Vector */}
                <line
                  stroke="#ffb95f"
                  strokeLinecap="round"
                  strokeWidth="3"
                  x1={tgtWorldX}
                  x2={tgtWorldX + velVecX}
                  y1={tgtWorldY}
                  y2={tgtWorldY + velVecY}
                />
                <polygon
                  fill="#ffb95f"
                  points={`${tgtWorldX + velVecX},${tgtWorldY + velVecY} ${tgtWorldX + velVecX - 12},${tgtWorldY + velVecY - 8} ${tgtWorldX + velVecX - 8},${tgtWorldY + velVecY + 8}`}
                />
                <text fill="#4edea3" fontFamily="JetBrains Mono" fontSize="22" fontWeight="bold" x={tgtWorldX + 18} y={tgtWorldY - 44}>
                  {status.validationMode ? 'BEACON [GT VALIDATION]' : 'BEACON [850nm]'} ({tgtWorldX.toFixed(1)}, {tgtWorldY.toFixed(1)})
                </text>
              </g>
            )}
          </svg>
        </div>

        {/* Top-Left HUD Overlay */}
        <div className="absolute top-3 left-3 flex flex-col gap-1 p-space-sm bg-surface-container-lowest/90 border border-outline-variant/30 rounded font-data-sm text-data-sm pointer-events-none">
          <div className="flex items-center gap-space-sm">
            <span className="text-primary font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-primary" />
              CANVAS_WORLD // SIM_ENGINE [CALIBRATED]
            </span>
          </div>
          <div className="flex items-center gap-space-sm text-[11px] text-tertiary font-mono">
            <span>LIVE OPERATIONAL: WORLD GT STRIPPED</span>
          </div>
          <div className="flex items-center gap-space-sm">
            <span className="text-outline">WORLD DIMS:</span>
            <span className="text-on-surface">2000 × 2000 px (4,000,000 px²)</span>
          </div>
          <div className="flex items-center gap-space-sm">
            <span className="text-outline">ORIGIN:</span>
            <span className="text-on-surface font-medium">(1000.0, 1000.0) [DATUM ZERO]</span>
          </div>
          <div className="flex items-center gap-space-sm">
            <span className="text-outline">CURSOR POS:</span>
            <span className="text-secondary font-medium">
              X: {cursorPos.x.toFixed(1)}, Y: {cursorPos.y.toFixed(1)}
            </span>
          </div>
        </div>

        {/* Top-Right HUD Overlay */}
        <div className="absolute top-3 right-3 flex flex-col gap-1 p-space-sm bg-surface-container-lowest/90 border border-outline-variant/30 rounded font-data-sm text-data-sm text-right pointer-events-none">
          <div className="flex items-center justify-end gap-space-sm">
            <span className="text-secondary font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
              Target Telemetry [{tState === 'TRACKING' ? 'LOCKED_IN_FOV' : tState}]
            </span>
          </div>
          <div className="flex items-center justify-end gap-space-sm">
            <span className="text-outline">Camera FOV Coverage:</span>
            <span className="text-primary font-medium">7.68% (640×480)</span>
          </div>
          <div className="flex items-center justify-end gap-space-sm">
            <span className="text-outline">Beacon World Pos:</span>
            <span className="text-on-surface font-medium">
              X: {tgtWorldX.toFixed(1)}, Y: {tgtWorldY.toFixed(1)}
            </span>
          </div>
          <div className="flex items-center justify-end gap-space-sm">
            <span className="text-outline">Beacon Velocity:</span>
            <span className="text-secondary font-medium">
              {slewVel}.0 px/s ({((slewVel / 640) * telemetry.cameraFovH).toFixed(2)}°/s)
            </span>
          </div>
          <div className="flex items-center justify-end gap-space-sm">
            <span className="text-outline">Uncertainty Envelope:</span>
            <span className="text-tertiary font-medium">R ≤ 460 px (Acq: 0.07s)</span>
          </div>
          <div className="flex items-center justify-end gap-space-sm">
            <span className="text-outline">Tracking State:</span>
            <span className="text-secondary font-medium">
              {tState === 'TRACKING' ? 'FINE_TRK (Nominal)' : tState}
            </span>
          </div>
        </div>

        {/* Bottom Viewport Status Bar */}
        <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between pointer-events-none">
          <div className="flex items-center gap-space-sm font-label-sm text-label-sm text-outline bg-surface-container-lowest/80 px-space-sm py-0.5 rounded">
            <span>CANVAS SPACE: 2000×2000</span>
            <span>•</span>
            <span>PROJECTION: ORTHOGRAPHIC GND</span>
            <span>•</span>
            <span className="text-secondary">SYNC: NOMINAL {loopRate > 0 ? loopRate.toFixed(1) : '62.7'} Hz</span>
          </div>
          <div className="font-data-sm text-data-sm text-outline-variant bg-surface-container-lowest/80 px-space-sm py-0.5 rounded">
            FOV COVERAGE: 640×480 px (307,200 px² = 7.68%)
          </div>
        </div>
      </div>

      {/* ── Bottom Synchronized Viewport Minimap Thumbnails Dock ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
        {/* Card 1: 2D Sensor View (640×480) */}
        <div className="flex flex-col bg-surface-container-low rounded border border-outline-variant/30 overflow-hidden">
          <div className="flex items-center justify-between px-space-md py-space-xs bg-surface-container border-b border-outline-variant/30">
            <div className="flex items-center gap-space-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse" />
              <span className="font-label-md text-label-md font-medium text-on-surface flex items-center gap-space-xs">
                <Video className="text-primary w-3.5 h-3.5" />
                <span>2D Sensor View (640×480)</span>
              </span>
            </div>
            <div className="flex items-center gap-space-xs">
              <span className="font-data-sm text-[10px] px-1 py-0.5 bg-secondary/10 text-secondary border border-secondary/30 rounded">
                SYNCED {loopRate > 0 ? loopRate.toFixed(1) : '62.7'} Hz
              </span>
              <button
                type="button"
                onClick={() => setActiveTab('2d')}
                className="flex items-center gap-0.5 px-space-xs py-0.5 bg-surface-container-highest hover:bg-surface-container hover:text-primary text-on-surface-variant font-data-sm text-[10px] rounded transition-colors"
              >
                <Maximize2 className="w-3 h-3" />
                <span>[EXPAND]</span>
              </button>
            </div>
          </div>
          <div className="relative w-full h-24 bg-surface-container-lowest flex items-center justify-center overflow-hidden p-space-xs select-none">
            <svg className="w-full h-full" viewBox="0 0 320 96">
              <defs>
                <radialGradient cx="50%" cy="50%" id="miniFpaSpot" r="50%">
                  <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
                  <stop offset="30%" stopColor="#4edea3" stopOpacity="0.8" />
                  <stop offset="80%" stopColor="#4edea3" stopOpacity="0.15" />
                  <stop offset="100%" stopColor="#4edea3" stopOpacity="0" />
                </radialGradient>
              </defs>
              <rect fill="none" height="94" rx="2" stroke="#424754" strokeDasharray="2,2" strokeWidth="0.8" width="318" x="1" y="1" />
              <line stroke="#8c909f" strokeDasharray="2,2" strokeOpacity="0.3" strokeWidth="0.8" x1="160" x2="160" y1="0" y2="96" />
              <line stroke="#8c909f" strokeDasharray="2,2" strokeOpacity="0.3" strokeWidth="0.8" x1="0" x2="320" y1="48" y2="48" />
              <circle cx="160" cy="48" fill="none" r="26" stroke="#4d8eff" strokeOpacity="0.5" strokeWidth="1" />
              <circle cx="160" cy="48" fill="none" r="42" stroke="#8c909f" strokeDasharray="3,3" strokeOpacity="0.35" strokeWidth="0.8" />
              <g stroke="#adc6ff" strokeWidth="1.5">
                <line x1="152" x2="168" y1="48" y2="48" />
                <line x1="160" x2="160" y1="40" y2="56" />
              </g>
              {/* Dynamic target marker */}
              {(() => {
                const spotX = cx !== null ? 160 + ((cx - 320) / 320) * 80 : 164.2
                const spotY = cy !== null ? 48 + ((cy - 240) / 240) * 36 : 46.8
                return (
                  <>
                    <circle cx={spotX} cy={spotY} fill="url(#miniFpaSpot)" r="14" />
                    <circle cx={spotX} cy={spotY} fill="#ffffff" r="2.2" />
                    <rect fill="none" height="20" stroke="#4edea3" strokeOpacity="0.8" strokeWidth="1" width="20" x={spotX - 10} y={spotY - 10} />
                    <g stroke="#4edea3" strokeWidth="1.2">
                      <line x1={spotX - 13} x2={spotX - 9} y1={spotY - 10} y2={spotY - 10} />
                      <line x1={spotX - 10} x2={spotX - 10} y1={spotY - 13} y2={spotY - 9} />
                      <line x1={spotX + 9} x2={spotX + 13} y1={spotY + 10} y2={spotY + 10} />
                      <line x1={spotX + 10} x2={spotX + 10} y1={spotY + 9} y2={spotY + 13} />
                    </g>
                    <text fill="#4edea3" fontFamily="JetBrains Mono" fontSize="9" fontWeight="bold" x="180" y="42">
                      {tState === 'TRACKING' ? 'LOCKED [FOV]' : tState}
                    </text>
                  </>
                )
              })()}
              <text fill="#adc6ff" fontFamily="JetBrains Mono" fontSize="8" x="6" y="12">FPA 640×480 @ 8-bit</text>
              <text fill="#8c909f" fontFamily="JetBrains Mono" fontSize="8" x="6" y="90">
                ΔX: {cx !== null ? (cx - 320 >= 0 ? `+${(cx - 320).toFixed(1)}` : (cx - 320).toFixed(1)) : '+4.2'} px | ΔY: {cy !== null ? (cy - 240 >= 0 ? `+${(cy - 240).toFixed(1)}` : (cy - 240).toFixed(1)) : '-1.2'} px
              </text>
              <text fill="#ffb95f" fontFamily="JetBrains Mono" fontSize="8" x="240" y="90">
                SNR: {telemetry.confidence > 0 ? (20 + telemetry.confidence * 4.8).toFixed(1) : '24.8'} dB
              </text>
            </svg>
          </div>
          <div className="px-space-md py-0.5 bg-surface-container-lowest/80 border-t border-outline-variant/20 flex items-center justify-between font-data-sm text-[10px]">
            <span className="text-outline">
              CENTROID: <span className="text-secondary font-medium">({cx !== null ? cx.toFixed(1) : '324.2'}, {cy !== null ? cy.toFixed(1) : '238.8'})</span>
            </span>
            <span className="text-outline">
              INTENSITY: <span className="text-on-surface">244 DN</span>
            </span>
            <span className="text-outline">
              SUB-PX: <span className="text-secondary">{boresightOffset !== null ? boresightOffset.toFixed(3) : '0.028'} px</span>
            </span>
          </div>
        </div>

        {/* Card 2: 3D Pedestal Frustum */}
        <div className="flex flex-col bg-surface-container-low rounded border border-outline-variant/30 overflow-hidden">
          <div className="flex items-center justify-between px-space-md py-space-xs bg-surface-container border-b border-outline-variant/30">
            <div className="flex items-center gap-space-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse" />
              <span className="font-label-md text-label-md font-medium text-on-surface flex items-center gap-space-xs">
                <Box className="text-primary w-3.5 h-3.5" />
                <span>3D Pedestal Frustum</span>
              </span>
            </div>
            <div className="flex items-center gap-space-xs">
              <span className="font-data-sm text-[10px] px-1 py-0.5 bg-secondary/10 text-secondary border border-secondary/30 rounded">
                GIMBAL TRACKING
              </span>
              <button
                type="button"
                onClick={() => setActiveTab('3d')}
                className="flex items-center gap-0.5 px-space-xs py-0.5 bg-surface-container-highest hover:bg-surface-container hover:text-primary text-on-surface-variant font-data-sm text-[10px] rounded transition-colors"
              >
                <Maximize2 className="w-3 h-3" />
                <span>[EXPAND]</span>
              </button>
            </div>
          </div>
          <div className="relative w-full h-24 bg-surface-container-lowest flex items-center justify-center overflow-hidden p-space-xs select-none">
            <svg className="w-full h-full" viewBox="0 0 320 96">
              <ellipse cx="160" cy="78" fill="rgba(66, 71, 84, 0.2)" rx="70" ry="12" stroke="#424754" strokeDasharray="2,2" strokeWidth="0.8" />
              <path d="M 148 78 L 154 58 L 166 58 L 172 78 Z" fill="#1c2024" stroke="#8c909f" strokeWidth="1" />
              <circle cx="160" cy="56" fill="#adc6ff" r="4" />
              <line stroke="#ffb95f" strokeDasharray="3,2" strokeWidth="1" x1="160" x2="245" y1="56" y2="22" />
              <polygon fill="rgba(77, 142, 255, 0.12)" points="160,56 220,12 270,30" stroke="#4d8eff" strokeOpacity="0.6" strokeWidth="1" />
              <line stroke="#adc6ff" strokeWidth="1.2" x1="160" x2="245" y1="56" y2="21" />
              <circle cx="245" cy="22" fill="#4edea3" r="3" />
              <text fill="#4edea3" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold" x="252" y="22">LEO-SAT</text>
              <text fill="#8c909f" fontFamily="JetBrains Mono" fontSize="8" x="6" y="12">
                AZ: {fmtNum(panDeg, 1)}° | EL: {fmtNum(tiltDeg, 1)}°
              </text>
              <text fill="#8c909f" fontFamily="JetBrains Mono" fontSize="8" x="6" y="90">
                SLEW: {slewVel}.0 px/s (LOS)
              </text>
              <text fill="#adc6ff" fontFamily="JetBrains Mono" fontSize="8" x="224" y="90">GIMBAL: DUAL-AXIS</text>
            </svg>
          </div>
          <div className="px-space-md py-0.5 bg-surface-container-lowest/80 border-t border-outline-variant/20 flex items-center justify-between font-data-sm text-[10px]">
            <span className="text-outline">
              AZ SERVO: <span className="text-secondary font-medium">0.00° ERR</span>
            </span>
            <span className="text-outline">
              EL SERVO: <span className="text-secondary font-medium">0.01° ERR</span>
            </span>
            <span className="text-outline">
              FRUSTUM: <span className="text-primary">ACTIVE 4°×3°</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
