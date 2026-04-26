# ─────────────────────────────────────────────
# STAGE 1: Builder — Install all dependencies
# ─────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /build

# Only runtime-needed system libs for compilation
# cmake/git nahi chahiye kyunki hum prebuilt wheels use kar rahe hain
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment to avoid shared library location issues
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip once
RUN pip install --no-cache-dir --upgrade pip

# ── Key Optimization: insightface prebuilt wheel ──
# Source se compile karne pe 10-15 min lagte hain
# Yeh prebuilt wheel seedha install hota hai — 30 seconds mein
RUN pip install --no-cache-dir \
    "https://github.com/jimacoff/insightface-wheels/releases/download/v0.7.3/insightface-0.7.3-cp310-cp310-linux_x86_64.whl" \
    || pip install --no-cache-dir --prefer-binary insightface==0.7.3

# ── Baaki sab dependencies — prefer-binary se prebuilt wheels milte hain ──
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefer-binary \
    -r requirements.txt


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

# Builder se compiled virtual environment copy karo
COPY --from=builder /opt/venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# App source code copy karo (.dockerignore se unnecessary files skip hoti hain)
COPY . .

# Writable directories banana
RUN mkdir -p /app/models_cache /app/storage/temp && \
    chmod -R 777 /app/models_cache /app/storage/temp

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV ENV=production
ENV PYTHONPATH=/app/backend:/app
ENV INSIGHTFACE_HOME=/app/models_cache

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

CMD ["waitress-serve", "--port=7860", "backend.app:app"]
