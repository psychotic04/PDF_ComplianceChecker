from pathlib import Path

import streamlit as st

from services import db_service


def render_reports_page() -> None:
    st.header("Reports")
    scans = db_service.list_scans()
    if not scans:
        st.info("No scans available yet.")
        return

    for scan in scans:
        with st.expander(f"#{scan['id']} - {scan['filename']}"):
            st.write(f"Uploaded: `{scan['upload_time']}`")
            st.write(f"Violations: **{scan['violations']}**")

            results = db_service.list_results(scan["id"])
            if results:
                st.dataframe(results, use_container_width=True, hide_index=True)
            else:
                st.success("No violations recorded for this scan.")

            ai_metrics = db_service.summarize_ai_usage_metrics(scan["id"])
            if ai_metrics.get("chunks_analyzed", 0):
                st.subheader("AI Usage Metrics")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("API Calls", ai_metrics.get("api_calls", 0))
                col2.metric("Cache Hits", ai_metrics.get("cache_hits", 0))
                col3.metric("Total Tokens", ai_metrics.get("total_tokens", 0))
                col4.metric("Latency", f"{ai_metrics.get('latency_ms', 0)} ms")

                detector_rows = ai_metrics.get("by_detector", [])
                if detector_rows:
                    st.dataframe(detector_rows, use_container_width=True, hide_index=True)

            performance_metrics = db_service.summarize_performance_metrics(scan["id"])
            if performance_metrics.get("by_stage", []):
                st.subheader("Performance Metrics")
                perf1, perf2, perf3, perf4 = st.columns(4)
                perf1.metric("Total Scan Time", f"{performance_metrics.get('total_duration_ms', 0)} ms")
                perf2.metric("Chunks", performance_metrics.get("chunks_count", 0))
                perf3.metric("Pages/sec", performance_metrics.get("pages_per_second", 0))
                perf4.metric("Chunks/sec", performance_metrics.get("chunks_per_second", 0))
                st.dataframe(performance_metrics.get("by_stage", []), use_container_width=True, hide_index=True)

            report_path = scan.get("report_path")
            if report_path and Path(report_path).exists():
                path = Path(report_path)
                st.download_button(
                    "Download Report",
                    data=path.read_bytes(),
                    file_name=path.name,
                    mime="application/pdf",
                    key=f"download-{scan['id']}",
                )
            else:
                st.warning("Report file is not available on disk.")
