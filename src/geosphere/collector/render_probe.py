from __future__ import annotations

from typing import Any


class RenderProbe:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def inspect(self, url: str) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "available": False}
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            return {"enabled": True, "available": False}
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                content = page.content()
                title = page.title()
                browser.close()
            return {
                "enabled": True,
                "available": True,
                "rendered_title": title,
                "rendered_length": len(content),
            }
        except Exception as exc:
            return {"enabled": True, "available": True, "error": str(exc)}
