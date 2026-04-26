# ─────────────────────────────────────────────
# STAGE 1: Builder — Install all dependencies
# ─────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /build

# System dependencies for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# insightface prebuilt wheel (Optimization for speed)
RUN pip install --no-cache-dir \
    "https://github.com/jimacoff/insightface-wheels/releases/download/v0.7.3/insightface-0.7.3-cp310-cp310-linux_x86_64.whl" \
    || pip install --no-cache-dir --prefer-binary insightface==0.7.3

# Backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# ─────────────────────────────────────────────
# STAGE 2: Final — Lightweight runtime image
# ─────────────────────────────────────────────
FROM python:3.10-slim

WORKDIR /app

# Runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libstdc++6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code
COPY . .

# Writable directories for Azure
RUN mkdir -p /app/models_cache /app/storage/temp && \
    chmod -R 777 /app/models_cache /app/storage/temp

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV ENV=production
ENV PYTHONPATH=/app/backend:/app
ENV INSIGHTFACE_HOME=/app/models_cache

# Azure App Service uses port 80/8080 by default. 
# We'll set WEBSITES_PORT=7860 in Azure config later.
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

# Start the server using Waitress
CMD ["waitress-serve", "--port=7860", "--threads=4", "backend.app:app"]
