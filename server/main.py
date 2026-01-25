import os
import time
from fastapi import FastAPI, Request, HTTPException 
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

#imports from local files
from valid_timeframe import validate_timeframe
from id_generator import IDGenerator
from download_command import download_tweet_video
from clip_from_download import clip_video_ffmpeg

# Initialize FastAPI app
app = FastAPI()

# Initialize ID generator
id_generator = IDGenerator()

#Enable CORS (Cross-Origin Resource Sharing) to allow the Next.js frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

#serve the download director for file access
DOWNLOAD_DIR = "'/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

#Mount theh static directory so files can be accessed via URL
app.mount("/downloads", StaticFiles(directory = DOWNLOAD_DIR), name="downloads")

@app.get("/")
async def root():
    return {
        "status" : "Video Clipper Server is running",
        "endpoints": "Available endpoints: /clip (POST), /downloads/ (GET)",
        "timestamp" : time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    }

@app.post("/clip")
async def clip_video(request: Request):
    body = await request.json()
    tweet_url = body.get("tweet_url", "").replace("x.com", "twitter.com")
    start_raw = body.get("start")
    end_raw = body.get("end")

    if not tweet_url:
        raise HTTPException(status_code=400, detail="Missing Clip Link")
    
    # Validate timeframe and set up filenames/URLs
    start_sec, end_sec = validate_timeframe(start_raw, end_raw)

    # Set up filenames and URLs (base -> localhost for testing, request_id -> unique identifier, video_filename -> downloaded video, clipped_filename -> final clipped video)
    request_id = id_generator.generate_id()
    video_filename = os.path.join(DOWNLOAD_DIR, f"{request_id}.mp4")
    
    try:
        # Step1 : Download the tweet video using yt-dlp
        download_tweet_video(tweet_url, video_filename)
    
        # Step 2 : Clip the video using ffmpeg (only if start/end provided)
        if start_sec is not None and end_sec is not None:
            clipped_filename = os.path.join(DOWNLOAD_DIR, f"clipped_{request_id}.mp4")
            clip_video_ffmpeg(video_filename, clipped_filename, start_sec, end_sec)
            target_filename = f"clipped_{request_id}.mp4"
    
        else:
            # Return full video if no clipping times provided
            target_filename = f"{request_id}.mp4"
        # Step 3 : Return the download link
        base_url = os.getenv("BASE_URL", str(request.base_url).rsplit("/"))
        download_url = f"{base_url}/downloads/{target_filename}"

        return JSONResponse(content={"download_url": download_url})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=port)