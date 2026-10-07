from __future__ import annotations

from pathlib import Path

from credits.db import build_db, connect
from credits.export import to_jsonresume, to_markdown
from credits.load import load_yaml
from credits.paths import basics_path
from credits.query import search

ROOT = Path(__file__).resolve().parents[1]


def _rows(**kwargs):
    conn = connect()
    build_db(conn, root=ROOT)
    return search(conn, **kwargs)


def _basics() -> dict:
    return load_yaml(basics_path(ROOT))


def test_jsonresume_maps_employment_and_projects() -> None:
    resume = to_jsonresume(_rows(), basics=_basics())
    assert resume["basics"]["name"] == "Kaspars Greizis"
    assert "email" not in resume["basics"]
    assert "phone" not in resume["basics"]
    work_names = {w["name"] for w in resume["work"]}
    assert work_names == {"Accenture Baltics", "Tet", "Cognizant"}
    project_names = {p["name"] for p in resume["projects"]}
    assert project_names == {"zenClip", "zenOS keel DSP", "audio-shield"}
    assert all("dev-master" not in p["name"] for p in resume["projects"])


def test_jsonresume_work_uses_jsonresume_field_names() -> None:
    resume = to_jsonresume(_rows(kind=["employment"]), basics=_basics())
    accenture = next(w for w in resume["work"] if w["name"] == "Accenture Baltics")
    assert accenture["position"] == "Senior Salesforce Developer"
    assert accenture["startDate"] == "2024-08-01"
    assert accenture["endDate"] == "2025-03-31"


def test_jsonresume_project_uses_description_keywords_roles() -> None:
    resume = to_jsonresume(_rows(query="keel"), basics=_basics())
    keel = resume["projects"][0]
    assert keel["name"] == "zenOS keel DSP"
    assert "description" in keel
    assert "biquad" in keel["keywords"]
    assert keel["roles"] == ["Author"]
    assert keel["entity"] == "zenOS"
    assert keel["url"] == "https://github.com/k-dot-greyz/zenOS"


def test_export_omits_private_redacted_even_if_search_returned_them() -> None:
    resume = to_jsonresume(_rows(visibility=["private-redacted"]), basics=_basics())
    assert "projects" not in resume
    md = to_markdown(_rows(visibility=["private-redacted"]), basics=_basics())
    assert "dev-master" not in md
    assert "Private project" not in md


def test_suno_shaped_markdown_pitch() -> None:
    """Main use case: pick audio/DSP credits for a consulting-shaped CV slice."""
    rows = _rows(kind=["project"], tag=["audio"])
    # keel is tagged dsp+audio; audio-shield is audio. zenClip is not audio.
    md = to_markdown(rows, basics=_basics())
    assert "zenOS keel DSP" in md
    assert "audio-shield" in md
    assert "zenClip" not in md
    assert "Accenture" not in md
    assert "Kaspars Greizis" in md
    assert "Riga" in md
