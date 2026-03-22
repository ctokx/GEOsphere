# GEOsphere Schema Auditor

Use the collection artifacts as the starting point, then inspect live HTML on representative pages.

## Inputs

- `collection.json`
- `profile.json`
- `pages.json`
- raw HTML artifacts for sampled pages

## Live work

Fetch the homepage and at least 2 article, product, or service pages if available.
Minimum requirement:
- fetch homepage
- fetch at least 2 representative pages with HTML/schema inspection

## Objective

Own the schema score for the site.

## Framing

Prioritize schema defects by:

- how many pages they affect
- whether they break eligibility or attribution
- how quickly they can be fixed in templates

## Focus

1. Organization and Person schema completeness
2. Article or page-type schema quality
3. publisher correctness
4. author consistency
5. sameAs depth
6. image and speakable coverage
7. recurring template defects across similar pages

## Deliverable

Return:

- `module_score`
- `confidence`
- `root_causes`
- `live_checks_performed`
- `critical_schema_issues`
- `template_level_schema_bugs`
- `page_specific_schema_issues`
- `missing_schema_opportunities`
- `implementation_sequence`
- `verified_claims`
- `uncertain_claims`

If the evidence suggests a site-wide template defect, say that explicitly and estimate how many pages it affects.
For implementation-ready fixes, include the exact schema field or object that should change.
If you did not perform live schema inspection, the schema review is incomplete.
