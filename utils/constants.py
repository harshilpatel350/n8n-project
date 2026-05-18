APP_NAME = "AI Resume Screening and Candidate Intelligence Platform"

MAX_UPLOAD_MB = 8
ALLOWED_MIME_TYPES = ("application/pdf",)
ALLOWED_EXTENSIONS = (".pdf",)

OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TIMEOUT_SEC = 45
OPENAI_MAX_RETRIES = 3
OPENAI_MAX_TEXT_CHARS = 15000

SCORING_WEIGHTS = {
    "keyword": 0.35,
    "semantic": 0.45,
    "experience": 0.20,
}

MIN_JD_LENGTH = 80
MIN_RESUME_TEXT_LENGTH = 200

UPLOAD_DIR_NAME = "uploads"
LOG_DIR_NAME = "logs"
STORAGE_DIR_NAME = "storage"
CANDIDATES_FILE_NAME = "candidates.csv"
CANDIDATES_DB_NAME = "candidates.db"

CANDIDATE_FIELDS = [
    "timestamp",
    "name",
    "score",
    "recommendation",
    "skills",
    "strengths",
    "weaknesses",
]
