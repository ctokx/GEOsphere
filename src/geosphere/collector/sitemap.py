from __future__ import annotations

from collections import deque
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from geosphere.contracts import SitemapSnapshot
from geosphere.helpers import normalize_url


class SitemapProbe:
    def __init__(self, timeout: int, user_agent: str) -> None:
        self.timeout = timeout
        self.user_agent = user_agent

    def fetch(self, base_url: str, hints: list[str] | None = None, cap: int = 100) -> SitemapSnapshot:
        parsed = urlparse(base_url)
        default_sources = [
            f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
            f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
        ]
        queue = deque(hints or [])
        for item in default_sources:
            if item not in queue:
                queue.append(item)
        discovered: list[str] = []
        sources: list[str] = []
        errors: list[str] = []
        seen_sources: set[str] = set()
        seen_pages: set[str] = set()
        while queue and len(discovered) < cap:
            source = queue.popleft()
            if source in seen_sources:
                continue
            seen_sources.add(source)
            sources.append(source)
            try:
                response = None
                for attempt in range(3):
                    try:
                        response = requests.get(source, timeout=self.timeout, headers={"User-Agent": self.user_agent})
                        break
                    except requests.RequestException:
                        if attempt == 2:
                            raise
                        time.sleep(0.4 * (attempt + 1))
                if response.status_code != 200:
                    errors.append(f"{source}:status_{response.status_code}")
                    continue
                soup = BeautifulSoup(response.text, "xml")
                for sitemap in soup.find_all("sitemap"):
                    loc = sitemap.find("loc")
                    if loc and loc.text.strip() not in seen_sources:
                        queue.append(loc.text.strip())
                for node in soup.find_all("url"):
                    loc = node.find("loc")
                    if not loc:
                        continue
                    url = normalize_url(loc.text.strip())
                    if url not in seen_pages:
                        seen_pages.add(url)
                        discovered.append(url)
                        if len(discovered) >= cap:
                            break
            except requests.RequestException as exc:
                errors.append(f"{source}:{exc}")
        return SitemapSnapshot(
            discovered_urls=discovered,
            source_urls=sources,
            sampled_urls=discovered[: min(len(discovered), 20)],
            errors=errors,
        )
