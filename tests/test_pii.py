from __future__ import annotations

from pathlib import Path

from credits.load import load_yaml
from credits.pii import scan_data, scan_files, scan_value

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_seed_records_have_no_pii() -> None:
    assert scan_files(ROOT) == []


def test_phone_from_fact_sheet_is_caught() -> None:
    data = load_yaml(FIXTURES / "pii_phone.yaml")
    findings = scan_data(data, "fixture")
    assert any("phone" in f for f in findings)


def test_salary_amounts_are_caught() -> None:
    data = load_yaml(FIXTURES / "pii_salary.yaml")
    findings = scan_data(data, "fixture")
    assert findings
    assert any("money" in f or "compensation" in f for f in findings)


def test_email_is_caught() -> None:
    data = load_yaml(FIXTURES / "pii_email.yaml")
    findings = scan_data(data, "fixture")
    assert any("email" in f for f in findings)


def test_sha256_is_not_a_phone() -> None:
    assert scan_value("summary", "SHA-256 content-addressed ingest") == []


def test_github_url_is_not_email() -> None:
    assert scan_value("url", "https://github.com/k-dot-greyz/zenClip") == []


def test_forbidden_field_names() -> None:
    findings = scan_data({"id": "x", "phone": "+1", "name": "x"}, "x")
    assert any("forbidden field" in f for f in findings)
