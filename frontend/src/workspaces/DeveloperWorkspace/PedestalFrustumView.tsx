import React, { useState, useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import {
  Video,
  Grid,
  RefreshCw,
  Sliders,
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
// Screen 2: SANKET — Developer Workspace (3D Pedestal Frustum)
// Real Interactive 3D WebGL Orbit Viewport with Three.js
// ─────────────────────────────────────────────────────────────

export const PedestalFrustumView: React.FC = () => {
  const telemetry = useSanketStore((s) => s.telemetry)
  const status = useSanketStore((s) => s.status)
  const latestFrame = useSanketStore((s) => s.latestFrame)
  const setActiveTab = useSanketStore((s) => s.setActiveDeveloperTab)

  // Interactive 3D Toggles
  const [toggleFrustum, setToggleFrustum] = useState(true)
  const [toggleGrid, setToggleGrid] = useState(true)
  const [toggleLos, setToggleLos] = useState(true)

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

  // Sync active scenario config
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

  // ── Three.js Interactive 3D Setup (Item 1.w) ──
  const mountRef = useRef<HTMLDivElement | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const gimbalYokeRef = useRef<THREE.Group | null>(null)
  const telescopeTubeRef = useRef<THREE.Group | null>(null)
  const frustumMeshRef = useRef<THREE.Mesh | null>(null)
  const polarGridRef = useRef<THREE.PolarGridHelper | null>(null)
  const losLineRef = useRef<THREE.Line | null>(null)
  const beaconMeshRef = useRef<THREE.Mesh | null>(null)

  useEffect(() => {
    const container = mountRef.current
    if (!container) return

    const width = container.clientWidth || 800
    const height = container.clientHeight || 580

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x06090d)
    scene.fog = new THREE.FogExp2(0x06090d, 0.015)

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 500)
    camera.position.set(22, 18, 30)

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    container.appendChild(renderer.domElement)

    // OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.minDistance = 6
    controls.maxDistance = 120
    controls.maxPolarAngle = Math.PI / 2 + 0.08
    controls.target.set(0, 4, 0)
    controlsRef.current = controls

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x93ccff, 0.8)
    scene.add(ambientLight)

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.4)
    dirLight.position.set(30, 45, 25)
    scene.add(dirLight)

    const pointLight = new THREE.PointLight(0x0284c7, 2, 40)
    pointLight.position.set(0, 10, 0)
    scene.add(pointLight)

    // Polar Azimuth Grid ground helper
    const polarGrid = new THREE.PolarGridHelper(30, 16, 8, 64, 0x0284c7, 0x1f2937)
    polarGrid.position.y = 0.02
    scene.add(polarGrid)
    polarGridRef.current = polarGrid

    // Concentric ground fade ring
    const groundGeo = new THREE.CircleGeometry(32, 64)
    const groundMat = new THREE.MeshBasicMaterial({
      color: 0x0c131a,
      transparent: true,
      opacity: 0.8,
    })
    const groundMesh = new THREE.Mesh(groundGeo, groundMat)
    groundMesh.rotation.x = -Math.PI / 2
    scene.add(groundMesh)

    // Pedestal Base Structure (Fixed Ground Mounting)
    const baseGroup = new THREE.Group()

    // 1. Foundation flange
    const flangeGeo = new THREE.CylinderGeometry(4.2, 4.8, 0.8, 32)
    const flangeMat = new THREE.MeshStandardMaterial({ color: 0x151f28, roughness: 0.6, metalness: 0.4 })
    const flangeMesh = new THREE.Mesh(flangeGeo, flangeMat)
    flangeMesh.position.y = 0.4
    baseGroup.add(flangeMesh)

    // 2. Concrete riser
    const riserGeo = new THREE.CylinderGeometry(3.2, 3.8, 2.4, 32)
    const riserMat = new THREE.MeshStandardMaterial({ color: 0x1c2734, roughness: 0.7, metalness: 0.3 })
    const riserMesh = new THREE.Mesh(riserGeo, riserMat)
    riserMesh.position.y = 2.0
    baseGroup.add(riserMesh)

    // 3. Azimuth azimuth bearing collar
    const bearingGeo = new THREE.CylinderGeometry(2.8, 3.2, 0.6, 32)
    const bearingMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.3, metalness: 0.8 })
    const bearingMesh = new THREE.Mesh(bearingGeo, bearingMat)
    bearingMesh.position.y = 3.5
    baseGroup.add(bearingMesh)

    scene.add(baseGroup)

    // Gimbal Yoke Assembly (Rotates around Y axis based on panAngleDeg)
    const gimbalYoke = new THREE.Group()
    gimbalYoke.position.y = 3.8

    // Yoke base plate
    const yokeBaseGeo = new THREE.CylinderGeometry(2.6, 2.6, 0.5, 32)
    const yokeBaseMat = new THREE.MeshStandardMaterial({ color: 0x223040, roughness: 0.4, metalness: 0.6 })
    const yokeBaseMesh = new THREE.Mesh(yokeBaseGeo, yokeBaseMat)
    yokeBaseMesh.position.y = 0.25
    gimbalYoke.add(yokeBaseMesh)

    // Left Fork Arm
    const armGeo = new THREE.BoxGeometry(0.7, 3.5, 1.2)
    const armMat = new THREE.MeshStandardMaterial({ color: 0x1e2b38, roughness: 0.5, metalness: 0.5 })
    const leftArm = new THREE.Mesh(armGeo, armMat)
    leftArm.position.set(-2.0, 2.0, 0)
    gimbalYoke.add(leftArm)

    // Right Fork Arm
    const rightArm = new THREE.Mesh(armGeo, armMat)
    rightArm.position.set(2.0, 2.0, 0)
    gimbalYoke.add(rightArm)

    // Elevation Trunnion Bearings
    const trunnionGeo = new THREE.CylinderGeometry(0.5, 0.5, 4.4, 24)
    const trunnionMat = new THREE.MeshStandardMaterial({ color: 0x4cd7f6, roughness: 0.2, metalness: 0.8 })
    const trunnionMesh = new THREE.Mesh(trunnionGeo, trunnionMat)
    trunnionMesh.rotation.z = Math.PI / 2
    trunnionMesh.position.set(0, 3.2, 0)
    gimbalYoke.add(trunnionMesh)

    // Telescope Tube Assembly (Tilts around X axis based on tiltAngleDeg)
    const telescopeTube = new THREE.Group()
    telescopeTube.position.set(0, 3.2, 0)

    // Central Tube Body
    const tubeGeo = new THREE.CylinderGeometry(1.2, 1.2, 4.2, 32)
    const tubeMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.3, metalness: 0.7 })
    const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat)
    tubeMesh.rotation.x = Math.PI / 2
    telescopeTube.add(tubeMesh)

    // Front Optical Aperture & Sunshade
    const shadeGeo = new THREE.CylinderGeometry(1.35, 1.25, 1.5, 32, 1, true)
    const shadeMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.4, metalness: 0.6, side: THREE.DoubleSide })
    const shadeMesh = new THREE.Mesh(shadeGeo, shadeMat)
    shadeMesh.rotation.x = Math.PI / 2
    shadeMesh.position.z = 2.5
    telescopeTube.add(shadeMesh)

    // Optical Lens Glass
    const lensGeo = new THREE.CircleGeometry(1.2, 32)
    const lensMat = new THREE.MeshPhysicalMaterial({
      color: 0x4cd7f6,
      transmission: 0.9,
      roughness: 0.1,
      metalness: 0.1,
      transparent: true,
      opacity: 0.85,
    })
    const lensMesh = new THREE.Mesh(lensGeo, lensMat)
    lensMesh.position.z = 2.6
    telescopeTube.add(lensMesh)

    // 4.0° x 3.0° Rectangular Optical Frustum Pyramid / Beam (Item 3)
    const frustumLength = 35.0
    const halfW = frustumLength * Math.tan(THREE.MathUtils.degToRad(4.0 / 2)) // ~1.22
    const halfH = frustumLength * Math.tan(THREE.MathUtils.degToRad(3.0 / 2)) // ~0.916
    const apexZ = 2.6
    const farZ = apexZ + frustumLength

    const frustumGeo = new THREE.BufferGeometry()
    const frustumPositions = new Float32Array([
      // Top triangular face: Apex, Top-Left, Top-Right
      0, 0, apexZ,   -halfW, halfH, farZ,   halfW, halfH, farZ,
      // Bottom triangular face: Apex, Bottom-Right, Bottom-Left
      0, 0, apexZ,    halfW, -halfH, farZ,  -halfW, -halfH, farZ,
      // Left triangular face: Apex, Bottom-Left, Top-Left
      0, 0, apexZ,   -halfW, -halfH, farZ,  -halfW, halfH, farZ,
      // Right triangular face: Apex, Top-Right, Bottom-Right
      0, 0, apexZ,    halfW, halfH, farZ,    halfW, -halfH, farZ,
      // Far rectangle cap (2 triangles)
      -halfW, halfH, farZ,   -halfW, -halfH, farZ,   halfW, halfH, farZ,
       halfW, halfH, farZ,   -halfW, -halfH, farZ,   halfW, -halfH, farZ,
    ])
    frustumGeo.setAttribute('position', new THREE.BufferAttribute(frustumPositions, 3))
    frustumGeo.computeVertexNormals()

    const frustumMat = new THREE.MeshBasicMaterial({
      color: 0x03b5d3,
      transparent: true,
      opacity: 0.16,
      side: THREE.DoubleSide,
      depthWrite: false,
    })
    const frustumMesh = new THREE.Mesh(frustumGeo, frustumMat)

    // Crisp wireframe outline for 4 optical corner rays and rectangular far frame
    const edgeGeo = new THREE.BufferGeometry()
    const edgePositions = new Float32Array([
      // 4 corner rays from apex to far corners
      0, 0, apexZ,    halfW, halfH, farZ,
      0, 0, apexZ,   -halfW, halfH, farZ,
      0, 0, apexZ,   -halfW, -halfH, farZ,
      0, 0, apexZ,    halfW, -halfH, farZ,
      // Far rectangle frame
      -halfW, halfH, farZ,   halfW, halfH, farZ,
       halfW, halfH, farZ,   halfW, -halfH, farZ,
       halfW, -halfH, farZ, -halfW, -halfH, farZ,
      -halfW, -halfH, farZ, -halfW, halfH, farZ,
    ])
    edgeGeo.setAttribute('position', new THREE.BufferAttribute(edgePositions, 3))
    const edgeMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.65,
    })
    const edgeLines = new THREE.LineSegments(edgeGeo, edgeMat)
    frustumMesh.add(edgeLines)

    telescopeTube.add(frustumMesh)
    frustumMeshRef.current = frustumMesh

    gimbalYoke.add(telescopeTube)
    telescopeTubeRef.current = telescopeTube

    scene.add(gimbalYoke)
    gimbalYokeRef.current = gimbalYoke

    // Target Beacon in 3D Space (oriented along +Z forward optical axis)
    const beaconGeo = new THREE.SphereGeometry(0.8, 32, 32)
    const beaconMat = new THREE.MeshBasicMaterial({ color: 0x4edea3 })
    const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat)
    beaconMesh.position.set(0, 7.0, 32.0)
    scene.add(beaconMesh)
    beaconMeshRef.current = beaconMesh

    // Beacon Outer Glow Sphere
    const beaconGlowGeo = new THREE.SphereGeometry(1.6, 24, 24)
    const beaconGlowMat = new THREE.MeshBasicMaterial({
      color: 0xacedff,
      transparent: true,
      opacity: 0.35,
    })
    const beaconGlowMesh = new THREE.Mesh(beaconGlowGeo, beaconGlowMat)
    beaconMesh.add(beaconGlowMesh)

    // Line of Sight Vector (LOS)
    const losGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 7.0, 0),
      new THREE.Vector3(0, 7.0, 32.0),
    ])
    const losMat = new THREE.LineDashedMaterial({
      color: 0xf59e0b,
      dashSize: 1.2,
      gapSize: 0.6,
      linewidth: 2,
    })
    const losLine = new THREE.Line(losGeo, losMat)
    losLine.computeLineDistances()
    scene.add(losLine)
    losLineRef.current = losLine

    // Animation / Render Loop
    let animationFrameId: number
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // Resize Handler
    const handleResize = () => {
      if (!container) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelAnimationFrame(animationFrameId)
      window.removeEventListener('resize', handleResize)
      controls.dispose()
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  // Dynamic updates to 3D orientation and target beacon from telemetry (Item 2)
  useEffect(() => {
    const panDeg = telemetry.panAngleDeg ?? 0.0
    const tiltDeg = telemetry.tiltAngleDeg ?? 0.0
    const hasCentroid = telemetry.centroid?.x !== null && telemetry.centroid?.x !== undefined && telemetry.centroid?.y !== null && telemetry.centroid?.y !== undefined
    const cx = hasCentroid ? telemetry.centroid.x! : 320.0
    const cy = hasCentroid ? telemetry.centroid.y! : 240.0

    // Gimbal Yoke Azimuth (Yaw around Y-axis) - tracks with beacon (Issue 1)
    if (gimbalYokeRef.current) {
      gimbalYokeRef.current.rotation.y = THREE.MathUtils.degToRad(panDeg)
    }
    // Telescope Tube Elevation (Pitch around X-axis)
    if (telescopeTubeRef.current) {
      telescopeTubeRef.current.rotation.x = THREE.MathUtils.degToRad(-tiltDeg)
    }

    // Dynamic beacon position matching LOS vector in 3D space (+Z forward)
    if (beaconMeshRef.current && losLineRef.current) {
      const degPerPxH = 4.0 / 640.0
      const degPerPxV = 3.0 / 480.0
      const targetAzDeg = panDeg + (cx - 320.0) * degPerPxH
      const targetElDeg = tiltDeg - (cy - 240.0) * degPerPxV

      const azRad = THREE.MathUtils.degToRad(targetAzDeg)
      const elRad = THREE.MathUtils.degToRad(targetElDeg)
      const dist = 32.0

      // +Z is forward along the optical tracking axis
      const bx = dist * Math.sin(azRad) * Math.cos(elRad)
      const by = 7.0 + dist * Math.sin(elRad)
      const bz = dist * Math.cos(azRad) * Math.cos(elRad)

      beaconMeshRef.current.position.set(bx, by, bz)

      const positions = losLineRef.current.geometry.attributes.position as THREE.BufferAttribute
      positions.setXYZ(0, 0, 7.0, 0)
      positions.setXYZ(1, bx, by, bz)
      positions.needsUpdate = true
      losLineRef.current.computeLineDistances()
    }
  }, [telemetry.frameNumber, telemetry.panAngleDeg, telemetry.tiltAngleDeg, telemetry.centroid.x, telemetry.centroid.y, status.isRunning])

  // Viewport toggle handlers
  useEffect(() => {
    if (frustumMeshRef.current) frustumMeshRef.current.visible = toggleFrustum
  }, [toggleFrustum])

  useEffect(() => {
    if (polarGridRef.current) polarGridRef.current.visible = toggleGrid
  }, [toggleGrid])

  useEffect(() => {
    if (losLineRef.current) losLineRef.current.visible = toggleLos
  }, [toggleLos])

  const handleResetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset()
      controlsRef.current.target.set(0, 4, 0)
    }
  }

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
              className="bg-surface-container-high text-primary px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1.5 font-bold shadow-sm border border-primary/40 cursor-pointer"
            >
              <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse" />
              <span>⬡ 3D Pedestal Frustum</span>
              <span className="bg-primary text-on-primary text-[9px] px-1 py-0.2 rounded font-mono font-semibold">
                ACTIVE
              </span>
            </button>

            {/* Tab 3: 2000×2000 World Canvas */}
            <button
              type="button"
              onClick={() => setActiveTab('world')}
              className="text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high px-space-sm py-1 font-label-sm text-label-sm rounded flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Grid className="w-3.5 h-3.5 text-outline" />
              <span>▦ 2000×2000 World Canvas</span>
            </button>
          </div>

          <span className="text-outline-variant font-label-sm mx-1">|</span>

          {/* Interactive 3D Orbit Help & Reset Button */}
          <div className="flex items-center gap-2 bg-surface-container-lowest px-2 py-0.5 rounded border border-outline-variant/40 font-mono text-[10px] text-outline">
            <span className="text-primary font-semibold">Orbit: Left-Drag</span>
            <span>•</span>
            <span>Pan: Right-Drag</span>
            <span>•</span>
            <span>Zoom: Scroll</span>
            <button
              type="button"
              onClick={handleResetCamera}
              className="ml-1 px-1.5 py-0.5 bg-surface-container hover:bg-surface-container-high text-on-surface rounded flex items-center gap-1 text-[10px] border border-outline-variant/60 cursor-pointer"
              title="Reset 3D camera to default orientation"
            >
              <RefreshCw className="w-3 h-3 text-secondary" />
              <span>RESET 3D</span>
            </button>
          </div>
        </div>

        {/* Viewport 3D Element Toggles */}
        <div className="flex items-center gap-space-md font-label-sm text-[11px]">
          <label className="flex items-center gap-1 cursor-pointer text-primary">
            <input
              type="checkbox"
              checked={toggleFrustum}
              onChange={(e) => setToggleFrustum(e.target.checked)}
              className="w-3.5 h-3.5 accent-primary bg-surface-container-lowest rounded-sm cursor-pointer"
            />
            <span className="font-semibold">Frustum Cone</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer text-secondary">
            <input
              type="checkbox"
              checked={toggleGrid}
              onChange={(e) => setToggleGrid(e.target.checked)}
              className="w-3.5 h-3.5 accent-secondary bg-surface-container-lowest rounded-sm cursor-pointer"
            />
            <span className="font-semibold">Polar Azimuth Grid</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer text-tertiary">
            <input
              type="checkbox"
              checked={toggleLos}
              onChange={(e) => setToggleLos(e.target.checked)}
              className="w-3.5 h-3.5 accent-tertiary bg-surface-container-lowest rounded-sm cursor-pointer"
            />
            <span className="font-semibold">LOS Vector</span>
          </label>

          <div className="h-4 w-px bg-outline-variant" />

          <div className="font-label-sm text-[11px] text-tertiary flex items-center gap-1 bg-surface-container-lowest px-2 py-0.5 rounded border border-tertiary/30 font-semibold">
            <Lock className="w-3 h-3 text-tertiary" />
            <span>HIL SYNCHRONIZED</span>
          </div>
        </div>
      </div>

      {/* ── Primary Workspace Content Grid ── */}
      <div className="p-space-sm grid grid-cols-1 lg:grid-cols-12 gap-gutter items-stretch">
        {/* Central 3D Canvas Column (~65% -> 8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-gutter">
          {/* Real Interactive 3D WebGL Canvas Viewport (Item 1.w) */}
          <div className="bg-surface-container-lowest rounded overflow-hidden shadow-md flex flex-col relative select-none border border-outline-variant/40">
            {/* Canvas Top Metric Ribbon */}
            <div className="bg-surface-container-low px-space-md py-1 flex items-center justify-between font-label-sm text-[11px] border-b border-outline-variant/40">
              <div className="flex items-center gap-space-sm font-mono flex-wrap">
                <div className="flex items-center gap-1 bg-surface-container-lowest text-tertiary px-2 py-0.5 rounded border border-tertiary/40 font-bold text-[10px] tracking-wide">
                  <span className={`w-1.5 h-1.5 rounded-full ${status.isRunning ? 'bg-tertiary animate-pulse' : 'bg-outline'}`} />
                  <span>
                    {status.isRunning ? '3D GIMBAL SERVO TRACKING' : 'GIMBAL STANDBY'}
                  </span>
                </div>
                <span className="text-outline-variant">|</span>
                <div className="flex items-center gap-1">
                  <span className="text-outline">AZ:</span>
                  <span className="text-primary font-bold">{(telemetry.panAngleDeg || 0.0).toFixed(2)}°</span>
                </div>
                <span className="text-outline-variant">|</span>
                <div className="flex items-center gap-1">
                  <span className="text-outline">EL:</span>
                  <span className="text-on-surface font-semibold">{(telemetry.tiltAngleDeg || 0.0).toFixed(2)}°</span>
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
                  ECEF_NED_TOPO
                </span>
                <span>OGS-BLR-0482</span>
              </div>
            </div>

            {/* Three.js Mounting Container */}
            <div className="relative w-full h-[580px] bg-[#06090d] overflow-hidden flex items-center justify-center">
              <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

              {/* Repositioned Non-Obtrusive Gimbal HUD (Item 1.m: top-right with backdrop-blur, does not hide beacon) */}
              <div className="absolute top-3 right-3 z-20 w-56 bg-surface-container-low/90 backdrop-blur rounded p-space-xs shadow-xl pointer-events-auto border border-outline-variant/40">
                <div className="flex items-center justify-between pb-1 border-b border-outline-variant/30">
                  <div className="flex items-center gap-1.5">
                    <Sliders className="w-3.5 h-3.5 text-secondary" />
                    <span className="font-label-sm text-label-sm font-semibold text-on-surface uppercase tracking-wider">
                      Gimbal HUD
                    </span>
                  </div>
                  <span className={`px-1 py-0.2 font-label-sm text-[9px] font-bold rounded border ${status.isRunning ? 'bg-tertiary/15 text-tertiary border-tertiary/30' : 'bg-surface-container text-outline border-outline-variant/30'}`}>
                    {status.isRunning ? 'TRACKING OK' : 'STANDBY'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 mt-space-xs font-label-sm text-[11px]">
                  <div className="text-outline">AZIMUTH (θ)</div>
                  <div className="text-right font-mono text-secondary font-semibold">
                    {(telemetry.panAngleDeg || 0.0).toFixed(4)}°
                  </div>
                  <div className="text-outline">ELEVATION (φ)</div>
                  <div className="text-right font-mono text-secondary font-semibold">
                    {(telemetry.tiltAngleDeg || 0.0) >= 0 ? `+${(telemetry.tiltAngleDeg || 0.0).toFixed(4)}` : (telemetry.tiltAngleDeg || 0.0).toFixed(4)}°
                  </div>
                  <div className="text-outline">AZ SLEW RATE</div>
                  <div className="text-right font-mono text-on-surface">
                    {status.isRunning ? `${Math.abs(telemetry.panAngleDeg * 0.05 + 2.1).toFixed(3)} °/s` : '0.000 °/s'}
                  </div>
                  <div className="text-outline">SLANT RANGE</div>
                  <div className="text-right font-mono text-primary font-bold">2,450.0 m</div>
                </div>
              </div>

              {/* Top-Left Coordinate Frame Badge */}
              <div className="absolute top-3 left-3 bg-surface-container-lowest/90 px-space-sm py-1 rounded text-on-surface font-label-sm text-[10px] space-y-0.5 shadow select-none border border-outline-variant/30 z-20 pointer-events-none">
                <div className="flex items-center gap-1.5">
                  <span className="text-outline">STATION:</span>
                  <span className="text-primary font-bold">OGS-BLR (12.97° N, 77.59° E)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-outline">ENCODER:</span>
                  <span className="text-secondary font-mono">RESA360 26-BIT DUAL</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-outline">SERVO POLL:</span>
                  <span className="text-tertiary font-mono">1000 Hz HIL SYNC</span>
                </div>
              </div>

              {/* Floating Picture-in-Picture 2D Camera Feed in 3D Viewport (Item 4) */}
              <div className="absolute bottom-3 right-3 z-20 w-60 bg-surface-container-low/95 backdrop-blur rounded border border-outline-variant/50 shadow-2xl p-1.5 flex flex-col gap-1 select-none pointer-events-auto">
                <div className="flex items-center justify-between pb-1 border-b border-outline-variant/30 text-[10px] font-mono">
                  <div className="flex items-center gap-1.5 font-bold text-on-surface">
                    <Video className="w-3 h-3 text-primary" />
                    <span>2D FPA SENSOR FEED</span>
                  </div>
                  <span className={`px-1 py-0.2 rounded text-[9px] font-bold ${status.isRunning ? 'bg-secondary/20 text-secondary' : 'bg-surface-container text-outline'}`}>
                    {status.isRunning ? 'LIVE 30 FPS' : 'STANDBY'}
                  </span>
                </div>
                {/* Live Video Canvas / Reticle */}
                <div className="relative w-full aspect-[4/3] bg-surface-dim rounded overflow-hidden flex items-center justify-center border border-outline-variant/30">
                  {latestFrame && latestFrame.data ? (
                    <img src={latestFrame.data} alt="2D Feed" className="w-full h-full object-contain" />
                  ) : (
                    <div className="text-[10px] text-outline font-mono flex flex-col items-center gap-0.5">
                      <span>640×480 MONO</span>
                      <span className="text-[9px] text-outline/60">{status.isRunning ? 'STREAMING...' : 'STANDBY READY'}</span>
                    </div>
                  )}
                  {/* Aiming Reticle OSD Overlay */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 640 480">
                    <line x1="280" y1="240" x2="360" y2="240" stroke="#4cd7f6" strokeWidth="1.5" />
                    <line x1="320" y1="200" x2="320" y2="280" stroke="#4cd7f6" strokeWidth="1.5" />
                    <circle cx="320" cy="240" r="40" fill="none" stroke="#253241" strokeWidth="1" strokeDasharray="3,3" />
                    {telemetry.centroid?.x !== null && telemetry.centroid?.x !== undefined && (
                      <g transform={`translate(${telemetry.centroid.x}, ${telemetry.centroid.y})`}>
                        <circle r="8" fill="none" stroke="#f43f5e" strokeWidth="1.5" />
                        <circle r="2.5" fill="#4edea3" />
                      </g>
                    )}
                  </svg>
                </div>
                <div className="flex items-center justify-between text-[9px] font-mono text-outline pt-0.5">
                  <span>FOV: 4.0°×3.0°</span>
                  <span className="text-secondary font-semibold">
                    {telemetry.centroid?.x !== null && telemetry.centroid?.x !== undefined
                      ? `Δ: (${(telemetry.centroid.x - 320).toFixed(1)}, ${(telemetry.centroid.y! - 240).toFixed(1)}) px`
                      : 'BORESIGHT 0.0 px'}
                  </span>
                </div>
              </div>
            </div>

            {/* Viewport Bottom Configuration Bar */}
            <div className="bg-surface-container-low px-space-md py-1.5 flex flex-wrap items-center justify-between font-label-sm text-[11px] text-on-surface-variant border-t border-outline-variant/30">
              <div className="flex items-center gap-space-md">
                <span>
                  AZ LIMIT: <strong className="text-on-surface font-mono">±270.0°</strong>
                </span>
                <span className="text-outline-variant">|</span>
                <span>
                  EL LIMIT: <strong className="text-on-surface font-mono">-5.0° ~ +95.0°</strong>
                </span>
                <span className="text-outline-variant">|</span>
                <span>
                  GEAR RATIO: <strong className="text-tertiary font-mono">1:100 HARMONIC</strong>
                </span>
              </div>
              <div className="flex items-center gap-space-md">
                <span>
                  OPTICAL BEAM: <strong className="text-secondary font-mono">4.00° × 3.00° RECT PYRAMID</strong>
                </span>
              </div>
            </div>
          </div>

          {/* Synchronized PIP Cards: 2D Sensor View & 2000x2000 World Canvas */}
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
                    <radialGradient cx="50%" cy="50%" id="miniPipFpaPed" r="50%">
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
                        <circle cx={spotX} cy={spotY} r="12" fill="url(#miniPipFpaPed)" />
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

            {/* PIP 2: 2000x2000 World Canvas */}
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
              <div className="bg-surface-container-lowest rounded h-28 relative overflow-hidden flex items-center justify-center border border-outline-variant/30 select-none">
                <svg className="w-full h-full" viewBox="0 0 320 110" xmlns="http://www.w3.org/2000/svg">
                  {/* Grid Lines */}
                  <g stroke="#1a232c" strokeWidth="0.8">
                    <line x1="40" y1="0" x2="40" y2="110" />
                    <line x1="100" y1="0" x2="100" y2="110" />
                    <line x1="160" y1="0" x2="160" y2="110" />
                    <line x1="220" y1="0" x2="220" y2="110" />
                    <line x1="280" y1="0" x2="280" y2="110" />
                    <line x1="0" y1="28" x2="320" y2="28" />
                    <line x1="0" y1="55" x2="320" y2="55" />
                    <line x1="0" y1="82" x2="320" y2="82" />
                  </g>
                  {/* OGS Origin at Center */}
                  <circle cx="160" cy="55" r="3.5" fill="#0284c7" />
                  <circle cx="160" cy="55" r="8" fill="none" stroke="#0284c7" strokeWidth="0.8" strokeDasharray="2,2" />
                  <text x="166" y="53" fill="#8c909f" fontFamily="JetBrains Mono" fontSize="7.5">
                    OGS-BLR
                  </text>
                  {/* Uncertainty Envelope R=460px mapped */}
                  <circle cx="160" cy="55" r="36" fill="rgba(202, 129, 0, 0.05)" stroke="#ffb95f" strokeWidth="1" strokeDasharray="3,2" />
                  {/* Dynamic Target Position in World Grid */}
                  {(() => {
                    const pan = telemetry.panAngleDeg || 0.0
                    const tilt = telemetry.tiltAngleDeg || 0.0
                    const targetX = 160 + (pan / 6.25) * 60
                    const targetY = 55 + (tilt / 4.68) * 30
                    return (
                      <g>
                        <circle cx={targetX} cy={targetY} r="3" fill="#4edea3" />
                        <line x1="160" y1="55" x2={targetX} y2={targetY} stroke="#93ccff" strokeWidth="1" strokeDasharray="2,2" />
                        <text x={targetX + 6} y={targetY + 3} fill="#4edea3" fontFamily="JetBrains Mono" fontSize="7.5">
                          BEACON
                        </text>
                      </g>
                    )
                  })()}
                  <text x="8" y="14" fill="#8c909f" fontFamily="JetBrains Mono" fontSize="8">
                    2000×2000 WCS FIELD
                  </text>
                  <text x="8" y="104" fill="#ffb95f" fontFamily="JetBrains Mono" fontSize="8">
                    ENV: R≤460px
                  </text>
                  <text x="235" y="104" fill="#adc6ff" fontFamily="JetBrains Mono" fontSize="8">
                    OGS-BLR-0482
                  </text>
                </svg>
              </div>
              <div className="mt-space-xs pt-space-xs flex items-center justify-between font-label-sm text-[10px] text-on-surface-variant font-mono">
                <span>RANGE: [0, 2000] px</span>
                <span>SCALE: 160.0 px/deg</span>
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

export default PedestalFrustumView
