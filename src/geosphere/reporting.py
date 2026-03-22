from __future__ import annotations

from geosphere.contracts import AuditOutcome, CollectionOutcome


def render_markdown(outcome: AuditOutcome) -> str:
    module_index = {module.name: module for module in outcome.modules}
    lines: list[str] = []
    lines.append(f"# GEOsphere Audit: {outcome.brand_name}")
    lines.append("")
    lines.append(f"- Target: {outcome.target_url}")
    lines.append(f"- Domain: {outcome.domain}")
    lines.append(f"- Business model: {outcome.business_model}")
    lines.append(f"- Overall score: {outcome.total_score}/100")
    lines.append("- Score note: Engine baseline — see manager-report.md for the calibrated Claude-led score if a full audit was run")
    lines.append(f"- Pages analyzed: {outcome.pages_analyzed}")
    lines.append("")
    collection_health = outcome.summary.get("collection_health", {})
    if collection_health and collection_health.get("status") != "ok":
        lines.append("## Collection Warning")
        lines.append("")
        lines.append(f"- Collection status: {collection_health.get('status')}")
        lines.append(f"- Successful pages: {collection_health.get('successful_pages', 0)}")
        errored = collection_health.get("errored_pages", [])
        if errored:
            for item in errored[:5]:
                lines.append(f"- Collection issue: {item}")
        lines.append("")
    lines.append("## Platform Readiness")
    lines.append("")
    platform_scores = outcome.summary.get("platform_scores", {})
    if platform_scores:
        lines.append("| Platform | Score |")
        lines.append("|---|---:|")
        for key, value in platform_scores.items():
            lines.append(f"| {key.replace('_', ' ').title()} | {value} |")
        lines.append("")
    lines.append("## Key Findings")
    lines.append("")
    strongest = sorted(outcome.modules, key=lambda item: item.score, reverse=True)[:2]
    weakest = sorted(outcome.modules, key=lambda item: item.score)[:3]
    lines.append("### Strengths")
    lines.append("")
    for module in strongest:
        lines.append(f"- {module.name.title()} is a relative strength at {module.score}/100.")
    lines.append("")
    lines.append("### Priority Gaps")
    lines.append("")
    for module in weakest:
        lines.append(f"- {module.name.title()} is limiting the overall score at {module.score}/100.")
        for finding in module.findings[:3]:
            lines.append(f"- {finding.get('title', '')}: {finding.get('detail', '')}")
    lines.append("")
    lines.append("## Severity Queue")
    lines.append("")
    for severity, heading in (("high", "Critical And High"), ("medium", "Medium"), ("low", "Low")):
        lines.append(f"### {heading}")
        lines.append("")
        bucket = []
        for module in outcome.modules:
            for finding in module.findings:
                if finding.get("severity") == severity:
                    bucket.append((module.name, finding))
        if not bucket:
            lines.append("- No findings.")
            lines.append("")
            continue
        for module_name, finding in bucket:
            lines.append(f"- **{module_name.title()}**: {finding.get('title', '')} — {finding.get('detail', '')}")
        lines.append("")
    lines.append("## Evidence Highlights")
    lines.append("")
    content_module = module_index.get("content")
    if content_module:
        lines.append("### Content Evidence")
        lines.append("")
        for item in content_module.evidence.get("top_pages", [])[:3]:
            lines.append(f"- Strong page: {item.get('url', '')} — score {item.get('score', '')}, words {item.get('word_count', '')}, citations {item.get('external_citations', '')}")
        for item in content_module.evidence.get("bottom_pages", [])[:3]:
            lines.append(f"- Weak page: {item.get('url', '')} — score {item.get('score', '')}, words {item.get('word_count', '')}, citations {item.get('external_citations', '')}")
        lines.append("")
    schema_module = module_index.get("schema")
    if schema_module:
        lines.append("### Schema Evidence")
        lines.append("")
        recurring = schema_module.evidence.get("recurring_issue_counts", {})
        for key, value in sorted(recurring.items(), key=lambda item: item[1], reverse=True)[:5]:
            lines.append(f"- {key}: {value} occurrences")
        if not recurring:
            lines.append("- No recurring schema defect clusters identified.")
        lines.append("")
    entity_module = module_index.get("entity")
    if entity_module:
        lines.append("### External Authority Evidence")
        lines.append("")
        authority = entity_module.evidence.get("authority", {})
        lines.append(f"- Wikipedia present: {authority.get('wikipedia', {}).get('present', False)}")
        lines.append(f"- Wikidata present: {authority.get('wikidata', {}).get('present', False)}")
        lines.append(f"- Hacker News mentions: {authority.get('hackernews', {}).get('mentions', 0)}")
        lines.append(f"- Reddit mentions: {authority.get('reddit', {}).get('mentions', 0)}")
        followers = authority.get("github", {}).get("followers")
        if followers is not None:
            lines.append(f"- GitHub followers: {followers}")
        lines.append("")
    lines.append("## Module Scores")
    lines.append("")
    lines.append("| Module | Score | Weight | Summary |")
    lines.append("|---|---:|---:|---|")
    for module in outcome.modules:
        lines.append(f"| {module.name} | {module.score} | {module.weight:.2f} | {module.summary} |")
    lines.append("")
    for module in outcome.modules:
        lines.append(f"## {module.name.title()}")
        lines.append("")
        lines.append(f"Score: **{module.score}/100**")
        lines.append("")
        if module.findings:
            lines.append("### Findings")
            lines.append("")
            for finding in module.findings:
                lines.append(f"- **{finding.get('severity', 'info').title()}**: {finding.get('title', '')} — {finding.get('detail', '')}")
            lines.append("")
        if module.recommendations:
            lines.append("### Recommendations")
            lines.append("")
            for item in module.recommendations:
                lines.append(f"- {item}")
            lines.append("")
        if module.name == "content":
            top_pages = module.evidence.get("top_pages", [])
            bottom_pages = module.evidence.get("bottom_pages", [])
            if top_pages:
                lines.append("### Highest-Leverage Pages")
                lines.append("")
                for item in top_pages:
                    lines.append(f"- {item.get('url', '')} — score {item.get('score', '')}, words {item.get('word_count', '')}, citations {item.get('external_citations', '')}")
                lines.append("")
            if bottom_pages:
                lines.append("### Weakest Pages")
                lines.append("")
                for item in bottom_pages:
                    lines.append(f"- {item.get('url', '')} — score {item.get('score', '')}, words {item.get('word_count', '')}, citations {item.get('external_citations', '')}")
                lines.append("")
        if module.name == "schema":
            sample_pages = module.evidence.get("sample_schema_pages", [])
            if sample_pages:
                lines.append("### Schema Validation Samples")
                lines.append("")
                for item in sample_pages:
                    lines.append(f"- {item.get('url', '')} — {item.get('issues', '')}")
                lines.append("")
        if module.name == "entity":
            authority = module.evidence.get("authority", {})
            lines.append("### Authority Signals")
            lines.append("")
            lines.append(f"- Wikipedia: {'present' if authority.get('wikipedia', {}).get('present') else 'missing'}")
            lines.append(f"- Wikidata: {'present' if authority.get('wikidata', {}).get('present') else 'missing'}")
            lines.append(f"- GitHub: {'present' if authority.get('github', {}).get('present') else 'missing'}")
            followers = authority.get("github", {}).get("followers")
            if followers is not None:
                lines.append(f"- GitHub followers: {followers}")
            lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    for item in outcome.summary.get("highlights", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Action Plan")
    lines.append("")
    action_plan = outcome.summary.get("action_plan", {})
    for section_name, heading in (
        ("quick_wins", "Quick Wins"),
        ("medium_term", "Medium-Term"),
        ("strategic", "Strategic"),
    ):
        lines.append(f"### {heading}")
        lines.append("")
        items = action_plan.get(section_name, [])
        if not items:
            lines.append("- No actions generated.")
            lines.append("")
            continue
        for item in items:
            lines.append(f"- **{item.get('module', '').title()}**: {item.get('action', '')} — {item.get('reason', '')}")
        lines.append("")
    lines.append("## llms.txt")
    lines.append("")
    llms_status = outcome.summary.get("llms_status", {})
    for key in ("llms_txt", "llms_full_txt"):
        status = llms_status.get(key, {})
        lines.append(f"- `{status.get('url', '')}`: {'present' if status.get('exists') else 'missing'}")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append("")
    lines.append(f"- Run ID: `{outcome.run_id}`")
    lines.append(f"- Domain: {outcome.domain}")
    lines.append(f"- Business model: {outcome.business_model}")
    lines.append(f"- Pages analyzed: {outcome.pages_analyzed}")
    lines.append("")
    lines.append("## Score Methodology")
    lines.append("")
    lines.append("The overall score is a weighted average of five module scores:")
    lines.append("")
    lines.append("| Module | Weight | Description |")
    lines.append("|---|---:|---|")
    for module in outcome.modules:
        desc = {
            "technical": "Crawlability, indexability, metadata, rendering",
            "content": "Citation readiness, E-E-A-T, freshness, depth",
            "schema": "Structured data completeness and validity",
            "entity": "External authority, disambiguation, sameAs graph",
            "platforms": "Platform-specific readiness across AI engines",
        }.get(module.name, module.summary)
        lines.append(f"| {module.name.title()} | {module.weight:.0%} | {desc} |")
    lines.append("")
    lines.append("For the full calibrated audit with specialist verification, run `/geosphere audit` in Claude Code.")
    lines.append("")
    lines.append("## Output")
    lines.append("")
    lines.append(f"- Evidence root: `{outcome.evidence_root}`")
    lines.append("")
    return "\n".join(lines)


def render_collection_markdown(outcome: CollectionOutcome) -> str:
    lines: list[str] = []
    lines.append(f"# GEOsphere Collection: {outcome.brand_name}")
    lines.append("")
    lines.append(f"- Target: {outcome.target_url}")
    lines.append(f"- Domain: {outcome.domain}")
    lines.append(f"- Business model: {outcome.business_model}")
    lines.append(f"- Pages analyzed: {outcome.pages_analyzed}")
    lines.append("")
    collection_health = outcome.summary.get("collection_health", {})
    lines.append("## Collection Status")
    lines.append("")
    lines.append(f"- Status: {collection_health.get('status', 'unknown')}")
    lines.append(f"- Successful pages: {collection_health.get('successful_pages', 0)}")
    for item in collection_health.get("errored_pages", [])[:5]:
        lines.append(f"- Collection issue: {item}")
    lines.append("")
    lines.append("## Crawl Overview")
    lines.append("")
    lines.append(f"- Discovered URLs: {outcome.summary.get('discovered_urls', 0)}")
    lines.append(f"- Pages saved: {outcome.pages_analyzed}")
    lines.append(f"- llms.txt present: {outcome.summary.get('llms_status', {}).get('llms_txt', {}).get('exists', False)}")
    lines.append(f"- llms-full.txt present: {outcome.summary.get('llms_status', {}).get('llms_full_txt', {}).get('exists', False)}")
    lines.append("")
    representative_urls = outcome.summary.get("representative_urls", [])
    if representative_urls:
        lines.append("## Representative URLs")
        lines.append("")
        for item in representative_urls[:12]:
            lines.append(f"- {item}")
        lines.append("")
    lines.append("## Use")
    lines.append("")
    lines.append("- Use these artifacts as an evidence pack for live specialist review.")
    lines.append(f"- Evidence root: `{outcome.evidence_root}`")
    lines.append("")
    return "\n".join(lines)
