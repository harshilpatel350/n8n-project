from __future__ import annotations

import sys
from pathlib import Path

# ensure repo root is on sys.path for tests run from tox/pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.webhook_service import WebhookService


class DummyResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


def test_webhook_fallback(monkeypatch):
    calls = []

    primary = "https://live.example/webhook"
    fallback = "https://test.example/webhook"

    service = WebhookService(primary, fallback_webhook_url=fallback, max_retries_per_url=2, backoff_factor=0.01)

    # stateful counter for calls per url
    counter = {primary: 0, fallback: 0}

    def fake_post(url, payload):
        calls.append(url)
        counter[url] += 1
        # primary fails with 500 twice, then would keep failing
        if url == primary:
            return DummyResponse(500, "server error")
        # fallback succeeds
        return DummyResponse(200, "ok")

    # patch the instance method
    monkeypatch.setattr(service, "_post", fake_post)

    result = service.send({"hello": "world"})

    assert result is True
    # ensure primary was tried (retries) and fallback was called
    assert primary in calls
    assert fallback in calls
