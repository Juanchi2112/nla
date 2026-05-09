#!/usr/bin/env bash
# GPU box setup: venv + deps + Qwen NLA actor weights.
# Run from anywhere — script cd's to repo root via $(dirname).
set -euo pipefail

# Path: gpu/scripts/setup.sh — go up two levels to repo root.
cd "$(dirname "$0")/../.."

MODEL_REPO="${MODEL_REPO:-kitft/nla-qwen2.5-7b-L20-av}"
MODEL_DIR="${MODEL_DIR:-./actor_hf}"

# 1. Install uv if missing.
if ! command -v uv >/dev/null 2>&1; then
    echo "[setup] Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# 2. Triton JIT-compiles a C helper at first GPU op and needs Python.h.
#    On Ubuntu/Debian containers (vast.ai), python3.11-dev is usually missing.
PY_INCLUDE_DIR="$(python3.11 -c 'import sysconfig; print(sysconfig.get_path("include"))' 2>/dev/null || echo "")"
if [ -n "$PY_INCLUDE_DIR" ] && [ ! -f "$PY_INCLUDE_DIR/Python.h" ]; then
    echo "[setup] Python.h not found at $PY_INCLUDE_DIR (Triton needs it)."
    if command -v apt-get >/dev/null 2>&1 && [ "$(id -u)" = "0" ]; then
        echo "[setup] Installing python3.11-dev via apt-get"
        apt-get update -qq
        apt-get install -y python3.11-dev
    else
        echo "[setup] WARNING: cannot auto-install. Run: sudo apt-get install python3.11-dev" >&2
    fi
fi

# 3. Create venv + install all GPU deps from pyproject.toml.
uv venv --python 3.11
uv sync --extra gpu

# 4. Download the NLA actor weights (~15 GB the first time).
if [ ! -d "$MODEL_DIR" ]; then
    echo "[setup] Downloading $MODEL_REPO -> $MODEL_DIR (~15 GB)"
    uv run hf download "$MODEL_REPO" --local-dir "$MODEL_DIR"
else
    echo "[setup] $MODEL_DIR already exists, skipping download"
fi

echo
echo "[setup] Done."
echo "  Activate venv:   source .venv/bin/activate"
echo "  Launch SGLang:   bash gpu/scripts/launch_sglang.sh   (terminal 1)"
echo "  Smoke test:      bash gpu/scripts/smoke_test.sh      (terminal 2)"
