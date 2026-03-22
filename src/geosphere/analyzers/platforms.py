from __future__ import annotations

from geosphere.contracts import ModuleScore, SiteProfile


class PlatformAnalyzer:
    def analyze(self, profile: SiteProfile, weight: float, module_index: dict[str, ModuleScore]) -> ModuleScore:
        content = module_index["content"].score
        technical = module_index["technical"].score
        schema = module_index["schema"].score
        entity = module_index["entity"].score
        home = profile.pages[0] if profile.pages else None
        question_headings = home.signals.get("question_headings", 0) if home else 0
        tables = sum(page.tables for page in profile.pages)
        dates = sum(1 for page in profile.pages if page.meta.published or page.meta.modified)
        social = module_index["entity"].evidence.get("linked_platforms", [])
        authority = module_index["entity"].evidence.get("authority", {})
        authority_bonus = 0
        if authority.get("wikipedia", {}).get("present"):
            authority_bonus += 10
        if authority.get("wikidata", {}).get("present"):
            authority_bonus += 8
        if authority.get("github", {}).get("present"):
            authority_bonus += 4
        chatgpt = round(entity * 0.3 + schema * 0.2 + technical * 0.2 + content * 0.3 + authority_bonus)
        aio = round(content * 0.35 + technical * 0.25 + schema * 0.15 + min(20, question_headings * 5) + min(5, tables))
        perplexity = round(content * 0.35 + entity * 0.25 + technical * 0.15 + min(15, dates * 3) + (10 if "reddit" in social else 0) + (6 if authority.get("wikipedia", {}).get("present") else 0))
        gemini = round(schema * 0.3 + entity * 0.2 + content * 0.25 + (12 if "youtube" in social else 0) + technical * 0.13 + (6 if authority.get("wikidata", {}).get("present") else 0))
        copilot = round(technical * 0.35 + entity * 0.2 + content * 0.2 + (10 if "linkedin" in social else 0) + schema * 0.15 + (4 if authority.get("github", {}).get("present") else 0))
        scores = {
            "google_ai_overviews": max(0, min(100, aio)),
            "chatgpt_search": max(0, min(100, chatgpt)),
            "perplexity": max(0, min(100, perplexity)),
            "gemini": max(0, min(100, gemini)),
            "bing_copilot": max(0, min(100, copilot)),
        }
        overall = round(sum(scores.values()) / len(scores))
        findings = []
        recommendations = []
        if scores["chatgpt_search"] < 55:
            findings.append({"severity": "medium", "title": "ChatGPT readiness limited", "detail": "Entity depth and authority cues are not yet strong enough for reliable citation."})
            recommendations.append("Expand sameAs coverage, authoritative references, and long-form canonical content for entity grounding.")
        if scores["google_ai_overviews"] < 55:
            findings.append({"severity": "medium", "title": "Google AIO extraction weak", "detail": "Question-led structure and direct answer formatting need improvement."})
            recommendations.append("Introduce query-shaped headings, answer-first paragraphs, tables, and dated updates on high-value pages.")
        if scores["gemini"] < 55:
            findings.append({"severity": "medium", "title": "Gemini ecosystem fit weak", "detail": "Schema breadth and Google-adjacent media signals are underdeveloped."})
            recommendations.append("Strengthen structured data and publish multimodal assets with strong on-site linking.")
        summary = "Platform readiness was modeled from deterministic technical, content, schema, and entity evidence."
        evidence = {"platform_scores": scores}
        return ModuleScore("platforms", overall, weight, summary, findings, recommendations, evidence)
