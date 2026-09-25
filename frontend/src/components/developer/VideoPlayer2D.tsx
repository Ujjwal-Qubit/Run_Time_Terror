import React, { useEffect, useRef, useState } from 'react';
import { Crosshair, Eye, EyeOff } from 'lucide-react';
import type { VisualizationPacket } from '../../types';

interface VideoPlayer2DProps {
  packet: VisualizationPacket | null;
}

export const VideoPlayer2D: React.FC<VideoPlayer2DProps> = ({ packet }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [showGroundTruth, setShowGroundTruth] = useState(true);
  const [showOverlays, setShowOverlays] = useState(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = packet?.resolution?.width || 640;
    const height = packet?.resolution?.height || 480;

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    // Clear background
    ctx.fillStyle = '#06090e';
    ctx.fillRect(0, 0, width, height);

    if (packet && packet.image_base64) {
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0, width, height);

        if (showOverlays) {
          drawOverlays(ctx, width, height, packet);
        }
      };
      img.src = packet.image_base64;
    } else {
      // Idle / Reset state rendering
      ctx.strokeStyle = 'rgba(0, 210, 255, 0.2)';
      ctx.lineWidth = 1;
      
      // Grid lines
      for (let x = 0; x < width; x += 40) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += 40) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Center reticle
      const cx = width / 2;
      const cy = height / 2;
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
      ctx.beginPath();
      ctx.moveTo(cx - 20, cy);
      ctx.lineTo(cx + 20, cy);
      ctx.moveTo(cx, cy - 20);
      ctx.lineTo(cx, cy + 20);
      ctx.stroke();

      ctx.fillStyle = '#94a3b8';
      ctx.font = '14px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText('OPTICAL SENSOR IDLE — CLICK START TO BEGIN ACQUISITION', cx, cy + 50);
    }
  }, [packet, showGroundTruth, showOverlays]);

  const drawOverlays = (ctx: CanvasRenderingContext2D, width: number, height: number, pkt: VisualizationPacket) => {
    const cx = width / 2;
    const cy = height / 2;

    // 1. Center Boresight Reticle (White Crosshair)
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(cx - 15, cy);
    ctx.lineTo(cx + 15, cy);
    ctx.moveTo(cx, cy - 15);
    ctx.lineTo(cx, cy + 15);
    ctx.stroke();

    // Deadband boundary circle (e.g. 10px)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.beginPath();
    ctx.arc(cx, cy, 10, 0, Math.PI * 2);
    ctx.stroke();

    // 2. Adaptive ROI Box (Cyan)
    if (pkt.roi) {
      ctx.strokeStyle = '#00d2ff';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(pkt.roi.x, pkt.roi.y, pkt.roi.w, pkt.roi.h);
      ctx.fillStyle = 'rgba(0, 210, 255, 0.1)';
      ctx.fillRect(pkt.roi.x, pkt.roi.y, pkt.roi.w, pkt.roi.h);
    }

    // 3. Sub-Pixel Estimated Centroid (Red Crosshair + Circle)
    if (pkt.estimated_centroid && (pkt.tracking_state === 'TRACKING' || pkt.tracking_state === 'ACQUIRING' || pkt.tracking_state === 'REACQUIRING')) {
      const ex = pkt.estimated_centroid.x;
      const ey = pkt.estimated_centroid.y;

      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 1.5;

      // 5px radius circle
      ctx.beginPath();
      ctx.arc(ex, ey, 5, 0, Math.PI * 2);
      ctx.stroke();

      // 10px crosshair
      ctx.beginPath();
      ctx.moveTo(ex - 8, ey);
      ctx.lineTo(ex + 8, ey);
      ctx.moveTo(ex, ey - 8);
      ctx.lineTo(ex, ey + 8);
      ctx.stroke();

      // Laser vector from center to target
      ctx.strokeStyle = 'rgba(239, 68, 68, 0.5)';
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(ex, ey);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 4. Ground Truth Marker (Green Square — Debug Mode)
    if (showGroundTruth && pkt.ground_truth) {
      const gx = pkt.ground_truth.x;
      const gy = pkt.ground_truth.y;
      ctx.fillStyle = '#10b981';
      ctx.fillRect(gx - 3, gy - 3, 6, 6);
      ctx.strokeStyle = '#047857';
      ctx.strokeRect(gx - 3, gy - 3, 6, 6);
    }

    // 5. Live Top-Left HUD Telemetry Overlay
    ctx.fillStyle = 'rgba(6, 11, 20, 0.8)';
    ctx.fillRect(10, 10, 220, 115);
    ctx.strokeStyle = 'rgba(0, 210, 255, 0.4)';
    ctx.strokeRect(10, 10, 220, 115);

    ctx.font = '11px JetBrains Mono, monospace';
    ctx.textAlign = 'left';

    ctx.fillStyle = '#94a3b8';
    ctx.fillText(`FRAME: ${pkt.frame_number}`, 18, 28);

    const stateColor =
      pkt.tracking_state === 'TRACKING' ? '#34d399' :
      pkt.tracking_state === 'ACQUIRING' ? '#38bdf8' :
      pkt.tracking_state === 'LOST' ? '#f87171' : '#f1f5f9';

    ctx.fillStyle = stateColor;
    ctx.fillText(`STATE: ${pkt.tracking_state} [${pkt.lock_status}]`, 18, 46);

    ctx.fillStyle = '#e2e8f0';
    ctx.fillText(`TRK ERR: ${pkt.tracking_error_px !== null ? `${pkt.tracking_error_px} px` : '---'}`, 18, 64);
    ctx.fillText(`LATENCY: ${pkt.latency_ms} ms | FPS: ${pkt.fps}`, 18, 82);
    ctx.fillText(`PTZ: P ${pkt.pan_angle_deg}° / T ${pkt.tilt_angle_deg}°`, 18, 100);
    ctx.fillText(`FOV: ${pkt.camera_fov}°`, 18, 118);
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Viewport Action Bar */}
      <div style={{
        padding: '8px 14px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '12px',
        background: 'rgba(10, 15, 25, 0.6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#38bdf8', fontWeight: 600 }}>
          <Crosshair className="w-4 h-4" />
          <span>2D Optical Sensor Focal Plane (HUD Viewport)</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => setShowGroundTruth(!showGroundTruth)}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '4px 8px' }}
            title="Toggle Ground Truth Overlay"
          >
            {showGroundTruth ? <Eye className="w-3.5 h-3.5" style={{ color: '#10b981' }} /> : <EyeOff className="w-3.5 h-3.5" />}
            <span>GT Marker</span>
          </button>

          <button
            onClick={() => setShowOverlays(!showOverlays)}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '4px 8px' }}
          >
            <span>Overlays: {showOverlays ? 'ON' : 'OFF'}</span>
          </button>
        </div>
      </div>

      {/* Canvas Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#04060a',
        padding: '12px',
        position: 'relative'
      }}>
        <canvas
          ref={canvasRef}
          style={{
            maxWidth: '100%',
            maxHeight: '100%',
            objectFit: 'contain',
            borderRadius: '4px',
            boxShadow: '0 0 30px rgba(0, 0, 0, 0.9), 0 0 1px 1px rgba(0, 210, 255, 0.2)'
          }}
        />
      </div>
    </div>
  );
};
