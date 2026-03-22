from __future__ import annotations

from geosphere.contracts import ModuleScore, SiteProfile


class SchemaAnalyzer:
    def analyze(self, profile: SiteProfile, weight: float) -> ModuleScore:
        findings: list[dict[str, str]] = []
        recommendations: list[str] = []
        total_blocks = sum(len(page.structured_data) for page in profile.pages)
        valid_jsonld = sum(
            1
            for page in profile.pages
            for item in page.structured_data
            if item.syntax == "json-ld" and item.valid
        )
        same_as_links = 0
        organization_present = False
        article_present = False
        business_specific = False
        issues = 0
        article_schema_issues = 0
        person_schema_issues = 0
        publisher_person_count = 0
        missing_article_images = 0
        inverted_author_names = 0
        missing_speakable = 0
        missing_org_logo = 0
        recurring_issue_counts: dict[str, int] = {}
        sample_schema_pages: list[dict[str, str]] = []
        for page in profile.pages:
            for item in page.structured_data:
                schema_type = item.schema_type.lower()
                if "organization" in schema_type or "localbusiness" in schema_type or "person" in schema_type:
                    organization_present = True
                    payload = item.payload if isinstance(item.payload, dict) else {}
                    same_as = payload.get("sameAs", []) if isinstance(payload, dict) else []
                    if isinstance(same_as, list):
                        same_as_links += len(same_as)
                if "article" in schema_type or "blogposting" in schema_type or "newsarticle" in schema_type:
                    article_present = True
                if any(term in schema_type for term in ("product", "softwareapplication", "service", "faqpage", "breadcrumbs", "website")):
                    business_specific = True
                if not item.valid:
                    issues += 1
                payloads = self._flatten_payload(item.payload)
                for payload in payloads:
                    payload_type = str(payload.get("@type", "")).lower()
                    if payload_type in {"article", "blogposting", "newsarticle", "techarticle"}:
                        article_present = True
                        article_issues = self._article_issues(payload)
                        article_schema_issues += len(article_issues)
                        for issue in article_issues:
                            recurring_issue_counts[issue] = recurring_issue_counts.get(issue, 0) + 1
                        if payload.get("publisher", {}).get("@type", "").lower() == "person":
                            publisher_person_count += 1
                        if not payload.get("image"):
                            missing_article_images += 1
                        if not payload.get("speakable"):
                            missing_speakable += 1
                        author_name = self._extract_author_name(payload.get("author"))
                        if self._looks_inverted(author_name, profile.brand_name):
                            inverted_author_names += 1
                        if article_issues:
                            sample_schema_pages.append({"url": page.url, "issues": ", ".join(article_issues[:3])})
                    if payload_type == "person":
                        person_schema_issues += len(self._person_issues(payload))
                    if payload_type in {"organization", "localbusiness"} and not payload.get("logo"):
                        missing_org_logo += 1
        score = 20
        if organization_present:
            score += 22
        if article_present:
            score += 14
        if business_specific:
            score += 14
        score += min(16, same_as_links * 2)
        score += min(12, valid_jsonld * 4)
        score -= min(18, issues * 5)
        score -= min(20, article_schema_issues * 2)
        score -= min(10, person_schema_issues)
        score -= min(12, inverted_author_names * 2)
        score -= min(10, missing_speakable)
        score -= min(6, missing_org_logo * 2)
        if not organization_present:
            findings.append({"severity": "high", "title": "entity schema missing", "detail": "No Organization, LocalBusiness, or Person schema was detected."})
            recommendations.append("Publish a primary entity schema with name, url, description, logo, sameAs, and contact data.")
        if same_as_links < 3:
            findings.append({"severity": "medium", "title": "sameAs graph weak", "detail": f"Only {same_as_links} sameAs links were detected across the sampled schema graph."})
            recommendations.append("Expand sameAs coverage to authoritative profiles such as LinkedIn, YouTube, Wikidata, GitHub, or Crunchbase.")
        if not business_specific:
            findings.append({"severity": "medium", "title": "business-specific schema absent", "detail": "No product, service, software, FAQ, or article-specific schema was found."})
            recommendations.append("Add schema tailored to the site model such as Product, Service, SoftwareApplication, Article, or FAQPage.")
        if issues:
            findings.append({"severity": "medium", "title": "schema validation issues", "detail": f"{issues} malformed or invalid structured data blocks were detected."})
            recommendations.append("Validate JSON-LD blocks and keep them server-rendered in the initial HTML.")
        if publisher_person_count:
            findings.append({"severity": "high", "title": "article publisher typed as person", "detail": f"{publisher_person_count} article schema blocks use Person as publisher instead of Organization."})
            recommendations.append("Use Organization as publisher on articles and attach a stable logo and @id reference.")
        if missing_article_images:
            findings.append({"severity": "medium", "title": "article schema missing images", "detail": f"{missing_article_images} article schema blocks had no image property."})
            recommendations.append("Add a representative image to each article schema and align it with the Open Graph image.")
        if inverted_author_names:
            findings.append({"severity": "high", "title": "author naming inconsistent in schema", "detail": f"{inverted_author_names} article schema blocks appear to use a token-reordered author name."})
            recommendations.append("Normalize author name formatting across Person and Article schema blocks so the same entity is referenced consistently.")
        if missing_speakable:
            findings.append({"severity": "medium", "title": "speakable markup absent", "detail": f"{missing_speakable} article schema blocks lacked a speakable property."})
            recommendations.append("Add speakable selectors for intro summaries or key takeaway blocks on article pages.")
        if missing_org_logo:
            findings.append({"severity": "medium", "title": "organization logo missing in schema", "detail": f"{missing_org_logo} organization-like schema blocks lacked a logo property."})
            recommendations.append("Attach a stable logo to Organization or LocalBusiness schema to improve publisher validation.")
        if person_schema_issues:
            findings.append({"severity": "medium", "title": "person schema underpopulated", "detail": "Detected Person schema blocks are missing common authority properties such as jobTitle, description, image, or sameAs."})
            recommendations.append("Expand Person schema with jobTitle, description, image, worksFor, knowsAbout, and broader sameAs coverage.")
        for issue, count in sorted(recurring_issue_counts.items(), key=lambda item: item[1], reverse=True):
            if count >= 3:
                findings.append({"severity": "medium", "title": f"recurring schema defect: {issue}", "detail": f"The issue `{issue}` appeared on {count} schema blocks, indicating a template-level defect."})
        summary = "Structured data was audited for entity clarity, schema breadth, sameAs graph depth, and validity."
        evidence = {
            "total_blocks": total_blocks,
            "valid_jsonld": valid_jsonld,
            "same_as_links": same_as_links,
            "organization_present": organization_present,
            "article_present": article_present,
            "article_schema_issues": article_schema_issues,
            "person_schema_issues": person_schema_issues,
            "inverted_author_names": inverted_author_names,
            "missing_speakable": missing_speakable,
            "recurring_issue_counts": recurring_issue_counts,
            "sample_schema_pages": sample_schema_pages[:8],
        }
        return ModuleScore("schema", max(0, min(100, score)), weight, summary, findings, recommendations, evidence)

    def _flatten_payload(self, payload):
        if isinstance(payload, list):
            results = []
            for item in payload:
                results.extend(self._flatten_payload(item))
            return results
        if isinstance(payload, dict):
            if "@graph" in payload and isinstance(payload["@graph"], list):
                results = []
                for item in payload["@graph"]:
                    results.extend(self._flatten_payload(item))
                return results
            return [payload]
        return []

    def _article_issues(self, payload: dict) -> list[str]:
        issues = []
        for field in ("headline", "author", "publisher"):
            if field not in payload:
                issues.append(f"missing_{field}")
        if not payload.get("image"):
            issues.append("missing_image")
        author = payload.get("author")
        if isinstance(author, dict) and not author.get("name"):
            issues.append("missing_author_name")
        publisher = payload.get("publisher")
        if isinstance(publisher, dict) and publisher.get("@type", "").lower() != "organization":
            issues.append("publisher_not_organization")
        return issues

    def _person_issues(self, payload: dict) -> list[str]:
        required = ("name", "sameAs", "description", "jobTitle", "image")
        return [f"missing_{field}" for field in required if not payload.get(field)]

    def _extract_author_name(self, author) -> str:
        if isinstance(author, dict):
            return str(author.get("name", ""))
        if isinstance(author, list) and author and isinstance(author[0], dict):
            return str(author[0].get("name", ""))
        if isinstance(author, str):
            return author
        return ""

    def _looks_inverted(self, candidate: str, expected: str) -> bool:
        candidate_tokens = [token.lower() for token in candidate.split() if token]
        expected_tokens = [token.lower() for token in expected.split() if token]
        if len(candidate_tokens) < 2 or len(candidate_tokens) != len(expected_tokens):
            return False
        return sorted(candidate_tokens) == sorted(expected_tokens) and candidate_tokens != expected_tokens
