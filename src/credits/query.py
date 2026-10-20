from __future__ import annotations

import json
import sqlite3
from typing import Any

from credits.db import FTS_COLUMNS


def _fts_safe(query: str) -> str:
    """Wrap each token in double quotes so user input is not FTS syntax."""
    tokens = [t for t in query.replace('"', " ").split() if t]
    if not tokens:
        return ""
    return " AND ".join(f'"{t}"' for t in tokens)


def search(
    conn: sqlite3.Connection,
    *,
    query: str | None = None,
    kind: list[str] | None = None,
    tag: list[str] | None = None,
    status: list[str] | None = None,
    visibility: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if query:
        match = _fts_safe(query)
        if match:
            clauses.append(
                "credits.rowid IN (SELECT rowid FROM credits_fts WHERE credits_fts MATCH ?)"
            )
            params.append(match)

    def add_in(column: str, values: list[str] | None) -> None:
        if not values:
            return
        placeholders = ",".join("?" for _ in values)
        clauses.append(f"{column} IN ({placeholders})")
        params.extend(values)

    add_in("kind", kind)
    add_in("status", status)
    add_in("visibility", visibility)

    if tag:
        for item in tag:
            like = f"%{item.lower()}%"
            clauses.append(
                "(lower(keywords) LIKE ? OR lower(tech) LIKE ? OR lower(roles) LIKE ?)"
            )
            params.extend([like, like, like])

    # Overlap: start <= to AND (end IS NULL OR end >= from). Missing start still matches.
    if date_from:
        clauses.append("(end_date IS NULL OR end_date >= ?)")
        params.append(date_from)
    if date_to:
        clauses.append("(start_date IS NULL OR start_date <= ?)")
        params.append(date_to)

    sql = "SELECT json FROM credits"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY COALESCE(start_date, '') DESC, id ASC"

    rows = conn.execute(sql, params).fetchall()
    return [json.loads(row["json"]) for row in rows]


def get_record(conn: sqlite3.Connection, rec_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT json FROM credits WHERE id = ?", (rec_id,)).fetchone()
    if row is None:
        return None
    return json.loads(row["json"])


def fts_columns() -> tuple[str, ...]:
    return FTS_COLUMNS
