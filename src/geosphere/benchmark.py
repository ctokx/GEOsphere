from __future__ import annotations

from pathlib import Path

from geosphere.contracts import AuditOutcome
from geosphere.helpers import write_json, write_text


def build_benchmark_payload(primary: AuditOutcome, competitors: list[AuditOutcome]) -> dict:
    primary_modules = {module.name: module.score for module in primary.modules}
    rows = []
    for outcome in [primary, *competitors]:
        rows.append(
            {
                "brand_name": outcome.brand_name,
                "domain": outcome.domain,
                "total_score": outcome.total_score,
                "modules": {module.name: module.score for module in outcome.modules},
            }
        )
    return {
        "primary": primary.brand_name,
        "rows": rows,
        "leaders": {
            "overall": max(rows, key=lambda item: item["total_score"])["brand_name"],
            "modules": {
                module: max(rows, key=lambda item: item["modules"].get(module, 0))["brand_name"]
                for module in primary_modules
            },
        },
    }


def render_benchmark_markdown(payload: dict) -> str:
    lines = []
    lines.append(f"# GEOsphere Benchmark: {payload['primary']}")
    lines.append("")
    module_names = list(payload["rows"][0]["modules"].keys()) if payload["rows"] else []
    header = "| Brand | Overall | " + " | ".join(name.title() for name in module_names) + " |"
    sep = "|---" + "|---:" * (2 + len(module_names))
    lines.append(header)
    lines.append(sep)
    for row in payload["rows"]:
        values = " | ".join(str(row["modules"].get(name, 0)) for name in module_names)
        lines.append(f"| {row['brand_name']} | {row['total_score']} | {values} |")
    lines.append("")
    return "\n".join(lines)


def write_benchmark_artifacts(output_dir: Path, payload: dict) -> tuple[Path, Path]:
    json_path = output_dir / "benchmark.json"
    md_path = output_dir / "benchmark.md"
    write_json(json_path, payload)
    write_text(md_path, render_benchmark_markdown(payload))
    return json_path, md_path
