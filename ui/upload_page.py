from pathlib import Path
from time import sleep

import streamlit as st

from graph.compliance_graph import build_compliance_graph
from services import db_service


UPLOAD_DIR = Path("uploads")


def _save_upload(uploaded_file) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / uploaded_file.name
    file_path.write_bytes(uploaded_file.getbuffer())
    return file_path


def _render_summary(report: dict) -> None:
    summary = report["summary"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Pages", summary["total_pages"])
    col2.metric("Total Violations", summary["total_violations"])
    col3.metric("Compliance Score", f"{summary['compliance_score']}%")

    ai_metrics = report.get("ai_metrics", {})
    if ai_metrics:
        st.subheader("AI Usage Metrics")
        metric_cols = st.columns(4)
        metric_cols[0].metric("Gemini API Calls", ai_metrics.get("api_calls", 0))
        metric_cols[1].metric("Cache Hits", ai_metrics.get("cache_hits", 0))
        metric_cols[2].metric("Total Tokens", ai_metrics.get("total_tokens", 0))
        metric_cols[3].metric("Latency", f"{ai_metrics.get('latency_ms', 0)} ms")

    performance_metrics = report.get("performance_metrics", {})
    if performance_metrics and performance_metrics.get("by_stage"):
        st.subheader("Performance Metrics")
        perf_cols = st.columns(4)
        perf_cols[0].metric("Total Scan Time", f"{performance_metrics.get('total_duration_ms', 0)} ms")
        perf_cols[1].metric("Chunks", performance_metrics.get("chunks_count", 0))
        perf_cols[2].metric("Pages/sec", performance_metrics.get("pages_per_second", 0))
        perf_cols[3].metric("Chunks/sec", performance_metrics.get("chunks_per_second", 0))
        st.dataframe(performance_metrics["by_stage"], use_container_width=True, hide_index=True)

    st.subheader("Page-wise Violations")
    for finding in report["findings"]:
        with st.expander(f"Page {finding['page']}", expanded=finding["page"] == 1):
            pii = finding["pii"]
            confidential = finding["confidential"]
            abusive = finding["abusive"]
            encoding = finding["encoding"]

            if pii.get("violation"):
                st.error(f"PII Found: {', '.join(pii.get('matches', []))}")
            else:
                st.success("PII Found: None")

            st.write(f"Confidential: **{confidential.get('violation', False)}**")
            if confidential.get("reason"):
                st.caption(confidential["reason"])

            st.write(f"Abusive: **{abusive.get('violation', False)}**")
            if abusive.get("reason"):
                st.caption(abusive["reason"])

            encoding_valid = encoding.get("encoding_valid", True)
            st.write(f"Encoding: **{'Valid' if encoding_valid else 'Invalid'}**")
            if encoding.get("reason"):
                st.caption(encoding["reason"])

    report_path = report.get("report_path")
    if report_path and Path(report_path).exists():
        st.download_button(
            "Download Compliance Report",
            data=Path(report_path).read_bytes(),
            file_name=Path(report_path).name,
            mime="application/pdf",
        )


def render_upload_page() -> None:
    st.header("Upload PDF")
    uploaded_file = st.file_uploader("Choose a text-based PDF document", type=["pdf"])

    if uploaded_file:
        st.info(f"Selected file: {uploaded_file.name}")

    if st.button("Start Scan", type="primary", disabled=uploaded_file is None):
        progress = st.progress(0, text="Saving uploaded PDF")
        file_path = _save_upload(uploaded_file)
        sleep(0.1)
        progress.progress(15, text="Creating scan record")
        scan_id = db_service.create_scan(uploaded_file.name)
        sleep(0.1)
        progress.progress(30, text="Running LangGraph compliance workflow")

        graph = build_compliance_graph()
        result = graph.invoke({"pdf_path": str(file_path), "scan_id": scan_id})
        result["final_report"]["performance_metrics"] = db_service.summarize_performance_metrics(scan_id)
        progress.progress(90, text="Finalizing report")
        sleep(0.1)
        progress.progress(100, text="Scan complete")

        st.success("Compliance scan completed.")
        _render_summary(result["final_report"])
