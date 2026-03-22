from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


NAVY = colors.HexColor("#0f172a")
SLATE = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#d7dee8")
PANEL = colors.HexColor("#f8fafc")
PANEL_ALT = colors.HexColor("#eef2f7")
WHITE = colors.white
RED = colors.HexColor("#dc2626")
AMBER = colors.HexColor("#d97706")
GREEN = colors.HexColor("#15803d")
BLUE = colors.HexColor("#1d4ed8")
TEAL = colors.HexColor("#0f766e")


def load_report_payload(source: str) -> dict:
    path = Path(source)
    if path.is_dir():
        for name in ("manager-brief.json", "executive-report.json", "audit-brief.json", "audit.json", "collection.json"):
            candidate = path / name
            if candidate.exists():
                return load_report_payload(str(candidate))
        raise FileNotFoundError(f"No supported report source found in {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "overall_score" in payload and "module_scores" in payload:
        return payload
    if "total_score" in payload and "modules" in payload:
        return _from_audit_payload(payload, path)
    if "pages_analyzed" in payload and "summary" in payload:
        return _from_collection_payload(payload, path)
    raise ValueError(f"Unsupported report payload: {path}")


def build_pdf_report(payload: dict, output_path: str) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    story = []
    story.extend(_cover_section(payload, styles))
    if payload.get("executive_summary"):
        story.extend(_text_panel("Executive Summary", payload["executive_summary"], styles))
    if payload.get("root_causes"):
        story.extend(_root_cause_panel(payload["root_causes"], styles))
    if payload.get("opportunity_snapshot"):
        story.extend(_opportunity_section(payload.get("opportunity_snapshot", {}), styles))
    if payload.get("module_scores"):
        story.extend(_module_section(payload.get("module_scores", []), styles))
    if payload.get("platform_readiness"):
        story.extend(_platform_section(payload.get("platform_readiness", []), styles))
    if payload.get("critical_issues"):
        story.extend(_issues_section(payload.get("critical_issues", []), styles))
    if payload.get("template_defects"):
        story.extend(_template_defects_section(payload.get("template_defects", []), styles))
    if payload.get("page_weaknesses"):
        story.extend(_page_weaknesses_section(payload.get("page_weaknesses", []), styles))
    if payload.get("quick_wins"):
        story.extend(_quick_wins_section(payload.get("quick_wins", []), styles))
    if payload.get("plan_30_day"):
        story.extend(_plan_section(payload.get("plan_30_day", []), styles))
    if payload.get("implementation_appendix"):
        story.append(PageBreak())
        story.extend(_implementation_appendix_section(payload.get("implementation_appendix", []), styles))
    if payload.get("implementation_checklist"):
        story.extend(_checklist_section(payload.get("implementation_checklist", []), styles))
    if payload.get("progress_delta"):
        story.extend(_progress_delta_section(payload.get("progress_delta", {}), styles))
    if payload.get("benchmark"):
        story.extend(_benchmark_section(payload.get("benchmark", []), styles))
    if payload.get("verification_notes"):
        if not payload.get("implementation_appendix"):
            story.append(PageBreak())
        story.extend(_verification_section(payload.get("verification_notes", []), styles))
    story.extend(_final_remarks_section(payload, styles))
    doc.build(story, onFirstPage=_draw_page_chrome(payload), onLaterPages=_draw_page_chrome(payload))
    return output


def _cover_section(payload: dict, styles: dict) -> list:
    title = payload.get("title", "GEOsphere Executive Brief")
    site = payload.get("brand_name", "")
    site_url = payload.get("site_url", "")
    run_id = payload.get("run_id", "")
    audited_at = payload.get("audited_at", "")
    overall = payload.get("overall_score", "N/A")
    confidence = payload.get("confidence", "N/A")
    summary_left = [
        Paragraph(title, styles["HeroTitle"]),
        Spacer(1, 2.5 * mm),
        Paragraph(site, styles["HeroSubtitle"]),
        Spacer(1, 4 * mm),
        Paragraph(site_url, styles["MetaLine"]),
        Paragraph(f"Run {run_id}", styles["MetaLine"]),
        Paragraph(f"Audited {audited_at}", styles["MetaLine"]),
    ]
    summary_right = Table(
        [
            [Paragraph("Overall Score", styles["ScoreLabel"])],
            [Paragraph(str(overall), styles["ScoreValue"])],
            [Paragraph(f"{confidence} confidence", styles["ConfidencePill"])],
        ],
        colWidths=[48 * mm],
    )
    summary_right.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _score_fill(overall)),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LINEABOVE", (0, 0), (-1, 0), 3.5, colors.HexColor(_score_hex(overall))),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    hero = Table([[summary_left, summary_right]], colWidths=[122 * mm, 48 * mm])
    hero.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.8, LINE),
                ("LINEABOVE", (0, 0), (-1, 0), 3.5, TEAL),
                ("LINEBELOW", (0, -1), (-1, -1), 0.7, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return [KeepTogether(hero), Spacer(1, 6 * mm)]


def _text_panel(title: str, body: str, styles: dict) -> list:
    panel = Table(
        [[Paragraph(title, styles["SectionTitle"])], [Paragraph(body, styles["BodyText"])]],
        colWidths=[170 * mm],
    )
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, -1), PANEL),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return [panel, Spacer(1, 5 * mm)]


def _root_cause_panel(root_causes: list[str], styles: dict) -> list:
    rows = [[Paragraph("Core Issue Tree", styles["SectionTitle"])]]
    for index, item in enumerate(root_causes[:6], start=1):
        rows.append([Paragraph(f"{index}. {item}", styles["BodyText"])])
    panel = Table(rows, colWidths=[170 * mm])
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), SLATE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [panel, Spacer(1, 5 * mm)]


def _coerce_opportunity(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    return {"current_score": "", "target_score_30d": "", "ceiling_score": "", "primary_win": text}


def _opportunity_section(opportunity_snapshot: dict, styles: dict) -> list:
    opportunity_snapshot = _coerce_opportunity(opportunity_snapshot)
    cards = []
    items = [
        ("Current", str(opportunity_snapshot.get("current_score", "N/A"))),
        ("Next 30 Days", str(opportunity_snapshot.get("target_score_30d", "N/A"))),
        ("Ceiling", str(opportunity_snapshot.get("ceiling_score", "N/A"))),
        ("Primary Win", str(opportunity_snapshot.get("primary_win", "N/A"))),
    ]
    for label, value in items:
        card = Table(
            [[Paragraph(label, styles["MiniLabel"])], [Paragraph(value, styles["MiniValue"])]],
            colWidths=[40 * mm],
        )
        card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                    ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        cards.append(card)
    header = [Paragraph("Opportunity Snapshot", styles["SectionHeader"])]
    row = Table([cards], colWidths=[42.5 * mm, 42.5 * mm, 42.5 * mm, 42.5 * mm])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return header + [row, Spacer(1, 5 * mm)]


def _module_section(module_scores: list[dict], styles: dict) -> list:
    elements = [Paragraph("Module Scorecard", styles["SectionHeader"])]
    chart = _build_module_chart(module_scores)
    if chart:
        elements.append(Image(chart, width=170 * mm, height=78 * mm))
        elements.append(Spacer(1, 4 * mm))
    rows = [["Module", "Score", "Confidence", "Primary Driver"]]
    for item in module_scores:
        rows.append(
            [
                Paragraph(str(item.get("name", "")), styles["TableText"]),
                Paragraph(str(item.get("score", "")), styles["TableTextCenter"]),
                Paragraph(str(item.get("confidence", "")), styles["TableTextCenter"]),
                Paragraph(str(item.get("driver") or item.get("primary_driver", "")), styles["TableText"]),
            ]
        )
    table = Table(rows, colWidths=[34 * mm, 18 * mm, 28 * mm, 90 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.6),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for row_index, item in enumerate(module_scores, start=1):
        style.append(("BACKGROUND", (1, row_index), (1, row_index), _score_fill(item.get("score", 0))))
    table.setStyle(TableStyle(style))
    elements.append(table)
    elements.append(Spacer(1, 5 * mm))
    return elements


def _platform_section(platform_readiness: list[dict], styles: dict) -> list:
    elements = [Paragraph("Platform Readiness", styles["SectionHeader"])]
    chart = _build_platform_chart(platform_readiness)
    if chart:
        elements.append(Image(chart, width=170 * mm, height=78 * mm))
        elements.append(Spacer(1, 4 * mm))
    rows = [["Platform", "Readiness", "Primary Constraint"]]
    for item in platform_readiness[:8]:
        score_text = item.get("score", item.get("readiness", ""))
        rows.append(
            [
                Paragraph(str(item.get("platform", "")), styles["TableText"]),
                Paragraph(str(score_text), styles["TableTextCenter"]),
                Paragraph(str(item.get("blocker", "")), styles["TableText"]),
            ]
        )
    table = Table(rows, colWidths=[44 * mm, 24 * mm, 102 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.6),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 5 * mm))
    return elements


def _issues_section(issues: list[dict], styles: dict) -> list:
    elements = [Paragraph("Critical And High-Priority Issues", styles["SectionHeader"])]
    for issue in issues[:8]:
        elements.append(_issue_card(issue, styles))
        elements.append(Spacer(1, 3.5 * mm))
    return elements


def _template_defects_section(defects: list[dict], styles: dict) -> list:
    elements = [Paragraph("Template-Level Defects", styles["SectionHeader"])]
    rows = [["Defect", "Scope", "Fix", "Impact"]]
    for item in defects[:12]:
        rows.append(
            [
                Paragraph(str(item.get("defect", item.get("title", ""))), styles["TableText"]),
                Paragraph(str(item.get("scope", "")), styles["TableTextCenter"]),
                Paragraph(str(item.get("fix", item.get("fix_location", ""))), styles["TableText"]),
                Paragraph(str(item.get("impact", item.get("expected_impact", ""))), styles["TableText"]),
            ]
        )
    table = Table(rows, colWidths=[48 * mm, 26 * mm, 48 * mm, 48 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.4),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 5 * mm))
    return elements


def _page_weaknesses_section(weaknesses: list[dict], styles: dict) -> list:
    elements = [Paragraph("Page-Level Weaknesses", styles["SectionHeader"])]
    rows = [["Page", "Issue", "Priority", "Action"]]
    for item in weaknesses[:12]:
        rows.append(
            [
                Paragraph(str(item.get("page", item.get("title", ""))), styles["TableText"]),
                Paragraph(str(item.get("issue", item.get("detail", ""))), styles["TableText"]),
                Paragraph(str(item.get("priority", "")), styles["TableTextCenter"]),
                Paragraph(str(item.get("action", item.get("fix", ""))), styles["TableText"]),
            ]
        )
    table = Table(rows, colWidths=[35 * mm, 74 * mm, 20 * mm, 41 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.4),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 5 * mm))
    return elements


def _issue_card(issue: dict, styles: dict):
    title = issue.get("title", "")
    verification = issue.get("verification_status", "N/A")
    scope = issue.get("scope", "N/A")
    fix_location = issue.get("fix_location", "N/A")
    effort = issue.get("effort", "N/A")
    expected = issue.get("expected_impact", "N/A")
    detail = issue.get("detail", "")
    meta_lines = []
    if scope and scope != "N/A":
        meta_lines.append(f"<b>Scope:</b> {scope}")
    if verification and verification != "N/A":
        meta_lines.append(f"<b>Verification:</b> {verification}")
    if fix_location and fix_location != "N/A":
        meta_lines.append(f"<b>Fix location:</b> {fix_location}")
    if effort and effort != "N/A":
        meta_lines.append(f"<b>Effort:</b> {effort}")
    if expected and expected != "N/A":
        meta_lines.append(f"<b>Expected impact:</b> {expected}")
    rows = [
        [Paragraph(title, styles["CardTitle"])],
        [Paragraph(detail, styles["BodyText"])],
    ]
    if meta_lines:
        rows.append([Paragraph("<br/>".join(meta_lines), styles["MetaBody"])])
    body = Table(rows, colWidths=[162 * mm])
    body.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.45, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    accent = Table([[""], [""], [""]], colWidths=[8 * mm], rowHeights=[10 * mm, 17 * mm, 16 * mm])
    accent.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RED if "CRITICAL" in title.upper() else AMBER),
                ("BOX", (0, 0), (-1, -1), 0.45, LINE),
            ]
        )
    )
    wrapper = Table([[accent, body]], colWidths=[8 * mm, 162 * mm])
    wrapper.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "STRETCH")]))
    return KeepTogether(wrapper)


def _quick_wins_section(quick_wins: list[dict], styles: dict) -> list:
    elements = [Paragraph("Quick Wins", styles["SectionHeader"])]
    rows = [["Action", "Owner", "Effort", "Why it matters", "Expected upside"]]
    for item in quick_wins[:10]:
        rows.append(
            [
                Paragraph(str(item.get("action", "")), styles["TableText"]),
                Paragraph(str(item.get("owner", "")), styles["TableTextCenter"]),
                Paragraph(str(item.get("effort", "")), styles["TableTextCenter"]),
                Paragraph(str(item.get("why", "")), styles["TableText"]),
                Paragraph(str(item.get("upside", item.get("expected_impact", ""))), styles["TableText"]),
            ]
        )
    table = Table(rows, colWidths=[43 * mm, 16 * mm, 18 * mm, 52 * mm, 41 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.6),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 5 * mm))
    return elements


def _plan_section(plan_30_day: list[dict], styles: dict) -> list:
    elements = [Paragraph("30-Day Plan", styles["SectionHeader"])]
    for phase in plan_30_day[:5]:
        rows = [[Paragraph(str(phase.get("phase", "")), styles["PhaseTitle"])]]
        for item in phase.get("items", [])[:8]:
            rows.append([Paragraph(f"- {item}", styles["BodyText"])])
        panel = Table(rows, colWidths=[170 * mm])
        panel.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PANEL_ALT),
                    ("BOX", (0, 0), (-1, -1), 0.55, LINE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        elements.append(panel)
        elements.append(Spacer(1, 3.5 * mm))
    return elements


def _verification_section(notes: list[dict], styles: dict) -> list:
    elements = [Paragraph("Verification Notes", styles["SectionHeader"])]
    rows = [["Claim", "Status", "Basis"]]
    for item in notes[:14]:
        rows.append(
            [
                Paragraph(str(item.get("claim", "")), styles["TableText"]),
                Paragraph(str(item.get("status", "")), styles["TableTextCenter"]),
                Paragraph(str(item.get("basis", "")), styles["TableText"]),
            ]
        )
    table = Table(rows, colWidths=[57 * mm, 24 * mm, 89 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.3),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for row_index, item in enumerate(notes[:14], start=1):
        status = str(item.get("status", "")).lower()
        fill = GREEN if "verified" in status else AMBER if "inference" in status else PANEL
        style.append(("BACKGROUND", (1, row_index), (1, row_index), fill))
    table.setStyle(TableStyle(style))
    elements.append(table)
    return elements


def _implementation_appendix_section(entries: list[dict], styles: dict) -> list:
    elements = [Paragraph("Implementation Appendix", styles["SectionHeader"])]
    for item in entries[:12]:
        title = item.get("title", "")
        body = item.get("body", "")
        appendix = Table(
            [
                [Paragraph(title, styles["CardTitle"])],
                [Paragraph(_codeish(body), styles["AppendixBody"])],
            ],
            colWidths=[170 * mm],
        )
        appendix.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PANEL_ALT),
                    ("BACKGROUND", (0, 1), (-1, -1), WHITE),
                    ("BOX", (0, 0), (-1, -1), 0.55, LINE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(appendix)
        elements.append(Spacer(1, 3.5 * mm))
    return elements


def _checklist_section(items: list[dict], styles: dict) -> list:
    elements = [Paragraph("Implementation Checklist", styles["SectionHeader"])]
    rows = [["", "Action", "Owner", "Effort", "Status"]]
    for item in items[:20]:
        rows.append(
            [
                Paragraph("\u2610", styles["TableTextCenter"]),
                Paragraph(str(item.get("action", "")), styles["TableText"]),
                Paragraph(str(item.get("owner", "")), styles["TableTextCenter"]),
                Paragraph(str(item.get("effort", "")), styles["TableTextCenter"]),
                Paragraph(str(item.get("status", "")), styles["TableTextCenter"]),
            ]
        )
    table = Table(rows, colWidths=[8 * mm, 72 * mm, 28 * mm, 24 * mm, 38 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.4),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 5 * mm))
    return elements


def _progress_delta_section(delta: dict, styles: dict) -> list:
    elements = [Paragraph("Progress Since Last Audit", styles["SectionHeader"])]
    prev = delta.get("previous_score", "N/A")
    curr = delta.get("current_score", "N/A")
    improvement = delta.get("improvement", "N/A")
    score_row = Table(
        [
            [
                Table([[Paragraph("Previous", styles["MiniLabel"])], [Paragraph(str(prev), styles["MiniValue"])]], colWidths=[42 * mm]),
                Table([[Paragraph("Current", styles["MiniLabel"])], [Paragraph(str(curr), styles["MiniValue"])]], colWidths=[42 * mm]),
                Table([[Paragraph("Change", styles["MiniLabel"])], [Paragraph(f"+{improvement}" if str(improvement).lstrip("-").isdigit() and int(str(improvement)) >= 0 else str(improvement), styles["MiniValue"])]], colWidths=[42 * mm]),
            ]
        ],
        colWidths=[56 * mm, 56 * mm, 56 * mm],
    )
    score_row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(score_row)
    elements.append(Spacer(1, 4 * mm))
    completed = delta.get("completed_items", [])
    remaining = delta.get("remaining_items", [])
    left_rows = [[Paragraph("Completed", styles["SectionTitle"])]] + [[Paragraph(f"\u2713 {item}", styles["BodyText"])] for item in completed[:10]]
    right_rows = [[Paragraph("Remaining", styles["SectionTitle"])]] + [[Paragraph(f"\u25cb {item}", styles["BodyText"])] for item in remaining[:10]]
    left = Table(left_rows, colWidths=[82 * mm])
    right = Table(right_rows, colWidths=[82 * mm])
    left.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), GREEN), ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    right.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), AMBER), ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    split = Table([[left, right]], colWidths=[85 * mm, 85 * mm])
    split.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(split)
    elements.append(Spacer(1, 5 * mm))
    return elements


def _benchmark_section(benchmark: list[dict], styles: dict) -> list:
    elements = [Paragraph("Competitor Benchmark", styles["SectionHeader"])]
    headers = ["Site", "Overall", "Technical", "Content", "Schema", "Entity", "Platforms"]
    rows = [headers]
    for index, item in enumerate(benchmark[:6]):
        row = [
            Paragraph(str(item.get("site", "")), styles["TableText"]),
            Paragraph(str(item.get("score", "")), styles["TableTextCenter"]),
            Paragraph(str(item.get("technical", "")), styles["TableTextCenter"]),
            Paragraph(str(item.get("content", "")), styles["TableTextCenter"]),
            Paragraph(str(item.get("schema", "")), styles["TableTextCenter"]),
            Paragraph(str(item.get("entity", "")), styles["TableTextCenter"]),
            Paragraph(str(item.get("platforms", "")), styles["TableTextCenter"]),
        ]
        rows.append(row)
    table = Table(rows, colWidths=[44 * mm, 18 * mm, 18 * mm, 18 * mm, 18 * mm, 18 * mm, 36 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.4),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if benchmark:
        style.append(("LINEABOVE", (0, 1), (-1, 1), 2.0, TEAL))
        style.append(("LINEBELOW", (0, 1), (-1, 1), 2.0, TEAL))
        style.append(("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    elements.append(table)
    elements.append(Spacer(1, 5 * mm))
    return elements


def _final_remarks_section(payload: dict, styles: dict) -> list:
    final_remarks = payload.get("final_remarks") or _synthesize_final_remarks(payload)
    panel = Table(
        [[Paragraph("Final Remarks", styles["SectionTitle"])], [Paragraph(final_remarks, styles["BodyText"])]],
        colWidths=[170 * mm],
    )
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, -1), PANEL),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return [Spacer(1, 5 * mm), panel]


def _draw_page_chrome(payload: dict):
    title = payload.get("title", "GEOsphere Executive Brief")
    site = payload.get("brand_name", "")
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    def draw(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, A4[1] - 11 * mm, A4[0] - doc.rightMargin, A4[1] - 11 * mm)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.setFillColor(NAVY)
        canvas.drawString(doc.leftMargin, A4[1] - 9 * mm, title)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(A4[0] - doc.rightMargin, A4[1] - 9 * mm, site)
        canvas.line(doc.leftMargin, 11 * mm, A4[0] - doc.rightMargin, 11 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(doc.leftMargin, 7 * mm, generated)
        canvas.drawRightString(A4[0] - doc.rightMargin, 7 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    return draw


def _from_audit_payload(payload: dict, path: Path) -> dict:
    audited_at = payload.get("run_id", "").split("T")[0] or datetime.utcnow().date().isoformat()
    module_scores = []
    for item in payload.get("modules", []):
        module_scores.append(
            {
                "name": str(item.get("name", "")).title(),
                "score": item.get("score", 0),
                "confidence": "",
                "driver": item.get("summary", ""),
            }
        )
    critical_issues = []
    for module in payload.get("modules", []):
        for finding in module.get("findings", []):
            if finding.get("severity") in {"high", "critical"}:
                critical_issues.append(
                    {
                        "title": f"{str(module.get('name', '')).title()} - {finding.get('title', '')}",
                        "detail": finding.get("detail", ""),
                        "scope": "",
                        "verification_status": "Artifact-derived",
                        "fix_location": "",
                        "effort": "",
                        "expected_impact": "",
                    }
                )
    return {
        "title": "GEOsphere Executive Brief",
        "brand_name": payload.get("brand_name", ""),
        "site_url": payload.get("target_url", ""),
        "run_id": payload.get("run_id", ""),
        "audited_at": audited_at,
        "overall_score": payload.get("total_score", 0),
        "confidence": "Deterministic",
        "executive_summary": "Generated from the local GEOsphere audit payload.",
        "opportunity_snapshot": {},
        "module_scores": module_scores,
        "platform_readiness": _platform_rows_from_summary(payload.get("summary", {})),
        "root_causes": payload.get("summary", {}).get("highlights", []),
        "critical_issues": critical_issues[:8],
        "quick_wins": [],
        "plan_30_day": [],
        "verification_notes": [],
        "source_path": str(path),
    }


def _from_collection_payload(payload: dict, path: Path) -> dict:
    summary = payload.get("summary", {})
    return {
        "title": "GEOsphere Collection Brief",
        "brand_name": payload.get("brand_name", ""),
        "site_url": payload.get("target_url", ""),
        "run_id": payload.get("run_id", ""),
        "audited_at": datetime.utcnow().date().isoformat(),
        "overall_score": "N/A",
        "confidence": "Collection only",
        "executive_summary": "This PDF was generated from collection artifacts only. Run a full Claude-led audit or provide a manager brief JSON for a calibrated executive report.",
        "module_scores": [],
        "platform_readiness": _platform_rows_from_summary(summary),
        "root_causes": [],
        "critical_issues": [],
        "quick_wins": [],
        "plan_30_day": [],
        "verification_notes": [],
        "source_path": str(path),
    }


def _platform_rows_from_summary(summary: dict) -> list[dict]:
    rows = []
    for name, score in summary.get("platform_scores", {}).items():
        rows.append({"platform": str(name).replace("_", " ").title(), "readiness": str(score), "blocker": ""})
    return rows


def _build_module_chart(module_scores: list[dict]) -> BytesIO | None:
    if not module_scores:
        return None
    names = [item.get("name", "") for item in module_scores]
    scores = [float(item.get("score", 0)) for item in module_scores]
    colors_list = [_score_hex(score) for score in scores]
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.edgecolor": "#cbd5e1",
            "axes.labelcolor": "#334155",
            "xtick.color": "#475569",
            "ytick.color": "#0f172a",
        }
    )
    fig, ax = plt.subplots(figsize=(8.4, 3.7))
    ax.barh(names, scores, color=colors_list, height=0.6)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Score")
    ax.grid(axis="x", color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for index, score in enumerate(scores):
        ax.text(min(score + 1.5, 96), index, f"{int(score)}", va="center", ha="left", fontsize=8.5, color="#0f172a")
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _build_platform_chart(platform_rows: list[dict]) -> BytesIO | None:
    if not platform_rows:
        return None
    scored_rows = []
    for item in platform_rows:
        value = item.get("score", item.get("readiness", ""))
        try:
            numeric = float(str(value).split("/")[0].strip())
        except Exception:
            continue
        scored_rows.append((item.get("platform", ""), numeric))
    if not scored_rows:
        return None
    names = [item[0] for item in scored_rows]
    scores = [item[1] for item in scored_rows]
    colors_list = [_score_hex(score) for score in scores]
    fig, ax = plt.subplots(figsize=(8.4, 3.7))
    ax.barh(names, scores, color=colors_list, height=0.6)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Readiness")
    ax.grid(axis="x", color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for index, score in enumerate(scores):
        ax.text(min(score + 1.5, 96), index, f"{int(score)}", va="center", ha="left", fontsize=8.5, color="#0f172a")
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _score_hex(score) -> str:
    try:
        value = float(score)
    except Exception:
        return "#94a3b8"
    if value >= 75:
        return "#15803d"
    if value >= 55:
        return "#1d4ed8"
    if value >= 40:
        return "#d97706"
    return "#dc2626"


def _score_fill(score):
    return colors.HexColor(_score_hex(score)).clone(alpha=0.12)


def _synthesize_final_remarks(payload: dict) -> str:
    parts = []
    if payload.get("executive_summary"):
        parts.append(str(payload.get("executive_summary", "")).strip())
    if payload.get("root_causes"):
        parts.append("Primary root causes: " + "; ".join(str(item) for item in payload.get("root_causes", [])[:4]) + ".")
    if payload.get("critical_issues"):
        titles = [str(item.get("title", "")) for item in payload.get("critical_issues", [])[:3] if item.get("title")]
        if titles:
            parts.append("Highest-priority corrections: " + "; ".join(titles) + ".")
    if payload.get("quick_wins"):
        wins = [str(item.get("action", "")) for item in payload.get("quick_wins", [])[:3] if item.get("action")]
        if wins:
            parts.append("Immediate next actions: " + "; ".join(wins) + ".")
    if payload.get("opportunity_snapshot", {}).get("ceiling_score"):
        parts.append(f"Estimated upside after the first wave of fixes: {payload['opportunity_snapshot'].get('ceiling_score')}.")
    return " ".join(part for part in parts if part).strip() or "This report consolidates the strongest verified findings, the highest-leverage fixes, and the fastest path to an improved GEO posture."


def _codeish(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
        .replace("  ", "&nbsp;&nbsp;")
    )


def _styles() -> dict:
    styles = getSampleStyleSheet()
    styles["Title"].fontName = "Helvetica-Bold"
    styles["Title"].fontSize = 24
    styles["Title"].leading = 28
    styles["Title"].alignment = TA_LEFT
    styles["Heading2"].fontName = "Helvetica-Bold"
    styles["Heading2"].fontSize = 16
    styles["Heading2"].leading = 20
    styles["Heading3"].fontName = "Helvetica-Bold"
    styles["Heading3"].fontSize = 11
    styles["Heading3"].leading = 14
    styles["BodyText"].fontName = "Helvetica"
    styles["BodyText"].fontSize = 9.4
    styles["BodyText"].leading = 13.4
    styles["BodyText"].textColor = SLATE
    styles.add(ParagraphStyle(name="HeroTitle", parent=styles["Title"], fontSize=23, leading=27, textColor=NAVY))
    styles.add(ParagraphStyle(name="HeroSubtitle", parent=styles["BodyText"], fontSize=12.5, leading=15, textColor=SLATE))
    styles.add(ParagraphStyle(name="MetaLine", parent=styles["BodyText"], fontSize=8.7, leading=11.5, textColor=MUTED))
    styles.add(ParagraphStyle(name="ScoreLabel", parent=styles["BodyText"], fontSize=8.5, leading=11, alignment=TA_CENTER, textColor=SLATE))
    styles.add(ParagraphStyle(name="ScoreValue", parent=styles["Title"], fontSize=28, leading=32, alignment=TA_CENTER, textColor=NAVY))
    styles.add(ParagraphStyle(name="ConfidencePill", parent=styles["BodyText"], fontSize=9, leading=11, alignment=TA_CENTER, textColor=SLATE))
    styles.add(ParagraphStyle(name="SectionHeader", parent=styles["Heading2"], fontSize=15, leading=19, textColor=NAVY, spaceAfter=6))
    styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading3"], fontSize=10.5, leading=13, textColor=WHITE))
    styles.add(ParagraphStyle(name="CardTitle", parent=styles["Heading3"], fontSize=11.5, leading=14.5, textColor=NAVY))
    styles.add(ParagraphStyle(name="MetaBody", parent=styles["BodyText"], fontSize=8.6, leading=12, textColor=MUTED))
    styles.add(ParagraphStyle(name="PhaseTitle", parent=styles["Heading3"], fontSize=10.5, leading=13.5, textColor=NAVY))
    styles.add(ParagraphStyle(name="MiniLabel", parent=styles["BodyText"], fontSize=8.2, leading=10.5, alignment=TA_CENTER, textColor=MUTED))
    styles.add(ParagraphStyle(name="MiniValue", parent=styles["Heading3"], fontSize=14, leading=17, alignment=TA_CENTER, textColor=NAVY))
    styles.add(ParagraphStyle(name="AppendixBody", parent=styles["BodyText"], fontSize=8.4, leading=11.4, textColor=SLATE, fontName="Courier"))
    styles.add(ParagraphStyle(name="TableText", parent=styles["BodyText"], fontSize=8.4, leading=11.2, textColor=SLATE))
    styles.add(ParagraphStyle(name="TableTextCenter", parent=styles["BodyText"], fontSize=8.4, leading=11.2, alignment=TA_CENTER, textColor=NAVY))
    return styles
