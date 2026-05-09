#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL_REPO="${MODEL_REPO:-kitft/nla-qwen2.5-7b-L20-av}"
MODEL_DIR="${MODEL_DIR:-./actor_hf}"
VENV_DIR="${VENV_DIR:-.venv}"

cd "$(dirname "$0")/.."

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: $PYTHON_BIN not found. Install Python 3.11 (recommended) or set PYTHON_BIN env var." >&2
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "[setup] Creating venv at $VENV_DIR with $PYTHON_BIN"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[setup] Upgrading pip"
pip install --upgrade pip

echo "[setup] Installing Python deps from requirements.txt"
pip install -r requirements.txt

if [ ! -d "$MODEL_DIR" ]; then
    echo "[setup] Downloading $MODEL_REPO -> $MODEL_DIR (~15 GB, takes a few minutes)"
    huggingface-cli download "$MODEL_REPO" --local-dir "$MODEL_DIR"
else
    echo "[setup] $MODEL_DIR already exists, skipping download"
fi

echo
echo "[setup] Done."
echo "  Activate venv:   source $VENV_DIR/bin/activate"
echo "  Launch SGLang:   bash scripts/launch_sglang.sh   (terminal 1)"
echo "  Smoke test:      bash scripts/smoke_test.sh      (terminal 2)"
