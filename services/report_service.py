from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


REPORTS_DIR = Path("reports")


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    text = "-" if value is None or value == "" else str(value)
    return Paragraph(escape(text), style)


def build_summary(state: dict[str, Any]) -> dict[str, Any]:
    total_pages = len(state.get("pages", []))
    total_violations = 0

    for key in ["pii_results", "confidential_results", "encoding_results", "abusive_results"]:
        total_violations += sum(1 for item in state.get(key, []) if item.get("violation"))

    max_checks = max(total_pages * 4, 1)
    compliance_score = round(max(0.0, 100.0 - (total_violations / max_checks * 100.0)), 1)
    return {
        "total_pages": total_pages,
        "total_violations": total_violations,
        "compliance_score": compliance_score,
    }


def page_findings(state: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    pii_by_page = {item["page"]: item for item in state.get("pii_results", [])}
    confidential_by_page = {item["page"]: item for item in state.get("confidential_results", [])}
    encoding_by_page = {item["page"]: item for item in state.get("encoding_results", [])}
    abusive_by_page = {item["page"]: item for item in state.get("abusive_results", [])}

    for page in state.get("pages", []):
        page_number = page["page"]
        findings.append(
            {
                "page": page_number,
                "pii": pii_by_page.get(page_number, {}),
                "confidential": confidential_by_page.get(page_number, {}),
                "encoding": encoding_by_page.get(page_number, {}),
                "abusive": abusive_by_page.get(page_number, {}),
            }
        )
    return findings


def create_pdf_report(report: dict[str, Any], filename: str) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).stem.replace(" ", "_")
    report_path = REPORTS_DIR / f"{safe_name}_compliance_report.pdf"

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "ReportTableBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        wordWrap="CJK",
        splitLongWords=True,
    )
    label_style = ParagraphStyle(
        "ReportTableLabel",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    story = []

    story.append(Paragraph("PDF Compliance Scan Report", styles["Title"]))
    story.append(Spacer(1, 12))
    summary = report["summary"]
    summary_table = Table(
        [
            ["Total Pages", summary["total_pages"]],
            ["Total Violations", summary["total_violations"]],
            ["Compliance Score", f"{summary['compliance_score']}%"],
        ],
        colWidths=[180, 260],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 18))

    ai_metrics = report.get("ai_metrics", {})
    if ai_metrics:
        story.append(Paragraph("AI Usage Metrics", styles["Heading2"]))
        metrics_table = Table(
            [
                ["Gemini API Calls", ai_metrics.get("api_calls", 0)],
                ["Cache Hits", ai_metrics.get("cache_hits", 0)],
                ["Chunks Analyzed", ai_metrics.get("chunks_analyzed", 0)],
                ["Prompt Tokens", ai_metrics.get("prompt_tokens", 0)],
                ["Candidate Tokens", ai_metrics.get("candidate_tokens", 0)],
                ["Total Tokens", ai_metrics.get("total_tokens", 0)],
                ["Total Latency", f"{ai_metrics.get('latency_ms', 0)} ms"],
            ],
            colWidths=[180, 260],
        )
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("PADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(metrics_table)
        story.append(Spacer(1, 18))

    performance_metrics = report.get("performance_metrics", {})
    if performance_metrics and performance_metrics.get("by_stage"):
        story.append(Paragraph("Performance Metrics", styles["Heading2"]))
        performance_table = Table(
            [
                ["Total Scan Time", f"{performance_metrics.get('total_duration_ms', 0)} ms"],
                ["Pages Processed", performance_metrics.get("pages_count", 0)],
                ["Chunks Processed", performance_metrics.get("chunks_count", 0)],
                ["Pages/sec", performance_metrics.get("pages_per_second", 0)],
                ["Chunks/sec", performance_metrics.get("chunks_per_second", 0)],
            ],
            colWidths=[180, 260],
        )
        performance_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("PADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(performance_table)
        story.append(Spacer(1, 18))

    story.append(Paragraph("Detailed Findings", styles["Heading2"]))

    for finding in report["findings"]:
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Page {finding['page']}", styles["Heading3"]))
        pii_matches = ", ".join(finding["pii"].get("matches", [])) or "None"
        confidential = finding["confidential"].get("violation", False)
        abusive = finding["abusive"].get("violation", False)
        encoding_valid = finding["encoding"].get("encoding_valid", True)
        details = [
            [_paragraph("PII Found", label_style), _paragraph(pii_matches, body_style)],
            [_paragraph("Confidential", label_style), _paragraph(str(confidential), body_style)],
            [
                _paragraph("Confidential Reason", label_style),
                _paragraph(finding["confidential"].get("reason", "") or "-", body_style),
            ],
            [_paragraph("Abusive", label_style), _paragraph(str(abusive), body_style)],
            [
                _paragraph("Abusive Reason", label_style),
                _paragraph(finding["abusive"].get("reason", "") or "-", body_style),
            ],
            [_paragraph("Encoding", label_style), _paragraph("Valid" if encoding_valid else "Invalid", body_style)],
            [
                _paragraph("Encoding Reason", label_style),
                _paragraph(finding["encoding"].get("reason", "") or "-", body_style),
            ],
        ]
        label_width = 130
        table = Table(details, colWidths=[label_width, doc.width - label_width], repeatRows=0)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    return str(report_path)
