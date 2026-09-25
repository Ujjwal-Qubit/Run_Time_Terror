import React, { useState } from 'react';
import { Play, Sparkles, Terminal, CheckCircle, XCircle, Loader2, Award, Zap } from 'lucide-react';
import { runBenchmarkMatrix, runAIScenario } from '../../api/client';
import type { AlgorithmInfo, MatrixResult } from '../../types';

interface EvaluatorPageProps {
  algorithms: AlgorithmInfo[];
  activeAlgorithm: string;
  onBenchmarkComplete: (result: MatrixResult) => void;
}

export const EvaluatorPage: React.FC<EvaluatorPageProps> = ({
  algorithms,
  activeAlgorithm,
  onBenchmarkComplete,
}) => {
  // Benchmark Matrix State
  const [subset, setSubset] = useState<'SMOKE' | 'CORE' | 'DISTURBANCE' | 'FULL'>('CORE');
  const [selectedAlgo, setSelectedAlgo] = useState(activeAlgorithm || 'baseline_tracker');
  const [matrixSeed, setMatrixSeed] = useState(42);
  const [matrixFrames, setMatrixFrames] = useState(30);
  const [isRunningMatrix, setIsRunningMatrix] = useState(false);
  const [matrixProgress, setMatrixProgress] = useState(0);

  // AI Scenario State
  const [aiPrompt, setAiPrompt] = useState(
    'Fast optical beacon moving in a spiral at 75 px/s through dense fog with severe camera jitter'
  );
  const [isRunningAI, setIsRunningAI] = useState(false);
  const [aiResult, setAiResult] = useState<any>(null);

  // Console Logs
  const [logs, setLogs] = useState<string[]>([
    'LumiTrack Evaluation Subsystem initialized.',
    'Ready to execute reproducible benchmark suites and generative AI test scenarios.',
  ]);

  const addLog = (msg: string) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  const handleRunMatrix = async () => {
    setIsRunningMatrix(true);
    setMatrixProgress(15);
    addLog(`Initiating Benchmark Matrix execution [Subset: ${subset}, UUT: ${selectedAlgo}, Seed: ${matrixSeed}]...`);

    try {
      setMatrixProgress(45);
      const res = await runBenchmarkMatrix({
        subset,
        algorithm: selectedAlgo,
        seed: matrixSeed,
        max_frames: matrixFrames,
      });

      setMatrixProgress(100);
      const verdictStr = res.passed_sih_spec ? 'PASSED (PS 26169 Compliant)' : 'FAILED CRITERIA';
      addLog(`Evaluation Complete. Verdict: ${verdictStr}`);
      addLog(`Metrics: Throughput=${res.mean_fps.toFixed(1)} FPS, Centroid RMSE=${res.mean_rmse !== null ? `${res.mean_rmse.toFixed(3)} px` : 'N/A'}, Loss Rate=${res.mean_loss_rate.toFixed(1)}%`);
      addLog(`Generated Report: ${res.report_paths.markdown}`);

      onBenchmarkComplete(res);
    } catch (err: any) {
      addLog(`ERROR executing matrix: ${err.message}`);
    } finally {
      setIsRunningMatrix(false);
    }
  };

  const handleRunAI = async () => {
    if (!aiPrompt.trim()) return;
    setIsRunningAI(true);
    setAiResult(null);
    addLog(`Sending prompt to AI Scenario Interpretation Engine: "${aiPrompt}"...`);

    try {
      const outcome = await runAIScenario({
        prompt: aiPrompt,
        algorithm: selectedAlgo,
        seed: matrixSeed,
        max_frames: 50,
      });

      setAiResult(outcome);

      if (outcome.valid) {
        addLog(`AI Scenario Validated & Executed successfully. Scenario ID: ${outcome.scenario_id}`);
        if (outcome.evaluation) {
          addLog(`Result: ${outcome.evaluation.passed_sih_spec ? 'PASS' : 'FAIL'} | FPS: ${outcome.evaluation.algorithm_fps?.toFixed(1)} | Loss: ${outcome.evaluation.target_loss_rate?.toFixed(1)}%`);
        }
      } else {
        addLog(`AI Scenario Validation REJECTED by physical boundary gatekeeper:`);
        outcome.validation_errors.forEach((err) => addLog(`  - ${err}`));
      }
    } catch (err: any) {
      addLog(`ERROR generating AI scenario: ${err.message}`);
    } finally {
      setIsRunningAI(false);
    }
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '16px',
      height: '100%',
      padding: '0 16px 16px 0',
      overflow: 'hidden'
    }}>
      {/* Left Column: Benchmark Matrix & AI Studio */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', overflowY: 'auto' }}>
        {/* 1. Standard Benchmark Matrix (BM1) */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 600, color: '#38bdf8' }}>
              <Award className="w-4 h-4" />
              <span>1. Standard Benchmark Matrix Execution</span>
            </div>
            <span className="badge badge-cyan">BM1 Matrix</span>
          </div>

          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '1.4' }}>
            Executes standardized batch benchmark scenarios against the Unit Under Test to measure Centroid RMSE, Processing Throughput (FPS), and Target Loss Rate against official SIH 26169 compliance thresholds.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
            <div>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Evaluation Matrix Subset</label>
              <select
                value={subset}
                onChange={(e) => setSubset(e.target.value as any)}
                disabled={isRunningMatrix}
                style={{ width: '100%', marginTop: '3px' }}
              >
                <option value="SMOKE">SMOKE (3 Scenarios - Fast Sanity)</option>
                <option value="CORE">CORE (6 Scenarios - Primary SIH)</option>
                <option value="DISTURBANCE">DISTURBANCE (8 Scenarios - Stress)</option>
                <option value="FULL">FULL (19 Scenarios - Exhaustive)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Algorithm Under Test</label>
              <select
                value={selectedAlgo}
                onChange={(e) => setSelectedAlgo(e.target.value)}
                disabled={isRunningMatrix}
                style={{ width: '100%', marginTop: '3px' }}
              >
                {algorithms.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
            <div>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Deterministic Seed</label>
              <input
                type="number"
                value={matrixSeed}
                onChange={(e) => setMatrixSeed(Number(e.target.value))}
                disabled={isRunningMatrix}
                style={{ width: '100%', marginTop: '3px' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Frames Per Scenario</label>
              <input
                type="number"
                value={matrixFrames}
                onChange={(e) => setMatrixFrames(Number(e.target.value))}
                disabled={isRunningMatrix}
                style={{ width: '100%', marginTop: '3px' }}
              />
            </div>
          </div>

          {/* Progress Bar */}
          {isRunningMatrix && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                <span>Executing Scenarios...</span>
                <span>{matrixProgress}%</span>
              </div>
              <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{
                  width: `${matrixProgress}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #00d2ff, #10b981)',
                  transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
          )}

          <button
            onClick={handleRunMatrix}
            disabled={isRunningMatrix}
            className="btn btn-primary"
            style={{ width: '100%', padding: '10px' }}
          >
            {isRunningMatrix ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
            <span>{isRunningMatrix ? 'Executing Matrix...' : `Run ${subset} Benchmark Suite`}</span>
          </button>
        </div>

        {/* 2. AI-Assisted Generative Scenario Studio */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 600, color: '#ff9933' }}>
              <Sparkles className="w-4 h-4" />
              <span>2. AI-Assisted Generative Scenario Studio</span>
            </div>
            <span className="badge" style={{ background: 'rgba(255,153,51,0.15)', color: '#ff9933', border: '1px solid rgba(255,153,51,0.3)' }}>
              NLP Synthesizer
            </span>
          </div>

          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '10px', lineHeight: '1.4' }}>
            Enter natural language prompts describing kinematic targets and atmospheric disturbances. The NLP engine parses parameters and validates physical safety boundaries.
          </p>

          <textarea
            rows={3}
            value={aiPrompt}
            onChange={(e) => setAiPrompt(e.target.value)}
            placeholder="e.g. Fast target moving in a spiral at 85 px/s through dense haze with 4 px jitter"
            disabled={isRunningAI}
            style={{ width: '100%', marginBottom: '10px', resize: 'vertical' }}
          />

          {/* Quick Prompt Presets */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {[
              'Sinusoidal target in dense fog with 6px jitter',
              'Fast spiral motion at 90 px/s with Poisson noise',
              'Random walk in heavy rain with platform drift',
            ].map((preset, i) => (
              <button
                key={i}
                onClick={() => setAiPrompt(preset)}
                className="btn btn-secondary"
                style={{ fontSize: '10px', padding: '3px 8px' }}
              >
                + {preset}
              </button>
            ))}
          </div>

          <button
            onClick={handleRunAI}
            disabled={isRunningAI || !aiPrompt.trim()}
            className="btn btn-success"
            style={{ width: '100%', padding: '10px' }}
          >
            {isRunningAI ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            <span>{isRunningAI ? 'Generating & Executing...' : 'Generate & Run AI Scenario'}</span>
          </button>

          {/* AI Outcome Spec Box */}
          {aiResult && (
            <div className="glass-panel-inset" style={{ marginTop: '12px', padding: '10px', fontSize: '11px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: aiResult.valid ? '#34d399' : '#f87171' }}>
                {aiResult.valid ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                <span>{aiResult.valid ? 'Scenario Accepted & Evaluated' : 'Validation Failed'}</span>
              </div>

              {aiResult.valid ? (
                <div style={{ marginTop: '6px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                  <div><strong>Scenario ID:</strong> {aiResult.scenario_id}</div>
                  <div><strong>Trajectory:</strong> {aiResult.spec?.motion?.motion_type} @ {aiResult.spec?.motion?.speed} px/s</div>
                  <div><strong>Condition:</strong> {aiResult.spec?.atmospheric?.condition}</div>
                </div>
              ) : (
                <div style={{ marginTop: '6px', color: '#fca5a5' }}>
                  {aiResult.validation_errors?.map((err: string, idx: number) => (
                    <div key={idx}>• {err}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right Column: Live Streaming Console Log */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        <div style={{
          padding: '10px 14px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '12px',
          background: 'rgba(10, 15, 25, 0.6)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#38bdf8', fontWeight: 600 }}>
            <Terminal className="w-4 h-4" />
            <span>Evaluation Console & Execution Logs</span>
          </div>

          <button
            onClick={() => setLogs([])}
            className="btn btn-secondary"
            style={{ fontSize: '10px', padding: '2px 8px' }}
          >
            Clear Console
          </button>
        </div>

        <div style={{
          flex: 1,
          padding: '14px',
          background: '#04060a',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '11px',
          color: '#cbd5e1',
          overflowY: 'auto',
          lineHeight: '1.6'
        }}>
          {logs.map((line, idx) => (
            <div key={idx} style={{
              color: line.includes('ERROR') ? '#f87171' :
                     line.includes('PASSED') ? '#34d399' :
                     line.includes('Initiating') || line.includes('Sending') ? '#38bdf8' : '#cbd5e1'
            }}>
              {line}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
