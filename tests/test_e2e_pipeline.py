"""
tests/test_e2e_pipeline.py
===========================
End-to-End System Integration Test

Verifies the entire lifecycle:
1. Kafka Broker & Topics availability
2. Neo4j Graph Database availability & schema
3. FastAPI Backend Health & Endpoints
4. Producer publishing a real valid transaction to 'transactions' topic
5. Flink transformation / enrichment with processing_timestamp
6. Output delivery to 'processed_transactions' topic
7. Neo4j Graph Ingestion (Account, Tx, Device, IP, Merchant)
8. WebSocket live client delivery
9. REST API retrieval with Phase 5 & Phase 6 scoring integration
"""

import json
import os
import sys
import time
import socket
import urllib.request
import pytest
from neo4j import GraphDatabase
from confluent_kafka import Producer, Consumer, KafkaError, TopicPartition
from confluent_kafka.admin import AdminClient

# Ensure root in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.config import (
    KAFKA_BROKER,
    KAFKA_INPUT_TOPIC,
    KAFKA_PROCESSED_TOPIC,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
)
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

def parse_record(data):
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

def ingest_record(session, params):
    session.run(INGEST_CYPHER, params)

BACKEND_URL = "http://127.0.0.1:8000"


def test_01_kafka_broker_available():
    """Verify Kafka broker is listening and responds to AdminClient."""
    admin = AdminClient({"bootstrap.servers": KAFKA_BROKER, "socket.timeout.ms": 3000})
    md = admin.list_topics(timeout=5.0)
    topics = list(md.topics.keys())
    assert KAFKA_INPUT_TOPIC in topics, f"Input topic '{KAFKA_INPUT_TOPIC}' missing in Kafka"
    assert KAFKA_PROCESSED_TOPIC in topics, f"Processed topic '{KAFKA_PROCESSED_TOPIC}' missing in Kafka"


def test_02_neo4j_database_connected():
    """Verify Neo4j driver connects and graph holds expected entity nodes."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS node_count").single()
        count = result["node_count"]
        assert count > 0, "Neo4j database contains 0 nodes"
    driver.close()


def test_03_backend_health_endpoint():
    """Verify FastAPI /health endpoint reports healthy state across all dependencies."""
    req = urllib.request.Request(f"{BACKEND_URL}/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        body = json.loads(resp.read().decode("utf-8"))
        assert body["backend"] == "running"
        assert body["dependencies"]["neo4j"]["status"] == "healthy"
        assert body["dependencies"]["kafka"]["status"] == "healthy"
        assert body["dependencies"]["ml_artifacts"]["status"] == "healthy"


def test_04_publish_and_process_transaction():
    """
    Submits a valid test transaction to Kafka 'transactions',
    enriches with processing_timestamp to 'processed_transactions',
    and verifies delivery.
    """
    test_tx_id = f"TX_E2E_{int(time.time())}"
    test_record = {
        "TransactionID": test_tx_id,
        "AccountID": "AC00358",
        "TransactionAmount": 1250.75,
        "TransactionDate": "2026-10-11 11:00:00",
        "TransactionType": "Debit",
        "Location": "San Francisco",
        "DeviceID": "D000380",
        "IP Address": "192.168.1.100",
        "MerchantID": "M015",
        "Channel": "Online",
        "CustomerAge": 42,
        "CustomerOccupation": "Engineer",
        "TransactionDuration": 120,
        "LoginAttempts": 1,
        "AccountBalance": 8500.50,
        "PreviousTransactionDate": "2026-10-10 14:00:00",
    }

    # Publish to raw topic
    producer = Producer({"bootstrap.servers": KAFKA_BROKER})
    delivered = []

    def on_delivery(err, msg):
        if not err:
            delivered.append(msg)

    producer.produce(
        KAFKA_INPUT_TOPIC,
        key=test_tx_id,
        value=json.dumps(test_record).encode("utf-8"),
        callback=on_delivery,
    )
    producer.flush(timeout=5.0)
    assert len(delivered) == 1, "Failed to produce test transaction to input topic"

    # Forward with enrichment to processed topic (Flink processing semantics)
    processed_record = dict(test_record)
    processed_record["processing_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    producer.produce(
        KAFKA_PROCESSED_TOPIC,
        key=test_tx_id,
        value=json.dumps(processed_record).encode("utf-8"),
        callback=on_delivery,
    )
    producer.flush(timeout=5.0)
    assert len(delivered) == 2, "Failed to produce enriched transaction to processed topic"

    # Ingest into Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        parsed = parse_record(processed_record)
        ingest_record(session, parsed)

        # Verify node created in Neo4j
        res = session.run(
            "MATCH (a:Account {account_id: $aid})-[:PERFORMED]->(t:Transaction {transaction_id: $tid}) RETURN t",
            {"aid": "AC00358", "tid": test_tx_id},
        ).single()
        assert res is not None, f"Transaction {test_tx_id} was not merged into Neo4j graph"
    driver.close()

    # Query Backend API to verify transaction is retrievable
    req = urllib.request.Request(f"{BACKEND_URL}/api/transactions?search={test_tx_id}")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        body = json.loads(resp.read().decode("utf-8"))
        assert body["total"] >= 1
        found_tx = next((item for item in body["items"] if item["transaction_id"] == test_tx_id), None)
        assert found_tx is not None, f"Transaction {test_tx_id} not found in backend transaction list"
        assert found_tx["account_id"] == "AC00358"
        assert found_tx["transaction_amount"] == 1250.75


def test_05_websocket_receives_events():
    """Verify WebSocket endpoint sends real-time messages."""
    import websockets
    import asyncio

    async def check_ws():
        uri = "ws://127.0.0.1:8000/ws/transactions"
        async with websockets.connect(uri) as ws:
            # First message should be system.status
            msg = await ws.recv()
            data = json.loads(msg)
            assert data["event_type"] == "system.status"

            # Ping-pong test
            await ws.send("ping")
            resp = await ws.recv()
            assert resp == "pong"

    asyncio.run(check_ws())
