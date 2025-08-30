FROM node:lts-alpine AS build_ui

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

COPY webui/pnpm-lock.yaml webui/pnpm-workspace.yaml webui/package.json ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

# Build
COPY webui .
RUN pnpm run build

# Build and run with uv
FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app
COPY --from=build_ui /app/dist webui/dist

# Copy only metadata first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies without installing the project yet
RUN uv sync --no-dev --frozen --compile-bytecode --no-install-project

# Now copy the rest of the source
COPY heimdall heimdall

# Install the project (editable style not needed in container)
RUN uv sync --no-dev --frozen --compile-bytecode

EXPOSE 8088

CMD ["uv", "run", "uvicorn", "heimdall.api:app", "--host", "0.0.0.0", "--port", "8088"]
