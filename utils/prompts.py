from __future__ import annotations

import json

RESUME_EXTRACTION_SYSTEM = (
    "You are an expert resume parser. Extract structured data with high accuracy."
)

ANALYSIS_SYSTEM = (
    "You are a senior recruiter and hiring manager. Provide concise, evidence-based"
    " assessments using the provided resume data and job description."
)


def build_resume_extraction_messages(resume_text: str) -> list[dict]:
    user_prompt = f"""
Extract the following fields from the resume text and return ONLY valid JSON.

Required JSON schema:
{{
  "name": "",
  "skills": [],
  "education": [],
  "experience": [],
  "certifications": [],
  "total_years_experience": 0
}}

Rules:
- If a field is missing, use an empty list or 0.
- Do not include extra keys.

Resume text:
{resume_text}
""".strip()

    return [
        {"role": "system", "content": RESUME_EXTRACTION_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]


def build_candidate_analysis_messages(
    candidate: dict, job_description: str, scoring: dict
) -> list[dict]:
    candidate_json = json.dumps(candidate, indent=2)
    scoring_json = json.dumps(scoring, indent=2)

    user_prompt = f"""
You are given a candidate profile, a job description, and a scoring breakdown.
Return ONLY valid JSON that matches the schema below.

Required JSON schema:
{{
  "professional_summary": "",
  "strengths": [],
  "weaknesses": [],
  "interview_questions": [],
  "experience_analysis": "",
  "hiring_recommendation": ""
}}

Guidelines:
- Keep responses concise and professional.
- Use evidence from the resume data and job description.

Candidate profile:
{candidate_json}

Job description:
{job_description}

Scoring breakdown:
{scoring_json}
""".strip()

    return [
        {"role": "system", "content": ANALYSIS_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
