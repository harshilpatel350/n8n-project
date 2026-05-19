# AI Resume Screening and Candidate Intelligence Platform

Local-first AI recruitment workflow with resume upload, structured extraction, JD matching, SQLite persistence, and n8n webhook delivery.

## What you need

- Python 3.11+
- Node.js 18+
- OpenAI API key
- n8n webhook URL

## Setup

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY` and `N8N_WEBHOOK_URL`.
2. Create and activate a Python virtual environment.

```powershell
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

3. Install frontend dependencies.

```bash
cd frontend
npm install
```

If you want the frontend to talk to a backend other than `http://localhost:8000`, set `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`.

## Run the app

Backend:

```bash
scripts/run_backend.sh
```

Windows PowerShell:

```powershell
.\scripts\run_backend.ps1
```

Frontend:

```bash
scripts/run_frontend.sh
```

Windows PowerShell:

```powershell
.\scripts\run_frontend.ps1
```

## Optional utilities

- Legacy Streamlit UI: `streamlit run app.py`
- CSV to SQLite migration: `python scripts/migrate_candidates.py --csv storage/candidates.csv --db storage/candidates.db`

## Notes

- The backend serves the API at `http://localhost:8000`.
- The frontend runs at `http://localhost:3000`.
- The SQLite store uses WAL mode for safer concurrent writes.
