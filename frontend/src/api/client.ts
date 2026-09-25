import type { AlgorithmInfo, MatrixResult, AIScenarioOutcome, ReportItem, SystemConfig, VisualizationPacket } from '../types';

/**
 * API base URL. In production (served by FastAPI), use same-origin (empty string).
 * In local Vite dev, use http://localhost:8000 or VITE_API_BASE_URL env variable.
 */
const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE_URL ??
  (typeof window !== 'undefined' && window.location.port === '5173'
    ? 'http://localhost:8000'
    : '');

/**
 * WebSocket base URL. Derived from API_BASE or window.location in production.
 */
const WS_BASE: string =
  (import.meta as any).env?.VITE_WS_BASE_URL ??
  (API_BASE
    ? API_BASE.replace(/^http/, 'ws')
    : `${typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws'}://${typeof window !== 'undefined' ? window.location.host : 'localhost:8000'}`);

export async function fetchAlgorithms(): Promise<{ algorithms: AlgorithmInfo[]; active_algorithm: string; error: string | null }> {
  const res = await fetch(`${API_BASE}/api/v1/algorithms`);
  if (!res.ok) throw new Error(`Failed to fetch algorithms: ${res.statusText}`);
  return res.json();
}

export async function selectAlgorithm(algorithm_name: string): Promise<{ success: boolean; active_algorithm: string; error: string | null }> {
  const res = await fetch(`${API_BASE}/api/v1/algorithms/select`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ algorithm_name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to select algorithm');
  }
  return res.json();
}

export async function fetchScenarios(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios`);
  if (!res.ok) throw new Error(`Failed to fetch scenarios: ${res.statusText}`);
  const data = await res.json();
  return data.scenarios || [];
}

export async function loadScenario(name: string): Promise<{ success: boolean; scenario: string; config: SystemConfig }> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios/load?name=${encodeURIComponent(name)}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to load scenario: ${res.statusText}`);
  return res.json();
}

export async function saveScenario(name: string): Promise<{ success: boolean; scenario: string }> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`Failed to save scenario: ${res.statusText}`);
  return res.json();
}

export async function deleteScenario(name: string): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete scenario: ${res.statusText}`);
  return res.json();
}

export async function fetchConfig(): Promise<SystemConfig> {
  const res = await fetch(`${API_BASE}/api/v1/config`);
  if (!res.ok) throw new Error(`Failed to fetch config: ${res.statusText}`);
  return res.json();
}

export async function updateConfig(partial: Partial<SystemConfig>): Promise<{ success: boolean; updated_config: SystemConfig }> {
  const res = await fetch(`${API_BASE}/api/v1/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(partial),
  });
  if (!res.ok) throw new Error(`Failed to update config: ${res.statusText}`);
  return res.json();
}

export async function startSimulation(): Promise<{ status: string; mode: string }> {
  const res = await fetch(`${API_BASE}/api/v1/simulation/start`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to start simulation');
  }
  return res.json();
}

export async function stopSimulation(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/v1/simulation/stop`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to stop simulation: ${res.statusText}`);
  return res.json();
}

export async function pauseSimulation(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/v1/simulation/pause`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to pause simulation: ${res.statusText}`);
  return res.json();
}

export async function resumeSimulation(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/v1/simulation/resume`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to resume simulation: ${res.statusText}`);
  return res.json();
}

export async function resetSimulation(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/v1/simulation/reset`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to reset simulation: ${res.statusText}`);
  return res.json();
}

export async function fetchSimulationStatus(): Promise<{ status: string; mode: string; frame_count: number; active_algorithm: string; algorithm_error: string | null }> {
  const res = await fetch(`${API_BASE}/api/v1/simulation/status`);
  if (!res.ok) throw new Error(`Failed to fetch status: ${res.statusText}`);
  return res.json();
}

export async function runBenchmarkMatrix(params: { subset: string; algorithm?: string; seed?: number; max_frames?: number }): Promise<MatrixResult> {
  const res = await fetch(`${API_BASE}/api/v1/evaluation/matrix`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Benchmark matrix execution failed');
  }
  return res.json();
}

export async function runAIScenario(params: { prompt: string; algorithm?: string; seed?: number; max_frames?: number }): Promise<AIScenarioOutcome> {
  const res = await fetch(`${API_BASE}/api/v1/evaluation/ai-scenario`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'AI scenario generation failed');
  }
  return res.json();
}

export async function fetchLatestReport(): Promise<{ filename: string; path: string; data: any }> {
  const res = await fetch(`${API_BASE}/api/v1/reports/latest`);
  if (!res.ok) throw new Error(`Failed to fetch latest report: ${res.statusText}`);
  return res.json();
}

export async function fetchReportsList(): Promise<{ reports: ReportItem[] }> {
  const res = await fetch(`${API_BASE}/api/v1/reports/list`);
  if (!res.ok) throw new Error(`Failed to fetch reports list: ${res.statusText}`);
  return res.json();
}

export class LiveStreamClient {
  private ws: WebSocket | null = null;
  private onPacketCallback: ((packet: VisualizationPacket) => void) | null = null;
  private onStatusChangeCallback: ((connected: boolean) => void) | null = null;
  private reconnectTimer: any = null;
  private shouldReconnect = true;

  connect(onPacket: (packet: VisualizationPacket) => void, onStatusChange?: (connected: boolean) => void) {
    this.onPacketCallback = onPacket;
    this.onStatusChangeCallback = onStatusChange || null;
    this.shouldReconnect = true;

    this.initSocket();
  }

  private initSocket() {
    try {
      this.ws = new WebSocket(`${WS_BASE}/ws/live`);

      this.ws.onopen = () => {
        this.onStatusChangeCallback?.(true);
      };

      this.ws.onmessage = (event) => {
        try {
          const packet: VisualizationPacket = JSON.parse(event.data);
          this.onPacketCallback?.(packet);
        } catch (err) {
          console.error('Failed to parse WebSocket packet:', err);
        }
      };

      this.ws.onclose = () => {
        this.onStatusChangeCallback?.(false);
        if (this.shouldReconnect) {
          this.reconnectTimer = setTimeout(() => this.initSocket(), 1000);
        }
      };

      this.ws.onerror = (err) => {
        console.warn('WebSocket error:', err);
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
