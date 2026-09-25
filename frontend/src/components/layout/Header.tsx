import React from 'react';
import { Activity, Shield, Wifi, WifiOff, Disc3 } from 'lucide-react';
import type { VisualizationPacket } from '../../types';

interface HeaderProps {
  packet: VisualizationPacket | null;
  activeAlgorithm: string;
  wsConnected: boolean;
  simulationStatus: string;
}

export const Header: React.FC<HeaderProps> = ({
  packet,
  activeAlgorithm,
  wsConnected,
  simulationStatus,
}) => {
  const lockStatus = packet?.lock_status || 'UNLOCKED';
  const trackingState = packet?.tracking_state || 'IDLE';

  return (
    <header className="glass-panel" style={{
      margin: '12px 16px 0 16px',
      padding: '10px 20px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      borderBottom: '1px solid rgba(0, 210, 255, 0.2)'
    }}>
      {/* Brand & Mission Tag */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'linear-gradient(135deg, rgba(0,210,255,0.15) 0%, rgba(37,99,235,0.15) 100%)',
          padding: '6px 12px',
          borderRadius: '6px',
          border: '1px solid rgba(0,210,255,0.3)'
        }}>
          <Disc3 className="w-5 h-5" style={{ color: '#00d2ff', animation: simulationStatus === 'RUNNING' ? 'spin 3s linear infinite' : 'none' }} />
          <span style={{ fontWeight: 700, fontSize: '16px', letterSpacing: '0.05em', color: '#f0f4fc' }}>
            Lumi<span style={{ color: '#00d2ff' }}>Track</span>
          </span>
          <span style={{
            fontSize: '10px',
            background: 'rgba(255,153,51,0.2)',
            color: '#ff9933',
            border: '1px solid rgba(255,153,51,0.4)',
            padding: '2px 6px',
            borderRadius: '4px',
            fontWeight: 700
          }}>
            SIH 2026 / ISRO PS-4
          </span>
        </div>

        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Shield className="w-3.5 h-3.5" style={{ color: '#10b981' }} />
          <span>FSOC Coarse Alignment Testbed</span>
        </div>
      </div>

      {/* Central Telemetry Indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Active Algorithm Badge */}
        <div className="glass-panel-inset" style={{ padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
          <span style={{ color: 'var(--text-muted)' }}>UUT:</span>
          <span className="font-mono" style={{ color: '#38bdf8', fontWeight: 600 }}>{activeAlgorithm || 'baseline_tracker'}</span>
        </div>

        {/* Lock State Pill */}
        <div className={`badge ${
          lockStatus === 'LOCKED' ? 'badge-locked pulse-lock' :
          lockStatus === 'ACQUIRING' ? 'badge-acquiring' : 'badge-unlocked'
        }`}>
          <Activity className="w-3.5 h-3.5" />
          <span>{lockStatus} [{trackingState}]</span>
        </div>

        {/* WebSocket Heartbeat */}
        <div className="glass-panel-inset" style={{
          padding: '4px 10px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '11px',
          color: wsConnected ? '#34d399' : '#f87171'
        }}>
          {wsConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          <span>{wsConnected ? 'LIVE FEED' : 'DISCONNECTED'}</span>
        </div>
      </div>
    </header>
  );
};
