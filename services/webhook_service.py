from __future__ import annotations

import random
import time
from typing import Optional

import requests

from config.logging_config import get_logger

logger = get_logger(__name__)


class WebhookService:
    def __init__(
        self,
        webhook_url: str,
        timeout_sec: int = 10,
        fallback_webhook_url: Optional[str] = None,
        max_retries_per_url: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout_sec = timeout_sec
        self.fallback_webhook_url = fallback_webhook_url
        self.max_retries_per_url = max_retries_per_url
        self.backoff_factor = backoff_factor

    def _post(self, url: str, payload: dict) -> requests.Response:
        return requests.post(url, json=payload, timeout=self.timeout_sec)

    def _is_retryable_status(self, status: int) -> bool:
        # Retry on 5xx and 429
        return status == 429 or 500 <= status < 600

    def send(self, payload: dict) -> bool:
        urls = [self.webhook_url]
        if self.fallback_webhook_url and self.fallback_webhook_url != self.webhook_url:
            urls.append(self.fallback_webhook_url)

        for url_index, url in enumerate(urls, start=1):
            for attempt in range(1, self.max_retries_per_url + 1):
                try:
                    logger.debug(
                        "Webhook attempt: url_index=%s attempt=%s url=%s",
                        url_index,
                        attempt,
                        url,
                    )
                    response = self._post(url, payload)
                    status = getattr(response, "status_code", None)
                    text = getattr(response, "text", "")

                    if status is None:
                        logger.error("Invalid response object from webhook POST to %s", url)
                        # treat as retryable
                        retry = True
                    else:
                        retry = self._is_retryable_status(status)

                    if status is not None and status < 400:
                        logger.info("Webhook delivered with status %s via %s", status, url)
                        return True

                    logger.warning(
                        "Webhook call to %s returned status=%s attempt=%s text=%s",
                        url,
                        status,
                        attempt,
                        text,
                    )

                    if attempt < self.max_retries_per_url and retry:
                        backoff = self.backoff_factor * (2 ** (attempt - 1))
                        # add jitter up to 50%
                        jitter = backoff * random.uniform(0, 0.5)
                        sleep_for = backoff + jitter
                        logger.debug("Retrying in %.2fs (backoff=%s jitter=%s)", sleep_for, backoff, jitter)
                        time.sleep(sleep_for)
                        continue
                    # if not retryable or no more retries, break to try next url
                    break
                except requests.RequestException as exc:
                    logger.warning(
                        "Webhook request exception for %s on attempt %s: %s",
                        url,
                        attempt,
                        exc,
                    )
                    if attempt < self.max_retries_per_url:
                        backoff = self.backoff_factor * (2 ** (attempt - 1))
                        jitter = backoff * random.uniform(0, 0.5)
                        sleep_for = backoff + jitter
                        logger.debug("Exception retrying in %.2fs", sleep_for)
                        time.sleep(sleep_for)
                        continue
                    break

            logger.info("Webhook URL exhausted or failed, moving to next if available: %s", url)

        logger.error("All webhook endpoints failed after retries: %s", urls)
        return False
