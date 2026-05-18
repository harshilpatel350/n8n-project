from __future__ import annotations

import re

import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config.logging_config import get_logger
from utils.constants import SCORING_WEIGHTS

logger = get_logger(__name__)


class ScoringService:
    def __init__(self, weights: dict | None = None) -> None:
        self.weights = weights or SCORING_WEIGHTS

    def score_candidate(
        self, candidate: dict, job_description: str, resume_text: str
    ) -> dict:
        keyword_score = self._keyword_overlap_score(candidate.get("skills", []), job_description)
        semantic_score = self._semantic_similarity_score(resume_text, job_description)
        experience_score = self._experience_score(
            candidate.get("total_years_experience", 0), job_description
        )

        final_score = (
            keyword_score * self.weights["keyword"]
            + semantic_score * self.weights["semantic"]
            + experience_score * self.weights["experience"]
        )

        return {
            "final_score": round(float(np.clip(final_score, 0, 100)), 1),
            "keyword_score": round(keyword_score, 1),
            "semantic_score": round(semantic_score, 1),
            "experience_score": round(experience_score, 1),
        }

    def _keyword_overlap_score(self, skills: list[str], job_description: str) -> float:
        if not skills:
            return 0.0

        jd_lower = job_description.lower()
        skill_set = {skill.lower() for skill in skills if skill.strip()}
        matches = sum(1 for skill in skill_set if skill and skill in jd_lower)
        return (matches / max(len(skill_set), 1)) * 100

    def _semantic_similarity_score(self, resume_text: str, job_description: str) -> float:
        if len(resume_text.strip()) < 50 or len(job_description.strip()) < 50:
            return 0.0
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf = vectorizer.fit_transform([resume_text, job_description])
            similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            return float(np.clip(similarity * 100, 0, 100))
        except Exception:
            logger.warning("Semantic similarity failed, defaulting to 0")
            return 0.0

    def _experience_score(self, candidate_years: float, job_description: str) -> float:
        required_years = self._extract_required_years(job_description)
        try:
            years = float(candidate_years)
        except (TypeError, ValueError):
            years = 0.0

        if required_years <= 0:
            return 70.0 if years > 0 else 50.0

        ratio = min(years / required_years, 1.2)
        return min(ratio * 100, 100.0)

    def _extract_required_years(self, job_description: str) -> float:
        matches = re.findall(r"(\d+)(?:\+)?\s*(?:years|yrs)", job_description.lower())
        if not matches:
            return 0.0
        return max(float(match) for match in matches)
