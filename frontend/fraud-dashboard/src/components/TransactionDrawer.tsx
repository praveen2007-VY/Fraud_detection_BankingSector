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
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Container */}
      <div className="relative w-full max-w-xl bg-white border-l border-slate-200 shadow-2xl h-full flex flex-col z-10 animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="h-18 px-6 border-b border-slate-100 flex items-center justify-between bg-white">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-2xl bg-emerald-50 text-[#05C168] flex items-center justify-center">
              <Layers className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-extrabold text-slate-800 font-mono">{transactionId}</h3>
                {tx && (
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold badge-${tx.risk_level}`}>
                    {tx.risk_level.toUpperCase()}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-medium">Transaction Investigation & Attribution</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-800 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 bg-[#F8FAFC]">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-64 text-slate-400">
              <div className="w-8 h-8 border-3 border-[#05C168] border-t-transparent rounded-full animate-spin" />
              <span className="text-xs font-semibold mt-2 text-slate-500">Loading entity topology...</span>
            </div>
          ) : error ? (
            <div className="card p-4 text-xs text-rose-600 bg-rose-50 border-rose-200 font-semibold">
              {error}
            </div>
          ) : tx && gf && exp ? (
            <>
              {/* Score Badges Summary */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-xs">
                  <span className="text-[11px] text-slate-400 block font-bold">Approach B Risk</span>
                  <div className="text-2xl font-extrabold font-mono text-[#05C168] mt-1">
                    {tx.approach_b_score !== null && tx.approach_b_score !== undefined
                      ? `${tx.approach_b_score.toFixed(0)} / 100`
                      : 'Pending'}
                  </div>
                  <span className="text-[10px] text-slate-400 font-medium">Rule point engine</span>
                </div>

                <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-xs">
                  <span className="text-[11px] text-slate-400 block font-bold">Approach A Score</span>
                  <div className="text-2xl font-extrabold font-mono text-slate-800 mt-1">
                    {tx.approach_a_score !== null && tx.approach_a_score !== undefined
                      ? tx.approach_a_score.toFixed(1)
                      : 'Pending'}
                  </div>
                  <span className="text-[10px] text-slate-400 font-medium">Normalized composite</span>
                </div>

                <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-xs">
                  <span className="text-[11px] text-slate-400 block font-bold">C2GAT Anomaly</span>
                  <div className="text-2xl font-extrabold font-mono text-indigo-600 mt-1">
                    {tx.anomaly_score !== null && tx.anomaly_score !== undefined
                      ? `${(tx.anomaly_score * 100).toFixed(1)}%`
                      : 'N/A'}
                  </div>
                  <span className="text-[10px] text-slate-400 font-medium">Reconstruction error</span>
                </div>
              </div>

              {/* Transaction Primary Details */}
              <div className="card p-5 bg-white space-y-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Transaction Metadata
                </h4>
                <div className="grid grid-cols-2 gap-y-3 text-xs">
                  <div>
                    <span className="text-slate-400 font-medium">Amount:</span>
                    <div className="font-mono font-extrabold text-slate-800 text-base mt-0.5">
                      ${tx.transaction_amount.toFixed(2)} USD
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Date & Time:</span>
                    <div className="font-mono text-slate-700 font-semibold mt-0.5">{tx.transaction_date}</div>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Account ID:</span>
                    <div className="font-mono text-slate-800 font-bold mt-0.5">{tx.account_id}</div>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Channel / Type:</span>
                    <div className="text-slate-700 font-semibold mt-0.5">{tx.channel || 'Online'} • {tx.transaction_type || 'Debit'}</div>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">City / Location:</span>
                    <div className="text-slate-700 font-semibold mt-0.5">{tx.location || 'Unknown'}</div>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Merchant Recipient:</span>
                    <div className="font-mono text-purple-600 font-bold mt-0.5">{tx.merchant_id || 'N/A'}</div>
                  </div>
                </div>
              </div>

              {/* Graph Topological Features */}
              <div className="card p-5 bg-white space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <GitFork className="w-3.5 h-3.5 text-[#05C168]" />
                    Graph Topology Features (Neo4j)
                  </h4>
                  <button
                    onClick={() => onExploreGraph(tx.account_id)}
                    className="text-xs text-[#05C168] hover:underline flex items-center gap-1 font-bold"
                  >
                    View in Graph <ExternalLink className="w-3 h-3" />
                  </button>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="flex items-center gap-2 text-slate-600 font-medium">
                      <Smartphone className="w-4 h-4 text-emerald-500" />
                      <span>Shared Device Accounts:</span>
                    </div>
                    <span className="font-mono font-bold text-slate-800">
                      {gf.shared_device_accounts} accounts
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="flex items-center gap-2 text-slate-600 font-medium">
                      <Globe className="w-4 h-4 text-amber-500" />
                      <span>Shared IP Accounts:</span>
                    </div>
                    <span className="font-mono font-bold text-slate-800">
                      {gf.shared_ip_accounts} accounts
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="flex items-center gap-2 text-slate-600 font-medium">
                      <Store className="w-4 h-4 text-purple-500" />
                      <span>Merchant Cluster Accounts:</span>
                    </div>
                    <span className="font-mono font-bold text-slate-800">
                      {gf.merchant_cluster_accounts} accounts
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="flex items-center gap-2 text-slate-600 font-medium">
                      <Clock className="w-4 h-4 text-rose-500" />
                      <span>Velocity Count (24h burst):</span>
                    </div>
                    <span className="font-mono font-bold text-slate-800">
                      {gf.rapid_velocity_count_24h} other tx
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="flex items-center gap-2 text-slate-600 font-medium">
                      <Layers className="w-4 h-4 text-blue-500" />
                      <span>Account Network Sprawl:</span>
                    </div>
                    <span className="font-mono font-bold text-slate-800">
                      degree {gf.account_network_sprawl_degree}
                    </span>
                  </div>
                </div>
              </div>

              {/* Explainable Attribution Reasons */}
              <div className="card p-5 bg-white space-y-2.5">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5 text-rose-500" />
                  Attribution & Explainable Triggers
                </h4>
                <div className="space-y-2">
                  {exp.risk_reasons.length > 0 ? (
                    exp.risk_reasons.map((reason, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-xl bg-rose-50 border border-rose-200/80 text-xs text-rose-700 font-medium flex items-start gap-2"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 mt-1.5 shrink-0" />
                        <span>{reason}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400 font-medium">Baseline transaction activity.</div>
                  )}
                </div>
              </div>

              {/* ML Embedding Metrics */}
              {exp.anomaly_score !== null && exp.anomaly_score !== undefined && (
                <div className="card p-5 bg-white space-y-2.5">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-indigo-500" />
                    C2GAT ML Tensor Embeddings
                  </h4>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                      <span className="text-[11px] text-slate-400 font-medium">Raw Anomaly Score:</span>
                      <div className="font-mono font-bold text-indigo-600 mt-0.5">
                        {exp.anomaly_score_raw?.toFixed(6) ?? 'N/A'}
                      </div>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                      <span className="text-[11px] text-slate-400 font-medium">Embedding Norm:</span>
                      <div className="font-mono font-bold text-purple-600 mt-0.5">
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
        <div className="p-4 px-6 border-t border-slate-100 bg-white flex items-center justify-between">
          <button onClick={onClose} className="btn btn-secondary text-xs rounded-xl">
            Close Panel
          </button>
          {tx && (
            <button
              onClick={() => onExploreGraph(tx.account_id)}
              className="btn btn-primary text-xs rounded-xl"
            >
              Explore {tx.account_id} Subgraph
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
