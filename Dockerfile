# 115-Media — Single Container Deployment
# Build: docker build -t 115-media .
# Run:   docker run -d -p 8000:8000 -p 8095:8095 -v 115-data:/app/data 115-media

# ── Stage 1: Build frontend ───────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: Final runtime image ──────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies: Redis + Supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ .

# Copy frontend build artifacts
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Data volume mount point
VOLUME ["/app/data"]

# Expose ports:
#   8000 — FastAPI (API + frontend SPA)
#   8095 — p115tiny302 (115 streaming redirect)
EXPOSE 8000 8095

# Start all services via supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
