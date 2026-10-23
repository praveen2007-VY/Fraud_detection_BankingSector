import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar, TabType } from './components/Sidebar';
import { Overview } from './components/Overview';
import { LiveTransactions } from './components/LiveTransactions';
import { FraudAlerts } from './components/FraudAlerts';
import { GraphExplorer } from './components/GraphExplorer';
import { ModelComparison } from './components/ModelComparison';
import { SystemHealth } from './components/SystemHealth';
import { TransactionDrawer } from './components/TransactionDrawer';
import {
  StatsResponse,
  RiskDistributionResponse,
  AlertItem,
  HealthResponse,
  TransactionSummary,
  StreamStatus,
} from './types';
import { api, WS_BASE_URL } from './api';

const EMPTY_BANDS = { low: 0, medium: 0, high: 0, critical: 0 };

const emptyStats = (prev: StatsResponse | null): StatsResponse => ({
  total_transactions: 0,
  total_volume: 0,
  currency: prev?.currency ?? 'USD',
  low_risk_count: 0,
  medium_risk_count: 0,
  high_risk_count: 0,
  critical_risk_count: 0,
  flagged_count: 0,
  flagged_percentage: 0,
  unique_accounts: 0,
  high_risk_accounts: 0,
  graph_scoring_available: prev?.graph_scoring_available ?? false,
  ml_scoring_available: prev?.ml_scoring_available ?? false,
});

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<TabType>('overview');
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [distribution, setDistribution] = useState<RiskDistributionResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  // Live WebSocket state & event telemetry
  const [liveTransactions, setLiveTransactions] = useState<TransactionSummary[]>([]);
  const [wsStatus, setWsStatus] = useState<'connected' | 'connecting' | 'disconnected'>('connecting');
  const [lastEventTime, setLastEventTime] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [streamStatus, setStreamStatus] = useState<StreamStatus | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);

  // Track seen IDs to prevent double counting
  const seenTxIdsRef = useRef<Set<string>>(new Set());
  const seenAccountsRef = useRef<Set<string>>(new Set());
  const seenHighRiskAccountsRef = useRef<Set<string>>(new Set());
  // Replay session currently shown; records from any other session start a fresh view
  const sessionIdRef = useRef<string | null>(null);

  // Inspector & Graph navigation state
  const [selectedTxId, setSelectedTxId] = useState<string | null>(null);
  const [graphAccountId, setGraphAccountId] = useState<string>('AC00358');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  // Clears every stream-derived view so a replay session is rendered from its first record
  const resetStreamView = (status: StreamStatus) => {
    sessionIdRef.current = status.session_id ?? null;
    seenTxIdsRef.current = new Set();
    seenAccountsRef.current = new Set();
    seenHighRiskAccountsRef.current = new Set();
    setLiveTransactions([]);
    setAlerts([]);
    setLastEventTime(null);
    setStats((prev) => emptyStats(prev));
    setDistribution({ approach_a: { ...EMPTY_BANDS }, approach_b: { ...EMPTY_BANDS }, anomaly: { ...EMPTY_BANDS }, total: 0 });
    setStreamStatus(status);
  };

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      const [healthData, statsData, distData, alertsData, streamData] = await Promise.all([
        api.getHealth().catch(() => null),
        api.getStats().catch(() => null),
        api.getRiskDistribution().catch(() => null),
        api.getAlerts(100).catch(() => ({ items: [], total: 0 })),
        api.getStreamStatus().catch(() => null),
      ]);
      if (healthData) setHealth(healthData);
      if (streamData) {
        if (streamData.mode === 'replay' && streamData.session_id !== sessionIdRef.current) {
          resetStreamView(streamData);
        } else {
          setStreamStatus(streamData);
        }
      }
      if (statsData) {
        setStats((prev) => {
          if (!prev) return statsData;
          // Keep highest transaction count to avoid rolling backward
          if (statsData.total_transactions >= prev.total_transactions) {
            return statsData;
          }
          return prev;
        });
      }
      if (distData) setDistribution(distData);
      if (alertsData && alertsData.items.length > 0) {
        setAlerts((prev) => {
          if (prev.length === 0) return alertsData.items;
          const existingIds = new Set(prev.map((a) => a.transaction_id));
          const newItems = alertsData.items.filter((a) => !existingIds.has(a.transaction_id));
          return [...prev, ...newItems];
        });
      }
    } catch (e) {
      console.error('Error loading dashboard telemetry:', e);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Refresh icon: restart the dataset replay from its first record through Kafka and the backend
  const restartStream = async () => {
    setIsRefreshing(true);
    setStreamError(null);
    try {
      const status = await api.restartReplay();
      resetStreamView(status);
    } catch (e) {
      console.error('Failed to restart dataset replay:', e);
      setStreamError(e instanceof Error ? e.message : String(e));
    }
    await loadData();
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 20000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket lifecycle management with auto-reconnect
  useEffect(() => {
    let reconnectAttempts = 0;

    const connectWs = () => {
      setWsStatus('connecting');
      try {
        const ws = new WebSocket(WS_BASE_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsStatus('connected');
          reconnectAttempts = 0;
          console.log('[WS] Connected to real-time transaction event stream.');
        };

        ws.onmessage = (event) => {
          try {
            const parsed = JSON.parse(event.data);
            if (parsed.event_type === 'stream.reset' && parsed.stream) {
              if (parsed.stream.session_id !== sessionIdRef.current) {
                resetStreamView(parsed.stream);
              }
              return;
            }
            if (parsed.event_type === 'transaction.processed' && parsed.data) {
              const newTx: TransactionSummary = {
                ...parsed.data,
                is_live: true,
              };

              const streamMeta = parsed.stream;
              if (streamMeta?.source === 'dataset_replay') {
                // The record can arrive before the stream.reset event for its session
                if (streamMeta.session_id !== sessionIdRef.current) {
                  resetStreamView({
                    mode: 'replay',
                    source: 'dataset_replay',
                    session_id: streamMeta.session_id,
                    total_records: 0,
                    processed: 0,
                  });
                }
                setStreamStatus((prev) =>
                  prev ? { ...prev, processed: Math.max(prev.processed, streamMeta.processed ?? 0) } : prev
                );
              }

              // Mark timestamp of last received live event
              setLastEventTime(new Date());

              // Append to real-time live feed (most recent first)
              setLiveTransactions((prev) => {
                const filtered = prev.filter((t) => t.transaction_id !== newTx.transaction_id);
                return [newTx, ...filtered].slice(0, 100);
              });

              // If flagged, append or update in alerts queue
              if (newTx.is_flagged) {
                const newAlert: AlertItem = {
                  alert_id: `ALT-${newTx.transaction_id}`,
                  transaction_id: newTx.transaction_id,
                  account_id: newTx.account_id,
                  transaction_amount: newTx.transaction_amount,
                  transaction_date: newTx.transaction_date,
                  severity: newTx.risk_level === 'critical' ? 'critical' : 'high',
                  detection_source:
                    newTx.approach_b_score && newTx.approach_b_score >= 50 && newTx.anomaly_score && newTx.anomaly_score >= 0.5
                      ? 'both'
                      : newTx.anomaly_score && newTx.anomaly_score >= 0.5
                      ? 'ml_anomaly'
                      : 'graph_rules',
                  approach_b_score: newTx.approach_b_score,
                  anomaly_score: newTx.anomaly_score,
                  reasons: newTx.risk_reasons ? newTx.risk_reasons.split(';') : ['Real-time streaming threshold trigger'],
                };
                setAlerts((prev) => {
                  const filtered = prev.filter((a) => a.transaction_id !== newTx.transaction_id);
                  return [newAlert, ...filtered].slice(0, 100);
                });
              }

              const isNewTx = !seenTxIdsRef.current.has(newTx.transaction_id);
              seenTxIdsRef.current.add(newTx.transaction_id);
              const isNewAccount = newTx.account_id ? !seenAccountsRef.current.has(newTx.account_id) : false;
              if (newTx.account_id) seenAccountsRef.current.add(newTx.account_id);
              const isHighRisk = newTx.risk_level === 'high' || newTx.risk_level === 'critical';
              const isNewHighRiskAccount =
                isHighRisk && !!newTx.account_id && !seenHighRiskAccountsRef.current.has(newTx.account_id);
              if (isNewHighRiskAccount) seenHighRiskAccountsRef.current.add(newTx.account_id);

              // Update stats counter dynamically
              if (isNewTx) {
                setStats((prev) => {
                  if (!prev) return prev;
                  const newTotal = prev.total_transactions + 1;
                  const newVolume = Math.round((prev.total_volume + newTx.transaction_amount) * 100) / 100;
                  const newFlagged = newTx.is_flagged ? prev.flagged_count + 1 : prev.flagged_count;
                  const newPct = Math.round((newFlagged / newTotal) * 10000) / 100;
                  const lowCount = newTx.risk_level === 'low' ? prev.low_risk_count + 1 : prev.low_risk_count;
                  const medCount = newTx.risk_level === 'medium' ? prev.medium_risk_count + 1 : prev.medium_risk_count;
                  const highCount = newTx.risk_level === 'high' ? prev.high_risk_count + 1 : prev.high_risk_count;
                  const critCount = newTx.risk_level === 'critical' ? prev.critical_risk_count + 1 : prev.critical_risk_count;
                  const newUniqueAccounts = isNewAccount ? prev.unique_accounts + 1 : prev.unique_accounts;
                  return {
                    ...prev,
                    total_transactions: newTotal,
                    total_volume: newVolume,
                    flagged_count: newFlagged,
                    flagged_percentage: newPct,
                    unique_accounts: newUniqueAccounts,
                    high_risk_accounts: isNewHighRiskAccount ? prev.high_risk_accounts + 1 : prev.high_risk_accounts,
                    low_risk_count: lowCount,
                    medium_risk_count: medCount,
                    high_risk_count: highCount,
                    critical_risk_count: critCount,
                  };
                });

                // Update risk distribution dynamically
                setDistribution((prev) => {
                  if (!prev) return prev;
                  const level = newTx.risk_level || 'low';
                  const prevB = prev.approach_b || { ...EMPTY_BANDS };
                  return {
                    ...prev,
                    total: prev.total + 1,
                    approach_b: {
                      ...prevB,
                      [level]: (prevB[level] || 0) + 1,
                    },
                  };
                });
              }
            }
          } catch (err) {
            console.error('[WS] Failed to parse event payload:', err);
          }
        };

        ws.onerror = (err) => {
          console.warn('[WS] WebSocket error:', err);
          setWsStatus('disconnected');
        };

        ws.onclose = () => {
          setWsStatus('disconnected');
          console.log('[WS] Disconnected. Reconnecting in backoff seconds...');
          const timeout = Math.min(1000 * Math.pow(2, reconnectAttempts), 15000);
          reconnectAttempts += 1;
          reconnectTimeoutRef.current = setTimeout(connectWs, timeout);
        };
      } catch (e) {
        console.error('[WS] Connection attempt failed:', e);
        setWsStatus('disconnected');
      }
    };

    connectWs();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const handleExploreGraph = (accountId: string) => {
    setGraphAccountId(accountId);
    setSelectedTxId(null);
    setCurrentTab('graph');
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F4F5FA] text-slate-800">
      {/* Top Navigation */}
      <Navbar
        health={health}
        wsStatus={wsStatus}
        lastEventTime={lastEventTime}
        streamStatus={streamStatus}
        streamError={streamError}
        onRefresh={restartStream}
        isRefreshing={isRefreshing}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar
          currentTab={currentTab}
          onSelectTab={setCurrentTab}
          alertCount={alerts.length}
          liveCount={liveTransactions.length}
        />

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="max-w-[1440px] mx-auto">
            {currentTab === 'overview' && (
              <Overview
                stats={stats}
                distribution={distribution}
                recentAlerts={alerts}
                health={health}
                liveTransactions={liveTransactions}
                lastEventTime={lastEventTime}
                onSelectTransaction={setSelectedTxId}
                onNavigateToTab={setCurrentTab}
                wsStatus={wsStatus}
                streamStatus={streamStatus}
                onRefresh={restartStream}
                isRefreshing={isRefreshing}
              />
            )}

            {currentTab === 'transactions' && (
              <LiveTransactions
                liveTransactions={liveTransactions}
                onSelectTransaction={setSelectedTxId}
                wsStatus={wsStatus}
                streamStatus={streamStatus}
              />
            )}

            {currentTab === 'alerts' && (
              <FraudAlerts
                alerts={alerts}
                onSelectTransaction={setSelectedTxId}
              />
            )}

            {currentTab === 'graph' && (
              <GraphExplorer
                initialAccountId={graphAccountId}
                onSelectTransaction={setSelectedTxId}
              />
            )}

            {currentTab === 'models' && <ModelComparison />}

            {currentTab === 'health' && (
              <SystemHealth
                health={health}
                onRefresh={loadData}
                isRefreshing={isRefreshing}
              />
            )}
          </div>
        </main>
      </div>

      {/* Investigation Drawer Modal */}
      <TransactionDrawer
        transactionId={selectedTxId}
        onClose={() => setSelectedTxId(null)}
        onExploreGraph={handleExploreGraph}
      />
    </div>
  );
};
