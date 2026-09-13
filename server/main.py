import os
import time
import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# imports from local files
from include.valid_timeframe import validate_timeframe, validate_timeframe_against_video
from include.id_generator import IDGenerator
from include.download_command import download_tweet_video
from include.clip_from_download import clip_video_ffmpeg

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Initialize rate limiter with Redis (fallback to memory if Redis unavailable)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    import redis

    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
    logger.info("Connected to Redis for rate limiting")
    limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL, default_limits=["10 per minute"])
except Exception as e:
    logger.warning(f"Redis not available, using in-memory rate limiting: {str(e)}")
    limiter = Limiter(key_func=get_remote_address, default_limits=["5 per minute"])

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize ID generator
id_generator = IDGenerator()

# Enable CORS (Cross-Origin Resource Sharing) to allow the Next.js frontend to communicate with this backend
# Restrict to specific origins in production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    allow_credentials=True,
)

# Use environment variable for download directory with sensible default
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/app/downloads")
DOWNLOAD_TTL_SECONDS = int(os.getenv("DOWNLOAD_TTL_SECONDS", "3600"))  # Default 1 hour

# Ensure download directory exists
Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

# Mount the static directory so files can be accessed via URL
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")


@app.get("/")
async def root():
    return {
        "status": "Video Clipper Server is running",
        "endpoints": "Available endpoints: /clip (POST), /downloads/ (GET)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/clip")
@limiter.limit("5 per minute")
async def clip_video(request: Request):
    body = await request.json()
    tweet_url = body.get("tweet_url", "").replace("x.com", "twitter.com")
    start_raw = body.get("start")
    end_raw = body.get("end")

    if not tweet_url:
        raise HTTPException(status_code=400, detail="Missing Clip Link")

    # Validate timeframe and set up filenames/URLs
    try:
        start_sec, end_sec = validate_timeframe(start_raw, end_raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Timeframe validation error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid timeframe parameters")

    # Set up filenames and URLs (base -> localhost for testing, request_id -> unique identifier, video_filename -> downloaded video, clipped_filename -> final clipped video)
    request_id = id_generator.generate_id()
    video_filename = os.path.join(DOWNLOAD_DIR, f"{request_id}.mp4")
    clipped_filename = None

    try:
        # Step1 : Download the tweet video using yt-dlp
        logger.info(f"Downloading video from: {tweet_url}")
        await download_tweet_video(tweet_url, video_filename)
        logger.info(f"Video downloaded successfully: {video_filename}")

        # Step 2 : Validate clip timeframe against actual video duration (if clipping requested)
        if start_sec is not None and end_sec is not None:
            logger.info("Validating clip timeframe against video duration")
            await validate_timeframe_against_video(start_sec, end_sec, video_filename)

        # Step 3 : Clip the video using ffmpeg (only if start/end provided and validated)
        if start_sec is not None and end_sec is not None:
            clipped_filename = os.path.join(DOWNLOAD_DIR, f"clipped_{request_id}.mp4")
            logger.info(f"Clipping video from {start_sec}s to {end_sec}s")
            await clip_video_ffmpeg(
                video_filename, clipped_filename, start_sec, end_sec
            )
            logger.info(f"Video clipped successfully: {clipped_filename}")
            target_filename = f"clipped_{request_id}.mp4"

        else:
            # Return full video if no clipping times provided
            logger.info("Returning full video (no clipping requested)")
            target_filename = f"{request_id}.mp4"

        # Step 4 : Return the download link
        base_url = os.getenv("BASE_URL", str(request.base_url).rstrip("/"))
        download_link = f"{base_url}/downloads/{target_filename}"

        return JSONResponse(content={"download_link": download_link})

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to process video. Please try again."
        )
    finally:
        # Schedule cleanup of temporary files
        if video_filename and os.path.exists(video_filename):
            asyncio.create_task(cleanup_file(video_filename, DOWNLOAD_TTL_SECONDS))
        if clipped_filename and os.path.exists(clipped_filename):
            asyncio.create_task(cleanup_file(clipped_filename, DOWNLOAD_TTL_SECONDS))


async def cleanup_file(filepath: str, ttl_seconds: int):
    """Clean up file after TTL seconds."""
    await asyncio.sleep(ttl_seconds)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Cleaned up file: {filepath}")
    except Exception as e:
        logger.error(f"Failed to cleanup file {filepath}: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
