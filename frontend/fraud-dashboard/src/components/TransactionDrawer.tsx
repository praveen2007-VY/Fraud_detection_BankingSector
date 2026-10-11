import React, { useState, useEffect } from 'react';
import {
  X,
  ShieldAlert,
  GitFork,
  ExternalLink,
  Layers,
  Cpu,
  Clock,
  User,
  Smartphone,
  Globe,
  Store,
  CheckCircle2,
} from 'lucide-react';
import { TransactionDetailResponse } from '../types';
import { api } from '../api';

interface TransactionDrawerProps {
  transactionId: string | null;
  onClose: () => void;
  onExploreGraph: (accountId: string) => void;
}

export const TransactionDrawer: React.FC<TransactionDrawerProps> = ({
  transactionId,
  onClose,
  onExploreGraph,
}) => {
  const [detail, setDetail] = useState<TransactionDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!transactionId) {
      setDetail(null);
      return;
    }

    setLoading(true);
    setError(null);
    api.getTransactionDetail(transactionId)
      .then(setDetail)
      .catch((err) => setError(err.message || 'Failed to load transaction audit.'))
      .finally(() => setLoading(false));
  }, [transactionId]);

  if (!transactionId) return null;

  const tx = detail?.transaction;
  const gf = detail?.graph_features;
  const exp = detail?.explainability;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Container */}
      <div className="relative w-full max-w-xl bg-[#0E1524] border-l border-[#1E293B] shadow-2xl h-full flex flex-col z-10 animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="h-16 px-6 border-b border-[#1E293B] flex items-center justify-between bg-[#11192E]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-950 text-cyan-400 border border-cyan-800">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white font-mono">{transactionId}</h3>
                {tx && (
                  <span className={`px-2 py-0.2 rounded text-[11px] font-semibold badge-${tx.risk_level}`}>
                    {tx.risk_level.toUpperCase()}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400">Transaction Investigation & Attribution</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-[#1E293B]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-64 text-slate-400">
              <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs mt-2">Loading entity topology...</span>
            </div>
          ) : error ? (
            <div className="card p-4 text-xs text-rose-400 bg-rose-950/20 border-rose-900">
              {error}
            </div>
          ) : tx && gf && exp ? (
            <>
              {/* Score Badges Summary */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-[#151D2E] border border-[#232F46]">
                  <span className="text-[11px] text-slate-400 block font-medium">Approach B Risk</span>
                  <div className="text-xl font-bold font-mono text-cyan-400 mt-1">
                    {tx.approach_b_score !== null && tx.approach_b_score !== undefined
                      ? `${tx.approach_b_score.toFixed(0)} / 100`
                      : 'Pending'}
                  </div>
                  <span className="text-[10px] text-slate-400">Rule point engine</span>
                </div>

                <div className="p-3 rounded-lg bg-[#151D2E] border border-[#232F46]">
                  <span className="text-[11px] text-slate-400 block font-medium">Approach A Score</span>
                  <div className="text-xl font-bold font-mono text-white mt-1">
                    {tx.approach_a_score !== null && tx.approach_a_score !== undefined
                      ? tx.approach_a_score.toFixed(1)
                      : 'Pending'}
                  </div>
                  <span className="text-[10px] text-slate-400">Normalized composite</span>
                </div>

                <div className="p-3 rounded-lg bg-[#151D2E] border border-[#232F46]">
                  <span className="text-[11px] text-slate-400 block font-medium">C2GAT Anomaly</span>
                  <div className="text-xl font-bold font-mono text-indigo-400 mt-1">
                    {tx.anomaly_score !== null && tx.anomaly_score !== undefined
                      ? `${(tx.anomaly_score * 100).toFixed(1)}%`
                      : 'N/A'}
                  </div>
                  <span className="text-[10px] text-slate-400">Reconstruction error</span>
                </div>
              </div>

              {/* Transaction Primary Details */}
              <div className="card p-4 space-y-3">
                <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Transaction Metadata
                </h4>
                <div className="grid grid-cols-2 gap-y-2.5 text-xs">
                  <div>
                    <span className="text-slate-400">Amount:</span>
                    <div className="font-mono font-bold text-white text-sm mt-0.5">
                      ${tx.transaction_amount.toFixed(2)} USD
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-400">Date & Time:</span>
                    <div className="font-mono text-slate-200 mt-0.5">{tx.transaction_date}</div>
                  </div>
                  <div>
                    <span className="text-slate-400">Account ID:</span>
                    <div className="font-mono text-cyan-400 font-semibold mt-0.5">{tx.account_id}</div>
                  </div>
                  <div>
                    <span className="text-slate-400">Channel / Type:</span>
                    <div className="text-slate-200 mt-0.5">{tx.channel || 'Online'} • {tx.transaction_type || 'Debit'}</div>
                  </div>
                  <div>
                    <span className="text-slate-400">City / Location:</span>
                    <div className="text-slate-200 mt-0.5">{tx.location || 'Unknown'}</div>
                  </div>
                  <div>
                    <span className="text-slate-400">Merchant Recipient:</span>
                    <div className="font-mono text-purple-400 font-semibold mt-0.5">{tx.merchant_id || 'N/A'}</div>
                  </div>
                </div>
              </div>

              {/* Graph Topological Features */}
              <div className="card p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <GitFork className="w-3.5 h-3.5 text-cyan-400" />
                    Graph Topology Features (Neo4j)
                  </h4>
                  <button
                    onClick={() => onExploreGraph(tx.account_id)}
                    className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
                  >
                    View in Graph <ExternalLink className="w-3 h-3" />
                  </button>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between p-2 rounded bg-[#0E1524] border border-[#1E293B]">
                    <div className="flex items-center gap-2 text-slate-300">
                      <Smartphone className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Shared Device Accounts:</span>
                    </div>
                    <span className="font-mono font-bold text-white">
                      {gf.shared_device_accounts} accounts
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded bg-[#0E1524] border border-[#1E293B]">
                    <div className="flex items-center gap-2 text-slate-300">
                      <Globe className="w-3.5 h-3.5 text-amber-400" />
                      <span>Shared IP Accounts:</span>
                    </div>
                    <span className="font-mono font-bold text-white">
                      {gf.shared_ip_accounts} accounts
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded bg-[#0E1524] border border-[#1E293B]">
                    <div className="flex items-center gap-2 text-slate-300">
                      <Store className="w-3.5 h-3.5 text-purple-400" />
                      <span>Merchant Cluster Accounts:</span>
                    </div>
                    <span className="font-mono font-bold text-white">
                      {gf.merchant_cluster_accounts} accounts
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded bg-[#0E1524] border border-[#1E293B]">
                    <div className="flex items-center gap-2 text-slate-300">
                      <Clock className="w-3.5 h-3.5 text-rose-400" />
                      <span>Velocity Count (24h burst):</span>
                    </div>
                    <span className="font-mono font-bold text-white">
                      {gf.rapid_velocity_count_24h} other tx
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded bg-[#0E1524] border border-[#1E293B]">
                    <div className="flex items-center gap-2 text-slate-300">
                      <Layers className="w-3.5 h-3.5 text-blue-400" />
                      <span>Account Network Sprawl:</span>
                    </div>
                    <span className="font-mono font-bold text-white">
                      degree {gf.account_network_sprawl_degree}
                    </span>
                  </div>
                </div>
              </div>

              {/* Explainable Attribution Reasons */}
              <div className="card p-4 space-y-2">
                <h4 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                  Attribution & Explainable Triggers
                </h4>
                <div className="space-y-1.5">
                  {exp.risk_reasons.length > 0 ? (
                    exp.risk_reasons.map((reason, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-rose-950/30 border border-rose-900/50 text-xs text-rose-200 flex items-start gap-2"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0" />
                        <span>{reason}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400">Baseline transaction activity.</div>
                  )}
                </div>
              </div>

              {/* ML Embedding Metrics */}
              {exp.anomaly_score !== null && exp.anomaly_score !== undefined && (
                <div className="card p-4 space-y-2">
                  <h4 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                    C2GAT ML Tensor Embeddings
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 rounded bg-[#0E1524] border border-[#1E293B]">
                      <span className="text-[11px] text-slate-400">Raw Anomaly Score:</span>
                      <div className="font-mono font-semibold text-indigo-300 mt-0.5">
                        {exp.anomaly_score_raw?.toFixed(6) ?? 'N/A'}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-[#0E1524] border border-[#1E293B]">
                      <span className="text-[11px] text-slate-400">Embedding Norm:</span>
                      <div className="font-mono font-semibold text-purple-300 mt-0.5">
                        {exp.c2gat_embedding_norm?.toFixed(6) ?? 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#1E293B] bg-[#11192E] flex items-center justify-between">
          <button onClick={onClose} className="btn btn-secondary text-xs">
            Close Panel
          </button>
          {tx && (
            <button
              onClick={() => onExploreGraph(tx.account_id)}
              className="btn btn-primary text-xs"
            >
              Explore {tx.account_id} Subgraph
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
