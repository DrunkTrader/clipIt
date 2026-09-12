# Twitter/X Video Clipper Server

A FastAPI backend service for downloading and clipping videos from Twitter/X posts.

## Features

- Download videos from Twitter/X URLs
- Clip videos to specific timeframes
- Automatic file cleanup with configurable TTL
- Async non-blocking operations for better performance
- Video duration validation before clipping
- Comprehensive logging

## Requirements

- Python 3.9+
- ffmpeg (includes ffprobe)
- yt-dlp

## Installation

### Using Docker (Recommended)

```bash
docker build -t twitter-clipper .
docker run -p 8080:8080 --env-file .env twitter-clipper
```

### Manual Installation

1. Install system dependencies:
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y ffmpeg

# macOS
brew install ffmpeg
```

2. Install Python dependencies:
```bash
pip install -r requirement.txt
```

3. Copy environment file and configure:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Run the server:
```bash
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Configuration

All configuration is done via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8080 | Server port |
| `DOWNLOAD_DIR` | /app/downloads | Directory for temporary files |
| `DOWNLOAD_TTL_SECONDS` | 3600 | File cleanup delay (seconds) |
| `ALLOWED_ORIGINS` | http://localhost:3000 | CORS allowed origins (comma-separated) |
| `BASE_URL` | auto-detected | Base URL for download links |
| `MAX_CLIP_SECONDS` | 600 | Maximum clip duration |
| `MAX_TIMECODE_SECONDS` | 86400 | Maximum timecode value |

## API Endpoints

### GET `/`
Health check endpoint.

### POST `/clip`
Download and optionally clip a Twitter/X video.

**Request Body:**
```json
{
  "tweet_url": "https://twitter.com/user/status/123456",
  "start": 10.5,  // optional, seconds
  "end": 25.0     // optional, seconds
}
```

**Response:**
```json
{
  "download_link": "http://localhost:8080/downloads/clipped_1234567890.mp4"
}
```

### GET `/downloads/{filename}`
Access downloaded/clipped video files.

## Error Handling

The server returns appropriate HTTP status codes:
- `400 Bad Request`: Invalid parameters or timeframe exceeds video duration
- `500 Internal Server Error`: Download or processing failures

All errors are logged but generic messages are returned to clients to avoid leaking internal details.

## File Cleanup

Files are automatically deleted after `DOWNLOAD_TTL_SECONDS` (default: 1 hour). This prevents disk space exhaustion.

## Security Notes

- Configure `ALLOWED_ORIGINS` for production (don't use `*`)
- Use HTTPS in production
- Consider adding rate limiting for high-traffic scenarios
- Monitor disk usage for the download directory
