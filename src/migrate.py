import psycopg

from common import get_dsn


def run_migrations() -> None:
    """
    Apply the database migration. Keeping it simple for this exercise rather than using a migration management
    tool such as alembic.
    """
    with psycopg.connect(get_dsn(), autocommit=True) as conn:
        conn.execute(open("migration.sql").read())
        print(f"applied migration")

if __name__ == "__main__":
    run_migrations()
