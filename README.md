# GEOsphere

![GEOsphere](./geo.png)

GEOsphere is a Claude Code skill and Python runtime for GEO audits.

It supports two paths:

- `quick`: local deterministic audit
- `audit`: Claude-led audit with specialist review and live verification

## What it does

GEOsphere can:

- collect site artifacts from homepage, sitemap, robots.txt, and sampled pages
- analyze technical, content, schema, entity, and platform issues
- inspect `llms.txt` and generate draft `llms.txt` outputs
- compare runs and benchmark sites
- save manager-facing markdown reports
- generate PDF reports from a structured manager brief

## Main workflow

### `quick`

Use `quick` for a fast local pass.

### `audit`

Use `audit` for the full Claude Code workflow:

1. GEOsphere collects artifacts into a run directory.
2. Claude reviews the collected evidence.
3. Specialists verify technical, content, schema, and entity issues.
4. Claude returns the final audit.
5. Claude can save:
   - `manager-report.md`
   - `manager-brief.json`
   - PDF output

## Requirements

- Python 3.10+
- Claude Code if you want `/geosphere ...`

## Install

### Windows

```powershell
cd C:\path\to\GEOsphere
python -m pip install -e .[dev]
```

### macOS

```bash
cd /path/to/GEOsphere
python3 -m pip install -e '.[dev]'
```

## Local usage

### Windows

```powershell
cd C:\path\to\GEOsphere
$env:PYTHONPATH='src'
python -m geosphere quick https://example.com
python -m geosphere collect https://example.com --max-pages 50
python -m geosphere report-pdf runs\<run-id>
python -m pytest -q
```

### macOS

```bash
cd /path/to/GEOsphere
export PYTHONPATH=src
python3 -m geosphere quick https://example.com
python3 -m geosphere collect https://example.com --max-pages 50
python3 -m geosphere report-pdf runs/<run-id>
python3 -m pytest -q
```

## Claude Code usage

Install the skill:

### Windows

```powershell
cd C:\path\to\GEOsphere
$env:PYTHONPATH='src'
python -m geosphere install-skill
```

### macOS

```bash
cd /path/to/GEOsphere
export PYTHONPATH=src
python3 -m geosphere install-skill
```

Then restart Claude Code and use:

```text
/geosphere audit https://example.com
/geosphere quick https://example.com
```

## Run directory

Collection runs write files such as:

- `collection.json`
- `collection.md`
- `profile.json`
- `pages.json`
- `robots.json`
- `sitemap.json`
- `llms-status.json`
- `llms.txt`
- `llms-full.txt`

Saved final audit outputs can also include:

- `manager-report.md`
- `manager-brief.json`
- PDF output

## Commands

```text
python -m geosphere collect <url> --max-pages 50
python -m geosphere audit <url>
python -m geosphere quick <url>
python -m geosphere inspect <url>
python -m geosphere llms <url>
python -m geosphere report-pdf <run-dir-or-json>
python -m geosphere compare <left-run> <right-run>
python -m geosphere benchmark <primary-url> <competitor-url> [more]
python -m geosphere install-skill
```

## Project layout

```text
src/geosphere/           Python runtime
geosphere/               Claude Code skill and specialist playbooks
tests/                   test suite
examples/                small example inputs
```

## Sample run structure

A completed audit run directory looks like this:

```text
runs/
└── 20260101T120000Z-example-com/
    ├── collection.json          # collection outcome
    ├── collection.md            # collection markdown
    ├── profile.json             # site profile
    ├── pages.json               # per-page snapshots
    ├── robots.json              # robots.txt data
    ├── sitemap.json             # sitemap data
    ├── llms-status.json         # llms.txt check
    ├── llms.txt                 # generated draft
    ├── llms-full.txt            # detailed generated draft
    ├── audit.json               # engine audit outcome (secondary)
    ├── audit.md                 # engine audit markdown (secondary)
    ├── manager-report.md        # final Claude synthesis (primary)
    ├── manager-brief.json       # structured brief for PDF
    ├── GEOsphere-Executive-Brief.pdf
    └── artifacts/
        ├── pages/               # raw HTML artifacts
        └── meta/
```

The `manager-report.md` and `manager-brief.json` are the primary outputs from a Claude-led audit. The engine outputs (`audit.json`, `audit.md`) are secondary evidence.

## License

MIT — see [LICENSE](LICENSE).
