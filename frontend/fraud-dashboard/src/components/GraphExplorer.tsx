import React, { useState, useEffect } from 'react';
import {
  Search,
  GitFork,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Info,
  Layers,
  Activity,
  Smartphone,
  Globe,
  Store,
  User,
} from 'lucide-react';
import { AccountGraphResponse, GraphNode, GraphEdge } from '../types';
import { api } from '../api';

interface GraphExplorerProps {
  initialAccountId?: string;
  onSelectTransaction: (txId: string) => void;
}

export const GraphExplorer: React.FC<GraphExplorerProps> = ({
  initialAccountId = 'AC00358',
  onSelectTransaction,
}) => {
  const [accountId, setAccountId] = useState<string>(initialAccountId);
  const [searchInput, setSearchInput] = useState<string>(initialAccountId);
  const [graphData, setGraphData] = useState<AccountGraphResponse | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Zoom & Pan
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const fetchGraph = async (id: string) => {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    try {
      const data = await api.getAccountGraph(id.trim());
      setGraphData(data);
      if (data.nodes.length === 0) {
        setError(`No graph topology found for account '${id}'. Ensure Neo4j is loaded.`);
      } else {
        const root = data.nodes.find((n) => n.id === id);
        if (root) setSelectedNode(root);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch graph data from Neo4j.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph(accountId);
  }, [accountId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setAccountId(searchInput.trim());
      setPan({ x: 0, y: 0 });
      setZoom(1);
    }
  };

  const nodePositions = React.useMemo(() => {
    if (!graphData || graphData.nodes.length === 0) return new Map<string, { x: number; y: number }>();
    const pos = new Map<string, { x: number; y: number }>();

    const centerX = 400;
    const centerY = 300;

    pos.set(graphData.account_id, { x: centerX, y: centerY });

    const txNodes = graphData.nodes.filter((n) => n.type === 'Transaction');
    const entityNodes = graphData.nodes.filter(
      (n) => n.type !== 'Transaction' && n.id !== graphData.account_id
    );

    const txRadius = 160;
    txNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(txNodes.length, 1)) * 2 * Math.PI;
      pos.set(node.id, {
        x: centerX + txRadius * Math.cos(angle),
        y: centerY + txRadius * Math.sin(angle),
      });
    });

    const entRadius = 280;
    entityNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(entityNodes.length, 1)) * 2 * Math.PI + Math.PI / 4;
      pos.set(node.id, {
        x: centerX + entRadius * Math.cos(angle),
        y: centerY + entRadius * Math.sin(angle),
      });
    });

    return pos;
  }, [graphData]);

  const getNodeConfig = (type: string) => {
    switch (type) {
      case 'Account':
        return { color: '#3B82F6', border: '#2563EB', icon: User, bg: '#EFF6FF' };
      case 'Transaction':
        return { color: '#05C168', border: '#04A85A', icon: Activity, bg: '#E8F8F0' };
      case 'Device':
        return { color: '#10B981', border: '#059669', icon: Smartphone, bg: '#ECFDF5' };
      case 'IP':
        return { color: '#F59E0B', border: '#D97706', icon: Globe, bg: '#FFFBEB' };
      case 'Merchant':
        return { color: '#8B5CF6', border: '#7C3AED', icon: Store, bg: '#F5F3FF' };
      default:
        return { color: '#64748B', border: '#475569', icon: Info, bg: '#F8FAFC' };
    }
  };

  const sampleAccounts = ['AC00358', 'AC00004', 'AC00021', 'AC00128', 'AC00396', 'AC00453'];

  return (
    <div className="space-y-5">
      {/* Search Header */}
      <div className="card p-5 bg-white flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-800 tracking-tight flex items-center gap-2">
            <GitFork className="w-5 h-5 text-[#05C168]" />
            Interactive Graph Explorer
          </h2>
          <p className="text-xs text-slate-400 font-medium">
            Bounded Neo4j topological traversals for account identity, device sharing, and merchant clusters.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3 pointer-events-none" />
            <input
              type="text"
              placeholder="Enter Account ID (e.g. AC00358)..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-10 text-xs w-64 rounded-xl border-slate-200"
            />
          </div>
          <button type="submit" className="btn btn-primary text-xs py-2 px-4 rounded-xl">
            Explore Graph
          </button>
        </form>
      </div>

      {/* Suggested Quick Switch Chips */}
      <div className="flex items-center gap-2 text-xs text-slate-500 overflow-x-auto pb-1">
        <span className="shrink-0 font-semibold">High-Sprawl Accounts:</span>
        {sampleAccounts.map((acc) => (
          <button
            key={acc}
            onClick={() => {
              setAccountId(acc);
              setSearchInput(acc);
            }}
            className={`px-3 py-1 rounded-full font-mono text-xs font-bold border transition-all ${
              accountId === acc
                ? 'bg-emerald-50 text-[#05C168] border-emerald-300'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
            }`}
          >
            {acc}
          </button>
        ))}
      </div>

      {/* Graph Canvas Container */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        {/* Visual Graph Box */}
        <div className="card p-0 lg:col-span-3 relative h-[600px] overflow-hidden bg-[#F8FAFC] border border-slate-200 flex flex-col justify-between select-none shadow-sm">
          {/* Controls Bar Overlay */}
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-white/95 backdrop-blur p-1.5 rounded-2xl border border-slate-200 shadow-sm">
            <button
              onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
              className="p-1.5 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))}
              className="p-1.5 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setZoom(1);
                setPan({ x: 0, y: 0 });
              }}
              className="p-1.5 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100"
              title="Reset View"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
            <div className="h-4 w-px bg-slate-200" />
            <span className="text-[11px] font-mono font-bold text-slate-500 px-2">
              {Math.round(zoom * 100)}%
            </span>
          </div>

          {/* Legend Overlay */}
          <div className="absolute bottom-4 left-4 z-10 bg-white/95 backdrop-blur p-3 rounded-2xl border border-slate-200 shadow-sm text-[11px] space-y-1.5">
            <div className="font-bold text-slate-800 text-xs mb-1">Entity Topology Legend</div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
              <span className="text-slate-600 font-medium">Account (Target Anchor)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#05C168]" />
              <span className="text-slate-600 font-medium">Transaction</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span className="text-slate-600 font-medium">Device Hardware</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span className="text-slate-600 font-medium">IP Address</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
              <span className="text-slate-600 font-medium">Merchant Recipient</span>
            </div>
          </div>

          {/* SVG Canvas Area */}
          <div
            className="w-full h-full cursor-grab active:cursor-grabbing"
            onMouseDown={(e) => {
              setIsDragging(true);
              setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
            }}
            onMouseMove={(e) => {
              if (isDragging) {
                setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
              }
            }}
            onMouseUp={() => setIsDragging(false)}
            onMouseLeave={() => setIsDragging(false)}
          >
            {loading ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400">
                <div className="w-8 h-8 border-3 border-[#05C168] border-t-transparent rounded-full animate-spin" />
                <span className="text-xs font-semibold mt-2 text-slate-500">Traversing graph in Neo4j...</span>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-full text-rose-500 text-xs p-6 text-center">
                <Info className="w-8 h-8 mb-2 opacity-80" />
                <p className="font-semibold">{error}</p>
              </div>
            ) : graphData && graphData.nodes.length > 0 ? (
              <svg
                width="100%"
                height="100%"
                viewBox="0 0 800 600"
                className="overflow-visible"
              >
                <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                  {/* Edges */}
                  {graphData.edges.map((edge) => {
                    const src = nodePositions.get(edge.source);
                    const tgt = nodePositions.get(edge.target);
                    if (!src || !tgt) return null;

                    const isHighlight =
                      selectedNode &&
                      (selectedNode.id === edge.source || selectedNode.id === edge.target);

                    return (
                      <g key={edge.id}>
                        <line
                          x1={src.x}
                          y1={src.y}
                          x2={tgt.x}
                          y2={tgt.y}
                          stroke={isHighlight ? '#05C168' : '#CBD5E1'}
                          strokeWidth={isHighlight ? 2.5 : 1.2}
                          strokeDasharray={edge.label === 'ACCESSED_VIA' ? '4 2' : undefined}
                          opacity={isHighlight ? 1 : 0.7}
                        />
                      </g>
                    );
                  })}

                  {/* Nodes */}
                  {graphData.nodes.map((node) => {
                    const pos = nodePositions.get(node.id);
                    if (!pos) return null;
                    const config = getNodeConfig(node.type);
                    const isSelected = selectedNode?.id === node.id;
                    const isRoot = node.id === graphData.account_id;

                    const radius = isRoot ? 26 : node.type === 'Transaction' ? 18 : 16;

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedNode(node);
                        }}
                        className="cursor-pointer group"
                      >
                        {/* Glow Circle */}
                        {isSelected && (
                          <circle
                            r={radius + 8}
                            fill="none"
                            stroke={config.color}
                            strokeWidth={2.5}
                            opacity={0.5}
                            className="animate-pulse"
                          />
                        )}

                        {/* Main Circle */}
                        <circle
                          r={radius}
                          fill={config.color}
                          stroke="#FFFFFF"
                          strokeWidth={2.5}
                          className="transition-all duration-200 shadow-md"
                        />

                        {/* Label Text */}
                        <text
                          y={radius + 14}
                          textAnchor="middle"
                          fill="#334155"
                          fontSize={10}
                          fontWeight="600"
                          fontFamily="JetBrains Mono, monospace"
                          className="pointer-events-none select-none"
                        >
                          {node.id}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </svg>
            ) : null}
          </div>
        </div>

        {/* Selected Node Properties Panel */}
        <div className="card p-5 bg-white space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <Layers className="w-4 h-4 text-[#05C168]" />
              <h3 className="text-sm font-extrabold text-slate-800">Entity Inspector</h3>
            </div>

            {selectedNode ? (
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                    Node Identifier
                  </span>
                  <div className="text-sm font-mono font-extrabold text-slate-800 mt-0.5">
                    {selectedNode.id}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-slate-500 font-semibold">Classification:</span>
                  <span
                    className="px-2.5 py-0.5 rounded-full text-[11px] font-bold"
                    style={{
                      backgroundColor: getNodeConfig(selectedNode.type).bg,
                      color: getNodeConfig(selectedNode.type).color,
                      border: `1px solid ${getNodeConfig(selectedNode.type).border}`,
                    }}
                  >
                    {selectedNode.type}
                  </span>
                </div>

                <div className="pt-2 border-t border-slate-100 space-y-2">
                  <span className="text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                    Graph Attributes
                  </span>

                  {Object.entries(selectedNode.properties || {}).map(([key, val]) => (
                    <div key={key} className="flex items-start justify-between gap-2 py-1 border-b border-slate-50">
                      <span className="text-slate-500 font-mono text-[11px]">{key}:</span>
                      <span className="text-slate-800 font-mono text-[11px] font-bold text-right truncate max-w-[150px]">
                        {String(val)}
                      </span>
                    </div>
                  ))}
                </div>

                {selectedNode.type === 'Transaction' && (
                  <button
                    onClick={() => onSelectTransaction(selectedNode.id)}
                    className="btn btn-primary w-full text-xs mt-3 rounded-xl"
                  >
                    View Full Transaction Audit
                  </button>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400 text-xs font-medium">
                Click any node in the graph canvas to inspect its Neo4j topology.
              </div>
            )}
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 text-[11px] text-slate-500">
            <div className="font-bold text-slate-800 mb-1">Graph Density Summary</div>
            <div>Nodes: <strong className="text-slate-800 font-mono">{graphData?.nodes.length || 0}</strong></div>
            <div>Edges: <strong className="text-slate-800 font-mono">{graphData?.edges.length || 0}</strong></div>
          </div>
        </div>
      </div>
    </div>
  );
};
