from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthDependency(BaseModel):
    status: str
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    backend: str = "running"
    dependencies: Dict[str, HealthDependency]


class TransactionSummary(BaseModel):
    transaction_id: str
    account_id: str
    transaction_amount: float
    transaction_date: str
    transaction_type: Optional[str] = None
    channel: Optional[str] = None
    location: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    merchant_id: Optional[str] = None
    
    # Phase 5 graph risk scores
    approach_a_score: Optional[float] = None
    approach_b_score: Optional[float] = None
    
    # Phase 6 ML anomaly score
    anomaly_score: Optional[float] = None
    anomaly_score_raw: Optional[float] = None
    c2gat_embedding_norm: Optional[float] = None
    
    # Unified risk categorization
    risk_level: str = "low"  # low, medium, high, critical
    is_flagged: bool = False
    
    # Explainability
    risk_reasons: Optional[str] = None
    approach_a_prominent_factors: Optional[str] = None


class TransactionListResponse(BaseModel):
    items: List[TransactionSummary]
    total: int
    limit: int
    offset: int


class TransactionDetailResponse(BaseModel):
    transaction: TransactionSummary
    graph_features: Dict[str, Any]
    explainability: Dict[str, Any]
    related_entities: Dict[str, Any]


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # Account, Transaction, Device, IP, Merchant
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str  # PERFORMED, USED_DEVICE, ORIGINATED_FROM, PAID_TO, ACCESSED_VIA, CONNECTED_FROM
    type: str


class AccountGraphResponse(BaseModel):
    account_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class AlertItem(BaseModel):
    alert_id: str
    transaction_id: str
    account_id: str
    transaction_amount: float
    transaction_date: str
    severity: str  # medium, high, critical
    detection_source: str  # graph_rules, ml_anomaly, both
    approach_b_score: Optional[float] = None
    anomaly_score: Optional[float] = None
    reasons: List[str]


class AlertListResponse(BaseModel):
    items: List[AlertItem]
    total: int


class StatsResponse(BaseModel):
    total_transactions: int
    total_volume: float
    currency: str = "USD"
    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int
    critical_risk_count: int
    flagged_count: int
    flagged_percentage: float
    unique_accounts: int
    high_risk_accounts: int
    graph_scoring_available: bool
    ml_scoring_available: bool


class RiskDistributionResponse(BaseModel):
    approach_a: Dict[str, int]
    approach_b: Dict[str, int]
    anomaly: Dict[str, int]
    total: int


class ModelComparisonResponse(BaseModel):
    metrics: Dict[str, Dict[str, float]]
    correlations: Dict[str, float]
    score_interpretation: Dict[str, str]
