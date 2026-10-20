from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from credits.load import load_records

FTS_COLUMNS = (
    "id",
    "name",
    "kind",
    "entity",
    "position",
    "summary",
    "keywords",
    "tech",
    "roles",
    "status",
)


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    target = ":memory:" if db_path is None else str(db_path)
    if db_path is not None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS credits_fts;
        DROP TABLE IF EXISTS credits;

        CREATE TABLE credits (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            entity TEXT,
            position TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT NOT NULL,
            summary TEXT,
            visibility TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            verification_source TEXT,
            url TEXT,
            keywords TEXT NOT NULL DEFAULT '',
            tech TEXT NOT NULL DEFAULT '',
            roles TEXT NOT NULL DEFAULT '',
            json TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE credits_fts USING fts5(
            id,
            name,
            kind,
            entity,
            position,
            summary,
            keywords,
            tech,
            roles,
            status,
            content='credits',
            content_rowid='rowid',
            tokenize='unicode61'
        );
        """
    )


def _join(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, list):
        return " ".join(str(v) for v in values)
    return str(values)


def _public_json(record: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in record.items() if k != "_path"}
    return out


def insert_record(conn: sqlite3.Connection, record: dict[str, Any]) -> None:
    payload = _public_json(record)
    verification = payload.get("verification") or {}
    conn.execute(
        """
        INSERT INTO credits (
            id, name, kind, entity, position, start_date, end_date, status,
            summary, visibility, verification_status, verification_source, url,
            keywords, tech, roles, json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["id"],
            payload["name"],
            payload["kind"],
            payload.get("entity"),
            payload.get("position"),
            payload.get("startDate"),
            payload.get("endDate"),
            payload["status"],
            payload.get("summary"),
            payload["visibility"],
            verification.get("status"),
            verification.get("source"),
            payload.get("url"),
            _join(payload.get("keywords")),
            _join(payload.get("tech")),
            _join(payload.get("roles")),
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
        ),
    )


def rebuild_fts(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO credits_fts(credits_fts) VALUES('rebuild')")


def build_db(
    conn: sqlite3.Connection,
    root: Path | None = None,
    records: Iterable[dict[str, Any]] | None = None,
) -> int:
    init_schema(conn)
    rows = list(records) if records is not None else load_records(root)
    for record in rows:
        insert_record(conn, record)
    rebuild_fts(conn)
    conn.commit()
    return len(rows)


def build_file(out: Path, root: Path | None = None) -> int:
    conn = connect(out)
    try:
        return build_db(conn, root=root)
    finally:
        conn.close()
