"""SQLite persistence for RatioBot warning history."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any

DATABASE_PATH = Path(__file__).resolve().parent / "ratiobot.sqlite3"


def _connect(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    """Create the warning log table if it does not already exist."""
    connection = _connect(database_path)
    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS warning_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    trigger_app TEXT NOT NULL,
                    active_minutes REAL NOT NULL,
                    strike_count INTEGER NOT NULL,
                    resolved INTEGER NOT NULL DEFAULT 0,
                    event_type TEXT NOT NULL DEFAULT 'warning'
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(warning_logs)")
            }
            if "event_type" not in columns:
                connection.execute(
                    "ALTER TABLE warning_logs ADD COLUMN event_type TEXT NOT NULL DEFAULT 'warning'"
                )
    finally:
        connection.close()


def insert_log(
    trigger_app: str,
    active_minutes: float,
    strike_count: int,
    database_path: Path = DATABASE_PATH,
    event_type: str = "warning",
    resolved: bool = False,
) -> int:
    """Insert a warning or audit event and return its database ID."""
    initialize_database(database_path)
    connection = _connect(database_path)
    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO warning_logs
                    (timestamp, trigger_app, active_minutes, strike_count, resolved, event_type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    trigger_app,
                    active_minutes,
                    strike_count,
                    int(resolved),
                    event_type,
                ),
            )
            return int(cursor.lastrowid)
    finally:
        connection.close()


def get_recent_logs(
    limit: int = 10,
    database_path: Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    """Return recent warnings as dictionaries for the dashboard."""
    initialize_database(database_path)
    connection = _connect(database_path)
    try:
        rows = connection.execute(
            """
            SELECT id, timestamp, trigger_app, active_minutes, strike_count,
                   resolved, event_type
            FROM warning_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, limit),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def resolve_logs(database_path: Path = DATABASE_PATH) -> None:
    """Mark all outstanding warnings as resolved after accepted proof."""
    initialize_database(database_path)
    connection = _connect(database_path)
    try:
        with connection:
            connection.execute("UPDATE warning_logs SET resolved = 1 WHERE resolved = 0")
    finally:
        connection.close()


def backup_database(
    database_path: Path = DATABASE_PATH,
    backup_path: Path | None = None,
) -> Path:
    """Create a backup copy of the SQLite database."""
    initialize_database(database_path)
    if backup_path is None:
        backup_path = database_path.with_suffix(".sqlite3.bak")
    source_conn = _connect(database_path)
    dest_conn = _connect(backup_path)
    try:
        source_conn.backup(dest_conn)
    finally:
        source_conn.close()
        dest_conn.close()
    return backup_path


