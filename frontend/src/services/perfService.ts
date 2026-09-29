/**
 * LumiTrack — Browser-Side Performance Instrumentation Service
 * Measures actual requestAnimationFrame UI rendering rate, canvas draw latency,
 * and telemetry arrival intervals directly inside the Chromium V8 environment.
 */

import type { BrowserPerformanceMetrics } from '../types/performance'
import { bridgeService } from './bridgeService'

class BrowserPerformanceService {
  private frameTimestamps: number[] = []
  private decodeLatencies: number[] = []
  private drawLatencies: number[] = []
  private telemetryTimestamps: number[] = []
  private lastReportTime = 0
  private droppedFrameCount = 0

  private currentMetrics: BrowserPerformanceMetrics = {
    renderFps: 60.0,
    minFps: 60.0,
    frameTimeMs: 16.6,
    droppedFrames: 0,
    browserDecodeTimeMs: 0.0,
    canvasDrawTimeMs: 0.0,
    totalBrowserPipelineMs: 0.0,
    telemetryReceiveHz: 25.0,
    telemetryDroppedCount: 0,
    lastTelemetryIntervalMs: 40.0,
  }

  constructor() {
    this.startRenderFpsLoop()
  }

  private startRenderFpsLoop(): void {
    let lastRafTime = performance.now()

    const onFrame = (now: number) => {
      const delta = now - lastRafTime
      lastRafTime = now

      if (delta > 33.3) {
        this.droppedFrameCount++
      }

      this.frameTimestamps.push(now)
      if (this.frameTimestamps.length > 60) {
        this.frameTimestamps.shift()
      }

      // Compute FPS over the rolling window
      if (this.frameTimestamps.length >= 10) {
        const span = this.frameTimestamps[this.frameTimestamps.length - 1] - this.frameTimestamps[0]
        const meanFps = (this.frameTimestamps.length - 1) / (span / 1000.0)

        // Find minimum instantaneous FPS
        let maxDelta = 0
        for (let i = 1; i < this.frameTimestamps.length; i++) {
          const d = this.frameTimestamps[i] - this.frameTimestamps[i - 1]
          if (d > maxDelta) maxDelta = d
        }
        const minFps = maxDelta > 0 ? 1000.0 / maxDelta : 60.0

        this.currentMetrics.renderFps = Math.min(120.0, Math.round(meanFps * 10) / 10)
        this.currentMetrics.minFps = Math.min(120.0, Math.round(minFps * 10) / 10)
        this.currentMetrics.frameTimeMs = Math.round(delta * 100) / 100
        this.currentMetrics.droppedFrames = this.droppedFrameCount
      }

      // Periodically report to backend bridge
      if (now - this.lastReportTime >= 1000) {
        this.lastReportTime = now
        bridgeService.reportBrowserMetrics(
          this.currentMetrics.renderFps,
          this.currentMetrics.minFps,
          this.currentMetrics.frameTimeMs,
          this.currentMetrics.browserDecodeTimeMs,
          this.currentMetrics.telemetryReceiveHz
        )
      }

      requestAnimationFrame(onFrame)
    }

    requestAnimationFrame(onFrame)
  }

  public recordFramePipeline(decodeMs: number, drawMs: number): void {
    this.decodeLatencies.push(decodeMs)
    this.drawLatencies.push(drawMs)
    if (this.decodeLatencies.length > 30) this.decodeLatencies.shift()
    if (this.drawLatencies.length > 30) this.drawLatencies.shift()

    const meanDecode = this.decodeLatencies.reduce((a, b) => a + b, 0) / this.decodeLatencies.length
    const meanDraw = this.drawLatencies.reduce((a, b) => a + b, 0) / this.drawLatencies.length

    this.currentMetrics.browserDecodeTimeMs = Math.round(meanDecode * 100) / 100
    this.currentMetrics.canvasDrawTimeMs = Math.round(meanDraw * 100) / 100
    this.currentMetrics.totalBrowserPipelineMs = Math.round((meanDecode + meanDraw) * 100) / 100
  }

  public recordTelemetryTick(): void {
    const now = performance.now()
    this.telemetryTimestamps.push(now)
    if (this.telemetryTimestamps.length > 25) {
      this.telemetryTimestamps.shift()
    }

    if (this.telemetryTimestamps.length >= 5) {
      const span = this.telemetryTimestamps[this.telemetryTimestamps.length - 1] - this.telemetryTimestamps[0]
      const hz = (this.telemetryTimestamps.length - 1) / (span / 1000.0)
      this.currentMetrics.telemetryReceiveHz = Math.round(hz * 10) / 10
      this.currentMetrics.lastTelemetryIntervalMs = Math.round(span / (this.telemetryTimestamps.length - 1))
    }
  }

  public getMetrics(): BrowserPerformanceMetrics {
    return { ...this.currentMetrics }
  }
}

export const perfService = new BrowserPerformanceService()
