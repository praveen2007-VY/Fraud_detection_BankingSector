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
    <div className="space-y-4">
      {/* Header and Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div
          onClick={() => setFilterSeverity('all')}
          className={`card p-4 cursor-pointer transition-all ${
            filterSeverity === 'all' ? 'border-cyan-500 bg-[#162238]' : ''
          }`}
        >
          <div className="text-xs text-slate-400 font-medium">Total Alerts</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">{alerts.length}</div>
          <div className="text-[11px] text-slate-400 mt-1">Active detections</div>
        </div>

        <div
          onClick={() => setFilterSeverity('critical')}
          className={`card p-4 cursor-pointer transition-all ${
            filterSeverity === 'critical' ? 'border-red-500 bg-red-950/20' : ''
          }`}
        >
          <div className="text-xs text-red-400 font-medium flex items-center gap-1">
            <ShieldAlert className="w-3.5 h-3.5" />
            Critical Severity
          </div>
          <div className="text-2xl font-bold font-mono text-red-400 mt-1">{criticalCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Score ≥ 70 / multi-signal</div>
        </div>

        <div
          onClick={() => setFilterSeverity('high')}
          className={`card p-4 cursor-pointer transition-all ${
            filterSeverity === 'high' ? 'border-rose-500 bg-rose-950/20' : ''
          }`}
        >
          <div className="text-xs text-rose-400 font-medium flex items-center gap-1">
            <AlertCircle className="w-3.5 h-3.5" />
            High Severity
          </div>
          <div className="text-2xl font-bold font-mono text-rose-400 mt-1">{highCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Score [50, 70)</div>
        </div>

        <div
          onClick={() => setFilterSeverity('medium')}
          className={`card p-4 cursor-pointer transition-all ${
            filterSeverity === 'medium' ? 'border-amber-500 bg-amber-950/20' : ''
          }`}
        >
          <div className="text-xs text-amber-400 font-medium">Medium Tier</div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">{mediumCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Score [30, 50)</div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="card p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Detection Queue</h3>
          <span className="text-xs text-slate-400 font-mono">({filteredAlerts.length} shown)</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Detection Source:</span>
            <select
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="text-xs py-1"
            >
              <option value="all">All Sources</option>
              <option value="both">Both (Rules + ML)</option>
              <option value="graph_rules">Graph Rules Only</option>
              <option value="ml_anomaly">ML Anomaly Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Alerts Table */}
      <div className="card overflow-hidden">
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
                  <td colSpan={9} className="text-center py-12 text-slate-400 text-xs">
                    No alerts match the chosen severity or source criteria.
                  </td>
                </tr>
              ) : (
                filteredAlerts.map((alt) => (
                  <tr key={alt.alert_id}>
                    <td className="font-mono text-xs text-slate-400">{alt.alert_id}</td>
                    <td className="font-mono text-xs font-semibold text-cyan-400 whitespace-nowrap">
                      {alt.transaction_id}
                    </td>
                    <td className="font-mono text-xs text-slate-300">{alt.account_id}</td>
                    <td className="font-mono text-xs text-white whitespace-nowrap">
                      ${alt.transaction_amount.toFixed(2)}
                    </td>
                    <td className="text-xs text-slate-400 whitespace-nowrap">{alt.transaction_date}</td>
                    <td>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold badge-${alt.severity}`}>
                        {alt.severity.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                          alt.detection_source === 'both'
                            ? 'bg-purple-950 text-purple-300 border-purple-800'
                            : alt.detection_source === 'ml_anomaly'
                            ? 'bg-blue-950 text-blue-300 border-blue-800'
                            : 'bg-slate-800 text-slate-300 border-slate-700'
                        }`}
                      >
                        {alt.detection_source === 'both'
                          ? 'Dual: Rule + ML'
                          : alt.detection_source === 'ml_anomaly'
                          ? 'ML Anomaly'
                          : 'Graph Rule'}
                      </span>
                    </td>
                    <td className="text-xs text-slate-300 max-w-md">
                      <div className="flex flex-wrap gap-1">
                        {alt.reasons.map((r, i) => (
                          <span
                            key={i}
                            className="inline-block px-1.5 py-0.5 rounded bg-[#0E1524] text-[11px] text-slate-300 border border-[#232F46]"
                          >
                            {r}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <button
                        onClick={() => onSelectTransaction(alt.transaction_id)}
                        className="btn btn-secondary text-xs px-2.5 py-1 whitespace-nowrap"
                      >
                        <Eye className="w-3 h-3 text-cyan-400" />
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
