FROM python:3.9-slim

# Install system dependencies including ffmpeg and ffprobe
RUN apt-get update \
    && apt-get install -y ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirement.txt .

# Install Python dependencies with pinned versions
RUN pip install --no-cache-dir -r requirement.txt

# Copy application code
COPY . .

# Create downloads directory
RUN mkdir -p /app/downloads

# Environment variables
ENV PORT=8080
ENV DOWNLOAD_DIR=/app/downloads
ENV DOWNLOAD_TTL_SECONDS=3600
ENV ALLOWED_ORIGINS=http://localhost:3000
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Use gunicorn with uvicorn workers for production
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "--timeout", "120", "--keep-alive", "5"]
