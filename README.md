# credits

greyZ credits ledger: one YAML file per project, job, asset, or reference, so the work can be indexed, searched, and sliced into a CV on request.

Owner: **Kaspars Greizis** (greyZ, GitHub [k-dot-greyz](https://github.com/k-dot-greyz), Riga, Latvia).

This is the source of truth. The SQLite database is generated; do not hand-edit it.

## What this is for

Keep a diff-friendly record of what exists — Salesforce work, audio QA, Rust DSP R&D, web, CI harnesses — without dumping private repo contents into a public git history.

Typical loop:

1. Add or edit a file under `records/`.
2. Open a PR. CI validates the schema, scans for obvious PII, and builds the DB.
3. Locally, search or export a subset (e.g. an audio-DSP slice for a Suno-shaped consulting pitch).

## Install

Python 3.11+. From the repo root:

```bash
python -m pip install -e ".[dev]"
```

## Record format

One file per credit: `records/<id>.yaml`. The `id` must match the filename stem (`zenclip` → `records/zenclip.yaml`).

Why YAML, not JSON: humans edit these; comments and short multiline summaries stay readable; diffs stay reviewable in PRs. The contract is still a JSON Schema (draft 2020-12) at `schema/credit.schema.json`. The build step parses YAML and validates the objects.

Field names follow [JSON Resume](https://jsonresume.org/schema) where they overlap:

| Credit field | JSON Resume |
|---|---|
| `name` | `projects[].name` / display title |
| `position` | `work[].position` |
| `entity` | `work[].name`, `projects[].entity` |
| `startDate` / `endDate` | same, ISO `YYYY` / `YYYY-MM` / `YYYY-MM-DD` |
| `summary` | `work[].summary`; copied to `projects[].description` on export |
| `highlights`, `keywords`, `roles`, `url` | same |

Ledger-only fields: `id`, `kind`, `status`, `tech`, `evidence`, `verification`, `visibility`.

`kind`: `project` · `employment` · `client-engagement` · `asset` · `publication` · `talk` · `release` · `reference`

`status`: `idea` · `R&D` · `in-development` · `shipped` · `archived`

Nothing gets `shipped` unless a source actually says it shipped. v0.1 seeds are R&D, in-development, or archived employment.

`visibility`:

- `public` — safe to publish and to include in CV export
- `private-redacted` — stub only (name + status + a one-liner). Export drops these.

Evidence links have their own `visibility`, so a public project can still redact a Linear id.

Minimal public record:

```yaml
$schema: ../schema/credit.schema.json
id: example
name: Example
kind: project
status: in-development
summary: One or two sentences. Verified, public, no PII.
keywords: [audio]
verification:
  status: verified          # or self-reported | needs-confirm
  source: https://github.com/k-dot-greyz/example
visibility: public
```

Public-identity bits used by export live in `meta/basics.yaml` (no email, phone, or street address).

## How to add a credit

1. Copy a neighbouring file in `records/` or the snippet above.
2. Use a kebab-case `id` that matches the filename.
3. Put **only** facts you can point at. If a date, employer, or bullet is unconfirmed, either omit it or set `verification.status: needs-confirm`. Quote any string that contains `#` (`"PR #80"`) — otherwise YAML treats it as a comment.
4. Private work: `visibility: private-redacted` and no stack, URLs, or descriptions from private repos.
5. Do not add rates, salary, phone numbers, personal addresses, or private emails. CI will fail the PR if it sees them.
6. Run:

```bash
python -m credits validate
python -m credits pii
python -m pytest
```

7. PR. Do not commit `*.sqlite`.

## Search and export

The CLI always compiles from `records/` (in-memory) unless you pass `--db`.

```bash
# full-text + filters
python -m credits search biquad
python -m credits search --kind project --tag dsp --status R&D
python -m credits search --from 2024-01 --to 2025-12 --kind employment

python -m credits show zenclip

# CV slice — audio/DSP projects (Suno-shaped pitch)
python -m credits export --format markdown --kind project --tag audio
python -m credits export --format jsonresume --kind project --tag dsp --out /tmp/resume.json
```

Export **never** includes `private-redacted` records, even if search found them. JSON Resume output is a `resume.json` object (`basics`, `work`, `projects`, `skills`, …). Markdown is a readable subset of the same slice.

Build the SQLite+FTS5 database when you want a file (CI does this and uploads it as an artifact):

```bash
python -m credits build --out dist/credits.sqlite
```

The DB is **not** committed. YAML is the source of truth; a binary DB would pick fights in merges and go stale the moment someone edits a record. CI rebuilds it on every PR.

## Privacy

This repo is public. Hard rules:

- No rates, salary, phone numbers, personal addresses, or private emails.
- No contents from private repos.
- Private items are stubs (`visibility: private-redacted`) or omitted.
- `python -m credits pii` (and the CI job of the same name) fails on phone-shaped strings, emails, compensation-like amounts, and forbidden field names (`salary`, `phone`, `email`, …).

## Layout

```
schema/credit.schema.json   JSON Schema draft 2020-12
records/*.yaml              one credit each
meta/basics.yaml            public identity for CV export
src/credits/                validate / pii / sqlite+fts5 / cli
tests/                      schema, seed policy, search, export
```
