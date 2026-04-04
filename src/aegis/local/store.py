"""SQLite-backed local store for standalone mode.

Stores traces, guard results, and cost data without any external dependency.
DB file lives at ``~/.aegis/local.db`` by default or in the project directory.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aegis.core.trace import Span

# ---------------------------------------------------------------------------
# Default DB location
# ---------------------------------------------------------------------------

_DEFAULT_DIR = Path.home() / ".aegis"


def _default_db_path() -> Path:
    _DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_DIR / "local.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    span_id     TEXT NOT NULL,
    parent_id   TEXT,
    name        TEXT NOT NULL,
    workspace   TEXT NOT NULL DEFAULT 'local',
    tenant_id   TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'ok',
    start_time  REAL NOT NULL,
    end_time    REAL NOT NULL,
    duration_ms REAL NOT NULL,
    attributes  TEXT NOT NULL DEFAULT '{}',
    events      TEXT NOT NULL DEFAULT '[]',
    error       TEXT,
    created_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_traces_workspace ON traces(workspace);
CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at);
CREATE INDEX IF NOT EXISTS idx_traces_name ON traces(name);
"""


# ---------------------------------------------------------------------------
# Trace summary (returned after each insert)
# ---------------------------------------------------------------------------


@dataclass
class TraceSummary:
    """Lightweight summary of a stored trace — used for terminal output."""

    name: str
    duration_ms: float
    tokens: int
    cost: float
    guard_status: str
    workspace: str


# ---------------------------------------------------------------------------
# LocalStore
# ---------------------------------------------------------------------------


class LocalStore:
    """Thread-safe SQLite store for local / standalone mode."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else _default_db_path()
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # -- write ---------------------------------------------------------------

    def store_span(self, span: Span) -> TraceSummary:
        """Persist a finished span and return a summary."""
        now = time.time()
        attrs = span.attributes or {}
        tokens = int(attrs.get("tokens", attrs.get("input_tokens", 0)))
        tokens += int(attrs.get("output_tokens", 0))
        cost = float(attrs.get("cost", attrs.get("aegis.cost", 0.0)))
        guard = attrs.get("aegis.guard.status", attrs.get("guard_status", "PASS"))

        row = (
            span.span_id,
            span.parent_id,
            span.name,
            span.workspace or "local",
            span.tenant_id or "",
            span.status.value if hasattr(span.status, "value") else str(span.status),
            span.start_time,
            span.end_time,
            span.duration_ms,
            json.dumps(attrs, default=str),
            json.dumps(span.events, default=str),
            span.error,
            now,
        )

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO traces "
                    "(span_id, parent_id, name, workspace, tenant_id, status, "
                    "start_time, end_time, duration_ms, attributes, events, error, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row,
                )

        return TraceSummary(
            name=span.name,
            duration_ms=round(span.duration_ms, 1),
            tokens=tokens,
            cost=cost,
            guard_status=str(guard),
            workspace=span.workspace or "local",
        )

    # -- read ----------------------------------------------------------------

    def recent_traces(self, limit: int = 50, workspace: str | None = None) -> list[dict[str, Any]]:
        """Return the most recent traces as dicts."""
        with self._lock:
            with self._connect() as conn:
                if workspace:
                    rows = conn.execute(
                        "SELECT * FROM traces WHERE workspace = ? "
                        "ORDER BY created_at DESC LIMIT ?",
                        (workspace, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM traces ORDER BY created_at DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
        return [dict(r) for r in rows]

    def stats(self, workspace: str | None = None) -> dict[str, Any]:
        """Aggregate stats: total traces, total cost, avg latency, guard blocks."""
        with self._lock:
            with self._connect() as conn:
                where = "WHERE workspace = ?" if workspace else ""
                params: tuple = (workspace,) if workspace else ()

                row = conn.execute(
                    f"SELECT COUNT(*) as total, "
                    f"COALESCE(AVG(duration_ms), 0) as avg_latency, "
                    f"COALESCE(MAX(duration_ms), 0) as max_latency "
                    f"FROM traces {where}",
                    params,
                ).fetchone()

                guard_blocks = conn.execute(
                    f"SELECT COUNT(*) as cnt FROM traces "
                    f"WHERE status = 'error' {('AND workspace = ?' if workspace else '')}",
                    params,
                ).fetchone()

        return {
            "total_traces": row["total"],
            "avg_latency_ms": round(row["avg_latency"], 1),
            "max_latency_ms": round(row["max_latency"], 1),
            "guard_blocks": guard_blocks["cnt"],
        }

    def workspaces(self) -> list[str]:
        """Return all distinct workspace names."""
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT workspace FROM traces ORDER BY workspace"
                ).fetchall()
        return [r["workspace"] for r in rows]

    def clear(self, workspace: str | None = None) -> int:
        """Delete traces. Returns count deleted."""
        with self._lock:
            with self._connect() as conn:
                if workspace:
                    cur = conn.execute(
                        "DELETE FROM traces WHERE workspace = ?", (workspace,)
                    )
                else:
                    cur = conn.execute("DELETE FROM traces")
                return cur.rowcount
