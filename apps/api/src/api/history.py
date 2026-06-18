"""Minimal SQLite-backed chat history.

Each chat session has a UUID. Messages belonging to a session are stored
in insertion order so the full conversation can be replayed on reload.
Deliberately simple (no ORM) since this is a learning/portfolio project,
not a production data layer -- swap for Postgres + SQLAlchemy if this
ever needs to scale beyond a single instance.
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from api.core.config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New chat',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    provider TEXT,
    model_name TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(title: str = "New chat") -> str:
    session_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title, created_at) VALUES (?, ?, ?)",
            (session_id, title, _now()),
        )
    return session_id


def list_sessions() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_session(session_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, title, created_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_session(session_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def add_message(
    session_id: str,
    role: str,
    content: str,
    provider: str | None = None,
    model_name: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO messages (session_id, role, content, provider, model_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, role, content, provider, model_name, _now()),
        )


def get_messages(session_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, provider, model_name, created_at
            FROM messages WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]
