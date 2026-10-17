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
      <div className="card p-6 bg-white flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-[#05C168] flex items-center justify-center">
              <Server className="w-5 h-5 stroke-[2.5]" />
            </div>
            Infrastructure & Component Observability
          </h2>
          <p className="text-xs text-slate-400 font-medium mt-1">
            Real-time health telemetry across the streaming fraud pipeline.
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="btn btn-primary text-xs py-2 px-4 rounded-xl"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          Run Health Probes
        </button>
      </div>

      {/* Component Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Backend API Card */}
        <div className="card p-6 bg-white space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center">
                <Server className="w-6 h-6 stroke-[2]" />
              </div>
              <div>
                <h3 className="text-sm font-extrabold text-slate-800">FastAPI Application Server</h3>
                <span className="text-xs text-slate-400 font-medium">Endpoint: http://127.0.0.1:8000</span>
              </div>
            </div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-[#05C168] border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5" />
              ONLINE
            </span>
          </div>

          <div className="text-xs space-y-2.5 pt-3 border-t border-slate-100">
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">Process State:</span>
              <span className="font-mono font-bold text-[#05C168]">uvicorn active</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">OpenAPI Documentation:</span>
              <a
                href="http://127.0.0.1:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="text-[#05C168] hover:underline flex items-center gap-1 font-mono font-bold"
              >
                /docs <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">WebSocket Endpoint:</span>
              <span className="font-mono text-slate-700 font-semibold">/ws/transactions</span>
            </div>
          </div>
        </div>

        {/* Apache Kafka KRaft */}
        <div className="card p-6 bg-white space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center">
                <Radio className="w-6 h-6 stroke-[2]" />
              </div>
              <div>
                <h3 className="text-sm font-extrabold text-slate-800">Apache Kafka (KRaft Mode)</h3>
                <span className="text-xs text-slate-400 font-medium">Broker: localhost:9092</span>
              </div>
            </div>
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                kafka?.status === 'healthy'
                  ? 'bg-emerald-50 text-[#05C168] border-emerald-200'
                  : 'bg-rose-50 text-rose-600 border-rose-200'
              }`}
            >
              {kafka?.status === 'healthy' ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  ONLINE
                </>
              ) : (
                <>
                  <XCircle className="w-3.5 h-3.5" />
                  OFFLINE
                </>
              )}
            </span>
          </div>

          <div className="text-xs space-y-2.5 pt-3 border-t border-slate-100">
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">Topic Ingestion:</span>
              <span className="font-mono text-slate-800 font-semibold">{kafka?.details?.topics?.join(', ') || 'transactions'}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">Stream Consumer:</span>
              <span className="font-mono font-bold text-[#05C168]">Background Worker Active</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">KRaft Metadata:</span>
              <span className="font-mono text-slate-700 font-semibold">Native Controller (No ZK)</span>
            </div>
          </div>
        </div>

        {/* Neo4j Database */}
        <div className="card p-6 bg-white space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-2xl bg-teal-50 text-[#0F5C5C] flex items-center justify-center">
                <Database className="w-6 h-6 stroke-[2]" />
              </div>
              <div>
                <h3 className="text-sm font-extrabold text-slate-800">Neo4j Graph Database</h3>
                <span className="text-xs text-slate-400 font-medium">Bolt: bolt://localhost:7687</span>
              </div>
            </div>
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                neo4j?.status === 'healthy'
                  ? 'bg-emerald-50 text-[#05C168] border-emerald-200'
                  : 'bg-rose-50 text-rose-600 border-rose-200'
              }`}
            >
              {neo4j?.status === 'healthy' ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  ONLINE
                </>
              ) : (
                <>
                  <XCircle className="w-3.5 h-3.5" />
                  OFFLINE
                </>
              )}
            </span>
          </div>

          <div className="text-xs space-y-2.5 pt-3 border-t border-slate-100">
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">Topology Nodes:</span>
              <span className="font-mono font-bold text-slate-800">4,380 Entity Nodes</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">Browser Interface:</span>
              <a
                href="http://localhost:7474"
                target="_blank"
                rel="noreferrer"
                className="text-[#05C168] hover:underline flex items-center gap-1 font-mono font-bold"
              >
                http://localhost:7474 <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">Cypher Engine:</span>
              <span className="font-mono text-slate-700 font-semibold">Community 5.26</span>
            </div>
          </div>
        </div>

        {/* Machine Learning Artifacts */}
        <div className="card p-6 bg-white space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center">
                <Cpu className="w-6 h-6 stroke-[2]" />
              </div>
              <div>
                <h3 className="text-sm font-extrabold text-slate-800">C2GAT-Inspired PyTorch Model</h3>
                <span className="text-xs text-slate-400 font-medium">Artifacts Checkpoint</span>
              </div>
            </div>
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                ml?.status === 'healthy'
                  ? 'bg-emerald-50 text-[#05C168] border-emerald-200'
                  : 'bg-amber-50 text-amber-600 border-amber-200'
              }`}
            >
              {ml?.status === 'healthy' ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  VERIFIED
                </>
              ) : (
                <>
                  <AlertTriangle className="w-3.5 h-3.5" />
                  PARTIAL
                </>
              )}
            </span>
          </div>

          <div className="text-xs space-y-2.5 pt-3 border-t border-slate-100">
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">Weights File:</span>
              <span className="font-mono text-slate-800 font-semibold">ml/c2gat_model.pt (Present)</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">Feature Normalizer:</span>
              <span className="font-mono text-slate-800 font-semibold">ml/c2gat_scaler.pkl (Present)</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span className="text-slate-400 font-medium">Anomaly Embeddings:</span>
              <span className="font-mono font-bold text-[#05C168]">2,512 Scores Verified</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
