from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from geosphere.contracts import HeadingRecord, ImageRecord, LinkRecord, MetaBundle, PageSnapshot, RedirectHop, StructuredDatum
from geosphere.helpers import absolutize, compact, normalize_url, same_domain, slugify, text_words
from geosphere.storage import RunWorkspace


class HttpProbe:
    def __init__(self, timeout: int, user_agent: str, workspace: RunWorkspace) -> None:
        self.timeout = timeout
        self.workspace = workspace
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def fetch_page(self, url: str) -> PageSnapshot:
        target = normalize_url(url)
        slug = slugify(urlparse(target).path or "home")
        html_path = self.workspace.page_html_path(slug)
        snapshot = PageSnapshot(
            url=target,
            final_url=target,
            status_code=0,
            content_type="",
            elapsed_ms=0,
            raw_artifact=str(html_path),
        )
        last_error = ""
        for attempt in range(3):
            try:
                response = self.session.get(target, timeout=self.timeout, allow_redirects=True)
                break
            except requests.RequestException as exc:
                last_error = str(exc)
                if attempt == 2:
                    snapshot.errors.append(last_error)
                    return snapshot
                time.sleep(0.4 * (attempt + 1))
        try:
            snapshot.final_url = normalize_url(response.url)
            snapshot.status_code = response.status_code
            snapshot.content_type = response.headers.get("Content-Type", "")
            snapshot.elapsed_ms = int(response.elapsed.total_seconds() * 1000)
            snapshot.redirects = [
                RedirectHop(url=normalize_url(item.url), status_code=item.status_code)
                for item in response.history
            ]
            html = response.text or ""
            snapshot.html_size = len(response.content or b"")
            html_path.write_text(html, encoding="utf-8", errors="ignore")
            content_type = snapshot.content_type.lower()
            if "xml" in content_type and "html" not in content_type:
                snapshot.errors.append("xml_response")
                return snapshot
            if "json" in content_type and "html" not in content_type:
                snapshot.errors.append("json_response")
                return snapshot
            if "html" not in content_type and not html.lstrip().startswith("<"):
                snapshot.errors.append("non_html_response")
                return snapshot
            soup = BeautifulSoup(html, "lxml")
            snapshot.meta = self._extract_meta(soup)
            snapshot.headings = self._extract_headings(soup)
            snapshot.structured_data = self._extract_structured_data(soup)
            snapshot.internal_links, snapshot.external_links = self._extract_links(snapshot.final_url, soup)
            snapshot.images = self._extract_images(soup)
            snapshot.social_links = self._extract_social_links(snapshot.external_links)
            snapshot.emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)))
            snapshot.phones = sorted(set(re.findall(r"\+?\d[\d\-\s().]{7,}\d", html)))
            snapshot.tables = len(soup.find_all("table"))
            snapshot.lists = len(soup.find_all(["ul", "ol"]))
            snapshot.forms = len(soup.find_all("form"))
            snapshot.scripts = len(soup.find_all("script"))
            snapshot.stylesheets = len(soup.find_all("link", rel=lambda v: v and "stylesheet" in str(v).lower()))
            snapshot.paragraphs = self._extract_paragraphs(soup)
            snapshot.text = " ".join(snapshot.paragraphs)
            snapshot.word_count = len(text_words(snapshot.text))
            snapshot.signals = self._extract_signals(snapshot, soup, response.headers)
            return snapshot
        except requests.RequestException as exc:
            snapshot.errors.append(str(exc))
            return snapshot

    def _extract_meta(self, soup: BeautifulSoup) -> MetaBundle:
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        meta = MetaBundle(title=title)
        html_tag = soup.find("html")
        if html_tag:
            meta.lang = html_tag.get("lang", "")
        for node in soup.find_all("meta"):
            key = (node.get("name") or node.get("property") or "").strip().lower()
            content = node.get("content", "").strip()
            if key == "description":
                meta.description = content
            elif key == "robots":
                meta.robots = content
            elif key in {"author", "article:author"}:
                meta.author = content
            elif key in {"article:published_time", "og:published_time"}:
                meta.published = content
            elif key in {"article:modified_time", "og:updated_time"}:
                meta.modified = content
        canonical = soup.find("link", rel=lambda v: v and "canonical" in str(v).lower())
        meta.canonical = canonical.get("href", "").strip() if canonical else ""
        return meta

    def _extract_headings(self, soup: BeautifulSoup) -> list[HeadingRecord]:
        items: list[HeadingRecord] = []
        for level in range(1, 7):
            for node in soup.find_all(f"h{level}"):
                text = node.get_text(" ", strip=True)
                if text:
                    items.append(HeadingRecord(level=level, text=text))
        return items

    def _extract_links(self, base_url: str, soup: BeautifulSoup) -> tuple[list[LinkRecord], list[LinkRecord]]:
        internal: list[LinkRecord] = []
        external: list[LinkRecord] = []
        seen: set[str] = set()
        for node in soup.find_all("a", href=True):
            href = absolutize(base_url, node["href"])
            if href in seen or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            seen.add(href)
            text = compact(node.get_text(" ", strip=True), 120)
            record = LinkRecord(url=href, text=text, internal=same_domain(base_url, href))
            if record.internal:
                internal.append(record)
            else:
                external.append(record)
        return internal, external

    def _extract_images(self, soup: BeautifulSoup) -> list[ImageRecord]:
        return [
            ImageRecord(
                src=node.get("src", ""),
                alt=node.get("alt", ""),
                width=str(node.get("width", "")),
                height=str(node.get("height", "")),
                loading=node.get("loading", ""),
            )
            for node in soup.find_all("img")
        ]

    def _extract_structured_data(self, soup: BeautifulSoup) -> list[StructuredDatum]:
        results: list[StructuredDatum] = []
        for node in soup.find_all("script", type="application/ld+json"):
            text = node.string or node.get_text()
            if not text.strip():
                continue
            try:
                payload = json.loads(text)
                results.append(StructuredDatum(syntax="json-ld", schema_type=self._schema_type(payload), valid=True, payload=payload))
            except json.JSONDecodeError as exc:
                results.append(StructuredDatum(syntax="json-ld", schema_type="unknown", valid=False, issues=[str(exc)], payload=text[:500]))
        if soup.find(attrs={"itemscope": True}):
            results.append(StructuredDatum(syntax="microdata", schema_type="detected", valid=True))
        if soup.find(attrs={"typeof": True}) or soup.find(attrs={"property": True, "vocab": True}):
            results.append(StructuredDatum(syntax="rdfa", schema_type="detected", valid=True))
        return results

    def _schema_type(self, payload: Any) -> str:
        if isinstance(payload, list) and payload:
            return self._schema_type(payload[0])
        if isinstance(payload, dict):
            schema_type = payload.get("@type", "")
            if isinstance(schema_type, list):
                return ", ".join(str(item) for item in schema_type)
            if isinstance(schema_type, str):
                return schema_type
        return "unknown"

    def _extract_paragraphs(self, soup: BeautifulSoup) -> list[str]:
        clone = BeautifulSoup(str(soup), "lxml")
        for node in clone.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            node.decompose()
        paragraphs: list[str] = []
        for node in clone.find_all(["p", "li", "blockquote", "td"]):
            text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
            if len(text_words(text)) >= 5:
                paragraphs.append(text)
        return paragraphs

    def _extract_social_links(self, external_links: list[LinkRecord]) -> dict[str, list[str]]:
        mapping = {
            "linkedin": [],
            "youtube": [],
            "wikipedia": [],
            "wikidata": [],
            "github": [],
            "reddit": [],
            "x": [],
            "facebook": [],
            "instagram": [],
            "crunchbase": [],
        }
        for link in external_links:
            url = link.url.lower()
            for key in mapping:
                if key == "x":
                    if "twitter.com" in url or "x.com" in url:
                        mapping[key].append(link.url)
                elif key in url:
                    mapping[key].append(link.url)
        return {key: value for key, value in mapping.items() if value}

    def _extract_signals(self, snapshot: PageSnapshot, soup: BeautifulSoup, headers: dict[str, str]) -> dict[str, Any]:
        body_text = " ".join(snapshot.paragraphs)
        return {
            "has_viewport": bool(soup.find("meta", attrs={"name": "viewport"})),
            "has_h1": any(item.level == 1 for item in snapshot.headings),
            "question_headings": sum(1 for item in snapshot.headings if item.text.endswith("?")),
            "heading_depth": max((item.level for item in snapshot.headings), default=0),
            "has_author": bool(snapshot.meta.author),
            "has_dates": bool(snapshot.meta.published or snapshot.meta.modified),
            "has_canonical": bool(snapshot.meta.canonical),
            "has_open_graph": bool(soup.find("meta", attrs={"property": re.compile(r"^og:", re.I)})),
            "has_twitter_cards": bool(soup.find("meta", attrs={"name": re.compile(r"^twitter:", re.I)})),
            "has_privacy_link": any("/privacy" in item.url for item in snapshot.internal_links),
            "has_terms_link": any("/terms" in item.url for item in snapshot.internal_links),
            "has_about_link": any("/about" in item.url for item in snapshot.internal_links),
            "has_contact_link": any("/contact" in item.url for item in snapshot.internal_links),
            "has_pricing_link": any("/pricing" in item.url for item in snapshot.internal_links),
            "has_product_terms": bool(re.search(r"\b(add to cart|sku|pricing|checkout|product)\b", body_text, re.I)),
            "has_service_terms": bool(re.search(r"\b(service|case study|consulting|strategy)\b", body_text, re.I)),
            "has_blog_terms": bool(re.search(r"\b(blog|article|guide|news|insights)\b", body_text, re.I)),
            "has_map_embed": bool(soup.find("iframe", src=re.compile("google.com/maps", re.I))),
            "has_feed_link": bool(soup.find("link", attrs={"type": re.compile(r"(rss|atom)\+xml", re.I)})),
            "has_math_runtime": bool(re.search(r"(katex|mathjax|tex-render)", str(soup), re.I)),
            "has_breadcrumbs": bool(re.search(r"breadcrumb", str(soup), re.I)),
            "has_references_section": bool(any(re.search(r"^(references|sources|further reading)$", item.text.strip(), re.I) for item in snapshot.headings)),
            "code_blocks": len(soup.find_all(["pre", "code"])),
            "article_like": self._article_like(snapshot, soup),
            "possible_csr": self._possible_csr(snapshot, soup),
            "security_headers": {key: headers.get(key, "") for key in (
                "Strict-Transport-Security",
                "Content-Security-Policy",
                "X-Frame-Options",
                "X-Content-Type-Options",
                "Referrer-Policy",
                "Permissions-Policy",
                "Cache-Control",
                "Content-Encoding",
            )},
        }

    def _possible_csr(self, snapshot: PageSnapshot, soup: BeautifulSoup) -> bool:
        roots = soup.find_all(id=re.compile(r"(root|app|__next|__nuxt)", re.I))
        if snapshot.word_count > 180:
            return False
        return bool(roots and snapshot.word_count < 80)

    def _article_like(self, snapshot: PageSnapshot, soup: BeautifulSoup) -> bool:
        body_text = " ".join(snapshot.paragraphs)
        article_markers = [
            bool(soup.find("article")),
            bool(re.search(r"\b(blog|article|guide|news|insights)\b", body_text, re.I)),
            "/articles/" in snapshot.url or "/blog/" in snapshot.url,
            bool(snapshot.meta.author),
        ]
        return sum(bool(item) for item in article_markers) >= 2
