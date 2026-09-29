/**
 * LumiTrack — Browser-Side Performance Instrumentation Contracts
 */

export interface BrowserPerformanceMetrics {
  renderFps: number
  minFps: number
  frameTimeMs: number
  droppedFrames: number
  browserDecodeTimeMs: number
  canvasDrawTimeMs: number
  totalBrowserPipelineMs: number
  telemetryReceiveHz: number
  telemetryDroppedCount: number
  lastTelemetryIntervalMs: number
}
