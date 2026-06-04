from graph.state import ComplianceState
from services.pii_service import detect_pii


def detect_pii_node(state: ComplianceState) -> ComplianceState:
    matches_by_page = {page["page"]: [] for page in state.get("pages", [])}
    chunks = state.get("chunks") or [
        {"page": page["page"], "chunk": 1, "text": page["text"]} for page in state.get("pages", [])
    ]

    for chunk in chunks:
        matches_by_page.setdefault(chunk["page"], []).extend(detect_pii(chunk["text"]))

    results = []
    for page_number in sorted(matches_by_page):
        normalized = sorted(set(match.strip() for match in matches_by_page[page_number] if match.strip()))
        results.append(
            {
                "page": page_number,
                "violation": bool(normalized),
                "type": "PII",
                "matches": normalized,
            }
        )
    return {**state, "pii_results": results}
