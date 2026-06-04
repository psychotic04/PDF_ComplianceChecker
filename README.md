# AI-Powered PDF Compliance Scanner

A Streamlit application for uploading text-based PDFs, extracting page-wise text with PyMuPDF, running compliance checks through a LangGraph workflow, storing scan results in SQLite, and generating downloadable PDF compliance reports.

## Features

- Upload text-based PDF files.
- Extract text page-by-page with PyMuPDF.
- Run Presidio-backed PII detection for email IDs, phone numbers, Aadhaar numbers, PAN numbers, and credit card numbers.
- Run Gemini 2.5 Flash checks for confidential information.
- Run Detoxify pretrained toxicity checks for abusive or unlawful content.
- Validate UTF-8, English-only text, and unsupported symbols.
- Orchestrate the scan with LangGraph.
- Store scans, violations, and editable compliance rules in SQLite.
- Generate downloadable PDF reports.
- Manage compliance rules from the Streamlit UI.

## Project Structure

```text
pdf-compliance-scanner/
├── app.py
├── ui/
│   ├── upload_page.py
│   ├── reports_page.py
│   └── rules_page.py
├── graph/
│   ├── compliance_graph.py
│   └── state.py
├── nodes/
│   ├── extract_pdf.py
│   ├── detect_pii.py
│   ├── detect_confidential.py
│   ├── detect_encoding.py
│   ├── detect_abusive.py
│   └── generate_report.py
├── services/
│   ├── abusive_service.py
│   ├── gemini_service.py
│   ├── pii_service.py
│   ├── report_service.py
│   └── db_service.py
├── database/
│   ├── compliance.db
│   └── schema.sql
├── uploads/
├── reports/
├── rules/
│   └── compliance_rules.json
├── prompts/
│   ├── confidential_prompt.txt
│   └── abusive_prompt.txt
├── scripts/
│   └── generate_sample_pdf.py
└── requirements.txt
```

## Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Configure Gemini.

```bash
cp .env.example .env
```

Edit `.env` and set:

```text
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

4. Generate the demo PDF.

```bash
python scripts/generate_sample_pdf.py
```

5. Run the application.

```bash
streamlit run app.py
```

## Workflow

```text
START
  |
Extract PDF
  |
PII Detection
  |
Confidential Detection
  |
Encoding Validation
  |
Abusive Content Detection
  |
Generate Report
  |
END
```

## Database

The application initializes SQLite automatically at `database/compliance.db`. The SQL schema is also available in `database/schema.sql`.

## Notes

- Gemini confidential checks return a safe fallback when `GEMINI_API_KEY` is not configured, so the app remains runnable for UI, PII, encoding, and Detoxify demos.
- This scanner is designed for text-based PDFs. Scanned image PDFs require OCR before analysis.
- Compliance rules are editable in SQLite from the UI. The JSON file seeds the database on first run.
