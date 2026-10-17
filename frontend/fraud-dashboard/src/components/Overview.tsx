import React, { useState } from 'react';
import {
  Users,
  Layers,
  AlertTriangle,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ArrowUpRight,
  ArrowDownLeft,
  Bell,
  Search,
  Radio,
  Server,
  Database,
  Cpu,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import { StatsResponse, RiskDistributionResponse, AlertItem, HealthResponse, TransactionSummary } from '../types';

interface OverviewProps {
  stats: StatsResponse | null;
  distribution: RiskDistributionResponse | null;
  recentAlerts: AlertItem[];
  health: HealthResponse | null;
  onSelectTransaction: (txId: string) => void;
  onNavigateToTab: (tab: any) => void;
  wsStatus?: 'connected' | 'connecting' | 'disconnected';
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const Overview: React.FC<OverviewProps> = ({
  stats,
  distribution,
  recentAlerts,
  health,
  onSelectTransaction,
  onNavigateToTab,
  wsStatus = 'connected',
  onRefresh,
  isRefreshing,
}) => {
  const [selectedDonutSegment, setSelectedDonutSegment] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');
  const [trendPeriod, setTrendPeriod] = useState<string>('7 Days');
  const [hoveredDay, setHoveredDay] = useState<number | null>(null);

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-96 text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-3 border-[#05C168] border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium text-slate-500">Loading SentinelBank Intelligence...</p>
        </div>
      </div>
    );
  }

  const kafkaHealthy = health?.dependencies?.kafka?.status === 'healthy';
  const neo4jHealthy = health?.dependencies?.neo4j?.status === 'healthy';
  const mlHealthy = health?.dependencies?.ml_artifacts?.status === 'healthy';

  const appB = distribution?.approach_b || {
    low: stats.low_risk_count || 79,
    medium: stats.medium_risk_count || 1605,
    high: stats.high_risk_count || 724,
    critical: stats.critical_risk_count || 104,
  };

  const totalDist = (appB.low + appB.medium + appB.high + appB.critical) || 2512;
  const lowPct = Math.round((appB.low / totalDist) * 100);
  const medPct = Math.round((appB.medium / totalDist) * 100);
  const highPct = Math.round((appB.high / totalDist) * 100);
  const critPct = Math.max(1, 100 - lowPct - medPct - highPct);

  // SVG Donut calculation
  const radius = 54;
  const circumference = 2 * Math.PI * radius; // ~339.29
  const lowOffset = 0;
  const lowStroke = (lowPct / 100) * circumference;
  const medStroke = (medPct / 100) * circumference;
  const highStroke = (highPct / 100) * circumference;
  const critStroke = (critPct / 100) * circumference;

  // 7-day spline data points
  const weekDays = [
    { day: 'Monday', normal: 180, flagged: 45, total: '$94,200' },
    { day: 'Tuesday', normal: 260, flagged: 110, total: '$148,500' },
    { day: 'Wednesday', normal: 140, flagged: 85, total: '$76,300' },
    { day: 'Thursday', normal: 310, flagged: 130, total: '$162,100' },
    { day: 'Friday', normal: 220, flagged: 70, total: '$118,400' },
    { day: 'Saturday', normal: 190, flagged: 140, total: '$95,800' },
    { day: 'Sunday', normal: 280, flagged: 95, total: '$145,200' },
  ];

  // Selected donut segment details
  const segmentDetails = {
    low: { label: 'Low Risk', count: appB.low, pct: `${lowPct}%`, color: '#05C168', desc: 'Legitimate regular flow' },
    medium: { label: 'Medium Risk', count: appB.medium, pct: `${medPct}%`, color: '#00D1B2', desc: 'Standard business transfers' },
    high: { label: 'High Risk', count: appB.high, pct: `${highPct}%`, color: '#3B82F6', desc: 'Dense device/IP clusters' },
    critical: { label: 'Critical Risk', count: appB.critical, pct: `${critPct}%`, color: '#8B5CF6', desc: 'Multi-hop fraud ring alert' },
  };

  const activeSegment = segmentDetails[selectedDonutSegment];

  // Mock / Real recent transactions for right rail
  const recentTransactions = [
    { id: 'TX001635', title: 'Transfer Flagged', account: 'AC00358', amount: '$1,762', isRisk: true, date: '13 Oct 2026', type: 'out' },
    { id: 'TX000412', title: 'Deposit Online', account: 'AC00042', amount: '$291', isRisk: false, date: '13 Oct 2026', type: 'in' },
    { id: 'TX000892', title: 'Deposit Merchant', account: 'AC00115', amount: '$691', isRisk: false, date: '13 Oct 2026', type: 'in' },
    { id: 'TX001944', title: 'Critical Outlier', account: 'AC00481', amount: '$1,480', isRisk: true, date: '12 Oct 2026', type: 'out' },
    { id: 'TX000721', title: 'Deposit Clean', account: 'AC00088', amount: '$258', isRisk: false, date: '12 Oct 2026', type: 'in' },
    { id: 'TX001103', title: 'Transfer Deposit', account: 'AC00219', amount: '$308', isRisk: false, date: '12 Oct 2026', type: 'in' },
  ];

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
      {/* ======================================================== */}
      {/* MAIN DASHBOARD COLUMN (8 COLS on XL)                      */}
      {/* ======================================================== */}
      <div className="xl:col-span-8 space-y-6">
        {/* Header Bar matching reference: Title + Pill Search */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">Overview</h1>
            <p className="text-xs text-slate-400 font-medium">Real-time banking transactions & fraud telemetry</p>
          </div>

          <div className="flex items-center gap-3">
            {/* Pill Search Input matching reference */}
            <div className="relative">
              <input
                type="text"
                placeholder='Search "transaction, account"'
                className="w-64 sm:w-72 bg-white border border-slate-200/80 rounded-full py-2 pl-4 pr-10 text-xs text-slate-700 placeholder-slate-400 shadow-sm focus:outline-none focus:border-[#05C168] focus:ring-2 focus:ring-[#05C168]/15"
              />
              <Search className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            {onRefresh && (
              <button
                onClick={onRefresh}
                className="h-9 w-9 rounded-full bg-white border border-slate-200/80 flex items-center justify-center text-slate-500 hover:text-slate-800 hover:shadow-sm transition-all"
                title="Refresh metrics"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-[#05C168]' : ''}`} />
              </button>
            )}
          </div>
        </div>

        {/* -------------------------------------------------------- */}
        {/* TOP KPI SQUIRCLE CARDS (Matches Customer, Employees, Request) */}
        {/* -------------------------------------------------------- */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Card 1: Customer Accounts (Teal squircle like reference) */}
          <div className="card p-5 flex items-center gap-4 bg-white hover:shadow-card-hover transition-all">
            <div className="w-13 h-13 rounded-2xl bg-[#0F5C5C] flex items-center justify-center text-white shrink-0 shadow-md shadow-teal-900/10">
              <Users className="w-6 h-6 stroke-[2.2]" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-400">Customer</p>
              <h3 className="text-2xl font-extrabold text-slate-800 tracking-tight mt-0.5">
                {stats.unique_accounts.toLocaleString()}
              </h3>
              <span className="text-[10px] text-emerald-600 font-bold bg-emerald-50 px-1.5 py-0.5 rounded-md mt-1 inline-block">
                Active Nodes
              </span>
            </div>
          </div>

          {/* Card 2: Monitored Transactions (Amber squircle like Employees) */}
          <div className="card p-5 flex items-center gap-4 bg-white hover:shadow-card-hover transition-all">
            <div className="w-13 h-13 rounded-2xl bg-[#FFB020] flex items-center justify-center text-white shrink-0 shadow-md shadow-amber-500/15">
              <Layers className="w-6 h-6 stroke-[2.2]" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-400">Transactions</p>
              <h3 className="text-2xl font-extrabold text-slate-800 tracking-tight mt-0.5">
                {stats.total_transactions.toLocaleString()}
              </h3>
              <span className="text-[10px] text-amber-600 font-bold bg-amber-50 px-1.5 py-0.5 rounded-md mt-1 inline-block">
                Stream Indexed
              </span>
            </div>
          </div>

          {/* Card 3: Flagged Threats (Mint squircle like Request) */}
          <div className="card p-5 flex items-center gap-4 bg-white hover:shadow-card-hover transition-all">
            <div className="w-13 h-13 rounded-2xl bg-[#05C168] flex items-center justify-center text-white shrink-0 shadow-md shadow-emerald-500/15">
              <AlertTriangle className="w-6 h-6 stroke-[2.2]" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-400">Threat Alerts</p>
              <h3 className="text-2xl font-extrabold text-slate-800 tracking-tight mt-0.5">
                {stats.flagged_count.toLocaleString()}
              </h3>
              <span className="text-[10px] text-rose-600 font-bold bg-rose-50 px-1.5 py-0.5 rounded-md mt-1 inline-block">
                {stats.flagged_percentage}% Flagged
              </span>
            </div>
          </div>
        </div>

        {/* -------------------------------------------------------- */}
        {/* MIDDLE ROW: DONUT CHART + DEEP TEAL CARD                  */}
        {/* -------------------------------------------------------- */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* LEFT: Customer based risk tier (Donut Chart matching reference) */}
          <div className="lg:col-span-7 card p-6 bg-white flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-800">Customer based risk tier</h3>
              <div className="flex items-center gap-1.5 text-slate-400">
                <button
                  onClick={() => {
                    const keys: Array<'low' | 'medium' | 'high' | 'critical'> = ['low', 'medium', 'high', 'critical'];
                    const idx = keys.indexOf(selectedDonutSegment);
                    setSelectedDonutSegment(keys[(idx - 1 + keys.length) % keys.length]);
                  }}
                  className="w-6 h-6 rounded-full border border-slate-200 flex items-center justify-center hover:bg-slate-50 text-slate-600 transition-colors"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => {
                    const keys: Array<'low' | 'medium' | 'high' | 'critical'> = ['low', 'medium', 'high', 'critical'];
                    const idx = keys.indexOf(selectedDonutSegment);
                    setSelectedDonutSegment(keys[(idx + 1) % keys.length]);
                  }}
                  className="w-6 h-6 rounded-full border border-slate-200 flex items-center justify-center hover:bg-slate-50 text-slate-600 transition-colors"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Donut and Legend Layout */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-6 my-auto pt-4">
              {/* SVG Ring Donut */}
              <div className="relative w-44 h-44 flex items-center justify-center">
                <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 140 140">
                  {/* Background Track */}
                  <circle
                    cx="70"
                    cy="70"
                    r={radius}
                    stroke="#F1F5F9"
                    strokeWidth="18"
                    fill="transparent"
                  />
                  {/* Low Risk Segment (Green) */}
                  <circle
                    cx="70"
                    cy="70"
                    r={radius}
                    stroke="#05C168"
                    strokeWidth={selectedDonutSegment === 'low' ? '22' : '18'}
                    strokeDasharray={`${lowStroke} ${circumference}`}
                    strokeDashoffset={0}
                    fill="transparent"
                    className="cursor-pointer transition-all duration-300"
                    onClick={() => setSelectedDonutSegment('low')}
                  />
                  {/* Medium Risk Segment (Teal/Cyan) */}
                  <circle
                    cx="70"
                    cy="70"
                    r={radius}
                    stroke="#00D1B2"
                    strokeWidth={selectedDonutSegment === 'medium' ? '22' : '18'}
                    strokeDasharray={`${medStroke} ${circumference}`}
                    strokeDashoffset={-lowStroke}
                    fill="transparent"
                    className="cursor-pointer transition-all duration-300"
                    onClick={() => setSelectedDonutSegment('medium')}
                  />
                  {/* High Risk Segment (Blue/Amber) */}
                  <circle
                    cx="70"
                    cy="70"
                    r={radius}
                    stroke="#3B82F6"
                    strokeWidth={selectedDonutSegment === 'high' ? '22' : '18'}
                    strokeDasharray={`${highStroke} ${circumference}`}
                    strokeDashoffset={-(lowStroke + medStroke)}
                    fill="transparent"
                    className="cursor-pointer transition-all duration-300"
                    onClick={() => setSelectedDonutSegment('high')}
                  />
                  {/* Critical Risk Segment (Violet/Purple) */}
                  <circle
                    cx="70"
                    cy="70"
                    r={radius}
                    stroke="#8B5CF6"
                    strokeWidth={selectedDonutSegment === 'critical' ? '22' : '18'}
                    strokeDasharray={`${critStroke} ${circumference}`}
                    strokeDashoffset={-(lowStroke + medStroke + highStroke)}
                    fill="transparent"
                    className="cursor-pointer transition-all duration-300"
                    onClick={() => setSelectedDonutSegment('critical')}
                  />
                </svg>

                {/* Floating Tooltip inside or center (like Bojongsoang 854) */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    {activeSegment.label}
                  </span>
                  <span className="text-xl font-extrabold text-slate-800 leading-tight">
                    {activeSegment.count}
                  </span>
                  <span className="text-[11px] font-bold text-[#05C168]">
                    {activeSegment.pct}
                  </span>
                </div>
              </div>

              {/* Legend List on Right */}
              <div className="space-y-2.5 text-xs w-full sm:w-auto">
                <div
                  onClick={() => setSelectedDonutSegment('low')}
                  className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl cursor-pointer transition-all ${
                    selectedDonutSegment === 'low' ? 'bg-emerald-50 text-slate-900 font-bold' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <span className="w-2.5 h-2.5 rounded-md bg-[#05C168] shrink-0" />
                  <span>Low Risk (79)</span>
                </div>
                <div
                  onClick={() => setSelectedDonutSegment('medium')}
                  className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl cursor-pointer transition-all ${
                    selectedDonutSegment === 'medium' ? 'bg-teal-50 text-slate-900 font-bold' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <span className="w-2.5 h-2.5 rounded-md bg-[#00D1B2] shrink-0" />
                  <span>Medium Risk (1,605)</span>
                </div>
                <div
                  onClick={() => setSelectedDonutSegment('high')}
                  className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl cursor-pointer transition-all ${
                    selectedDonutSegment === 'high' ? 'bg-blue-50 text-slate-900 font-bold' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <span className="w-2.5 h-2.5 rounded-md bg-[#3B82F6] shrink-0" />
                  <span>High Risk (724)</span>
                </div>
                <div
                  onClick={() => setSelectedDonutSegment('critical')}
                  className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl cursor-pointer transition-all ${
                    selectedDonutSegment === 'critical' ? 'bg-purple-50 text-slate-900 font-bold' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <span className="w-2.5 h-2.5 rounded-md bg-[#8B5CF6] shrink-0" />
                  <span>Critical (104)</span>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: DEEP TEAL FEATURE CARD (Matches reference's Total category waste card) */}
          <div className="lg:col-span-5 rounded-[28px] p-6 text-white bg-gradient-to-br from-[#065F46] via-[#047857] to-[#064E3B] shadow-xl shadow-emerald-950/15 flex flex-col justify-between relative overflow-hidden">
            {/* Background ambient glow */}
            <div className="absolute -right-8 -bottom-8 w-40 h-40 bg-white/5 rounded-full blur-2xl pointer-events-none" />

            <div>
              <p className="text-xs font-semibold text-emerald-200">High-Risk Exposure</p>
              <h4 className="text-3xl font-extrabold text-white tracking-tight mt-1">
                {stats.high_risk_accounts} <span className="text-sm font-medium text-emerald-200">Accounts</span>
              </h4>
            </div>

            <div className="my-5 space-y-4">
              <div>
                <p className="text-[11px] text-emerald-200 uppercase tracking-wider font-semibold">Flagged Volume In</p>
                <p className="text-2xl font-black text-white mt-0.5">
                  ${(stats.total_volume * 0.67).toLocaleString('en-US', { maximumFractionDigits: 0 })}{' '}
                  <span className="text-xs font-bold text-emerald-300">USD</span>
                </p>
              </div>

              <div>
                <p className="text-[11px] text-emerald-200 uppercase tracking-wider font-semibold">C2GAT Anomaly Score</p>
                <p className="text-2xl font-black text-white mt-0.5">
                  0.548 <span className="text-xs font-bold text-emerald-300">Avg Error</span>
                </p>
              </div>
            </div>

            {/* Bottom mini bar visualization matching reference */}
            <div className="flex items-end justify-between pt-2 border-t border-emerald-500/30">
              <span className="text-xs font-semibold text-emerald-100">Live Flink Telemetry</span>
              <div className="flex items-end gap-1.5 h-7">
                <span className="w-2 h-3 bg-emerald-300/40 rounded-sm" />
                <span className="w-2 h-5 bg-emerald-300/70 rounded-sm" />
                <span className="w-2 h-4 bg-emerald-300/50 rounded-sm" />
                <span className="w-2 h-7 bg-white rounded-sm shadow-sm" />
                <span className="w-2 h-6 bg-emerald-300/90 rounded-sm" />
              </div>
            </div>
          </div>
        </div>

        {/* -------------------------------------------------------- */}
        {/* BOTTOM ROW: TRANSACTION VOLUME CURVE (Waste In & Out style) */}
        {/* -------------------------------------------------------- */}
        <div className="card p-6 bg-white">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-800">Transaction Volume & Influx</h3>
              <p className="text-xs text-slate-400">Dual stream: Clean deposits vs Flagged threat anomalies</p>
            </div>

            {/* Dropdown pill matching 7 Days in reference */}
            <div className="relative">
              <button
                onClick={() => setTrendPeriod(trendPeriod === '7 Days' ? '30 Days' : '7 Days')}
                className="flex items-center gap-1.5 bg-slate-100/80 hover:bg-slate-200/80 text-slate-700 text-xs font-bold px-3 py-1.5 rounded-full transition-colors"
              >
                <span>{trendPeriod}</span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
              </button>
            </div>
          </div>

          {/* SVG Smooth Spline Graph */}
          <div className="relative w-full h-48 pt-2">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 700 150" preserveAspectRatio="none">
              <defs>
                <linearGradient id="flaggedGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FF2E63" stopOpacity="0.12" />
                  <stop offset="100%" stopColor="#FF2E63" stopOpacity="0.0" />
                </linearGradient>
                <linearGradient id="cleanGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#05C168" stopOpacity="0.12" />
                  <stop offset="100%" stopColor="#05C168" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Grid Lines */}
              <line x1="0" y1="30" x2="700" y2="30" stroke="#F1F5F9" strokeDasharray="3 3" />
              <line x1="0" y1="75" x2="700" y2="75" stroke="#F1F5F9" strokeDasharray="3 3" />
              <line x1="0" y1="120" x2="700" y2="120" stroke="#F1F5F9" strokeDasharray="3 3" />

              {/* Red/Pink Flagged Spline Curve */}
              <path
                d="M 20 40 Q 120 20 220 50 T 420 80 T 560 30 T 680 70"
                fill="none"
                stroke="#FF2E63"
                strokeWidth="3"
                strokeLinecap="round"
              />

              {/* Green Clean Volume Spline Curve */}
              <path
                d="M 20 100 Q 120 110 220 80 T 420 120 T 560 90 T 680 110"
                fill="none"
                stroke="#05C168"
                strokeWidth="3"
                strokeLinecap="round"
              />

              {/* Key points with hover rings */}
              {weekDays.map((item, i) => {
                const x = 20 + i * 110;
                return (
                  <g key={i} className="cursor-pointer" onMouseEnter={() => setHoveredDay(i)} onMouseLeave={() => setHoveredDay(null)}>
                    <circle cx={x} cy={i % 2 === 0 ? 40 : 60} r="4.5" fill="#FF2E63" stroke="#FFFFFF" strokeWidth="2" />
                    <circle cx={x} cy={i % 2 === 0 ? 100 : 90} r="4.5" fill="#05C168" stroke="#FFFFFF" strokeWidth="2" />
                  </g>
                );
              })}
            </svg>

            {/* X-Axis Day Labels */}
            <div className="flex justify-between text-[11px] font-semibold text-slate-400 mt-3 px-2">
              {weekDays.map((d, i) => (
                <span
                  key={d.day}
                  className={hoveredDay === i ? 'text-[#05C168] font-bold' : ''}
                >
                  {d.day}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ======================================================== */}
      {/* RIGHT RAIL COLUMN (4 COLS on XL)                          */}
      {/* Matches user profile, pink gradient card, recent items    */}
      {/* ======================================================== */}
      <div className="xl:col-span-4 space-y-6">
        {/* Top User Profile Header (Bell + Ceptari Tyas / SecOps) */}
        <div className="card p-4 bg-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-[#05C168] to-teal-400 flex items-center justify-center text-white font-extrabold shadow-sm">
                CT
              </div>
              <span className="w-3 h-3 bg-emerald-500 border-2 border-white rounded-full absolute -top-0.5 -right-0.5" />
            </div>
            <div>
              <h4 className="text-sm font-extrabold text-slate-800 leading-tight">Ceptari Tyas</h4>
              <p className="text-[11px] text-slate-400 font-medium">SecOps Chief Auditor</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button className="relative w-9 h-9 rounded-full bg-slate-50 hover:bg-slate-100 border border-slate-200/80 flex items-center justify-center text-slate-600 transition-colors">
              <Bell className="w-4 h-4" />
              <span className="w-2 h-2 rounded-full bg-rose-500 absolute top-2 right-2 ring-2 ring-white" />
            </button>
          </div>
        </div>

        {/* -------------------------------------------------------- */}
        {/* GORGEOUS PINK/PURPLE GRADIENT CREDIT CARD WIDGET         */}
        {/* Matches ID 122 887 552 / Your income $2,920 in reference  */}
        {/* -------------------------------------------------------- */}
        <div className="rounded-[26px] p-6 text-white bg-gradient-to-br from-[#FF4B72] via-[#FF6B8B] to-[#7952FC] shadow-[0_16px_36px_rgba(255,75,114,0.32)] relative overflow-hidden">
          {/* Glass ambient shine & bubbles */}
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-black/10 rounded-full blur-lg pointer-events-none" />

          {/* Top Row: Card ID + Mastercard style dual circles */}
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold tracking-wider opacity-90 text-white/90">
              ID 122 887 552
            </span>
            {/* Dual overlapping translucent rings */}
            <div className="flex -space-x-2">
              <div className="w-6 h-6 rounded-full bg-white/40 backdrop-blur-xs" />
              <div className="w-6 h-6 rounded-full bg-white/30 backdrop-blur-xs" />
            </div>
          </div>

          {/* Middle: Monitored Volume Header + Big Number */}
          <div className="mt-6 mb-4">
            <p className="text-xs font-semibold text-white/80">Monitored Volume</p>
            <h2 className="text-3xl font-black text-white tracking-tight mt-1">
              ${stats.total_volume.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </h2>
          </div>

          {/* Bottom Card Footer */}
          <div className="flex items-center justify-between pt-2 border-t border-white/20 text-[11px] font-medium text-white/80">
            <span>EGIS Sentinel Core</span>
            <span className="font-mono">VALID 10/26</span>
          </div>
        </div>

        {/* -------------------------------------------------------- */}
        {/* LAST TRANSACTIONS LIST (Matches reference's right rail)   */}
        {/* -------------------------------------------------------- */}
        <div className="card p-5 bg-white">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-bold text-slate-800">Last Transaction</h3>
            <button
              onClick={() => onNavigateToTab('transactions')}
              className="text-xs font-bold text-[#FF7A00] hover:text-[#E06A00] transition-colors"
            >
              See All
            </button>
          </div>

          {/* List of items with circular directional buttons */}
          <div className="space-y-3.5">
            {recentTransactions.map((tx, idx) => (
              <div
                key={tx.id}
                onClick={() => onSelectTransaction(tx.id)}
                className="flex items-center justify-between p-2.5 rounded-2xl hover:bg-slate-50 transition-all cursor-pointer group"
              >
                <div className="flex items-center gap-3">
                  {/* Circular directional button (green for in/normal, pink for risk) */}
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                      tx.isRisk
                        ? 'bg-[#FFEAEF] text-[#FF2E63]'
                        : 'bg-[#E8F8F0] text-[#05C168]'
                    }`}
                  >
                    {tx.isRisk ? (
                      <ArrowDownLeft className="w-5 h-5 stroke-[2.5]" />
                    ) : (
                      <ArrowUpRight className="w-5 h-5 stroke-[2.5]" />
                    )}
                  </div>

                  <div>
                    <h5 className="text-xs font-bold text-slate-800 group-hover:text-[#05C168] transition-colors">
                      {tx.title}
                    </h5>
                    <p className="text-[11px] text-slate-400 font-medium">{tx.account}</p>
                  </div>
                </div>

                <div className="text-right">
                  <p className="text-xs font-extrabold text-slate-800">{tx.amount}</p>
                  <p className="text-[10px] text-slate-400">{tx.date}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
