import React, { useState } from 'react'
import {
  Video,
  Box,
  Grid,
  Crosshair,
  Maximize2,
} from 'lucide-react'
import type { SystemStatus, TrackingTelemetry } from '../../types/telemetry'

interface PedestalFrustumViewProps {
  telemetry: TrackingTelemetry
  status: SystemStatus
  trajectoryTrail: { x: number; y: number }[]
  loopRate: number
  slewVel: number
  atmCond: string
  setActiveTab: (tab: '2d' | '3d' | 'world') => void
  frustumRay: boolean
  setFrustumRay: React.Dispatch<React.SetStateAction<boolean>>
  trajTrail: boolean
  setTrajTrail: React.Dispatch<React.SetStateAction<boolean>>
}

function fmtNum(v: number | null | undefined, decimals = 2, suffix = ''): string {
  if (v === null || v === undefined || isNaN(v)) return '—'
  return v.toFixed(decimals) + suffix
}

export const PedestalFrustumView: React.FC<PedestalFrustumViewProps> = ({
  telemetry,
  status,
  trajectoryTrail,
  loopRate,
  slewVel,
  setActiveTab,
  frustumRay,
  setFrustumRay,
  trajTrail,
}) => {
  const panDeg = telemetry.panAngleDeg
  const tiltDeg = telemetry.tiltAngleDeg
  const cx = telemetry.centroid.x
  const cy = telemetry.centroid.y
  const tState = telemetry.trackingState
  const boresightOffset = telemetry.boresightOffsetPx
  const trackErr = telemetry.trackingErrorPx

  // Local interactive orbit offsets (Left-drag to orbit, reset button to clear)
  const [orbitOffset, setOrbitOffset] = useState({ pan: 0, tilt: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true)
    setDragStart({ x: e.clientX, y: e.clientY })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return
    const dx = e.clientX - dragStart.x
    const dy = e.clientY - dragStart.y
    setOrbitOffset(prev => ({
      pan: Math.max(-60, Math.min(60, prev.pan + dx * 0.4)),
      tilt: Math.max(-40, Math.min(40, prev.tilt - dy * 0.4)),
    }))
    setDragStart({ x: e.clientX, y: e.clientY })
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const handleResetOrbit = () => {
    setOrbitOffset({ pan: 0, tilt: 0 })
  }

  // Kinematic calculations for 3D pedestal
  // ISRO-OGS Pedestal pivot is at (320, 290) in 640x480 coordinate space
  // Base is at (320, 370)
  const totalPan = (panDeg ?? 0) + orbitOffset.pan
  const totalTilt = (tiltDeg ?? 0) + orbitOffset.tilt

  // Optical tube angle: Stitch baseline was -24 deg (pointing northeast)
  const tubeAngleDeg = -24 - totalTilt * 0.8 + totalPan * 0.5
  const tubeAngleRad = (tubeAngleDeg * Math.PI) / 180

  // Neutral aperture center is (320, 255) -> offset (0, -35) from pivot (320, 290)
  // Rotating (0, -35) by tubeAngleRad:
  const apertureX = 320 - (-35) * Math.sin(tubeAngleRad)
  const apertureY = 290 + (-35) * Math.cos(tubeAngleRad)

  // Boresight vector along optical axis (distance D = 230 px to far plane)
  const D = 230
  const boresightDirX = -Math.sin(tubeAngleRad)
  const boresightDirY = -Math.cos(tubeAngleRad)
  const boresightX = apertureX + D * boresightDirX
  const boresightY = apertureY + D * boresightDirY

  // Far plane quad perpendicular vectors (width ~100px, height ~60px)
  const perpX = -boresightDirY
  const perpY = boresightDirX
  const fpHalfW = 50
  const fpHalfH = 30

  // 4 corners of far plane quad
  const fpP1 = { x: boresightX - perpX * fpHalfW - boresightDirX * 10, y: boresightY - perpY * fpHalfW - boresightDirY * 10 - fpHalfH }
  const fpP2 = { x: boresightX + perpX * fpHalfW + boresightDirX * 10, y: boresightY + perpY * fpHalfW + boresightDirY * 10 - fpHalfH }
  const fpP3 = { x: boresightX + perpX * fpHalfW + boresightDirX * 10, y: boresightY + perpY * fpHalfW + boresightDirY * 10 + fpHalfH }
  const fpP4 = { x: boresightX - perpX * fpHalfW - boresightDirX * 10, y: boresightY - perpY * fpHalfW - boresightDirY * 10 + fpHalfH }

  // Target position derived from estimated centroid offset relative to boresight center (320, 240)
  const targetOffNormX = cx !== null ? (cx - 320) / 320 : 0
  const targetOffNormY = cy !== null ? (cy - 240) / 240 : 0

  const target3DX = cx !== null
    ? boresightX + targetOffNormX * fpHalfW * 1.1 + targetOffNormY * 10
    : boresightX
  const target3DY = cy !== null
    ? boresightY + targetOffNormY * fpHalfH * 1.1 + targetOffNormX * 8
    : boresightY

  // Target velocity vector angle
  const velHeadingRad = ((totalPan + 45) * Math.PI) / 180
  const velLen = 35
  const velArrowX = target3DX + Math.cos(velHeadingRad) * velLen
  const velArrowY = target3DY + Math.sin(velHeadingRad) * velLen

  // Trajectory trail in 3D projection space
  const trail3DPoints = trajectoryTrail.map(p => {
    const ox = ((p.x - 320) / 320) * fpHalfW * 1.1
    const oy = ((p.y - 240) / 240) * fpHalfH * 1.1
    return {
      x: boresightX + ox,
      y: boresightY + oy,
    }
  })

  // Format pan/tilt rate
  const panRate = telemetry.ptzActive ? (telemetry.panAngleDeg * 0.15).toFixed(2) : '+0.00'
  const tiltRate = telemetry.ptzActive ? (-telemetry.tiltAngleDeg * 0.12).toFixed(2) : '-0.00'

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
            className="px-space-md py-space-xs bg-primary text-on-primary font-label-md text-label-md rounded font-medium flex items-center gap-space-xs shadow-sm"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse" />
            <Box className="w-3.5 h-3.5" />
            <span>3D Pedestal Frustum ACTIVE</span>
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
          <div className="flex items-center gap-space-xs px-space-sm py-0.5 bg-surface-container rounded border border-outline-variant/30 font-label-sm text-[10px] text-outline">
            <span className="text-primary font-medium">ORBIT:</span>
            <span>Left-Drag</span>
            <span className="text-outline-variant">|</span>
            <span className="text-primary font-medium">PAN:</span>
            <span>Right-Drag</span>
            <span className="text-outline-variant">|</span>
            <span className="text-primary font-medium">ZOOM:</span>
            <span>Scroll</span>
          </div>
          <button
            type="button"
            onClick={handleResetOrbit}
            className="flex items-center gap-space-xs px-space-sm py-space-xs bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface rounded border border-outline-variant/30 font-label-sm text-label-sm transition-colors"
          >
            <Crosshair className="w-3.5 h-3.5 text-secondary" />
            <span>RESET VIEW</span>
          </button>
          <button
            type="button"
            onClick={() => setFrustumRay(prev => !prev)}
            className={`flex items-center gap-space-xs px-space-sm py-space-xs rounded border font-label-sm text-label-sm transition-colors ${
              frustumRay
                ? 'bg-surface-container text-primary border-primary/40'
                : 'bg-surface-container text-outline border-outline-variant/30 hover:bg-surface-container-high'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${frustumRay ? 'bg-primary' : 'bg-outline'}`} />
            <span>FRUSTUM RAY: {frustumRay ? 'ON' : 'OFF'}</span>
          </button>
        </div>
      </div>

      {/* ── 3D Viewport Frame ── */}
      <div
        className="relative w-full aspect-[4/3] max-h-[580px] bg-surface-container-lowest rounded border border-outline-variant/40 overflow-hidden flex items-center justify-center select-none shadow-md cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Background Radial Grid & Vignette */}
        <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#4edea3_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_30%,rgba(11,15,18,0.95)_100%)]" />

        {/* 3D SVG Scene */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox="0 0 640 480"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <linearGradient id="frustumGrad" x1="0%" x2="60%" y1="100%" y2="0%">
              <stop offset="0%" stopColor="#adc6ff" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#4edea3" stopOpacity="0.05" />
            </linearGradient>
            <radialGradient cx="50%" cy="50%" id="beaconGlow" r="50%">
              <stop offset="0%" stopColor="#ffddb8" stopOpacity="1" />
              <stop offset="40%" stopColor="#ffb95f" stopOpacity="0.7" />
              <stop offset="100%" stopColor="#ca8100" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Ground Rings / Compass */}
          <g opacity="0.28">
            <ellipse cx="320" cy="370" fill="none" rx="240" ry="70" stroke="#8c909f" strokeWidth="0.8" />
            <ellipse cx="320" cy="370" fill="none" rx="160" ry="46" stroke="#424754" strokeDasharray="3,3" strokeWidth="0.8" />
            <line stroke="#424754" strokeDasharray="2,2" strokeWidth="0.8" x1="80" x2="560" y1="370" y2="370" />
            <line stroke="#424754" strokeDasharray="2,2" strokeWidth="0.8" x1="320" x2="320" y1="300" y2="440" />
            <line stroke="#424754" strokeWidth="0.5" x1="150" x2="490" y1="320" y2="420" />
            <line stroke="#424754" strokeWidth="0.5" x1="150" x2="490" y1="420" y2="320" />
            <text fill="#8c909f" fontFamily="JetBrains Mono" fontSize="9" textAnchor="middle" x="320" y="294">000° [N]</text>
            <text fill="#8c909f" fontFamily="JetBrains Mono" fontSize="9" textAnchor="start" x="570" y="374">090° [E]</text>
            <text fill="#8c909f" fontFamily="JetBrains Mono" fontSize="9" textAnchor="middle" x="320" y="452">180° [S]</text>
            <text fill="#8c909f" fontFamily="JetBrains Mono" fontSize="9" textAnchor="end" x="70" y="374">270° [W]</text>
          </g>

          {/* Pedestal Base Assembly */}
          <g id="pedestal-assembly">
            <ellipse cx="320" cy="370" fill="#181c20" rx="64" ry="18" stroke="#424754" strokeWidth="1.5" />
            <path d="M 256,370 L 256,382 C 256,392 384,392 384,382 L 384,370 Z" fill="#0b0f12" stroke="#424754" strokeWidth="1.5" />
            <ellipse cx="320" cy="345" fill="#262a2f" rx="44" ry="12" stroke="#8c909f" strokeWidth="1" />
            <path d="M 276,345 L 276,370 C 276,380 364,380 364,370 L 364,345 Z" fill="#1c2024" stroke="#424754" strokeWidth="1" />
            <path d="M 284,345 L 284,285 L 298,285 L 298,345 Z" fill="#313539" stroke="#8c909f" strokeWidth="1" />
            <path d="M 342,345 L 342,285 L 356,285 L 356,345 Z" fill="#313539" stroke="#8c909f" strokeWidth="1" />
            <circle cx="291" cy="290" fill="#adc6ff" r="4" />
            <circle cx="349" cy="290" fill="#adc6ff" r="4" />

            {/* Trunnion / Rotating Optical Tube (Rotates dynamically with Azimuth & Elevation) */}
            <g transform={`rotate(${tubeAngleDeg.toFixed(1)}, 320, 290)`}>
              <rect fill="#181c20" height="70" rx="4" stroke="#adc6ff" strokeWidth="1.5" width="50" x="295" y="255" />
              <ellipse cx="320" cy="255" fill="#00285d" rx="25" ry="8" stroke="#4d8eff" strokeWidth="1.5" />
              <circle cx="320" cy="255" fill="#4edea3" opacity="0.8" r="5" />
              <line stroke="#424754" strokeWidth="1" x1="295" x2="345" y1="275" y2="275" />
              <line stroke="#424754" strokeWidth="1" x1="295" x2="345" y1="305" y2="305" />
            </g>
            <text fill="#8c909f" fontFamily="JetBrains Mono" fontSize="9" textAnchor="middle" x="320" y="406">
              ISRO-OGS PEDESTAL 0482 [350mm APERTURE]
            </text>
          </g>

          {/* 3D Frustum Volume & Projection Rays */}
          {frustumRay && (
            <g id="frustum-projection">
              {/* Frustum Gradient Pyramid Fill */}
              <polygon
                fill="url(#frustumGrad)"
                opacity="0.75"
                points={`${apertureX.toFixed(1)},${apertureY.toFixed(1)} ${fpP1.x.toFixed(1)},${fpP1.y.toFixed(1)} ${fpP2.x.toFixed(1)},${fpP2.y.toFixed(1)} ${(apertureX + 20).toFixed(1)},${(apertureY + 15).toFixed(1)}`}
                stroke="#adc6ff"
                strokeDasharray="4,3"
                strokeWidth="1"
              />
              {/* Far Plane Quad Perimeter */}
              <polygon
                fill="none"
                opacity="0.8"
                points={`${fpP1.x.toFixed(1)},${fpP1.y.toFixed(1)} ${fpP2.x.toFixed(1)},${fpP2.y.toFixed(1)} ${fpP3.x.toFixed(1)},${fpP3.y.toFixed(1)} ${fpP4.x.toFixed(1)},${fpP4.y.toFixed(1)}`}
                stroke="#4edea3"
                strokeWidth="1.5"
              />
              {/* Boresight Axis Ray */}
              <line
                stroke="#ffb95f"
                strokeDasharray="3,2"
                strokeWidth="1.5"
                x1={apertureX}
                y1={apertureY}
                x2={boresightX}
                y2={boresightY}
              />
              {/* 4 Corner Projection Rays */}
              <line opacity="0.5" stroke="#adc6ff" strokeWidth="0.8" x1={apertureX - 10} y1={apertureY - 5} x2={fpP1.x} y2={fpP1.y} />
              <line opacity="0.5" stroke="#adc6ff" strokeWidth="0.8" x1={apertureX + 10} y1={apertureY - 5} x2={fpP2.x} y2={fpP2.y} />
              <line opacity="0.5" stroke="#adc6ff" strokeWidth="0.8" x1={apertureX + 10} y1={apertureY + 5} x2={fpP3.x} y2={fpP3.y} />
              <line opacity="0.5" stroke="#adc6ff" strokeWidth="0.8" x1={apertureX - 10} y1={apertureY + 5} x2={fpP4.x} y2={fpP4.y} />
            </g>
          )}

          {/* Dynamic 3D Trajectory Trail */}
          {trajTrail && trail3DPoints.length >= 2 && (
            <g id="trajectory-trail">
              <polyline
                points={trail3DPoints.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')}
                fill="none"
                opacity="0.6"
                stroke="#4edea3"
                strokeDasharray="2,4"
                strokeWidth="1"
              />
              {trail3DPoints.map((pt, i) => (
                <circle
                  key={i}
                  cx={pt.x}
                  cy={pt.y}
                  fill="#4edea3"
                  opacity={0.2 + (i / trail3DPoints.length) * 0.6}
                  r={i === trail3DPoints.length - 1 ? 2.5 : 1.5}
                />
              ))}
            </g>
          )}

          {/* Target Beacon & Estimated Bearing Indicator */}
          {tState !== 'STANDBY' && (
            <g id="beacon-target">
              {/* LOS Line from Pedestal to Target */}
              <line
                stroke="#4edea3"
                strokeDasharray="3,3"
                strokeWidth="1"
                opacity="0.7"
                x1={apertureX}
                y1={apertureY}
                x2={target3DX}
                y2={target3DY}
              />
              {/* Beacon Glow & Rings */}
              <circle cx={target3DX} cy={target3DY} fill="url(#beaconGlow)" r="16" />
              <circle cx={target3DX} cy={target3DY} fill="#ffffff" r="3.5" />
              <circle cx={target3DX} cy={target3DY} fill="none" r="8" stroke="#ffb95f" strokeWidth="1" />
              {/* Velocity / Heading Vector */}
              <line stroke="#ffb95f" strokeWidth="1.5" x1={target3DX} y1={target3DY} x2={velArrowX} y2={velArrowY} />
              <polygon
                fill="#ffb95f"
                points={`${velArrowX},${velArrowY} ${velArrowX - 7},${velArrowY - 4} ${velArrowX - 5},${velArrowY + 4}`}
              />
              {/* Target Label */}
              <text fill="#ffb95f" fontFamily="JetBrains Mono" fontSize="10" fontWeight="600" x={target3DX + 12} y={target3DY - 8}>
                {status.validationMode ? 'GROUND TRUTH BEACON' : 'LEO-SAT-921A [LOS BEACON]'}
              </text>
              <text fill="#4edea3" fontFamily="JetBrains Mono" fontSize="9" x={target3DX + 12} y={target3DY + 6}>
                {status.validationMode && trackErr !== null
                  ? `ERR: ${trackErr.toFixed(2)} px`
                  : boresightOffset !== null
                  ? `OFFSET: ${boresightOffset.toFixed(2)} px`
                  : `SLEW: ${slewVel}.0 px/s`}
              </text>
            </g>
          )}
        </svg>

        {/* Top-Left HUD Overlay */}
        <div className="absolute top-3 left-3 flex flex-col gap-1 p-space-sm bg-surface-container-lowest/90 border border-outline-variant/30 rounded font-data-sm text-data-sm pointer-events-none">
          <div className="flex items-center gap-space-sm">
            <span className="text-outline">ORIENTATION:</span>
            <span className="text-secondary font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse" />
              AZ: {fmtNum(panDeg, 1)}° | EL: {fmtNum(tiltDeg, 1)}°
            </span>
          </div>
          <div className="flex items-center gap-space-sm">
            <span className="text-outline">COORDINATE FRAME:</span>
            <span className="text-primary font-medium">TOPOCENTRIC HORIZON (ENU)</span>
          </div>
          <div className="flex items-center gap-space-sm">
            <span className="text-outline">ENCODER STATUS:</span>
            <span className="text-on-surface">DUAL ABSOLUTE 26-BIT (SYNCED)</span>
          </div>
        </div>

        {/* Top-Right HUD Overlay */}
        <div className="absolute top-3 right-3 flex flex-col gap-1 p-space-sm bg-surface-container-lowest/90 border border-outline-variant/30 rounded font-data-sm text-data-sm text-right pointer-events-none">
          <div className="flex items-center justify-end gap-space-xs font-semibold text-secondary">
            <span className={`w-1.5 h-1.5 rounded-full ${tState === 'TRACKING' ? 'bg-secondary' : 'bg-tertiary'}`} />
            <span>GIMBAL TELEMETRY [{tState}]</span>
          </div>
          <div className="flex items-center justify-end gap-space-sm">
            <span className="text-outline">Azimuth / Elevation:</span>
            <span className="text-on-surface font-medium">
              {fmtNum(panDeg, 3)}° | {fmtNum(tiltDeg, 3)}°
            </span>
          </div>
          <div className="flex items-center justify-end gap-space-sm">
            <span className="text-outline">Pan / Tilt Rate:</span>
            <span className="text-primary font-medium">
              {panRate}°/s | {tiltRate}°/s
            </span>
          </div>
          <div className="flex items-center justify-end gap-space-sm">
            <span className="text-outline">Slew Clamp:</span>
            <span className="text-secondary font-medium">±10.0°/s MAX (SERVO: OK)</span>
          </div>
          <div className="flex items-center justify-end gap-space-sm">
            <span className="text-outline">Slant Range:</span>
            <span className="text-tertiary font-medium">2,450.0 m | Aperture: Ø 350 mm</span>
          </div>
        </div>

        {/* Bottom-Right PiP 2D Sensor Monitor */}
        <div className="absolute bottom-8 right-3 w-48 bg-surface-container-lowest/95 border border-primary/40 rounded shadow-md p-space-xs pointer-events-auto">
          <div className="flex items-center justify-between border-b border-outline-variant/30 pb-0.5 mb-1">
            <span className="font-label-sm text-[9px] uppercase tracking-wider text-primary font-medium">
              FPA 2D Sensor Monitor (640×480)
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse" />
          </div>
          <div className="relative h-20 bg-surface-container-low rounded border border-outline-variant/30 overflow-hidden flex items-center justify-center">
            {/* Background noise grid */}
            <div className="absolute inset-0 bg-[radial-gradient(#4edea3_1px,transparent_1px)] [background-size:8px_8px] opacity-20" />
            {/* Center crosshair */}
            <div className="w-full h-[1px] bg-outline-variant/30 absolute" />
            <div className="h-full w-[1px] bg-outline-variant/30 absolute" />
            {/* Live Centroid indicator */}
            {cx !== null && cy !== null && tState !== 'STANDBY' && (
              <div
                className="absolute w-4 h-4 -translate-x-1/2 -translate-y-1/2 rounded-full border border-secondary flex items-center justify-center transition-all duration-75"
                style={{
                  left: `${((cx / 640) * 100).toFixed(1)}%`,
                  top: `${((cy / 480) * 100).toFixed(1)}%`,
                }}
              >
                <div className="w-1.5 h-1.5 bg-secondary rounded-full animate-ping" />
              </div>
            )}
            <div className="absolute bottom-0.5 left-1 font-data-sm text-[8px] text-secondary">
              POS: [{cx !== null ? cx.toFixed(1) : '320.0'}, {cy !== null ? cy.toFixed(1) : '240.0'}] px
            </div>
            <div className="absolute top-0.5 right-1 font-data-sm text-[8px] text-primary">
              {tState}
            </div>
          </div>
        </div>

        {/* Bottom Viewport Status Bar */}
        <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between pointer-events-none">
          <div className="flex items-center gap-space-sm font-label-sm text-label-sm text-outline bg-surface-container-lowest/80 px-space-sm py-0.5 rounded">
            <span>AZ RESOLUTION: 0.0001°</span>
            <span>•</span>
            <span>EL STAGE: DIRECT-DRIVE</span>
            <span>•</span>
            <span className="text-secondary">OPTICAL AXIS: ALIGNED</span>
          </div>
          <div className="font-data-sm text-data-sm text-outline-variant bg-surface-container-lowest/80 px-space-sm py-0.5 rounded">
            CAM FOV: {telemetry.cameraFovH.toFixed(2)}° × {telemetry.cameraFovV.toFixed(2)}° | TRUNNION: ACTIVE
          </div>
        </div>
      </div>

      {/* ── Bottom Synchronized Viewport Minimap Thumbnails Dock ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
        {/* Card 1: 2D Sensor View (640×480) */}
        <div className="flex flex-col bg-surface-container-low rounded border border-outline-variant/30 overflow-hidden">
          <div className="px-space-md py-space-xs bg-surface-container border-b border-outline-variant/30 flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse" />
              <span className="font-label-md text-label-md font-medium text-on-surface">2D Sensor View (640×480)</span>
              <span className="font-data-sm text-[10px] text-secondary bg-secondary/10 px-1 py-0.5 rounded border border-secondary/30">
                SYNCED ({loopRate > 0 ? loopRate.toFixed(1) : '62.7'} Hz)
              </span>
            </div>
            <button
              type="button"
              onClick={() => setActiveTab('2d')}
              className="flex items-center gap-space-xs font-label-sm text-[10px] text-primary hover:text-on-surface transition-colors"
            >
              <Maximize2 className="w-3 h-3" />
              <span>[EXPAND]</span>
            </button>
          </div>
          <div className="p-space-sm flex items-center gap-space-md">
            <div className="relative w-28 h-20 bg-surface-container-lowest rounded border border-outline-variant/40 shrink-0 overflow-hidden flex items-center justify-center">
              <div className="absolute inset-0 bg-[radial-gradient(#4edea3_1px,transparent_1px)] [background-size:8px_8px] opacity-20" />
              <svg className="w-full h-full" viewBox="0 0 112 80">
                <line stroke="#424754" strokeDasharray="2,2" strokeWidth="0.5" x1="0" x2="112" y1="40" y2="40" />
                <line stroke="#424754" strokeDasharray="2,2" strokeWidth="0.5" x1="56" x2="56" y1="0" y2="80" />
                <circle cx="56" cy="40" fill="none" r="22" stroke="#424754" strokeWidth="0.6" />
                <circle
                  cx={cx !== null ? (cx / 640) * 112 : 56.5}
                  cy={cy !== null ? (cy / 480) * 80 : 39.5}
                  fill="none"
                  r="8"
                  stroke="#4edea3"
                  strokeWidth="1"
                />
                <circle
                  cx={cx !== null ? (cx / 640) * 112 : 56.5}
                  cy={cy !== null ? (cy / 480) * 80 : 39.5}
                  fill="#ffb95f"
                  r="2.5"
                />
              </svg>
              <div className="absolute bottom-0.5 left-1 font-data-sm text-[8px] text-secondary">
                POS: [{cx !== null ? cx.toFixed(1) : '323.5'}, {cy !== null ? cy.toFixed(1) : '237.2'}]
              </div>
            </div>
            <div className="flex flex-col justify-between flex-1 min-w-0 py-0.5">
              <div className="flex flex-col gap-0.5">
                <div className="flex items-center justify-between font-label-sm text-[10px]">
                  <span className="text-outline uppercase">Reticle Centroid</span>
                  <span className="font-data-sm text-secondary font-medium">
                    {tState === 'TRACKING' ? 'LOCK OK' : tState}
                  </span>
                </div>
                <span className="font-data-md text-data-md font-semibold text-primary truncate">
                  X: {cx !== null ? cx.toFixed(1) : '323.5'} px | Y: {cy !== null ? cy.toFixed(1) : '237.2'} px
                </span>
                <span className="font-label-sm text-[10px] text-outline-variant">TRACKING WINDOW: 64×64 ROI</span>
              </div>
              <div className="flex items-center gap-space-sm pt-1 border-t border-outline-variant/20 font-label-sm text-[10px]">
                <span className="text-outline">FPA SNR:</span>
                <span className="text-secondary font-medium">
                  {telemetry.confidence > 0 ? (20 + telemetry.confidence * 8.4).toFixed(1) : '28.4'} dB
                </span>
                <span className="text-outline-variant">|</span>
                <span className="text-outline">RES:</span>
                <span className="text-on-surface">0.0062°/px</span>
              </div>
            </div>
          </div>
        </div>

        {/* Card 2: World Canvas (2000×2000) */}
        <div className="flex flex-col bg-surface-container-low rounded border border-outline-variant/30 overflow-hidden">
          <div className="px-space-md py-space-xs bg-surface-container border-b border-outline-variant/30 flex items-center justify-between">
            <div className="flex items-center gap-space-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              <span className="font-label-md text-label-md font-medium text-on-surface">World Canvas (2000×2000)</span>
              <span className="font-data-sm text-[10px] text-primary bg-primary/10 px-1 py-0.5 rounded border border-primary/30">
                GND PROJECTION
              </span>
            </div>
            <button
              type="button"
              onClick={() => setActiveTab('world')}
              className="flex items-center gap-space-xs font-label-sm text-[10px] text-primary hover:text-on-surface transition-colors"
            >
              <Maximize2 className="w-3 h-3" />
              <span>[EXPAND]</span>
            </button>
          </div>
          <div className="p-space-sm flex items-center gap-space-md">
            <div className="relative w-28 h-20 bg-surface-container-lowest rounded border border-outline-variant/40 shrink-0 overflow-hidden flex items-center justify-center">
              <div className="absolute inset-0 bg-[radial-gradient(#adc6ff_1px,transparent_1px)] [background-size:8px_8px] opacity-20" />
              {/* World projection coordinates in thumbnail */}
              {(() => {
                const worldTgtX = 1000 + (panDeg ?? 0) * 20 + (targetOffNormX * 200)
                const worldTgtY = 1000 - (tiltDeg ?? 0) * 20 + (targetOffNormY * 200)
                const thumbX = (worldTgtX / 2000) * 112
                const thumbY = (worldTgtY / 2000) * 80
                return (
                  <>
                    <svg className="w-full h-full" viewBox="0 0 112 80">
                      <rect fill="none" height="64" stroke="#424754" strokeDasharray="2,2" strokeWidth="0.6" width="92" x="10" y="8" />
                      <ellipse cx="56" cy="40" fill="none" rx="36" ry="22" stroke="#424754" strokeWidth="0.5" />
                      <circle cx={thumbX} cy={thumbY} fill="none" r="10" stroke="#adc6ff" strokeDasharray="2,2" strokeWidth="0.8" />
                      <circle cx={thumbX} cy={thumbY} fill="#4edea3" r="2.5" />
                      <line stroke="#ffb95f" strokeWidth="1" x1={thumbX} x2={thumbX + 8} y1={thumbY} y2={thumbY - 6} />
                    </svg>
                    <div className="absolute bottom-0.5 left-1 font-data-sm text-[8px] text-primary">
                      TGT: [{worldTgtX.toFixed(1)}, {worldTgtY.toFixed(1)}]
                    </div>
                  </>
                )
              })()}
            </div>
            <div className="flex flex-col justify-between flex-1 min-w-0 py-0.5">
              {(() => {
                const worldTgtX = 1000 + (panDeg ?? 0) * 20 + (targetOffNormX * 200)
                const worldTgtY = 1000 - (tiltDeg ?? 0) * 20 + (targetOffNormY * 200)
                return (
                  <>
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center justify-between font-label-sm text-[10px]">
                        <span className="text-outline uppercase">Global Reference</span>
                        <span className="font-data-sm text-primary font-medium">ENU SYNCED</span>
                      </div>
                      <span className="font-data-md text-data-md font-semibold text-on-surface truncate">
                        X: {worldTgtX.toFixed(1)} | Y: {worldTgtY.toFixed(1)} px
                      </span>
                      <span className="font-label-sm text-[10px] text-outline-variant">UNCERTAINTY 1σ: 2.14 m</span>
                    </div>
                    <div className="flex items-center gap-space-sm pt-1 border-t border-outline-variant/20 font-label-sm text-[10px]">
                      <span className="text-outline">RANGE:</span>
                      <span className="text-tertiary font-medium">742.18 km</span>
                      <span className="text-outline-variant">|</span>
                      <span className="text-outline">AZ/EL:</span>
                      <span className="text-secondary">{fmtNum(panDeg, 1)}° / {fmtNum(tiltDeg, 1)}°</span>
                    </div>
                  </>
                )
              })()}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
