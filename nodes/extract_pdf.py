import fitz

from graph.state import ComplianceState


CHUNK_SIZE = 2_000
CHUNK_OVERLAP = 250
RECURSIVE_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text.strip():
        return []
    base_chunks = _recursive_split(text, chunk_size, RECURSIVE_SEPARATORS)
    return _merge_chunks(base_chunks, chunk_size, overlap)


def _recursive_split(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    separator = separators[0]
    remaining_separators = separators[1:]
    if separator:
        pieces = text.split(separator)
        if len(pieces) == 1:
            return _recursive_split(text, chunk_size, remaining_separators)
        splits = []
        for index, piece in enumerate(pieces):
            if not piece:
                continue
            restored_piece = piece if index == len(pieces) - 1 else piece + separator
            if len(restored_piece) > chunk_size and remaining_separators:
                splits.extend(_recursive_split(restored_piece, chunk_size, remaining_separators))
            else:
                splits.append(restored_piece)
        return splits

    return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]


def _merge_chunks(splits: list[str], chunk_size: int, overlap: int) -> list[str]:
    chunks = []
    current = ""

    for split in splits:
        split = split.strip()
        if not split:
            continue
        if not current:
            current = split
        elif len(current) + len(split) <= chunk_size:
            current = f"{current} {split}"
        else:
            chunks.append(current)
            current = f"{_overlap_text(current, overlap)} {split}"

    if current:
        chunks.append(current)
    return chunks


def _overlap_text(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    return text[-overlap:].strip()


def extract_pdf_node(state: ComplianceState) -> ComplianceState:
    pages = []
    chunks = []
    with fitz.open(state["pdf_path"]) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text")
            pages.append({"page": index, "text": text})
            for chunk_index, chunk_text in enumerate(_split_text(text), start=1):
                chunks.append(
                    {
                        "page": index,
                        "chunk": chunk_index,
                        "text": chunk_text,
                    }
                )
    return {**state, "pages": pages, "chunks": chunks}
