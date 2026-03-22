from __future__ import annotations

import json
from pathlib import Path


def load_audit_payload(path: str) -> dict:
    candidate = Path(path)
    if candidate.is_dir():
        candidate = candidate / "audit.json"
    return json.loads(candidate.read_text(encoding="utf-8"))


def compare_audits(left: dict, right: dict) -> dict:
    left_modules = {item["name"]: item for item in left.get("modules", [])}
    right_modules = {item["name"]: item for item in right.get("modules", [])}
    module_deltas = {}
    for key in sorted(set(left_modules) | set(right_modules)):
        left_score = left_modules.get(key, {}).get("score", 0)
        right_score = right_modules.get(key, {}).get("score", 0)
        module_deltas[key] = {
            "left": left_score,
            "right": right_score,
            "delta": right_score - left_score,
        }
    return {
        "left": {"brand": left.get("brand_name"), "score": left.get("total_score"), "run_id": left.get("run_id")},
        "right": {"brand": right.get("brand_name"), "score": right.get("total_score"), "run_id": right.get("run_id")},
        "overall_delta": right.get("total_score", 0) - left.get("total_score", 0),
        "module_deltas": module_deltas,
    }


def render_compare_markdown(payload: dict) -> str:
    lines = []
    lines.append(f"# GEOsphere Comparison: {payload['left']['brand']} -> {payload['right']['brand']}")
    lines.append("")
    lines.append(f"- Left run: {payload['left']['run_id']} ({payload['left']['score']}/100)")
    lines.append(f"- Right run: {payload['right']['run_id']} ({payload['right']['score']}/100)")
    lines.append(f"- Overall delta: {payload['overall_delta']:+d}")
    lines.append("")
    lines.append("| Module | Left | Right | Delta |")
    lines.append("|---|---:|---:|---:|")
    for name, delta in payload["module_deltas"].items():
        lines.append(f"| {name} | {delta['left']} | {delta['right']} | {delta['delta']:+d} |")
    lines.append("")
    return "\n".join(lines)
