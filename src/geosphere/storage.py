from __future__ import annotations

from pathlib import Path

from geosphere.helpers import ensure_dir


class RunWorkspace:
    def __init__(self, root: Path, run_id: str) -> None:
        self.root = ensure_dir(root / run_id)
        self.artifacts = ensure_dir(self.root / "artifacts")
        self.pages = ensure_dir(self.artifacts / "pages")
        self.meta = ensure_dir(self.artifacts / "meta")

    def page_html_path(self, slug: str) -> Path:
        return self.pages / f"{slug}.html"

    def data_path(self, name: str) -> Path:
        return self.root / name
