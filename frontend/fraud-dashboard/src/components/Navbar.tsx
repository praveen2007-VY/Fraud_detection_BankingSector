import React, { useState, useEffect } from 'react';
import { ShieldCheck, Radio, RefreshCw, Server, Database, Cpu } from 'lucide-react';
import { HealthResponse, StreamStatus } from '../types';

interface NavbarProps {
  health: HealthResponse | null;
  wsStatus: 'connected' | 'connecting' | 'disconnected';
  lastEventTime?: Date | null;
  streamStatus?: StreamStatus | null;
  streamError?: string | null;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  wsStatus,
  lastEventTime,
  streamStatus,
  streamError,
  onRefresh,
  isRefreshing,
}) => {
  const [timeStr, setTimeStr] = useState<string>('');
  const [nowTs, setNowTs] = useState<number>(Date.now());

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTimeStr(now.toUTCString().slice(17, 25) + ' UTC');
      setNowTs(Date.now());
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const kafkaHealthy = health?.dependencies?.kafka?.status === 'healthy';
  const flinkHealthy = health?.dependencies?.flink?.status === 'healthy';
  const neo4jHealthy = health?.dependencies?.neo4j?.status === 'healthy';
  const mlHealthy = health?.dependencies?.ml_artifacts?.status === 'healthy';

  const isStreamingLive = wsStatus === 'connected' && lastEventTime && (nowTs - lastEventTime.getTime() < 15000);
  const lastEventSeconds = lastEventTime ? Math.max(0, Math.round((nowTs - lastEventTime.getTime()) / 1000)) : null;

  // The only producer is the bundled dataset, so label the stream by its source rather than as live traffic
  const isReplay = streamStatus?.mode === 'replay';
  const sourceLabel = isReplay ? 'Dataset Replay' : 'Dataset Snapshot';
  const replayProgress =
    isReplay && streamStatus.total_records > 0
      ? `${streamStatus.processed.toLocaleString()}/${streamStatus.total_records.toLocaleString()}`
      : null;
  const routeLabel =
    streamStatus?.route === 'flink' ? 'Kafka -> Flink -> backend' : streamStatus?.route === 'direct' ? 'Kafka -> backend (Flink job not running)' : null;
  const streamTitle = streamError
    ? `Replay restart failed: ${streamError}`
    : isReplay
    ? `Replaying transactions_clean.csv from record 1${routeLabel ? ` via ${routeLabel}` : ''}. ${
        lastEventSeconds !== null ? `Last record processed ${lastEventSeconds}s ago.` : 'Waiting for first processed record.'
      }`
    : 'Showing the preloaded dataset with precomputed scores. Click refresh to replay it through the pipeline.';

  return (
    <header className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-200/60 px-6 flex items-center justify-between sticky top-0 z-30 shadow-xs">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-2xl bg-[#05C168] flex items-center justify-center shadow-md shadow-emerald-500/20 text-white">
          <ShieldCheck className="w-5 h-5 stroke-[2.5]" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-extrabold text-slate-800 tracking-tight">
              EGIS-SENTINEL
            </h1>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
              {sourceLabel}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-medium">Enterprise Real-Time Fraud & Anomaly Intelligence</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Status Pills */}
        <div className="hidden lg:flex items-center gap-2 text-xs">
          {/* WebSocket stream status */}
          <div
            className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-50 border border-slate-200/80 cursor-default"
            title={streamTitle}
          >
            <Radio className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">{isReplay ? 'Replay:' : 'Stream:'}</span>
            <span className="flex items-center gap-1 font-bold">
              <span
                className={`status-pulse ${
                  wsStatus !== 'connected' || streamError ? 'offline' : isStreamingLive ? 'online' : 'degraded'
                }`}
              />
              <span
                className={
                  wsStatus !== 'connected' || streamError
                    ? 'text-rose-500'
                    : isStreamingLive
                    ? 'text-[#05C168]'
                    : 'text-amber-500'
                }
              >
                {streamError
                  ? 'RESTART FAILED'
                  : wsStatus !== 'connected'
                  ? wsStatus.toUpperCase()
                  : !isReplay
                  ? 'NOT STREAMING'
                  : isStreamingLive
                  ? `REPLAYING ${replayProgress ?? ''}`.trim()
                  : streamStatus.processed > 0 && streamStatus.processed >= streamStatus.total_records
                  ? `COMPLETE ${replayProgress ?? ''}`.trim()
                  : lastEventSeconds !== null
                  ? `IDLE (${lastEventSeconds}s)`
                  : 'WAITING'}
              </span>
            </span>
          </div>

          {/* Kafka status */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-50 border border-slate-200/80">
            <Server className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">Kafka:</span>
            <span className="flex items-center gap-1 font-bold">
              <span className={`status-pulse ${kafkaHealthy ? 'online' : 'offline'}`} />
              <span className={kafkaHealthy ? 'text-[#05C168]' : 'text-rose-500'}>
                {kafkaHealthy ? 'READY' : 'OFFLINE'}
              </span>
            </span>
          </div>

          {/* Flink status */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-50 border border-slate-200/80">
            <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">Flink:</span>
            <span className="flex items-center gap-1 font-bold">
              <span className={`status-pulse ${flinkHealthy ? 'online' : 'degraded'}`} />
              <span className={flinkHealthy ? 'text-[#05C168]' : 'text-amber-500'}>
                {flinkHealthy ? 'READY' : 'OFFLINE'}
              </span>
            </span>
          </div>

          {/* Neo4j status */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-50 border border-slate-200/80">
            <Database className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">Neo4j:</span>
            <span className="flex items-center gap-1 font-bold">
              <span className={`status-pulse ${neo4jHealthy ? 'online' : 'offline'}`} />
              <span className={neo4jHealthy ? 'text-[#05C168]' : 'text-rose-500'}>
                {neo4jHealthy ? 'READY' : 'OFFLINE'}
              </span>
            </span>
          </div>

          {/* ML Models */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-50 border border-slate-200/80">
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">C2GAT:</span>
            <span className="flex items-center gap-1 font-bold">
              <span className={`status-pulse ${mlHealthy ? 'online' : 'degraded'}`} />
              <span className={mlHealthy ? 'text-[#05C168]' : 'text-amber-500'}>
                {mlHealthy ? 'ACTIVE' : 'OFFLINE'}
              </span>
            </span>
          </div>
        </div>

        {/* Refresh & Clock */}
        <div className="flex items-center gap-2.5">
          <span className="hidden sm:inline-block text-xs font-mono font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-lg">
            {timeStr}
          </span>
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
            title="Restart dataset replay from the first record"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-[#05C168]' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
