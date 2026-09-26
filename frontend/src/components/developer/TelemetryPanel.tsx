import React from 'react';
import { Radio } from 'lucide-react';
import type { VisualizationPacket } from '../../types';

interface TelemetryPanelProps {
  packet: VisualizationPacket | null;
  activeAlgorithm: string;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ packet, activeAlgorithm }) => {
  const isLocked = packet?.lock_status === 'LOCKED';
  const isAcquiring = packet?.lock_status === 'ACQUIRING';

  const metrics = [
    {
      label: 'ALGORITHM',
      value: activeAlgorithm || 'baseline_tracker',
      unit: '',
      color: '#38bdf8',
      isBold: true,
    },
    {
      label: 'FRAME',
      value: packet ? packet.frame_number : '---',
      unit: '',
      color: '#f8fafc',
    },
    {
      label: 'STATE',
      value: packet ? packet.tracking_state : 'IDLE',
      unit: '',
      color: isLocked ? '#34d399' : isAcquiring ? '#fbbf24' : '#f87171',
      isBold: true,
    },
    {
      label: 'LOCK STATUS',
      value: packet ? packet.lock_status : 'UNLOCKED',
      unit: '',
      color: isLocked ? '#34d399' : isAcquiring ? '#fbbf24' : '#f87171',
      isBold: true,
    },
    {
      label: 'TRACKING ERROR',
      value: packet?.tracking_error_px !== null && packet?.tracking_error_px !== undefined ? packet.tracking_error_px.toFixed(2) : '---',
      unit: 'px',
      color: '#fbbf24',
    },
    {
      label: 'CENTROID X',
      value: packet?.estimated_centroid ? packet.estimated_centroid.x.toFixed(2) : '---',
      unit: 'px',
      color: '#e2e8f0',
    },
    {
      label: 'CENTROID Y',
      value: packet?.estimated_centroid ? packet.estimated_centroid.y.toFixed(2) : '---',
      unit: 'px',
      color: '#e2e8f0',
    },
    {
      label: 'GIMBAL PAN',
      value: packet ? packet.pan_angle_deg.toFixed(2) : '0.00',
      unit: 'deg',
      color: '#60a5fa',
    },
    {
      label: 'GIMBAL TILT',
      value: packet ? packet.tilt_angle_deg.toFixed(2) : '0.00',
      unit: 'deg',
      color: '#60a5fa',
    },
    {
      label: 'THROUGHPUT',
      value: packet ? packet.fps.toFixed(1) : '---',
      unit: 'FPS',
      color: '#34d399',
    },
    {
      label: 'CORE LATENCY',
      value: packet ? packet.latency_ms.toFixed(2) : '---',
      unit: 'ms',
      color: '#38bdf8',
    },
  ];

  return (
    <div className="glass-panel" style={{ padding: '10px 14px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '8px',
        fontSize: '11px',
        fontWeight: 700,
        color: 'var(--text-muted)',
        letterSpacing: '0.05em'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Radio className="w-3.5 h-3.5" style={{ color: '#00d2ff' }} />
          <span>REAL-TIME TELEMETRY HUD & GIMBAL KINEMATICS (30 HZ)</span>
        </div>
        <span className="font-mono" style={{ fontSize: '10px', color: '#94a3b8' }}>
          FIREWALL SECURE
        </span>
      </div>

      <div className="grid-telemetry">
        {metrics.map((m, idx) => (
          <div
            key={idx}
            className="glass-panel-inset"
            style={{
              padding: '6px 10px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center'
            }}
          >
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.04em' }}>
              {m.label}
            </div>
            <div className="font-mono" style={{
              fontSize: '13px',
              fontWeight: m.isBold ? 700 : 500,
              color: m.color,
              marginTop: '2px',
              display: 'flex',
              alignItems: 'baseline',
              gap: '3px'
            }}>
              <span>{m.value}</span>
              {m.unit && <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{m.unit}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
