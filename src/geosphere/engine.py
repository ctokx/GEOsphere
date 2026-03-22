from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from geosphere.analyzers.content import ContentAnalyzer
from geosphere.analyzers.entity import EntityAnalyzer
from geosphere.analyzers.platforms import PlatformAnalyzer
from geosphere.analyzers.schema import SchemaAnalyzer
from geosphere.analyzers.technical import TechnicalAnalyzer
from geosphere.collector.http_probe import HttpProbe
from geosphere.collector.render_probe import RenderProbe
from geosphere.collector.robots import RobotsProbe
from geosphere.collector.sitemap import SitemapProbe
from geosphere.contracts import AuditOutcome, CollectionOutcome, ModuleScore, SiteProfile
from geosphere.discovery import DiscoveryPlanner
from geosphere.helpers import detect_business_model, infer_brand_name, now_run_id, slugify, write_json, write_text
from geosphere.llms_text import generate_llms, inspect_remote_llms
from geosphere.planning import build_action_plan
from geosphere.reporting import render_collection_markdown, render_markdown
from geosphere.settings import RuntimeOptions
from geosphere.storage import RunWorkspace


class AuditEngine:
    def __init__(self, options: RuntimeOptions) -> None:
        self.options = options

    def collect(self, url: str) -> CollectionOutcome:
        run_id, workspace, profile, llms_status, llms_generated = self._collect_site(url)
        summary = {
            "brand_name": profile.brand_name,
            "domain": profile.domain,
            "business_model": profile.business_model,
            "discovered_urls": len(profile.discovered_urls),
            "representative_urls": [page.url for page in profile.pages[:12]],
            "collection_health": profile.overview.get("collection_health", {}),
            "llms_status": llms_status,
            "render_probe": profile.overview.get("render_probe", {}),
        }
        outcome = CollectionOutcome(
            run_id=run_id,
            target_url=profile.url,
            domain=profile.domain,
            brand_name=profile.brand_name,
            business_model=profile.business_model,
            pages_analyzed=len(profile.pages),
            evidence_root=str(workspace.root),
            summary=summary,
        )
        self._write_collection_artifacts(workspace, profile, llms_status, llms_generated)
        write_json(workspace.data_path("collection.json"), outcome.to_dict())
        write_text(workspace.data_path("collection.md"), render_collection_markdown(outcome))
        return outcome

    def audit(self, url: str) -> AuditOutcome:
        run_id, workspace, profile, llms_status, llms_generated = self._collect_site(url)
        modules = self._analyze(profile)
        total_score = round(sum(module.score * module.weight for module in modules))
        collection_health = profile.overview.get("collection_health", {})
        if collection_health.get("status") != "ok":
            total_score = min(total_score, 35)
        action_plan = build_action_plan(modules)
        summary = self._summary(profile, modules, total_score, llms_status, action_plan)
        outcome = AuditOutcome(
            run_id=run_id,
            target_url=profile.url,
            domain=profile.domain,
            brand_name=profile.brand_name,
            business_model=profile.business_model,
            total_score=total_score,
            modules=modules,
            summary=summary,
            pages_analyzed=len(profile.pages),
            evidence_root=str(workspace.root),
        )
        self._write_collection_artifacts(workspace, profile, llms_status, llms_generated)
        write_json(workspace.data_path("audit.json"), outcome.to_dict())
        write_json(workspace.data_path("summary.json"), summary)
        write_text(workspace.data_path("audit.md"), render_markdown(outcome))
        return outcome

    def _collect_site(self, url: str) -> tuple[str, RunWorkspace, SiteProfile, dict[str, Any], dict[str, str]]:
        run_id = now_run_id() + "-" + slugify(urlparse(url).netloc or url)
        workspace = RunWorkspace(self.options.output_root, run_id)
        http = HttpProbe(self.options.request_timeout, self.options.user_agent, workspace)
        render_probe = RenderProbe(self.options.render_probe)
        robots_probe = RobotsProbe(self.options.request_timeout, self.options.user_agent, self.options.ai_agents)
        sitemap_probe = SitemapProbe(self.options.request_timeout, self.options.user_agent)
        homepage = http.fetch_page(url)
        robots = robots_probe.fetch(homepage.final_url)
        sitemap = sitemap_probe.fetch(homepage.final_url, robots.sitemaps, cap=max(self.options.max_pages * 4, 40))
        planner = DiscoveryPlanner(self.options.important_path_hints, self.options.max_pages)
        crawl_urls = planner.build(homepage, robots, sitemap)
        pages = []
        fetched = set()
        for item in crawl_urls:
            if item in fetched:
                continue
            fetched.add(item)
            pages.append(homepage if item == homepage.url else http.fetch_page(item))
        all_paths = [urlparse(page.url).path for page in pages]
        combined_text = " ".join(page.text[:3000] for page in pages[:4])
        business_model = detect_business_model(all_paths, combined_text)
        brand_name = infer_brand_name(homepage.meta.title, urlparse(homepage.final_url).netloc)
        profile = SiteProfile(
            url=homepage.final_url,
            domain=urlparse(homepage.final_url).netloc,
            brand_name=brand_name,
            business_model=business_model,
            pages=pages,
            robots=robots,
            sitemap=sitemap,
            discovered_urls=crawl_urls,
            evidence_root=str(workspace.root),
            overview=self._overview(pages),
        )
        profile.overview["collection_health"] = self._collection_health(profile)
        profile.overview["render_probe"] = render_probe.inspect(profile.url)
        llms_status = inspect_remote_llms(profile.url, self.options.request_timeout, self.options.user_agent)
        llms_generated = {
            "llms.txt": generate_llms(profile, detailed=False),
            "llms-full.txt": generate_llms(profile, detailed=True),
        }
        return run_id, workspace, profile, llms_status, llms_generated

    def _write_collection_artifacts(self, workspace: RunWorkspace, profile: SiteProfile, llms_status: dict[str, Any], llms_generated: dict[str, str]) -> None:
        write_json(workspace.data_path("robots.json"), {
            "url": profile.robots.url,
            "found": profile.robots.found,
            "status_code": profile.robots.status_code,
            "sitemaps": profile.robots.sitemaps,
            "ai_access": profile.robots.ai_access,
            "errors": profile.robots.errors,
        })
        write_json(workspace.data_path("sitemap.json"), {
            "source_urls": profile.sitemap.source_urls,
            "discovered_urls": profile.sitemap.discovered_urls,
            "errors": profile.sitemap.errors,
        })
        write_json(workspace.data_path("pages.json"), [
            {
                "url": page.url,
                "final_url": page.final_url,
                "status_code": page.status_code,
                "word_count": page.word_count,
                "elapsed_ms": page.elapsed_ms,
                "title": page.meta.title,
                "description": page.meta.description,
                "canonical": page.meta.canonical,
                "robots": page.meta.robots,
                "author": page.meta.author,
                "published": page.meta.published,
                "modified": page.meta.modified,
                "lang": page.meta.lang,
                "headings": [{"level": item.level, "text": item.text} for item in page.headings[:20]],
                "internal_links_count": len(page.internal_links),
                "external_links_count": len(page.external_links),
                "images_count": len(page.images),
                "tables": page.tables,
                "lists": page.lists,
                "forms": page.forms,
                "scripts": page.scripts,
                "question_headings": page.signals.get("question_headings", 0),
                "has_author": page.signals.get("has_author", False),
                "has_dates": page.signals.get("has_dates", False),
                "possible_csr": page.signals.get("possible_csr", False),
                "has_open_graph": page.signals.get("has_open_graph", False),
                "has_twitter_cards": page.signals.get("has_twitter_cards", False),
                "has_viewport": page.signals.get("has_viewport", False),
                "has_feed_link": page.signals.get("has_feed_link", False),
                "has_math_runtime": page.signals.get("has_math_runtime", False),
                "has_references_section": page.signals.get("has_references_section", False),
                "article_like": page.signals.get("article_like", False),
                "social_links": page.social_links,
                "structured_data": [
                    {
                        "syntax": item.syntax,
                        "schema_type": item.schema_type,
                        "valid": item.valid,
                        "issues": item.issues,
                    }
                    for item in page.structured_data
                ],
                "raw_artifact": page.raw_artifact,
                "errors": page.errors,
            }
            for page in profile.pages
        ])
        write_json(workspace.data_path("profile.json"), {
            "url": profile.url,
            "domain": profile.domain,
            "brand_name": profile.brand_name,
            "business_model": profile.business_model,
            "discovered_urls": profile.discovered_urls,
            "overview": profile.overview,
        })
        write_json(workspace.data_path("llms-status.json"), llms_status)
        write_text(workspace.data_path("llms.txt"), llms_generated["llms.txt"])
        write_text(workspace.data_path("llms-full.txt"), llms_generated["llms-full.txt"])

    def _analyze(self, profile: SiteProfile) -> list[ModuleScore]:
        technical = TechnicalAnalyzer().analyze(profile, self.options.platform_weights["technical"])
        content = ContentAnalyzer().analyze(profile, self.options.platform_weights["content"])
        schema = SchemaAnalyzer().analyze(profile, self.options.platform_weights["schema"])
        entity = EntityAnalyzer().analyze(profile, self.options.platform_weights["entity"], self.options.external_lookup_timeout, self.options.user_agent)
        module_index = {
            "technical": technical,
            "content": content,
            "schema": schema,
            "entity": entity,
        }
        platforms = PlatformAnalyzer().analyze(profile, self.options.platform_weights["platforms"], module_index)
        return [technical, content, schema, entity, platforms]

    def _overview(self, pages: list[Any]) -> dict[str, Any]:
        return {
            "urls": [page.url for page in pages],
            "status_codes": {page.url: page.status_code for page in pages},
            "word_counts": {page.url: page.word_count for page in pages},
        }

    def _summary(self, profile: SiteProfile, modules: list[ModuleScore], total_score: int, llms_status: dict[str, Any], action_plan: dict[str, Any]) -> dict[str, Any]:
        highlights = []
        weakest = sorted(modules, key=lambda item: item.score)[:2]
        strongest = sorted(modules, key=lambda item: item.score, reverse=True)[:2]
        for item in strongest:
            highlights.append(f"Strongest area: {item.name} scored {item.score}/100.")
        for item in weakest:
            highlights.append(f"Priority gap: {item.name} scored {item.score}/100 and needs concentrated improvement.")
        platform_scores = next((module.evidence.get("platform_scores", {}) for module in modules if module.name == "platforms"), {})
        return {
            "brand_name": profile.brand_name,
            "domain": profile.domain,
            "business_model": profile.business_model,
            "overall_score": total_score,
            "highlights": highlights,
            "platform_scores": platform_scores,
            "llms_status": llms_status,
            "action_plan": action_plan,
            "collection_health": profile.overview.get("collection_health", {}),
        }

    def _collection_health(self, profile: SiteProfile) -> dict[str, Any]:
        successful_pages = [page for page in profile.pages if page.status_code == 200 and page.word_count > 50]
        errored_pages = [page.url for page in profile.pages if page.errors or page.status_code == 0]
        if len(successful_pages) >= 3:
            return {"status": "ok", "successful_pages": len(successful_pages), "errored_pages": errored_pages[:10]}
        if successful_pages:
            return {"status": "partial", "successful_pages": len(successful_pages), "errored_pages": errored_pages[:10]}
        return {"status": "degraded", "successful_pages": 0, "errored_pages": errored_pages[:10]}
