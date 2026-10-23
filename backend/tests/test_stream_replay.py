import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.graph_service import GraphService
from backend.services.transaction_service import TransactionService

client = TestClient(app)


@pytest.fixture
def tx_service(monkeypatch):
    service = TransactionService.get_instance()
    monkeypatch.setattr(GraphService.get_instance(), "ingest_transaction", lambda record: None)
    saved = (service.transactions, service.tx_by_id, service.stream_mode, service.stream_session_id, service.stream_processed_count)
    yield service
    (service.transactions, service.tx_by_id, service.stream_mode,
     service.stream_session_id, service.stream_processed_count) = saved


def _record(tx_id, session_id, seq):
    return {
        "TransactionID": tx_id,
        "AccountID": "AC00001",
        "TransactionAmount": 120.5,
        "TransactionDate": "2023-04-11 16:29:14",
        "TransactionType": "Debit",
        "replay_session_id": session_id,
        "replay_sequence": seq,
    }


def test_stream_status_defaults_to_snapshot():
    res = client.get("/api/stream/status")
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "snapshot"
    assert data["source"] == "dataset_snapshot"


def test_reset_starts_stats_from_zero(tx_service):
    tx_service.reset_stream("session-a")
    stats = client.get("/api/stats").json()
    assert stats["total_transactions"] == 0

    tx_service.add_or_update_live_transaction(_record("TX000001", "session-a", 1))
    stats = client.get("/api/stats").json()
    assert stats["total_transactions"] == 1
    assert tx_service.stream_processed_count == 1

    status = client.get("/api/stream/status").json()
    assert status["mode"] == "replay"
    assert status["processed"] == 1


def test_records_from_superseded_session_are_dropped(tx_service):
    tx_service.reset_stream("session-new")
    assert tx_service.add_or_update_live_transaction(_record("TX000002", "session-old", 5)) is None
    assert tx_service.transactions == []

    enriched = tx_service.add_or_update_live_transaction(_record("TX000002", "session-new", 1))
    assert enriched["stream_source"] == "dataset_replay"
    assert enriched["replay_sequence"] == 1


def test_detail_lookup_falls_back_to_dataset_after_reset(tx_service):
    tx_service.reset_stream("session-b")
    res = client.get("/api/transactions/TX000003")
    assert res.status_code == 200
