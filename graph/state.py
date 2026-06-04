from typing import Any, TypedDict


class ComplianceState(TypedDict, total=False):
    pdf_path: str
    scan_id: int
    pages: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    pii_results: list[dict[str, Any]]
    confidential_results: list[dict[str, Any]]
    encoding_results: list[dict[str, Any]]
    abusive_results: list[dict[str, Any]]
    performance_metrics: list[dict[str, Any]]
    final_report: dict[str, Any]
