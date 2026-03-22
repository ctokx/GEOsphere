from __future__ import annotations

from statistics import mean

from geosphere.contracts import ModuleScore, SiteProfile


class TechnicalAnalyzer:
    def analyze(self, profile: SiteProfile, weight: float) -> ModuleScore:
        pages = profile.pages
        findings: list[dict[str, str]] = []
        recommendations: list[str] = []
        score = 100
        blocked = [agent for agent, status in profile.robots.ai_access.items() if "blocked" in status]
        if blocked:
            score -= min(28, len(blocked) * 4)
            findings.append({"severity": "high", "title": "AI crawler restrictions", "detail": ", ".join(blocked[:6])})
            recommendations.append("Allow core AI crawlers in robots.txt unless a specific licensing policy requires restriction.")
        if not profile.robots.found:
            score -= 8
            findings.append({"severity": "medium", "title": "robots.txt missing", "detail": "No robots.txt response was found."})
            recommendations.append("Publish a robots.txt file with explicit sitemap references and AI crawler policy.")
        if not profile.sitemap.discovered_urls:
            score -= 8
            findings.append({"severity": "medium", "title": "sitemap coverage weak", "detail": "No crawlable XML sitemap was discovered."})
            recommendations.append("Publish an XML sitemap and reference it from robots.txt.")
        canonical_missing = sum(1 for page in pages if not page.meta.canonical and page.status_code == 200)
        if canonical_missing:
            score -= min(12, canonical_missing * 2)
            findings.append({"severity": "medium", "title": "canonical gaps", "detail": f"{canonical_missing} analyzed pages lacked canonical tags."})
            recommendations.append("Add self-referencing canonical tags to every indexable page.")
        noindex_pages = sum(1 for page in pages if "noindex" in page.meta.robots.lower())
        if noindex_pages:
            score -= min(14, noindex_pages * 4)
            findings.append({"severity": "high", "title": "index suppression", "detail": f"{noindex_pages} analyzed pages contain noindex directives."})
            recommendations.append("Review noindex usage on revenue and authority pages.")
        csr_pages = [page.url for page in pages if page.signals.get("possible_csr")]
        if csr_pages:
            score -= min(18, len(csr_pages) * 4)
            findings.append({"severity": "high", "title": "rendering risk", "detail": f"{len(csr_pages)} pages appear to rely on client-side rendering."})
            recommendations.append("Ensure critical content, metadata, structured data, and links are present in raw HTML.")
        slow_pages = [page.elapsed_ms for page in pages if page.elapsed_ms]
        if slow_pages:
            avg_ms = int(mean(slow_pages))
            if avg_ms > 2500:
                score -= 10
                findings.append({"severity": "medium", "title": "slow response times", "detail": f"Average response time was {avg_ms} ms."})
                recommendations.append("Reduce server response time and remove render-blocking assets from top templates.")
        security_failures = 0
        for page in pages[:3]:
            sec = page.signals.get("security_headers", {})
            required = ["Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"]
            missing = sum(1 for item in required if not sec.get(item))
            security_failures += missing
        if security_failures:
            score -= min(12, security_failures)
            findings.append({"severity": "medium", "title": "security header gaps", "detail": f"{security_failures} missing high-value security headers were detected on sampled pages."})
            recommendations.append("Add HSTS, X-Content-Type-Options, X-Frame-Options, and Referrer-Policy at the edge.")
        if any(not page.signals.get("has_viewport") for page in pages[:3]):
            score -= 6
            findings.append({"severity": "medium", "title": "mobile viewport missing", "detail": "At least one sampled page lacks a viewport tag."})
            recommendations.append("Add a responsive viewport meta tag to every public template.")
        render_info = profile.overview.get("render_probe", {})
        if render_info.get("enabled") and render_info.get("available") and not render_info.get("error"):
            homepage = pages[0] if pages else None
            if homepage and homepage.meta.title and render_info.get("rendered_title") and homepage.meta.title != render_info.get("rendered_title"):
                score -= 4
                findings.append({"severity": "medium", "title": "rendered title diverges from raw HTML", "detail": "The rendered page title does not match the raw HTML title, which can confuse crawlers."})
                recommendations.append("Keep critical metadata identical between raw HTML and rendered output.")
        if render_info.get("enabled") and not render_info.get("available"):
            findings.append({"severity": "low", "title": "render probe unavailable", "detail": "Playwright is not installed, so rendered-vs-raw checks were skipped."})
            recommendations.append("Install the render extra and Playwright browsers to unlock browser-level validation.")
        og_missing = sum(1 for page in pages if page.status_code == 200 and not page.signals.get("has_open_graph"))
        if og_missing:
            score -= min(10, og_missing)
            findings.append({"severity": "medium", "title": "Open Graph metadata gaps", "detail": f"{og_missing} analyzed pages lacked Open Graph metadata."})
            recommendations.append("Add og:title, og:description, og:type, og:url, and og:image to public templates.")
        twitter_missing = sum(1 for page in pages if page.status_code == 200 and not page.signals.get("has_twitter_cards"))
        if twitter_missing:
            score -= min(6, twitter_missing)
            findings.append({"severity": "low", "title": "Twitter card coverage weak", "detail": f"{twitter_missing} analyzed pages lacked Twitter card metadata."})
            recommendations.append("Add twitter:card and aligned social preview tags to article and landing page templates.")
        math_runtime_pages = [page.url for page in pages if page.signals.get("has_math_runtime")]
        if math_runtime_pages:
            score -= min(8, len(math_runtime_pages))
            findings.append({"severity": "medium", "title": "math rendering depends on runtime scripts", "detail": f"{len(math_runtime_pages)} pages appear to depend on client-side math rendering."})
            recommendations.append("Pre-render mathematical notation to static HTML or MathML so non-browser agents can read it.")
        if not any(page.signals.get("has_feed_link") for page in pages[:2]):
            findings.append({"severity": "low", "title": "feed discovery missing", "detail": "No RSS or Atom link tag was detected on sampled pages."})
            recommendations.append("Publish a discoverable RSS or Atom feed and expose it via a link tag in the head.")
        image_gaps = sum(1 for page in pages for image in page.images if not image.alt)
        if image_gaps:
            score -= min(8, image_gaps)
            findings.append({"severity": "low", "title": "image accessibility gaps", "detail": f"{image_gaps} sampled images lacked alt text."})
            recommendations.append("Add descriptive alt text for informative images and product visuals.")
        recurring = self._recurring_issues(pages)
        for issue in recurring:
            findings.append(issue)
        score = max(0, min(100, score))
        summary = "Crawl access, indexability, rendering, and security were evaluated against machine-readability requirements."
        evidence = {
            "blocked_agents": blocked,
            "robots_found": profile.robots.found,
            "sitemap_urls": len(profile.sitemap.discovered_urls),
            "possible_csr_pages": csr_pages[:10],
            "math_runtime_pages": math_runtime_pages[:10],
            "recurring_issues": recurring,
        }
        return ModuleScore("technical", score, weight, summary, findings, recommendations, evidence)

    def _recurring_issues(self, pages):
        results = []
        canonical_missing_pages = [page.url for page in pages if page.status_code == 200 and not page.signals.get("has_canonical")]
        if len(canonical_missing_pages) >= 3:
            results.append({"severity": "medium", "title": "recurring canonical omission", "detail": f"Canonical tags are missing on {len(canonical_missing_pages)} sampled pages, which suggests a template-level issue."})
        og_missing_pages = [page.url for page in pages if page.status_code == 200 and not page.signals.get("has_open_graph")]
        if len(og_missing_pages) >= 3:
            results.append({"severity": "medium", "title": "recurring social metadata omission", "detail": f"Open Graph metadata is missing on {len(og_missing_pages)} sampled pages, indicating incomplete base templates."})
        undated_pages = [page.url for page in pages if page.status_code == 200 and not page.signals.get("has_dates") and page.signals.get("article_like")]
        if len(undated_pages) >= 3:
            results.append({"severity": "medium", "title": "recurring article date omission", "detail": f"{len(undated_pages)} article-like pages lacked visible date signals, suggesting the article template does not expose freshness metadata."})
        return results
