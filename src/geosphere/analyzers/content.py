from __future__ import annotations

import re
from statistics import mean

from geosphere.contracts import ModuleScore, SiteProfile
from geosphere.helpers import text_words


class ContentAnalyzer:
    def analyze(self, profile: SiteProfile, weight: float) -> ModuleScore:
        findings: list[dict[str, str]] = []
        recommendations: list[str] = []
        page_scores: list[int] = []
        stale_pages = 0
        author_pages = 0
        citation_gaps = 0
        thin_pages = 0
        reference_section_gaps = 0
        low_structure_pages = 0
        page_details = []
        for page in profile.pages:
            if page.status_code != 200:
                continue
            page_score = 40
            if page.word_count >= 700:
                page_score += 10
            if page.word_count >= 1400:
                page_score += 8
            if page.word_count < 500:
                thin_pages += 1
            if page.signals.get("question_headings", 0):
                page_score += min(12, page.signals["question_headings"] * 3)
            if page.signals.get("heading_depth", 0) < 3 and page.word_count > 800:
                low_structure_pages += 1
            strong_paragraphs = 0
            stats_count = 0
            for paragraph in page.paragraphs[:30]:
                words = len(text_words(paragraph))
                if 80 <= words <= 220:
                    strong_paragraphs += 1
                if re.search(r"\b\d+(?:\.\d+)?%|\$\d|\b20\d{2}\b", paragraph):
                    stats_count += 1
            page_score += min(15, strong_paragraphs * 2)
            page_score += min(8, stats_count * 2)
            external_citations = sum(
                1
                for link in page.external_links
                if not any(domain in link.url.lower() for domain in ("linkedin.com", "github.com", "youtube.com", "twitter.com", "x.com", "facebook.com", "instagram.com"))
            )
            if external_citations:
                page_score += min(10, external_citations * 2)
            else:
                citation_gaps += 1
            if page.signals.get("has_references_section"):
                page_score += 6
            elif page.signals.get("article_like"):
                reference_section_gaps += 1
            if page.meta.author or page.signals.get("has_author"):
                page_score += 7
                author_pages += 1
            if page.meta.published or page.meta.modified:
                page_score += 5
            else:
                stale_pages += 1
            if page.signals.get("has_about_link"):
                page_score += 3
            if page.signals.get("has_contact_link"):
                page_score += 2
            if any("/privacy" in link.url for link in page.internal_links):
                page_score += 2
            filler = sum(1 for paragraph in page.paragraphs[:20] if re.search(r"\b(in today's world|it is important to note|at the end of the day)\b", paragraph, re.I))
            page_score -= min(8, filler * 2)
            final_page_score = max(0, min(100, page_score))
            page_scores.append(final_page_score)
            page_details.append(
                {
                    "url": page.url,
                    "score": final_page_score,
                    "word_count": page.word_count,
                    "external_citations": external_citations,
                    "has_dates": bool(page.meta.published or page.meta.modified),
                    "question_headings": page.signals.get("question_headings", 0),
                    "has_references_section": page.signals.get("has_references_section", False),
                }
            )
        score = int(mean(page_scores)) if page_scores else 0
        if score < 55:
            findings.append({"severity": "high", "title": "weak citation readiness", "detail": "Content blocks are too thin, too generic, or poorly structured for extraction."})
            recommendations.append("Rewrite key pages with question-led sections, direct answer paragraphs, and evidence-backed claims.")
        if stale_pages:
            findings.append({"severity": "medium", "title": "freshness gaps", "detail": f"{stale_pages} sampled pages lacked visible publish or update dates."})
            recommendations.append("Display publish and last-updated dates on all key pages and keep them synchronized with structured data.")
        if citation_gaps:
            findings.append({"severity": "medium", "title": "source citation gaps", "detail": f"{citation_gaps} sampled pages lacked outbound citations to external references."})
            recommendations.append("Add cited sources, documentation links, papers, or benchmark references to technical articles and comparison pages.")
        if thin_pages:
            findings.append({"severity": "medium", "title": "thin content pockets", "detail": f"{thin_pages} sampled pages were under 500 words."})
            recommendations.append("Expand short pages with worked examples, references, tables, or practical implementation detail.")
        if reference_section_gaps:
            findings.append({"severity": "medium", "title": "reference sections absent", "detail": f"{reference_section_gaps} article-like pages lacked a references or sources section."})
            recommendations.append("Add explicit references or further-reading sections to article pages so claims can be verified quickly.")
        if low_structure_pages:
            findings.append({"severity": "low", "title": "long pages lack structural depth", "detail": f"{low_structure_pages} longer pages appear to stop at shallow heading depth."})
            recommendations.append("Introduce H3-level subsections, comparison tables, and example blocks in longer pages.")
        if author_pages == 0:
            findings.append({"severity": "high", "title": "author signals absent", "detail": "No author signal was detected on sampled content."})
            recommendations.append("Add bylines, credentials, author pages, and editorial ownership on articles and expertise pages.")
        top_pages = sorted(
            page_details,
            key=lambda item: (item["score"], item["external_citations"], item["word_count"]),
            reverse=True,
        )[:5]
        bottom_pages = sorted(page_details, key=lambda item: (item["score"], item["word_count"]))[:5]
        summary = "E-E-A-T, passage extractability, authorship, freshness, and structure were evaluated from collected pages."
        evidence = {
            "top_pages": top_pages,
            "bottom_pages": bottom_pages,
            "authored_pages": author_pages,
            "undated_pages": stale_pages,
            "citation_gap_pages": citation_gaps,
            "reference_section_gaps": reference_section_gaps,
        }
        return ModuleScore("content", score, weight, summary, findings, recommendations, evidence)
