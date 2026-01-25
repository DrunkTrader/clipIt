import subprocess
from fastapi import HTTPException


def clip_video_ffmpeg(input_path: str, output_path: str, start_sec: float, end_sec: float) -> None:
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
        subprocess.run(command, check=True)
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error clipping video: {str(e)}")
