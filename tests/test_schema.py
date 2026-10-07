from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from credits.load import load_records, load_schema
from credits.validate import validate_records

ROOT = Path(__file__).resolve().parents[1]


def test_seed_records_validate() -> None:
    assert validate_records(ROOT) == []


def test_schema_is_draft_2020_12() -> None:
    schema = load_schema(ROOT)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)


def test_id_must_match_filename() -> None:
    records = load_records(ROOT)
    for record in records:
        path = Path(record["_path"])
        assert record["id"] == path.stem


def test_required_fields_present() -> None:
    for record in load_records(ROOT):
        for key in ("id", "name", "kind", "status", "visibility", "verification"):
            assert key in record


def test_unknown_property_rejected() -> None:
    schema = load_schema(ROOT)
    val = Draft202012Validator(schema, format_checker=FormatChecker())
    sample = deepcopy(next(r for r in load_records(ROOT) if r["visibility"] == "public"))
    sample.pop("_path", None)
    sample["salary"] = "nope"
    errors = list(val.iter_errors(sample))
    assert errors
    assert any("salary" in e.message or "additional" in e.message.lower() for e in errors)


def test_kind_enum_rejects_typos() -> None:
    schema = load_schema(ROOT)
    val = Draft202012Validator(schema, format_checker=FormatChecker())
    sample = {
        "id": "x",
        "name": "x",
        "kind": "job",
        "status": "R&D",
        "visibility": "public",
        "verification": {"status": "verified", "source": "t"},
    }
    messages = " ".join(e.message for e in val.iter_errors(sample))
    assert "job" in messages


@pytest.mark.parametrize(
    "date_value",
    ["2024", "2024-08", "2024-08-01"],
)
def test_iso8601_dates_accepted(date_value: str) -> None:
    schema = load_schema(ROOT)
    val = Draft202012Validator(schema, format_checker=FormatChecker())
    sample = {
        "id": "x",
        "name": "x",
        "kind": "employment",
        "status": "archived",
        "startDate": date_value,
        "visibility": "public",
        "verification": {"status": "needs-confirm", "source": "t"},
    }
    assert list(val.iter_errors(sample)) == []
