import type { VisualizationPacket } from '../../types';

export function hasTargetLock(packet: VisualizationPacket | null): boolean {
  return packet?.lock_status === 'LOCKED' && packet.tracking_state === 'TRACKING'
    && packet.estimated_centroid !== null;
}
