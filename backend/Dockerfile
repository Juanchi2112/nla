# Backend service — orchestrator + in-process judge.
# Build context: repo root.
FROM python:3.11-slim

WORKDIR /app

# uv: fast resolver + single source of truth from pyproject.toml.
RUN pip install --no-cache-dir uv

# Copy lockfile + project metadata first so dep install caches independently
# of source code churn.
COPY pyproject.toml uv.lock /app/

# Install only core deps. --no-dev skips pytest/ruff. --no-install-project
# skips installing the local package (we just need its deps; the source
# code goes in via COPY below and is found via CWD on sys.path).
RUN uv sync --frozen --no-dev --no-install-project

# App code last — changes more often than deps.
COPY backend/ /app/backend/

# Scenario artifacts — read at boot in ORCHESTRATOR_GPU=scenario mode.
COPY demo_data/ /app/demo_data/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8001

EXPOSE 8001

CMD ["sh", "-c", "uv run uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8001}"]
