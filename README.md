# GEOsphere

GEOsphere is a Claude Code skill and Python runtime for GEO audits.

![GEOsphere](./geo.png)

It has two modes:

- `quick`: local deterministic audit
- `audit`: Claude-led review using collected artifacts and specialist agents

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

Expected audit flow:

1. GEOsphere collects artifacts into a run directory.
2. Claude reviews the artifacts and performs live verification.
3. Specialists analyze technical, content, schema, and entity issues.
4. Claude returns the final audit.
5. Claude can save `manager-report.md` and optionally generate a PDF.

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

If you save the final Claude output, the run directory can also contain:

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
