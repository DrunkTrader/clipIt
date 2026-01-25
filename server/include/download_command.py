import subprocess
from fastapi import HTTPException


def download_tweet_video(tweet_url: str, output_path: str) -> None:
    """
    Download a video from a Twitter/X post using yt-dlp.

    Raises HTTPException(500) if the subprocess fails.
    """
    command = [
        "yt-dlp",
        "-o",
        output_path,
        "-f",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        tweet_url,
    ]

    try:
        subprocess.run(command, check=True)
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error downloading video: {str(e)}")
