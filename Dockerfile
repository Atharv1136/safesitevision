# ==============================================================================
# SafeSite Vision - All-In-One Unified Application Dockerfile
# ==============================================================================

# Stage 1: Build the React + Vite Frontend
FROM node:20-alpine AS web-builder
WORKDIR /app/web
COPY services/web/package*.json ./
RUN npm ci
COPY services/web/ ./
RUN npm run build

# Stage 2: Python Backend & Ingestion Engine
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp"

# System dependencies (ffmpeg for RTSP streams, libgl for OpenCV, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source directories
COPY services/ ./services/
COPY configs/ ./configs/
COPY models/ ./models/
COPY storage/ ./storage/
COPY classes.py .
COPY yolo11n.pt .

# Copy built frontend assets from Stage 1 into the backend's static directory
COPY --from=web-builder /app/web/dist ./services/web/dist

# Ensure persistent evidence and report storage directories exist
RUN mkdir -p storage/evidence storage/reports

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
