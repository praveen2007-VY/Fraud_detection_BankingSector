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
} from './types';
import { api, WS_BASE_URL } from './api';

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

  // Track seen IDs to prevent double counting
  const seenTxIdsRef = useRef<Set<string>>(new Set());
  const seenAccountsRef = useRef<Set<string>>(new Set());

  // Inspector & Graph navigation state
  const [selectedTxId, setSelectedTxId] = useState<string | null>(null);
  const [graphAccountId, setGraphAccountId] = useState<string>('AC00358');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      const [healthData, statsData, distData, alertsData] = await Promise.all([
        api.getHealth().catch(() => null),
        api.getStats().catch(() => null),
        api.getRiskDistribution().catch(() => null),
        api.getAlerts(100).catch(() => ({ items: [], total: 0 })),
      ]);
      if (healthData) setHealth(healthData);
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
            if (parsed.event_type === 'transaction.processed' && parsed.data) {
              const newTx: TransactionSummary = {
                ...parsed.data,
                is_live: true,
              };

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
                  const prevB = prev.approach_b || { low: 79, medium: 1605, high: 724, critical: 104 };
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
        onRefresh={loadData}
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
                onRefresh={loadData}
                isRefreshing={isRefreshing}
              />
            )}

            {currentTab === 'transactions' && (
              <LiveTransactions
                liveTransactions={liveTransactions}
                lastEventTime={lastEventTime}
                onSelectTransaction={setSelectedTxId}
                wsStatus={wsStatus}
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
