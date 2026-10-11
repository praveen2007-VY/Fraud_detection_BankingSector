import React from 'react';
import {
  TrendingUp,
  AlertTriangle,
  Users,
  Layers,
  ShieldAlert,
  ArrowRight,
  Database,
  Radio,
  Server,
  Cpu,
} from 'lucide-react';
import { StatsResponse, RiskDistributionResponse, AlertItem, HealthResponse, TransactionSummary } from '../types';

interface OverviewProps {
  stats: StatsResponse | null;
  distribution: RiskDistributionResponse | null;
  recentAlerts: AlertItem[];
  health: HealthResponse | null;
  onSelectTransaction: (txId: string) => void;
  onNavigateToTab: (tab: any) => void;
}

export const Overview: React.FC<OverviewProps> = ({
  stats,
  distribution,
  recentAlerts,
  health,
  onSelectTransaction,
  onNavigateToTab,
}) => {
  if (!stats) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Loading telemetry metrics...</p>
        </div>
      </div>
    );
  }

  const kpis = [
    {
      label: 'Total Processed',
      value: stats.total_transactions.toLocaleString(),
      subtext: `${stats.unique_accounts} unique accounts`,
      icon: Layers,
      color: 'from-blue-600 to-cyan-500',
    },
    {
      label: 'Transaction Volume',
      value: `$${stats.total_volume.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      subtext: 'Currency: USD',
      icon: TrendingUp,
      color: 'from-cyan-600 to-teal-500',
    },
    {
      label: 'Flagged Transactions',
      value: `${stats.flagged_count.toLocaleString()}`,
      subtext: `${stats.flagged_percentage}% of total activity`,
      icon: AlertTriangle,
      color: 'from-amber-500 to-rose-500',
    },
    {
      label: 'High-Risk Accounts',
      value: `${stats.high_risk_accounts.toLocaleString()}`,
      subtext: 'Accounts with score ≥ 50',
      icon: Users,
      color: 'from-rose-600 to-red-600',
    },
  ];

  const totalDist = distribution?.total || stats.total_transactions || 1;
  const appB = distribution?.approach_b || {
    low: stats.low_risk_count,
    medium: stats.medium_risk_count,
    high: stats.high_risk_count,
    critical: stats.critical_risk_count,
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="card p-5 bg-gradient-to-r from-[#11192E] via-[#151D2E] to-[#111827] border-cyan-900/40 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <h2 className="text-lg font-bold text-white tracking-tight">Real-Time Operational Sentinel</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Continuous multi-model ingestion: Graph topology (Phase 5) + Temporal attention autoencoder (Phase 6 C2GAT).
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigateToTab('transactions')}
            className="btn btn-primary text-xs"
          >
            Live Monitor
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onNavigateToTab('alerts')}
            className="btn btn-secondary text-xs"
          >
            Review Alerts ({recentAlerts.length})
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div key={idx} className="card p-4 card-hover">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">{kpi.label}</span>
                <div className={`p-2 rounded-lg bg-gradient-to-br ${kpi.color} shadow-sm`}>
                  <Icon className="w-4 h-4 text-white" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-xl font-bold font-mono tracking-tight text-white">{kpi.value}</div>
                <div className="text-[11px] text-slate-400 mt-1">{kpi.subtext}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Analytics Row: Risk Distribution & Infrastructure Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Distribution Breakdown */}
        <div className="card p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Risk Tier Distribution</h3>
              <p className="text-xs text-slate-400">Approach B Additive Point Engine (0–100 Scale)</p>
            </div>
            <button
              onClick={() => onNavigateToTab('models')}
              className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
            >
              Compare Models <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-4">
            {/* Visual Bar Spectrum */}
            <div className="h-4 w-full bg-[#0E1524] rounded-full overflow-hidden flex border border-[#1E293B]">
              <div
                style={{ width: `${(appB.low / totalDist) * 100}%` }}
                className="bg-emerald-500 transition-all duration-500"
                title={`Low: ${appB.low}`}
              />
              <div
                style={{ width: `${(appB.medium / totalDist) * 100}%` }}
                className="bg-amber-500 transition-all duration-500"
                title={`Medium: ${appB.medium}`}
              />
              <div
                style={{ width: `${(appB.high / totalDist) * 100}%` }}
                className="bg-rose-500 transition-all duration-500"
                title={`High: ${appB.high}`}
              />
              <div
                style={{ width: `${(appB.critical / totalDist) * 100}%` }}
                className="bg-red-600 transition-all duration-500"
                title={`Critical: ${appB.critical}`}
              />
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg bg-[#0E1524] border border-[#1E293B]">
                <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  Low Risk [0–30)
                </div>
                <div className="text-lg font-bold font-mono text-white mt-1">{appB.low}</div>
                <div className="text-[11px] text-slate-400">
                  {((appB.low / totalDist) * 100).toFixed(1)}% of total
                </div>
              </div>

              <div className="p-3 rounded-lg bg-[#0E1524] border border-[#1E293B]">
                <div className="flex items-center gap-1.5 text-xs text-amber-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  Medium Risk [30–50)
                </div>
                <div className="text-lg font-bold font-mono text-white mt-1">{appB.medium}</div>
                <div className="text-[11px] text-slate-400">
                  {((appB.medium / totalDist) * 100).toFixed(1)}% of total
                </div>
              </div>

              <div className="p-3 rounded-lg bg-[#0E1524] border border-[#1E293B]">
                <div className="flex items-center gap-1.5 text-xs text-rose-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-rose-400" />
                  High Risk [50–70)
                </div>
                <div className="text-lg font-bold font-mono text-white mt-1">{appB.high}</div>
                <div className="text-[11px] text-slate-400">
                  {((appB.high / totalDist) * 100).toFixed(1)}% of total
                </div>
              </div>

              <div className="p-3 rounded-lg bg-[#0E1524] border border-[#1E293B]">
                <div className="flex items-center gap-1.5 text-xs text-red-500 font-medium">
                  <span className="w-2 h-2 rounded-full bg-red-500" />
                  Critical [70–100]
                </div>
                <div className="text-lg font-bold font-mono text-white mt-1">{appB.critical}</div>
                <div className="text-[11px] text-slate-400">
                  {((appB.critical / totalDist) * 100).toFixed(1)}% of total
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Infrastructure Observability Summary */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">System Connectivity</h3>
            <button
              onClick={() => onNavigateToTab('health')}
              className="text-xs text-cyan-400 hover:text-cyan-300"
            >
              Details
            </button>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-2.5 rounded bg-[#0E1524] border border-[#1E293B]">
              <div className="flex items-center gap-2.5 text-xs">
                <Server className="w-4 h-4 text-cyan-400" />
                <span>FastAPI Backend</span>
              </div>
              <span className="text-[11px] font-mono text-emerald-400 font-semibold">ONLINE</span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded bg-[#0E1524] border border-[#1E293B]">
              <div className="flex items-center gap-2.5 text-xs">
                <Radio className="w-4 h-4 text-cyan-400" />
                <span>Apache Kafka KRaft</span>
              </div>
              <span
                className={`text-[11px] font-mono font-semibold ${
                  health?.dependencies?.kafka?.status === 'healthy' ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {health?.dependencies?.kafka?.status === 'healthy' ? 'CONNECTED' : 'OFFLINE'}
              </span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded bg-[#0E1524] border border-[#1E293B]">
              <div className="flex items-center gap-2.5 text-xs">
                <Database className="w-4 h-4 text-cyan-400" />
                <span>Neo4j Graph Database</span>
              </div>
              <span
                className={`text-[11px] font-mono font-semibold ${
                  health?.dependencies?.neo4j?.status === 'healthy' ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {health?.dependencies?.neo4j?.status === 'healthy' ? 'CONNECTED' : 'OFFLINE'}
              </span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded bg-[#0E1524] border border-[#1E293B]">
              <div className="flex items-center gap-2.5 text-xs">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <span>C2GAT ML Checkpoint</span>
              </div>
              <span
                className={`text-[11px] font-mono font-semibold ${
                  health?.dependencies?.ml_artifacts?.status === 'healthy' ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {health?.dependencies?.ml_artifacts?.status === 'healthy' ? 'READY' : 'DEGRADED'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Priority Flagged Alerts Ticker */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-500" />
            <h3 className="text-sm font-semibold text-white">Priority Flagged Suspicious Transactions</h3>
          </div>
          <button
            onClick={() => onNavigateToTab('alerts')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-medium"
          >
            View All Alerts ({recentAlerts.length})
          </button>
        </div>

        {recentAlerts.length === 0 ? (
          <div className="text-xs text-slate-400 p-4 text-center bg-[#0E1524] rounded border border-[#1E293B]">
            No unreviewed critical alerts detected.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Alert ID</th>
                  <th>Transaction</th>
                  <th>Account</th>
                  <th>Amount</th>
                  <th>Timestamp</th>
                  <th>Severity</th>
                  <th>Source</th>
                  <th>Primary Triggers</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentAlerts.slice(0, 5).map((alt) => (
                  <tr key={alt.alert_id}>
                    <td className="font-mono text-xs text-slate-300">{alt.alert_id}</td>
                    <td className="font-mono text-xs text-cyan-400 font-semibold">{alt.transaction_id}</td>
                    <td className="font-mono text-xs text-slate-300">{alt.account_id}</td>
                    <td className="font-mono text-xs text-slate-200">${alt.transaction_amount.toFixed(2)}</td>
                    <td className="text-xs text-slate-400">{alt.transaction_date}</td>
                    <td>
                      <span className={`px-2 py-0.5 rounded text-[11px] badge-${alt.severity}`}>
                        {alt.severity.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {alt.detection_source}
                      </span>
                    </td>
                    <td className="text-xs text-slate-400 max-w-xs truncate" title={alt.reasons.join(', ')}>
                      {alt.reasons.join('; ')}
                    </td>
                    <td>
                      <button
                        onClick={() => onSelectTransaction(alt.transaction_id)}
                        className="btn btn-secondary text-xs px-2.5 py-1"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
