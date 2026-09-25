import React from 'react';
import { Play, Square, Pause, RotateCcw, Cpu, Video, AlertTriangle, Layers } from 'lucide-react';
import type { AlgorithmInfo } from '../../types';

interface ControlPanelProps {
  mode: 'SIMULATION' | 'MP4';
  setMode: (mode: 'SIMULATION' | 'MP4') => void;
  scenarios: string[];
  selectedScenario: string;
  onSelectScenario: (scenario: string) => void;
  mp4Path: string;
  setMp4Path: (path: string) => void;
  algorithms: AlgorithmInfo[];
  activeAlgorithm: string;
  onSelectAlgorithm: (algo: string) => void;
  simulationStatus: string;
  onStart: () => void;
  onStop: () => void;
  onPause: () => void;
  onResume: () => void;
  onReset: () => void;
  algorithmError: string | null;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  mode,
  setMode,
  scenarios,
  selectedScenario,
  onSelectScenario,
  mp4Path,
  setMp4Path,
  algorithms,
  activeAlgorithm,
  onSelectAlgorithm,
  simulationStatus,
  onStart,
  onStop,
  onPause,
  onResume,
  onReset,
  algorithmError,
}) => {
  const isRunning = simulationStatus === 'RUNNING';
  const isPaused = simulationStatus === 'PAUSED';
  const isIdle = simulationStatus === 'IDLE';

  const currentAlgoObj = algorithms.find((a) => a.name === activeAlgorithm);

  return (
    <div className="glass-panel" style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {/* 1. Operation Mode Selection & Scenario in single row */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
          <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
            OPERATION MODE
          </span>
          <span style={{ fontSize: '10px', color: '#38bdf8' }}>{mode === 'SIMULATION' ? 'BM1 Closed-Loop' : 'BM2 Open-Loop'}</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
          <button
            onClick={() => setMode('SIMULATION')}
            disabled={!isIdle}
            className={`btn ${mode === 'SIMULATION' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '11px', padding: '6px 8px' }}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>BM1 (Simulation)</span>
          </button>
          <button
            onClick={() => setMode('MP4')}
            disabled={!isIdle}
            className={`btn ${mode === 'MP4' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '11px', padding: '6px 8px' }}
          >
            <Video className="w-3.5 h-3.5" />
            <span>BM2 (MP4 Video)</span>
          </button>
        </div>
      </div>

      {/* Scenario / MP4 picker */}
      {mode === 'SIMULATION' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <label style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Scenario Preset:</label>
          <select
            value={selectedScenario}
            onChange={(e) => onSelectScenario(e.target.value)}
            disabled={!isIdle}
            style={{ width: '100%', fontSize: '12px', padding: '4px 8px' }}
          >
            <option value="">Default Parameters (Interactive)</option>
            {scenarios.map((sc) => (
              <option key={sc} value={sc}>
                {sc}
              </option>
            ))}
          </select>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <label style={{ fontSize: '10px', color: 'var(--text-muted)' }}>MP4 Video File:</label>
          <input
            type="text"
            placeholder="e.g. data/test_flight.mp4"
            value={mp4Path}
            onChange={(e) => setMp4Path(e.target.value)}
            disabled={!isIdle}
            style={{ width: '100%', fontSize: '12px', padding: '4px 8px' }}
          />
        </div>
      )}

      {/* 2. Algorithm (Unit Under Test) */}
      <div className="glass-panel-inset" style={{ padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 600 }}>
            <Cpu className="w-3.5 h-3.5" style={{ color: '#00d2ff' }} />
            <span>Algorithm Under Test (UUT)</span>
          </div>
          <span className={`badge ${algorithmError ? 'badge-unlocked' : 'badge-locked'}`} style={{ fontSize: '9px', padding: '2px 6px' }}>
            {algorithmError ? 'ERROR' : (currentAlgoObj?.status || 'READY')}
          </span>
        </div>

        <select
          value={activeAlgorithm}
          onChange={(e) => onSelectAlgorithm(e.target.value)}
          disabled={!isIdle}
          style={{ width: '100%', fontSize: '12px', padding: '4px 8px' }}
        >
          {algorithms.map((algo) => (
            <option key={algo.name} value={algo.name}>
              {algo.name} (v{algo.version})
            </option>
          ))}
        </select>

        {algorithmError && (
          <div style={{
            padding: '4px 6px',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '4px',
            fontSize: '10px',
            color: '#fca5a5',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <AlertTriangle className="w-3 h-3 flex-shrink-0" />
            <span>{algorithmError}</span>
          </div>
        )}
      </div>

      {/* 3. Playback Controls */}
      <div>
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr 1fr', gap: '6px' }}>
          <button
            onClick={onStart}
            disabled={!isIdle}
            className="btn btn-success"
            style={{ fontSize: '11px', padding: '6px 8px' }}
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Start</span>
          </button>

          <button
            onClick={onStop}
            disabled={isIdle}
            className="btn btn-danger"
            style={{ fontSize: '11px', padding: '6px 8px' }}
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>Stop</span>
          </button>

          {isPaused ? (
            <button
              onClick={onResume}
              disabled={!isPaused}
              className="btn btn-primary"
              style={{ fontSize: '11px', padding: '6px 8px' }}
            >
              <Play className="w-3.5 h-3.5" />
              <span>Resume</span>
            </button>
          ) : (
            <button
              onClick={onPause}
              disabled={!isRunning}
              className="btn btn-secondary"
              style={{ fontSize: '11px', padding: '6px 8px' }}
            >
              <Pause className="w-3.5 h-3.5" />
              <span>Pause</span>
            </button>
          )}

          <button
            onClick={onReset}
            disabled={!isIdle}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '6px 8px' }}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        </div>
      </div>
    </div>
  );
};
