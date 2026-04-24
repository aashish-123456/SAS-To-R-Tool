# ── Stage 1: Build the React frontend ────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python + R runtime ──────────────────────────────────────────────
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install R base + pre-compiled dplyr/tidyr from Debian repos (no source compile,
# keeps build fast and the image lean).
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    r-cran-dplyr \
    r-cran-tidyr \
    && rm -rf /var/lib/apt/lists/*

# Verify R is available
RUN Rscript --version

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application code
COPY backend/ /app/backend/

# Copy built frontend assets
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

EXPOSE 8000
CMD ["python", "backend/main.py"]
