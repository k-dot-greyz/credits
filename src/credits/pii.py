from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from credits.load import load_yaml, record_files
from credits.paths import basics_path

# Field names that must never appear on a credit or in basics.
FORBIDDEN_KEYS = frozenset(
    {
        "phone",
        "email",
        "address",
        "postalcode",
        "salary",
        "compensation",
        "wage",
        "pay",
        "rate",
        "dayrate",
        "hourlyrate",
        "fee",
    }
)

# (+371) 28366168, +371 28366168, 712-117-2923 — requires a country/area group.
PHONE_RE = re.compile(
    r"""
    (?:
        \(\+\d{1,3}\)[\s.-]*\d{5,12}
        |
        \+\d{1,3}[\s.-]*\(?\d{2,4}\)?[\s.-]*\d{3}[\s.-]*\d{2,4}
        |
        \(\d{2,4}\)[\s.-]*\d{3}[\s.-]*\d{3,4}
        |
        \b\d{3}[\s.-]\d{3}[\s.-]\d{4}\b
    )
    """,
    re.VERBOSE,
)

EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)

# Compensation-like amounts. Avoid flagging GitHub $schema or SHA-256.
MONEY_RE = re.compile(
    r"""
    (?:
        (?<![A-Za-z])[$€£]\s*\d
        |
        \b\d[\d,]*(?:\.\d+)?\s*(?:usd|eur|gbp|chf|cad|aud)\b
        |
        \b(?:salary|compensation|hourly\s*rate|day\s*rate|dayrate|pay\s*rate)\b
        |
        \b\d+(?:\.\d+)?\s*/\s*(?:hr|hour|day|mo|month|yr|year)\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _walk_strings(node: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _walk_strings(value, path)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _walk_strings(value, f"{prefix}[{i}]")
    elif isinstance(node, str):
        yield prefix, node
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        yield prefix, str(node)


def _walk_keys(node: Any, prefix: str = "") -> Iterable[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path
            yield from _walk_keys(value, path)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _walk_keys(value, f"{prefix}[{i}]")


def scan_value(path: str, text: str) -> list[str]:
    hits: list[str] = []
    if PHONE_RE.search(text):
        hits.append(f"{path}: possible phone number")
    if EMAIL_RE.search(text):
        hits.append(f"{path}: possible email address")
    if MONEY_RE.search(text):
        hits.append(f"{path}: possible compensation / money amount")
    return hits


def scan_data(data: Any, origin: str) -> list[str]:
    findings: list[str] = []
    for key_path in _walk_keys(data):
        leaf = key_path.rsplit(".", 1)[-1].rsplit("[", 1)[0]
        normalized = re.sub(r"[^a-z]", "", leaf.lower())
        if normalized in FORBIDDEN_KEYS:
            findings.append(f"{origin}: forbidden field {key_path}")
    for field_path, text in _walk_strings(data):
        for hit in scan_value(field_path, text):
            findings.append(f"{origin}: {hit}")
    return findings


def scan_files(root: Path | None = None) -> list[str]:
    findings: list[str] = []
    for path in record_files(root):
        try:
            data = load_yaml(path)
        except Exception as exc:  # noqa: BLE001
            findings.append(f"{path}: {exc}")
            continue
        findings.extend(scan_data(data, str(path)))
    basics = basics_path(root)
    if basics.is_file():
        try:
            data = load_yaml(basics)
        except Exception as exc:  # noqa: BLE001
            findings.append(f"{basics}: {exc}")
        else:
            findings.extend(scan_data(data, str(basics)))
    return findings
