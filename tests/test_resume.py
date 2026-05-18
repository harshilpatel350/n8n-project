from __future__ import annotations

import sys
from pathlib import Path

# ensure repo root on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.resume_service import ResumeService


def test_normalize_candidate_handles_types():
    svc = ResumeService(openai_service=None)
    raw = {
        "name": None,
        "skills": "Python, SQL, leadership",
        "education": ["BS Computer Science"],
        "experience": [{"title": "Engineer", "company": "X", "years": "3"}, "Freelancer"],
        "certifications": None,
        "total_years_experience": "5.2",
    }

    normalized = svc._normalize_candidate(raw)

    assert isinstance(normalized, dict)
    assert normalized["name"] == "Unknown"
    assert isinstance(normalized["skills"], list)
    assert len(normalized["skills"]) >= 1
    assert normalized["total_years_experience"] == 5.2
