from __future__ import annotations

from geosphere.contracts import ModuleScore, SiteProfile
from geosphere.external_authority import verify_entity_presence


class EntityAnalyzer:
    def analyze(self, profile: SiteProfile, weight: float, timeout: int, user_agent: str) -> ModuleScore:
        findings: list[dict[str, str]] = []
        recommendations: list[str] = []
        home = profile.pages[0] if profile.pages else None
        social_count = 0
        phones = 0
        emails = 0
        about_pages = 0
        contact_pages = 0
        external_presence: set[str] = set()
        social_index: dict[str, list[str]] = {}
        for page in profile.pages:
            social_count += sum(len(value) for value in page.social_links.values())
            phones += len(page.phones)
            emails += len(page.emails)
            if page.signals.get("has_about_link"):
                about_pages += 1
            if page.signals.get("has_contact_link"):
                contact_pages += 1
            for key, values in page.social_links.items():
                external_presence.add(key)
                social_index.setdefault(key, [])
                for value in values:
                    if value not in social_index[key]:
                        social_index[key].append(value)
        authority = verify_entity_presence(profile.brand_name, profile.domain, social_index, timeout, user_agent)
        score = 25
        score += min(16, len(external_presence) * 4)
        if phones:
            score += 10
        if emails:
            score += 8
        if about_pages:
            score += 10
        if contact_pages:
            score += 10
        if home and home.meta.description:
            score += 6
        if home and home.word_count > 300:
            score += 8
        if authority["wikipedia"]["present"]:
            score += 10
        if authority["wikidata"]["present"]:
            score += 8
        if authority["github"]["present"]:
            score += 6
        score += min(8, authority.get("hackernews", {}).get("mentions", 0) * 2)
        score += min(6, authority.get("reddit", {}).get("mentions", 0) * 2)
        if not phones and not emails:
            findings.append({"severity": "high", "title": "contact transparency weak", "detail": "No phone number or email signal was detected in sampled pages."})
            recommendations.append("Expose contact data clearly in header, footer, contact pages, and structured data.")
        if "linkedin" not in external_presence:
            findings.append({"severity": "medium", "title": "LinkedIn presence not linked", "detail": "No LinkedIn profile link was detected on-site."})
            recommendations.append("Link the primary LinkedIn page from the site and include it in sameAs.")
        if "youtube" not in external_presence:
            findings.append({"severity": "medium", "title": "YouTube signal absent", "detail": "No YouTube channel link was detected on-site."})
            recommendations.append("Launch a topic-aligned YouTube channel or link the existing channel from the site.")
        if not authority["has_independent_anchor"]:
            findings.append({"severity": "medium", "title": "independent entity references absent", "detail": "No Wikipedia or Wikidata references were detected from the sampled graph."})
            recommendations.append("Strengthen the entity graph with authoritative external references where the brand qualifies.")
        if authority.get("hackernews", {}).get("mentions", 0) == 0:
            findings.append({"severity": "low", "title": "no hacker news footprint detected", "detail": "No public Hacker News mentions were found for the domain."})
            recommendations.append("Promote flagship technical work where it can earn independent discussion and citations.")
        if authority.get("reddit", {}).get("mentions", 0) == 0:
            findings.append({"severity": "low", "title": "no reddit footprint detected", "detail": "No public Reddit mentions were found for the domain."})
            recommendations.append("Build authentic community discussion around standout content or tools in relevant subreddits.")
        if authority["github"]["present"] and authority["github"]["followers"] is not None and authority["github"]["followers"] < 25:
            findings.append({"severity": "low", "title": "developer authority still early", "detail": f"Linked GitHub presence exists but is still small at {authority['github']['followers']} followers."})
            recommendations.append("Promote flagship repositories and documentation to grow third-party recognition around the brand.")
        summary = "On-site entity signals, profile links, contact transparency, and ecosystem connectivity were evaluated."
        evidence = {
            "linked_platforms": sorted(external_presence),
            "email_count": emails,
            "phone_count": phones,
            "social_link_count": social_count,
            "authority": authority,
        }
        return ModuleScore("entity", max(0, min(100, score)), weight, summary, findings, recommendations, evidence)
