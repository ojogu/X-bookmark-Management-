# ---------- Stage 1: Build ----------
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv export --format requirements-txt --no-hashes -o requirements.txt
RUN uv pip install --system -r requirements.txt
COPY . .

# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim
WORKDIR /app

# Copy installed packages from builder (this is what you're missing)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app source
COPY --from=builder /app/src ./src
COPY --from=builder /app/frontend.py ./

EXPOSE 5000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000"]
