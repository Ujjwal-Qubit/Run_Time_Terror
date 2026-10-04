import React, { useEffect } from 'react'
import { Sidebar } from './components/Sidebar'
import { Header } from './components/Header'
import { Footer } from './components/Footer'
import { bridgeService } from './services/bridgeService'
import { perfService } from './services/perfService'
import { useSanketStore } from './store/useSanketStore'

import { DeveloperWorkspace } from './workspaces/DeveloperWorkspace/DeveloperWorkspace'
import { EvaluatorWorkspace } from './workspaces/EvaluatorWorkspace/EvaluatorWorkspace'
import { DiagnosticsWorkspace } from './workspaces/DiagnosticsWorkspace/DiagnosticsWorkspace'
import { HistoryWorkspace } from './workspaces/HistoryWorkspace/HistoryWorkspace'
import { ResultsWorkspace } from './workspaces/ResultsWorkspace/ResultsWorkspace'

export const App: React.FC = () => {
  const activeWorkspace = useSanketStore((state) => state.activeWorkspace)
  const setConnected = useSanketStore((state) => state.setConnected)
  const setStatus = useSanketStore((state) => state.setStatus)
  const setTelemetry = useSanketStore((state) => state.setTelemetry)
  const setLatestFrame = useSanketStore((state) => state.setLatestFrame)
  const setSubsystems = useSanketStore((state) => state.setSubsystems)
  const setRunHistory = useSanketStore((state) => state.setRunHistory)
  const setSelectedArtifact = useSanketStore((state) => state.setSelectedArtifact)
  const setBenchmarkProgress = useSanketStore((state) => state.setBenchmarkProgress)
  const setLatestBenchmarkResult = useSanketStore((state) => state.setLatestBenchmarkResult)
  const setResultsData = useSanketStore((state) => state.setResultsData)
  const updateBrowserPerf = useSanketStore((state) => state.updateBrowserPerf)

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
    <div className="bg-background font-body-md text-on-surface antialiased selection:bg-primary-container selection:text-on-primary-container min-h-screen w-screen overflow-x-hidden flex">
      {/* Fixed Left Navigation Sidebar (w-60) */}
      <Sidebar />

      {/* Main Content Area offset by pl-60 */}
      <div className="pl-60 w-full min-h-screen flex flex-col bg-background">
        {/* Fixed Top Header (h-14) */}
        <Header />

        {/* Workspace Body */}
        <main
          id="sanket-main-scroll-container"
          className="flex-1 pt-10 md:pt-14 pb-7 md:pb-8 w-full bg-surface relative min-h-[calc(100vh-68px)] overflow-y-auto overflow-x-hidden"
        >
          {renderWorkspace()}
        </main>

        {/* Fixed Bottom Footer (h-8) */}
        <Footer />
      </div>
    </div>
  )
}

export default App
