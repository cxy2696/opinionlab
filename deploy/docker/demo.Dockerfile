# Single-container public demo: no PostgreSQL, Redis or MinIO required.
# The demo API runs the real engine in-process; auth, runs and reports that
# need the database are unavailable in this image by design.
FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OPINIONLAB_ENV=production

RUN groupadd --system app && useradd --system --gid app --home /app app \
    && mkdir -p /app && chown -R app:app /app
WORKDIR /app

COPY pyproject.toml ./
COPY packages ./packages
COPY apps ./apps
RUN pip install --no-cache-dir -e packages/hnle -e apps/api

COPY scenarios ./scenarios
COPY docs ./docs

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
