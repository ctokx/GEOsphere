from __future__ import annotations

import time
from urllib.parse import urlparse

import requests

from geosphere.contracts import RobotsSnapshot


class RobotsProbe:
    def __init__(self, timeout: int, user_agent: str, ai_agents: tuple[str, ...]) -> None:
        self.timeout = timeout
        self.user_agent = user_agent
        self.ai_agents = ai_agents

    def fetch(self, url: str) -> RobotsSnapshot:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        snapshot = RobotsSnapshot(url=robots_url, found=False, status_code=0)
        try:
            response = None
            last_error = ""
            for attempt in range(3):
                try:
                    response = requests.get(robots_url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
                    break
                except requests.RequestException as exc:
                    last_error = str(exc)
                    if attempt == 2:
                        raise
                    time.sleep(0.4 * (attempt + 1))
            snapshot.status_code = response.status_code
            if response.status_code != 200:
                snapshot.errors.append(f"status_{response.status_code}")
                for agent in self.ai_agents:
                    snapshot.ai_access[agent] = "unknown"
                return snapshot
            snapshot.found = True
            snapshot.content = response.text
            current_agents: list[str] = []
            for raw_line in response.text.splitlines():
                line = raw_line.split("#", 1)[0].strip()
                if not line or ":" not in line:
                    continue
                key, value = [part.strip() for part in line.split(":", 1)]
                lower_key = key.lower()
                if lower_key == "user-agent":
                    current_agents = [value]
                    snapshot.directives.setdefault(value, [])
                elif lower_key in {"allow", "disallow"} and current_agents:
                    for agent in current_agents:
                        snapshot.directives.setdefault(agent, []).append({"directive": key.title(), "path": value})
                elif lower_key == "sitemap":
                    snapshot.sitemaps.append(value)
            for agent in self.ai_agents:
                snapshot.ai_access[agent] = self._classify(agent, snapshot.directives)
            return snapshot
        except requests.RequestException as exc:
            snapshot.errors.append(str(exc))
            for agent in self.ai_agents:
                snapshot.ai_access[agent] = "unknown"
            return snapshot

    def _classify(self, agent: str, directives: dict[str, list[dict[str, str]]]) -> str:
        for candidate in (agent, agent.lower(), agent.upper()):
            if candidate in directives:
                return self._rules_status(directives[candidate])
        if "*" in directives:
            return f"wildcard_{self._rules_status(directives['*'])}"
        return "not_listed"

    def _rules_status(self, rules: list[dict[str, str]]) -> str:
        if any(item["directive"] == "Disallow" and item["path"] == "/" for item in rules):
            return "blocked"
        if any(item["directive"] == "Disallow" and item["path"] not in {"", "/"} for item in rules):
            return "partial"
        if any(item["directive"] == "Allow" for item in rules):
            return "allowed"
        return "neutral"
