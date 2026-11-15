"""SQLite persistence layer.

Uses the Python standard-library ``sqlite3`` module with the same-thread
connection kept open per-call.  A small helper (:func:`query`) returns
``sqlite3.Row`` objects so callers can index by column name.

Schema is created idempotently on import; on a fresh database the seed
records are inserted so the dashboard has something to show out of the box.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

from .config import settings

# Column names used by several tables; kept here to avoid typos.
CONNECTOR_TYPES = ("rest", "api", "db", "sftp", "queue")
AUTH_TYPES = ("none", "bearer", "basic")
TRANSFORM_TYPES = ("direct", "upper", "lower", "concat", "const")
JOB_STATUSES = ("active", "paused")
RUN_STATUSES = ("success", "failure")


SCHEMA = """
CREATE TABLE IF NOT EXISTS connectors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL CHECK (type IN ('rest','api','db','sftp','queue')),
    base_url    TEXT,
    auth_type   TEXT NOT NULL DEFAULT 'none'
                CHECK (auth_type IN ('none','bearer','basic')),
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mappings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    source_connector_id INTEGER NOT NULL REFERENCES connectors(id),
    target_connector_id INTEGER NOT NULL REFERENCES connectors(id),
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mapping_fields (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    mapping_id       INTEGER NOT NULL REFERENCES mappings(id) ON DELETE CASCADE,
    source_field     TEXT NOT NULL,
    target_field     TEXT NOT NULL,
    transform        TEXT NOT NULL DEFAULT 'direct'
                     CHECK (transform IN ('direct','upper','lower','concat','const')),
    transform_param  TEXT,
    sort_order       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS jobs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    source_connector_id INTEGER NOT NULL REFERENCES connectors(id),
    target_connector_id INTEGER NOT NULL REFERENCES connectors(id),
    mapping_id          INTEGER NOT NULL REFERENCES mappings(id),
    schedule_note       TEXT,
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','paused')),
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS run_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      INTEGER NOT NULL REFERENCES jobs(id),
    status      TEXT NOT NULL CHECK (status IN ('success','failure')),
    rows_in     INTEGER NOT NULL DEFAULT 0,
    rows_out    INTEGER NOT NULL DEFAULT 0,
    error       TEXT,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS webhooks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id         INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    path           TEXT NOT NULL UNIQUE,
    method         TEXT NOT NULL DEFAULT 'POST',
    active         INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect() -> sqlite3.Connection:
    """Open a new connection for the configured database file."""
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """Context manager yielding a connection and committing on success."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
    """Run a SELECT and return all rows as a list of ``sqlite3.Row``."""
    return conn.execute(sql, params).fetchall()


def query_one(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
    """Run a SELECT and return the first row, or ``None``."""
    return conn.execute(sql, params).fetchone()


def init_db() -> None:
    """Create the schema and seed sample data (once per database file)."""
    with get_db() as conn:
        conn.executescript(SCHEMA)
        _seed_if_empty(conn)


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    """Convert a ``sqlite3.Row`` to a plain ``dict`` (or ``None``)."""
    return dict(row) if row is not None else None


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    """Insert demo records when the connectors table is empty."""
    if query_one(conn, "SELECT COUNT(*) AS c FROM connectors")["c"] > 0:
        return

    # Insert each connector separately so we can capture its real id.
    # (A multi-row INSERT makes ``lastrowid`` the *last* row's id, which would
    # silently point mappings at a non-existent connector.)
    connectors = [
        ("Salesforce CRM", "rest", "https://api.salesforce.example",
         "bearer", "Placeholder credentials only. Target: standard SObjects."),
        ("Postgres Warehouse", "db", "postgres://warehouse.example:5432/mart",
         "basic", "Analytics warehouse. No secrets stored - DB creds via env."),
        ("RMQ Order Queue", "queue", "amqp://queue.example/orders",
         "none", "Order ingestion queue."),
    ]
    source_id = conn.execute(
        "INSERT INTO connectors (name, type, base_url, auth_type, notes)"
        " VALUES (?,?,?,?,?)", connectors[0],
    ).lastrowid
    target_id = conn.execute(
        "INSERT INTO connectors (name, type, base_url, auth_type, notes)"
        " VALUES (?,?,?,?,?)", connectors[1],
    ).lastrowid
    conn.execute(
        "INSERT INTO connectors (name, type, base_url, auth_type, notes)"
        " VALUES (?,?,?,?,?)", connectors[2],
    )

    map1_id = conn.execute(
        "INSERT INTO mappings (name, source_connector_id, target_connector_id, notes)"
        " VALUES ('Customer Sync', ?, ?, 'Normalise CRM contacts into warehouse.');",
        (source_id, target_id),
    ).lastrowid
    map2_id = conn.execute(
        "INSERT INTO mappings (name, source_connector_id, target_connector_id, notes)"
        " VALUES ('Order Mirror', ?, ?, 'Copy order fields with upper-casing on status.');",
        (source_id, target_id),
    ).lastrowid

    field_sql = (
        "INSERT INTO mapping_fields (mapping_id, source_field, target_field,"
        " transform, transform_param, sort_order) VALUES"
    )
    conn.execute(
        field_sql
        + " (?, 'Name', 'full_name', 'direct', NULL, 0),"
          " (?, 'Email', 'email', 'lower', NULL, 1),"
          " (?, 'Type', 'customer_type', 'upper', NULL, 2),"
          " (?, 'Region_Code', 'region', 'const', 'APAC', 3);",
        (map1_id, map1_id, map1_id, map1_id),
    )
    conn.execute(
        field_sql
        + " (?, 'Order_No', 'order_id', 'direct', NULL, 0),"
          " (?, 'Status', 'status', 'upper', NULL, 1),"
          " (?, 'created_on', 'created_at_ts', 'const', 'SYNCED', 2);",
        (map2_id, map2_id, map2_id),
    )

    job1_id = conn.execute(
        "INSERT INTO jobs (name, source_connector_id, target_connector_id,"
        " mapping_id, schedule_note, status)"
        " VALUES ('Hourly Customer Sync', ?, ?, ?, 'cron: 0 * * * *', 'active');",
        (source_id, target_id, map1_id),
    ).lastrowid
    job2_id = conn.execute(
        "INSERT INTO jobs (name, source_connector_id, target_connector_id,"
        " mapping_id, schedule_note, status)"
        " VALUES ('Daily Order Mirror', ?, ?, ?, 'cron: 0 2 * * *', 'active');",
        (source_id, target_id, map2_id),
    ).lastrowid

    conn.execute(
        "INSERT INTO webhooks (job_id, path, method) VALUES (?, '/hooks/customer-sync', 'POST');",
        (job1_id,),
    )

    conn.execute(
        "INSERT INTO run_logs (job_id, status, rows_in, rows_out, error)"
        " VALUES (?, 'success', 2, 2, NULL), (?, 'success', 2, 2, NULL),"
        " (?, 'failure', 2, 1, 'Missing field: Email on row 2');",
        (job1_id, job1_id, job2_id),
    )