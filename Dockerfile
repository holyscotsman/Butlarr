# =============================================================================
# Butlarr Dockerfile
# Multi-stage build with embedded AI support
# Version is read from VERSION file at runtime
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build frontend
# -----------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copy frontend files
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm

# Labels
LABEL maintainer="Jason"
LABEL description="AI-Powered Plex Library Manager"

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_DIR=/app \
    DATA_DIR=/app/data \
    PORT=8765

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For llama-cpp-python (embedded AI)
    build-essential \
    cmake \
    # For git auto-updates
    git \
    # For FFprobe (media analysis)
    ffmpeg \
    # For gosu (user switching)
    gosu \
    # For healthchecks and downloads
    curl \
    wget \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copy backend code
COPY backend/ ./backend/

# Copy VERSION file for runtime version detection
COPY VERSION ./VERSION

# Copy built frontend from stage 1
COPY --from=frontend-builder /build/dist ./frontend/dist

# Copy entrypoint and scripts
COPY entrypoint.sh /entrypoint.sh
COPY scripts/ ./scripts/
RUN chmod +x /entrypoint.sh

# Create directories
RUN mkdir -p /app/data /app/data/models /app/data/logs /app/data/reports

# Expose port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8765/api/health || exit 1

# Volumes
VOLUME ["/app/data", "/media"]

ENTRYPOINT ["/entrypoint.sh"]
