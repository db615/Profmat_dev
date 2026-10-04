FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/auth
COPY pyproject.toml ./
COPY app ./app
RUN pip install . && useradd --uid 10001 --create-home auth
COPY alembic.ini ./
COPY migrations ./migrations

USER auth
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS test
USER root
RUN pip install '.[dev]'
COPY tests ./tests
ENV PYTEST_ADDOPTS="-p no:cacheprovider" \
    RUFF_NO_CACHE=true
USER auth
CMD ["pytest", "-q"]

FROM base AS runtime