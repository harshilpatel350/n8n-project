from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# allow importing project services from parent folder
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from config.settings import get_settings, Settings  # type: ignore
from services.openai_service import OpenAIService  # type: ignore
from services.resume_service import ResumeService  # type: ignore
from services.scoring_service import ScoringService  # type: ignore
from services.candidate_service import CandidateStorage  # type: ignore
from services.webhook_service import WebhookService  # type: ignore
from utils.constants import STORAGE_DIR_NAME, CANDIDATES_DB_NAME
from utils.helpers import ensure_dir, now_iso, safe_filename  # type: ignore

app = FastAPI(title="AI Resume Screening API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _init_services() -> dict[str, Any]:
    try:
        settings: Settings = get_settings()
    except Exception as exc:
        # settings not available; return partial state for /health to surface
        return {"error": str(exc)}

    base = Path(__file__).resolve().parents[1]
    storage_dir = base / STORAGE_DIR_NAME
    ensure_dir(str(storage_dir))
    db_path = str(storage_dir / CANDIDATES_DB_NAME)

    openai_service = OpenAIService(api_key=settings.openai_api_key, model=settings.openai_model)
    resume_service = ResumeService(openai_service)
    scoring_service = ScoringService()
    storage = CandidateStorage(db_path)
    webhook_service = WebhookService(settings.n8n_webhook_url, fallback_webhook_url=settings.n8n_test_webhook_url)

    return {
        "settings": settings,
        "openai": openai_service,
        "resume": resume_service,
        "scoring": scoring_service,
        "storage": storage,
        "webhook": webhook_service,
    }


@app.on_event("startup")
def startup_event() -> None:
    # initialize services once and stash on app.state
    app.state.services = _init_services()


@app.get("/api/health")
def health() -> dict:
    services = getattr(app.state, "services", None) or {}
    if services.get("error"):
        return {"status": "error", "reason": services.get("error")}
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_description: str = Form(""),
) -> dict:
    services = getattr(app.state, "services", None) or _init_services()
    if services.get("error"):
        raise HTTPException(status_code=500, detail=services.get("error"))

    settings: Settings = services["settings"]

    # basic validation
    content = await file.read()
    if file.content_type not in settings.allowed_mime_types:
        raise HTTPException(status_code=400, detail="Invalid file type")

    # reuse existing logic from Streamlit app
    try:
        timestamp = now_iso()
        safe_name = safe_filename(file.filename)

        extraction = services["resume"].extract_candidate(content, file.filename)

        scoring = services["scoring"].score_candidate(
            extraction["candidate"], job_description, extraction["resume_text"]
        )

        analysis = services["openai"].generate_candidate_analysis(
            extraction["candidate"], job_description, scoring
        )

        final_score = scoring["final_score"]
        recommendation = analysis.get("hiring_recommendation", "Review manually")

        record = {
            "timestamp": timestamp,
            "name": extraction["candidate"]["name"],
            "score": final_score,
            "recommendation": recommendation,
            "skills": extraction["candidate"].get("skills", []),
            "strengths": analysis.get("strengths", []),
            "weaknesses": analysis.get("weaknesses", []),
        }

        services["storage"].append_record(record)

        webhook_payload = {
            "timestamp": record["timestamp"],
            "name": record["name"],
            "score": record["score"],
            "recommendation": record["recommendation"],
            "strengths": ", ".join(record["strengths"]),
            "weaknesses": ", ".join(record["weaknesses"]),
        }

        # send webhook in background
        background_tasks.add_task(services["webhook"].send, webhook_payload)

        return {"ok": True, "record": record}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/candidates")
def list_candidates(limit: int = 20) -> dict:
    services = getattr(app.state, "services", None) or _init_services()
    if services.get("error"):
        raise HTTPException(status_code=500, detail=services.get("error"))
    try:
        recent = services["storage"].load_recent(limit=limit)
        return {"ok": True, "candidates": recent}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/migrate")
def migrate_csv(csv_path: str = Form("storage/candidates.csv")) -> dict:
    services = getattr(app.state, "services", None) or _init_services()
    if services.get("error"):
        raise HTTPException(status_code=500, detail=services.get("error"))
    try:
        inserted = services["storage"].migrate_from_csv(csv_path, backup=True)
        return {"ok": True, "migrated": inserted}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, log_level="info")
