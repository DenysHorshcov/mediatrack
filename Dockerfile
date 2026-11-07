# MediaTrack: one image with the API and the built frontend.
# Build: docker build -t mediatrack .
# Run:   docker run --rm -p 8000:8000 --env-file .env mediatrack

# --- Stage 1: frontend build ---
FROM node:22-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Same origin as the API, so the default "/api" base URL is used.
RUN npm run build

# --- Stage 2: backend runtime ---
FROM python:3.14-slim AS runtime

# Pinned to backend/pyproject.toml [tool.uv] required-version.
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/backend/.venv \
    FRONTEND_DIST_DIR=/app/frontend/dist \
    PATH="/app/backend/.venv/bin:$PATH"

WORKDIR /app/backend

# Dependencies first so code changes reuse this layer.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/ ./
COPY --from=frontend /src/frontend/dist /app/frontend/dist

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app

ENV PORT=8000
EXPOSE 8000

# Migrations run at start: Render's Pre-Deploy Command is paid-only.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
