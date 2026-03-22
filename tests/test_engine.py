import json

from geosphere.compare import compare_audits, load_audit_payload
from geosphere.installer import install_skill
from geosphere.pdf_report import build_pdf_report, load_report_payload
from geosphere.analyzers.content import ContentAnalyzer
from geosphere.analyzers import entity as entity_module
from geosphere.analyzers.entity import EntityAnalyzer
from geosphere.analyzers.schema import SchemaAnalyzer
from geosphere.analyzers.technical import TechnicalAnalyzer
from geosphere.collector.http_probe import HttpProbe
from geosphere.contracts import RobotsSnapshot, SiteProfile, SitemapSnapshot
from geosphere.storage import RunWorkspace


HTML = """
<html lang="en">
  <head>
    <title>Orbital Labs | AI Search Intelligence</title>
    <meta name="description" content="Independent GEO platform for AI search visibility." />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta property="og:title" content="Orbital Labs" />
    <link rel="canonical" href="https://example.com/" />
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Orbital Labs",
        "url": "https://example.com",
        "sameAs": [
          "https://www.linkedin.com/company/orbital-labs",
          "https://www.youtube.com/@orbitallabs",
          "https://github.com/orbitallabs"
        ]
      }
    </script>
  </head>
  <body>
    <header>
      <a href="/about">About</a>
      <a href="/contact">Contact</a>
      <a href="/pricing">Pricing</a>
      <a href="/blog/geo-briefing">Blog</a>
      <a href="https://www.linkedin.com/company/orbital-labs">LinkedIn</a>
      <a href="https://www.youtube.com/@orbitallabs">YouTube</a>
    </header>
    <main>
      <h1>How AI search visibility works</h1>
      <h2>What is GEO?</h2>
      <p>Generative engine optimization is the practice of shaping pages so machine agents can discover, understand, and cite them without relying on browser-only execution.</p>
      <p>In 2026, teams that publish direct answers, explicit entities, and strong evidence structures outperform pages built around vague marketing language.</p>
      <h2>Why does structure matter?</h2>
      <p>According to internal benchmarking, pages that combine direct answers, tables, dates, and authorship are easier for retrieval systems to extract and rank with confidence.</p>
      <table><tr><td>signal</td><td>impact</td></tr></table>
      <img src="/hero.jpg" alt="GEO dashboard" width="1200" height="800" loading="eager" />
    </main>
    <footer>
      <a href="/privacy">Privacy</a>
      <a href="/terms">Terms</a>
      <p>Contact us at hello@example.com or +1 555 222 3333</p>
    </footer>
  </body>
</html>
"""


class StubResponse:
    def __init__(self, url: str, text: str, status_code: int = 200, headers: dict | None = None):
        self.url = url
        self.text = text
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "text/html", "X-Content-Type-Options": "nosniff"}
        self.history = []
        self.content = text.encode("utf-8")

        class Elapsed:
            def total_seconds(self) -> float:
                return 0.2

        self.elapsed = Elapsed()


def test_http_probe_extracts_core_signals(tmp_path, monkeypatch):
    workspace = RunWorkspace(tmp_path, "run-1")
    probe = HttpProbe(timeout=10, user_agent="test-agent", workspace=workspace)

    def fake_get(url, timeout, allow_redirects):
        return StubResponse(url, HTML)

    monkeypatch.setattr(probe.session, "get", fake_get)
    page = probe.fetch_page("https://example.com")
    assert page.meta.title == "Orbital Labs | AI Search Intelligence"
    assert page.meta.canonical == "https://example.com/"
    assert page.word_count > 40
    assert page.signals["has_viewport"] is True
    assert page.social_links["linkedin"]
    assert any(item.schema_type == "Organization" for item in page.structured_data)


def test_analyzers_return_scores(tmp_path, monkeypatch):
    workspace = RunWorkspace(tmp_path, "run-2")
    probe = HttpProbe(timeout=10, user_agent="test-agent", workspace=workspace)

    def fake_get(url, timeout, allow_redirects):
        return StubResponse(url, HTML)

    monkeypatch.setattr(probe.session, "get", fake_get)
    monkeypatch.setattr(
        entity_module,
        "verify_entity_presence",
        lambda brand_name, domain, social_links, timeout, user_agent: {
            "wikipedia": {"present": False},
            "wikidata": {"present": False},
            "github": {"present": True, "followers": 42},
            "has_independent_anchor": False,
        },
    )
    page = probe.fetch_page("https://example.com")
    profile = SiteProfile(
        url="https://example.com",
        domain="example.com",
        brand_name="Orbital Labs",
        business_model="saas",
        pages=[page],
        robots=RobotsSnapshot(
            url="https://example.com/robots.txt",
            found=True,
            status_code=200,
            ai_access={"GPTBot": "allowed", "ClaudeBot": "allowed"},
            directives={},
            sitemaps=["https://example.com/sitemap.xml"],
        ),
        sitemap=SitemapSnapshot(discovered_urls=["https://example.com/about"]),
        discovered_urls=["https://example.com"],
        evidence_root=str(workspace.root),
    )
    technical = TechnicalAnalyzer().analyze(profile, 0.22)
    content = ContentAnalyzer().analyze(profile, 0.24)
    schema = SchemaAnalyzer().analyze(profile, 0.16)
    entity = EntityAnalyzer().analyze(profile, 0.16, 5, "test-agent")
    assert technical.score > 40
    assert content.score > 40
    assert schema.score > 40
    assert entity.score > 40


def test_compare_payload_and_loader(tmp_path):
    left = {"run_id": "a", "brand_name": "Alpha", "total_score": 40, "modules": [{"name": "technical", "score": 50}]}
    right = {"run_id": "b", "brand_name": "Beta", "total_score": 65, "modules": [{"name": "technical", "score": 80}]}
    run_dir = tmp_path / "left-run"
    run_dir.mkdir()
    (run_dir / "audit.json").write_text(json.dumps(left), encoding="utf-8")
    loaded_left = load_audit_payload(str(run_dir))
    payload = compare_audits(loaded_left, right)
    assert payload["overall_delta"] == 25
    assert payload["module_deltas"]["technical"]["delta"] == 30


def test_install_skill_writes_resolved_file(tmp_path):
    project_root = tmp_path / "repo"
    project_root.mkdir()
    skill_source_dir = project_root / "geosphere"
    skill_source_dir.mkdir()
    (skill_source_dir / "SKILL.md").write_text("name: geosphere", encoding="utf-8")
    target = tmp_path / "skills" / "GEOsphere"
    installed = install_skill(project_root, target)
    assert installed.exists()
    assert "geosphere" in installed.read_text(encoding="utf-8")


def test_pdf_report_builds_from_custom_payload(tmp_path):
    payload_path = tmp_path / "manager-brief.json"
    payload_path.write_text(
        json.dumps(
            {
                "title": "GEOsphere Executive Brief",
                "brand_name": "Orbital Labs",
                "site_url": "https://example.com",
                "run_id": "run-123",
                "audited_at": "2026-03-22",
                "overall_score": 61,
                "confidence": "High",
                "executive_summary": "A concise operator summary.",
                "opportunity_snapshot": {
                    "current_score": "61 / 100",
                    "target_score_30d": "72 / 100",
                    "ceiling_score": "84 / 100",
                    "primary_win": "Fix entity and metadata layer",
                },
                "root_causes": ["Metadata gaps", "Weak external validation"],
                "module_scores": [
                    {"name": "Technical", "score": 72, "confidence": "High", "driver": "Good crawlability"},
                    {"name": "Content", "score": 55, "confidence": "High", "driver": "Needs references"},
                ],
                "platform_readiness": [
                    {"platform": "ChatGPT Web Search", "score": 58, "blocker": "No llms.txt"}
                ],
                "critical_issues": [
                    {
                        "title": "Missing llms.txt",
                        "detail": "No machine-readable site manifest is present.",
                        "scope": "Site-wide",
                        "verification_status": "Verified",
                        "fix_location": "Site root",
                        "effort": "30 min",
                        "expected_impact": "Improves AI discovery",
                    }
                ],
                "template_defects": [
                    {
                        "defect": "Missing llms.txt",
                        "scope": "Site-wide",
                        "fix": "Create /llms.txt",
                        "impact": "Improves AI discovery",
                    }
                ],
                "page_weaknesses": [
                    {
                        "page": "Homepage",
                        "issue": "Too thin for a trust anchor",
                        "priority": "High",
                        "action": "Expand homepage summary",
                    }
                ],
                "quick_wins": [
                    {"action": "Create llms.txt", "owner": "Dev", "effort": "30 min", "why": "Improves AI discovery", "upside": "Higher AI discovery confidence"}
                ],
                "plan_30_day": [{"phase": "Week 1", "items": ["Create llms.txt", "Fix schema"]}],
                "verification_notes": [{"claim": "llms.txt missing", "status": "Verified", "basis": "404 at /llms.txt"}],
                "implementation_appendix": [{"title": "Minimal llms.txt", "body": "# Orbital Labs\n\n## Key Pages\n- /"}],
                "final_remarks": "This report consolidates the strongest verified findings and the highest-leverage fixes.",
            }
        ),
        encoding="utf-8",
    )
    payload = load_report_payload(str(payload_path))
    output = tmp_path / "brief.pdf"
    built = build_pdf_report(payload, str(output))
    assert built.exists()
    assert built.stat().st_size > 0
