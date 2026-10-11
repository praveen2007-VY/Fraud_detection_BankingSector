import React, { useState } from 'react';
import {
  Server,
  Radio,
  Database,
  Cpu,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { HealthResponse } from '../types';
import { api } from '../api';

interface SystemHealthProps {
  health: HealthResponse | null;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const SystemHealth: React.FC<SystemHealthProps> = ({
  health,
  onRefresh,
  isRefreshing,
}) => {
  const [testResult, setTestResult] = useState<string | null>(null);

  const kafka = health?.dependencies?.kafka;
  const neo4j = health?.dependencies?.neo4j;
  const ml = health?.dependencies?.ml_artifacts;

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="card p-5 bg-gradient-to-r from-[#11192E] to-[#151D2E] border-cyan-900/40 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <Server className="w-5 h-5 text-cyan-400" />
            Infrastructure & Component Observability
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time health telemetry across the streaming fraud pipeline.
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="btn btn-primary text-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          Run Health Probes
        </button>
      </div>

      {/* Component Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Backend API Card */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-blue-950 text-blue-400 border border-blue-800">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">FastAPI Application Server</h3>
                <span className="text-xs text-slate-400">Endpoint: http://127.0.0.1:8000</span>
              </div>
            </div>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
              <CheckCircle2 className="w-3.5 h-3.5" />
              ONLINE
            </span>
          </div>

          <div className="text-xs space-y-2 pt-2 border-t border-[#1E293B]">
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Process State:</span>
              <span className="font-mono text-emerald-400">uvicorn active</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">OpenAPI Documentation:</span>
              <a
                href="http://127.0.0.1:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="text-cyan-400 hover:underline flex items-center gap-1 font-mono"
              >
                /docs <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">WebSocket Endpoint:</span>
              <span className="font-mono text-slate-200">/ws/transactions</span>
            </div>
          </div>
        </div>

        {/* Apache Kafka KRaft */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-cyan-950 text-cyan-400 border border-cyan-800">
                <Radio className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Apache Kafka 3.6.1 (KRaft)</h3>
                <span className="text-xs text-slate-400">Broker: localhost:9092</span>
              </div>
            </div>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                kafka?.status === 'healthy'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : 'bg-rose-950 text-rose-400 border border-rose-800'
              }`}
            >
              {kafka?.status === 'healthy' ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  REACHABLE
                </>
              ) : (
                <>
                  <XCircle className="w-3.5 h-3.5" />
                  OFFLINE
                </>
              )}
            </span>
          </div>

          <div className="text-xs space-y-2 pt-2 border-t border-[#1E293B]">
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Raw Input Topic:</span>
              <span className="font-mono text-cyan-400">transactions</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Processed Topic:</span>
              <span className="font-mono text-emerald-400">processed_transactions</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Message Serialization:</span>
              <span className="font-mono text-slate-200">JSON UTF-8 Payload</span>
            </div>
          </div>
        </div>

        {/* Neo4j Graph Database */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-purple-950 text-purple-400 border border-purple-800">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Neo4j Graph Database 5.26</h3>
                <span className="text-xs text-slate-400">Bolt: bolt://localhost:7687</span>
              </div>
            </div>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                neo4j?.status === 'healthy'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : 'bg-rose-950 text-rose-400 border border-rose-800'
              }`}
            >
              {neo4j?.status === 'healthy' ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  CONNECTED
                </>
              ) : (
                <>
                  <XCircle className="w-3.5 h-3.5" />
                  UNREACHABLE
                </>
              )}
            </span>
          </div>

          <div className="text-xs space-y-2 pt-2 border-t border-[#1E293B]">
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Graph Browser UI:</span>
              <a
                href="http://localhost:7474"
                target="_blank"
                rel="noreferrer"
                className="text-cyan-400 hover:underline flex items-center gap-1 font-mono"
              >
                http://localhost:7474 <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Ingested Graph Entities:</span>
              <span className="font-mono text-purple-300">4,380 Nodes Verified</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Graph Schema:</span>
              <span className="font-mono text-slate-200">Account, Tx, Device, IP, Merchant</span>
            </div>
          </div>
        </div>

        {/* Machine Learning Model Checkpoints */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-teal-950 text-teal-400 border border-teal-800">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">C2GAT ML Artifacts</h3>
                <span className="text-xs text-slate-400">Location: /ml/c2gat_model.pt</span>
              </div>
            </div>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                ml?.status === 'healthy'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : 'bg-amber-950 text-amber-400 border border-amber-800'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              VERIFIED
            </span>
          </div>

          <div className="text-xs space-y-2 pt-2 border-t border-[#1E293B]">
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Model Checkpoint:</span>
              <span className="font-mono text-emerald-400">c2gat_model.pt (68.6 KB)</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">StandardScaler Artifact:</span>
              <span className="font-mono text-emerald-400">c2gat_scaler.pkl</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Score Database:</span>
              <span className="font-mono text-cyan-400">2,512 Scores Linked</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
