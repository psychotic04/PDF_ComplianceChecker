from pathlib import Path

import streamlit as st

from services import db_service
from ui.reports_page import render_reports_page
from ui.rules_page import render_rules_page
from ui.upload_page import render_upload_page


st.set_page_config(
    page_title="PDF Compliance Scanner",
    page_icon="PDF",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        .main .block-container { padding-top: 1.5rem; }
        .metric-card {
            border: 1px solid #e7e9ef;
            border-radius: 8px;
            padding: 18px 20px;
            background: #ffffff;
            box-shadow: 0 1px 6px rgba(20, 31, 56, 0.06);
        }
        .metric-card h3 {
            color: #5b6475;
            font-size: 0.9rem;
            margin: 0 0 8px 0;
            font-weight: 600;
        }
        .metric-card p {
            color: #151b2d;
            font-size: 1.8rem;
            margin: 0;
            font-weight: 700;
        }
        .status-ok { color: #0f8a5f; font-weight: 700; }
        .status-bad { color: #b42318; font-weight: 700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ensure_directories() -> None:
    for directory in ["uploads", "reports", "database", "rules", "prompts"]:
        Path(directory).mkdir(parents=True, exist_ok=True)


def render_dashboard() -> None:
    metrics = db_service.dashboard_metrics()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"<div class='metric-card'><h3>Total PDFs Scanned</h3><p>{metrics['total_scans']}</p></div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<div class='metric-card'><h3>Total Violations</h3><p>{metrics['total_violations']}</p></div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"<div class='metric-card'><h3>Compliance %</h3><p>{metrics['compliance_percentage']}%</p></div>",
            unsafe_allow_html=True,
        )
    st.divider()


def main() -> None:
    ensure_directories()
    db_service.init_db()
    apply_styles()

    st.sidebar.title("PDF Compliance Scanner")
    page = st.sidebar.radio("Navigate", ["Upload PDF", "Reports", "Compliance Rules"])

    st.title("AI-Powered PDF Compliance Scanner")
    render_dashboard()

    if page == "Upload PDF":
        render_upload_page()
    elif page == "Reports":
        render_reports_page()
    else:
        render_rules_page()


if __name__ == "__main__":
    main()
