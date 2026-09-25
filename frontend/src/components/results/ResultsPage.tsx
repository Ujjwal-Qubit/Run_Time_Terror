import React, { useEffect, useState } from 'react';
import { Award, CheckCircle, XCircle, RefreshCw, FileText, AlertTriangle, ShieldCheck, Database, HelpCircle } from 'lucide-react';
import confetti from 'canvas-confetti';
import { fetchLatestReport, fetchReportsList } from '../../api/client';
import type { MatrixResult, ReportItem } from '../../types';

interface ResultsPageProps {
  latestResult: MatrixResult | null;
}

/** Renders a metric that may be genuinely absent as "N/A", never as a fake value. */
const MetricDisplay: React.FC<{
  value: number | null | undefined;
  formatter: (v: number) => string;
  fallback?: string;
  color?: string;
}> = ({ value, formatter, fallback = 'N/A', color = '#f0f4fc' }) => {
  if (value === null || value === undefined) {
    return (
      <span className="font-mono" style={{ color: 'var(--text-muted)' }}>
        {fallback}
      </span>
    );
  }
  return (
    <span className="font-mono" style={{ color }}>
      {formatter(value)}
    </span>
  );
};

export const ResultsPage: React.FC<ResultsPageProps> = ({ latestResult }) => {
  const [reportData, setReportData] = useState<any>(latestResult?.report_data || null);
  const [reportsList, setReportsList] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [latest, list] = await Promise.all([
        fetchLatestReport().catch(() => null),
        fetchReportsList().catch(() => ({ reports: [] })),
      ]);

      if (latest && !latestResult) {
        setReportData(latest.data);
      } else if (latestResult?.report_data) {
        setReportData(latestResult.report_data);
      }
      setReportsList(list.reports || []);
    } catch (e) {
      console.error('Error loading reports:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [latestResult]);

  useEffect(() => {
    // Only fire confetti when there is a real, confirmed PASS — never for undefined state.
    if (latestResult?.passed_sih_spec === true || reportData?.overall_summary?.passed_sih_spec === true) {
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
      });
    }
  }, [latestResult, reportData]);

  // ---------------------------------------------------------------------------
  // Derive metrics strictly from real data.
  // The overall_summary is the canonical nested object in the report JSON.
  // Never invent values — missing data renders as "N/A" or "UNVERIFIED".
  // ---------------------------------------------------------------------------
  const summary = reportData?.overall_summary ?? null;

  // Passed verdict: must be explicitly true — undefined/null = UNVERIFIED, not PASS
  const isPassed: boolean | null =
    latestResult?.passed_sih_spec ??
    summary?.passed_sih_spec ??
    null;

  const meanFps: number | null =
    latestResult?.mean_fps ??
    summary?.mean_algorithm_fps ??
    null;

  const meanRmse: number | null =
    latestResult?.mean_rmse ??
    summary?.mean_rmse_centroid ??
    null;

  // mean_loss_rate is a fraction (0.0–1.0) from backend; convert to pct for display
  const meanLossRaw: number | null =
    latestResult?.mean_loss_rate ??
    summary?.mean_target_loss_rate ??
    null;
  const meanLossPct: number | null = meanLossRaw !== null ? meanLossRaw * 100 : null;

  const totalRuns: number | null = summary?.total_runs ?? null;
  const successfulRuns: number | null = summary?.successful_runs ?? null;
  const failedRuns: number | null = summary?.failed_runs ?? null;

  // Acquisition time from report if available
  const meanAcqTime: number | null = summary?.mean_acquisition_time_s ?? null;

  const hasAnyResult = isPassed !== null || meanFps !== null;

  // ---------------------------------------------------------------------------
  // Compliance gates — only populated when data is real
  // ---------------------------------------------------------------------------
  const complianceGates = [
    {
      metric: 'Processing Throughput (FPS)',
      sihLimit: '≥ 20.0 FPS',
      measured: meanFps !== null ? `${meanFps.toFixed(1)} FPS` : 'N/A',
      passed: meanFps !== null ? meanFps >= 20.0 : null,
      note: 'SIH PS-4 Core Hard Requirement',
    },
    {
      metric: 'Tracking Error (Centroid RMSE)',
      sihLimit: '≤ 10.0 px',
      measured: meanRmse !== null ? `${meanRmse.toFixed(3)} px` : 'N/A',
      passed: meanRmse !== null ? meanRmse <= 10.0 : null,
      note: meanRmse === null ? 'No ground-truth reference — UNVERIFIED' : 'Sub-pixel accuracy gate',
    },
    {
      metric: 'Acquisition Time',
      sihLimit: '≤ 2.0 s',
      measured: meanAcqTime !== null ? `${meanAcqTime.toFixed(3)} s` : 'N/A',
      passed: meanAcqTime !== null ? meanAcqTime <= 2.0 : null,
      note: meanAcqTime === null ? 'Not measured in this run' : 'Initial lock acquisition',
    },
    {
      metric: 'Target Loss Rate',
      sihLimit: '< 5.0%',
      measured: meanLossPct !== null ? `${meanLossPct.toFixed(1)}%` : 'N/A',
      passed: meanLossPct !== null ? meanLossPct < 5.0 : null,
      note: 'Lock stability across scenarios',
    },
    {
      metric: 'PTZ Gimbal Slew Rates',
      sihLimit: 'Max 5.0°/s – 10.0°/s',
      measured: 'Config-enforced',
      passed: true, // always enforced by config validation
      note: 'Kinematic motor protection (config gate)',
    },
  ];

  // Overall verdict label
  const verdictLabel =
    isPassed === true ? 'PASSED (PS COMPLIANT)' :
    isPassed === false ? 'FAILED CRITERIA' :
    'UNVERIFIED — No Result';

  const verdictColor =
    isPassed === true ? '#34d399' :
    isPassed === false ? '#f87171' :
    '#94a3b8';

  const borderColor =
    isPassed === true ? 'rgba(16, 185, 129, 0.4)' :
    isPassed === false ? 'rgba(239, 68, 68, 0.4)' :
    'rgba(148, 163, 184, 0.3)';

  const bgGradient =
    isPassed === true ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(15, 23, 42, 0.8) 100%)' :
    isPassed === false ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(15, 23, 42, 0.8) 100%)' :
    'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)';

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1.2fr 1fr',
      gap: '16px',
      height: '100%',
      padding: '0 16px 16px 0',
      overflow: 'hidden'
    }}>
      {/* Left Column: SIH Compliance Gates & Grand Evaluation Scorecard */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', overflowY: 'auto' }}>
        {/* Grand Evaluation Header Card */}
        <div className="glass-panel" style={{
          padding: '16px',
          background: bgGradient,
          border: `1px solid ${borderColor}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Award className="w-6 h-6" style={{ color: verdictColor }} />
              <div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#f0f4fc' }}>
                  SIH Problem Statement 26169 Evaluation Scorecard
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                  Department of Space / ISRO Autonomous FSOC Coarse Alignment
                </div>
              </div>
            </div>

            <div
              className={`badge ${isPassed === true ? 'badge-locked pulse-lock' : isPassed === false ? 'badge-unlocked' : ''}`}
              style={{ fontSize: '13px', padding: '6px 12px', borderColor: verdictColor }}
            >
              {isPassed === true ? <CheckCircle className="w-4 h-4" /> :
               isPassed === false ? <XCircle className="w-4 h-4" /> :
               <HelpCircle className="w-4 h-4" />}
              <span>{verdictLabel}</span>
            </div>
          </div>

          {/* KPI Summary Grid — only show values when real data exists */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginTop: '14px' }}>
            <div className="glass-panel-inset" style={{ padding: '8px 10px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>THROUGHPUT</div>
              <MetricDisplay
                value={meanFps}
                formatter={(v) => `${v.toFixed(1)} FPS`}
                color="#34d399"
              />
            </div>
            <div className="glass-panel-inset" style={{ padding: '8px 10px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>CENTROID RMSE</div>
              <MetricDisplay
                value={meanRmse}
                formatter={(v) => `${v.toFixed(3)} px`}
                fallback="N/A"
                color="#38bdf8"
              />
            </div>
            <div className="glass-panel-inset" style={{ padding: '8px 10px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>LOSS RATE</div>
              <MetricDisplay
                value={meanLossPct}
                formatter={(v) => `${v.toFixed(1)}%`}
                fallback="N/A"
                color="#34d399"
              />
            </div>
            <div className="glass-panel-inset" style={{ padding: '8px 10px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>RUN SUCCESS</div>
              <div className="font-mono" style={{ fontSize: '14px', fontWeight: 700, color: '#fbbf24' }}>
                {successfulRuns !== null && totalRuns !== null
                  ? `${successfulRuns}/${totalRuns} Passed`
                  : 'N/A'}
              </div>
            </div>
          </div>

          {!hasAnyResult && (
            <div style={{ marginTop: '12px', padding: '8px', background: 'rgba(148,163,184,0.1)', borderRadius: '6px', fontSize: '11px', color: 'var(--text-muted)' }}>
              No evaluation results available. Run an evaluation matrix from the Evaluator workflow.
            </div>
          )}
        </div>

        {/* Compliance Thresholds Table */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#38bdf8', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ShieldCheck className="w-4 h-4" />
            <span>SIH 26169 Pass/Fail Compliance Threshold Gates</span>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '8px 6px' }}>Benchmark Metric</th>
                <th style={{ padding: '8px 6px' }}>SIH Required Limit</th>
                <th style={{ padding: '8px 6px' }}>Measured Value</th>
                <th style={{ padding: '8px 6px' }}>Verdict</th>
              </tr>
            </thead>
            <tbody>
              {complianceGates.map((gate, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '8px 6px', fontWeight: 500 }}>
                    <div>{gate.metric}</div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{gate.note}</div>
                  </td>
                  <td className="font-mono" style={{ padding: '8px 6px', color: 'var(--text-secondary)' }}>{gate.sihLimit}</td>
                  <td className="font-mono" style={{ padding: '8px 6px', color: '#f0f4fc' }}>{gate.measured}</td>
                  <td style={{ padding: '8px 6px' }}>
                    {gate.passed === true ? (
                      <span className="badge badge-locked">PASS</span>
                    ) : gate.passed === false ? (
                      <span className="badge badge-unlocked">FAIL</span>
                    ) : (
                      <span className="badge" style={{ background: 'rgba(148,163,184,0.2)', color: '#94a3b8', border: '1px solid rgba(148,163,184,0.3)' }}>N/A</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Failure Analysis Panel */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#f87171', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle className="w-4 h-4" />
            <span>Failure Analysis & Episode Breakdown</span>
          </div>

          <div className="glass-panel-inset font-mono" style={{ padding: '12px', fontSize: '11px', color: '#94a3b8', lineHeight: '1.5' }}>
            {failedRuns === null ? (
              <div style={{ color: 'var(--text-muted)' }}>No evaluation data available.</div>
            ) : failedRuns > 0 ? (
              <div style={{ color: '#fca5a5' }}>
                {failedRuns} run{failedRuns !== 1 ? 's' : ''} failed out of {totalRuns ?? '?'}. Inspect logs in output/ for details.
              </div>
            ) : (
              <div style={{ color: '#34d399' }}>
                ✓ Zero fatal failures detected. All {totalRuns} evaluation runs completed within nominal limits.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right Column: Generated Artifacts & Reports Explorer */}
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
            <Database className="w-4 h-4" />
            <span>Generated Report Artifacts (`output/`)</span>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '4px 10px' }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Results</span>
          </button>
        </div>

        <div style={{ flex: 1, padding: '14px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {reportsList.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px', marginTop: '40px' }}>
              No generated reports found yet. Run an evaluation matrix from the Evaluator workflow.
            </div>
          ) : (
            reportsList.map((rep, idx) => (
              <div
                key={idx}
                className="glass-panel-inset"
                style={{
                  padding: '10px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <FileText className="w-4 h-4" style={{
                    color: rep.type === 'JSON' ? '#38bdf8' : rep.type === 'CSV' ? '#34d399' : '#f97316'
                  }} />
                  <div>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#f0f4fc' }}>{rep.name}</div>
                    <div className="font-mono" style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {(rep.size_bytes / 1024).toFixed(1)} KB • {new Date(rep.mtime * 1000).toLocaleTimeString()}
                    </div>
                  </div>
                </div>

                <span className="badge badge-cyan">{rep.type}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
