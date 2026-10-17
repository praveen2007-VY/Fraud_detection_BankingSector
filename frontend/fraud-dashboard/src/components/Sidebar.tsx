import React from 'react';
import {
  LayoutDashboard,
  Activity,
  ShieldAlert,
  GitFork,
  BarChart3,
  Server,
  ShieldCheck,
  ChevronDown,
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
    { id: 'overview' as TabType, label: 'Dashboard', icon: LayoutDashboard },
    {
      id: 'transactions' as TabType,
      label: 'Transactions',
      icon: Activity,
      badge: liveCount > 0 ? `${liveCount}` : undefined,
      badgeColor: 'bg-emerald-50 text-emerald-600 border-emerald-200',
    },
    {
      id: 'alerts' as TabType,
      label: 'Fraud Alerts',
      icon: ShieldAlert,
      badge: alertCount > 0 ? `${alertCount}` : undefined,
      badgeColor: 'bg-rose-50 text-rose-600 border-rose-200',
    },
    { id: 'graph' as TabType, label: 'Graph Explorer', icon: GitFork },
    { id: 'models' as TabType, label: 'ML Models', icon: BarChart3 },
    { id: 'health' as TabType, label: 'System Health', icon: Server },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-100/90 flex flex-col justify-between shrink-0 select-none py-6 px-4 shadow-[4px_0_24px_rgba(0,0,0,0.015)] z-20">
      <div className="space-y-7">
        {/* Brand Logo matching WasteBank style */}
        <div className="flex items-center gap-3 px-3">
          <div className="h-10 w-10 rounded-2xl bg-[#05C168] flex items-center justify-center text-white shadow-lg shadow-emerald-500/20">
            <ShieldCheck className="w-6 h-6 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="text-lg font-extrabold text-slate-800 tracking-tight leading-none">
              Sentinel<span className="text-[#05C168]">Bank</span>
            </h1>
            <span className="text-[11px] text-slate-400 font-medium">Fraud Intelligence</span>
          </div>
        </div>

        {/* Navigation list */}
        <div className="space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-3 rounded-2xl text-[14px] font-semibold transition-all relative ${
                  isActive
                    ? 'bg-[#E8F8F0] text-[#05C168]'
                    : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center gap-3.5">
                  <Icon className={`w-5 h-5 ${isActive ? 'text-[#05C168] stroke-[2.2]' : 'text-slate-400 stroke-[1.8]'}`} />
                  <span>{item.label}</span>
                </div>

                <div className="flex items-center gap-2">
                  {item.badge && (
                    <span
                      className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded-full border ${item.badgeColor}`}
                    >
                      {item.badge}
                    </span>
                  )}
                  {/* Active dot indicator on the right edge (like reference image) */}
                  {isActive && (
                    <span className="w-2 h-2 rounded-full bg-[#05C168] shadow-sm" />
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* User / Workspace switcher pill at bottom (matches reference) */}
      <div className="p-3 bg-[#F8FAFC] rounded-2xl border border-slate-100 flex items-center justify-between hover:bg-slate-100/80 transition-colors cursor-pointer">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#05C168] to-teal-400 flex items-center justify-center text-white text-xs font-bold shadow-sm">
            WB
          </div>
          <div className="text-left">
            <p className="text-[10px] text-slate-400 font-medium leading-none">Welcome,</p>
            <p className="text-xs font-bold text-slate-800 mt-0.5 leading-none">SecOps Sentinel</p>
          </div>
        </div>
        <ChevronDown className="w-4 h-4 text-slate-400" />
      </div>
    </aside>
  );
};
