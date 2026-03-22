---
name: geosphere
description: Claude-first GEOsphere audit command for Claude Code. Use for deep GEO audits, llms generation, run comparisons, benchmarking, and website-manager-grade action plans.
allowed-tools: Read, Grep, Glob, Bash, Write, WebFetch
---

# geosphere

Use this slash skill as `/geosphere ...`.

## Commands

- `/geosphere audit <url>`
- `/geosphere quick <url>`
- `/geosphere inspect <url>`
- `/geosphere llms <url>`
- `/geosphere report-pdf <run-dir-or-json>`
- `/geosphere compare <left-run> <right-run>`
- `/geosphere benchmark <primary-url> <competitor-url> [more]`

If the user provides only a URL such as `/geosphere https://site.com`, treat it as `/geosphere audit https://site.com`.

## Local runtime

Run from:

`C:/Users/varol/Desktop/geo/GEOsphere`

## Execution mapping

- `audit` -> `python -m geosphere collect <url> --max-pages 50`
- `quick` -> `python -m geosphere quick <url>`
- `inspect` -> `python -m geosphere inspect <url>`
- `llms` -> `python -m geosphere llms <url>`
- `report-pdf` -> `python -m geosphere report-pdf <run-dir-or-json>`
- `compare` -> `python -m geosphere compare <left-run> <right-run>`
- `benchmark` -> `python -m geosphere benchmark <primary-url> <competitor-url> [more]`

## Operating model

`quick` is engine-first.

`audit` is Claude-first.

For `audit`, the Python runtime is an evidence collector, not the final judge. Claude specialists own the real scoring, severity calls, and final action plan.

## Startup banner

When `/geosphere audit ...` starts, begin with a short GEOsphere banner before the first execution step.

Output this banner inside a fenced code block so the Claude Code UI renders it with fixed-width font and correct alignment:

````text
```
   ______ ______  ____                          __
  / ____// ____/ / __ \ ______ ____   _____   / /_   ___   _____ ___
 / / __ / __/   / / / // ___// __ \ / ___/  / __ \ / _ \ / ___// _ \
/ /_/ // /___  / /_/ /(__  )/ /_/ // /     / / / //  __// /   /  __/
\____//_____/  \____//____// .___//_/     /_/ /_/ \___//_/    \___/
                          /_/
```
````

Immediately below the code block, add one short line of plain text:

`GEOsphere audit starting. Collecting evidence and launching specialist review.`

## Behavior

### `quick`

1. Run the local command.
2. Read the generated artifacts if needed.
3. Return a concise summary.

### `audit`

This is the manager-grade mode and should feel materially deeper than `quick`.

1. Run:
   `python -m geosphere collect <url> --max-pages 50`
2. Read:
   - `collection.json`
   - `collection.md`
   - `profile.json`
   - `pages.json`
   - `robots.json`
   - `sitemap.json`
   - `llms-status.json`
3. Start with a discovery-verification pass before specialist launch:
   - identify the major page clusters from the sitemap and page inventory
   - choose 4 to 6 representative pages across homepage, about, strongest content, weakest content, and one or two edge cases
   - fetch those pages live
   - note any early contradictions between artifacts and live pages
4. Treat the collection artifacts as the starting evidence pack, not the ceiling.
5. Explicitly read these playbooks from the installed skill directory before launching specialists:
   - `C:/Users/varol/.claude/skills/geosphere/agents/technical-review.md`
   - `C:/Users/varol/.claude/skills/geosphere/agents/content-review.md`
   - `C:/Users/varol/.claude/skills/geosphere/agents/schema-review.md`
   - `C:/Users/varol/.claude/skills/geosphere/agents/entity-review.md`
6. Launch the four specialists in parallel. Each specialist MUST produce a visible block in the conversation before the synthesis begins, structured as:
   ```
   ### [Specialist Name] Review
   - URLs fetched live: [list]
   - Module score: [N]/100
   - Confidence: [high/medium/low]
   - Key findings: [2-4 bullets]
   ```
   These blocks confirm live work happened and provide the user visibility into specialist activity.
7. Specialists may use both:
   - the saved artifacts
   - fresh live fetches against the site and relevant third-party pages when needed
8. Specialist autonomy is mandatory:
   - each specialist owns its own verification path
   - each specialist must perform its own live checks, not only reason over shared notes
   - if a specialist returns with zero live verification and no explicit blocker, treat that work as incomplete
9. Minimum live verification per specialist:
   - Technical: robots.txt + homepage + at least 1 representative content page
   - Content: homepage/about + at least 2 representative content pages
   - Schema: homepage + at least 2 representative pages with raw HTML inspection
   - Entity: about page + at least 2 external or platform checks when available
10. Specialists should validate or overturn artifact impressions when live evidence justifies it.
11. If a specialist appears to have done no live work, relaunch or redirect that specialist with a stricter instruction rather than accepting a shallow pass.
12. Read the synthesis playbook from:
   - `C:/Users/varol/.claude/skills/geosphere/agents/executive-synthesis.md`
13. Run one synthesis pass after specialists finish.
14. Return a single manager-grade final audit with:
   - calibrated overall score
   - confidence
   - module scores owned by the specialists
   - critical and high-priority issues
   - template-level defects
   - page-level weaknesses
   - quick wins
   - 30-day plan
   - what should be fixed in templates versus page-by-page
   - appendix-style implementation guidance when a fix is straightforward
   - explicit scope counts for major recurring defects
   - verification labeling for important claims
15. At the end, ask one concise follow-up question covering both optional outputs:
   - whether the user wants the final synthesized audit saved as markdown
   - whether the user wants the PDF executive brief generated
16. If the user wants the markdown saved:
   - write the final synthesized audit to `manager-report.md` inside the run directory immediately
   - this markdown must reflect the final Claude synthesis, not the raw collection summary
   - do not ask again for confirmation — execute the write as the next action after the user replies yes
17. If the user wants the PDF:
   - write `manager-brief.json` into the run directory immediately — do not skip this step
   - that JSON must reflect the final synthesized audit, not the raw collection artifacts
   - include all of these keys with the exact types shown:
     - `title` — string
     - `brand_name` — string
     - `site_url` — string
     - `run_id` — string
     - `audited_at` — string (YYYY-MM-DD)
     - `overall_score` — integer
     - `confidence` — string
     - `executive_summary` — string
     - `opportunity_snapshot` — **object** with keys: `current_score`, `target_score_30d`, `ceiling_score`, `primary_win` (all strings)
     - `root_causes` — array of strings
     - `module_scores` — **array of objects**, each with: `name` (string), `score` (integer), `confidence` (string), `driver` (string, the primary driver sentence)
     - `platform_readiness` — array of objects, each with: `platform` (string), `score` or `readiness` (string), `blocker` (string)
     - `critical_issues` — array of objects, each with: `title`, `detail`, `scope`, `verification_status`, `fix_location`, `effort`, `expected_impact`
     - `template_defects` — array of objects, each with: `defect`, `scope`, `fix`, `impact`
     - `page_weaknesses` — array of objects, each with: `page`, `issue`, `priority`, `action`
     - `quick_wins` — array of objects, each with: `action`, `owner`, `effort`, `why`, `upside`
     - `plan_30_day` — array of objects, each with: `phase` (string label), `items` (array of strings)
     - `verification_notes` — array of objects, each with: `claim`, `status`, `basis`
     - `implementation_appendix` — **array of objects**, each with: `title` (string), `body` (string — plain text or pseudo-code, no nested JSON)
     - `final_remarks` — string
   - then immediately run: `python -m geosphere report-pdf <path-to-manager-brief.json>`
18. If the user wants both:
   - save `manager-report.md` first
   - save `manager-brief.json` second
   - then run the report-pdf command against that `manager-brief.json`
   - do not ask for further confirmation between these steps — execute them sequentially as a single action block

### `report-pdf`

1. Accept either:
   - a run directory
   - a JSON payload file
2. If generating immediately after an audit, always prefer writing a structured `manager-brief.json` into the run directory that reflects the calibrated final audit.
3. Then run:
   `python -m geosphere report-pdf <path-to-manager-brief.json>`
4. Return the PDF path and summarize what it contains.

### `benchmark`

1. Run `python -m geosphere collect <primary-url> --max-pages 50` for the primary site.
2. Run `python -m geosphere collect <competitor-url> --max-pages 20` for each competitor.
3. Read collection artifacts for all sites.
4. Run parallel specialist review on the primary site (full depth).
5. Run lighter specialist passes on competitors (technical + content minimum).
6. Produce a side-by-side comparison table:

   | Site | Overall | Technical | Content | Schema | Entity | Platforms |
   |---|---|---|---|---|---|---|
   | Primary | ... | ... | ... | ... | ... | ... |
   | Competitor 1 | ... | ... | ... | ... | ... | ... |

7. Highlight where the primary site leads, where it trails, and the highest-leverage gaps.
8. Offer to save `benchmark-report.md` in the primary run directory.
9. Offer to generate a PDF with the benchmark section included.

## Constraints

- Do not anchor the final answer on a deterministic engine score.
- If you mention any base engine output, label it explicitly as `Engine baseline (secondary):`.
- Never present the `audit.json` total_score as the GEO score — that is a deterministic heuristic. The calibrated specialist score is the GEO score.
- Prefer live specialist judgment over artifact heuristics when there is conflict and the live evidence is stronger.
- Do not invent evidence.
- Keep the final audit practical for a website manager, not just technically correct.
- Important claims should be either:
  - `verified` by live fetch and artifact agreement
  - `verified` by repeated artifact evidence across pages
  - clearly labeled as `inference`
- Every critical or high issue should include:
  - scope
  - why it matters
  - exact fix location or likely fix location
  - expected impact
- The audit should feel like parallel work by a professional team, not one analyst with four passive reviewers.
