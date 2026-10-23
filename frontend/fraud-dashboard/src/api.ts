import {
  HealthResponse,
  StatsResponse,
  TransactionListResponse,
  TransactionDetailResponse,
  AccountGraphResponse,
  AlertListResponse,
  RiskDistributionResponse,
  ModelComparisonResponse,
  TransactionSummary,
  StreamStatus,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
export const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws/transactions';

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        ...options?.headers,
      },
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`HTTP ${res.status}: ${errText || res.statusText}`);
    }

    return (await res.json()) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  getHealth: () => fetchJson<HealthResponse>('/health'),
  getStats: () => fetchJson<StatsResponse>('/api/stats'),
  getTransactions: (params?: {
    limit?: number;
    offset?: number;
    search?: string;
    risk_level?: string;
    min_amount?: number;
    max_amount?: number;
    flagged_only?: boolean;
    sort_by?: string;
    order?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
      if (params.offset !== undefined) searchParams.set('offset', String(params.offset));
      if (params.search) searchParams.set('search', params.search);
      if (params.risk_level) searchParams.set('risk_level', params.risk_level);
      if (params.min_amount !== undefined) searchParams.set('min_amount', String(params.min_amount));
      if (params.max_amount !== undefined) searchParams.set('max_amount', String(params.max_amount));
      if (params.flagged_only !== undefined) searchParams.set('flagged_only', String(params.flagged_only));
      if (params.sort_by) searchParams.set('sort_by', params.sort_by);
      if (params.order) searchParams.set('order', params.order);
    }
    const query = searchParams.toString();
    return fetchJson<TransactionListResponse>(`/api/transactions${query ? `?${query}` : ''}`);
  },
  getTransactionDetail: (id: string) => fetchJson<TransactionDetailResponse>(`/api/transactions/${id}`),
  getAccountGraph: (accountId: string, limitTx = 15) =>
    fetchJson<AccountGraphResponse>(`/api/accounts/${accountId}/graph?limit_tx=${limitTx}`),
  getAlerts: (limit = 50, severity?: string) => {
    const query = severity ? `?limit=${limit}&severity=${severity}` : `?limit=${limit}`;
    return fetchJson<AlertListResponse>(`/api/alerts${query}`);
  },
  getRiskDistribution: () => fetchJson<RiskDistributionResponse>('/api/analytics/risk-distribution'),
  getModelComparison: () => fetchJson<ModelComparisonResponse>('/api/analytics/model-comparison'),
  getStreamStatus: () => fetchJson<StreamStatus>('/api/stream/status'),
  restartReplay: (delay?: number) =>
    fetchJson<StreamStatus>(`/api/stream/replay${delay !== undefined ? `?delay=${delay}` : ''}`, { method: 'POST' }),
};
