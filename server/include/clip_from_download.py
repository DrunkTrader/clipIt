import subprocess
import asyncio
from fastapi import HTTPException


async def clip_video_ffmpeg(
    input_path: str, output_path: str, start_sec: float, end_sec: float
) -> None:
    """
    Clip a segment from an existing video file using ffmpeg with stream copy.

    Uses -ss/-to with -c copy for fast clipping (keyframe-accurate).
    Raises HTTPException(500) if the subprocess fails.
    """
    command = [
        "ffmpeg",
        "-i",
        input_path,
        "-ss",
        str(start_sec),
        "-to",
        str(end_sec),
        "-c",
        "copy",
        output_path,
    ]

    try:
        # Use asyncio.create_subprocess_exec for non-blocking execution
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown ffmpeg error"
            raise subprocess.CalledProcessError(
                process.returncode, command, stdout, stderr
            )

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        raise HTTPException(
            status_code=500, detail=f"Error clipping video: {error_msg}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clipping video: {str(e)}")
