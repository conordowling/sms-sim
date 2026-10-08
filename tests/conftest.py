import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from testcontainers.community.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_dsn():
    """Spins up a disposable Postgres for the whole test session — no
    `docker compose up -d postgres` needed beforehand, and no risk of
    picking up stale state from a long-running dev Postgres.

    `migrate.py`'s run_migrations() has no DSN parameter — it only reads
    DATABASE_URL from the environment — so this sets that env var for the
    container's lifetime rather than just returning the DSN as a value.
    """
    with PostgresContainer(
        "postgres:17-alpine",
        username="sms",
        password="sms",
        dbname="sms_simulation",
        driver=None,  # plain postgresql:// URL, not postgresql+psycopg2://
    ) as container:
        dsn = container.get_connection_url()
        original = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = dsn
        try:
            yield dsn
        finally:
            if original is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = original


class AsyncContextManagerMock:
    """Wraps a value so `async with x:` yields it.

    psycopg's pool.connection() / conn.cursor() are plain (sync) methods
    that each return an async context manager — calling them is not
    itself awaited, only __aenter__/__aexit__ are. That's why the parent
    objects below are MagicMock (so calling .connection()/.cursor() just
    returns this object directly) rather than AsyncMock (which would wrap
    the call itself in a coroutine).
    """

    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc_info):
        return False


def fake_pool(cursor: AsyncMock) -> MagicMock:
    """A mock connection pool whose `async with pool.connection() as conn:`
    bottoms out at a `conn` wired for both ways message_record_service.py
    gets a cursor: `async with conn.cursor() as cur:` (record_batch) and
    `cursor = await conn.execute(...)` (get_stats).
    """
    conn = MagicMock()
    conn.cursor = MagicMock(return_value=AsyncContextManagerMock(cursor))
    conn.execute = AsyncMock(return_value=cursor)
    pool = MagicMock()
    pool.connection = MagicMock(return_value=AsyncContextManagerMock(conn))
    return pool
