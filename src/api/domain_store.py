from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return base or "domain"


@dataclass
class DomainRecord:
    id: str
    name: str
    description: str
    emoji: str
    variant: str
    enabled: bool
    is_archived: bool
    created_at: str
    updated_at: str
    archived_at: str | None


class DomainStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS domains (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    emoji TEXT NOT NULL DEFAULT '',
                    variant TEXT NOT NULL DEFAULT 'coral',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    is_archived INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived_at TEXT
                )
                """
            )
            conn.commit()

    def _from_row(self, row: sqlite3.Row | None) -> DomainRecord | None:
        if row is None:
            return None
        return DomainRecord(
            id=str(row["id"]),
            name=str(row["name"]),
            description=str(row["description"]),
            emoji=str(row["emoji"]),
            variant=str(row["variant"]),
            enabled=bool(row["enabled"]),
            is_archived=bool(row["is_archived"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            archived_at=row["archived_at"],
        )

    def _next_available_slug(self, conn: sqlite3.Connection, base_slug: str) -> str:
        idx = 1
        while True:
            candidate = base_slug if idx == 1 else f"{base_slug}-{idx}"
            row = conn.execute("SELECT 1 FROM domains WHERE id = ?", (candidate,)).fetchone()
            if row is None:
                return candidate
            idx += 1

    def create_domain(
        self,
        *,
        name: str,
        description: str = "",
        emoji: str = "",
        variant: str = "coral",
    ) -> DomainRecord:
        with self._lock:
            with self._connect() as conn:
                now = _utc_now_iso()
                slug = self._next_available_slug(conn, _slugify(name))
                conn.execute(
                    """
                    INSERT INTO domains (
                        id, name, description, emoji, variant, enabled,
                        is_archived, created_at, updated_at, archived_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slug,
                        name,
                        description,
                        emoji,
                        variant,
                        1,
                        0,
                        now,
                        now,
                        None,
                    ),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM domains WHERE id = ?", (slug,)).fetchone()
            out = self._from_row(row)
            assert out is not None
            return out

    def archive_domain(self, domain_id: str) -> DomainRecord:
        with self._lock:
            with self._connect() as conn:
                now = _utc_now_iso()
                conn.execute(
                    """
                    UPDATE domains
                    SET enabled = 0, is_archived = 1,
                        archived_at = COALESCE(archived_at, ?), updated_at = ?
                    WHERE id = ?
                    """,
                    (now, now, domain_id),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM domains WHERE id = ?", (domain_id,)).fetchone()
            out = self._from_row(row)
            if out is None:
                raise KeyError(f"domain not found: {domain_id}")
            return out

    def get_domain(self, domain_id: str) -> DomainRecord | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM domains WHERE id = ?", (domain_id,)).fetchone()
            return self._from_row(row)

    def list_domains(self, *, include_archived: bool = False) -> list[DomainRecord]:
        with self._lock:
            with self._connect() as conn:
                if include_archived:
                    rows = conn.execute(
                        "SELECT * FROM domains WHERE is_archived = 1 ORDER BY created_at ASC"
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM domains WHERE is_archived = 0 ORDER BY created_at ASC"
                    ).fetchall()
        out: list[DomainRecord] = []
        for row in rows:
            rec = self._from_row(row)
            if rec is not None:
                out.append(rec)
        return out
