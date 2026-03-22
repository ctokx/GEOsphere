from __future__ import annotations

import shutil
from pathlib import Path


def install_skill(project_root: Path, target_dir: Path) -> Path:
    source_dir = project_root / "geosphere"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    return target_dir / "SKILL.md"
