from __future__ import annotations

import os
import sys
from pathlib import Path

# ensure repo root on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import get_settings, clear_settings_cache


def test_missing_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("N8N_WEBHOOK_URL", "http://127.0.0.1:5678/webhook/candidate-intake")
    clear_settings_cache()
    try:
        try:
            get_settings()
            raise AssertionError("get_settings should have raised for missing OPENAI_API_KEY")
        except RuntimeError:
            pass
    finally:
        clear_settings_cache()


def test_invalid_webhook_url(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("N8N_WEBHOOK_URL", "not-a-url")
    clear_settings_cache()
    try:
        try:
            get_settings()
            raise AssertionError("get_settings should have raised for invalid N8N_WEBHOOK_URL")
        except RuntimeError:
            pass
    finally:
        clear_settings_cache()
