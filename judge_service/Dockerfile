# Judge service — small CPU-only container.
# Build context: repo root (so we can COPY both judge_service/ and nla_judge/).
FROM python:3.11-slim

WORKDIR /app

# Install deps first so the dependency layer caches across code changes.
COPY judge_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the shared package and the service code.
COPY nla_judge/ /app/nla_judge/
COPY judge_service/ /app/judge_service/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

# Railway sets $PORT at runtime; use a shell-form CMD so it expands.
CMD ["sh", "-c", "uvicorn judge_service.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
