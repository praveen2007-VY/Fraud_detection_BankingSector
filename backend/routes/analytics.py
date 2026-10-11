from fastapi import APIRouter
from backend.schemas.fraud import RiskDistributionResponse, ModelComparisonResponse
from backend.services.transaction_service import TransactionService
from backend.services.scoring_service import ScoringService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/risk-distribution", response_model=RiskDistributionResponse)
async def get_risk_distribution():
    tx_service = TransactionService.get_instance()
    return tx_service.get_risk_distribution()


@router.get("/model-comparison", response_model=ModelComparisonResponse)
async def get_model_comparison():
    scoring_service = ScoringService.get_instance()
    res = scoring_service.compute_model_comparison()
    return ModelComparisonResponse(**res)
