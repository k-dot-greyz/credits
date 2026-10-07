from __future__ import annotations

from pathlib import Path

from credits.load import load_records

ROOT = Path(__file__).resolve().parents[1]

# Seed policy from the v0.1 brief: only verified-and-safe facts; no invented
# shipped products; private repos as stubs; employment needs-confirm; skip
# [CONFIRM]/[ADD] rows (Sonarworks, unnamed 2016 employer, internship, independent 2025).
ALLOWED_PUBLIC_PROJECTS = {"zenclip", "zenos-keel-dsp", "audio-shield"}
ALLOWED_PRIVATE_STUBS = {"dev-master", "midi-gem", "kitties-tts"}
ALLOWED_EMPLOYMENT = {"accenture-baltics", "tet", "cognizant"}
FORBIDDEN_NAMES = ("sonarworks", "soundid", "focusrite")


def test_no_record_is_shipped() -> None:
    for record in load_records(ROOT):
        assert record["status"] != "shipped", record["id"]


def test_public_projects_are_the_named_repos() -> None:
    projects = {
        r["id"]
        for r in load_records(ROOT)
        if r["kind"] == "project" and r["visibility"] == "public"
    }
    assert projects == ALLOWED_PUBLIC_PROJECTS


def test_private_stubs_are_redacted() -> None:
    stubs = [r for r in load_records(ROOT) if r["id"] in ALLOWED_PRIVATE_STUBS]
    assert {r["id"] for r in stubs} == ALLOWED_PRIVATE_STUBS
    for record in stubs:
        assert record["visibility"] == "private-redacted"
        assert record["summary"] == "Private project. Details redacted."
        assert "evidence" not in record
        assert "tech" not in record
        assert "url" not in record
        assert "github.com" not in record["summary"].lower()


def test_employment_is_needs_confirm_and_sparse() -> None:
    jobs = [r for r in load_records(ROOT) if r["kind"] == "employment"]
    assert {r["id"] for r in jobs} == ALLOWED_EMPLOYMENT
    for record in jobs:
        assert record["verification"]["status"] == "needs-confirm"
        assert record["visibility"] == "public"
        assert "highlights" not in record
        assert not record.get("summary")


def test_no_confirm_or_add_employers() -> None:
    blob = " ".join(
        (r.get("entity") or "") + " " + r["name"] + " " + (r.get("summary") or "")
        for r in load_records(ROOT)
    ).lower()
    for needle in FORBIDDEN_NAMES:
        assert needle not in blob


def test_hash_marks_in_yaml_are_quoted_not_commented_out() -> None:
    """Unquoted '#80' is a YAML comment. PR numbers must survive the parse."""
    records = {r["id"]: r for r in load_records(ROOT)}
    zenclip = records["zenclip"]
    assert any("#2" in h for h in zenclip["highlights"])
    pr = next(e for e in zenclip["evidence"] if e["type"] == "pr")
    assert pr["label"] == "PR #2"
    keel = records["zenos-keel-dsp"]
    assert any("#80" in h for h in keel["highlights"])
    keel_pr = next(e for e in keel["evidence"] if e["type"] == "pr")
    assert keel_pr["label"] == "PR #80"


def test_accenture_dates_are_the_verified_ones() -> None:
    record = next(r for r in load_records(ROOT) if r["id"] == "accenture-baltics")
    assert record["entity"] == "Accenture Baltics"
    assert record["position"] == "Senior Salesforce Developer"
    assert record["startDate"] == "2024-08-01"
    assert record["endDate"] == "2025-03-31"
