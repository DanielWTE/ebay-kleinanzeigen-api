FROM python:3.14-slim-bookworm AS build
WORKDIR /app

# Install uv (pinned) for reproducible install from uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

# Install Python dependencies before copying source (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-editable

# Make the venv the default Python environment for subsequent layers
ENV PATH="/app/.venv/bin:$PATH"


FROM python:3.14-slim-bookworm
WORKDIR /app

# Copy only the resolved venv (no uv, no build tooling)
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install Playwright headless-only Chromium + system deps (single layer, apt cache cleaned)
RUN playwright install --with-deps chromium --only-shell \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
