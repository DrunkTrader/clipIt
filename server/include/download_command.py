import subprocess
import asyncio
from fastapi import HTTPException


async def download_tweet_video(tweet_url: str, output_path: str) -> None:
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
        # Use asyncio.create_subprocess_exec for non-blocking execution
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, command, stdout, stderr
            )

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        raise HTTPException(
            status_code=500, detail=f"Error downloading video: {error_msg}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error downloading video: {str(e)}"
        )
