#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if [ -f backend/requirements.txt ]; then
  pip install -r backend/requirements.txt
fi

exec uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload