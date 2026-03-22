from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse


def now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "site"


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or parsed.path
    path = parsed.path if parsed.netloc else ""
    path = path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urlunparse((scheme, netloc.lower(), path, "", parsed.query, ""))


def same_domain(base_url: str, candidate: str) -> bool:
    return urlparse(base_url).netloc.lower() == urlparse(candidate).netloc.lower()


def absolutize(base_url: str, href: str) -> str:
    return normalize_url(urljoin(base_url, href))


def text_words(value: str) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", value)


def detect_business_model(paths: list[str], text: str) -> str:
    joined = " ".join(paths).lower() + " " + text.lower()
    checks = [
        ("ecommerce", ["/cart", "/shop", "/product", "add to cart", "checkout"]),
        ("saas", ["/pricing", "free trial", "book a demo", "api", "dashboard"]),
        ("publisher", ["/blog", "/news", "author", "published", "newsletter"]),
        ("agency", ["/services", "/case-study", "our work", "portfolio"]),
        ("local_business", ["google maps", "opening hours", "visit us", "call now"]),
    ]
    for label, terms in checks:
        if any(term in joined for term in terms):
            return label
    return "general"


def infer_brand_name(title: str, domain: str) -> str:
    if title:
        parts = re.split(r"[|\-–—:]", title)
        if parts and parts[0].strip():
            return parts[0].strip()
    core = domain.split(".")[0].replace("-", " ").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in core.split())


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.write_text(payload, encoding="utf-8")


def compact(value: str, limit: int = 240) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value[: limit - 3] + "..." if len(value) > limit else value
