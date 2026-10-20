from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from credits.paths import records_dir, schema_path

Record = dict[str, Any]


def load_schema(root: Path | None = None) -> dict[str, Any]:
    path = schema_path(root)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validator(root: Path | None = None) -> Draft202012Validator:
    return Draft202012Validator(load_schema(root), format_checker=FormatChecker())


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        raise ValueError(f"{path}: empty file")
    return data


def record_files(root: Path | None = None) -> list[Path]:
    directory = records_dir(root)
    if not directory.is_dir():
        raise FileNotFoundError(f"records directory missing: {directory}")
    return sorted(p for p in directory.glob("*.yaml") if p.is_file())


def load_records(root: Path | None = None) -> list[Record]:
    records: list[Record] = []
    for path in record_files(root):
        data = load_yaml(path)
        if not isinstance(data, dict):
            raise ValueError(f"{path}: expected a mapping, got {type(data).__name__}")
        data["_path"] = str(path)
        records.append(data)
    return records
