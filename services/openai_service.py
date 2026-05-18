from __future__ import annotations

import time
from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)

from config.logging_config import get_logger
from utils.constants import OPENAI_MAX_RETRIES, OPENAI_TIMEOUT_SEC
from utils.helpers import safe_json_parse, truncate_text
from utils.prompts import (
    build_candidate_analysis_messages,
    build_resume_extraction_messages,
)

logger = get_logger(__name__)


class OpenAIService:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_sec: int = OPENAI_TIMEOUT_SEC,
        max_retries: int = OPENAI_MAX_RETRIES,
    ) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries

    def extract_resume_structured(self, resume_text: str) -> dict:
        messages = build_resume_extraction_messages(truncate_text(resume_text))
        return self._chat_json(messages, max_tokens=800)

    def generate_candidate_analysis(
        self, candidate: dict, job_description: str, scoring: dict
    ) -> dict:
        messages = build_candidate_analysis_messages(candidate, job_description, scoring)
        return self._chat_json(messages, max_tokens=900)

    def _chat_json(self, messages: list[dict], max_tokens: int) -> dict:
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    timeout=self.timeout_sec,
                )
                content = response.choices[0].message.content or "{}"
                data = safe_json_parse(content)
                if not isinstance(data, dict):
                    raise ValueError("OpenAI response is not a JSON object")
                return data
            except BadRequestError as exc:
                logger.exception("OpenAI request failed")
                raise exc
            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as exc:
                last_error = exc
                logger.warning(
                    "OpenAI retry %s/%s due to %s",
                    attempt,
                    self.max_retries,
                    type(exc).__name__,
                )
                time.sleep(2**attempt)
            except ValueError as exc:
                last_error = exc
                logger.warning("OpenAI JSON parse failed, retrying")
                time.sleep(2**attempt)

        raise RuntimeError("OpenAI request failed") from last_error
