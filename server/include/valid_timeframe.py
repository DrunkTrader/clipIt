import os
import math
import subprocess
import asyncio
from fastapi import HTTPException


async def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file using ffprobe.
    Returns duration in seconds as a float.
    """
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise ValueError(f"ffprobe failed: {stderr.decode()}")
        
        return float(stdout.decode().strip())
    except Exception as e:
        raise ValueError(f"Could not determine video duration: {str(e)}")


def validate_timeframe(start_raw, end_raw):
    """
    Validate start/end values and return (start_sec, end_sec) as floats or (None, None) if not provided.
    Rules:
    - optional (if both None, returns None, None for full video)
    - numeric and finite
    - start >= 0, end > start
    - (end - start) <= MAX_CLIP_SECONDS (default 600)
    - start, end <= MAX_TIMECODE_SECONDS (default 86400)
    Raises HTTPException(400) on invalid input.
    """

    # If both are None, return None to indicate full video download
    if start_raw is None and end_raw is None:
        return None, None
    
    # If only one is provided, raise an error
    if start_raw is None or end_raw is None:
        raise HTTPException(status_code=400, detail="Both start and end must be provided, or leave both empty for full video")

    try:
        start_sec = float(start_raw)
        end_sec = float(end_raw)

    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="start and end must be numeric seconds")

    if not math.isfinite(start_sec) or not math.isfinite(end_sec):
        raise HTTPException(status_code=400, detail="start and end must be finite numbers")

    if start_sec < 0 or end_sec <= 0:
        raise HTTPException(status_code=400, detail="start must be >= 0 and end must be > 0")

    if end_sec <= start_sec:
        raise HTTPException(status_code=400, detail="end must be greater than start")

    max_clip_seconds = int(os.getenv("MAX_CLIP_SECONDS", "600"))
    max_timecode_seconds = int(os.getenv("MAX_TIMECODE_SECONDS", "86400"))

    if (end_sec - start_sec) > max_clip_seconds:
        raise HTTPException(
            status_code=400,
            detail=f"Clip length exceeds maximum of {max_clip_seconds} seconds",
        )

    if start_sec > max_timecode_seconds or end_sec > max_timecode_seconds:
        raise HTTPException(
            status_code=400,
            detail=f"timecodes too large; must be <= {max_timecode_seconds} seconds",
        )

    return start_sec, end_sec


async def validate_timeframe_against_video(start_sec: float, end_sec: float, video_path: str) -> None:
    """
    Validate that the requested clip timeframe is within the actual video duration.
    Raises HTTPException(400) if the timeframe exceeds video duration.
    """
    try:
        duration = await get_video_duration(video_path)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Add small buffer (1 second) for floating point precision
    if end_sec > duration + 1:
        raise HTTPException(
            status_code=400,
            detail=f"End time ({end_sec}s) exceeds video duration ({duration:.2f}s)",
        )
    
    if start_sec > duration:
        raise HTTPException(
            status_code=400,
            detail=f"Start time ({start_sec}s) exceeds video duration ({duration:.2f}s)",
        )
