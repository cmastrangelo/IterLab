FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY iterlab ./iterlab
RUN pip install --no-cache-dir .

COPY alembic.ini ./
COPY alembic ./alembic

# Non-root runtime user.
RUN useradd --system --create-home --uid 1001 iterlab \
    && mkdir -p /var/lib/iterlab/artifacts \
    && chown -R iterlab:iterlab /var/lib/iterlab
USER iterlab

EXPOSE 8000

# entrypoint runs the schema/table bootstrap (when enabled) then serves.
CMD ["uvicorn", "iterlab.main:app", "--host", "0.0.0.0", "--port", "8000"]
