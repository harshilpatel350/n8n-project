from __future__ import annotations

from pathlib import Path
import threading

import streamlit as st

from config.logging_config import configure_logging, get_logger
from config.settings import get_settings
from services.candidate_service import CandidateStorage
from services.openai_service import OpenAIService
from services.resume_service import ResumeService
from services.scoring_service import ScoringService
from services.webhook_service import WebhookService
from utils.constants import (
    APP_NAME,
    CANDIDATES_FILE_NAME,
    LOG_DIR_NAME,
    STORAGE_DIR_NAME,
    UPLOAD_DIR_NAME,
)
from utils.helpers import ensure_dir, now_iso, safe_filename
from utils.validators import validate_job_description, validate_upload

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / UPLOAD_DIR_NAME
LOG_DIR = BASE_DIR / LOG_DIR_NAME
STORAGE_DIR = BASE_DIR / STORAGE_DIR_NAME
CANDIDATES_PATH = STORAGE_DIR / CANDIDATES_FILE_NAME
CANDIDATES_DB_PATH = STORAGE_DIR / "candidates.db"

_MIGRATION_LOCK = threading.Lock()
_MIGRATION_STATE = {
    "status": "idle",  # idle | running | success | error | skipped
    "message": "",
}


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">AI Resume Screening</div>
            <div class="hero-subtitle">Candidate Intelligence Platform</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    st.sidebar.markdown("## Control Center")
    st.sidebar.write("Upload resumes and assess job fit with structured AI insights.")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Output")
    st.sidebar.write("- Structured candidate profile")
    st.sidebar.write("- Match score with breakdown")
    st.sidebar.write("- Strengths, weaknesses, questions")
    st.sidebar.write("- n8n webhook delivery")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Data Handling")
    st.sidebar.write("Results persist to a local CSV for audit and analytics.")


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&family=Space+Grotesk:wght@500;700&display=swap');
        .main {
            background:
              radial-gradient(circle at top left, rgba(17, 24, 39, 0.08), transparent 45%),
              radial-gradient(circle at 80% 20%, rgba(14, 116, 144, 0.12), transparent 40%),
              linear-gradient(135deg, #f7f5f0 0%, #e9f0f7 100%);
        }
        .block-container { padding-top: 2rem; }
        html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
        .hero {
            background: #111827;
            color: #f9fafb;
            padding: 1.5rem 2rem;
            border-radius: 16px;
            margin-bottom: 1.5rem;
            animation: rise 0.6s ease-out;
        }
        .hero-title {
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            font-family: 'Space Grotesk', sans-serif;
        }
        .hero-subtitle {
            font-size: 1rem;
            opacity: 0.85;
        }
        .metric-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            border: 1px solid #e5e7eb;
            margin-bottom: 1rem;
            animation: fade-in 0.5s ease-out;
        }
        @keyframes rise {
            from { transform: translateY(8px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        @keyframes fade-in {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _start_migration_in_background(logger) -> None:
    with _MIGRATION_LOCK:
        if _MIGRATION_STATE["status"] in {"running", "success", "error", "skipped"}:
            return

        if not CANDIDATES_PATH.exists():
            _MIGRATION_STATE["status"] = "skipped"
            _MIGRATION_STATE["message"] = "No legacy CSV found."
            return

        _MIGRATION_STATE["status"] = "running"
        _MIGRATION_STATE["message"] = "Migrating legacy CSV data into SQLite..."

    def _worker() -> None:
        try:
            storage_for_migration = CandidateStorage(str(CANDIDATES_DB_PATH))
            migrated = storage_for_migration.migrate_from_csv(str(CANDIDATES_PATH), backup=True)
            msg = f"Migration complete. {migrated} record(s) moved to SQLite."
            with _MIGRATION_LOCK:
                _MIGRATION_STATE["status"] = "success"
                _MIGRATION_STATE["message"] = msg
            logger.info(msg)
        except Exception as exc:
            with _MIGRATION_LOCK:
                _MIGRATION_STATE["status"] = "error"
                _MIGRATION_STATE["message"] = f"Migration failed: {exc}"
            logger.exception("Background migration failed")

    threading.Thread(target=_worker, daemon=True, name="candidate-csv-migration").start()


def render_migration_banner() -> None:
    with _MIGRATION_LOCK:
        status = _MIGRATION_STATE["status"]
        message = _MIGRATION_STATE["message"]

    if status == "running":
        st.info(message)
    elif status == "success":
        st.success(message)
    elif status == "error":
        st.error(message)


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    apply_styles()

    try:
        settings = get_settings()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    ensure_dir(str(UPLOAD_DIR))
    ensure_dir(str(LOG_DIR))
    ensure_dir(str(STORAGE_DIR))

    configure_logging(str(LOG_DIR))
    logger = get_logger(__name__)

    # Kick off one-time migration in the background so startup stays responsive.
    _start_migration_in_background(logger)

    openai_service = OpenAIService(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )
    resume_service = ResumeService(openai_service)
    scoring_service = ScoringService()
    storage = CandidateStorage(str(CANDIDATES_DB_PATH))
    webhook_service = WebhookService(
        settings.n8n_webhook_url,
        fallback_webhook_url=settings.n8n_test_webhook_url,
    )

    render_header()
    render_migration_banner()
    render_sidebar()

    left, right = st.columns([0.55, 0.45], gap="large")

    with left:
        st.subheader("1. Upload Resume")
        uploaded_file = st.file_uploader(
            "PDF resume only", type=["pdf"], accept_multiple_files=False
        )

        st.subheader("2. Job Description")
        job_description = st.text_area(
            "Paste the role details here",
            height=220,
            placeholder="Required skills, responsibilities, and experience.",
        )

        process = st.button("Process Candidate", type="primary", use_container_width=True)

    with right:
        st.subheader("Live Status")
        status_placeholder = st.empty()
        score_placeholder = st.empty()

    if process:
        errors = []
        errors.extend(
            validate_upload(
                uploaded_file,
                settings.allowed_extensions,
                settings.allowed_mime_types,
                settings.max_upload_mb,
            )
        )
        errors.extend(validate_job_description(job_description))

        if errors:
            for err in errors:
                st.error(err)
            st.stop()

        status = st.status("Processing candidate", expanded=True)
        status.update(label="Validating inputs", state="running")

        try:
            timestamp = now_iso().replace(":", "-")
            safe_name = safe_filename(uploaded_file.name)
            file_path = UPLOAD_DIR / f"{timestamp}_{safe_name}"
            file_bytes = uploaded_file.getvalue()
            file_path.write_bytes(file_bytes)
            logger.info("Uploaded resume saved: %s", file_path)

            status.update(label="Extracting resume content", state="running")
            extraction = resume_service.extract_candidate(file_bytes, uploaded_file.name)

            status.update(label="Scoring candidate against job description", state="running")
            scoring = scoring_service.score_candidate(
                extraction["candidate"],
                job_description,
                extraction["resume_text"],
            )

            status.update(label="Generating AI insights", state="running")
            analysis = openai_service.generate_candidate_analysis(
                extraction["candidate"],
                job_description,
                scoring,
            )

            final_score = scoring["final_score"]
            recommendation = analysis.get("hiring_recommendation", "Review manually")

            record = {
                "timestamp": now_iso(),
                "name": extraction["candidate"]["name"],
                "score": final_score,
                "recommendation": recommendation,
                "skills": extraction["candidate"]["skills"],
                "strengths": analysis.get("strengths", []),
                "weaknesses": analysis.get("weaknesses", []),
            }
            storage.append_record(record)

            webhook_payload = {
                "timestamp": record["timestamp"],
                "name": record["name"],
                "score": record["score"],
                "recommendation": record["recommendation"],
                "strengths": ", ".join(record["strengths"]),
                "weaknesses": ", ".join(record["weaknesses"]),
            }
            webhook_ok = webhook_service.send(webhook_payload)

            status.update(label="Completed", state="complete")
            status_placeholder.success("Candidate processed successfully.")

            if not webhook_ok:
                st.warning("Webhook delivery failed. Check logs for details.")

            with score_placeholder.container():
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric(label="Match Score", value=f"{final_score:.1f} / 100")
                st.progress(min(int(final_score), 100))
                st.caption(
                    f"Keyword: {scoring['keyword_score']:.1f} | "
                    f"Semantic: {scoring['semantic_score']:.1f} | "
                    f"Experience: {scoring['experience_score']:.1f}"
                )
                st.markdown("</div>", unsafe_allow_html=True)

            st.subheader("Candidate Snapshot")
            st.write(f"**Name:** {extraction['candidate']['name']}")
            st.write(
                f"**Total Experience:** {extraction['candidate']['total_years_experience']} years"
            )

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Skills**")
                st.write(extraction["candidate"]["skills"] or "Not detected")
            with col_b:
                st.markdown("**Certifications**")
                st.write(extraction["candidate"]["certifications"] or "Not detected")

            st.subheader("AI Assessment")
            st.expander("Professional Summary", expanded=True).write(
                analysis.get("professional_summary", "")
            )
            st.expander("Experience Analysis").write(
                analysis.get("experience_analysis", "")
            )
            st.expander("Strengths").write(analysis.get("strengths", []))
            st.expander("Weaknesses").write(analysis.get("weaknesses", []))
            st.expander("Interview Questions").write(
                analysis.get("interview_questions", [])
            )
            st.expander("Hiring Recommendation").write(recommendation)

            st.subheader("Experience and Education")
            st.write("**Experience**")
            st.write(extraction["candidate"]["experience"] or "Not detected")
            st.write("**Education**")
            st.write(extraction["candidate"]["education"] or "Not detected")

            st.subheader("Recent Candidates")
            recent = storage.load_recent(limit=15)
            st.dataframe(recent, use_container_width=True)
        except Exception as exc:
            logger.exception("Processing failed")
            status.update(label="Processing failed", state="error")
            st.error(f"Processing failed: {exc}")


if __name__ == "__main__":
    main()
