import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.routes.health import router as health_router
from backend.routes.fraud import router as fraud_router
from backend.routes.analytics import router as analytics_router
from backend.services.kafka_service import KafkaService
from backend.services.graph_service import GraphService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("fraud_detection_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Fraud Detection Backend...")
    loop = asyncio.get_running_loop()
    
    # Start Kafka background consumer
    kafka_service = KafkaService.get_instance()
    kafka_service.start_consumer(loop)
    
    yield
    
    logger.info("Shutting down Fraud Detection Backend...")
    kafka_service.stop_consumer()
    GraphService.get_instance().close()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Real-Time Financial Fraud Detection & Anomaly System",
    description="Enterprise API providing graph analytics, C2GAT temporal ML anomaly scores, and Kafka streaming telemetry.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router)
app.include_router(fraud_router)
app.include_router(analytics_router)


@app.get("/")
async def root():
    return {
        "service": "Real-Time Financial Fraud Detection System",
        "status": "operational",
        "documentation": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }


@app.websocket("/ws/transactions")
async def websocket_transactions_endpoint(websocket: WebSocket):
    kafka_service = KafkaService.get_instance()
    await kafka_service.connection_manager.connect(websocket)
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "event_type": "system.status",
            "message": "Connected to real-time transaction event stream",
        })
        while True:
            # Keep connection alive; handle client pings or commands if sent
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await kafka_service.connection_manager.disconnect(websocket)
    except Exception as e:
        logger.warning("WebSocket connection exception: %s", e)
        await kafka_service.connection_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
