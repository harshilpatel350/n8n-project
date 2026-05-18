from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.constants import OPENAI_MAX_TEXT_CHARS


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    return cleaned or "upload.pdf"


def truncate_text(text: str, max_chars: int = OPENAI_MAX_TEXT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def safe_json_parse(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise ValueError("Failed to parse JSON response")


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[,;/\n]+", value)
        return [part.strip() for part in parts if part.strip()]
    return [str(value).strip()]
