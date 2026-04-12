"""
Single DuckDB connection for the entire backend.
All persistent data lives here: users, workspaces, history, feedback,
conversation turns, AND the uploaded dataset tables.
Thread safety via threading.Lock (FastAPI sync handlers run in thread pool).
"""

import threading
from pathlib import Path

import duckdb

from app.core.config import settings


class Database:
    def __init__(self) -> None:
        db_path = Path(settings.duckdb_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)

        self._conn = duckdb.connect(str(db_path))
        self._lock = threading.Lock()
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        stmts = [
            # Users
            """
            CREATE TABLE IF NOT EXISTS users (
                id          VARCHAR PRIMARY KEY,
                email       VARCHAR UNIQUE NOT NULL,
                username    VARCHAR NOT NULL,
                password_hash VARCHAR NOT NULL,
                role        VARCHAR DEFAULT 'analyst',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Workspaces — one per uploaded dataset, scoped to a user
            """
            CREATE TABLE IF NOT EXISTS workspaces (
                id          VARCHAR PRIMARY KEY,
                user_id     VARCHAR NOT NULL,
                name        VARCHAR NOT NULL,
                description VARCHAR DEFAULT '',
                file_path   VARCHAR,
                table_name  VARCHAR,
                columns     VARCHAR,
                row_count   INTEGER DEFAULT 0,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Query history — every question asked in a workspace
            """
            CREATE TABLE IF NOT EXISTS query_history (
                id              VARCHAR PRIMARY KEY,
                workspace_id    VARCHAR NOT NULL,
                user_id         VARCHAR NOT NULL,
                query           TEXT NOT NULL,
                sql_generated   TEXT,
                narrative       TEXT,
                chart_type      VARCHAR,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Conversation turns — multi-turn context per workspace
            """
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id              VARCHAR PRIMARY KEY,
                workspace_id    VARCHAR NOT NULL,
                user_id         VARCHAR NOT NULL,
                role            VARCHAR NOT NULL,
                content         TEXT NOT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Feedback — thumbs up/down on any query
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id                  VARCHAR PRIMARY KEY,
                query_history_id    VARCHAR NOT NULL,
                user_id             VARCHAR NOT NULL,
                was_helpful         BOOLEAN NOT NULL,
                correction          TEXT,
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ]
        with self._lock:
            for stmt in stmts:
                self._conn.execute(stmt)

    # ------------------------------------------------------------------
    # Thread-safe execution helpers
    # ------------------------------------------------------------------
    def execute(self, sql: str, params: list | None = None):
        with self._lock:
            if params:
                return self._conn.execute(sql, params)
            return self._conn.execute(sql)

    def fetchall(self, sql: str, params: list | None = None) -> list:
        with self._lock:
            if params:
                return self._conn.execute(sql, params).fetchall()
            return self._conn.execute(sql).fetchall()

    def fetchone(self, sql: str, params: list | None = None):
        with self._lock:
            if params:
                return self._conn.execute(sql, params).fetchone()
            return self._conn.execute(sql).fetchone()

    def execute_query(self, sql: str) -> tuple[list[str], list[list]]:
        """Run an arbitrary user-supplied SQL and return (columns, rows)."""
        with self._lock:
            cursor = self._conn.execute(sql)
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            return columns, [list(r) for r in rows]

    def load_csv(self, table_name: str, file_path: str) -> tuple[list[str], int]:
        """Ingest a CSV/Excel file as a DuckDB table, return (columns, row_count)."""
        path = Path(file_path)
        with self._lock:
            if path.suffix.lower() in (".xlsx", ".xls"):
                # DuckDB can't read Excel natively — caller converts to CSV first
                raise ValueError("Pass a CSV path; convert Excel before calling load_csv.")
            self._conn.execute(
                f"CREATE OR REPLACE TABLE \"{table_name}\" AS "
                f"SELECT * FROM read_csv_auto('{path.as_posix()}', HEADER=TRUE)"
            )
            cursor = self._conn.execute(f'DESCRIBE "{table_name}"')
            columns = [r[0] for r in cursor.fetchall()]
            row_count = self._conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
        return columns, row_count

    def table_schema(self, table_name: str) -> list[dict]:
        """Return [{name, type}] for a dataset table."""
        rows = self.fetchall(f'DESCRIBE "{table_name}"')
        return [{"name": r[0], "type": r[1]} for r in rows]

    def drop_table(self, table_name: str) -> None:
        self.execute(f'DROP TABLE IF EXISTS "{table_name}"')


db = Database()
