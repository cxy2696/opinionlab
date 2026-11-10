FROM python:3.12.5-slim-bookworm@sha256:5d9c2b2d1b7a3b0c6d5f4e3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd --system app && useradd --system --gid app --home /app app \
    && mkdir -p /app && chown -R app:app /app
WORKDIR /app
COPY pyproject.toml ./
COPY packages ./packages
COPY apps ./apps
RUN pip install --no-cache-dir -e packages/hnle -e apps/api
COPY alembic.ini ./
COPY migrations ./migrations
COPY scenarios ./scenarios
USER app
CMD ["celery", "-A", "app.celery_app.celery_app", "worker", \
     "-Q", "q_normal,q_batch,q_ingest", "--loglevel=INFO"]
