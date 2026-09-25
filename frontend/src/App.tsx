import { useEffect, useState, useRef } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import type { ActiveTab } from './components/layout/Sidebar';
import { DeveloperPage } from './components/developer/DeveloperPage';
import { EvaluatorPage } from './components/evaluator/EvaluatorPage';
import { ResultsPage } from './components/results/ResultsPage';
import {
  fetchAlgorithms,
  selectAlgorithm,
  fetchScenarios,
  loadScenario,
  fetchConfig,
  updateConfig,
  startSimulation,
  stopSimulation,
  pauseSimulation,
  resumeSimulation,
  resetSimulation,
  fetchSimulationStatus,
  LiveStreamClient,
} from './api/client';
import type { AlgorithmInfo, MatrixResult, SystemConfig, VisualizationPacket } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('developer');

  // Backend state
  const [algorithms, setAlgorithms] = useState<AlgorithmInfo[]>([]);
  const [activeAlgorithm, setActiveAlgorithm] = useState<string>('baseline_tracker');
  const [algorithmError, setAlgorithmError] = useState<string | null>(null);

  const [scenarios, setScenarios] = useState<string[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('');
  const [mode, setMode] = useState<'SIMULATION' | 'MP4'>('SIMULATION');
  const [mp4Path, setMp4Path] = useState<string>('');

  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [simulationStatus, setSimulationStatus] = useState<string>('IDLE');

  // WebSocket live frame packet & connection state
  const [packet, setPacket] = useState<VisualizationPacket | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);

  // Latest evaluation result for ResultsPage
  const [latestMatrixResult, setLatestMatrixResult] = useState<MatrixResult | null>(null);

  const streamClientRef = useRef<LiveStreamClient | null>(null);

  // Initial load
  useEffect(() => {
    async function init() {
      try {
        const [algosRes, scenariosList, cfg] = await Promise.all([
          fetchAlgorithms().catch(() => ({ algorithms: [], active_algorithm: 'baseline_tracker', error: null })),
          fetchScenarios().catch(() => []),
          fetchConfig().catch(() => null),
        ]);

        setAlgorithms(algosRes.algorithms || []);
        setActiveAlgorithm(algosRes.active_algorithm || 'baseline_tracker');
        setAlgorithmError(algosRes.error || null);
        setScenarios(scenariosList || []);
        if (cfg) setConfig(cfg);
      } catch (err) {
        console.error('Initialization error:', err);
      }
    }
    init();

    // Setup live stream client
    const client = new LiveStreamClient();
    streamClientRef.current = client;
    client.connect(
      (newPacket) => {
        setPacket(newPacket);
        if (newPacket.tracking_state && simulationStatus === 'IDLE') {
          setSimulationStatus('RUNNING');
        }
      },
      (connected) => {
        setWsConnected(connected);
      }
    );

    // Periodic simulation status check
    const statusInterval = setInterval(async () => {
      try {
        const status = await fetchSimulationStatus();
        setSimulationStatus(status.status);
        if (status.active_algorithm) setActiveAlgorithm(status.active_algorithm);
        setAlgorithmError(status.algorithm_error);
      } catch {}
    }, 1000);

    return () => {
      client.disconnect();
      clearInterval(statusInterval);
    };
  }, []);

  const handleSelectAlgorithm = async (algo: string) => {
    try {
      const res = await selectAlgorithm(algo);
      setActiveAlgorithm(res.active_algorithm);
      setAlgorithmError(res.error);
    } catch (err: any) {
      setAlgorithmError(err.message);
    }
  };

  const handleSelectScenario = async (sc: string) => {
    setSelectedScenario(sc);
    if (sc) {
      try {
        const res = await loadScenario(sc);
        if (res.config) setConfig(res.config);
      } catch (err) {
        console.error('Failed to load scenario:', err);
      }
    }
  };

  const handleUpdateConfig = async (partial: Partial<SystemConfig>) => {
    try {
      const res = await updateConfig(partial);
      if (res.updated_config) setConfig(res.updated_config);
    } catch (err) {
      console.error('Failed to update config:', err);
    }
  };

  const handleStart = async () => {
    try {
      // Sync simulation mode before start
      await updateConfig({
        simulation: {
          ...config?.simulation!,
          mode,
          mp4_path: mode === 'MP4' ? mp4Path : undefined,
        } as any,
      });

      const res = await startSimulation();
      setSimulationStatus(res.status);
    } catch (err: any) {
      alert(`Simulation start error: ${err.message}`);
    }
  };

  const handleStop = async () => {
    try {
      const res = await stopSimulation();
      setSimulationStatus(res.status);
    } catch (err) {
      console.error('Stop error:', err);
    }
  };

  const handlePause = async () => {
    try {
      const res = await pauseSimulation();
      setSimulationStatus(res.status);
    } catch (err) {
      console.error('Pause error:', err);
    }
  };

  const handleResume = async () => {
    try {
      const res = await resumeSimulation();
      setSimulationStatus(res.status);
    } catch (err) {
      console.error('Resume error:', err);
    }
  };

  const handleReset = async () => {
    try {
      const res = await resetSimulation();
      setSimulationStatus(res.status);
      setPacket(null);
    } catch (err) {
      console.error('Reset error:', err);
    }
  };

  const handleBenchmarkComplete = (result: MatrixResult) => {
    setLatestMatrixResult(result);
    // Auto switch to Results & Analysis tab
    setActiveTab('results');
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Top Aerospace HUD Header */}
      <Header
        packet={packet}
        activeAlgorithm={activeAlgorithm}
        wsConnected={wsConnected}
        simulationStatus={simulationStatus}
      />

      {/* Main Content Body */}
      <div style={{ flex: 1, display: 'flex', gap: '14px', minHeight: 0 }}>
        {/* Navigation Sidebar */}
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Dynamic Workflow Page Content */}
        <main style={{ flex: 1, minHeight: 0, height: 'calc(100% - 12px)', marginTop: '12px', overflow: 'hidden' }}>
          {activeTab === 'developer' && (
            <DeveloperPage
              mode={mode}
              setMode={setMode}
              scenarios={scenarios}
              selectedScenario={selectedScenario}
              onSelectScenario={handleSelectScenario}
              mp4Path={mp4Path}
              setMp4Path={setMp4Path}
              algorithms={algorithms}
              activeAlgorithm={activeAlgorithm}
              onSelectAlgorithm={handleSelectAlgorithm}
              simulationStatus={simulationStatus}
              onStart={handleStart}
              onStop={handleStop}
              onPause={handlePause}
              onResume={handleResume}
              onReset={handleReset}
              algorithmError={algorithmError}
              config={config}
              onUpdateConfig={handleUpdateConfig}
              packet={packet}
            />
          )}

          {activeTab === 'evaluator' && (
            <EvaluatorPage
              algorithms={algorithms}
              activeAlgorithm={activeAlgorithm}
              onBenchmarkComplete={handleBenchmarkComplete}
            />
          )}

          {activeTab === 'results' && (
            <ResultsPage latestResult={latestMatrixResult} />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
