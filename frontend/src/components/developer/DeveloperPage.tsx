import React, { useState } from 'react';
import { Crosshair, Box } from 'lucide-react';
import { ControlPanel } from './ControlPanel';
import { ConfigPanel } from './ConfigPanel';
import { VideoPlayer2D } from './VideoPlayer2D';
import { View3DThree } from './View3DThree';
import { TelemetryPanel } from './TelemetryPanel';
import type { AlgorithmInfo, SystemConfig, VisualizationPacket } from '../../types';

interface DeveloperPageProps {
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
  config: SystemConfig | null;
  onUpdateConfig: (partial: Partial<SystemConfig>) => void;
  packet: VisualizationPacket | null;
}

export const DeveloperPage: React.FC<DeveloperPageProps> = (props) => {
  const [viewportTab, setViewportTab] = useState<'2d' | '3d'>('2d');

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '380px 1fr',
      gap: '14px',
      height: '100%',
      minHeight: 0,
      padding: '0 16px 16px 0',
      overflow: 'hidden',
      boxSizing: 'border-box'
    }}>
      {/* Left Column: Controls & Configuration (Independently Scrollable) */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        overflowY: 'auto',
        minHeight: 0,
        height: '100%',
        maxHeight: '100%',
        paddingRight: '6px',
        paddingBottom: '16px',
        boxSizing: 'border-box'
      }}>
        <ControlPanel
          mode={props.mode}
          setMode={props.setMode}
          scenarios={props.scenarios}
          selectedScenario={props.selectedScenario}
          onSelectScenario={props.onSelectScenario}
          mp4Path={props.mp4Path}
          setMp4Path={props.setMp4Path}
          algorithms={props.algorithms}
          activeAlgorithm={props.activeAlgorithm}
          onSelectAlgorithm={props.onSelectAlgorithm}
          simulationStatus={props.simulationStatus}
          onStart={props.onStart}
          onStop={props.onStop}
          onPause={props.onPause}
          onResume={props.onResume}
          onReset={props.onReset}
          algorithmError={props.algorithmError}
        />

        <ConfigPanel
          config={props.config}
          onUpdateConfig={props.onUpdateConfig}
          disabled={props.mode === 'MP4'}
        />
      </div>

      {/* Right Column: Dual Viewport + Bottom Telemetry Bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%', overflow: 'hidden' }}>
        {/* Dual Viewport Tabs */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setViewportTab('2d')}
            className={`btn ${viewportTab === '2d' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '12px', padding: '6px 14px' }}
          >
            <Crosshair className="w-4 h-4" />
            <span>2D HUD Sensor View</span>
          </button>
          <button
            onClick={() => setViewportTab('3d')}
            className={`btn ${viewportTab === '3d' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '12px', padding: '6px 14px' }}
          >
            <Box className="w-4 h-4" />
            <span>3D Geometric Orbital View</span>
          </button>
        </div>

        {/* Viewport Display Area */}
        <div style={{ flex: 1, minHeight: 0 }}>
          {viewportTab === '2d' ? (
            <VideoPlayer2D packet={props.packet} />
          ) : (
            <View3DThree packet={props.packet} />
          )}
        </div>

        {/* Bottom 11-field Telemetry HUD Bar */}
        <TelemetryPanel packet={props.packet} activeAlgorithm={props.activeAlgorithm} />
      </div>
    </div>
  );
};
