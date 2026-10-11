from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.schemas.fraud import (
    TransactionListResponse,
    TransactionDetailResponse,
    StatsResponse,
    AlertListResponse,
    AccountGraphResponse,
)
from backend.services.transaction_service import TransactionService
from backend.services.graph_service import GraphService

router = APIRouter(prefix="/api", tags=["Fraud Detection"])


@router.get("/stats", response_model=StatsResponse)
async def get_system_stats():
    tx_service = TransactionService.get_instance()
    return tx_service.get_stats()


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    limit: int = Query(default=20, ge=1, le=1000, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    search: Optional[str] = Query(default=None, description="Search by transaction, account, device, IP or merchant ID"),
    risk_level: Optional[str] = Query(default=None, pattern="^(low|medium|high|critical)$", description="Filter by risk category"),
    min_amount: Optional[float] = Query(default=None, ge=0, description="Minimum transaction amount"),
    max_amount: Optional[float] = Query(default=None, ge=0, description="Maximum transaction amount"),
    flagged_only: bool = Query(default=False, description="Filter only flagged transactions"),
    sort_by: str = Query(default="timestamp", pattern="^(timestamp|amount|risk_score|anomaly_score)$", description="Sort attribute"),
    order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort order direction"),
):
    tx_service = TransactionService.get_instance()
    return tx_service.get_transactions(
        limit=limit,
        offset=offset,
        search=search,
        risk_level=risk_level,
        min_amount=min_amount,
        max_amount=max_amount,
        flagged_only=flagged_only,
        sort_by=sort_by,
        order=order,
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionDetailResponse)
async def get_transaction_detail(transaction_id: str):
    tx_service = TransactionService.get_instance()
    detail = tx_service.get_transaction_by_id(transaction_id)
    if not detail:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction with ID '{transaction_id}' was not found.",
        )
    return detail


@router.get("/accounts/{account_id}/graph", response_model=AccountGraphResponse)
async def get_account_graph(
    account_id: str,
    limit_tx: int = Query(default=15, ge=1, le=50, description="Maximum number of connected transactions to traverse"),
):
    graph_service = GraphService.get_instance()
    res = graph_service.get_account_subgraph(account_id, limit_tx=limit_tx)
    return res


@router.get("/alerts", response_model=AlertListResponse)
async def get_fraud_alerts(
    limit: int = Query(default=50, ge=1, le=500, description="Maximum alerts to return"),
    severity: Optional[str] = Query(default=None, pattern="^(medium|high|critical)$", description="Filter by severity"),
):
    tx_service = TransactionService.get_instance()
    return tx_service.get_alerts(limit=limit, severity=severity)
