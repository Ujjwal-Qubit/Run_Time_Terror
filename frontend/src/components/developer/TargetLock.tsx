import { Crosshair } from 'lucide-react';
import type { VisualizationPacket } from '../../types';

import { hasTargetLock } from './targetLockState';

export function TargetLock({ packet }: { packet: VisualizationPacket | null }) {
  const locked = hasTargetLock(packet);
  const acquiring = packet?.tracking_state === 'ACQUIRING' || packet?.tracking_state === 'REACQUIRING';
  const label = locked ? 'TARGET LOCKED' : acquiring ? 'ACQUIRING TARGET' : packet?.tracking_state === 'LOST' ? 'TARGET LOST' : packet ? 'SEARCHING' : 'SENSOR IDLE';
  const color = locked ? '#34d399' : acquiring ? '#fbbf24' : '#94a3b8';
  return <span role="status" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '5px 8px', border: `1px solid ${color}`, borderRadius: '4px', background: 'rgba(6, 11, 20, 0.9)', color, fontSize: '10px', fontWeight: 700, whiteSpace: 'nowrap' }}><Crosshair size={13} />{label}</span>;
}
