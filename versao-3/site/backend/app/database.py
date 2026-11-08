from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings
from .config import PROJECT_ROOT


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id BIGSERIAL PRIMARY KEY,
        username VARCHAR(80) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS components (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(160) NOT NULL,
        category VARCHAR(100),
        code VARCHAR(100),
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS component_images (
        id BIGSERIAL PRIMARY KEY,
        component_id BIGINT NOT NULL REFERENCES components(id) ON DELETE CASCADE,
        filename TEXT NOT NULL,
        original_name TEXT,
        content_type VARCHAR(100),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recognition_events (
        id BIGSERIAL PRIMARY KEY,
        component_id BIGINT REFERENCES components(id) ON DELETE SET NULL,
        detected_name VARCHAR(160),
        confidence NUMERIC(5,4),
        status VARCHAR(30) NOT NULL DEFAULT 'pending',
        image_filename TEXT,
        device_id VARCHAR(100),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_events_created_at ON recognition_events(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_component_images_component ON component_images(component_id)",
]


class Database:
    def __init__(self) -> None:
        self.pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row},
            open=False,
        )

    def open(self) -> None:
        self.pool.open(wait=True)
        with self.connection() as conn:
            # App e worker podem iniciar juntos: serializar ANTES de qualquer DDL.
            conn.execute("SELECT pg_advisory_xact_lock(681923003)")
            for statement in SCHEMA_STATEMENTS:
                conn.execute(statement)
            # Migrações versionadas registradas, transacionais e apenas aditivas.
            conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
            for path in sorted((PROJECT_ROOT / "database" / "migrations").glob("*.sql")):
                if not conn.execute("SELECT name FROM schema_migrations WHERE name=%s", (path.name,)).fetchone():
                    conn.execute(path.read_text(encoding="utf-8"))
                    conn.execute("INSERT INTO schema_migrations(name) VALUES (%s)", (path.name,))

    def close(self) -> None:
        self.pool.close()

    @contextmanager
    def connection(self):
        with self.pool.connection() as conn:
            with conn.transaction():
                yield conn


db = Database()

