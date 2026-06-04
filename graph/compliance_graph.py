from time import perf_counter

from langgraph.graph import END, START, StateGraph

from graph.state import ComplianceState
from nodes.detect_abusive import detect_abusive_node
from nodes.detect_confidential import detect_confidential_node
from nodes.detect_encoding import detect_encoding_node
from nodes.detect_pii import detect_pii_node
from nodes.extract_pdf import extract_pdf_node
from nodes.generate_report import generate_report_node


STAGE_LABELS = {
    "extract_pdf": "Extract PDF",
    "detect_pii": "PII Detection",
    "detect_confidential": "Confidential Detection",
    "detect_encoding": "Encoding Validation",
    "detect_abusive": "Abusive Detection",
    "generate_report": "Report Generation",
}


def timed_node(stage: str, node):
    def wrapper(state: ComplianceState) -> ComplianceState:
        started_at = perf_counter()
        result = node(state)
        duration_ms = int((perf_counter() - started_at) * 1000)
        metric = {
            "stage": STAGE_LABELS.get(stage, stage),
            "duration_ms": duration_ms,
            "pages_count": len(result.get("pages", [])),
            "chunks_count": len(result.get("chunks", [])),
        }
        return {
            **result,
            "performance_metrics": [*state.get("performance_metrics", []), metric],
        }

    return wrapper


def build_compliance_graph():
    workflow = StateGraph(ComplianceState)
    workflow.add_node("extract_pdf", timed_node("extract_pdf", extract_pdf_node))
    workflow.add_node("detect_pii", timed_node("detect_pii", detect_pii_node))
    workflow.add_node("detect_confidential", timed_node("detect_confidential", detect_confidential_node))
    workflow.add_node("detect_encoding", timed_node("detect_encoding", detect_encoding_node))
    workflow.add_node("detect_abusive", timed_node("detect_abusive", detect_abusive_node))
    workflow.add_node("generate_report", timed_node("generate_report", generate_report_node))

    workflow.add_edge(START, "extract_pdf")
    workflow.add_edge("extract_pdf", "detect_pii")
    workflow.add_edge("detect_pii", "detect_confidential")
    workflow.add_edge("detect_confidential", "detect_encoding")
    workflow.add_edge("detect_encoding", "detect_abusive")
    workflow.add_edge("detect_abusive", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()
