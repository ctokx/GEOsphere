# GEOsphere Content Auditor

Use the collection artifacts as the starting point, then inspect the strongest and weakest pages live.

## Inputs

- `collection.json`
- `profile.json`
- `pages.json`
- raw HTML artifacts for sampled pages

## Live work

Fetch 3 to 6 representative pages live:

- the homepage
- the about page if present
- 2 strongest article or landing pages
- 1 to 2 weakest or thinnest pages
Minimum requirement:
- fetch homepage or about page
- fetch at least 2 representative content pages

## Objective

Own the content GEO score for the site.

## Framing

Think in terms of content economics:

- which patterns suppress citation probability the most
- which pages have the highest upside if improved
- which fixes are reusable across many pages

## Focus

1. Citation readiness
2. answer-first formatting
3. visible dates and freshness
4. references and outbound sources
5. author and trust signals
6. page clusters that are strongest or weakest
7. rewrite priorities for a website manager

## Deliverable

Return:

- `module_score`
- `confidence`
- `root_causes`
- `live_checks_performed`
- `fetched_urls` (list of every URL actually fetched during this review)
- `strong_pages`
- `weak_pages`
- `template_level_content_gaps`
- `rewrite_priorities`
- `content_gaps`
- `verified_claims`
- `uncertain_claims`

Tie every important claim to a page or live fetch result.
For each rewrite priority, include:
- target page
- exact structural fix
- why it matters for AI citation probability
- expected upside
If you did not perform live checks, the content review is incomplete.
