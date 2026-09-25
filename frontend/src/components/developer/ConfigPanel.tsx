import React, { useState } from 'react';
import { Camera, Target, Wind, Sliders, ShieldCheck } from 'lucide-react';
import type { SystemConfig } from '../../types';

interface ConfigPanelProps {
  config: SystemConfig | null;
  onUpdateConfig: (partial: Partial<SystemConfig>) => void;
  disabled?: boolean;
}

type TabKey = 'camera' | 'target' | 'disturbances' | 'ptz';

export const ConfigPanel: React.FC<ConfigPanelProps> = ({ config, onUpdateConfig, disabled = false }) => {
  const [activeTab, setActiveTab] = useState<TabKey>('camera');

  if (!config) {
    return (
      <div className="glass-panel" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '11px' }}>
        Loading parameters...
      </div>
    );
  }

  const tabs = [
    { id: 'camera' as TabKey, label: 'Camera', icon: Camera },
    { id: 'target' as TabKey, label: 'Target', icon: Target },
    { id: 'disturbances' as TabKey, label: 'Disturbances', icon: Wind },
    { id: 'ptz' as TabKey, label: 'PTZ', icon: Sliders },
  ];

  return (
    <div className="glass-panel" style={{
      padding: '12px',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      opacity: disabled ? 0.5 : 1,
      width: '100%',
      boxSizing: 'border-box',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
          SIMULATION CONFIGURATION
        </span>
        <span style={{ fontSize: '10px', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <ShieldCheck className="w-3 h-3" /> Live Tuning Active
        </span>
      </div>

      {/* Tab Selectors Bar */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '4px',
        background: 'rgba(10, 15, 25, 0.6)',
        padding: '3px',
        borderRadius: '6px',
        border: '1px solid rgba(255, 255, 255, 0.06)'
      }}>
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              disabled={disabled}
              title={`Switch to ${tab.label} Settings`}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '4px',
                padding: '6px 2px',
                fontSize: '11px',
                fontWeight: isActive ? 700 : 500,
                color: isActive ? '#ffffff' : 'var(--text-secondary)',
                background: isActive ? 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)' : 'transparent',
                border: isActive ? '1px solid #38bdf8' : '1px solid transparent',
                borderRadius: '4px',
                cursor: 'pointer',
                boxShadow: isActive ? '0 0 10px rgba(56, 189, 248, 0.3)' : 'none',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon className="w-3.5 h-3.5 flex-shrink-0" />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Contents Area with dedicated scrollability */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        fontSize: '11px',
        maxHeight: '260px',
        overflowY: 'auto',
        paddingRight: '4px'
      }}>
        {/* CAMERA TAB */}
        {activeTab === 'camera' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Width (px)</label>
                <input
                  type="number"
                  value={config.camera.width}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ camera: { ...config.camera, width: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Height (px)</label>
                <input
                  type="number"
                  value={config.camera.height}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ camera: { ...config.camera, height: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Horizontal FOV (°)</label>
                <input
                  type="number"
                  step="0.1"
                  value={config.camera.fov_h_deg}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ camera: { ...config.camera, fov_h_deg: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Frame Rate (Hz)</label>
                <input
                  type="number"
                  value={config.camera.update_rate_hz}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ camera: { ...config.camera, update_rate_hz: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
            </div>
          </div>
        )}

        {/* TARGET TAB */}
        {activeTab === 'target' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Beacon Size (px)</label>
                <input
                  type="number"
                  min="3"
                  max="40"
                  value={config.target.size}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ target: { ...config.target, size: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Shape Profile</label>
                <select
                  value={config.target.shape}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ target: { ...config.target, shape: e.target.value as any } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                >
                  <option value="gaussian">Gaussian Spot</option>
                  <option value="circle">Circular Disk</option>
                  <option value="square">Square Spot</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Motion Pattern</label>
                <select
                  value={config.motion.motion_type}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ motion: { ...config.motion, motion_type: e.target.value as any } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
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
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Target Speed (px/s)</label>
                <input
                  type="number"
                  step="5"
                  value={config.motion.speed}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ motion: { ...config.motion, speed: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
            </div>
          </div>
        )}

        {/* DISTURBANCES TAB */}
        {activeTab === 'disturbances' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Atmospheric Model</label>
                <select
                  value={config.atmospheric.condition}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ atmospheric: { ...config.atmospheric, condition: e.target.value as any } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                >
                  <option value="CLEAR">CLEAR (Nominal)</option>
                  <option value="HAZE">HAZE (Moderate)</option>
                  <option value="FOG">FOG (Dense)</option>
                  <option value="RAIN">RAIN (Scattering)</option>
                  <option value="LOW_LIGHT">LOW LIGHT</option>
                </select>
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Noise Type</label>
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
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                >
                  <option value="NONE">None</option>
                  <option value="GAUSSIAN">Gaussian Noise (σ=8)</option>
                  <option value="SP">Salt & Pepper</option>
                  <option value="POISSON">Poisson Shot Noise</option>
                </select>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-secondary)' }}>
                <span>Camera Jitter (px/f)</span>
                <span className="font-mono" style={{ color: '#38bdf8' }}>{config.jitter.max_px_per_frame} px</span>
              </div>
              <input
                type="range"
                min="0"
                max="20"
                step="0.5"
                value={config.jitter.max_px_per_frame}
                disabled={disabled}
                onChange={(e) => onUpdateConfig({ jitter: { ...config.jitter, enabled: Number(e.target.value) > 0, max_px_per_frame: Number(e.target.value) } })}
                style={{ width: '100%', marginTop: '2px' }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-secondary)' }}>
                <span>Platform Drift (px/f)</span>
                <span className="font-mono" style={{ color: '#38bdf8' }}>{config.platform_motion.max_px_per_frame} px</span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                step="1"
                value={config.platform_motion.max_px_per_frame}
                disabled={disabled}
                onChange={(e) => onUpdateConfig({ platform_motion: { ...config.platform_motion, enabled: Number(e.target.value) > 0, max_px_per_frame: Number(e.target.value) } })}
                style={{ width: '100%', marginTop: '2px' }}
              />
            </div>
          </div>
        )}

        {/* PTZ GIMBAL TAB */}
        {activeTab === 'ptz' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Kp (Proportional)</label>
                <input
                  type="number"
                  step="0.5"
                  value={config.ptz.kp}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, kp: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Ki (Integral)</label>
                <input
                  type="number"
                  step="0.5"
                  value={config.ptz.ki}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, ki: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Deadband (px)</label>
                <input
                  type="number"
                  step="0.5"
                  value={config.ptz.deadband_px}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, deadband_px: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Max Speed (°/s)</label>
                <input
                  type="number"
                  step="1"
                  value={config.ptz.max_speed_deg_per_s}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, max_speed_deg_per_s: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
