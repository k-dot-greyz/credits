from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import yaml

from credits import __version__
from credits.db import build_db, build_file, connect
from credits.export import to_jsonresume, to_markdown
from credits.load import load_yaml
from credits.paths import basics_path, records_dir, repo_root
from credits.pii import scan_files
from credits.query import get_record, search
from credits.validate import validate_records


def _root(args: argparse.Namespace) -> Path:
    if getattr(args, "root", None):
        return Path(args.root).resolve()
    return repo_root()


def _open_db(args: argparse.Namespace):
    root = _root(args)
    db_path = getattr(args, "db", None)
    if db_path:
        conn = connect(db_path)
        # If the file is empty/new, build it.
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='credits'"
        ).fetchone()
        if exists is None:
            build_db(conn, root=root)
        return conn
    conn = connect()
    build_db(conn, root=root)
    return conn


def _multi(values: list[str] | None) -> list[str] | None:
    return values or None


def _search_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "query": args.query or None,
        "kind": _multi(getattr(args, "kind", None)),
        "tag": _multi(getattr(args, "tag", None)),
        "status": _multi(getattr(args, "status", None)),
        "visibility": _multi(getattr(args, "visibility", None)),
        "date_from": getattr(args, "date_from", None),
        "date_to": getattr(args, "date_to", None),
    }


def cmd_validate(args: argparse.Namespace) -> int:
    errors = validate_records(_root(args))
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        print(f"{len(errors)} validation error(s)", file=sys.stderr)
        return 1
    print("OK: all records valid")
    return 0


def cmd_pii(args: argparse.Namespace) -> int:
    findings = scan_files(_root(args))
    if findings:
        for line in findings:
            print(line, file=sys.stderr)
        print(f"{len(findings)} PII finding(s)", file=sys.stderr)
        return 1
    print("OK: no obvious PII")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    errors = validate_records(_root(args))
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 1
    findings = scan_files(_root(args))
    if findings:
        for line in findings:
            print(line, file=sys.stderr)
        return 1
    out = Path(args.out)
    count = build_file(out, root=_root(args))
    print(f"Wrote {count} records to {out}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    conn = _open_db(args)
    try:
        rows = search(conn, **_search_kwargs(args))
    finally:
        conn.close()
    if args.json:
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    if not rows:
        print("No matches")
        return 0
    print(f"{'id':<22} {'kind':<18} {'status':<16} name")
    for row in rows:
        print(
            f"{row['id']:<22} {row['kind']:<18} {row['status']:<16} {row['name']}"
        )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    source = records_dir(_root(args)) / f"{args.id}.yaml"
    if source.is_file() and not getattr(args, "db", None):
        text = source.read_text(encoding="utf-8")
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return 0
    conn = _open_db(args)
    try:
        record = get_record(conn, args.id)
    finally:
        conn.close()
    if record is None:
        print(f"not found: {args.id}", file=sys.stderr)
        return 1
    yaml.safe_dump(record, sys.stdout, sort_keys=False, allow_unicode=True)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    conn = _open_db(args)
    try:
        rows = search(conn, **_search_kwargs(args))
    finally:
        conn.close()
    basics_file = basics_path(_root(args))
    basics = load_yaml(basics_file) if basics_file.is_file() else {}
    if args.format == "jsonresume":
        payload = to_jsonresume(rows, basics=basics)
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        text = to_markdown(rows, basics=basics)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


def _add_filter_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("query", nargs="?", help="full-text query (AND of tokens)")
    parser.add_argument("--kind", action="append", help="filter by kind (repeatable)")
    parser.add_argument(
        "--tag",
        action="append",
        help="filter by keyword/tech/role substring (repeatable)",
    )
    parser.add_argument(
        "--status", action="append", help="filter by status (repeatable)"
    )
    parser.add_argument(
        "--visibility",
        action="append",
        help="filter by visibility (repeatable). Default: all visibilities for search/show; export still drops private-redacted",
    )
    parser.add_argument("--from", dest="date_from", help="ISO date range start (inclusive)")
    parser.add_argument("--to", dest="date_to", help="ISO date range end (inclusive)")
    parser.add_argument("--db", help="SQLite file (default: build in-memory from records/)")
    parser.add_argument("--root", help="credits repo root")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="credits",
        description="Validate, index, search, and export greyZ credit records.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="validate records against the JSON Schema")
    p_val.add_argument("--root", help="credits repo root")
    p_val.set_defaults(func=cmd_validate)

    p_pii = sub.add_parser("pii", help="fail on obvious PII in records and basics")
    p_pii.add_argument("--root", help="credits repo root")
    p_pii.set_defaults(func=cmd_pii)

    p_build = sub.add_parser("build", help="validate, PII-scan, and compile SQLite+FTS5")
    p_build.add_argument("--out", default="dist/credits.sqlite", help="output sqlite path")
    p_build.add_argument("--root", help="credits repo root")
    p_build.set_defaults(func=cmd_build)

    p_search = sub.add_parser("search", help="full-text search with filters")
    _add_filter_flags(p_search)
    p_search.add_argument("--json", action="store_true", help="dump matching records as JSON")
    p_search.set_defaults(func=cmd_search)

    p_show = sub.add_parser("show", help="print one record as YAML")
    p_show.add_argument("id", help="record id/slug")
    p_show.add_argument("--db", help="SQLite file")
    p_show.add_argument("--root", help="credits repo root")
    p_show.set_defaults(func=cmd_show)

    p_export = sub.add_parser("export", help="export a CV subset")
    p_export.add_argument(
        "--format",
        required=True,
        choices=("jsonresume", "markdown"),
        help="jsonresume (resume.json) or markdown",
    )
    p_export.add_argument("--out", help="write to file instead of stdout")
    _add_filter_flags(p_export)
    p_export.set_defaults(func=cmd_export)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
