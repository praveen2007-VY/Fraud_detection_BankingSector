from fastapi import APIRouter
from backend.schemas.fraud import HealthResponse, HealthDependency
from backend.services.graph_service import GraphService
from backend.services.kafka_service import KafkaService
from backend.services.scoring_service import ScoringService

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def check_health():
    graph_service = GraphService.get_instance()
    kafka_service = KafkaService.get_instance()
    scoring_service = ScoringService.get_instance()

    neo4j_ok = graph_service.verify_connectivity()
    kafka_health = kafka_service.check_broker_health()
    ml_status = scoring_service.check_ml_artifacts_status()

    dependencies = {
        "neo4j": HealthDependency(
            status="healthy" if neo4j_ok else "unreachable",
            message="Neo4j graph database connected" if neo4j_ok else "Cannot connect to Neo4j instance",
        ),
        "kafka": HealthDependency(
            status="healthy" if kafka_health.get("reachable") else "unreachable",
            message="Kafka broker connected" if kafka_health.get("reachable") else kafka_health.get("error", "Cannot connect to Kafka broker"),
            details=kafka_health,
        ),
        "ml_artifacts": HealthDependency(
            status="healthy" if ml_status.get("model_checkpoint_present") and ml_status.get("scores_present") else "degraded",
            message="All C2GAT model checkpoints and scores loaded" if ml_status.get("scores_present") else "Some ML artifacts missing",
            details=ml_status,
        ),
    }

    overall_status = "healthy"
    if not neo4j_ok or not kafka_health.get("reachable"):
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        backend="running",
        dependencies=dependencies,
    )
