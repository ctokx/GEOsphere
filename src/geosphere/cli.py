from __future__ import annotations

import argparse
import json
from pathlib import Path

from geosphere.benchmark import build_benchmark_payload, write_benchmark_artifacts
from geosphere.compare import compare_audits, load_audit_payload, render_compare_markdown
from geosphere.engine import AuditEngine
from geosphere.installer import install_skill
from geosphere.pdf_report import build_pdf_report, load_report_payload
from geosphere.settings import RuntimeOptions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geosphere", description="Independent GEO audit engine")
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="Collect evidence for a Claude-first GEOsphere audit")
    collect.add_argument("url")
    collect.add_argument("--max-pages", type=int, default=50)
    collect.add_argument("--output", default="runs")
    collect.add_argument("--render", action="store_true")

    audit = sub.add_parser("audit", help="Run a full GEOsphere audit")
    audit.add_argument("url")
    audit.add_argument("--max-pages", type=int, default=12)
    audit.add_argument("--output", default="runs")
    audit.add_argument("--render", action="store_true")

    quick = sub.add_parser("quick", help="Run audit and print compact summary")
    quick.add_argument("url")
    quick.add_argument("--max-pages", type=int, default=8)
    quick.add_argument("--output", default="runs")
    quick.add_argument("--render", action="store_true")

    inspect = sub.add_parser("inspect", help="Run audit and print raw JSON")
    inspect.add_argument("url")
    inspect.add_argument("--max-pages", type=int, default=6)
    inspect.add_argument("--output", default="runs")
    inspect.add_argument("--render", action="store_true")

    llms = sub.add_parser("llms", help="Run audit and emit llms.txt outputs")
    llms.add_argument("url")
    llms.add_argument("--max-pages", type=int, default=10)
    llms.add_argument("--output", default="runs")
    llms.add_argument("--render", action="store_true")

    report_pdf = sub.add_parser("report-pdf", help="Generate a PDF executive brief from a run directory or report JSON")
    report_pdf.add_argument("source")
    report_pdf.add_argument("--output", default="")

    compare = sub.add_parser("compare", help="Compare two GEOsphere runs or audit.json files")
    compare.add_argument("left")
    compare.add_argument("right")
    compare.add_argument("--markdown-out", default="")

    install = sub.add_parser("install-skill", help="Install a Claude skill file pointing to this GEOsphere project")
    install.add_argument("--target", default="")

    benchmark = sub.add_parser("benchmark", help="Audit a primary site against one or more competitors")
    benchmark.add_argument("primary")
    benchmark.add_argument("competitors", nargs="+")
    benchmark.add_argument("--max-pages", type=int, default=8)
    benchmark.add_argument("--output", default="runs")
    benchmark.add_argument("--render", action="store_true")
    return parser


def run_with_options(url: str, max_pages: int, output: str, render: bool = False) -> AuditEngine:
    options = RuntimeOptions(max_pages=max_pages, output_root=Path(output), render_probe=render)
    return AuditEngine(options)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "compare":
        payload = compare_audits(load_audit_payload(args.left), load_audit_payload(args.right))
        markdown = render_compare_markdown(payload)
        if args.markdown_out:
            Path(args.markdown_out).write_text(markdown, encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if args.command == "install-skill":
        target = Path(args.target) if args.target else Path.home() / ".claude" / "skills" / "geosphere"
        installed = install_skill(Path.cwd(), target)
        print(f"Installed: {installed}")
        return 0
    if args.command == "report-pdf":
        payload = load_report_payload(args.source)
        source_path = Path(args.source)
        default_output = source_path / "GEOsphere-Executive-Brief.pdf" if source_path.is_dir() else source_path.with_suffix(".pdf")
        output = Path(args.output) if args.output else default_output
        built = build_pdf_report(payload, str(output))
        print(f"PDF: {built}")
        return 0
    if args.command == "benchmark":
        engine = run_with_options(args.primary, args.max_pages, args.output, args.render)
        primary_outcome = engine.audit(args.primary)
        competitor_outcomes = [engine.audit(url) for url in args.competitors]
        payload = build_benchmark_payload(primary_outcome, competitor_outcomes)
        json_path, md_path = write_benchmark_artifacts(Path(primary_outcome.evidence_root), payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"Benchmark JSON: {json_path}")
        print(f"Benchmark Markdown: {md_path}")
        return 0
    engine = run_with_options(args.url, args.max_pages, args.output, args.render)
    if args.command == "collect":
        outcome = engine.collect(args.url)
        print(f"Run: {outcome.run_id}")
        print(f"Pages: {outcome.pages_analyzed}")
        print(f"Artifacts: {outcome.evidence_root}")
        return 0
    outcome = engine.audit(args.url)
    if args.command == "inspect":
        print(json.dumps(outcome.to_dict(), indent=2, ensure_ascii=False))
    elif args.command == "llms":
        print(f"Run: {outcome.run_id}")
        print(f"llms.txt: {Path(outcome.evidence_root) / 'llms.txt'}")
        print(f"llms-full.txt: {Path(outcome.evidence_root) / 'llms-full.txt'}")
    elif args.command == "quick":
        lines = [
            f"{outcome.brand_name} [{outcome.business_model}]",
            f"Score: {outcome.total_score}/100",
            f"Pages: {outcome.pages_analyzed}",
        ]
        for module in outcome.modules:
            lines.append(f"{module.name}: {module.score}/100")
        print("\n".join(lines))
    else:
        print(f"Run: {outcome.run_id}")
        print(f"Score: {outcome.total_score}/100")
        print(f"Artifacts: {outcome.evidence_root}")
    return 0
