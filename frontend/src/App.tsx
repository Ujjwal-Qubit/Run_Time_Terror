import React, { useEffect } from 'react'
import { Sidebar } from './components/Sidebar'
import { Header } from './components/Header'
import { Footer } from './components/Footer'
import { bridgeService } from './services/bridgeService'
import { perfService } from './services/perfService'
import { useLumiTrackStore } from './store/useLumiTrackStore'

import { DeveloperWorkspace } from './workspaces/DeveloperWorkspace/DeveloperWorkspace'
import { EvaluatorWorkspace } from './workspaces/EvaluatorWorkspace/EvaluatorWorkspace'
import { DiagnosticsWorkspace } from './workspaces/DiagnosticsWorkspace/DiagnosticsWorkspace'
import { HistoryWorkspace } from './workspaces/HistoryWorkspace/HistoryWorkspace'
import { ResultsWorkspace } from './workspaces/ResultsWorkspace/ResultsWorkspace'


export const App: React.FC = () => {
  const activeWorkspace = useLumiTrackStore((state) => state.activeWorkspace)
  const setConnected = useLumiTrackStore((state) => state.setConnected)
  const setStatus = useLumiTrackStore((state) => state.setStatus)
  const setTelemetry = useLumiTrackStore((state) => state.setTelemetry)
  const setLatestFrame = useLumiTrackStore((state) => state.setLatestFrame)
  const setSubsystems = useLumiTrackStore((state) => state.setSubsystems)
  const setRunHistory = useLumiTrackStore((state) => state.setRunHistory)
  const setSelectedArtifact = useLumiTrackStore((state) => state.setSelectedArtifact)
  const setBenchmarkProgress = useLumiTrackStore((state) => state.setBenchmarkProgress)
  const setLatestBenchmarkResult = useLumiTrackStore((state) => state.setLatestBenchmarkResult)
  const setResultsData = useLumiTrackStore((state) => state.setResultsData)
  const updateBrowserPerf = useLumiTrackStore((state) => state.updateBrowserPerf)

  useEffect(() => {
    // 1. Subscribe to all QtWebChannel IPC bridge events
    const unsubConn = bridgeService.onConnectionChange((connected) => {
      setConnected(connected)
    })

    const unsubStatus = bridgeService.onSystemStatus((status) => {
      setStatus(status)
    })

    const unsubTelemetry = bridgeService.onTelemetry((telemetry) => {
      setTelemetry(telemetry)
      perfService.recordTelemetryTick()
    })

    const unsubFrame = bridgeService.onSensorFrame((frame) => {
      setLatestFrame(frame)
    })

    const unsubDiagnostics = bridgeService.onDiagnostics((diag) => {
      setSubsystems(diag)
    })

    const unsubHistory = bridgeService.onRunHistory((history) => {
      setRunHistory(history)
    })

    const unsubArtifact = bridgeService.onArtifactLoaded((artifact) => {
      setSelectedArtifact(artifact)
    })

    const unsubBenchProgress = bridgeService.onBenchmarkProgress((prog) => {
      setBenchmarkProgress(prog)
    })

    const unsubBenchResult = bridgeService.onBenchmarkCompleted((res) => {
      setLatestBenchmarkResult(res)
    })

    const unsubResultsData = bridgeService.onResultsAnalysisLoaded((data) => {
      setResultsData(data)
    })

    // 2. Browser performance metrics sync loop
    const perfInterval = setInterval(() => {
      updateBrowserPerf(perfService.getMetrics())
    }, 500)

    // 3. Initialize QWebChannel connection to Python PySide6 host
    bridgeService.init().then((success) => {
      console.log('[SANKET] Bridge initialization result:', success)
    })

    return () => {
      unsubConn()
      unsubStatus()
      unsubTelemetry()
      unsubFrame()
      unsubDiagnostics()
      unsubHistory()
      unsubArtifact()
      unsubBenchProgress()
      unsubBenchResult()
      unsubResultsData()
      clearInterval(perfInterval)
    }
  }, [
    setConnected,
    setStatus,
    setTelemetry,
    setLatestFrame,
    setSubsystems,
    setRunHistory,
    setSelectedArtifact,
    setBenchmarkProgress,
    setLatestBenchmarkResult,
    setResultsData,
    updateBrowserPerf,
  ])

  // Render workspace based on active selection
  const renderWorkspace = () => {
    switch (activeWorkspace) {
      case 'developer':
        return <DeveloperWorkspace />
      case 'evaluator':
        return <EvaluatorWorkspace />
      case 'diagnostics':
        return <DiagnosticsWorkspace />
      case 'history':
        return <HistoryWorkspace />
      case 'results':
        return <ResultsWorkspace />
      default:
        return <DeveloperWorkspace />
    }
  }

  return (
    <div className="bg-surface font-body-md text-on-surface antialiased selection:bg-primary-container selection:text-on-primary-container h-screen w-screen overflow-hidden flex">
      {/* Fixed Left Navigation Sidebar (width w-60) */}
      <Sidebar />

      {/* Main Content Area offset by pl-60, taking exact viewport height */}
      <div className="pl-60 w-full h-screen flex flex-col overflow-hidden">
        {/* Fixed Top Header (height h-10) */}
        <Header />

        {/* Workspace Body: single primary scroll container between fixed Header and Footer */}
        <main
          id="lumitrack-main-scroll-container"
          className="w-full mt-10 mb-7 h-[calc(100vh-68px)] max-h-[calc(100vh-68px)] overflow-y-auto overflow-x-hidden bg-surface"
        >
          {renderWorkspace()}
        </main>

        {/* Fixed Bottom Footer (height h-7) */}
        <Footer />
      </div>
    </div>
  )
}

export default App
