Param()

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path .venv)) {
  python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (Test-Path backend\requirements.txt) {
  pip install -r backend\requirements.txt
}

uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload