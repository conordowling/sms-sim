from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import monitor
from common import MessageStats


@pytest.fixture
def mock_record_service():
    service = AsyncMock()
    service.get_stats.return_value = MessageStats(sent=10, failed=2, avg_send_time_seconds=0.15)
    return service


@pytest.fixture
def mock_producer():
    return AsyncMock()


@pytest.fixture
def client(mock_record_service, mock_producer):
    # Patch the classes monitor.py's lifespan constructs, so the real
    # lifespan code runs unmodified but never touches real Postgres/Kafka.
    with (
        patch("monitor.MessageRecordService", return_value=mock_record_service),
        patch("monitor.Producer", return_value=mock_producer),
    ):
        with TestClient(monitor.app) as test_client:
            yield test_client


def test_get_stats_returns_shape_from_record_service(client):
    response = client.get("/stats")

    assert response.status_code == 200
    assert response.json() == {"sent": 10, "failed": 2, "avg_send_time_seconds": 0.15}


def test_post_produce_calls_producer_run_and_returns_count(client, mock_producer):
    response = client.post("/produce", json={"num_messages": 250})

    assert response.status_code == 200
    assert response.json() == {"num_messages": 250}
    mock_producer.run.assert_awaited_once_with(250)


@pytest.mark.parametrize("num_messages", [0, -5, 100_001])
def test_post_produce_rejects_out_of_range_num_messages(client, num_messages):
    response = client.post("/produce", json={"num_messages": num_messages})

    assert response.status_code == 422


def test_post_produce_returns_502_when_producer_raises(client, mock_producer):
    mock_producer.run.side_effect = RuntimeError("kafka is down")

    response = client.post("/produce", json={"num_messages": 10})

    assert response.status_code == 502
    assert "kafka is down" in response.json()["detail"]


def test_lifespan_opens_and_starts_on_entry_closes_and_stops_on_exit(mock_record_service, mock_producer):
    with (
        patch("monitor.MessageRecordService", return_value=mock_record_service),
        patch("monitor.Producer", return_value=mock_producer),
    ):
        with TestClient(monitor.app):
            mock_record_service.open.assert_awaited_once()
            mock_producer.start.assert_awaited_once()
            mock_record_service.close.assert_not_awaited()
            mock_producer.stop.assert_not_awaited()

        mock_record_service.close.assert_awaited_once()
        mock_producer.stop.assert_awaited_once()
