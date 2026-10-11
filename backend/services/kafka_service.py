import asyncio
import json
import logging
import threading
import time
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket
from confluent_kafka import Consumer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient

from backend.config import KAFKA_BROKER, KAFKA_PROCESSED_TOPIC
from backend.services.transaction_service import TransactionService

logger = logging.getLogger("kafka_service")


class ConnectionManager:
    """Manages active WebSocket client connections for real-time streaming."""
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info("WebSocket client connected. Total clients: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total clients: %d", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]):
        async with self._lock:
            disconnected = []
            payload = json.dumps(message)
            for connection in self.active_connections:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.warning("Failed to send WebSocket message: %s", e)
                    disconnected.append(connection)

            for dead_conn in disconnected:
                self.active_connections.discard(dead_conn)


class KafkaService:
    _instance: Optional["KafkaService"] = None

    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def get_instance(cls) -> "KafkaService":
        if cls._instance is None:
            cls._instance = KafkaService()
        return cls._instance

    def check_broker_health(self) -> Dict[str, Any]:
        """Independent non-blocking check of Kafka broker availability."""
        try:
            admin = AdminClient({"bootstrap.servers": KAFKA_BROKER, "socket.timeout.ms": 2000})
            md = admin.list_topics(timeout=3.0)
            topics = list(md.topics.keys())
            return {
                "reachable": True,
                "broker": KAFKA_BROKER,
                "topics_found": topics,
                "processed_topic_exists": KAFKA_PROCESSED_TOPIC in topics,
            }
        except Exception as e:
            return {
                "reachable": False,
                "broker": KAFKA_BROKER,
                "error": str(e),
            }

    def start_consumer(self, loop: asyncio.AbstractEventLoop):
        if self.running:
            return
        self.running = True
        self._loop = loop
        self._thread = threading.Thread(target=self._consume_loop, daemon=True, name="KafkaConsumerThread")
        self._thread.start()
        logger.info("Started Kafka background consumer thread for topic '%s'", KAFKA_PROCESSED_TOPIC)

    def stop_consumer(self):
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
            logger.info("Stopped Kafka consumer thread.")

    def _consume_loop(self):
        conf = {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": "fastapi-dashboard-consumer",
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
            "socket.timeout.ms": 5000,
        }

        consumer = None
        tx_service = TransactionService.get_instance()

        while self.running:
            try:
                if consumer is None:
                    consumer = Consumer(conf)
                    consumer.subscribe([KAFKA_PROCESSED_TOPIC])
                    logger.info("Kafka consumer subscribed to '%s'", KAFKA_PROCESSED_TOPIC)

                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.warning("Kafka consumer error: %s", msg.error())
                    time.sleep(1.0)
                    continue

                raw_val = msg.value().decode("utf-8")
                data = json.loads(raw_val)

                # Process transaction and join scores
                enriched = tx_service.add_or_update_live_transaction(data)

                # Broadcast WebSocket event
                event = {
                    "event_type": "transaction.processed",
                    "timestamp": enriched.get("processing_timestamp") or time.strftime("%Y-%m-%d %H:%M:%S"),
                    "data": enriched,
                }

                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.connection_manager.broadcast(event),
                        self._loop,
                    )

            except Exception as e:
                logger.error("Exception in Kafka consume loop: %s", e)
                time.sleep(2.0)

        if consumer is not None:
            try:
                consumer.close()
            except Exception:
                pass
