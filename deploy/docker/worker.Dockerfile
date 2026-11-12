FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c AS runtime

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
