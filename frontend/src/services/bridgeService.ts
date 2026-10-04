/**
 * SANKET — QtWebChannel Bridge Client Service (Phase 2 Expanded)
 * Bridges React to the native Python PySide6 QWebEngine host.
 */

import { QWebChannel } from './qwebchannel'
import type { SystemStatus, TrackingTelemetry, SensorFramePayload } from '../types/telemetry'
import type { SubsystemState } from '../types/diagnostics'
import type { RunCatalogItem, RunArtifactPayload } from '../types/history'
import type { BenchmarkProgress, BenchmarkResult, BenchmarkVideoMeta } from '../types/benchmark'
import type { ResultsTimeSeriesData } from '../types/scene3d'

type SystemStatusCallback = (status: SystemStatus) => void
type TelemetryCallback = (telemetry: TrackingTelemetry) => void
type SensorFrameCallback = (frame: SensorFramePayload) => void
type ConnectionCallback = (connected: boolean) => void
type DiagnosticsCallback = (diagnostics: SubsystemState[]) => void
type HistoryCallback = (history: RunCatalogItem[]) => void
type ArtifactCallback = (artifact: RunArtifactPayload) => void
type BenchmarkProgressCallback = (progress: BenchmarkProgress) => void
type BenchmarkResultCallback = (result: BenchmarkResult) => void
type ResultsDataCallback = (data: ResultsTimeSeriesData) => void
type BenchmarkVideoCallback = (meta: BenchmarkVideoMeta) => void
type FileSavedCallback = (path: string) => void

interface PyBridgeObject {
  // Signals
  systemStatusChanged: { connect: (cb: (jsonStr: string) => void) => void }
  telemetryUpdated: { connect: (cb: (jsonStr: string) => void) => void }
  sensorFrameReady: { connect: (cb: (jsonStr: string) => void) => void }
  subsystemDiagnosticsUpdated: { connect: (cb: (jsonStr: string) => void) => void }
  runHistoryUpdated: { connect: (cb: (jsonStr: string) => void) => void }
  runArtifactLoaded: { connect: (cb: (jsonStr: string) => void) => void }
  benchmarkProgress: { connect: (cb: (jsonStr: string) => void) => void }
  benchmarkCompleted: { connect: (cb: (jsonStr: string) => void) => void }
  resultsAnalysisLoaded: { connect: (cb: (jsonStr: string) => void) => void }
  benchmarkVideoLoaded?: { connect: (cb: (jsonStr: string) => void) => void }
  fileSaved?: { connect: (cb: (path: string) => void) => void }

  // Slots
  clientReady: () => void
  runSimulation: () => void
  pauseSimulation: () => void
  resumeSimulation: () => void
  stopSimulation: () => void
  stepSimulation: () => void
  resetSimulation: () => void
  selectAlgorithm: (name: string) => void
  selectScenario: (name: string) => void
  setPtzEnabled: (enabled: boolean) => void
  toggleValidationMode: (enabled: boolean) => void
  getSubsystemDiagnostics: () => void
  getRunHistory: () => void
  getRunArtifact: (path: string) => void
  runBenchmarkMatrix: (subset: string) => void
  stopBenchmarkMatrix?: () => void
  saveTextFile?: (filename: string, content: string) => void
  getResultsAnalysisData: (runId: string) => void
  setTrackingEnabled: (enabled: boolean) => void
  setMotionPattern: (pattern: string) => void
  setTargetSpeed: (speed: number) => void
  setTargetSize: (size: number) => void
  setAtmosphericCondition: (condition: string) => void
  setNoiseEnabled: (noiseType: string, enabled: boolean) => void
  saveScenario: (name: string, jsonStr: string) => void
  generateAiScenario: (prompt: string) => void
  setPtzGains: (kp: number, ki: number, deadband: number) => void
  loadBenchmarkVideo?: (filePath?: string) => void
  loadBenchmarkVideoByName?: (name: string) => void
  uploadBenchmarkVideoData?: (fileName: string, base64Data: string) => void
  playBenchmarkVideo?: () => void
  pauseBenchmarkVideo?: () => void
  resetBenchmarkVideo?: () => void
  reportBrowserMetrics: (
    renderFps: number,
    minFps: number,
    frameTimeMs: number,
    decodeTimeMs: number,
    telemetryHz: number
  ) => void
  firstFramePresented: (decodeMs: number, drawMs: number) => void
}

class BridgeService {
  private pyBridge: PyBridgeObject | null = null
  private isConnected = false
  private connectionListeners: ConnectionCallback[] = []
  private statusListeners: SystemStatusCallback[] = []
  private telemetryListeners: TelemetryCallback[] = []
  private frameListeners: SensorFrameCallback[] = []
  private diagnosticsListeners: DiagnosticsCallback[] = []
  private historyListeners: HistoryCallback[] = []
  private artifactListeners: ArtifactCallback[] = []
  private progressListeners: BenchmarkProgressCallback[] = []
  private benchmarkResultListeners: BenchmarkResultCallback[] = []
  private resultsDataListeners: ResultsDataCallback[] = []
  private videoMetaListeners: BenchmarkVideoCallback[] = []
  private fileSavedListeners: FileSavedCallback[] = []

  public init(): Promise<boolean> {
    return new Promise((resolve) => {
      const checkAndConnect = () => {
        const qt = (window as unknown as { qt?: { webChannelTransport?: unknown } }).qt
        if (qt && qt.webChannelTransport) {
          try {
            new QWebChannel(qt.webChannelTransport, (channel: { objects: { pyBridge?: PyBridgeObject } }) => {
              if (channel.objects.pyBridge) {
                this.pyBridge = channel.objects.pyBridge
                this.setupSignalListeners()
                this.isConnected = true
                this.notifyConnection(true)
                try {
                  this.pyBridge.clientReady()
                } catch (e) {
                  console.warn('Error calling clientReady:', e)
                }
                resolve(true)
              } else {
                console.error('[BridgeService] pyBridge object not found on QWebChannel.')
                resolve(false)
              }
            })
          } catch (err) {
            console.error('[BridgeService] Failed to initialize QWebChannel:', err)
            resolve(false)
          }
        } else {
          // Retry for up to 3 seconds in case transport is injected asynchronously
          let retries = 0
          const interval = setInterval(() => {
            retries++
            const dynamicQt = (window as unknown as { qt?: { webChannelTransport?: unknown } }).qt
            if (dynamicQt && dynamicQt.webChannelTransport) {
              clearInterval(interval)
              new QWebChannel(dynamicQt.webChannelTransport, (channel: { objects: { pyBridge?: PyBridgeObject } }) => {
                if (channel.objects.pyBridge) {
                  this.pyBridge = channel.objects.pyBridge
                  this.setupSignalListeners()
                  this.isConnected = true
                  this.notifyConnection(true)
                  try {
                    this.pyBridge.clientReady()
                  } catch (e) {
                    console.warn('Error calling clientReady:', e)
                  }
                  resolve(true)
                } else {
                  resolve(false)
                }
              })
            } else if (retries > 30) {
              clearInterval(interval)
              console.warn('[BridgeService] Qt WebChannel transport not found. Running in standalone browser preview.')
              resolve(false)
            }
          }, 100)
        }
      }

      checkAndConnect()
    })
  }

  private setupSignalListeners(): void {
    if (!this.pyBridge) return

    // System status signal
    if (this.pyBridge.systemStatusChanged) {
      this.pyBridge.systemStatusChanged.connect((jsonStr: string) => {
        try {
          const status = JSON.parse(jsonStr) as SystemStatus
          this.statusListeners.forEach((cb) => cb(status))
        } catch (e) {
          console.error('[BridgeService] Failed to parse SystemStatus JSON:', e)
        }
      })
    }

    // Telemetry signal
    if (this.pyBridge.telemetryUpdated) {
      this.pyBridge.telemetryUpdated.connect((jsonStr: string) => {
        try {
          const telemetry = JSON.parse(jsonStr) as TrackingTelemetry
          this.telemetryListeners.forEach((cb) => cb(telemetry))
        } catch (e) {
          console.error('[BridgeService] Failed to parse TrackingTelemetry JSON:', e)
        }
      })
    }

    // Sensor frame signal
    if (this.pyBridge.sensorFrameReady) {
      this.pyBridge.sensorFrameReady.connect((jsonStr: string) => {
        try {
          const frame = JSON.parse(jsonStr) as SensorFramePayload
          this.frameListeners.forEach((cb) => cb(frame))
        } catch (e) {
          console.error('[BridgeService] Failed to parse SensorFramePayload JSON:', e)
        }
      })
    }

    // Diagnostics signal
    if (this.pyBridge.subsystemDiagnosticsUpdated) {
      this.pyBridge.subsystemDiagnosticsUpdated.connect((jsonStr: string) => {
        try {
          const diag = JSON.parse(jsonStr) as SubsystemState[]
          this.diagnosticsListeners.forEach((cb) => cb(diag))
        } catch (e) {
          console.error('[BridgeService] Failed to parse SubsystemState JSON:', e)
        }
      })
    }

    // Run History signal
    if (this.pyBridge.runHistoryUpdated) {
      this.pyBridge.runHistoryUpdated.connect((jsonStr: string) => {
        try {
          const items = JSON.parse(jsonStr) as RunCatalogItem[]
          this.historyListeners.forEach((cb) => cb(items))
        } catch (e) {
          console.error('[BridgeService] Failed to parse RunCatalogItem JSON:', e)
        }
      })
    }

    // Run Artifact loaded signal
    if (this.pyBridge.runArtifactLoaded) {
      this.pyBridge.runArtifactLoaded.connect((jsonStr: string) => {
        try {
          const artifact = JSON.parse(jsonStr) as RunArtifactPayload
          this.artifactListeners.forEach((cb) => cb(artifact))
        } catch (e) {
          console.error('[BridgeService] Failed to parse RunArtifactPayload JSON:', e)
        }
      })
    }

    // Benchmark Progress signal
    if (this.pyBridge.benchmarkProgress) {
      this.pyBridge.benchmarkProgress.connect((jsonStr: string) => {
        try {
          const progress = JSON.parse(jsonStr) as BenchmarkProgress
          this.progressListeners.forEach((cb) => cb(progress))
        } catch (e) {
          console.error('[BridgeService] Failed to parse BenchmarkProgress JSON:', e)
        }
      })
    }

    // Benchmark Completed signal
    if (this.pyBridge.benchmarkCompleted) {
      this.pyBridge.benchmarkCompleted.connect((jsonStr: string) => {
        try {
          const result = JSON.parse(jsonStr) as BenchmarkResult
          this.benchmarkResultListeners.forEach((cb) => cb(result))
        } catch (e) {
          console.error('[BridgeService] Failed to parse BenchmarkResult JSON:', e)
        }
      })
    }

    // Results Analysis Data signal
    if (this.pyBridge.resultsAnalysisLoaded) {
      this.pyBridge.resultsAnalysisLoaded.connect((jsonStr: string) => {
        try {
          const data = JSON.parse(jsonStr) as ResultsTimeSeriesData
          this.resultsDataListeners.forEach((cb) => cb(data))
        } catch (e) {
          console.error('[BridgeService] Failed to parse ResultsTimeSeriesData JSON:', e)
        }
      })
    }

    // Benchmark 2 Video Loaded signal
    if (this.pyBridge.benchmarkVideoLoaded) {
      this.pyBridge.benchmarkVideoLoaded.connect((jsonStr: string) => {
        try {
          const meta = JSON.parse(jsonStr) as BenchmarkVideoMeta
          this.videoMetaListeners.forEach((cb) => cb(meta))
        } catch (e) {
          console.error('[BridgeService] Failed to parse BenchmarkVideoMeta JSON:', e)
        }
      })
    }

    // File Saved notification signal
    if (this.pyBridge.fileSaved) {
      this.pyBridge.fileSaved.connect((path: string) => {
        this.fileSavedListeners.forEach((cb) => cb(path))
      })
    }
  }

  // Subscriptions
  public onFileSaved(cb: FileSavedCallback): () => void {
    this.fileSavedListeners.push(cb)
    return () => {
      this.fileSavedListeners = this.fileSavedListeners.filter((l) => l !== cb)
    }
  }

  public onBenchmarkVideoLoaded(cb: BenchmarkVideoCallback): () => void {
    this.videoMetaListeners.push(cb)
    return () => {
      this.videoMetaListeners = this.videoMetaListeners.filter((l) => l !== cb)
    }
  }

  public onConnectionChange(cb: ConnectionCallback): () => void {
    this.connectionListeners.push(cb)
    cb(this.isConnected)
    return () => {
      this.connectionListeners = this.connectionListeners.filter((l) => l !== cb)
    }
  }

  public onSystemStatus(cb: SystemStatusCallback): () => void {
    this.statusListeners.push(cb)
    return () => {
      this.statusListeners = this.statusListeners.filter((l) => l !== cb)
    }
  }

  public onTelemetry(cb: TelemetryCallback): () => void {
    this.telemetryListeners.push(cb)
    return () => {
      this.telemetryListeners = this.telemetryListeners.filter((l) => l !== cb)
    }
  }

  public onSensorFrame(cb: SensorFrameCallback): () => void {
    this.frameListeners.push(cb)
    return () => {
      this.frameListeners = this.frameListeners.filter((l) => l !== cb)
    }
  }

  public onDiagnostics(cb: DiagnosticsCallback): () => void {
    this.diagnosticsListeners.push(cb)
    return () => {
      this.diagnosticsListeners = this.diagnosticsListeners.filter((l) => l !== cb)
    }
  }

  public onRunHistory(cb: HistoryCallback): () => void {
    this.historyListeners.push(cb)
    return () => {
      this.historyListeners = this.historyListeners.filter((l) => l !== cb)
    }
  }

  public onArtifactLoaded(cb: ArtifactCallback): () => void {
    this.artifactListeners.push(cb)
    return () => {
      this.artifactListeners = this.artifactListeners.filter((l) => l !== cb)
    }
  }

  public onBenchmarkProgress(cb: BenchmarkProgressCallback): () => void {
    this.progressListeners.push(cb)
    return () => {
      this.progressListeners = this.progressListeners.filter((l) => l !== cb)
    }
  }

  public onBenchmarkCompleted(cb: BenchmarkResultCallback): () => void {
    this.benchmarkResultListeners.push(cb)
    return () => {
      this.benchmarkResultListeners = this.benchmarkResultListeners.filter((l) => l !== cb)
    }
  }

  public onResultsAnalysisLoaded(cb: ResultsDataCallback): () => void {
    this.resultsDataListeners.push(cb)
    return () => {
      this.resultsDataListeners = this.resultsDataListeners.filter((l) => l !== cb)
    }
  }

  private notifyConnection(status: boolean): void {
    this.connectionListeners.forEach((cb) => cb(status))
  }

  // --- Remote Command Slots ---

  public run(): void {
    this.pyBridge?.runSimulation?.()
  }

  public pause(): void {
    this.pyBridge?.pauseSimulation?.()
  }

  public resume(): void {
    this.pyBridge?.resumeSimulation?.()
  }

  public stop(): void {
    this.pyBridge?.stopSimulation?.()
  }

  public step(): void {
    this.pyBridge?.stepSimulation?.()
  }

  public reset(): void {
    this.pyBridge?.resetSimulation?.()
  }

  public selectAlgorithm(name: string): void {
    this.pyBridge?.selectAlgorithm?.(name)
  }

  public selectScenario(name: string): void {
    this.pyBridge?.selectScenario?.(name)
  }

  public setPtzEnabled(enabled: boolean): void {
    this.pyBridge?.setPtzEnabled?.(enabled)
  }

  public setTrackingEnabled(enabled: boolean): void {
    this.pyBridge?.setTrackingEnabled?.(enabled)
  }

  public setMotionPattern(pattern: string): void {
    this.pyBridge?.setMotionPattern?.(pattern)
  }

  public setTargetSpeed(speed: number): void {
    this.pyBridge?.setTargetSpeed?.(speed)
  }

  public setTargetSize(size: number): void {
    this.pyBridge?.setTargetSize?.(size)
  }

  public setAtmosphericCondition(condition: string): void {
    this.pyBridge?.setAtmosphericCondition?.(condition)
  }

  public setNoiseEnabled(noiseType: string, enabled: boolean): void {
    this.pyBridge?.setNoiseEnabled?.(noiseType, enabled)
  }

  public setPtzGains(kp: number, ki: number, deadband: number): void {
    this.pyBridge?.setPtzGains?.(kp, ki, deadband)
  }

  public toggleValidationMode(enabled: boolean): void {
    this.pyBridge?.toggleValidationMode?.(enabled)
  }

  public saveScenario(name: string, jsonStr: string): void {
    this.pyBridge?.saveScenario?.(name, jsonStr)
  }

  public generateAiScenario(prompt: string): void {
    this.pyBridge?.generateAiScenario?.(prompt)
  }

  public getSubsystemDiagnostics(): void {
    this.pyBridge?.getSubsystemDiagnostics?.()
  }

  public getRunHistory(): void {
    this.pyBridge?.getRunHistory?.()
  }

  public getRunArtifact(path: string): void {
    this.pyBridge?.getRunArtifact?.(path)
  }

  public runBenchmarkMatrix(subset: string): void {
    this.pyBridge?.runBenchmarkMatrix?.(subset)
  }

  public stopBenchmarkMatrix(): void {
    this.pyBridge?.stopBenchmarkMatrix?.()
  }

  public saveTextFile(filename: string, content: string): void {
    this.pyBridge?.saveTextFile?.(filename, content)
  }

  public getResultsAnalysisData(runId: string = ''): void {
    this.pyBridge?.getResultsAnalysisData?.(runId)
  }

  public reportBrowserMetrics(
    renderFps: number,
    minFps: number,
    frameTimeMs: number,
    decodeTimeMs: number,
    telemetryHz: number
  ): void {
    this.pyBridge?.reportBrowserMetrics?.(renderFps, minFps, frameTimeMs, decodeTimeMs, telemetryHz)
  }

  public firstFramePresented(decodeMs: number, drawMs: number): void {
    this.pyBridge?.firstFramePresented?.(decodeMs, drawMs)
  }

  public loadBenchmarkVideo(filePath?: string): void {
    this.pyBridge?.loadBenchmarkVideo?.(filePath || 'BROWSE')
  }

  public loadBenchmarkVideoByName(name: string): void {
    this.pyBridge?.loadBenchmarkVideoByName?.(name)
  }

  public uploadBenchmarkVideoData(fileName: string, base64Data: string): void {
    this.pyBridge?.uploadBenchmarkVideoData?.(fileName, base64Data)
  }

  public playBenchmarkVideo(): void {
    this.pyBridge?.playBenchmarkVideo?.()
  }

  public pauseBenchmarkVideo(): void {
    this.pyBridge?.pauseBenchmarkVideo?.()
  }

  public resetBenchmarkVideo(): void {
    this.pyBridge?.resetBenchmarkVideo?.()
  }

  public getConnected(): boolean {
    return this.isConnected
  }
}

export const bridgeService = new BridgeService()
