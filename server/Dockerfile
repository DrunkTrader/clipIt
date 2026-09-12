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

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
