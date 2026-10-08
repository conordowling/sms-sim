import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import psycopg
import pytest

from common import MessageResult
from conftest import fake_pool
from migrate import run_migrations
from message_record_service import MessageRecordService

SRC_DIR = Path(__file__).resolve().parent.parent / "src"


# --- unit: mocked connection, no real Postgres -----------------------------

async def test_record_batch_empty_list_is_a_noop():
    pool = fake_pool(cursor=AsyncMock())
    service = MessageRecordService()
    service.pool = pool

    await service.record_batch([])

    pool.connection.assert_not_called()


async def test_get_stats_maps_null_avg_to_zero():
    cursor = AsyncMock()
    cursor.fetchone.return_value = (0, 0, None)
    pool = fake_pool(cursor=cursor)
    service = MessageRecordService()
    service.pool = pool

    stats = await service.get_stats()

    assert stats.sent == 0
    assert stats.failed == 0
    assert stats.avg_send_time_seconds == 0.0


# --- integration: real Postgres, via a disposable testcontainer ------------

@pytest.fixture
async def record_service(postgres_dsn):
    # run_migrations() reads "migration.sql" via a relative path, which
    # only resolves when the cwd is src/ (true in Docker, not true when
    # pytest runs from the repo root) — chdir just for this call rather
    # than changing migrate.py, which is out of scope here.
    cwd = os.getcwd()
    os.chdir(SRC_DIR)
    try:
        run_migrations()
    finally:
        os.chdir(cwd)

    service = MessageRecordService(dsn=postgres_dsn)
    await service.open()
    async with service.pool.connection() as conn:
        await conn.execute("TRUNCATE TABLE message_results RESTART IDENTITY")

    yield service

    await service.close()


@pytest.mark.integration
async def test_record_batch_issues_one_executemany_round_trip(record_service):
    original = psycopg.AsyncCursor.executemany
    with patch.object(psycopg.AsyncCursor, "executemany", wraps=original, autospec=True) as spy:
        results = [
            MessageResult(success=True, send_time=0.1, content=f"msg-{i}", timestamp=float(i))
            for i in range(7)
        ]
        await record_service.record_batch(results)

    assert spy.call_count == 1

    async with record_service.pool.connection() as conn:
        row = await (await conn.execute("SELECT COUNT(*) FROM message_results")).fetchone()
    assert row[0] == 7


@pytest.mark.integration
async def test_get_stats_reflects_real_inserted_rows(record_service):
    results = [
        MessageResult(success=True, send_time=0.2, content="a", timestamp=1.0),
        MessageResult(success=True, send_time=0.4, content="b", timestamp=2.0),
        MessageResult(success=False, send_time=0.1, content="c", timestamp=3.0),
    ]
    await record_service.record_batch(results)

    stats = await record_service.get_stats()

    assert stats.sent == 2
    assert stats.failed == 1
    assert stats.avg_send_time_seconds == pytest.approx((0.2 + 0.4 + 0.1) / 3)
