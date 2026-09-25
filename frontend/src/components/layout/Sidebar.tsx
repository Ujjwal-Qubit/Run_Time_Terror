import React from 'react';
import { Wrench, BarChart2, TrendingUp, Radio } from 'lucide-react';

export type ActiveTab = 'developer' | 'evaluator' | 'results';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const navItems = [
    {
      id: 'developer' as ActiveTab,
      label: 'Developer Workflow',
      subtext: 'Live Simulation & Tuning',
      icon: Wrench,
    },
    {
      id: 'evaluator' as ActiveTab,
      label: 'Evaluator Workflow',
      subtext: 'Matrix & AI Scenarios',
      icon: BarChart2,
    },
    {
      id: 'results' as ActiveTab,
      label: 'Results & Analysis',
      subtext: 'Scorecards & SIH Audit',
      icon: TrendingUp,
    },
  ];

  return (
    <aside className="glass-panel" style={{
      width: '240px',
      margin: '12px 0 12px 16px',
      padding: '16px 12px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      gap: '16px',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{
          padding: '4px 8px 12px 8px',
          fontSize: '11px',
          fontWeight: 700,
          color: 'var(--text-muted)',
          letterSpacing: '0.08em',
          borderBottom: '1px solid rgba(255,255,255,0.06)'
        }}>
          WORKFLOW NAVIGATOR
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '12px 14px',
                borderRadius: '8px',
                border: isActive ? '1px solid rgba(0, 210, 255, 0.4)' : '1px solid transparent',
                background: isActive
                  ? 'linear-gradient(135deg, rgba(0, 210, 255, 0.15) 0%, rgba(37, 99, 235, 0.1) 100%)'
                  : 'transparent',
                color: isActive ? '#f0f4fc' : 'var(--text-secondary)',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.15s ease',
                outline: 'none',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                  e.currentTarget.style.color = '#ffffff';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }
              }}
            >
              <Icon className="w-5 h-5" style={{ color: isActive ? '#00d2ff' : 'var(--text-muted)', marginTop: '2px', flexShrink: 0 }} />
              <div>
                <div style={{ fontWeight: isActive ? 600 : 500, fontSize: '13px' }}>{item.label}</div>
                <div style={{ fontSize: '11px', color: isActive ? '#93c5fd' : 'var(--text-muted)', marginTop: '2px' }}>
                  {item.subtext}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* System Status Footnote */}
      <div className="glass-panel-inset" style={{ padding: '12px', fontSize: '11px', color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '4px' }}>
          <Radio className="w-3.5 h-3.5" style={{ color: '#10b981' }} />
          <span>Platform v1.2</span>
        </div>
        <div>Ground-Truth Firewall: Active</div>
        <div style={{ marginTop: '2px' }}>Dual-Benchmark: BM1 & BM2</div>
      </div>
    </aside>
  );
};
