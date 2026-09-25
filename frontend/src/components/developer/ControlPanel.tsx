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
    <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* 1. Operation Mode Selection */}
      <div>
        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.05em', marginBottom: '8px' }}>
          OPERATION MODE
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <button
            onClick={() => setMode('SIMULATION')}
            disabled={!isIdle}
            className={`btn ${mode === 'SIMULATION' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '12px', padding: '8px' }}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Benchmark 1 (Sim)</span>
          </button>
          <button
            onClick={() => setMode('MP4')}
            disabled={!isIdle}
            className={`btn ${mode === 'MP4' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '12px', padding: '8px' }}
          >
            <Video className="w-3.5 h-3.5" />
            <span>Benchmark 2 (MP4)</span>
          </button>
        </div>
      </div>

      {/* Scenario or MP4 file picker */}
      {mode === 'SIMULATION' ? (
        <div>
          <label style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
            Predefined Scenario:
          </label>
          <select
            value={selectedScenario}
            onChange={(e) => onSelectScenario(e.target.value)}
            disabled={!isIdle}
            style={{ width: '100%' }}
          >
            <option value="">Default Parameters</option>
            {scenarios.map((sc) => (
              <option key={sc} value={sc}>
                {sc}
              </option>
            ))}
          </select>
        </div>
      ) : (
        <div>
          <label style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
            MP4 Video Path:
          </label>
          <input
            type="text"
            placeholder="e.g. data/test_flight.mp4"
            value={mp4Path}
            onChange={(e) => setMp4Path(e.target.value)}
            disabled={!isIdle}
            style={{ width: '100%' }}
          />
        </div>
      )}

      {/* 2. Algorithm (Unit Under Test) Management */}
      <div className="glass-panel-inset" style={{ padding: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600 }}>
            <Cpu className="w-4 h-4" style={{ color: '#00d2ff' }} />
            <span>Unit Under Test (UUT)</span>
          </div>
          <span className={`badge ${algorithmError ? 'badge-unlocked' : 'badge-locked'}`}>
            {algorithmError ? 'ERROR' : (currentAlgoObj?.status || 'READY')}
          </span>
        </div>

        <select
          value={activeAlgorithm}
          onChange={(e) => onSelectAlgorithm(e.target.value)}
          disabled={!isIdle}
          style={{ width: '100%', marginBottom: '8px' }}
        >
          {algorithms.map((algo) => (
            <option key={algo.name} value={algo.name}>
              {algo.name} (v{algo.version})
            </option>
          ))}
        </select>

        {currentAlgoObj && (
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
            <div><strong style={{ color: '#cbd5e1' }}>Author:</strong> {currentAlgoObj.author || 'SIH Evaluator'}</div>
            <div style={{ marginTop: '3px', color: 'var(--text-muted)' }}>{currentAlgoObj.description}</div>
          </div>
        )}

        {algorithmError && (
          <div style={{
            marginTop: '8px',
            padding: '6px 8px',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '4px',
            fontSize: '11px',
            color: '#fca5a5',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{algorithmError}</span>
          </div>
        )}
      </div>

      {/* 3. Playback Controls */}
      <div>
        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.05em', marginBottom: '8px' }}>
          PLAYBACK & CONTROLS
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <button
              onClick={onStart}
              disabled={!isIdle}
              className="btn btn-success"
              style={{ width: '100%' }}
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Start</span>
            </button>

            <button
              onClick={onStop}
              disabled={isIdle}
              className="btn btn-danger"
              style={{ width: '100%' }}
            >
              <Square className="w-4 h-4 fill-current" />
              <span>Stop</span>
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            {isPaused ? (
              <button
                onClick={onResume}
                disabled={!isPaused}
                className="btn btn-primary"
                style={{ width: '100%' }}
              >
                <Play className="w-4 h-4" />
                <span>Resume</span>
              </button>
            ) : (
              <button
                onClick={onPause}
                disabled={!isRunning}
                className="btn btn-secondary"
                style={{ width: '100%' }}
              >
                <Pause className="w-4 h-4" />
                <span>Pause</span>
              </button>
            )}

            <button
              onClick={onReset}
              disabled={!isIdle}
              className="btn btn-secondary"
              style={{ width: '100%' }}
            >
              <RotateCcw className="w-4 h-4" />
              <span>Reset</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
