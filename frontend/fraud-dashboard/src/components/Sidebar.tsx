import React from 'react';
import {
  LayoutDashboard,
  Activity,
  ShieldAlert,
  GitFork,
  BarChart3,
  Server,
  FileText,
} from 'lucide-react';

export type TabType = 'overview' | 'transactions' | 'alerts' | 'graph' | 'models' | 'health';

interface SidebarProps {
  currentTab: TabType;
  onSelectTab: (tab: TabType) => void;
  alertCount: number;
  liveCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  alertCount,
  liveCount,
}) => {
  const navItems = [
    { id: 'overview' as TabType, label: 'Overview', icon: LayoutDashboard },
    {
      id: 'transactions' as TabType,
      label: 'Live Transactions',
      icon: Activity,
      badge: liveCount > 0 ? `${liveCount}` : undefined,
      badgeColor: 'bg-cyan-900 text-cyan-300 border-cyan-700',
    },
    {
      id: 'alerts' as TabType,
      label: 'Fraud Alerts',
      icon: ShieldAlert,
      badge: alertCount > 0 ? `${alertCount}` : undefined,
      badgeColor: 'bg-rose-950 text-rose-300 border-rose-800',
    },
    { id: 'graph' as TabType, label: 'Network Graph', icon: GitFork },
    { id: 'models' as TabType, label: 'Model Comparison', icon: BarChart3 },
    { id: 'health' as TabType, label: 'System Health', icon: Server },
  ];

  return (
    <aside className="w-64 bg-[#0E1524] border-r border-[#1E293B] flex flex-col justify-between shrink-0 select-none">
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Navigation
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-gradient-to-r from-cyan-900/40 to-blue-900/30 text-cyan-300 border border-cyan-800/60 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#151D2E]'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded-full border ${item.badgeColor}`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="p-4 border-t border-[#1E293B] text-xs text-slate-400 space-y-2">
        <div className="flex items-center justify-between">
          <span>Engine Pipeline</span>
          <span className="text-cyan-400 font-mono">KRaft+Flink</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Graph Engine</span>
          <span className="text-emerald-400 font-mono">Neo4j Bolt</span>
        </div>
        <div className="flex items-center justify-between">
          <span>ML Architecture</span>
          <span className="text-indigo-400 font-mono">C2GAT-PyTorch</span>
        </div>
      </div>
    </aside>
  );
};
