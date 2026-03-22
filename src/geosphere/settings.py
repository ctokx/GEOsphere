from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class RuntimeOptions:
    max_pages: int = 12
    request_timeout: int = 20
    external_lookup_timeout: int = 8
    output_root: Path = Path("runs")
    user_agent: str = "GEOsphereBot/0.1 (+https://local.audit/geosphere)"
    render_probe: bool = False
    ai_agents: tuple[str, ...] = (
        "GPTBot",
        "ClaudeBot",
        "PerplexityBot",
        "Googlebot",
        "Google-Extended",
        "bingbot",
        "CCBot",
        "Applebot-Extended",
        "OAI-SearchBot",
        "ChatGPT-User",
        "Amazonbot",
        "Bytespider",
        "FacebookBot",
    )
    important_path_hints: tuple[str, ...] = (
        "/about",
        "/contact",
        "/pricing",
        "/features",
        "/product",
        "/products",
        "/services",
        "/blog",
        "/resources",
        "/docs",
        "/faq",
        "/team",
        "/privacy",
        "/terms",
    )
    platform_weights: dict[str, float] = field(
        default_factory=lambda: {
            "technical": 0.22,
            "content": 0.24,
            "schema": 0.16,
            "entity": 0.16,
            "platforms": 0.22,
        }
    )
