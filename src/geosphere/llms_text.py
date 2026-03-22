from __future__ import annotations

from urllib.parse import urlparse

import requests

from geosphere.contracts import SiteProfile


def inspect_remote_llms(base_url: str, timeout: int, user_agent: str) -> dict:
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    results = {
        "llms_txt": {"url": f"{root}/llms.txt", "exists": False, "status_code": 0, "content": "", "issues": []},
        "llms_full_txt": {"url": f"{root}/llms-full.txt", "exists": False, "status_code": 0, "content": "", "issues": []},
    }
    for key, payload in results.items():
        try:
            response = requests.get(payload["url"], timeout=timeout, headers={"User-Agent": user_agent})
            payload["status_code"] = response.status_code
            if response.status_code == 200:
                payload["exists"] = True
                payload["content"] = response.text
                lines = [line.strip() for line in response.text.splitlines() if line.strip()]
                if not lines or not lines[0].startswith("# "):
                    payload["issues"].append("missing_title")
                if not any(line.startswith("## ") for line in lines):
                    payload["issues"].append("missing_sections")
            else:
                payload["issues"].append(f"status_{response.status_code}")
        except requests.RequestException as exc:
            payload["issues"].append(str(exc))
    return results


def generate_llms(profile: SiteProfile, detailed: bool = False) -> str:
    lines = [
        f"# {profile.brand_name}",
        f"> {profile.brand_name} official web presence for {profile.business_model.replace('_', ' ')} topics and supporting resources.",
        "",
    ]
    groups: dict[str, list[tuple[str, str]]] = {
        "Main": [],
        "Commercial": [],
        "Knowledge": [],
        "Trust": [],
    }
    seen: set[str] = set()
    for page in profile.pages:
        if page.url in seen or page.status_code != 200:
            continue
        seen.add(page.url)
        label = page.meta.title or page.url
        if "/pricing" in page.url or "/product" in page.url or "/services" in page.url:
            bucket = "Commercial"
        elif "/blog" in page.url or "/docs" in page.url or "/resources" in page.url or "/faq" in page.url:
            bucket = "Knowledge"
        elif "/about" in page.url or "/contact" in page.url or "/privacy" in page.url or "/terms" in page.url:
            bucket = "Trust"
        else:
            bucket = "Main"
        if detailed and page.meta.description:
            groups[bucket].append((label, f"{page.url} - {page.meta.description.strip()}"))
        else:
            groups[bucket].append((label, page.url))
    for section, entries in groups.items():
        if not entries:
            continue
        lines.append(f"## {section}")
        for label, target in entries[:12]:
            if detailed and " - " in target:
                url, description = target.split(" - ", 1)
                lines.append(f"- [{label}]({url}): {description}")
            else:
                lines.append(f"- [{label}]({target})")
        lines.append("")
    lines.append("## Contact")
    lines.append(f"- Website: {profile.url}")
    email = ""
    phone = ""
    for page in profile.pages:
        if page.emails and not email:
            email = page.emails[0]
        if page.phones and not phone:
            phone = page.phones[0]
    if email:
        lines.append(f"- Email: {email}")
    if phone:
        lines.append(f"- Phone: {phone}")
    lines.append("")
    return "\n".join(lines)
