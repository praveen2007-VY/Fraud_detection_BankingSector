import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import pandas as pd
from confluent_kafka import Producer

from backend.config import (
    CLEAN_TRANSACTIONS_CSV,
    KAFKA_BROKER,
    KAFKA_INPUT_TOPIC,
    KAFKA_PROCESSED_TOPIC,
)
from backend.services.kafka_service import KafkaService
from backend.services.transaction_service import TransactionService

logger = logging.getLogger("replay_service")

REPLAY_SOURCE = "dataset_replay"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


class ReplayUnavailableError(RuntimeError):
    pass


class ReplayService:
    """
    Replays transactions_clean.csv from the first record through the real pipeline.

    Each record is published to Kafka tagged with a replay session id and sequence
    number. When a Flink job is running the records go to the input topic and flow
    through Flink; otherwise they are published straight to the processed topic.
    Either way the backend consumer performs Neo4j ingestion, scoring and the
    WebSocket broadcast for every record, exactly as for any other Kafka event.
    """

    _instance: Optional["ReplayService"] = None

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._df: Optional[pd.DataFrame] = None
        self._state: Dict[str, Any] = {}

    @classmethod
    def get_instance(cls) -> "ReplayService":
        if cls._instance is None:
            cls._instance = ReplayService()
        return cls._instance

    def _load_dataset(self) -> pd.DataFrame:
        if self._df is None:
            if not CLEAN_TRANSACTIONS_CSV.exists():
                raise ReplayUnavailableError(f"Dataset not found at {CLEAN_TRANSACTIONS_CSV}")
            self._df = pd.read_csv(CLEAN_TRANSACTIONS_CSV)
        return self._df

    def start(self, delay: float = 0.5) -> Dict[str, Any]:
        kafka_service = KafkaService.get_instance()
        broker = kafka_service.check_broker_health()
        if not broker.get("reachable"):
            raise ReplayUnavailableError(f"Kafka broker unreachable: {broker.get('error', KAFKA_BROKER)}")

        flink = kafka_service.check_flink_health()
        if flink.get("running_jobs", 0) > 0:
            route, topic = "flink", KAFKA_INPUT_TOPIC
        else:
            route, topic = "direct", KAFKA_PROCESSED_TOPIC

        df = self._load_dataset()

        with self._lock:
            self._stop_running_replay()

            session_id = uuid.uuid4().hex[:12]
            TransactionService.get_instance().reset_stream(session_id)
            self._state = {
                "session_id": session_id,
                "route": route,
                "topic": topic,
                "total_records": len(df),
                "published": 0,
                "delay_seconds": delay,
                "started_at": _utc_now(),
                "finished_publishing_at": None,
                "error": None,
            }
            self._stop_event = threading.Event()
            self._thread = threading.Thread(
                target=self._publish_loop,
                args=(session_id, df, topic, delay, self._stop_event),
                daemon=True,
                name=f"ReplayPublisher-{session_id}",
            )
            self._thread.start()

        logger.info(
            "[REPLAY] Session %s started: %d records via %s (topic '%s', delay %.2fs)",
            session_id, len(df), route, topic, delay,
        )
        return self.status()

    def stop(self):
        with self._lock:
            self._stop_running_replay()

    def _stop_running_replay(self):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=5.0)

    def _publish_loop(self, session_id: str, df: pd.DataFrame, topic: str, delay: float, stop_event: threading.Event):
        producer = Producer({"bootstrap.servers": KAFKA_BROKER, "linger.ms": 5})
        try:
            for seq, (_, row) in enumerate(df.iterrows(), start=1):
                if stop_event.is_set():
                    logger.info("[REPLAY] Session %s stopped after %d records", session_id, seq - 1)
                    return

                record = row.to_dict()
                record["replay_session_id"] = session_id
                record["replay_sequence"] = seq
                if topic == KAFKA_PROCESSED_TOPIC:
                    record["processing_timestamp"] = _utc_now()

                # One key per session keeps every record on the same partition, preserving order
                producer.produce(topic, key=session_id, value=json.dumps(record, default=str))
                producer.poll(0)
                self._state["published"] = seq

                if delay > 0:
                    stop_event.wait(delay)

            producer.flush(10.0)
            self._state["finished_publishing_at"] = _utc_now()
            logger.info("[REPLAY] Session %s finished publishing %d records", session_id, len(df))
        except Exception as e:
            logger.error("[REPLAY] Session %s failed: %s", session_id, e)
            self._state["error"] = str(e)
        finally:
            producer.flush(5.0)

    def status(self) -> Dict[str, Any]:
        tx_service = TransactionService.get_instance()
        if tx_service.stream_mode != "replay":
            return {
                "mode": "snapshot",
                "source": "dataset_snapshot",
                "total_records": len(tx_service.transactions),
                "processed": len(tx_service.transactions),
            }
        return {
            "mode": "replay",
            "source": REPLAY_SOURCE,
            "running": bool(self._thread and self._thread.is_alive()),
            "processed": tx_service.stream_processed_count,
            **{k: v for k, v in self._state.items() if k != "topic"},
        }
