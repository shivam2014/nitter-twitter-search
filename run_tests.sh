#!/bin/bash
# Run the test suite. Uses .venv when present, otherwise the active python.
set -euo pipefail
cd "$(dirname "$0")"

if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
else
    PY=$(command -v python3)
fi

export PYTHONPATH="src:${PYTHONPATH:-}"
exec "$PY" -m pytest tests/ "${@:-}"
