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
        maxHeight: '300px',
        overflowY: 'auto',
        paddingRight: '4px'
      }}>

        {/* ================================================================
            CAMERA TAB
            Fields: width, height, fov_h_deg, fov_v_deg, update_rate_hz
            (initial_x, initial_y are scene-center by default, not shown here)
            ================================================================ */}
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
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Vertical FOV (°)</label>
                <input
                  type="number"
                  step="0.1"
                  value={config.camera.fov_v_deg}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ camera: { ...config.camera, fov_v_deg: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
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
        )}

        {/* ================================================================
            TARGET TAB
            Fields: size, shape, intensity, speed, motion_type
            motion_type → motion section (correct backend field)
            speed → target.speed (correct backend field)
            ================================================================ */}
        {activeTab === 'target' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Beacon Size (px)</label>
                <input
                  type="number"
                  min="5"
                  max="20"
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
                  onChange={(e) => onUpdateConfig({ target: { ...config.target, shape: e.target.value } })}
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
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Intensity (0–255)</label>
                <input
                  type="number"
                  min="0"
                  max="255"
                  value={config.target.intensity}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ target: { ...config.target, intensity: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
              <div>
                {/* target.speed is the real backend field (TargetConfig.speed) */}
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Speed (px/s)</label>
                <input
                  type="number"
                  step="5"
                  min="0"
                  value={config.target.speed}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ target: { ...config.target, speed: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
            </div>

            <div>
              {/* motion_type lives in MotionConfig, not TargetConfig — correct section */}
              <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Motion Pattern</label>
              <select
                value={config.motion.motion_type}
                disabled={disabled}
                onChange={(e) => onUpdateConfig({ motion: { ...config.motion, motion_type: e.target.value } })}
                style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
              >
                <option value="STRAIGHT_LINE">Straight Line</option>
                <option value="CIRCULAR">Circular Orbit</option>
                <option value="FIGURE_8">Figure-8</option>
                <option value="SPIRAL">Spiral</option>
                <option value="SINUSOIDAL">Sinusoidal</option>
                <option value="RANDOM">Random Walk</option>
                <option value="POLYGON">Polygon</option>
                <option value="ZIGZAG">ZigZag</option>
              </select>
            </div>
          </div>
        )}

        {/* ================================================================
            DISTURBANCES TAB
            Atmospheric: condition, contrast_factor, brightness_offset
            Noise: gaussian_sigma, sp_density (all real backend fields)
            Jitter: max_px_per_frame
            Platform: max_px_per_frame
            Local Contrast: enabled, amplitude
            ================================================================ */}
        {activeTab === 'disturbances' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {/* Atmospheric */}
            <div style={{ fontSize: '10px', fontWeight: 700, color: '#64748b', letterSpacing: '0.05em' }}>ATMOSPHERIC</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Condition</label>
                <select
                  value={config.atmospheric.condition}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ atmospheric: { ...config.atmospheric, condition: e.target.value } })}
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
                {/* contrast_factor: real backend field (AtmosphericConfig.contrast_factor) */}
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Contrast Factor (0–1)</label>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={config.atmospheric.contrast_factor ?? ''}
                  placeholder="Condition default"
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({
                    atmospheric: {
                      ...config.atmospheric,
                      contrast_factor: e.target.value === '' ? null : Number(e.target.value)
                    }
                  })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
            </div>

            {/* Noise */}
            <div style={{ fontSize: '10px', fontWeight: 700, color: '#64748b', letterSpacing: '0.05em', marginTop: '4px' }}>SENSOR NOISE</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
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
                  <option value="GAUSSIAN">Gaussian (σ)</option>
                  <option value="SP">Salt & Pepper</option>
                  <option value="POISSON">Poisson Shot Noise</option>
                </select>
              </div>
              <div>
                {/* gaussian_sigma: real backend field (NoiseConfig.gaussian_sigma) */}
                {config.noise.gaussian_enabled && (
                  <>
                    <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Gaussian Sigma (σ)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      max="50"
                      value={config.noise.gaussian_sigma}
                      disabled={disabled}
                      onChange={(e) => onUpdateConfig({ noise: { ...config.noise, gaussian_sigma: Number(e.target.value) } })}
                      style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                    />
                  </>
                )}
                {/* sp_density: real backend field (NoiseConfig.sp_density) */}
                {config.noise.sp_enabled && (
                  <>
                    <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>S&P Density (0–1)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                      value={config.noise.sp_density}
                      disabled={disabled}
                      onChange={(e) => onUpdateConfig({ noise: { ...config.noise, sp_density: Number(e.target.value) } })}
                      style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                    />
                  </>
                )}
                {/* poisson_scale: real backend field (NoiseConfig.poisson_scale). 1.0 = standard */}
                {config.noise.poisson_enabled && (
                  <>
                    <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Poisson Scale (exposure)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.1"
                      max="5"
                      value={config.noise.poisson_scale}
                      disabled={disabled}
                      onChange={(e) => onUpdateConfig({ noise: { ...config.noise, poisson_scale: Number(e.target.value) } })}
                      style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                    />
                  </>
                )}
              </div>
            </div>

            {/* Jitter */}
            <div style={{ fontSize: '10px', fontWeight: 700, color: '#64748b', letterSpacing: '0.05em', marginTop: '4px' }}>GEOMETRIC DISTURBANCES</div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-secondary)' }}>
                <span>Camera Jitter (px/frame)</span>
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
                <span>Platform Drift (px/frame)</span>
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

            {/* Local Contrast */}
            <div style={{ fontSize: '10px', fontWeight: 700, color: '#64748b', letterSpacing: '0.05em', marginTop: '4px' }}>LOCAL CONTRAST CLUTTER</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px', alignItems: 'center' }}>
              <label style={{ color: 'var(--text-secondary)', fontSize: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <input
                  type="checkbox"
                  checked={config.local_contrast?.enabled ?? false}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ local_contrast: { ...config.local_contrast, enabled: e.target.checked } })}
                />
                Enable
              </label>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Background clutter blobs</span>
            </div>
            {config.local_contrast?.enabled && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-secondary)' }}>
                  <span>Clutter Amplitude (0–150)</span>
                  <span className="font-mono" style={{ color: '#f59e0b' }}>{config.local_contrast.amplitude}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="150"
                  step="5"
                  value={config.local_contrast.amplitude}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ local_contrast: { ...config.local_contrast, amplitude: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px' }}
                />
              </div>
            )}
          </div>
        )}

        {/* ================================================================
            PTZ GIMBAL TAB
            Uses real backend field names:
              proportional_gain (not kp)
              integral_gain     (not ki)
              max_pan_speed_deg_s  (not max_speed_deg_per_s)
              max_tilt_speed_deg_s
              deadband_px
            There is no kd in the current backend PTZ controller.
            ================================================================ */}
        {activeTab === 'ptz' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                {/* proportional_gain: real backend field (PTZConfig.proportional_gain) */}
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Proportional Gain (Kp)</label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  value={config.ptz.proportional_gain}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, proportional_gain: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
              <div>
                {/* integral_gain: real backend field (PTZConfig.integral_gain) */}
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Integral Gain (Ki)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={config.ptz.integral_gain}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, integral_gain: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                {/* max_pan_speed_deg_s: real backend field */}
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Max Pan Speed (°/s)</label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  max="10"
                  value={config.ptz.max_pan_speed_deg_s}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, max_pan_speed_deg_s: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
              <div>
                {/* max_tilt_speed_deg_s: real backend field */}
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Max Tilt Speed (°/s)</label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  max="10"
                  value={config.ptz.max_tilt_speed_deg_s}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, max_tilt_speed_deg_s: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <div>
                {/* deadband_px: real backend field */}
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Deadband (px)</label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  value={config.ptz.deadband_px}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, deadband_px: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
              <div>
                {/* update_rate_hz: real backend field */}
                <label style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Update Rate (Hz)</label>
                <input
                  type="number"
                  step="1"
                  min="1"
                  value={config.ptz.update_rate_hz}
                  disabled={disabled}
                  onChange={(e) => onUpdateConfig({ ptz: { ...config.ptz, update_rate_hz: Number(e.target.value) } })}
                  style={{ width: '100%', marginTop: '2px', fontSize: '11px', padding: '4px 6px' }}
                />
              </div>
            </div>

            <div style={{ fontSize: '10px', color: 'var(--text-muted)', padding: '6px', background: 'rgba(15,23,42,0.5)', borderRadius: '4px' }}>
              Current controller: Proportional-Integral (PI). No derivative term (Kd) in this release.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
