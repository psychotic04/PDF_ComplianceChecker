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
for text-based PDFs. Scanned image PDFs require OCR before analysis.
- Compliance rules are editable in SQLite from the UI. The JSON file seeds the database on first run.
<img width="1026" height="581" alt="Screenshot 2026-06-04 at 4 00 53 PM" src="https://github.com/user-attachments/assets/ea5b27c0-da08-44e4-831f-d4015170af42" />

<img width="1023" height="583" alt="image" src="https://github.com/user-attachments/assets/dddd7836-7dee-4f09-b8c2-a2c5bfb90c8c" />

<img width="928" height="576" alt="image" src="https://github.com/user-attachments/assets/9072f7fe-5d4a-4b51-a8ab-b3a146bdffcd" />

<img width="916" height="557" alt="image" src="https://github.com/user-attachments/assets/8a78751a-3b6f-4062-91f0-eb39ef3c984b" />






