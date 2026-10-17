import React, { useState } from 'react';
import { ShieldAlert, AlertCircle, Eye, Filter, CheckCircle2 } from 'lucide-react';
import { AlertItem } from '../types';

interface FraudAlertsProps {
  alerts: AlertItem[];
  onSelectTransaction: (txId: string) => void;
}

export const FraudAlerts: React.FC<FraudAlertsProps> = ({
  alerts,
  onSelectTransaction,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterSource, setFilterSource] = useState<string>('all');

  const filteredAlerts = alerts.filter((alt) => {
    if (filterSeverity !== 'all' && alt.severity !== filterSeverity) return false;
    if (filterSource !== 'all' && alt.detection_source !== filterSource) return false;
    return true;
  });

  const criticalCount = alerts.filter((a) => a.severity === 'critical').length;
  const highCount = alerts.filter((a) => a.severity === 'high').length;
  const mediumCount = alerts.filter((a) => a.severity === 'medium').length;

  return (
    <div className="space-y-5">
      {/* Header and Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div
          onClick={() => setFilterSeverity('all')}
          className={`card p-5 cursor-pointer transition-all ${
            filterSeverity === 'all' ? 'border-[#05C168] bg-emerald-50/40 ring-2 ring-[#05C168]/20' : 'bg-white'
          }`}
        >
          <div className="text-xs text-slate-400 font-semibold">Total Alerts</div>
          <div className="text-2xl font-extrabold text-slate-800 font-mono mt-1">{alerts.length}</div>
          <div className="text-[11px] text-slate-400 font-medium mt-1">Active detections</div>
        </div>

        <div
          onClick={() => setFilterSeverity('critical')}
          className={`card p-5 cursor-pointer transition-all ${
            filterSeverity === 'critical' ? 'border-rose-400 bg-rose-50/50 ring-2 ring-rose-400/20' : 'bg-white'
          }`}
        >
          <div className="text-xs text-rose-600 font-bold flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4" />
            Critical Severity
          </div>
          <div className="text-2xl font-extrabold text-rose-600 font-mono mt-1">{criticalCount}</div>
          <div className="text-[11px] text-slate-400 font-medium mt-1">Score ≥ 70 / multi-signal</div>
        </div>

        <div
          onClick={() => setFilterSeverity('high')}
          className={`card p-5 cursor-pointer transition-all ${
            filterSeverity === 'high' ? 'border-orange-400 bg-orange-50/50 ring-2 ring-orange-400/20' : 'bg-white'
          }`}
        >
          <div className="text-xs text-orange-600 font-bold flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4" />
            High Severity
          </div>
          <div className="text-2xl font-extrabold text-orange-600 font-mono mt-1">{highCount}</div>
          <div className="text-[11px] text-slate-400 font-medium mt-1">Score [50, 70)</div>
        </div>

        <div
          onClick={() => setFilterSeverity('medium')}
          className={`card p-5 cursor-pointer transition-all ${
            filterSeverity === 'medium' ? 'border-sky-400 bg-sky-50/50 ring-2 ring-sky-400/20' : 'bg-white'
          }`}
        >
          <div className="text-xs text-sky-600 font-bold">Medium Tier</div>
          <div className="text-2xl font-extrabold text-sky-600 font-mono mt-1">{mediumCount}</div>
          <div className="text-[11px] text-slate-400 font-medium mt-1">Score [30, 50)</div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="card p-5 bg-white flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Filter className="w-4 h-4 text-[#05C168]" />
          <h3 className="text-sm font-extrabold text-slate-800">Threat Detection Queue</h3>
          <span className="text-xs text-slate-400 font-mono font-bold">({filteredAlerts.length} shown)</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 font-semibold">Detection Source:</span>
            <select
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="text-xs py-1.5 px-3 rounded-xl border-slate-200"
            >
              <option value="all">All Sources</option>
              <option value="both">Both (Rules + ML)</option>
              <option value="graph_rules">Graph Rules Only</option>
              <option value="ml_anomaly">ML Anomaly Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Alerts Table Card */}
      <div className="card bg-white overflow-hidden">
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Alert ID</th>
                <th>TxID</th>
                <th>Account</th>
                <th>Amount</th>
                <th>Timestamp</th>
                <th>Severity</th>
                <th>Detection Source</th>
                <th>Risk Reasons & Attribution Triggers</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-16 text-slate-400 text-xs font-semibold">
                    No alerts match the chosen severity or source criteria.
                  </td>
                </tr>
              ) : (
                filteredAlerts.map((alt) => (
                  <tr key={alt.alert_id}>
                    <td className="font-mono text-xs text-slate-400 font-semibold">{alt.alert_id}</td>
                    <td className="font-mono text-xs font-bold text-slate-800 whitespace-nowrap">
                      {alt.transaction_id}
                    </td>
                    <td className="font-mono text-xs text-slate-600 font-medium">{alt.account_id}</td>
                    <td className="font-mono text-xs font-extrabold text-slate-800 whitespace-nowrap">
                      ${alt.transaction_amount.toFixed(2)}
                    </td>
                    <td className="text-xs text-slate-400 whitespace-nowrap">{alt.transaction_date}</td>
                    <td>
                      <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold badge-${alt.severity}`}>
                        {alt.severity.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                          alt.detection_source === 'both'
                            ? 'bg-purple-50 text-purple-600 border-purple-200'
                            : alt.detection_source === 'ml_anomaly'
                            ? 'bg-blue-50 text-blue-600 border-blue-200'
                            : 'bg-slate-100 text-slate-700 border-slate-200'
                        }`}
                      >
                        {alt.detection_source === 'both'
                          ? 'Dual: Rule + ML'
                          : alt.detection_source === 'ml_anomaly'
                          ? 'ML Anomaly'
                          : 'Graph Rule'}
                      </span>
                    </td>
                    <td className="text-xs text-slate-600 max-w-md">
                      <div className="flex flex-wrap gap-1">
                        {alt.reasons.map((r, i) => (
                          <span
                            key={i}
                            className="inline-block px-2 py-0.5 rounded-lg bg-slate-50 text-[11px] text-slate-600 border border-slate-200 font-medium"
                          >
                            {r}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <button
                        onClick={() => onSelectTransaction(alt.transaction_id)}
                        className="btn btn-secondary text-xs px-3 py-1.5 rounded-xl text-slate-700 hover:text-[#05C168] whitespace-nowrap"
                      >
                        <Eye className="w-3.5 h-3.5 text-slate-500" />
                        Investigate
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
