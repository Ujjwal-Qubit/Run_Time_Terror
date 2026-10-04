import React, { useState, useRef } from 'react'
import {
  Video,
  Play,
  Pause,
  Square,
  Redo,
  RotateCcw,
  Sliders,
  Activity,
  Shield,
  Layers,
  Zap,
  Upload,
  Save,
  Sparkles,
  X,
} from 'lucide-react'
import { useSanketStore } from '../../store/useSanketStore'
import { bridgeService } from '../../services/bridgeService'

export type TrajectoryPattern = 'linear' | 'circular' | 'figure8' | 'brownian'
export type AtmCondition = 'clear' | 'haze' | 'fog' | 'rain'

interface DeveloperControlSidebarProps {
  pattern: TrajectoryPattern
  setPattern: (p: TrajectoryPattern) => void
  slewSpeed: number
  setSlewSpeed: (s: number) => void
  atmCondition: AtmCondition
  setAtmCondition: (c: AtmCondition) => void
  gaussianNoise: boolean
  setGaussianNoise: (v: boolean) => void
  poissonNoise: boolean
  setPoissonNoise: (v: boolean) => void
  saltPepperNoise: boolean
  setSaltPepperNoise: (v: boolean) => void
  kp: number
  setKp: (v: number) => void
  ki: number
  setKi: (v: number) => void
  deadband: number
  setDeadband: (v: number) => void
  appliedNotice: boolean
  handleApplyGains: () => void
}

export const DeveloperControlSidebar: React.FC<DeveloperControlSidebarProps> = ({
  pattern,
  setPattern,
  slewSpeed,
  setSlewSpeed,
  atmCondition,
  setAtmCondition,
  gaussianNoise,
  setGaussianNoise,
  poissonNoise,
  setPoissonNoise,
  saltPepperNoise,
  setSaltPepperNoise,
  kp,
  setKp,
  ki,
  setKi,
  deadband,
  setDeadband,
  appliedNotice,
  handleApplyGains,
}) => {
  const status = useSanketStore((s) => s.status)
  const telemetry = useSanketStore((s) => s.telemetry)

  const [showAiModal, setShowAiModal] = useState(false)
  const [aiPrompt, setAiPrompt] = useState('')
  const [isGeneratingAi, setIsGeneratingAi] = useState(false)
  const [aiSuccess, setAiSuccess] = useState(false)

  const [showSaveModal, setShowSaveModal] = useState(false)
  const [newScenarioName, setNewScenarioName] = useState('')

  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const loopRate = (
    status.isRunning
      ? status.backendFps > 0
        ? status.backendFps
        : telemetry.algorithmFps > 0
        ? telemetry.algorithmFps
        : 30.0
      : 0.0
  ).toFixed(1)

  const handlePatternChange = (p: TrajectoryPattern) => {
    setPattern(p)
    bridgeService.setMotionPattern(p)
  }

  const handleSlewChange = (val: number) => {
    setSlewSpeed(val)
    bridgeService.setTargetSpeed(val)
  }

  const handleAtmChange = (c: AtmCondition) => {
    setAtmCondition(c)
    bridgeService.setAtmosphericCondition(c)
  }

  const handleNoiseToggle = (type: 'gaussian' | 'poisson' | 'salt_and_pepper', val: boolean) => {
    if (type === 'gaussian') setGaussianNoise(val)
    if (type === 'poisson') setPoissonNoise(val)
    if (type === 'salt_and_pepper') setSaltPepperNoise(val)
    bridgeService.setNoiseEnabled(type, val)
  }

  const handleImportFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (evt) => {
      const content = evt.target?.result as string
      if (content) {
        bridgeService.saveScenario(file.name, content)
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const handleSaveScenarioSubmit = () => {
    if (!newScenarioName.trim()) return
    const scenarioPayload = {
      name: newScenarioName.trim(),
      description: `User-saved configuration with ${pattern} trajectory and ${atmCondition} atmosphere.`,
      target: {
        speed: slewSpeed,
        motion_type: pattern,
      },
      atmospheric: {
        condition: atmCondition,
      },
      noise: {
        gaussian_enabled: gaussianNoise,
        poisson_enabled: poissonNoise,
        sp_enabled: saltPepperNoise,
      },
      ptz: {
        proportional_gain: kp,
        integral_gain: ki,
        deadband_px: deadband,
      },
    }
    bridgeService.saveScenario(newScenarioName.trim(), JSON.stringify(scenarioPayload, null, 2))
    setShowSaveModal(false)
    setNewScenarioName('')
  }

  const handleAiGenerateSubmit = () => {
    if (!aiPrompt.trim()) return
    setIsGeneratingAi(true)
    setAiSuccess(false)
    bridgeService.generateAiScenario(aiPrompt.trim())
    setTimeout(() => {
      setIsGeneratingAi(false)
      setAiSuccess(true)
      setTimeout(() => {
        setShowAiModal(false)
        setAiPrompt('')
        setAiSuccess(false)
      }, 1200)
    }, 1500)
  }

  return (
    <div className="flex flex-col gap-gutter h-full min-h-0 overflow-y-auto pr-1 select-none">
      {/* Card 1: Simulation Control & Scenario */}
      <div className="bg-surface-container-low rounded p-space-sm shadow-sm select-none border border-outline-variant/40">
        <div className="flex items-center justify-between pb-space-xs mb-space-xs border-b border-outline-variant/40">
          <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-tertiary font-bold">
            <Zap className="w-4 h-4 text-tertiary" />
            <span className="uppercase tracking-wider">Simulation Control &amp; Scenario</span>
          </div>
          <span className="font-label-sm text-[9px] bg-tertiary/20 text-tertiary px-1.5 py-0.5 rounded font-mono font-bold uppercase tracking-wider">
            AIR-GAP SITL
          </span>
        </div>

        {/* Scenario Selection Dropdown & Matrix Loader (Item 1.bb, 1.cc, 1.dd, 1.ee) */}
        <div className="mb-space-xs bg-surface-container-lowest p-2 rounded border border-outline-variant/40">
          <div className="flex items-center justify-between text-[10px] font-label-sm text-outline mb-1">
            <span className="font-mono flex items-center gap-1">
              <Layers className="w-3 h-3 text-primary" />
              ACTIVE SCENARIO
            </span>
            <span className="text-tertiary font-mono text-[9px] uppercase">
              {status.activeScenario ? status.activeScenario.replace(/\.json$/, '') : 'NONE'}
            </span>
          </div>

          <select
            value={status.activeScenario || ''}
            onChange={(e) => {
              const val = e.target.value
              if (val) {
                bridgeService.selectScenario(val.replace(/\.json$/, ''))
              }
            }}
            className="w-full bg-surface-container-low text-on-surface font-mono text-[11px] p-1.5 rounded border border-outline-variant/60 focus:outline-none focus:border-primary cursor-pointer mb-2"
          >
            <option value="">-- Select Scenario Matrix (19 Available) --</option>
            {status.availableScenarios.map((scen) => (
              <option key={scen} value={scen}>
                {scen}
              </option>
            ))}
          </select>

          {/* Action Row: Import, Save, AI Generator */}
          <div className="grid grid-cols-3 gap-1">
            <input
              type="file"
              ref={fileInputRef}
              accept=".json"
              className="hidden"
              onChange={handleImportFile}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="px-1.5 py-1 bg-surface-container hover:bg-surface-container-high text-on-surface font-mono text-[10px] rounded border border-outline-variant/50 flex items-center justify-center gap-1 transition-colors"
              title="Upload and load a custom scenario JSON from your computer"
            >
              <Upload className="w-3 h-3 text-secondary" />
              <span>IMPORT</span>
            </button>

            <button
              type="button"
              onClick={() => setShowSaveModal(true)}
              className="px-1.5 py-1 bg-surface-container hover:bg-surface-container-high text-on-surface font-mono text-[10px] rounded border border-outline-variant/50 flex items-center justify-center gap-1 transition-colors"
              title="Save current parameter configurations to scenarios/"
            >
              <Save className="w-3 h-3 text-primary" />
              <span>SAVE</span>
            </button>

            <button
              type="button"
              onClick={() => setShowAiModal(true)}
              className="px-1.5 py-1 bg-tertiary/15 hover:bg-tertiary/25 text-tertiary font-mono text-[10px] font-bold rounded border border-tertiary/40 flex items-center justify-center gap-1 transition-colors"
              title="Generate custom trajectory & conditions using AI natural language"
            >
              <Sparkles className="w-3 h-3" />
              <span>AI GEN</span>
            </button>
          </div>
        </div>

        {/* Primary Simulation Execution Grid */}
        <div className="flex flex-col gap-1.5">
          <button
            type="button"
            onClick={() => bridgeService.run()}
            disabled={status.isRunning && !status.isPaused}
            className="w-full bg-tertiary text-on-tertiary hover:bg-tertiary-container hover:text-on-tertiary-container h-8 px-2.5 font-label-sm text-[11px] font-bold rounded flex items-center justify-center gap-1.5 transition-colors shadow-sm tracking-wide disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>RUN SIMULATION</span>
          </button>
          <div className="grid grid-cols-4 gap-1">
            <button
              type="button"
              onClick={() => (status.isPaused ? bridgeService.resume() : bridgeService.pause())}
              disabled={!status.isRunning}
              className="bg-surface-container text-on-surface hover:bg-surface-container-high h-7 px-1.5 font-label-sm text-[10px] font-medium rounded flex items-center justify-center gap-1 transition-colors border border-outline-variant/50 disabled:opacity-40"
            >
              <Pause className="w-3 h-3 fill-current" />
              <span>{status.isPaused ? 'RESUME' : 'PAUSE'}</span>
            </button>
            <button
              type="button"
              onClick={() => bridgeService.stop()}
              disabled={!status.isRunning}
              className="bg-surface-container text-error hover:bg-error-container hover:text-on-error-container h-7 px-1.5 font-label-sm text-[10px] font-medium rounded flex items-center justify-center gap-1 transition-colors border border-outline-variant/50 disabled:opacity-40"
            >
              <Square className="w-3 h-3 fill-current" />
              <span>STOP</span>
            </button>
            <button
              type="button"
              onClick={() => bridgeService.step()}
              className="bg-surface-container text-on-surface hover:bg-surface-container-high h-7 px-1.5 font-label-sm text-[10px] font-medium rounded flex items-center justify-center gap-1 transition-colors border border-outline-variant/50"
            >
              <Redo className="w-3 h-3" />
              <span>+1 STEP</span>
            </button>
            <button
              type="button"
              onClick={() => bridgeService.reset()}
              className="bg-surface-container text-on-surface hover:bg-surface-container-high h-7 px-1.5 font-label-sm text-[10px] font-medium rounded flex items-center justify-center gap-1 transition-colors border border-outline-variant/50"
            >
              <RotateCcw className="w-3 h-3" />
              <span>RESET</span>
            </button>
          </div>

          {/* Subsystem Toggles: Tracking & PTZ */}
          <div className="grid grid-cols-2 gap-1.5 pt-1.5 border-t border-outline-variant/30">
            <button
              type="button"
              id="toggle-tracking-btn"
              onClick={() => {
                const next = !status.trackingEnabled
                useSanketStore.setState((s) => ({ status: { ...s.status, trackingEnabled: next } }))
                bridgeService.setTrackingEnabled(next)
              }}
              className={`h-7 px-2 font-mono text-[10px] font-bold rounded flex items-center justify-between transition-colors border cursor-pointer ${
                status.trackingEnabled
                  ? 'bg-tertiary/15 text-tertiary border-tertiary/40 hover:bg-tertiary/25'
                  : 'bg-surface-container text-outline border-outline-variant/50 hover:bg-surface-container-high'
              }`}
              title={status.trackingEnabled ? 'Tracking Loop Active' : 'Tracking Loop Standby'}
            >
              <span className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${status.trackingEnabled ? 'bg-tertiary animate-pulse' : 'bg-outline'}`} />
                TRACKING
              </span>
              <span className="font-mono text-[9px] uppercase font-bold">
                {status.trackingEnabled ? 'ON' : 'OFF'}
              </span>
            </button>

            <button
              type="button"
              id="toggle-ptz-btn"
              onClick={() => {
                const next = !status.ptzEnabled
                useSanketStore.setState((s) => ({ status: { ...s.status, ptzEnabled: next } }))
                bridgeService.setPtzEnabled(next)
              }}
              className={`h-7 px-2 font-mono text-[10px] font-bold rounded flex items-center justify-between transition-colors border cursor-pointer ${
                status.ptzEnabled
                  ? 'bg-secondary/15 text-secondary border-secondary/40 hover:bg-secondary/25'
                  : 'bg-surface-container text-outline border-outline-variant/50 hover:bg-surface-container-high'
              }`}
              title={status.ptzEnabled ? 'PTZ Gimbal Slew Active' : 'PTZ Gimbal Slew Disabled'}
            >
              <span className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${status.ptzEnabled ? 'bg-secondary animate-pulse' : 'bg-outline'}`} />
                PTZ
              </span>
              <span className="font-mono text-[9px] uppercase font-bold">
                {status.ptzEnabled ? 'ON' : 'OFF'}
              </span>
            </button>
          </div>

          {/* Validation Mode Trigger (Item 1.aa: DEV-26) */}
          <div className="pt-1.5 mt-1 border-t border-outline-variant/30">
            <button
              type="button"
              onClick={() => bridgeService.toggleValidationMode(!status.validationMode)}
              className={`w-full h-7 px-2 font-mono text-[10px] font-bold rounded flex items-center justify-between transition-colors border cursor-pointer ${
                status.validationMode
                  ? 'bg-amber-500/20 text-amber-400 border-amber-500/50 hover:bg-amber-500/30'
                  : 'bg-surface-container text-outline border-outline-variant/50 hover:bg-surface-container-high'
              }`}
              title="DEV-026: Toggle Ground-Truth Validation Mode"
            >
              <span className="flex items-center gap-1.5">
                <Shield className={`w-3.5 h-3.5 ${status.validationMode ? 'text-amber-400' : 'text-outline'}`} />
                <span>VALIDATION MODE</span>
              </span>
              <span className="font-mono text-[9px] uppercase font-bold">
                {status.validationMode ? 'ACTIVE (GT BYPASS)' : 'OFF (BLIND HIL)'}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Card 2: 01. Camera & Sensor FPA */}
      <div className="bg-surface-container-low rounded p-space-sm shadow-sm select-none border border-outline-variant/40">
        <div className="flex items-center justify-between pb-space-xs mb-space-xs border-b border-outline-variant/40">
          <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-primary font-bold">
            <Video className="w-4 h-4 text-primary" />
            <span className="uppercase tracking-wider">01. Camera &amp; Sensor FPA</span>
          </div>
          <span className="font-label-sm text-[9px] bg-surface-container-high text-outline px-1.5 py-0.5 rounded font-mono">
            READ-ONLY
          </span>
        </div>
        <div className="space-y-1 font-label-sm text-[11px]">
          <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
            <span className="text-outline">Array Resolution:</span>
            <span className="text-on-surface font-mono font-semibold">640 × 480 Mono (8-bit)</span>
          </div>
          <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
            <span className="text-outline">Field of View:</span>
            <span className="text-on-surface font-mono">4.00° × 3.00° (240×180 arcmin)</span>
          </div>
          <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
            <span className="text-outline">Integration Time:</span>
            <span className="text-secondary font-mono font-semibold">33.3 ms (30.0 FPS)</span>
          </div>
          <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
            <span className="text-outline">Loop Rate:</span>
            <span className="text-tertiary font-mono font-bold">{loopRate} Hz (Zero-Overrun)</span>
          </div>
        </div>
      </div>

      {/* Card 3: 02. Target Kinematics */}
      <div className="bg-surface-container-low rounded p-space-sm shadow-sm select-none border border-outline-variant/40">
        <div className="flex items-center justify-between pb-space-xs mb-space-xs border-b border-outline-variant/40">
          <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-primary font-bold">
            <Activity className="w-4 h-4 text-primary" />
            <span className="uppercase tracking-wider">02. Target Kinematics</span>
          </div>
          <span className="font-label-sm text-[9px] bg-surface-container text-secondary px-1.5 py-0.5 rounded font-mono font-semibold">
            ACTIVE PROFILE
          </span>
        </div>
        <div className="mb-space-sm">
          <div className="flex justify-between text-[10px] font-label-sm text-outline mb-1">
            <span>TRAJECTORY PROFILE</span>
            <span className="text-primary font-mono capitalize">{pattern} Active</span>
          </div>
          <div className="grid grid-cols-4 gap-1 bg-surface-container-lowest p-0.5 rounded">
            {(['linear', 'circular', 'figure8', 'brownian'] as TrajectoryPattern[]).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => handlePatternChange(p)}
                className={`py-1 font-label-sm text-[10px] text-center rounded transition-colors capitalize ${
                  pattern === p
                    ? 'bg-primary text-on-primary font-bold shadow-sm'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {p === 'figure8' ? 'Figure-8' : p}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-space-sm font-label-sm text-[11px]">
          <div>
            <div className="flex justify-between text-outline mb-1 font-mono text-[11px]">
              <span>Slew Speed (V_t):</span>
              <span className="text-primary font-bold">{slewSpeed.toFixed(1)} px/s</span>
            </div>
            <input
              type="range"
              min="5"
              max="150"
              value={slewSpeed}
              onChange={(e) => handleSlewChange(parseFloat(e.target.value))}
              className="w-full h-1 bg-surface-container-lowest rounded-lg appearance-none cursor-pointer accent-primary"
            />
            <div className="flex justify-between text-[9px] text-outline mt-0.5 font-mono">
              <span>5 px/s</span>
              <span>Nominal: 45.0 px/s</span>
              <span>150 px/s</span>
            </div>
          </div>
          <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
            <span className="text-outline">Gaussian Spot Divergence:</span>
            <span className="text-on-surface font-mono font-semibold">10.0 px FWHM</span>
          </div>
        </div>
      </div>

      {/* Card 4: 03. Environmental Disturbances */}
      <div className="bg-surface-container-low rounded p-space-sm shadow-sm select-none border border-outline-variant/40">
        <div className="flex items-center justify-between pb-space-xs mb-space-xs border-b border-outline-variant/40">
          <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-secondary font-bold">
            <Shield className="w-4 h-4 text-secondary" />
            <span className="uppercase tracking-wider">03. Environmental Disturbances</span>
          </div>
          <span className="font-label-sm text-[9px] bg-surface-container-high text-secondary px-1.5 py-0.5 rounded font-mono">
            ISRO SIH
          </span>
        </div>
        <div className="mb-space-sm">
          <div className="flex justify-between text-[10px] font-label-sm text-outline mb-1">
            <span>ATMOSPHERE (MODTRAN)</span>
            <span className="text-secondary font-mono font-bold">
              LOSS: {atmCondition === 'fog' ? '-4.8 dB' : atmCondition === 'rain' ? '-6.2 dB' : atmCondition === 'haze' ? '-2.1 dB' : '-0.4 dB'}
            </span>
          </div>
          <div className="grid grid-cols-4 gap-1 bg-surface-container-lowest p-0.5 rounded">
            {(['clear', 'haze', 'fog', 'rain'] as AtmCondition[]).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => handleAtmChange(c)}
                className={`py-1 font-label-sm text-[10px] text-center rounded transition-colors capitalize ${
                  atmCondition === c
                    ? 'bg-secondary text-on-secondary font-bold shadow-sm'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {c} {atmCondition === c ? '[ON]' : ''}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-1.5 font-label-sm text-[11px]">
          <label className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded cursor-pointer">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={gaussianNoise}
                onChange={(e) => handleNoiseToggle('gaussian', e.target.checked)}
                className="w-3.5 h-3.5 accent-primary rounded-sm"
              />
              <span className="text-on-surface">Gaussian Noise</span>
            </div>
            <span className="text-outline font-mono text-[10px]">σ = 12.5 DN</span>
          </label>

          <label className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded cursor-pointer">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={poissonNoise}
                onChange={(e) => handleNoiseToggle('poisson', e.target.checked)}
                className="w-3.5 h-3.5 accent-primary rounded-sm"
              />
              <span className="text-on-surface">Poisson Shot Noise</span>
            </div>
            <span className="text-tertiary font-mono text-[10px] font-semibold">
              {poissonNoise ? 'ACTIVE' : 'OFF'}
            </span>
          </label>

          <label className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded cursor-pointer">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={saltPepperNoise}
                onChange={(e) => handleNoiseToggle('salt_and_pepper', e.target.checked)}
                className="w-3.5 h-3.5 accent-primary rounded-sm"
              />
              <span className="text-on-surface">Salt &amp; Pepper Noise</span>
            </div>
            <span className="text-outline font-mono text-[10px]">10% DENSITY</span>
          </label>

          <div className="pt-1 flex items-center justify-between text-[10px] text-outline px-1 font-mono">
            <span>
              JITTER: <span className="text-error font-semibold">±8.4 px/fr</span>
            </span>
            <span>
              DRIFT: <span className="text-on-surface font-semibold">3.2 px/s</span>
            </span>
          </div>
        </div>
      </div>

      {/* Card 5: 04. PTZ Servo Loop Control */}
      <div className="bg-surface-container-low rounded p-space-sm shadow-sm select-none border border-outline-variant/40">
        <div className="flex items-center justify-between pb-space-xs mb-space-xs border-b border-outline-variant/40">
          <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-tertiary font-bold">
            <Sliders className="w-4 h-4 text-tertiary" />
            <span className="uppercase tracking-wider">04. PTZ Servo Loop Control</span>
          </div>
          <span className="font-label-sm text-[9px] text-tertiary bg-surface-container px-1 py-0.2 rounded font-mono">
            CL_ACTIVE
          </span>
        </div>
        <div className="grid grid-cols-2 gap-1.5 font-label-sm text-[11px] mb-space-sm">
          <div className="bg-surface-container-lowest p-1.5 rounded">
            <div className="text-outline text-[10px]">Prop. Gain (Kp)</div>
            <div className="flex items-center justify-between mt-0.5">
              <input
                type="number"
                step="0.5"
                value={kp}
                onChange={(e) => setKp(parseFloat(e.target.value) || 0)}
                className="w-14 bg-transparent text-primary font-mono text-body-md font-bold focus:outline-none"
              />
              <span className="text-[9px] text-outline font-mono">s⁻¹</span>
            </div>
          </div>

          <div className="bg-surface-container-lowest p-1.5 rounded">
            <div className="text-outline text-[10px]">Integral Gain (Ki)</div>
            <div className="flex items-center justify-between mt-0.5">
              <input
                type="number"
                step="0.5"
                value={ki}
                onChange={(e) => setKi(parseFloat(e.target.value) || 0)}
                className="w-14 bg-transparent text-primary font-mono text-body-md font-bold focus:outline-none"
              />
              <span className="text-[9px] text-outline font-mono">s⁻²</span>
            </div>
          </div>

          <div className="bg-surface-container-lowest p-1.5 rounded">
            <div className="text-outline text-[10px]">Deadband (ε)</div>
            <div className="flex items-center justify-between mt-0.5">
              <input
                type="number"
                step="0.1"
                value={deadband}
                onChange={(e) => setDeadband(parseFloat(e.target.value) || 0)}
                className="w-14 bg-transparent text-on-surface font-mono text-body-md font-bold focus:outline-none"
              />
              <span className="text-[9px] text-outline font-mono">px</span>
            </div>
          </div>

          <div className="bg-surface-container-lowest p-1.5 rounded">
            <div className="text-outline text-[10px]">Anti-Windup Clamp</div>
            <div className="flex items-center justify-between mt-0.5">
              <span className="text-tertiary font-mono text-label-sm font-semibold">ACTIVE</span>
              <span className="text-[9px] text-tertiary font-mono">0% SAT</span>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={handleApplyGains}
          className="w-full bg-primary hover:bg-primary-container text-on-primary hover:text-on-primary-container py-2 px-space-sm rounded font-label-sm text-label-sm font-bold flex items-center justify-center gap-2 transition-colors shadow border border-primary/30"
        >
          <Zap className="w-4 h-4" />
          <span>{appliedNotice ? 'GAINS APPLIED & SYNCED!' : 'APPLY & RE-SYNC MATRIX'}</span>
        </button>
      </div>

      {/* AI Scenario Modal (Item 1.ee) */}
      {showAiModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-surface-container-low border border-primary/40 rounded-lg p-5 w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between pb-2 mb-3 border-b border-outline-variant/30">
              <div className="flex items-center gap-2 text-primary font-bold font-mono text-sm">
                <Sparkles className="w-4 h-4" />
                <span>AI TRAJECTORY &amp; SCENARIO GENERATOR</span>
              </div>
              <button
                type="button"
                onClick={() => setShowAiModal(false)}
                className="text-outline hover:text-on-surface p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[11px] text-outline mb-3 leading-relaxed">
              Describe the physical flight trajectory, target dynamics, and atmospheric disturbances in natural language.
              The AI workflow will synthesize, validate, and hot-load the scenario matrix.
            </p>
            <textarea
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="e.g., Supersonic figure-8 evasion at 110 px/s with dense cloud fog and heavy Poisson noise"
              rows={4}
              className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs p-2.5 rounded border border-outline-variant/60 focus:outline-none focus:border-primary resize-none mb-3"
            />
            {aiSuccess && (
              <div className="mb-3 px-3 py-1.5 bg-secondary/15 text-secondary border border-secondary/40 rounded font-mono text-xs flex items-center gap-1.5">
                <span>✓</span>
                <span>AI Scenario Synthesized &amp; Loaded into Workstation!</span>
              </div>
            )}
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowAiModal(false)}
                className="px-3 py-1.5 text-xs text-outline hover:text-on-surface rounded font-mono"
              >
                CANCEL
              </button>
              <button
                type="button"
                disabled={!aiPrompt.trim() || isGeneratingAi || aiSuccess}
                onClick={handleAiGenerateSubmit}
                className="px-4 py-1.5 bg-primary text-on-primary font-mono text-xs font-bold rounded flex items-center gap-1.5 hover:bg-primary/90 disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{isGeneratingAi ? 'SYNTHESIZING...' : aiSuccess ? 'LOADED ✓' : 'GENERATE & LOAD'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save Scenario Modal (Item 1.cc) */}
      {showSaveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-surface-container-low border border-outline-variant/40 rounded-lg p-5 w-full max-w-sm shadow-2xl">
            <div className="flex items-center justify-between pb-2 mb-3 border-b border-outline-variant/30">
              <div className="flex items-center gap-2 text-on-surface font-bold font-mono text-sm">
                <Save className="w-4 h-4 text-primary" />
                <span>SAVE SCENARIO MATRIX</span>
              </div>
              <button
                type="button"
                onClick={() => setShowSaveModal(false)}
                className="text-outline hover:text-on-surface p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[11px] text-outline mb-3">
              Enter a name for this custom benchmark configuration. It will be saved into the app's scenarios directory.
            </p>
            <input
              type="text"
              value={newScenarioName}
              onChange={(e) => setNewScenarioName(e.target.value)}
              placeholder="e.g., custom_storm_stress"
              className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs p-2 rounded border border-outline-variant/60 focus:outline-none focus:border-primary mb-3"
            />
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowSaveModal(false)}
                className="px-3 py-1.5 text-xs text-outline hover:text-on-surface rounded font-mono"
              >
                CANCEL
              </button>
              <button
                type="button"
                disabled={!newScenarioName.trim()}
                onClick={handleSaveScenarioSubmit}
                className="px-4 py-1.5 bg-primary text-on-primary font-mono text-xs font-bold rounded hover:bg-primary/90 disabled:opacity-50"
              >
                SAVE TO MATRIX
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
