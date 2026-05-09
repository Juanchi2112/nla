#!/usr/bin/env bash
set -euo pipefail

# Path: gpu/scripts/smoke_test.sh — go up two levels to repo root.
cd "$(dirname "$0")/../.."

MODEL_DIR="${MODEL_DIR:-./actor_hf}"
SGLANG_URL="${SGLANG_URL:-http://localhost:30000}"
VENV_DIR="${VENV_DIR:-.venv}"

if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
fi

# Random unit vector. If output is English -> injection works.
# If output is CJK / Chinese -> something failed (see README.md Debugging section).
exec python gpu/nla_inference.py "$MODEL_DIR" --sglang-url "$SGLANG_URL"
