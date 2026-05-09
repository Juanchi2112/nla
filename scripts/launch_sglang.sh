#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MODEL_DIR="${MODEL_DIR:-./actor_hf}"
PORT="${PORT:-30000}"
MEM_FRAC="${MEM_FRAC:-0.85}"
VENV_DIR="${VENV_DIR:-.venv}"

if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
fi

# --disable-radix-cache is REQUIRED. Radix cache keys on token IDs;
# input_embeds requests have none, so different embed sequences alias to the
# same cache entry -> silent garbage. See README.md.
exec python -m sglang.launch_server \
    --model-path "$MODEL_DIR" \
    --port "$PORT" \
    --disable-radix-cache \
    --mem-fraction-static "$MEM_FRAC" \
    --trust-remote-code
