import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


DB_PATH = Path("database/compliance.db")
RULES_JSON_PATH = Path("rules/compliance_rules.json")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scans(
                id INTEGER PRIMARY KEY,
                filename TEXT,
                upload_time TEXT,
                report_path TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS compliance_results(
                id INTEGER PRIMARY KEY,
                scan_id INTEGER,
                page_number INTEGER,
                violation_type TEXT,
                reason TEXT,
                FOREIGN KEY(scan_id) REFERENCES scans(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS compliance_rules(
                id INTEGER PRIMARY KEY,
                rule_name TEXT,
                rule_description TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunk_analysis_cache(
                id INTEGER PRIMARY KEY,
                detector TEXT NOT NULL,
                model TEXT NOT NULL,
                chunk_hash TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(detector, model, chunk_hash)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_usage_metrics(
                id INTEGER PRIMARY KEY,
                scan_id INTEGER,
                detector TEXT NOT NULL,
                model TEXT NOT NULL,
                source TEXT NOT NULL,
                chunk_count INTEGER NOT NULL,
                batch_count INTEGER NOT NULL,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                candidate_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(scan_id) REFERENCES scans(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS performance_metrics(
                id INTEGER PRIMARY KEY,
                scan_id INTEGER,
                stage TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                pages_count INTEGER NOT NULL DEFAULT 0,
                chunks_count INTEGER NOT NULL DEFAULT 0,
                throughput_per_second REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(scan_id) REFERENCES scans(id)
            )
            """
        )
        if conn.execute("SELECT COUNT(*) FROM compliance_rules").fetchone()[0] == 0:
            seed_rules(conn)


def seed_rules(conn: sqlite3.Connection | None = None) -> None:
    RULES_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    rules = json.loads(RULES_JSON_PATH.read_text(encoding="utf-8"))
    owns_connection = conn is None
    conn = conn or get_connection()
    try:
        conn.executemany(
            "INSERT INTO compliance_rules(rule_name, rule_description) VALUES(?, ?)",
            [(rule["rule_name"], rule["rule_description"]) for rule in rules],
        )
        conn.commit()
    finally:
        if owns_connection:
            conn.close()


def create_scan(filename: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO scans(filename, upload_time, report_path) VALUES(?, ?, ?)",
            (filename, datetime.utcnow().isoformat(timespec="seconds"), ""),
        )
        return int(cursor.lastrowid)


def update_scan_report(scan_id: int, report_path: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE scans SET report_path = ? WHERE id = ?", (report_path, scan_id))


def save_compliance_result(scan_id: int, page_number: int, violation_type: str, reason: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO compliance_results(scan_id, page_number, violation_type, reason)
            VALUES(?, ?, ?, ?)
            """,
            (scan_id, page_number, violation_type, reason),
        )


def get_cached_chunk_results(detector: str, model: str, chunk_hashes: list[str]) -> dict[str, dict[str, Any]]:
    if not chunk_hashes:
        return {}

    placeholders = ", ".join("?" for _ in chunk_hashes)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT chunk_hash, result_json
            FROM chunk_analysis_cache
            WHERE detector = ?
              AND model = ?
              AND chunk_hash IN ({placeholders})
            """,
            [detector, model, *chunk_hashes],
        ).fetchall()

    cached = {}
    for row in rows:
        try:
            cached[row["chunk_hash"]] = json.loads(row["result_json"])
        except json.JSONDecodeError:
            continue
    return cached


def save_chunk_result(detector: str, model: str, chunk_hash: str, result: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO chunk_analysis_cache(
                detector,
                model,
                chunk_hash,
                result_json,
                created_at
            )
            VALUES(?, ?, ?, ?, ?)
            """,
            (
                detector,
                model,
                chunk_hash,
                json.dumps(result),
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )


def save_ai_usage_metric(
    scan_id: int | None,
    detector: str,
    model: str,
    source: str,
    chunk_count: int,
    batch_count: int,
    prompt_tokens: int = 0,
    candidate_tokens: int = 0,
    total_tokens: int = 0,
    latency_ms: int = 0,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_usage_metrics(
                scan_id,
                detector,
                model,
                source,
                chunk_count,
                batch_count,
                prompt_tokens,
                candidate_tokens,
                total_tokens,
                latency_ms,
                created_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                detector,
                model,
                source,
                chunk_count,
                batch_count,
                prompt_tokens,
                candidate_tokens,
                total_tokens,
                latency_ms,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )


def list_ai_usage_metrics(scan_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                detector,
                model,
                source,
                chunk_count,
                batch_count,
                prompt_tokens,
                candidate_tokens,
                total_tokens,
                latency_ms,
                created_at
            FROM ai_usage_metrics
            WHERE scan_id = ?
            ORDER BY id
            """,
            (scan_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def summarize_ai_usage_metrics(scan_id: int) -> dict[str, Any]:
    rows = list_ai_usage_metrics(scan_id)
    totals = {
        "api_calls": 0,
        "cache_hits": 0,
        "chunks_analyzed": 0,
        "prompt_tokens": 0,
        "candidate_tokens": 0,
        "total_tokens": 0,
        "latency_ms": 0,
    }
    by_detector: dict[str, dict[str, Any]] = {}

    for row in rows:
        detector = row["detector"]
        detector_totals = by_detector.setdefault(
            detector,
            {
                "detector": detector,
                "model": row["model"],
                "api_calls": 0,
                "cache_hits": 0,
                "chunks_analyzed": 0,
                "prompt_tokens": 0,
                "candidate_tokens": 0,
                "total_tokens": 0,
                "latency_ms": 0,
            },
        )

        chunk_count = int(row["chunk_count"])
        batch_count = int(row["batch_count"])
        prompt_tokens = int(row["prompt_tokens"])
        candidate_tokens = int(row["candidate_tokens"])
        total_tokens = int(row["total_tokens"])
        latency_ms = int(row["latency_ms"])

        totals["chunks_analyzed"] += chunk_count
        detector_totals["chunks_analyzed"] += chunk_count

        if row["source"] == "cache":
            totals["cache_hits"] += chunk_count
            detector_totals["cache_hits"] += chunk_count
        else:
            totals["api_calls"] += batch_count
            detector_totals["api_calls"] += batch_count

        for key, value in [
            ("prompt_tokens", prompt_tokens),
            ("candidate_tokens", candidate_tokens),
            ("total_tokens", total_tokens),
            ("latency_ms", latency_ms),
        ]:
            totals[key] += value
            detector_totals[key] += value

    return {
        **totals,
        "by_detector": list(by_detector.values()),
        "events": rows,
    }


def save_performance_metric(
    scan_id: int | None,
    stage: str,
    duration_ms: int,
    pages_count: int = 0,
    chunks_count: int = 0,
) -> None:
    duration_seconds = max(duration_ms / 1000.0, 0.001)
    work_units = chunks_count or pages_count
    throughput = round(work_units / duration_seconds, 2) if work_units else 0.0

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO performance_metrics(
                scan_id,
                stage,
                duration_ms,
                pages_count,
                chunks_count,
                throughput_per_second,
                created_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                stage,
                duration_ms,
                pages_count,
                chunks_count,
                throughput,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )


def list_performance_metrics(scan_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                stage,
                duration_ms,
                pages_count,
                chunks_count,
                throughput_per_second,
                created_at
            FROM performance_metrics
            WHERE scan_id = ?
            ORDER BY id
            """,
            (scan_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def summarize_performance_metrics(scan_id: int) -> dict[str, Any]:
    rows = list_performance_metrics(scan_id)
    total_duration_ms = sum(int(row["duration_ms"]) for row in rows)
    pages_count = max((int(row["pages_count"]) for row in rows), default=0)
    chunks_count = max((int(row["chunks_count"]) for row in rows), default=0)
    scan_seconds = max(total_duration_ms / 1000.0, 0.001)

    return {
        "total_duration_ms": total_duration_ms,
        "pages_count": pages_count,
        "chunks_count": chunks_count,
        "chunks_per_second": round(chunks_count / scan_seconds, 2) if chunks_count else 0.0,
        "pages_per_second": round(pages_count / scan_seconds, 2) if pages_count else 0.0,
        "by_stage": rows,
    }


def list_scans() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                scans.id,
                scans.filename,
                scans.upload_time,
                scans.report_path,
                COUNT(compliance_results.id) AS violations
            FROM scans
            LEFT JOIN compliance_results ON scans.id = compliance_results.scan_id
            GROUP BY scans.id
            ORDER BY scans.id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def list_results(scan_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT page_number, violation_type, reason
            FROM compliance_results
            WHERE scan_id = ?
            ORDER BY page_number, violation_type
            """,
            (scan_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def dashboard_metrics() -> dict[str, Any]:
    with get_connection() as conn:
        total_scans = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        total_violations = conn.execute("SELECT COUNT(*) FROM compliance_results").fetchone()[0]
    compliance = 100.0 if total_scans == 0 else max(0.0, 100.0 - (total_violations / max(total_scans, 1) * 10.0))
    return {
        "total_scans": total_scans,
        "total_violations": total_violations,
        "compliance_percentage": round(compliance, 1),
    }


def list_rules() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, rule_name, rule_description FROM compliance_rules ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def add_rule(rule_name: str, rule_description: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO compliance_rules(rule_name, rule_description) VALUES(?, ?)",
            (rule_name, rule_description),
        )


def update_rule(rule_id: int, rule_name: str, rule_description: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE compliance_rules SET rule_name = ?, rule_description = ? WHERE id = ?",
            (rule_name, rule_description, rule_id),
        )


def delete_rule(rule_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM compliance_rules WHERE id = ?", (rule_id,))
