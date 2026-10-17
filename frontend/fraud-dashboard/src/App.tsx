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

  // Live WebSocket state
  const [liveTransactions, setLiveTransactions] = useState<TransactionSummary[]>([]);
  const [wsStatus, setWsStatus] = useState<'connected' | 'connecting' | 'disconnected'>('connecting');
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

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
      if (statsData) setStats(statsData);
      if (distData) setDistribution(distData);
      if (alertsData) setAlerts(alertsData.items);
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

              setLiveTransactions((prev) => {
                // Deduplicate by transaction_id
                const filtered = prev.filter((t) => t.transaction_id !== newTx.transaction_id);
                return [newTx, ...filtered].slice(0, 100);
              });

              // If flagged, append to alerts queue
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
                setAlerts((prev) => [newAlert, ...prev]);
              }

              // Update stats counter
              setStats((prev) => {
                if (!prev) return prev;
                return {
                  ...prev,
                  total_transactions: prev.total_transactions + 1,
                  total_volume: prev.total_volume + newTx.transaction_amount,
                  flagged_count: newTx.is_flagged ? prev.flagged_count + 1 : prev.flagged_count,
                };
              });
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
