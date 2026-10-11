import React, { useState, useEffect, useRef } from 'react';
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
        // Find the root account node
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

  // Node position layout calculation (hierarchical concentric graph)
  const nodePositions = React.useMemo(() => {
    if (!graphData || graphData.nodes.length === 0) return new Map<string, { x: number; y: number }>();
    const pos = new Map<string, { x: number; y: number }>();

    const centerX = 400;
    const centerY = 300;

    // Center root account
    pos.set(graphData.account_id, { x: centerX, y: centerY });

    const txNodes = graphData.nodes.filter((n) => n.type === 'Transaction');
    const entityNodes = graphData.nodes.filter(
      (n) => n.type !== 'Transaction' && n.id !== graphData.account_id
    );

    // Place transactions on inner circle (radius 160)
    const txRadius = 160;
    txNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(txNodes.length, 1)) * 2 * Math.PI;
      pos.set(node.id, {
        x: centerX + txRadius * Math.cos(angle),
        y: centerY + txRadius * Math.sin(angle),
      });
    });

    // Place Devices, IPs, Merchants on outer circle (radius 280)
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

  // Color & Icon by Node Type
  const getNodeConfig = (type: string) => {
    switch (type) {
      case 'Account':
        return { color: '#3B82F6', border: '#60A5FA', icon: User, bg: 'rgba(59, 130, 246, 0.2)' };
      case 'Transaction':
        return { color: '#06B6D4', border: '#38BDF8', icon: Activity, bg: 'rgba(6, 182, 212, 0.2)' };
      case 'Device':
        return { color: '#10B981', border: '#34D399', icon: Smartphone, bg: 'rgba(16, 185, 129, 0.2)' };
      case 'IP':
        return { color: '#F59E0B', border: '#FBBF24', icon: Globe, bg: 'rgba(245, 158, 11, 0.2)' };
      case 'Merchant':
        return { color: '#A855F7', border: '#C084FC', icon: Store, bg: 'rgba(168, 85, 247, 0.2)' };
      default:
        return { color: '#94A3B8', border: '#CBD5E1', icon: Info, bg: 'rgba(148, 163, 184, 0.2)' };
    }
  };

  const sampleAccounts = ['AC00358', 'AC00004', 'AC00021', 'AC00128', 'AC00396', 'AC00453'];

  return (
    <div className="space-y-4">
      {/* Search Header */}
      <div className="card p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <GitFork className="w-4 h-4 text-cyan-400" />
            Interactive Graph Explorer
          </h2>
          <p className="text-xs text-slate-400">
            Bounded Neo4j topological traversals for account identity, device sharing, and merchant clusters.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Enter Account ID (e.g. AC00358)..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-9 text-xs w-64"
            />
          </div>
          <button type="submit" className="btn btn-primary text-xs">
            Explore Graph
          </button>
        </form>
      </div>

      {/* Suggested Quick Switch Chips */}
      <div className="flex items-center gap-2 text-xs text-slate-400 overflow-x-auto pb-1">
        <span className="shrink-0 font-medium">High-Sprawl Accounts:</span>
        {sampleAccounts.map((acc) => (
          <button
            key={acc}
            onClick={() => {
              setAccountId(acc);
              setSearchInput(acc);
            }}
            className={`px-2 py-0.5 rounded font-mono text-[11px] shrink-0 border transition-all ${
              accountId === acc
                ? 'bg-cyan-950 text-cyan-300 border-cyan-700'
                : 'bg-[#151D2E] text-slate-300 border-[#232F46] hover:bg-[#1E293B]'
            }`}
          >
            {acc}
          </button>
        ))}
      </div>

      {/* Graph Canvas Container */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Visual Graph Box */}
        <div className="card p-0 lg:col-span-3 relative h-[600px] overflow-hidden bg-[#0A0E17] flex flex-col justify-between select-none">
          {/* Controls Bar Overlay */}
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-[#111827]/90 backdrop-blur p-1 rounded-lg border border-[#1E293B]">
            <button
              onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
              className="p-1.5 text-slate-300 hover:text-white rounded hover:bg-[#1E293B]"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))}
              className="p-1.5 text-slate-300 hover:text-white rounded hover:bg-[#1E293B]"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setZoom(1);
                setPan({ x: 0, y: 0 });
              }}
              className="p-1.5 text-slate-300 hover:text-white rounded hover:bg-[#1E293B]"
              title="Reset View"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
            <div className="h-4 w-px bg-slate-700" />
            <span className="text-[11px] font-mono text-slate-400 px-2">
              {Math.round(zoom * 100)}%
            </span>
          </div>

          {/* Legend Overlay */}
          <div className="absolute bottom-4 left-4 z-10 bg-[#111827]/90 backdrop-blur p-2.5 rounded-lg border border-[#1E293B] text-[11px] space-y-1.5">
            <div className="font-semibold text-slate-300 text-xs mb-1">Entity Topology Legend</div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
              <span className="text-slate-300">Account (Target Anchor)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
              <span className="text-slate-300">Transaction</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
              <span className="text-slate-300">Device Hardware</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
              <span className="text-slate-300">IP Address</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
              <span className="text-slate-300">Merchant Recipient</span>
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
                <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-xs mt-2">Traversing graph in Neo4j...</span>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-full text-rose-400 text-xs p-6 text-center">
                <Info className="w-8 h-8 mb-2 opacity-80" />
                <p>{error}</p>
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
                          stroke={isHighlight ? '#38BDF8' : '#1E293B'}
                          strokeWidth={isHighlight ? 2 : 1}
                          strokeDasharray={edge.label === 'ACCESSED_VIA' ? '4 2' : undefined}
                          opacity={isHighlight ? 1 : 0.65}
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
                            stroke={config.border}
                            strokeWidth={2}
                            opacity={0.7}
                            className="animate-pulse"
                          />
                        )}

                        {/* Main Circle */}
                        <circle
                          r={radius}
                          fill={config.color}
                          stroke={isSelected ? '#FFFFFF' : config.border}
                          strokeWidth={isSelected ? 3 : 1.5}
                          className="transition-all duration-200"
                        />

                        {/* Label Text */}
                        <text
                          y={radius + 14}
                          textAnchor="middle"
                          fill="#E2E8F0"
                          fontSize={10}
                          fontFamily="JetBrains Mono, monospace"
                          className="pointer-events-none drop-shadow"
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
        <div className="card p-4 space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2 pb-3 border-b border-[#1E293B]">
              <Layers className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">Entity Inspector</h3>
            </div>

            {selectedNode ? (
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                    Node Identifier
                  </span>
                  <div className="text-sm font-mono font-bold text-white mt-0.5">
                    {selectedNode.id}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Classification:</span>
                  <span
                    className="px-2 py-0.5 rounded text-[11px] font-semibold"
                    style={{
                      backgroundColor: getNodeConfig(selectedNode.type).bg,
                      color: getNodeConfig(selectedNode.type).color,
                      border: `1px solid ${getNodeConfig(selectedNode.type).border}`,
                    }}
                  >
                    {selectedNode.type}
                  </span>
                </div>

                <div className="pt-2 border-t border-[#1E293B] space-y-2">
                  <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                    Graph Attributes
                  </span>

                  {Object.entries(selectedNode.properties || {}).map(([key, val]) => (
                    <div key={key} className="flex items-start justify-between gap-2 py-1 border-b border-[#172033]">
                      <span className="text-slate-400 font-mono text-[11px]">{key}:</span>
                      <span className="text-slate-200 font-mono text-[11px] text-right truncate max-w-[150px]">
                        {String(val)}
                      </span>
                    </div>
                  ))}
                </div>

                {selectedNode.type === 'Transaction' && (
                  <button
                    onClick={() => onSelectTransaction(selectedNode.id)}
                    className="btn btn-primary w-full text-xs mt-3"
                  >
                    View Full Transaction Audit
                  </button>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400 text-xs">
                Click any node in the graph canvas to inspect its Neo4j topology.
              </div>
            )}
          </div>

          <div className="p-3 rounded-lg bg-[#0E1524] border border-[#1E293B] text-[11px] text-slate-400">
            <div className="font-semibold text-slate-300 mb-1">Graph Density Summary</div>
            <div>Nodes: <strong className="text-white font-mono">{graphData?.nodes.length || 0}</strong></div>
            <div>Edges: <strong className="text-white font-mono">{graphData?.edges.length || 0}</strong></div>
          </div>
        </div>
      </div>
    </div>
  );
};
