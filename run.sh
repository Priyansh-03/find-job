#!/usr/bin/env bash
set -euo pipefail

# Run the dashboard locally with zero manual setup steps.
# - creates `.venv/` if missing
# - installs `requirements.txt` if needed
# - starts `dashboard_app.py`

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PY_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PY_BIN="python"
else
  echo "Error: python3 or python not found in PATH." >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  "$PY_BIN" -m venv .venv
fi

".venv/bin/activate"

python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt >/dev/null

exec .venv/bin/python dashboard_app.py

