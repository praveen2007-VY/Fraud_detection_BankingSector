import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "documentation" in data


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["backend"] == "running"
    assert "dependencies" in data
    assert "neo4j" in data["dependencies"]
    assert "kafka" in data["dependencies"]
    assert "ml_artifacts" in data["dependencies"]


def test_stats():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_transactions"] >= 2512
    assert data["total_volume"] > 0
    assert data["currency"] == "USD"
    assert data["unique_accounts"] > 0
    assert data["graph_scoring_available"] is True
    assert data["ml_scoring_available"] is True
    assert (data["low_risk_count"] + data["medium_risk_count"] + data["high_risk_count"] + data["critical_risk_count"]) == data["total_transactions"]


def test_transactions_pagination():
    response = client.get("/api/transactions?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert data["total"] >= 2512

    # Verify transaction schema
    first = data["items"][0]
    assert "transaction_id" in first
    assert "account_id" in first
    assert "transaction_amount" in first
    assert "approach_b_score" in first
    assert "anomaly_score" in first
    assert "risk_level" in first


def test_transactions_filtering_and_search():
    # Search by transaction ID
    res = client.get("/api/transactions?search=TX000001")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    assert items[0]["transaction_id"] == "TX000001"

    # Filter by risk level
    res_high = client.get("/api/transactions?risk_level=high")
    assert res_high.status_code == 200
    for tx in res_high.json()["items"]:
        assert tx["risk_level"] == "high"

    # Filter by amount range
    res_amt = client.get("/api/transactions?min_amount=1000&max_amount=1500")
    assert res_amt.status_code == 200
    for tx in res_amt.json()["items"]:
        assert 1000 <= tx["transaction_amount"] <= 1500


def test_transaction_sorting():
    # Sort by amount desc
    res_desc = client.get("/api/transactions?sort_by=amount&order=desc&limit=5")
    assert res_desc.status_code == 200
    items_desc = res_desc.json()["items"]
    amounts_desc = [x["transaction_amount"] for x in items_desc]
    assert amounts_desc == sorted(amounts_desc, reverse=True)

    # Sort by amount asc
    res_asc = client.get("/api/transactions?sort_by=amount&order=asc&limit=5")
    assert res_asc.status_code == 200
    items_asc = res_asc.json()["items"]
    amounts_asc = [x["transaction_amount"] for x in items_asc]
    assert amounts_asc == sorted(amounts_asc)


def test_transaction_detail():
    # Valid transaction
    res = client.get("/api/transactions/TX000001")
    assert res.status_code == 200
    data = res.json()
    assert data["transaction"]["transaction_id"] == "TX000001"
    assert "graph_features" in data
    assert "explainability" in data
    assert "related_entities" in data
    assert data["graph_features"]["shared_device_accounts"] >= 1

    # Non-existent transaction
    res_404 = client.get("/api/transactions/TX999999_NONEXISTENT")
    assert res_404.status_code == 404


def test_account_graph():
    # Valid account with known node in Neo4j
    res = client.get("/api/accounts/AC00128/graph")
    assert res.status_code == 200
    data = res.json()
    assert data["account_id"] == "AC00128"
    assert "nodes" in data
    assert "edges" in data
    if data["nodes"]:
        node_types = {n["type"] for n in data["nodes"]}
        assert "Account" in node_types


def test_alerts():
    res = client.get("/api/alerts?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    if data["items"]:
        first = data["items"][0]
        assert "alert_id" in first
        assert "detection_source" in first
        assert first["detection_source"] in ("graph_rules", "ml_anomaly", "both")


def test_risk_distribution():
    res = client.get("/api/analytics/risk-distribution")
    assert res.status_code == 200
    data = res.json()
    assert "approach_a" in data
    assert "approach_b" in data
    assert "anomaly" in data
    assert data["total"] >= 2512


def test_model_comparison():
    res = client.get("/api/analytics/model-comparison")
    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    assert "approach_a" in data["metrics"]
    assert "approach_b" in data["metrics"]
    assert "anomaly_score" in data["metrics"]
    assert "correlations" in data
    assert "pearson_approach_a_vs_b" in data["correlations"]


def test_websocket_stream():
    with client.websocket_connect("/ws/transactions") as ws:
        # Initial greeting event
        event = ws.receive_json()
        assert event["event_type"] == "system.status"
        
        # Test ping-pong
        ws.send_text("ping")
        resp = ws.receive_text()
        assert resp == "pong"
