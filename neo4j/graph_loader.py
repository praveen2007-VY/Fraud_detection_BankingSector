"""
graph_loader.py
===============
Phase 4: Kafka to Neo4j Graph Ingestion Service

Consumes real processed transactions from Kafka topic 'processed_transactions'
and merges entities and relationships into Neo4j graph database.

Entities:
  - (:Account {account_id})
  - (:Device {device_id})
  - (:IP {ip_address})
  - (:Merchant {merchant_id})
  - (:Transaction {transaction_id, ...})

Relationships:
  - (Account)-[:PERFORMED]->(Transaction)
  - (Transaction)-[:USED_DEVICE]->(Device)
  - (Transaction)-[:ORIGINATED_FROM]->(IP)
  - (Transaction)-[:PAID_TO]->(Merchant)
  - (Account)-[:ACCESSED_VIA]->(Device)
  - (Account)-[:CONNECTED_FROM]->(IP)
"""

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

# pyrefly: ignore [missing-import]
from confluent_kafka import Consumer, KafkaError, KafkaException, TopicPartition 
from neo4j import GraphDatabase, Driver

# Ensure workspace root is in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config.config import (
    KAFKA_BROKER,
    KAFKA_PROCESSED_TOPIC,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("graph_loader")

# Idempotent Cypher query to ingest one transaction record
INGEST_CYPHER = """
MERGE (a:Account {account_id: $account_id})
ON CREATE SET 
    a.customer_occupation = $customer_occupation,
    a.customer_age = $customer_age

MERGE (d:Device {device_id: $device_id})

MERGE (i:IP {ip_address: $ip_address})

MERGE (m:Merchant {merchant_id: $merchant_id})

MERGE (t:Transaction {transaction_id: $transaction_id})
ON CREATE SET 
    t.transaction_amount = $transaction_amount,
    t.transaction_date = $transaction_date,
    t.transaction_type = $transaction_type,
    t.channel = $channel,
    t.location = $location,
    t.transaction_duration = $transaction_duration,
    t.login_attempts = $login_attempts,
    t.account_balance = $account_balance,
    t.customer_age = $customer_age,
    t.customer_occupation = $customer_occupation,
    t.previous_transaction_date = $previous_transaction_date,
    t.processing_timestamp = $processing_timestamp

MERGE (a)-[:PERFORMED]->(t)
MERGE (t)-[:USED_DEVICE]->(d)
MERGE (t)-[:ORIGINATED_FROM]->(i)
MERGE (t)-[:PAID_TO]->(m)
MERGE (a)-[:ACCESSED_VIA]->(d)
MERGE (a)-[:CONNECTED_FROM]->(i)
"""


def parse_record(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and cast transaction fields for Neo4j ingestion."""
    return {
        "account_id": str(data.get("AccountID", "")),
        "device_id": str(data.get("DeviceID", "")),
        "ip_address": str(data.get("IP Address", "")),
        "merchant_id": str(data.get("MerchantID", "")),
        "transaction_id": str(data.get("TransactionID", "")),
        "transaction_amount": float(data.get("TransactionAmount", 0.0)),
        "transaction_date": str(data.get("TransactionDate", "")),
        "transaction_type": str(data.get("TransactionType", "")),
        "channel": str(data.get("Channel", "")),
        "location": str(data.get("Location", "")),
        "transaction_duration": int(data.get("TransactionDuration", 0)),
        "login_attempts": int(data.get("LoginAttempts", 0)),
        "account_balance": float(data.get("AccountBalance", 0.0)),
        "customer_age": int(data.get("CustomerAge", 0)),
        "customer_occupation": str(data.get("CustomerOccupation", "")),
        "previous_transaction_date": str(data.get("PreviousTransactionDate", "")),
        "processing_timestamp": str(data.get("processing_timestamp", "")),
    }


def ingest_record(session, params: Dict[str, Any]) -> None:
    """Ingest a single record into Neo4j using an open session."""
    session.run(INGEST_CYPHER, params)


def run_loader(
    max_records: Optional[int] = 10,
    poll_timeout: float = 5.0,
    max_idle_seconds: float = 30.0,
    from_offset: Optional[int] = None,
) -> int:
    """
    Consume records from Kafka processed_transactions and ingest into Neo4j.
    Stops after max_records are written, or on idle timeout.
    """
    logger.info("=" * 60)
    logger.info("  PHASE 4: Kafka -> Neo4j Graph Loader")
    logger.info("=" * 60)
    logger.info("  Broker      : %s", KAFKA_BROKER)
    logger.info("  Topic       : %s", KAFKA_PROCESSED_TOPIC)
    logger.info("  Group ID    : neo4j-graph-loader")
    logger.info("  Neo4j URI   : %s", NEO4J_URI)
    logger.info("  Max Records : %s", max_records if max_records is not None else "Unlimited")
    if from_offset is not None:
        logger.info("  From Offset : %d", from_offset)

    # Connect to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
        logger.info("[OK] Neo4j connection verified.")
    except Exception as exc:
        logger.error("[FAIL] Could not connect to Neo4j: %s", exc)
        driver.close()
        raise

    # Configure Kafka Consumer
    consumer_config = {
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": "neo4j-graph-loader",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }
    consumer = Consumer(consumer_config)
    if from_offset is not None:
        consumer.assign([TopicPartition(KAFKA_PROCESSED_TOPIC, 0, from_offset)])
        logger.info("[OK] Kafka consumer assigned to '%s' at offset %d.", KAFKA_PROCESSED_TOPIC, from_offset)
    else:
        consumer.subscribe([KAFKA_PROCESSED_TOPIC])
        logger.info("[OK] Kafka consumer subscribed to '%s'.", KAFKA_PROCESSED_TOPIC)

    written_count = 0
    last_message_time = time.time()

    with driver.session() as session:
        try:
            while True:
                if max_records is not None and written_count >= max_records:
                    logger.info("Target record count (%d) reached. Stopping loader.", max_records)
                    break

                msg = consumer.poll(timeout=poll_timeout)
                if msg is None:
                    idle_time = time.time() - last_message_time
                    if idle_time > max_idle_seconds:
                        logger.warning("No messages received for %.1fs. Stopping loader.", idle_time)
                        break
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    raise KafkaException(msg.error())

                try:
                    raw_data = json.loads(msg.value().decode("utf-8"))
                except Exception as exc:
                    logger.error("[PARSE-ERROR] Could not decode JSON: %s", exc)
                    continue

                params = parse_record(raw_data)
                ingest_record(session, params)
                written_count += 1
                last_message_time = time.time()

                if written_count % 250 == 0 or written_count == 1 or written_count == max_records:
                    logger.info(
                        "[INGESTED %d] TxID=%s Account=%s Amount=%.2f Merchant=%s",
                        written_count,
                        params["transaction_id"],
                        params["account_id"],
                        params["transaction_amount"],
                        params["merchant_id"],
                    )

        finally:
            consumer.close()
            driver.close()
            logger.info("Kafka consumer and Neo4j driver closed cleanly.")

    logger.info("Graph loader completed. Ingested %d records into Neo4j.", written_count)
    return written_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kafka to Neo4j Graph Loader")
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Maximum records to process before stopping (default: None/all)",
    )
    parser.add_argument(
        "--from-offset",
        type=int,
        default=None,
        help="Kafka topic offset to start consuming from (default: resume from committed)",
    )
    args = parser.parse_args()
    count = run_loader(max_records=args.max_records, from_offset=args.from_offset)
    print(f"\nSuccessfully loaded {count} records into Neo4j.")
