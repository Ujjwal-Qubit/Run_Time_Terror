import React, { useState } from 'react';
import { Camera, Target, Wind, Sliders, ShieldCheck } from 'lucide-react';
import type { SystemConfig } from '../../types';

interface ConfigPanelProps {
  config: SystemConfig | null;
  onUpdateConfig: (partial: Partial<SystemConfig>) => void;
  disabled?: boolean;
}

type TabKey = 'camera' | 'target' | 'motion' | 'disturbances' | 'ptz';

export const ConfigPanel: React.FC<ConfigPanelProps> = ({ config, onUpdateConfig, disabled = false }) => {
  const [activeTab, setActiveTab] = useState<TabKey>('camera');

  if (!config) {
    return (
      <div className="glass-panel" style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '12px' }}>
        Loading parameters...
      </div>
    );
  }

  const tabs = [
    { id: 'camera' as TabKey, label: 'Camera', icon: Camera },
    { id: 'target' as TabKey, label: 'Target', icon: Target },
    { id: 'disturbances' as TabKey, label: 'Disturb', icon: Wind },
    { id: 'ptz' as TabKey, label: 'PTZ', icon: Sliders },
  ];

  return (
    <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px', opacity: disabled ? 0.5 : 1, width: '100%', boxSizing: 'border-box', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
          SIMULATION CONFIGURATION
        </span>
        <span style={{ fontSize: '10px', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <ShieldCheck className="w-3 h-3" /> Live Sync
        </span>
      </div>

      {/* Tab Selectors — 4 column uniform grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '6px' }}>
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              disabled={disabled}
              title={tab.label === 'PTZ' ? 'PTZ Gimbal' : tab.label === 'Disturb' ? 'Disturbances' : tab.label}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px',
                padding: '6px 4px',
                fontSize: '11px',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? '#00d2ff' : 'var(--text-secondary)',
                background: isActive ? 'rgba(0, 210, 255, 0.12)' : 'transparent',
                border: 'none',
                borderBottom: isActive ? '2px solid #00d2ff' : '2px solid transparent',
                borderRadius: '4px 4px 0 0',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                boxSizing: 'border-box',
              }}
            >
              <Icon className="w-3.5 h-3.5 flex-shrink-0" />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Contents */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '12px' }}>
        {/* CAMERA TAB */}
        {activeTab === 'camera' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Resolution Width (px)</label>
                <input
                  type="number"
                  value={config.camera.width}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ camera: { ...config.camera, width: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '3px' }}
                />
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Resolution Height (px)</label>
                <input
                  type="number"
                  value={config.camera.height}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ camera: { ...config.camera, height: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '3px' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Horizontal FOV (deg)</label>
                <input
                  type="number"
                  step="0.1"
                  value={config.camera.fov_h_deg}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ camera: { ...config.camera, fov_h_deg: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '3px' }}
                />
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Update Rate (Hz)</label>
                <input
                  type="number"
                  value={config.camera.update_rate_hz}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ camera: { ...config.camera, update_rate_hz: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '3px' }}
                />
              </div>
            </div>
          </div>
        )}

        {/* TARGET TAB */}
        {activeTab === 'target' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Beacon Size (px)</label>
                <input
                  type="number"
                  min="3"
                  max="40"
                  value={config.target.size}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ target: { ...config.target, size: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '3px' }}
                />
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Shape</label>
                <select
                  value={config.target.shape}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ target: { ...config.target, shape: e.target.value as any } })}
                  style={{ width: '100%', marginTop: '3px' }}
                >
                  <option value="gaussian">Gaussian Spot</option>
                  <option value="circle">Circular Disk</option>
                  <option value="square">Square</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Motion Pattern</label>
                <select
                  value={config.motion.motion_type}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ motion: { ...config.motion, motion_type: e.target.value as any } })}
                  style={{ width: '100%', marginTop: '3px' }}
                >
                  <option value="STRAIGHT_LINE">Straight Line</option>
                  <option value="CIRCULAR">Circular Orbit</option>
                  <option value="FIGURE_8">Figure-8</option>
                  <option value="SPIRAL">Spiral</option>
                  <option value="SINUSOIDAL">Sinusoidal</option>
                  <option value="RANDOM">Random Walk</option>
                </select>
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Speed (px/s)</label>
                <input
                  type="number"
                  step="5"
                  value={config.motion.speed}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ motion: { ...config.motion, speed: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '3px' }}
                />
              </div>
            </div>
          </div>
        )}

        {/* DISTURBANCES TAB */}
        {activeTab === 'disturbances' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Atmospheric Condition</label>
                <select
                  value={config.atmospheric.condition}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ atmospheric: { ...config.atmospheric, condition: e.target.value as any } })}
                  style={{ width: '100%', marginTop: '3px' }}
                >
                  <option value="CLEAR">CLEAR (Ideal)</option>
                  <option value="HAZE">HAZE (Moderate)</option>
                  <option value="FOG">FOG (Dense)</option>
                  <option value="RAIN">RAIN (Scattering)</option>
                  <option value="LOW_LIGHT">LOW LIGHT</option>
                </select>
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Noise Type</label>
                <select
                  value={
                    config.noise.gaussian_enabled
                      ? 'GAUSSIAN'
                      : config.noise.sp_enabled
                      ? 'SP'
                      : config.noise.poisson_enabled
                      ? 'POISSON'
                      : 'NONE'
                  }
                  disabled={disabled}
                  onChange={(e) => {
                    const val = e.target.value;
                    onUpdateConfig({
                      noise: {
                        ...config.noise,
                        gaussian_enabled: val === 'GAUSSIAN',
                        sp_enabled: val === 'SP',
                        poisson_enabled: val === 'POISSON',
                      },
                    });
                  }}
                  style={{ width: '100%', marginTop: '3px' }}
                >
                  <option value="NONE">None</option>
                  <option value="GAUSSIAN">Gaussian Noise (σ=8)</option>
                  <option value="SP">Salt & Pepper</option>
                  <option value="POISSON">Poisson Shot Noise</option>
                </select>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)' }}>
                <span>Camera Jitter Amplitude (px/f)</span>
                <span className="font-mono">{config.jitter.max_px_per_frame} px</span>
              </div>
              <input
                type="range"
                min="0"
                max="20"
                step="0.5"
                value={config.jitter.max_px_per_frame}
                disabled={disabled}
                onChange={(e) => onUpdateConfig({ jitter: { ...config.jitter, enabled: Number(e.target.value) > 0, max_px_per_frame: Number(e.target.value) } })}
                style={{ width: '100%', marginTop: '4px' }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)' }}>
                <span>Platform Drift Motion (px/f)</span>
                <span className="font-mono">{config.platform_motion.max_px_per_frame} px</span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                step="1"
                value={config.platform_motion.max_px_per_frame}
                disabled={disabled}
                onChange={(e) => onUpdateConfig({ platform_motion: { ...config.platform_motion, enabled: Number(e.target.value) > 0, max_px_per_frame: Number(e.target.value) } })}
                style={{ width: '100%', marginTop: '4px' }}
              />
            </div>
          </div>
        )}

        {/* PTZ GIMBAL TAB */}
        {activeTab === 'ptz' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Proportional Gain (Kp)</label>
                <input
                  type="number"
                  step="0.5"
                  value={config.ptz.kp}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, kp: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '3px' }}
                />
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Integral Gain (Ki)</label>
                <input
                  type="number"
                  step="0.5"
                  value={config.ptz.ki}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, ki: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '3px' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Deadband (px)</label>
                <input
                  type="number"
                  step="0.5"
                  value={config.ptz.deadband_px}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, deadband_px: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '3px' }}
                />
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Max Slew Speed (°/s)</label>
                <input
                  type="number"
                  step="1"
                  value={config.ptz.max_speed_deg_per_s}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, max_speed_deg_per_s: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '3px' }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
