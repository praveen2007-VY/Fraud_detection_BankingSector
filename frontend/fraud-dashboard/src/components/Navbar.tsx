import React, { useState, useEffect } from 'react';
import { Shield, Radio, RefreshCw, Server, Database, Cpu } from 'lucide-react';
import { HealthResponse } from '../types';

interface NavbarProps {
  health: HealthResponse | null;
  wsStatus: 'connected' | 'connecting' | 'disconnected';
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  wsStatus,
  onRefresh,
  isRefreshing,
}) => {
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTimeStr(now.toUTCString().slice(17, 25) + ' UTC');
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const kafkaHealthy = health?.dependencies?.kafka?.status === 'healthy';
  const neo4jHealthy = health?.dependencies?.neo4j?.status === 'healthy';
  const mlHealthy = health?.dependencies?.ml_artifacts?.status === 'healthy';

  return (
    <header className="h-16 bg-[#0E1524] border-b border-[#1E293B] px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold text-white tracking-tight">EGIS-SENTINEL</h1>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
              v1.0 Real-Time
            </span>
          </div>
          <p className="text-xs text-slate-400">Enterprise Financial Fraud & Anomaly Intelligence</p>
        </div>
      </div>

      <div className="flex items-center gap-5">
        {/* Status Pills */}
        <div className="hidden lg:flex items-center gap-2 text-xs">
          {/* WebSocket status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#151D2E] border border-[#232F46]">
            <Radio className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Stream:</span>
            <span className="flex items-center gap-1 font-medium">
              <span
                className={`status-pulse ${
                  wsStatus === 'connected' ? 'online' : wsStatus === 'connecting' ? 'degraded' : 'offline'
                }`}
              />
              <span className={wsStatus === 'connected' ? 'text-emerald-400' : 'text-amber-400'}>
                {wsStatus === 'connected' ? 'LIVE' : wsStatus.toUpperCase()}
              </span>
            </span>
          </div>

          {/* Kafka status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#151D2E] border border-[#232F46]">
            <Server className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Kafka:</span>
            <span className="flex items-center gap-1 font-medium">
              <span className={`status-pulse ${kafkaHealthy ? 'online' : 'offline'}`} />
              <span className={kafkaHealthy ? 'text-emerald-400' : 'text-rose-400'}>
                {kafkaHealthy ? 'READY' : 'OFFLINE'}
              </span>
            </span>
          </div>

          {/* Neo4j status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#151D2E] border border-[#232F46]">
            <Database className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Neo4j:</span>
            <span className="flex items-center gap-1 font-medium">
              <span className={`status-pulse ${neo4jHealthy ? 'online' : 'offline'}`} />
              <span className={neo4jHealthy ? 'text-emerald-400' : 'text-rose-400'}>
                {neo4jHealthy ? 'READY' : 'OFFLINE'}
              </span>
            </span>
          </div>

          {/* ML Models */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#151D2E] border border-[#232F46]">
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">C2GAT:</span>
            <span className="flex items-center gap-1 font-medium">
              <span className={`status-pulse ${mlHealthy ? 'online' : 'degraded'}`} />
              <span className={mlHealthy ? 'text-emerald-400' : 'text-amber-400'}>
                {mlHealthy ? 'ACTIVE' : 'DEGRADED'}
              </span>
            </span>
          </div>
        </div>

        {/* Clock */}
        <div className="font-mono text-xs text-slate-400 bg-[#151D2E] px-2.5 py-1 rounded border border-[#232F46]">
          {timeStr}
        </div>

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="btn btn-secondary text-xs px-2.5 py-1.5"
          title="Refresh All Dashboard Data"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>
    </header>
  );
};
