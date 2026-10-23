export interface TransactionSummary {
  transaction_id: string;
  account_id: string;
  transaction_amount: number;
  transaction_date: string;
  transaction_type?: string;
  channel?: string;
  location?: string;
  device_id?: string;
  ip_address?: string;
  merchant_id?: string;
  approach_a_score?: number | null;
  approach_b_score?: number | null;
  anomaly_score?: number | null;
  anomaly_score_raw?: number | null;
  c2gat_embedding_norm?: number | null;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  is_flagged: boolean;
  risk_reasons?: string | null;
  approach_a_prominent_factors?: string | null;
  is_live?: boolean;
  processing_timestamp?: string;
  stream_source?: 'dataset_replay' | 'kafka';
  replay_session_id?: string | null;
  replay_sequence?: number | null;
}

// 'snapshot': preloaded dataset with precomputed scores (nothing streamed yet)
// 'replay': only records the pipeline has processed since the last replay started
export interface StreamStatus {
  mode: 'snapshot' | 'replay';
  source: 'dataset_snapshot' | 'dataset_replay';
  session_id?: string | null;
  route?: 'flink' | 'direct' | null;
  running?: boolean;
  total_records: number;
  published?: number;
  processed: number;
  delay_seconds?: number;
  started_at?: string | null;
  finished_publishing_at?: string | null;
  error?: string | null;
}

export interface TransactionListResponse {
  items: TransactionSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface TransactionDetailResponse {
  transaction: TransactionSummary;
  graph_features: {
    shared_device_accounts: number;
    shared_ip_accounts: number;
    merchant_cluster_accounts: number;
    rapid_velocity_count_24h: number;
    account_network_sprawl_degree: number;
  };
  explainability: {
    risk_reasons: string[];
    prominent_factors: string[];
    approach_a_score?: number | null;
    approach_b_score?: number | null;
    anomaly_score?: number | null;
    anomaly_score_raw?: number | null;
    c2gat_embedding_norm?: number | null;
  };
  related_entities: {
    account_id: string;
    device_id: string;
    ip_address: string;
    merchant_id: string;
    location: string;
    channel: string;
  };
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'Account' | 'Transaction' | 'Device' | 'IP' | 'Merchant';
  properties?: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: string;
}

export interface AccountGraphResponse {
  account_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AlertItem {
  alert_id: string;
  transaction_id: string;
  account_id: string;
  transaction_amount: number;
  transaction_date: string;
  severity: 'medium' | 'high' | 'critical';
  detection_source: 'graph_rules' | 'ml_anomaly' | 'both';
  approach_b_score?: number | null;
  anomaly_score?: number | null;
  reasons: string[];
}

export interface AlertListResponse {
  items: AlertItem[];
  total: number;
}

export interface StatsResponse {
  total_transactions: number;
  total_volume: number;
  currency: string;
  low_risk_count: number;
  medium_risk_count: number;
  high_risk_count: number;
  critical_risk_count: number;
  flagged_count: number;
  flagged_percentage: number;
  unique_accounts: number;
  high_risk_accounts: number;
  graph_scoring_available: boolean;
  ml_scoring_available: boolean;
}

export interface RiskDistributionResponse {
  approach_a: Record<string, number>;
  approach_b: Record<string, number>;
  anomaly: Record<string, number>;
  total: number;
}

export interface ModelComparisonResponse {
  metrics: Record<string, {
    min: number;
    max: number;
    mean: number;
    median: number;
    p75: number;
    p90: number;
    std_dev: number;
  }>;
  correlations: Record<string, number>;
  score_interpretation: Record<string, string>;
}

export interface DependencyStatus {
  status: 'healthy' | 'degraded' | 'unreachable';
  message?: string;
  details?: any;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  backend: string;
  dependencies: {
    neo4j: DependencyStatus;
    kafka: DependencyStatus;
    flink?: DependencyStatus;
    ml_artifacts: DependencyStatus;
  };
}
