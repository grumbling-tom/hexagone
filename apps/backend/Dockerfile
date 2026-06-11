# Production ASGI image for the Hexagone backend — runs uvicorn directly, with no
# AWS Lambda runtime or adapter. The Lambda packaging lives separately in
# Dockerfile.lambda; this image is what the k8s Deployment (infra/k8s) runs.
#
# source: https://docs.astral.sh/uv/guides/integration/docker/
FROM ghcr.io/astral-sh/uv:0.9.9 AS uv

FROM python:3.14-slim

# uv binary — used only at build time to materialise the venv.
COPY --from=uv /uv /usr/local/bin/uv

# - compile bytecode for faster cold starts
# - copy (don't hardlink) out of the uv cache, which is on a separate mount
# - run from the project venv, and put /app on sys.path so `uvicorn src.app...`
#   resolves (the console script doesn't add cwd the way `python -m` would)
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app

# Dependencies first, so this layer caches unless pyproject.toml / uv.lock change.
# --no-dev drops dev deps; --no-install-workspace installs deps only (app code is
# copied below and imported from /app via PYTHONPATH).
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-workspace

# App code + Alembic config. alembic.ini is required by the migration init
# container in infra/k8s/base/app/backend.yaml (`alembic upgrade head`).
COPY ./src ./src
COPY ./alembic.ini ./

EXPOSE 8000

# Default to the server; the migration init container overrides this with alembic.
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
