from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from time import perf_counter
from typing import Any

from services import db_service
from services.gemini_service import GeminiService


BATCH_SIZE = 5
MAX_WORKERS = 3


def analyze_chunks(
    detector: str,
    prompt_name: str,
    result_key: str,
    fallback: dict[str, Any],
    chunks: list[dict[str, Any]],
    scan_id: int | None = None,
) -> list[dict[str, Any]]:
    service = GeminiService()
    model = service.model
    chunk_hashes = [_chunk_hash(chunk["text"]) for chunk in chunks]
    cached_results = db_service.get_cached_chunk_results(detector, model, chunk_hashes)

    results: list[dict[str, Any] | None] = [None] * len(chunks)
    missing = []
    for index, (chunk, chunk_hash) in enumerate(zip(chunks, chunk_hashes)):
        cached_result = cached_results.get(chunk_hash)
        if cached_result is not None:
            results[index] = cached_result
        else:
            missing.append((index, chunk, chunk_hash))

    cache_hits = len(chunks) - len(missing)
    if cache_hits:
        db_service.save_ai_usage_metric(
            scan_id=scan_id,
            detector=detector,
            model=model,
            source="cache",
            chunk_count=cache_hits,
            batch_count=0,
        )

    if missing:
        batches = [missing[index : index + BATCH_SIZE] for index in range(0, len(missing), BATCH_SIZE)]
        worker_count = min(MAX_WORKERS, len(batches))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(
                    _analyze_batch,
                    detector,
                    prompt_name,
                    result_key,
                    fallback,
                    model,
                    batch,
                    scan_id,
                )
                for batch in batches
            ]
            for future in as_completed(futures):
                for index, result in future.result():
                    results[index] = result

    return [result if result is not None else fallback.copy() for result in results]


def _analyze_batch(
    detector: str,
    prompt_name: str,
    result_key: str,
    fallback: dict[str, Any],
    model: str,
    batch: list[tuple[int, dict[str, Any], str]],
    scan_id: int | None,
) -> list[tuple[int, dict[str, Any]]]:
    texts = [chunk["text"] for _, chunk, _ in batch]
    service = GeminiService()
    started_at = perf_counter()
    batch_results, usage = service.analyze_json_batch_with_usage(prompt_name, texts, result_key, fallback)
    latency_ms = int((perf_counter() - started_at) * 1000)

    db_service.save_ai_usage_metric(
        scan_id=scan_id,
        detector=detector,
        model=model,
        source="api",
        chunk_count=len(batch),
        batch_count=1,
        prompt_tokens=usage["prompt_tokens"],
        candidate_tokens=usage["candidate_tokens"],
        total_tokens=usage["total_tokens"],
        latency_ms=latency_ms,
    )

    indexed_results = []
    for (index, _chunk, chunk_hash), result in zip(batch, batch_results):
        indexed_results.append((index, result))
        if service.enabled and _is_cacheable(result):
            db_service.save_chunk_result(detector, model, chunk_hash, result)
    return indexed_results


def _chunk_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _is_cacheable(result: dict[str, Any]) -> bool:
    reason = str(result.get("reason", "")).lower()
    skipped_markers = [
        "api key is not configured",
        "temporarily unavailable",
        "could not be completed",
    ]
    return not any(marker in reason for marker in skipped_markers)
