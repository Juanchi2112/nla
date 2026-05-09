#!/usr/bin/env bash
set -euo pipefail

# Path: gpu/scripts/launch_sglang.sh — go up two levels to repo root.
cd "$(dirname "$0")/../.."

MODEL_DIR="${MODEL_DIR:-./actor_hf}"
PORT="${PORT:-30000}"
# MEM_FRAC: fraction of GPU mem SGLang pre-allocates.
#   0.85 = standalone (only AV on GPU). Default — works on 4060 Ti 16GB,
#          A10 24GB, RTX 4090, A100 standalone.
#   0.30 = override when cohabiting with Qwen base + AR on a single A100 80GB
#          (steering loop). Set via `MEM_FRAC=0.30 bash gpu/scripts/launch_sglang.sh`.
#   0.20 = override for A100 40GB cohabitation (AR must be on CPU).
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
