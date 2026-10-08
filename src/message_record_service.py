import psycopg
from psycopg_pool import AsyncConnectionPool
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from common import MessageResult, MessageStats, get_dsn

# I'm using simple templated SQL statements instead of a full ORM such as sql-alchemy
# given the limited scope of the exercise.
_INSERT_SQL = """
    INSERT INTO message_results (content, success, send_time, timestamp)
    VALUES (%s, %s, %s, %s)
"""

# This query is currently implemented using a full table scan. If the table got larger and
# latency or database usage was increasing, I would look to move these standardized measurements
# to counters in a Redis store.
_STATS_SQL = """
    SELECT
        COUNT(*) FILTER (WHERE success) AS sent,
        COUNT(*) FILTER (WHERE NOT success) AS failed,
        AVG(send_time) AS avg_send_time
    FROM message_results
"""

# Simple retry configuration using tenacity in case the database blips, this class can recover
# from a transient failure without callers needing to handle it.
_RETRY_ON_TRANSIENT_ERROR = dict(
    retry=retry_if_exception_type(psycopg.OperationalError),
    wait=wait_exponential(multiplier=0.2, max=2),
    stop=stop_after_attempt(5),
)


class MessageRecordService:
    """Async Postgres access shared by the Sender (writes) and Monitor (reads)."""

    def __init__(self, dsn: str | None = None, min_size: int = 1, max_size: int = 2):
        self._dsn = dsn or get_dsn()
        self._min_size = min_size
        self._max_size = max_size
        self.pool: AsyncConnectionPool | None = None

    async def open(self) -> None:
        self.pool = AsyncConnectionPool(
            conninfo=self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
            open=False,
        )
        await self.pool.open()

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()

    @retry(**_RETRY_ON_TRANSIENT_ERROR)
    async def record_batch(self, results: list[MessageResult]) -> None:
        """Insert a batch of results in a single round trip."""
        if not results:
            return

        rows = [(r.content, r.success, r.send_time, r.timestamp) for r in results]
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(_INSERT_SQL, rows)

    @retry(**_RETRY_ON_TRANSIENT_ERROR)
    async def get_stats(self) -> MessageStats:
        """Get stats about the message records for the monitor."""
        async with self.pool.connection() as conn:
            cursor = await conn.execute(_STATS_SQL)
            sent, failed, avg_send_time = await cursor.fetchone()

        return MessageStats(
            sent=sent or 0,
            failed=failed or 0,
            avg_send_time_seconds=float(avg_send_time or 0.0),
        )
