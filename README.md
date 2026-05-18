# AI Resume Screening and Candidate Intelligence

This repository contains a Streamlit-based UI, local n8n webhook integration, resume parsing, OpenAI analysis, and candidate persistence. The project is configured for local development and includes tests and a migration tool to move legacy CSV data into an SQLite database.

Getting started

1. Create a Python environment (recommended Python 3.11+):

```bash
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Create a `.env` file with the required variables (see `.env.example`):

- `OPENAI_API_KEY` (required)
- `N8N_WEBHOOK_URL` (required)
- `N8N_TEST_WEBHOOK_URL` (optional)

3. Run the Streamlit app:

```bash
streamlit run app.py
```

Migration from legacy CSV

If you have an existing `storage/candidates.csv`, migrate it to SQLite:

```bash
python scripts/migrate_candidates.py --csv storage/candidates.csv --db storage/candidates.db
```

CI

This repo includes a GitHub Actions workflow to run tests on push. The workflow sets minimal environment variables required for tests. You can view it at `.github/workflows/ci.yml`.

Docker

Build the app image:

```bash
docker build -t ai-resume-screening:latest .
docker run -p 8501:8501 --env-file .env ai-resume-screening:latest
```

Notes

- For local n8n, use a portable Node runtime if you prefer not to install globally. The project stores n8n data in `.n8n-local` by default.
- The SQLite store uses WAL mode for concurrent writes.
# AI Resume Screening and Candidate Intelligence Platform

A production-grade AI recruitment intelligence platform for resume ingestion, structured extraction, job description matching, and automated HR workflows. Built for enterprise teams that need consistent, explainable candidate insights and automated downstream actions.

## Architecture

- Streamlit UI provides a professional front end for HR teams.
- Configuration and logging are centralized for consistent operations.
- Services layer encapsulates AI extraction, scoring, persistence, and webhook delivery.
- Utilities provide parsing, validation, prompts, and shared helpers.
- CSV storage offers simple persistence for audit and analytics.
- n8n workflow automates Google Sheets updates and HR notifications.

## Features

- PDF resume upload with validation
- Structured candidate extraction (name, skills, education, experience, certifications)
- Job description matching with weighted scoring
- AI-generated summary, strengths, weaknesses, interview questions
- Experience analysis and hiring recommendation
- Persistent storage in storage/candidates.csv
- n8n webhook integration for HR automation
- Centralized logging to logs/app.log

## Tech Stack

- Python 3.11+
- Streamlit
- OpenAI API
- pdfplumber
- pandas, numpy, scikit-learn
- python-dotenv
- requests

## Setup

1. Create and activate a virtual environment
   - python -m venv venv
   - .\venv\Scripts\Activate.ps1

2. Install dependencies
   - python -m pip install --upgrade pip
   - pip install -r requirements.txt

3. Configure environment variables
   - Copy .env.example to .env
   - Set OPENAI_API_KEY and N8N_WEBHOOK_URL

4. Run the app
   - streamlit run app.py

## Configuration

The app uses .env only. Required variables:

- OPENAI_API_KEY
- N8N_WEBHOOK_URL

## n8n Workflow

1. Import workflows/n8n_workflow.json into n8n.
2. Update Google Sheets and SMTP credentials in the workflow.
3. Use the webhook URL from the Webhook node as N8N_WEBHOOK_URL.

## Troubleshooting

- OpenAI errors: validate API key and model access.
- Webhook errors: check the n8n URL and webhook node path.
- PDF extraction errors: use text-based PDFs rather than scanned images.
- Scoring seems low: adjust weights in utils/constants.py.

## Future Scalability

- Replace CSV storage with a relational database and search index.
- Add role-based access control and audit trails.
- Introduce multi-tenant separation for enterprise deployments.
- Add model routing, prompt versioning, and evaluation tracking.

## Deployment Ideas

- Containerize with Docker and deploy to Azure Container Apps.
- Add a background worker for asynchronous processing.
- Use a managed database for multi-user access.

## Interview Talking Points

- Modular layered architecture for long-term maintainability.
- Structured AI outputs with robust validation and retries.
- Clear separation of UI, services, and utilities.
- Production-grade logging and error handling.
- Automation-ready integrations with n8n.
