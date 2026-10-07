from __future__ import annotations

from pathlib import Path

from credits.db import build_db, connect
from credits.query import get_record, search

ROOT = Path(__file__).resolve().parents[1]


def _db():
    conn = connect()
    build_db(conn, root=ROOT)
    return conn


def test_build_indexes_all_records() -> None:
    conn = _db()
    count = conn.execute("SELECT COUNT(*) AS n FROM credits").fetchone()["n"]
    assert count == 9


def test_fts_finds_biquad() -> None:
    conn = _db()
    rows = search(conn, query="biquad")
    assert [r["id"] for r in rows] == ["zenos-keel-dsp"]


def test_filter_kind_and_tag() -> None:
    conn = _db()
    rows = search(conn, kind=["project"], tag=["dsp"])
    assert [r["id"] for r in rows] == ["zenos-keel-dsp"]


def test_filter_status() -> None:
    conn = _db()
    rows = search(conn, status=["in-development"], visibility=["public"])
    ids = {r["id"] for r in rows}
    assert "zenclip" in ids
    assert "audio-shield" in ids
    assert "zenos-keel-dsp" not in ids


def test_date_overlap_accenture() -> None:
    conn = _db()
    rows = search(conn, date_from="2024-09", date_to="2025-01", kind=["employment"])
    assert [r["id"] for r in rows] == ["accenture-baltics"]


def test_show_record() -> None:
    conn = _db()
    record = get_record(conn, "zenclip")
    assert record is not None
    assert record["name"] == "zenClip"
    assert get_record(conn, "nope") is None


def test_search_private_stubs() -> None:
    conn = _db()
    rows = search(conn, query="dev-master", visibility=["private-redacted"])
    assert [r["id"] for r in rows] == ["dev-master"]
