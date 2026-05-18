from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlsplit

from dotenv import load_dotenv

from utils.constants import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    APP_NAME,
    MAX_UPLOAD_MB,
    OPENAI_MODEL,
)

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str
    openai_api_key: str
    n8n_webhook_url: str
    n8n_test_webhook_url: str | None
    allowed_mime_types: tuple[str, ...]
    allowed_extensions: tuple[str, ...]
    max_upload_mb: int
    openai_model: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL", "").strip()
    n8n_test_webhook_url = os.getenv("N8N_TEST_WEBHOOK_URL", "").strip() or None

    missing = []
    if not openai_api_key:
        missing.append("OPENAI_API_KEY")
    if not n8n_webhook_url:
        missing.append("N8N_WEBHOOK_URL")
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    def _is_valid_url(u: str) -> bool:
        try:
            parts = urlsplit(u)
            return parts.scheme in ("http", "https") and bool(parts.netloc)
        except Exception:
            return False

    if not _is_valid_url(n8n_webhook_url):
        raise RuntimeError("N8N_WEBHOOK_URL is not a valid http(s) URL: %s" % n8n_webhook_url)

    if n8n_test_webhook_url and not _is_valid_url(n8n_test_webhook_url):
        raise RuntimeError("N8N_TEST_WEBHOOK_URL is not a valid http(s) URL: %s" % n8n_test_webhook_url)

    return Settings(
        app_name=APP_NAME,
        openai_api_key=openai_api_key,
        n8n_webhook_url=n8n_webhook_url,
        n8n_test_webhook_url=n8n_test_webhook_url,
        allowed_mime_types=ALLOWED_MIME_TYPES,
        allowed_extensions=ALLOWED_EXTENSIONS,
        max_upload_mb=MAX_UPLOAD_MB,
        openai_model=OPENAI_MODEL,
    )


def clear_settings_cache() -> None:
    """Clear the cached settings (useful in tests)."""
    get_settings.cache_clear()
