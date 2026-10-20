from __future__ import annotations

from pathlib import Path

from credits.load import load_yaml, record_files, validator


def validate_records(root: Path | None = None) -> list[str]:
    """Return human-readable error strings. Empty list means OK."""
    errors: list[str] = []
    val = validator(root)
    seen_ids: dict[str, str] = {}

    files = record_files(root)
    if not files:
        errors.append("no records/*.yaml files found")
        return errors

    for path in files:
        try:
            data = load_yaml(path)
        except Exception as exc:  # noqa: BLE001 — surface YAML errors as validation
            errors.append(f"{path}: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path}: expected a mapping")
            continue

        instance = {k: v for k, v in data.items() if k != "_path"}
        for err in sorted(val.iter_errors(instance), key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in err.path) or "(root)"
            errors.append(f"{path}: {loc}: {err.message}")

        rec_id = instance.get("id")
        if isinstance(rec_id, str):
            if rec_id != path.stem:
                errors.append(
                    f"{path}: id {rec_id!r} does not match filename stem {path.stem!r}"
                )
            if rec_id in seen_ids:
                errors.append(
                    f"{path}: duplicate id {rec_id!r} (also {seen_ids[rec_id]})"
                )
            else:
                seen_ids[rec_id] = str(path)

        start, end = instance.get("startDate"), instance.get("endDate")
        if isinstance(start, str) and isinstance(end, str) and end < start:
            errors.append(f"{path}: endDate {end} is before startDate {start}")

    return errors
