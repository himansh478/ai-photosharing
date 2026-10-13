# ─────────────────────────────────────────────
# STAGE 1: Builder — Install all dependencies
# ─────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /build

# Compiler for the packages that have no prebuilt wheel (insightface)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment to avoid shared library location issues
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip

# Everything comes from PyPI; prefer-binary uses prebuilt wheels wherever they exist
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt


# ─────────────────────────────────────────────
# STAGE 2: Final — Lightweight runtime image
# ─────────────────────────────────────────────
FROM python:3.10-slim

WORKDIR /app

# Sirf runtime libs — no cmake, no build-essential
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libstdc++6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# The app runs as an unprivileged user; uid 1000 is also what Hugging Face Spaces expects
RUN useradd --create-home --uid 1000 appuser
ENV HOME=/home/appuser

# Builder se compiled virtual environment copy karo
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# App source code copy karo (.dockerignore se unnecessary files skip hoti hain)
COPY . .

# The source stays read-only; only these two directories are writable
RUN mkdir -p /app/models_cache /app/storage/temp && \
    chown -R appuser:appuser /app/models_cache /app/storage

USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV ENV=production
ENV PYTHONPATH=/app
ENV INSIGHTFACE_HOME=/app/models_cache

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

CMD ["waitress-serve", "--port=7860", "--threads=8", "backend.app:app"]
