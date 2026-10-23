from fastapi import APIRouter, HTTPException, Query
from backend.schemas.fraud import StreamStatusResponse
from backend.services.kafka_service import KafkaService
from backend.services.replay_service import ReplayService, ReplayUnavailableError

router = APIRouter(prefix="/api/stream", tags=["Stream Replay"])


@router.get("/status", response_model=StreamStatusResponse)
async def get_stream_status():
    return ReplayService.get_instance().status()


@router.post("/replay", response_model=StreamStatusResponse)
async def restart_replay(
    delay: float = Query(default=0.5, ge=0.0, le=5.0, description="Seconds between published records"),
):
    replay_service = ReplayService.get_instance()
    try:
        status = replay_service.start(delay=delay)
    except ReplayUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Tell every connected dashboard to clear its view before the first record arrives
    await KafkaService.get_instance().connection_manager.broadcast({
        "event_type": "stream.reset",
        "stream": status,
    })
    return status
