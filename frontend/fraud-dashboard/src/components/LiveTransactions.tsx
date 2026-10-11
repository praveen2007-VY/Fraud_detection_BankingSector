import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  ArrowUpDown,
  Radio,
  Eye,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { TransactionSummary } from '../types';
import { api } from '../api';

interface LiveTransactionsProps {
  liveTransactions: TransactionSummary[];
  onSelectTransaction: (txId: string) => void;
  wsStatus: 'connected' | 'connecting' | 'disconnected';
}

export const LiveTransactions: React.FC<LiveTransactionsProps> = ({
  liveTransactions,
  onSelectTransaction,
  wsStatus,
}) => {
  const [transactions, setTransactions] = useState<TransactionSummary[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters & Pagination state
  const [page, setPage] = useState<number>(0);
  const [limit, setLimit] = useState<number>(25);
  const [search, setSearch] = useState<string>('');
  const [riskLevel, setRiskLevel] = useState<string>('');
  const [flaggedOnly, setFlaggedOnly] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<string>('timestamp');
  const [order, setOrder] = useState<string>('desc');

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const res = await api.getTransactions({
        limit,
        offset: page * limit,
        search: search.trim() || undefined,
        risk_level: riskLevel || undefined,
        flagged_only: flaggedOnly || undefined,
        sort_by: sortBy,
        order,
      });
      setTransactions(res.items);
      setTotal(res.total);
    } catch (e) {
      console.error('Failed to fetch transactions:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [page, limit, search, riskLevel, flaggedOnly, sortBy, order]);

  // Combine newly arrived live events if on page 0 and no search filter
  const displayedTransactions = React.useMemo(() => {
    if (page === 0 && !search && !riskLevel) {
      // Prepend live events that are not already in transactions
      const existingIds = new Set(transactions.map((t) => t.transaction_id));
      const newItems = liveTransactions.filter((lt) => !existingIds.has(lt.transaction_id));
      return [...newItems, ...transactions];
    }
    return transactions;
  }, [transactions, liveTransactions, page, search, riskLevel]);

  const totalPages = Math.ceil(total / limit) || 1;

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setOrder(order === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(field);
      setOrder('desc');
    }
    setPage(0);
  };

  return (
    <div className="space-y-4">
      {/* Top Controls Bar */}
      <div className="card p-4 space-y-3">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-white tracking-tight">Transaction Monitor</h2>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono bg-[#0E1524] border border-[#232F46]">
              <Radio className="w-3 h-3 text-cyan-400" />
              <span className={wsStatus === 'connected' ? 'text-emerald-400' : 'text-amber-400'}>
                {wsStatus === 'connected' ? 'LIVE FEED ACTIVE' : 'STREAM ' + wsStatus.toUpperCase()}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 font-mono">
              Total Records: <strong className="text-white">{total.toLocaleString()}</strong>
            </span>
          </div>
        </div>

        {/* Filter Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 pt-2 border-t border-[#1E293B]">
          {/* Search */}
          <div className="relative md:col-span-2">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search TxID, Account, Device, IP, Merchant..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              className="w-full pl-9 text-xs"
            />
          </div>

          {/* Risk Level Filter */}
          <div>
            <select
              value={riskLevel}
              onChange={(e) => {
                setRiskLevel(e.target.value);
                setPage(0);
              }}
              className="w-full text-xs"
            >
              <option value="">All Risk Tiers</option>
              <option value="low">Low Risk [0–30)</option>
              <option value="medium">Medium Risk [30–50)</option>
              <option value="high">High Risk [50–70)</option>
              <option value="critical">Critical Risk [70–100]</option>
            </select>
          </div>

          {/* Flagged Checkbox */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#0E1524] rounded border border-[#243048]">
            <input
              type="checkbox"
              id="flaggedOnly"
              checked={flaggedOnly}
              onChange={(e) => {
                setFlaggedOnly(e.target.checked);
                setPage(0);
              }}
              className="rounded text-cyan-500 focus:ring-0 cursor-pointer"
            />
            <label htmlFor="flaggedOnly" className="text-xs text-slate-300 cursor-pointer select-none">
              Flagged Only
            </label>
          </div>

          {/* Page Limit Selector */}
          <div>
            <select
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setPage(0);
              }}
              className="w-full text-xs"
            >
              <option value={15}>15 per page</option>
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto min-h-[400px]">
          <table>
            <thead>
              <tr>
                <th
                  onClick={() => handleSort('timestamp')}
                  className="cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Timestamp</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th>TxID</th>
                <th>Account</th>
                <th
                  onClick={() => handleSort('amount')}
                  className="cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Amount</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th>Channel / Location</th>
                <th
                  onClick={() => handleSort('risk_score')}
                  className="cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Approach B Risk</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('anomaly_score')}
                  className="cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1.5">
                    <span>C2GAT Anomaly</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading && displayedTransactions.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-16 text-slate-400">
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                      <span className="text-xs">Loading records...</span>
                    </div>
                  </td>
                </tr>
              ) : displayedTransactions.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-16 text-slate-400">
                    <p className="text-sm">No transactions match the selected filters.</p>
                  </td>
                </tr>
              ) : (
                displayedTransactions.map((tx) => {
                  const isNew = tx.is_live;
                  return (
                    <tr key={tx.transaction_id} className={isNew ? 'row-new' : ''}>
                      <td className="text-xs text-slate-400 font-mono whitespace-nowrap">
                        {tx.transaction_date}
                      </td>
                      <td className="text-xs font-mono font-semibold text-cyan-400 whitespace-nowrap">
                        {tx.transaction_id}
                        {isNew && (
                          <span className="ml-1.5 px-1 py-0.2 rounded bg-cyan-950 text-cyan-300 text-[10px] font-sans border border-cyan-800">
                            NEW
                          </span>
                        )}
                      </td>
                      <td className="text-xs font-mono text-slate-300 whitespace-nowrap">
                        {tx.account_id}
                      </td>
                      <td className="text-xs font-mono font-semibold text-white whitespace-nowrap">
                        ${tx.transaction_amount.toFixed(2)}
                      </td>
                      <td className="text-xs text-slate-400">
                        {tx.channel || 'Online'} • {tx.location || 'N/A'}
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-semibold text-slate-200">
                            {tx.approach_b_score !== null && tx.approach_b_score !== undefined
                              ? tx.approach_b_score.toFixed(0)
                              : 'Pending'}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[11px] badge-${tx.risk_level}`}>
                            {tx.risk_level.toUpperCase()}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="text-xs font-mono text-indigo-300 font-medium">
                          {tx.anomaly_score !== null && tx.anomaly_score !== undefined
                            ? (tx.anomaly_score * 100).toFixed(1) + '%'
                            : 'N/A'}
                        </span>
                      </td>
                      <td>
                        {tx.is_flagged ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 px-2 py-0.5 rounded bg-rose-950/60 border border-rose-900/60">
                            <ShieldAlert className="w-3 h-3" /> Flagged
                          </span>
                        ) : (
                          <span className="text-[11px] text-slate-500 font-mono">Normal</span>
                        )}
                      </td>
                      <td>
                        <button
                          onClick={() => onSelectTransaction(tx.transaction_id)}
                          className="btn btn-secondary text-xs px-2.5 py-1"
                        >
                          <Eye className="w-3 h-3 text-cyan-400" />
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-4 border-t border-[#1E293B] flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing <strong className="text-white">{page * limit + 1}</strong> to{' '}
            <strong className="text-white">{Math.min((page + 1) * limit, total)}</strong> of{' '}
            <strong className="text-white">{total.toLocaleString()}</strong> transactions
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="btn btn-secondary text-xs px-2.5 py-1 disabled:opacity-40"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Previous
            </button>
            <span className="font-mono px-2">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1 || loading}
              className="btn btn-secondary text-xs px-2.5 py-1 disabled:opacity-40"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
