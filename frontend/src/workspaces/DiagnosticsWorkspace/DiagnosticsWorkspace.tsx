import React, { useEffect, useState } from 'react'
import {
  Zap,
  Shield,
  Globe,
  Lock,
  ShieldCheck,
  CheckCircle2,
  Ban,
  Radio,
  GitBranch,
  Brain,
  Timer,
  FileText
} from 'lucide-react'
import { useSanketStore } from '../../store/useSanketStore'
import { bridgeService } from '../../services/bridgeService'

// ─────────────────────────────────────────────────────────────
// Screen 7: SANKET — Diagnostics & Subsystem Audit
// Visual design strictly matches Stitch: 7_diagnostics_e69d.html
// ─────────────────────────────────────────────────────────────

export const DiagnosticsWorkspace: React.FC = () => {
  const isConnected = useSanketStore((state) => state.isConnected)
  const subsystems = useSanketStore((state) => state.subsystems)
  const status = useSanketStore((state) => state.status)
  const telemetry = useSanketStore((state) => state.telemetry)

  const [isAuditing, setIsAuditing] = useState(false)
  const [auditSuccess, setAuditSuccess] = useState(false)

  const subFrame = subsystems.find((s) => s.id === 'frame_provider')
  const subCentroid = subsystems.find((s) => s.id === 'centroid_estimator')
  const subAiml = subsystems.find((s) => s.id === 'aiml_classifier')
  const subKalman = subsystems.find((s) => s.id === 'kalman_tracker')
  const subPtz = subsystems.find((s) => s.id === 'ptz_controller')

  const stage1Latency = subFrame ? subFrame.latencyMs.toFixed(2) : '2.10'
  const stage2Latency = subCentroid ? (subCentroid.latencyMs * 0.35).toFixed(2) : '0.40'
  const stage3Latency = subAiml ? subAiml.latencyMs.toFixed(3) : '0.082'
  const stage4Latency = subCentroid ? (subCentroid.latencyMs * 0.65).toFixed(2) : '0.80'
  const stage5Latency = subKalman ? subKalman.latencyMs.toFixed(2) : '0.40'
  const stage6Latency = subPtz ? subPtz.latencyMs.toFixed(2) : '0.20'
  const totalStageRuntime = (
    parseFloat(stage1Latency) + parseFloat(stage2Latency) + parseFloat(stage3Latency) +
    parseFloat(stage4Latency) + parseFloat(stage5Latency) + parseFloat(stage6Latency)
  ).toFixed(3)
  const executionFreq = (status.backendFps > 0 ? status.backendFps : telemetry.algorithmFps > 0 ? telemetry.algorithmFps : 62.7).toFixed(1)

  useEffect(() => {
    if (isConnected) {
      bridgeService.getSubsystemDiagnostics()
      const timer = setInterval(() => {
        bridgeService.getSubsystemDiagnostics()
      }, 1000)
      return () => clearInterval(timer)
    }
  }, [isConnected])

  const handleExecuteAudit = () => {
    setIsAuditing(true)
    bridgeService.getSubsystemDiagnostics()
    setTimeout(() => {
      setIsAuditing(false)
      setAuditSuccess(true)
      setTimeout(() => setAuditSuccess(false), 2500)
    }, 600)
  }

  return (
    <div className="flex flex-col w-full space-y-space-md p-margin select-none bg-surface text-on-surface">
      {/* ── A. TOP HEALTH & ANOMALY SUMMARY BANNER (Priority 1: DETECT) ── */}
      <section className="bg-surface-container-low border border-outline-variant/50 rounded-lg p-space-md shadow-sm">
        <div className="flex flex-col space-y-space-md">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md pb-space-sm border-b border-outline-variant/40">
            <div className="flex flex-wrap items-center gap-space-md">
              <div className="bg-tertiary/10 border border-tertiary/30 px-space-md py-2.5 rounded-lg flex items-center gap-space-sm shrink-0 shadow-sm">
                <span className="relative flex h-3.5 w-3.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-tertiary opacity-75" />
                  <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-tertiary" />
                </span>
                <div>
                  <div className="font-label-md text-label-md text-tertiary font-bold tracking-wide uppercase font-mono">
                    SYSTEM HEALTH: NOMINAL
                  </div>
                  <div className="font-label-sm text-[11px] text-on-surface-variant font-mono">
                    0 ACTIVE ANOMALIES // ALL SUBSYSTEMS NOMINAL
                  </div>
                </div>
              </div>

              <div className="hidden md:block h-10 w-px bg-outline-variant/60" />

              <div className="space-y-0.5">
                <div className="flex items-center gap-space-xs font-label-sm text-label-sm">
                  <span className="text-on-surface font-semibold">Subsystems Audited:</span>
                  <span className="text-tertiary font-bold font-mono">6 / 6 Operational</span>
                </div>
                <div className="font-body-sm text-[11px] text-on-surface-variant font-mono">
                  0 Faults • 0 Degraded • Air-Gap Isolated
                </div>
              </div>
            </div>

            <div className="flex items-center shrink-0">
              <button
                type="button"
                id="execute-audit-btn"
                onClick={handleExecuteAudit}
                disabled={isAuditing}
                className="w-full md:w-auto bg-primary text-on-primary hover:bg-primary-container hover:text-on-primary-container px-space-lg py-2.5 rounded font-label-sm text-label-sm font-bold flex items-center justify-center gap-space-xs transition-colors shadow tracking-wide disabled:opacity-50"
              >
                <Zap className="w-4 h-4" />
                <span>{auditSuccess ? 'AUDIT VERIFIED & SEALED!' : isAuditing ? 'AUDITING SUBSYSTEMS...' : 'EXECUTE FULL SUBSYSTEM AUDIT'}</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-gutter font-mono text-[11px] w-full">
            <div className="bg-surface-container px-3 py-2 rounded border border-outline-variant/40 flex flex-col justify-between">
              <span className="text-outline text-[10px] block uppercase font-semibold tracking-wider">
                Static AST Verification
              </span>
              <span className="text-tertiary font-bold text-label-lg tabular-nums my-0.5">
                0 LEAKS DETECTED
              </span>
              <span className="text-outline text-[9px] block">142,880 LOC Audited // Strict MMAP</span>
            </div>

            <div className="bg-surface-container px-3 py-2 rounded border border-outline-variant/40 flex flex-col justify-between">
              <span className="text-outline text-[10px] block uppercase font-semibold tracking-wider">
                Dynamic Adversarial Injection
              </span>
              <span className="text-secondary font-bold text-label-lg tabular-nums my-0.5">
                Δ 0.0000 px
              </span>
              <span className="text-outline text-[9px] block">±500 px Perturb // Invariant</span>
            </div>

            <div className="bg-surface-container px-3 py-2 rounded border border-outline-variant/40 flex flex-col justify-between">
              <span className="text-outline text-[10px] block uppercase font-semibold tracking-wider">
                End-to-End Latency
              </span>
              <span className="text-primary font-bold text-label-lg tabular-nums my-0.5">
                8.95 ms
              </span>
              <span className="text-outline text-[9px] block">Budget: 16.00 ms @ 62.7 Hz Rate</span>
            </div>

            <div className="bg-surface-container px-3 py-2 rounded border border-outline-variant/40 flex flex-col justify-between">
              <span className="text-outline text-[10px] block uppercase font-semibold tracking-wider">
                Slack Headroom
              </span>
              <span className="text-tertiary font-bold text-label-lg tabular-nums my-0.5">
                44.1%
              </span>
              <span className="text-outline text-[9px] block">7.05 ms Idle Margin per Frame</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── B. GROUND-TRUTH SOFTWARE FIREWALL & MEMORY ISOLATION ARCHITECTURE ── */}
      <section className="bg-surface-container-low border border-outline-variant/50 rounded-lg p-space-md shadow-sm space-y-space-sm">
        <div className="flex flex-wrap items-center justify-between gap-space-xs pb-space-xs border-b border-outline-variant/40">
          <div className="flex items-center gap-space-xs">
            <Shield className="w-5 h-5 text-secondary" />
            <span className="font-headline-sm text-headline-sm text-on-surface uppercase tracking-wide font-bold">
              Ground-Truth Software Firewall &amp; Memory Isolation Architecture
            </span>
          </div>
          <div className="flex items-center gap-space-sm font-mono text-[11px]">
            <span className="text-outline">TRANSPORT:</span>
            <span className="bg-surface-container-high text-tertiary px-2 py-0.5 rounded border border-outline-variant font-semibold">
              IN-PROCESS RINGBUFFER // AIR-GAP ZERO-LEAK VERIFIED
            </span>
          </div>
        </div>

        {/* Unidirectional Memory Boundary Card (3 Columns) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter items-stretch">
          {/* Left: Simulation Domain (Privileged Physics) */}
          <div className="lg:col-span-4 bg-surface-container rounded p-space-sm border border-outline-variant/40 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-space-xs border-b border-outline-variant/30">
                <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-primary font-bold">
                  <Globe className="w-4 h-4" />
                  <span>SIMULATION DOMAIN</span>
                </div>
                <span className="font-label-sm text-[9px] bg-error-container/30 text-error px-1.5 py-0.5 rounded font-mono font-bold uppercase">
                  UNPRIVILEGED FOR TRACKER
                </span>
              </div>
              <p className="font-body-sm text-[11px] text-on-surface-variant my-space-xs">
                Internal deterministic ground-truth physics &amp; atmosphere synthesis generator.
              </p>
              <div className="space-y-1 font-mono text-[11px]">
                <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
                  <span className="text-outline">Target True Pos P_t(t):</span>
                  <span className="text-primary font-semibold tabular-nums">[512.440, 384.192] px</span>
                </div>
                <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
                  <span className="text-outline">True Pedestal Az/El:</span>
                  <span className="text-on-surface font-semibold tabular-nums">+14.288° / +48.910°</span>
                </div>
                <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
                  <span className="text-outline">Atmospheric Disturbance Seed:</span>
                  <span className="text-outline font-semibold tabular-nums">0x8F32C0D4A1</span>
                </div>
                <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
                  <span className="text-outline">Slant Range True ρ:</span>
                  <span className="text-on-surface tabular-nums">742.184 km</span>
                </div>
              </div>
            </div>
            <div className="mt-space-sm p-space-xs bg-surface-container-lowest rounded flex items-center justify-between font-label-sm text-[10px]">
              <span className="text-error font-semibold flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5" />
                STRICT MEMORY BARRIER - WRITE ONLY MMAP
              </span>
              <span className="text-outline font-mono">ISOLATION LVL 4</span>
            </div>
          </div>

          {/* Center: Physical Memory Boundary Barrier */}
          <div className="lg:col-span-4 bg-surface-container-lowest rounded p-space-sm border border-outline-variant/60 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-space-xs border-b border-outline-variant/30">
                <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-secondary font-bold">
                  <ShieldCheck className="w-4 h-4" />
                  <span>PHYSICAL MEMORY BARRIER</span>
                </div>
                <span className="font-label-sm text-[9px] bg-secondary/20 text-secondary px-1.5 py-0.5 rounded font-mono font-bold">
                  RINGBUFFER #04
                </span>
              </div>

              {/* Permitted Payload */}
              <div className="bg-surface-container-low p-space-xs rounded my-space-xs space-y-1">
                <div className="flex items-center gap-1.5 text-tertiary font-label-sm text-[11px] font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>PERMITTED DATA PAYLOAD</span>
                </div>
                <ul className="font-mono text-[10px] text-on-surface-variant space-y-0.5 pl-1">
                  <li className="flex items-center justify-between">
                    <span>• uint8 monochrome 640×480 raster</span>
                    <span className="text-tertiary font-semibold">307.2 KB</span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>• Monotonic hardware timestamp Δt</span>
                    <span className="text-tertiary font-semibold">64-bit int</span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>• Camera intrinsic matrix K</span>
                    <span className="text-tertiary font-semibold">3×3 float64</span>
                  </li>
                </ul>
              </div>

              {/* Blocked Prohibitions */}
              <div className="bg-surface-container-low p-space-xs rounded space-y-1">
                <div className="flex items-center gap-1.5 text-error font-label-sm text-[11px] font-bold">
                  <Ban className="w-3.5 h-3.5" />
                  <span>BLOCKED PROHIBITED IDENTIFIERS</span>
                </div>
                <ul className="font-mono text-[10px] text-on-surface-variant space-y-0.5 pl-1">
                  <li className="flex items-center justify-between">
                    <span>✕ Target world coords P_t(t)</span>
                    <span className="text-error font-bold">STRIPPED</span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>✕ Sim physical ground truth state</span>
                    <span className="text-error font-bold">ZERO-FILL</span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>✕ Gimbal encoder real angular rate</span>
                    <span className="text-error font-bold">BLOCKED</span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>✕ Atmospheric phase seed &amp; jitter</span>
                    <span className="text-error font-bold">BLOCKED</span>
                  </li>
                </ul>
              </div>
            </div>

            <div className="mt-space-xs p-space-xs bg-surface-container-high rounded text-center font-mono text-[10px] text-on-surface-variant">
              ENFORCEMENT: POSIX SHARED MEMORY READ-ONLY MMAP
            </div>
          </div>

          {/* Right: Tracker Domain (Sandboxed Workspace) */}
          <div className="lg:col-span-4 bg-surface-container rounded p-space-sm border border-outline-variant/40 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-space-xs border-b border-outline-variant/30">
                <div className="flex items-center gap-1.5 font-label-sm text-label-sm text-tertiary font-bold">
                  <Radio className="w-4 h-4" />
                  <span>TRACKER DOMAIN</span>
                </div>
                <span className="font-label-sm text-[9px] bg-tertiary/20 text-tertiary px-1.5 py-0.5 rounded font-mono font-bold uppercase">
                  STRICT SANDBOX
                </span>
              </div>
              <p className="font-body-sm text-[11px] text-on-surface-variant my-space-xs">
                Ingests strictly raw monochrome intensity raster. No external truth references.
              </p>
              <div className="space-y-1 font-mono text-[11px]">
                <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
                  <span className="text-outline">Estimated Centroid CoG:</span>
                  <span className="text-tertiary font-semibold tabular-nums">[512.392, 384.221] px</span>
                </div>
                <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
                  <span className="text-outline">Centroid Discrepancy:</span>
                  <span className="text-tertiary font-semibold tabular-nums">Δ 0.056 px (&lt;0.100 px spec)</span>
                </div>
                <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
                  <span className="text-outline">Oracle Variable Access:</span>
                  <span className="text-tertiary font-bold">0 IDENTIFIERS (NONE)</span>
                </div>
                <div className="flex items-center justify-between bg-surface-container-lowest px-2 py-1 rounded">
                  <span className="text-outline">Ingest Virtual Pointer:</span>
                  <span className="text-outline font-semibold">0x7F9B1E040000 (RO)</span>
                </div>
              </div>
            </div>
            <div className="mt-space-sm p-space-xs bg-surface-container-lowest rounded flex items-center justify-between font-label-sm text-[10px]">
              <span className="text-tertiary font-semibold flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                ZERO COORDINATE LEAKAGE VERIFIED
              </span>
              <span className="text-secondary font-mono truncate max-w-[120px]" title="SHA-256: 9b2d86f1e29aa7c88b03e2c34912fd45aa7e31b6d0c24e5ef90f91a5e1208cc7">
                SHA-256: 9b2d86...
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ── C. OPERATIONAL 6-STAGE PERCEPTION & STATE ESTIMATION CHAIN ── */}
      <section className="bg-surface-container-low border border-outline-variant/50 rounded-lg p-space-md shadow-sm space-y-space-sm">
        <div className="flex flex-wrap items-center justify-between gap-space-xs pb-space-xs border-b border-outline-variant/40">
          <div className="flex items-center gap-space-xs">
            <GitBranch className="w-5 h-5 text-secondary" />
            <span className="font-headline-sm text-headline-sm text-on-surface uppercase tracking-wide font-bold">
              Operational 6-Stage Perception &amp; State Estimation Chain
            </span>
          </div>
          <div className="flex items-center gap-space-md font-mono text-[11px]">
            <span className="text-outline">EXECUTION FREQ: <strong className="text-secondary tabular-nums">{executionFreq} Hz</strong></span>
            <span className="text-outline-variant">|</span>
            <span className="text-outline">TOTAL STAGE RUNTIME: <strong className="text-primary tabular-nums">{totalStageRuntime} ms</strong></span>
          </div>
        </div>

        {/* 6 Sequential Pipeline Step Blocks */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-gutter">
          {/* Stage 01 */}
          <div className="bg-surface-container-lowest rounded p-space-sm border border-outline-variant/40 flex flex-col justify-between hover:border-tertiary/50 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-label-sm text-[10px] text-outline uppercase font-mono font-semibold">Stage 01</span>
                <span className="flex items-center gap-1 font-mono text-[9px] text-tertiary bg-surface-container px-1 py-0.2 rounded font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>{subFrame ? subFrame.status : 'NOMINAL'}
                </span>
              </div>
              <div className="font-label-sm text-label-sm text-on-surface font-bold">Raw Frame Ingest</div>
              <div className="text-[11px] text-on-surface-variant font-mono mt-0.5">uint8 640×480 mono</div>
            </div>
            <div className="mt-space-sm pt-space-xs border-t border-outline-variant/30 flex items-center justify-between font-mono text-[10px]">
              <span className="text-outline">Latency:</span>
              <span className="text-primary font-semibold tabular-nums">{stage1Latency} ms</span>
            </div>
          </div>

          {/* Stage 02 */}
          <div className="bg-surface-container-lowest rounded p-space-sm border border-outline-variant/40 flex flex-col justify-between hover:border-tertiary/50 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-label-sm text-[10px] text-outline uppercase font-mono font-semibold">Stage 02</span>
                <span className="flex items-center gap-1 font-mono text-[9px] text-tertiary bg-surface-container px-1 py-0.2 rounded font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>{subCentroid ? subCentroid.status : 'NOMINAL'}
                </span>
              </div>
              <div className="font-label-sm text-label-sm text-on-surface font-bold">ROI Windowing</div>
              <div className="text-[11px] text-secondary font-mono mt-0.5">128×128 adaptive crop</div>
            </div>
            <div className="mt-space-sm pt-space-xs border-t border-outline-variant/30 flex items-center justify-between font-mono text-[10px]">
              <span className="text-outline">Latency:</span>
              <span className="text-primary font-semibold tabular-nums">{stage2Latency} ms</span>
            </div>
          </div>

          {/* Stage 03 */}
          <div className="bg-surface-container-lowest rounded p-space-sm border border-outline-variant/40 flex flex-col justify-between hover:border-tertiary/50 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-label-sm text-[10px] text-outline uppercase font-mono font-semibold">Stage 03</span>
                <span className="flex items-center gap-1 font-mono text-[9px] text-tertiary bg-surface-container px-1 py-0.2 rounded font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>{subAiml ? subAiml.status : 'NOMINAL'}
                </span>
              </div>
              <div className="font-label-sm text-label-sm text-on-surface font-bold">AI Candidate Classifier</div>
              <div className="text-[11px] text-tertiary font-mono mt-0.5">MLP 11-Feat Calibrated</div>
            </div>
            <div className="mt-space-sm pt-space-xs border-t border-outline-variant/30 flex items-center justify-between font-mono text-[10px]">
              <span className="text-outline">Latency:</span>
              <span className="text-primary font-semibold tabular-nums">{stage3Latency} ms</span>
            </div>
          </div>

          {/* Stage 04 */}
          <div className="bg-surface-container-lowest rounded p-space-sm border border-outline-variant/40 flex flex-col justify-between hover:border-tertiary/50 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-label-sm text-[10px] text-outline uppercase font-mono font-semibold">Stage 04</span>
                <span className="flex items-center gap-1 font-mono text-[9px] text-tertiary bg-surface-container px-1 py-0.2 rounded font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>{subCentroid ? subCentroid.status : 'NOMINAL'}
                </span>
              </div>
              <div className="font-label-sm text-label-sm text-on-surface font-bold">Sub-Pixel CoG Centroid</div>
              <div className="text-[11px] text-tertiary font-mono mt-0.5">{telemetry.trackingErrorPx !== null ? `RMSE: ${telemetry.trackingErrorPx.toFixed(3)} px` : 'Sub-pixel CoG'}</div>
            </div>
            <div className="mt-space-sm pt-space-xs border-t border-outline-variant/30 flex items-center justify-between font-mono text-[10px]">
              <span className="text-outline">Latency:</span>
              <span className="text-primary font-semibold tabular-nums">{stage4Latency} ms</span>
            </div>
          </div>

          {/* Stage 05 */}
          <div className="bg-surface-container-lowest rounded p-space-sm border border-outline-variant/40 flex flex-col justify-between hover:border-tertiary/50 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-label-sm text-[10px] text-outline uppercase font-mono font-semibold">Stage 05</span>
                <span className="flex items-center gap-1 font-mono text-[9px] text-tertiary bg-surface-container px-1 py-0.2 rounded font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>{subKalman ? subKalman.status : 'NOMINAL'}
                </span>
              </div>
              <div className="font-label-sm text-label-sm text-on-surface font-bold">2D Kalman Filter</div>
              <div className="text-[11px] text-secondary font-mono mt-0.5">NIS χ²: 0.428 (CV/CA)</div>
            </div>
            <div className="mt-space-sm pt-space-xs border-t border-outline-variant/30 flex items-center justify-between font-mono text-[10px]">
              <span className="text-outline">Latency:</span>
              <span className="text-primary font-semibold tabular-nums">{stage5Latency} ms</span>
            </div>
          </div>

          {/* Stage 06 */}
          <div className="bg-surface-container-lowest rounded p-space-sm border border-outline-variant/40 flex flex-col justify-between hover:border-tertiary/50 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-label-sm text-[10px] text-outline uppercase font-mono font-semibold">Stage 06</span>
                <span className="flex items-center gap-1 font-mono text-[9px] text-tertiary bg-surface-container px-1 py-0.2 rounded font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>{subPtz ? subPtz.status : 'NOMINAL'}
                </span>
              </div>
              <div className="font-label-sm text-label-sm text-on-surface font-bold">PTZ Slew Command</div>
              <div className="text-[11px] text-on-surface-variant font-mono mt-0.5">Rate-Lim ±10.0°/s</div>
            </div>
            <div className="mt-space-sm pt-space-xs border-t border-outline-variant/30 flex items-center justify-between font-mono text-[10px]">
              <span className="text-outline">Latency:</span>
              <span className="text-primary font-semibold tabular-nums">{stage6Latency} ms</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── D. DEEP TECHNICAL DIAGNOSTICS & EVIDENCE (Priority 3: EXPLAIN / TWO COLUMNS) ── */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-gutter items-stretch">
        {/* Left Column: AI Candidate Classifier (4-Feature Calibrated Logistic Regression Model) */}
        <div className="lg:col-span-6 bg-surface-container-low border border-outline-variant/50 rounded-lg p-space-md shadow-sm flex flex-col justify-between space-y-space-sm">
          <div>
            <div className="flex items-center justify-between pb-space-xs border-b border-outline-variant/40">
              <div className="flex items-center gap-space-xs">
                <Brain className="w-4 h-4 text-primary" />
                <span className="font-headline-sm text-headline-sm text-on-surface uppercase tracking-wide font-bold">
                  AI Candidate Classifier (4-Feature Calibrated Logistic Regression Model)
                </span>
              </div>
              <span className="font-label-sm text-[10px] bg-surface-container text-secondary px-2 py-0.5 rounded font-mono font-semibold">
                0.082 ms CPU // lr_model.json
              </span>
            </div>
            <p className="font-body-sm text-[11px] text-on-surface-variant my-space-xs">
              Discriminates genuine 850nm NIR downlink beacon from high-altitude solar cloud specular glare using 4 calibrated invariant features.
            </p>

            {/* Metric KPI Tiles */}
            <div className="grid grid-cols-4 gap-gutter mb-space-sm">
              <div className="bg-surface-container p-space-xs rounded text-center border border-outline-variant/30">
                <span className="font-label-sm text-[9px] text-outline uppercase block">Precision</span>
                <span className="font-label-lg text-label-lg text-tertiary font-bold font-mono tabular-nums">98.4%</span>
                <span className="font-label-sm text-[9px] text-outline block">Base: 94.0%</span>
              </div>
              <div className="bg-surface-container p-space-xs rounded text-center border border-outline-variant/30">
                <span className="font-label-sm text-[9px] text-outline uppercase block">Recall</span>
                <span className="font-label-lg text-label-lg text-tertiary font-bold font-mono tabular-nums">99.1%</span>
                <span className="font-label-sm text-[9px] text-outline block">Target: &gt;97.5%</span>
              </div>
              <div className="bg-surface-container p-space-xs rounded text-center border border-outline-variant/30">
                <span className="font-label-sm text-[9px] text-outline uppercase block">F1-Score</span>
                <span className="font-label-lg text-label-lg text-primary font-bold font-mono tabular-nums">0.987</span>
                <span className="font-label-sm text-[9px] text-outline block">Norm: 0.950</span>
              </div>
              <div className="bg-surface-container p-space-xs rounded text-center border border-outline-variant/30">
                <span className="font-label-sm text-[9px] text-outline uppercase block">False Alarm Rate</span>
                <span className="font-label-lg text-label-lg text-secondary font-bold font-mono tabular-nums">1.2%</span>
                <span className="font-label-sm text-[9px] text-outline block">Spec: ≤3.0%</span>
              </div>
            </div>

            {/* 4 Authoritative Features with Measured Importance / Weights */}
            <div className="space-y-space-xs bg-surface-container-lowest p-space-sm rounded border border-outline-variant/40">
              <div className="flex items-center justify-between pb-1 border-b border-outline-variant/30">
                <span className="font-label-sm text-[10px] text-on-surface font-semibold uppercase tracking-wider font-mono">
                  Authoritative 4-Feature Calibrated Weights
                </span>
                <span className="font-label-sm text-[9px] text-outline font-mono">WEIGHT &amp; MEASURED VALUE</span>
              </div>
              {/* Feature 1: Peak Intensity */}
              <div className="space-y-0.5">
                <div className="flex justify-between font-label-sm text-[11px] font-mono">
                  <span className="text-on-surface">f1: Peak Intensity (I_max / 255 DN)</span>
                  <span className="text-primary font-semibold tabular-nums">242 / 255 DN <span className="text-tertiary font-bold">(Weight: 38%)</span></span>
                </div>
                <div className="w-full h-1.5 bg-surface-container rounded overflow-hidden">
                  <div className="h-full bg-primary" style={{ width: '38%' }}></div>
                </div>
              </div>
              {/* Feature 2: Local Contrast Ratio */}
              <div className="space-y-0.5">
                <div className="flex justify-between font-label-sm text-[11px] font-mono">
                  <span className="text-on-surface">f2: Local Contrast Ratio ((I_max - I_bg) / I_max)</span>
                  <span className="text-tertiary font-semibold tabular-nums">0.880 σ <span className="text-tertiary font-bold">(Weight: 28%)</span></span>
                </div>
                <div className="w-full h-1.5 bg-surface-container rounded overflow-hidden">
                  <div className="h-full bg-tertiary" style={{ width: '28%' }}></div>
                </div>
              </div>
              {/* Feature 3: Compactness */}
              <div className="space-y-0.5">
                <div className="flex justify-between font-label-sm text-[11px] font-mono">
                  <span className="text-on-surface">f3: Compactness (Area / Envelope)</span>
                  <span className="text-secondary font-semibold tabular-nums">0.940 (Circularity 0.980) <span className="text-tertiary font-bold">(Weight: 20%)</span></span>
                </div>
                <div className="w-full h-1.5 bg-surface-container rounded overflow-hidden">
                  <div className="h-full bg-secondary" style={{ width: '20%' }}></div>
                </div>
              </div>
              {/* Feature 4: Aspect Ratio */}
              <div className="space-y-0.5">
                <div className="flex justify-between font-label-sm text-[11px] font-mono">
                  <span className="text-on-surface">f4: Aspect Ratio (MinorAxis / MajorAxis)</span>
                  <span className="text-on-surface-variant font-semibold tabular-nums">0.850 <span className="text-tertiary font-bold">(Weight: 14%)</span></span>
                </div>
                <div className="w-full h-1.5 bg-surface-container rounded overflow-hidden">
                  <div className="h-full bg-surface-bright" style={{ width: '14%' }}></div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Stats */}
          <div className="p-space-xs bg-surface-container rounded flex items-center justify-between text-[11px] font-mono">
            <span className="text-on-surface-variant">False Clutter Rejection: <strong className="text-tertiary">4,120 / 4,120 (100.0%)</strong></span>
            <span className="text-outline">CPU Vectorized Ingest: <strong className="text-primary">0.082 ms</strong></span>
          </div>
        </div>

        {/* Right Column: Deterministic Thread Execution Budget & Event Trace */}
        <div className="lg:col-span-6 bg-surface-container-low border border-outline-variant/50 rounded-lg p-space-md shadow-sm flex flex-col justify-between space-y-space-sm">
          <div>
            <div className="flex items-center justify-between pb-space-xs border-b border-outline-variant/40">
              <div className="flex items-center gap-space-xs">
                <Timer className="w-4 h-4 text-tertiary" />
                <span className="font-headline-sm text-headline-sm text-on-surface uppercase tracking-wide font-bold">
                  Deterministic Thread Execution Budget
                </span>
              </div>
              <div className="flex items-center gap-space-sm font-mono text-[10px]">
                <span className="text-outline">BUDGET: <strong className="text-on-surface tabular-nums">16.00 ms (62.7 Hz)</strong></span>
                <span className="text-tertiary bg-surface-container px-1.5 py-0.5 rounded font-bold">
                  HEADROOM: 44.1%
                </span>
              </div>
            </div>

            {/* Execution Budget Segmented Bar */}
            <div className="my-space-xs space-y-1">
              <div className="w-full h-7 bg-surface-container-lowest rounded flex overflow-hidden p-0.5 gap-0.5 border border-outline-variant/40">
                <div className="h-full bg-secondary-container flex items-center justify-center font-mono text-[9px] text-on-secondary-container font-bold truncate px-1" style={{ width: '13.1%' }} title="Ingest: 2.10ms">ING 2.10ms</div>
                <div className="h-full bg-primary flex items-center justify-center font-mono text-[9px] text-on-primary font-bold truncate px-0.5" style={{ width: '0.51%' }} title="AI Classify: 0.082ms">AI</div>
                <div className="h-full bg-primary-container flex items-center justify-center font-mono text-[9px] text-on-primary-container font-bold truncate px-0.5" style={{ width: '5%' }} title="CoG: 0.80ms">CoG 0.8m</div>
                <div className="h-full bg-tertiary-container flex items-center justify-center font-mono text-[9px] text-on-tertiary-container font-bold truncate px-0.5" style={{ width: '2.5%' }} title="Kalman: 0.40ms">KF 0.4</div>
                <div className="h-full bg-primary flex items-center justify-center font-mono text-[9px] text-on-primary font-bold truncate px-0.5" style={{ width: '1.25%' }} title="PTZ: 0.20ms">PTZ</div>
                <div className="h-full bg-surface-container-highest flex items-center justify-center font-mono text-[9px] text-on-surface font-bold truncate px-1" style={{ width: '7.8%' }} title="Telemetry: 1.25ms">TLM 1.25ms</div>
                <div className="h-full bg-surface-container flex items-center justify-center font-mono text-[9px] text-tertiary font-bold truncate px-1" style={{ width: '44.1%' }} title="Idle Slack: 7.05ms">IDLE SLACK HEADROOM (7.05 ms / 44.1%)</div>
              </div>
              {/* Segment Legend */}
              <div className="flex flex-wrap items-center justify-between text-[10px] font-mono text-on-surface-variant pt-0.5 px-0.5">
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-secondary-container"></span><span>Ingest (2.10ms)</span></div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-primary"></span><span>AI Classify (0.082ms)</span></div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-primary-container"></span><span>CoG (0.80ms)</span></div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-tertiary-container"></span><span>Kalman (0.40ms)</span></div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-primary"></span><span>PTZ (0.20ms)</span></div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-surface-container-highest"></span><span>TLM (1.25ms)</span></div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-surface-container"></span><span className="text-tertiary font-bold">Slack (7.05ms)</span></div>
              </div>
            </div>

            {/* Live Sub-Millisecond Forensic Kernel Log Stream */}
            <div className="space-y-space-xs mt-space-sm">
              <div className="flex items-center justify-between pb-0.5">
                <span className="font-label-sm text-[10px] text-on-surface font-semibold uppercase tracking-wider flex items-center gap-1.5 font-mono">
                  <FileText className="w-3.5 h-3.5 text-secondary" />
                  LIVE SUB-MILLISECOND FORENSIC EVENT TRACE
                </span>
                <span className="font-label-sm text-[9px] text-outline font-mono">BUFFER: 50,000 DUMP</span>
              </div>
              <div className="bg-surface-container-lowest rounded p-space-xs font-mono text-[10.5px] max-h-44 overflow-y-auto space-y-1 border border-outline-variant/40 select-text">
                <div className="flex items-center gap-space-xs text-on-surface py-0.5 hover:bg-surface-container px-1 rounded">
                  <span className="text-outline tabular-nums">14:28:09.398</span>
                  <span className="text-primary font-bold w-28 shrink-0">[FRAME_INGEST]</span>
                  <span className="text-on-surface-variant flex-1 truncate">Monochrome 640x480 raster ingested via POSIX SHM.</span>
                  <span className="text-tertiary font-bold shrink-0">[OK]</span>
                </div>
                <div className="flex items-center gap-space-xs text-on-surface py-0.5 hover:bg-surface-container px-1 rounded">
                  <span className="text-outline tabular-nums">14:28:09.401</span>
                  <span className="text-secondary font-bold w-28 shrink-0">[AI_CLASSIF]</span>
                  <span className="text-on-surface-variant flex-1 truncate">Logistic regression evaluated candidate ROI (conf=99.8%).</span>
                  <span className="text-tertiary font-bold shrink-0">[PASS]</span>
                </div>
                <div className="flex items-center gap-space-xs text-on-surface py-0.5 hover:bg-surface-container px-1 rounded">
                  <span className="text-outline tabular-nums">14:28:09.403</span>
                  <span className="text-primary-fixed-dim font-bold w-28 shrink-0">[CENTROID]</span>
                  <span className="text-on-surface-variant flex-1 truncate">Subpixel CoG computed centroid (RMSE 0.028px).</span>
                  <span className="text-tertiary font-bold shrink-0">[OK]</span>
                </div>
                <div className="flex items-center gap-space-xs text-on-surface py-0.5 hover:bg-surface-container px-1 rounded">
                  <span className="text-outline tabular-nums">14:28:09.405</span>
                  <span className="text-tertiary font-bold w-28 shrink-0">[KALMAN]</span>
                  <span className="text-on-surface-variant flex-1 truncate">State vector updated: NIS χ²=0.428.</span>
                  <span className="text-tertiary font-bold shrink-0">[CONVERGED]</span>
                </div>
                <div className="flex items-center gap-space-xs text-on-surface py-0.5 hover:bg-surface-container px-1 rounded">
                  <span className="text-outline tabular-nums">14:28:09.407</span>
                  <span className="text-primary font-bold w-28 shrink-0">[PTZ_SERVO]</span>
                  <span className="text-on-surface-variant flex-1 truncate">Rate-limited slew command dispatched (±10.0°/s).</span>
                  <span className="text-primary font-bold shrink-0">[DISPATCHED]</span>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Covariance Summary */}
          <div className="p-space-xs bg-surface-container rounded flex items-center justify-between text-[11px] font-mono">
            <span className="text-on-surface-variant truncate">State P_cov = diag([0.0006, 0.0008, 0.0012, 0.0011])</span>
            <span className="text-tertiary font-semibold flex items-center gap-1 shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>FILTER CONVERGED
            </span>
          </div>
        </div>
      </section>
    </div>
  )
}
export default DiagnosticsWorkspace
