from graph.state import ComplianceState
from services import db_service
from services.report_service import build_summary, create_pdf_report, page_findings


def generate_report_node(state: ComplianceState) -> ComplianceState:
    report = {
        "summary": build_summary(state),
        "findings": page_findings(state),
    }

    scan_id = state.get("scan_id")
    if scan_id:
        for finding in report["findings"]:
            if finding["pii"].get("violation"):
                db_service.save_compliance_result(
                    scan_id,
                    finding["page"],
                    "PII",
                    ", ".join(finding["pii"].get("matches", [])),
                )
            if finding["confidential"].get("violation"):
                db_service.save_compliance_result(
                    scan_id,
                    finding["page"],
                    "Confidential",
                    finding["confidential"].get("reason", ""),
                )
            if finding["encoding"].get("violation"):
                db_service.save_compliance_result(
                    scan_id,
                    finding["page"],
                    "Encoding",
                    finding["encoding"].get("reason", ""),
                )
            if finding["abusive"].get("violation"):
                db_service.save_compliance_result(
                    scan_id,
                    finding["page"],
                    "Abusive",
                    finding["abusive"].get("reason", ""),
                )

        for metric in state.get("performance_metrics", []):
            db_service.save_performance_metric(
                scan_id=scan_id,
                stage=metric["stage"],
                duration_ms=metric["duration_ms"],
                pages_count=metric.get("pages_count", 0),
                chunks_count=metric.get("chunks_count", 0),
            )
        report["ai_metrics"] = db_service.summarize_ai_usage_metrics(scan_id)
        report["performance_metrics"] = db_service.summarize_performance_metrics(scan_id)
        report_path = create_pdf_report(report, state["pdf_path"])
        db_service.update_scan_report(scan_id, report_path)
        report["report_path"] = report_path

    return {**state, "final_report": report}
