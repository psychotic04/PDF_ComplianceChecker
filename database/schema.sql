CREATE TABLE IF NOT EXISTS scans(
    id INTEGER PRIMARY KEY,
    filename TEXT,
    upload_time TEXT,
    report_path TEXT
);

CREATE TABLE IF NOT EXISTS compliance_results(
    id INTEGER PRIMARY KEY,
    scan_id INTEGER,
    page_number INTEGER,
    violation_type TEXT,
    reason TEXT,
    FOREIGN KEY(scan_id) REFERENCES scans(id)
);

CREATE TABLE IF NOT EXISTS compliance_rules(
    id INTEGER PRIMARY KEY,
    rule_name TEXT,
    rule_description TEXT
);

CREATE TABLE IF NOT EXISTS chunk_analysis_cache(
    id INTEGER PRIMARY KEY,
    detector TEXT NOT NULL,
    model TEXT NOT NULL,
    chunk_hash TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(detector, model, chunk_hash)
);

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
);

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
);
