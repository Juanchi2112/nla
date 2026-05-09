# Orchestrator service — small CPU-only container.
# Build context: repo root.
FROM python:3.11-slim

WORKDIR /app

COPY orchestrator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY orchestrator/ /app/orchestrator/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8001

EXPOSE 8001

CMD ["sh", "-c", "uvicorn orchestrator.app:app --host 0.0.0.0 --port ${PORT:-8001}"]
