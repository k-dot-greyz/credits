from __future__ import annotations

from datetime import date
from typing import Any

KIND_TO_SECTION = {
    "employment": "work",
    "client-engagement": "work",
    "project": "projects",
    "asset": "projects",
    "release": "projects",
    "talk": "projects",
    "publication": "publications",
    "reference": "references",
}


def _public_evidence(record: dict[str, Any]) -> list[dict[str, Any]]:
    links = []
    for item in record.get("evidence") or []:
        if item.get("visibility") == "public":
            links.append(item)
    return links


def _primary_url(record: dict[str, Any]) -> str | None:
    if record.get("url"):
        return record["url"]
    for item in _public_evidence(record):
        if item.get("url"):
            return item["url"]
    return None


def record_to_work(record: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {}
    if record.get("entity"):
        item["name"] = record["entity"]
    if record.get("position") or record.get("name"):
        item["position"] = record.get("position") or record["name"]
    if record.get("location"):
        item["location"] = record["location"]
    url = _primary_url(record)
    if url:
        item["url"] = url
    if record.get("startDate"):
        item["startDate"] = record["startDate"]
    if record.get("endDate"):
        item["endDate"] = record["endDate"]
    if record.get("summary"):
        item["summary"] = record["summary"]
    if record.get("highlights"):
        item["highlights"] = list(record["highlights"])
    return item


def record_to_project(record: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {"name": record["name"]}
    if record.get("summary"):
        item["description"] = record["summary"]
    if record.get("highlights"):
        item["highlights"] = list(record["highlights"])
    keywords = list(record.get("keywords") or [])
    for tech in record.get("tech") or []:
        if tech not in keywords:
            keywords.append(tech)
    if keywords:
        item["keywords"] = keywords
    if record.get("startDate"):
        item["startDate"] = record["startDate"]
    if record.get("endDate"):
        item["endDate"] = record["endDate"]
    url = _primary_url(record)
    if url:
        item["url"] = url
    if record.get("roles"):
        item["roles"] = list(record["roles"])
    if record.get("entity"):
        item["entity"] = record["entity"]
    item["type"] = "talk" if record["kind"] == "talk" else record["kind"]
    return item


def record_to_publication(record: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {"name": record["name"]}
    if record.get("entity"):
        item["publisher"] = record["entity"]
    if record.get("startDate") or record.get("endDate"):
        item["releaseDate"] = record.get("endDate") or record.get("startDate")
    url = _primary_url(record)
    if url:
        item["url"] = url
    if record.get("summary"):
        item["summary"] = record["summary"]
    return item


def record_to_reference(record: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {"name": record.get("entity") or record["name"]}
    if record.get("summary"):
        item["reference"] = record["summary"]
    return item


def collect_skills(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    topics: list[str] = []
    stack: list[str] = []
    seen_topics: set[str] = set()
    seen_stack: set[str] = set()
    for record in records:
        for word in record.get("keywords") or []:
            key = word.lower()
            if key not in seen_topics:
                seen_topics.add(key)
                topics.append(word)
        for word in record.get("tech") or []:
            key = word.lower()
            if key not in seen_stack:
                seen_stack.add(key)
                stack.append(word)
    skills: list[dict[str, Any]] = []
    if topics:
        skills.append({"name": "Keywords", "keywords": topics})
    if stack:
        skills.append({"name": "Tech", "keywords": stack})
    return skills


def to_jsonresume(
    records: list[dict[str, Any]],
    basics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    public = [r for r in records if r.get("visibility") == "public"]
    resume: dict[str, Any] = {
        "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/master/schema.json",
        "basics": dict(basics or {}),
        "meta": {
            "version": "0.1.0",
            "lastModified": date.today().isoformat(),
        },
    }
    work: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    publications: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []

    for record in public:
        section = KIND_TO_SECTION.get(record["kind"])
        if section == "work":
            work.append(record_to_work(record))
        elif section == "projects":
            projects.append(record_to_project(record))
        elif section == "publications":
            publications.append(record_to_publication(record))
        elif section == "references":
            references.append(record_to_reference(record))

    if work:
        resume["work"] = work
    if projects:
        resume["projects"] = projects
    if publications:
        resume["publications"] = publications
    if references:
        resume["references"] = references
    skills = collect_skills(public)
    if skills:
        resume["skills"] = skills
    return resume


def _date_range(record: dict[str, Any]) -> str:
    start = record.get("startDate")
    end = record.get("endDate")
    if start and end:
        return f"{start} — {end}"
    if start:
        return f"{start} — present"
    return ""


def to_markdown(
    records: list[dict[str, Any]],
    basics: dict[str, Any] | None = None,
) -> str:
    public = [r for r in records if r.get("visibility") == "public"]
    basics = basics or {}
    lines: list[str] = []
    name = basics.get("name") or "Credits"
    lines.append(f"# {name}")
    label = basics.get("label")
    if label:
        lines.append(label)
    location = basics.get("location") or {}
    loc_bits = [
        location.get("city"),
        location.get("region") if location.get("region") != location.get("city") else None,
        location.get("countryCode"),
    ]
    loc = ", ".join(bit for bit in loc_bits if bit)
    if loc:
        lines.append(loc)
    if basics.get("url"):
        lines.append(basics["url"])
    lines.append("")

    groups: list[tuple[str, str, list[dict[str, Any]]]] = [
        ("Work", "work", []),
        ("Projects", "projects", []),
        ("Publications", "publications", []),
        ("References", "references", []),
    ]
    buckets = {key: items for _, key, items in groups}
    for record in public:
        section = KIND_TO_SECTION.get(record["kind"])
        if section in buckets:
            buckets[section].append(record)

    for heading, key, _ in groups:
        items = buckets[key]
        if not items:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        for record in items:
            title = record["name"]
            if record.get("entity") and record["kind"] in {
                "employment",
                "client-engagement",
            }:
                title = f"{record.get('position') or record['name']} — {record['entity']}"
            elif record.get("entity"):
                title = f"{record['name']} ({record['entity']})"
            lines.append(f"### {title}")
            dates = _date_range(record)
            meta = [record.get("status"), dates]
            lines.append(" · ".join(part for part in meta if part))
            if record.get("summary"):
                lines.append("")
                lines.append(record["summary"])
            for bullet in record.get("highlights") or []:
                lines.append(f"- {bullet}")
            url = _primary_url(record)
            if url:
                lines.append(f"- {url}")
            tags = list(record.get("keywords") or []) + list(record.get("tech") or [])
            if tags:
                lines.append("- tags: " + ", ".join(tags))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
