from __future__ import annotations

from collections import OrderedDict

from geosphere.contracts import PageSnapshot, RobotsSnapshot, SitemapSnapshot


class DiscoveryPlanner:
    def __init__(self, important_hints: tuple[str, ...], max_pages: int) -> None:
        self.important_hints = important_hints
        self.max_pages = max_pages

    def build(self, homepage: PageSnapshot, robots: RobotsSnapshot, sitemap: SitemapSnapshot) -> list[str]:
        ordered: OrderedDict[str, None] = OrderedDict()
        ordered[homepage.url] = None
        important_from_sitemap = []
        for url in sitemap.discovered_urls:
            if any(hint in url.lower() for hint in self.important_hints):
                important_from_sitemap.append(url)
        for url in important_from_sitemap[: self.max_pages]:
            ordered[url] = None
        for link in homepage.internal_links:
            if self._skip(link.url):
                continue
            if any(hint in link.url.lower() for hint in self.important_hints):
                ordered[link.url] = None
        for link in homepage.internal_links:
            if self._skip(link.url):
                continue
            ordered[link.url] = None
            if len(ordered) >= self.max_pages:
                break
        for url in sitemap.discovered_urls:
            if self._skip(url):
                continue
            ordered[url] = None
            if len(ordered) >= self.max_pages:
                break
        return list(ordered.keys())[: self.max_pages]

    def _skip(self, url: str) -> bool:
        lowered = url.lower()
        blocked = (".xml", ".json", "/feed", "/rss", ".jpg", ".jpeg", ".png", ".gif", ".pdf", ".webp", ".svg")
        return any(token in lowered for token in blocked)
