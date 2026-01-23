import os
import time
from fastapi import FastAPI, Request, HTTPException 
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Change these from relative to absolute imports
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
os.makedirs("downloads", exist_ok=True)
app.mount("/downloads", StaticFiles(directory = "downloads"), name="downloads")

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
    base_url = os.getenv("BASE_URL", "http://localhost:9000")
    request_id = id_generator.generate_id()
    video_filename = f"downloads/{request_id}.mp4"
    
    # Step1 : Download the tweet video using yt-dlp
    download_tweet_video(tweet_url, video_filename)
    
    # Step 2 : Clip the video using ffmpeg (only if start/end provided)
    if start_sec is not None and end_sec is not None:
        clipped_filename = f"downloads/clipped_{request_id}.mp4"
        clip_video_ffmpeg(video_filename, clipped_filename, start_sec, end_sec)
        download_link = f"{base_url}/downloads/clipped_{request_id}.mp4"
    
    else:
        # Return full video if no clipping times provided
        download_link = f"{base_url}/downloads/{request_id}.mp4"
    
    # Step 3 : Return the download link
    return JSONResponse(content={"download_link": download_link})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=port)