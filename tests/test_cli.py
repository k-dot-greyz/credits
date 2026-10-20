from __future__ import annotations

import json
import shutil
from pathlib import Path

from credits.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_validate_subcommand() -> None:
    assert main(["validate", "--root", str(ROOT)]) == 0


def test_pii_subcommand() -> None:
    assert main(["pii", "--root", str(ROOT)]) == 0


def test_search_and_show(tmp_path: Path, capsys) -> None:
    db = tmp_path / "credits.sqlite"
    assert main(["build", "--root", str(ROOT), "--out", str(db)]) == 0
    capsys.readouterr()
    assert main(["search", "--root", str(ROOT), "--db", str(db), "keel"]) == 0
    out = capsys.readouterr().out
    assert "zenos-keel-dsp" in out
    assert main(["show", "--root", str(ROOT), "--db", str(db), "zenclip"]) == 0
    shown = capsys.readouterr().out
    assert "zenClip" in shown


def test_export_jsonresume_stdout(capsys) -> None:
    assert (
        main(
            [
                "export",
                "--root",
                str(ROOT),
                "--format",
                "jsonresume",
                "--kind",
                "project",
                "--tag",
                "dsp",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["projects"][0]["name"] == "zenOS keel DSP"
    assert payload["basics"]["name"] == "Kaspars Greizis"


def test_pii_cli_fails_on_phone(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "schema", tmp_path / "schema")
    (tmp_path / "records").mkdir()
    shutil.copy(
        ROOT / "tests" / "fixtures" / "pii_phone.yaml",
        tmp_path / "records" / "pii-phone.yaml",
    )
    (tmp_path / "meta").mkdir()
    shutil.copy(ROOT / "meta" / "basics.yaml", tmp_path / "meta" / "basics.yaml")
    assert main(["pii", "--root", str(tmp_path)]) == 1
