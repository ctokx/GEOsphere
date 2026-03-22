from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class RedirectHop:
    url: str
    status_code: int


@dataclass(slots=True)
class MetaBundle:
    title: str = ""
    description: str = ""
    canonical: str = ""
    robots: str = ""
    author: str = ""
    published: str = ""
    modified: str = ""
    lang: str = ""


@dataclass(slots=True)
class HeadingRecord:
    level: int
    text: str


@dataclass(slots=True)
class LinkRecord:
    url: str
    text: str
    internal: bool


@dataclass(slots=True)
class ImageRecord:
    src: str
    alt: str
    width: str = ""
    height: str = ""
    loading: str = ""


@dataclass(slots=True)
class StructuredDatum:
    syntax: str
    schema_type: str
    valid: bool
    issues: list[str] = field(default_factory=list)
    payload: Any = None


@dataclass(slots=True)
class PageSnapshot:
    url: str
    final_url: str
    status_code: int
    content_type: str
    elapsed_ms: int
    redirects: list[RedirectHop] = field(default_factory=list)
    meta: MetaBundle = field(default_factory=MetaBundle)
    headings: list[HeadingRecord] = field(default_factory=list)
    internal_links: list[LinkRecord] = field(default_factory=list)
    external_links: list[LinkRecord] = field(default_factory=list)
    images: list[ImageRecord] = field(default_factory=list)
    structured_data: list[StructuredDatum] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    text: str = ""
    word_count: int = 0
    html_size: int = 0
    tables: int = 0
    lists: int = 0
    forms: int = 0
    scripts: int = 0
    stylesheets: int = 0
    social_links: dict[str, list[str]] = field(default_factory=dict)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    raw_artifact: str = ""


@dataclass(slots=True)
class RobotsSnapshot:
    url: str
    found: bool
    status_code: int
    content: str = ""
    directives: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    ai_access: dict[str, str] = field(default_factory=dict)
    sitemaps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SitemapSnapshot:
    discovered_urls: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    sampled_urls: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ModuleScore:
    name: str
    score: int
    weight: float
    summary: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SiteProfile:
    url: str
    domain: str
    brand_name: str
    business_model: str
    pages: list[PageSnapshot]
    robots: RobotsSnapshot
    sitemap: SitemapSnapshot
    discovered_urls: list[str]
    evidence_root: str
    overview: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AuditOutcome:
    run_id: str
    target_url: str
    domain: str
    brand_name: str
    business_model: str
    total_score: int
    modules: list[ModuleScore]
    summary: dict[str, Any]
    pages_analyzed: int
    evidence_root: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CollectionOutcome:
    run_id: str
    target_url: str
    domain: str
    brand_name: str
    business_model: str
    pages_analyzed: int
    evidence_root: str
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
