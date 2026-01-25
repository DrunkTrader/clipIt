import os
import math
from fastapi import HTTPException


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
