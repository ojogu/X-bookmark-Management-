# FROM python:3.11-slim

# # set working directory inside container
# WORKDIR /app

# # copy only dependencies first (for caching optimization)
# COPY pyproject.toml uv.lock ./

# RUN uv sync --locked

# # copy ONLY your source code (exclude env, .git, etc. via .dockerignore)
# COPY . .

# # set default command (point to entry file inside src)
# CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port","8000"]

# ---------- Stage 1: Build ----------
FROM python:3.12-slim AS builder
# Copy uv binaries from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
# Copy only dependency files first (for layer caching)
COPY pyproject.toml uv.lock ./
# Export locked dependencies to requirements.txt (respects uv.lock)
RUN uv export --format requirements-txt --no-hashes -o requirements.txt
# Install dependencies into system Python (no venv)
RUN uv pip install --system -r requirements.txt
#  copy ONLY your source code (exclude env, .git, etc. via .dockerignore)
COPY . .
# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim
WORKDIR /app
# Copy installed dependencies from build step (system-level: libs and binaries)
COPY --from=builder /usr/local /usr/local
# Copy app source from the build step filesystem into runtime filesystem
COPY --from=builder /app/src ./src
EXPOSE 5000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]

