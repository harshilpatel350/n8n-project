from __future__ import annotations

from config.logging_config import get_logger
from utils.constants import MIN_RESUME_TEXT_LENGTH
from utils.helpers import normalize_list
from utils.parser import extract_text_from_pdf

logger = get_logger(__name__)


class ResumeService:
    def __init__(self, openai_service) -> None:
        self.openai_service = openai_service

    def extract_candidate(self, file_bytes: bytes, filename: str) -> dict:
        resume_text = extract_text_from_pdf(file_bytes)
        if len(resume_text) < MIN_RESUME_TEXT_LENGTH:
            raise ValueError("Resume text is too short for reliable extraction.")

        logger.info("Extracting candidate data from %s", filename)
        raw_candidate = self.openai_service.extract_resume_structured(resume_text)
        if not isinstance(raw_candidate, dict):
            logger.error("OpenAI returned unexpected resume structure: %s", type(raw_candidate))
            raise ValueError("Invalid resume structure returned from extraction service")

        candidate = self._normalize_candidate(raw_candidate)

        return {"candidate": candidate, "resume_text": resume_text}

    def _normalize_candidate(self, raw_candidate: dict) -> dict:
        if not isinstance(raw_candidate, dict):
            raise ValueError("raw_candidate must be a dict")

        name = str(raw_candidate.get("name") or "").strip() or "Unknown"
        # cap name length
        if len(name) > 200:
            name = name[:200]

        # normalize skills to list of short strings
        skills = normalize_list(raw_candidate.get("skills"))
        cleaned_skills = []
        for s in skills:
            s_str = str(s).strip()
            if not s_str:
                continue
            if len(s_str) > 100:
                s_str = s_str[:100]
            cleaned_skills.append(s_str)
        skills = cleaned_skills
        education = normalize_list(raw_candidate.get("education"))
        experience = self._normalize_experience(raw_candidate.get("experience"))
        certifications = normalize_list(raw_candidate.get("certifications"))

        total_years = raw_candidate.get("total_years_experience", 0)
        try:
            total_years_value = float(total_years) if total_years is not None else 0.0
        except (TypeError, ValueError):
            total_years_value = 0.0

        return {
            "name": name,
            "skills": skills,
            "education": education,
            "experience": experience,
            "certifications": certifications,
            "total_years_experience": round(total_years_value, 1),
        }

    def _normalize_experience(self, value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            normalized: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    parts = [
                        str(item.get("title", "")).strip(),
                        str(item.get("company", "")).strip(),
                        str(item.get("years", "")).strip(),
                        str(item.get("summary", "")).strip(),
                    ]
                    joined = " | ".join([part for part in parts if part])
                    if joined:
                        normalized.append(joined)
                else:
                    text = str(item).strip()
                    if text:
                        normalized.append(text)
            return normalized
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []
