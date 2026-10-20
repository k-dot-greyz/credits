from __future__ import annotations

import os
from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """Walk from start (or cwd / this file) until schema/credit.schema.json exists."""
    env = os.environ.get("CREDITS_ROOT")
    if env:
        root = Path(env).resolve()
        if (root / "schema" / "credit.schema.json").is_file():
            return root
        raise FileNotFoundError(f"CREDITS_ROOT={env} has no schema/credit.schema.json")

    candidates: list[Path] = []
    if start is not None:
        candidates.append(start.resolve())
    candidates.append(Path.cwd().resolve())
    candidates.append(Path(__file__).resolve())

    seen: set[Path] = set()
    for origin in candidates:
        here = origin if origin.is_dir() else origin.parent
        for path in [here, *here.parents]:
            if path in seen:
                continue
            seen.add(path)
            if (path / "schema" / "credit.schema.json").is_file():
                return path
    raise FileNotFoundError(
        "Could not find a credits repo (schema/credit.schema.json). "
        "Run from the repo, or set CREDITS_ROOT."
    )


def schema_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "schema" / "credit.schema.json"


def records_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "records"


def basics_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "meta" / "basics.yaml"
