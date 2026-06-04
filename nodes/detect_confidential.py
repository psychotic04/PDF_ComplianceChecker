from graph.state import ComplianceState
from services.chunk_analysis_service import analyze_chunks


def detect_confidential_node(state: ComplianceState) -> ComplianceState:
    results_by_page = {
        page["page"]: {
            "page": page["page"],
            "violation": False,
            "type": "Confidential",
            "reason": "",
            "reasons": [],
        }
        for page in state.get("pages", [])
    }

    chunks = state.get("chunks") or [
        {"page": page["page"], "chunk": 1, "text": page["text"]} for page in state.get("pages", [])
    ]

    analyses = analyze_chunks(
        detector="confidential",
        prompt_name="confidential_prompt.txt",
        result_key="confidential",
        fallback={"confidential": False, "reason": ""},
        chunks=chunks,
        scan_id=state.get("scan_id"),
    )

    for chunk, analysis in zip(chunks, analyses):
        page_result = results_by_page.setdefault(
            chunk["page"],
            {
                "page": chunk["page"],
                "violation": False,
                "type": "Confidential",
                "reason": "",
                "reasons": [],
            },
        )
        page_result["violation"] = page_result["violation"] or bool(analysis.get("confidential", False))

        reason = str(analysis.get("reason", "")).strip()
        if reason:
            page_result["reasons"].append(f"Chunk {chunk['chunk']}: {reason}")

    results = []
    for page_number in sorted(results_by_page):
        page_result = results_by_page[page_number]
        reasons = page_result.pop("reasons")
        page_result["reason"] = " ".join(reasons)
        results.append(page_result)

    return {**state, "confidential_results": results}
