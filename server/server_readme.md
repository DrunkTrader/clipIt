# ClipIt - Server Documentation

A FastAPI-based backend service for downloading and clipping Twitter/X videos.

## 🚀 Overview

This server handles video processing requests from the client, downloads Twitter/X videos using yt-dlp, and optionally clips them to specified time ranges. Videos are temporarily stored and served to clients for download.

## 📋 Prerequisites

- Python 3.8+
- FFmpeg installed on your system
- yt-dlp (installed via requirements)

## 🛠️ Installation

1. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

2. **Install dependencies:**
```bash
pip install -r requirement.txt
```

3. **Configure environment variables:**
Create a `.env` file in the server directory:
```env
BASE_URL=http://localhost:9000
```

4. **Run the server:**
```bash
python main.py
```

Server will start at `http://localhost:9000`

## 📁 Project Structure

```
server/
├── main.py                  # FastAPI application & main endpoints
├── download_command.py      # yt-dlp video download logic
├── clip_from_download.py    # FFmpeg video clipping logic
├── valid_timeframe.py       # Time validation utilities
├── id_generator.py          # Unique ID generation for videos
├── requirement.txt          # Python dependencies
├── .env                     # Environment configuration
├── downloads/               # Temporary video storage
└── __pycache__/            # Python cache files
```

## 🔧 Component Details

### **1. main.py**
**Role:** Core FastAPI application and API endpoints

**Key Functions:**
- `download_full_video()` - Downloads entire Twitter/X video
- `download_clip_video()` - Downloads and clips video to specified timeframe
- `get_video()` - Serves the downloaded video file
- `health_check()` - Server health status endpoint

**API Endpoints:**
```
POST /download-full-video
  Body: { "url": "twitter_video_url" }
  Response: { "message": "success", "video_url": "http://..." }

POST /download-clip-video
  Body: { "url": "twitter_video_url", "start_time": "00:10", "end_time": "00:30" }
  Response: { "message": "success", "video_url": "http://..." }

GET /video/{filename}
  Response: Video file (video/mp4)

GET /health
  Response: { "status": "healthy" }
```

**CORS Configuration:**
- Allows all origins (`*`)
- Supports credentials
- Permits all methods and headers

---

### **2. download_command.py**
**Role:** Handles video downloading from Twitter/X using yt-dlp

**Key Functions:**
- `download_video(url: str) -> str`
  - Takes Twitter/X video URL
  - Generates unique filename using `id_generator`
  - Downloads video using yt-dlp with best quality settings
  - Returns the downloaded filename

**yt-dlp Configuration:**
```python
{
    'format': 'bestvideo+bestaudio/best',  # Best quality
    'outtmpl': 'downloads/%(title)s.%(ext)s',  # Output path
    'merge_output_format': 'mp4',  # Force MP4 format
    'quiet': True  # Suppress output
}
```

**Error Handling:**
- Catches download errors
- Prints error messages
- Returns `None` on failure

---

### **3. clip_from_download.py**
**Role:** Clips downloaded videos using FFmpeg

**Key Functions:**
- `clip_video(input_file: str, start_time: str, end_time: str) -> str`
  - Takes input video file path
  - Accepts start and end times (format: HH:MM:SS or MM:SS)
  - Creates clipped version using FFmpeg
  - Returns output filename

**FFmpeg Command:**
```bash
ffmpeg -i input.mp4 -ss START_TIME -to END_TIME -c copy output_clipped.mp4
```

**Features:**
- Fast processing using stream copy (`-c copy`)
- No re-encoding required
- Preserves original video quality
- Automatically names output with "_clipped" suffix

**Error Handling:**
- Validates FFmpeg installation
- Catches subprocess errors
- Returns `None` on failure

---

### **4. valid_timeframe.py**
**Role:** Validates and processes time inputs

**Key Functions:**
- `valid_time(start_time: str, end_time: str) -> tuple`
  - Validates time format (HH:MM:SS or MM:SS)
  - Ensures start time is before end time
  - Returns `(None, None)` if both times are empty (for full video)
  - Returns validated times or raises exceptions

**Validation Rules:**
1. Both times must be provided together or both empty
2. Start time must be less than end time
3. Accepts formats: `HH:MM:SS`, `MM:SS`, or `SS`

**Error Handling:**
- Raises `ValueError` for invalid formats
- Raises `ValueError` if start >= end
- Raises `ValueError` if only one time is provided

---

### **5. id_generator.py**
**Role:** Generates unique identifiers for video files

**Key Functions:**
- `generate_unique_id(length: int = 8) -> str`
  - Creates random alphanumeric strings
  - Default length: 8 characters
  - Uses uppercase, lowercase, and digits
  - Ensures unique filenames to prevent collisions

**Usage:**
```python
unique_id = generate_unique_id()  # Example: "aB3xY9kL"
filename = f"video_{unique_id}.mp4"
```

---

## 🔄 Request Flow

### **Full Video Download:**
```
1. Client sends POST to /download-full-video with URL
2. main.py receives request
3. download_command.py downloads video using yt-dlp
4. Video saved to downloads/ folder
5. Server returns video URL
6. Client requests GET /video/{filename}
7. main.py serves the video file
```

### **Clipped Video Download:**
```
1. Client sends POST to /download-clip-video with URL and times
2. valid_timeframe.py validates start/end times
3. download_command.py downloads full video
4. clip_from_download.py clips video using FFmpeg
5. Original video deleted, clipped version saved
6. Server returns video URL
7. Client requests GET /video/{filename}
8. main.py serves the clipped video file
```

### **Optional Clipping Logic:**
```python
if start_time and end_time:
    # Both times provided → clip the video
    clip_video(downloaded_file, start_time, end_time)
else:
    # No times provided → return full video
    return full_video_url
```

---

## 🗂️ File Management

**Downloads Folder:**
- Location: `server/downloads/`
- Purpose: Temporary storage for videos
- Cleanup: Manual (consider adding auto-cleanup cron job)

**Naming Convention:**
```
Original: video_aB3xY9kL.mp4
Clipped:  video_aB3xY9kL_clipped.mp4
```

---

## 🔒 Security Considerations

**Current Implementation:**
- ⚠️ CORS allows all origins (development only)
- ⚠️ No authentication/authorization
- ⚠️ No rate limiting
- ⚠️ Temporary files not auto-cleaned

**Production Recommendations:**
1. Implement proper CORS with specific origins
2. Add authentication (API keys/JWT)
3. Implement rate limiting (e.g., 10 requests/minute)
4. Add file cleanup scheduler
5. Validate video URLs before processing
6. Set maximum file size limits
7. Use secure file storage (S3/cloud storage)

---

## 🐛 Error Handling

**Common Errors:**

1. **Invalid Twitter URL:**
   - yt-dlp fails to download
   - Returns error message to client

2. **Invalid Time Format:**
   - valid_timeframe.py raises ValueError
   - Returns 400 Bad Request

3. **FFmpeg Not Installed:**
   - clip_from_download.py fails
   - Returns error message

4. **Video Not Found:**
   - GET /video/{filename} returns 404

---

## 📊 Dependencies

```txt
fastapi          # Web framework
uvicorn          # ASGI server
yt-dlp           # Video downloader
python-dotenv    # Environment variables
python-multipart # Form data handling
```

**External Tools:**
- FFmpeg (system-level installation required)

---

## 🧪 Testing

**Health Check:**
```bash
curl http://localhost:9000/health
```

**Download Full Video:**
```bash
curl -X POST http://localhost:9000/download-full-video \
  -H "Content-Type: application/json" \
  -d '{"url": "https://twitter.com/user/status/123"}'
```

**Download Clip:**
```bash
curl -X POST http://localhost:9000/download-clip-video \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://twitter.com/user/status/123",
    "start_time": "00:10",
    "end_time": "00:30"
  }'
```

---

## 🚀 Deployment

**Production Considerations:**

1. **Use Gunicorn or similar:**
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

2. **Set up reverse proxy (Nginx):**
```nginx
location / {
    proxy_pass http://localhost:9000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

3. **Environment Variables:**
```env
BASE_URL=https://api.yourdomain.com
MAX_FILE_SIZE=100MB
CLEANUP_INTERVAL=3600
```

4. **Monitoring:**
- Add logging (Python logging module)
- Monitor disk space in downloads/
- Track API request metrics

---

## 📝 Future Enhancements

- [ ] Add video format conversion options
- [ ] Implement batch download support
- [ ] Add video thumbnail generation
- [ ] Support multiple video platforms
- [ ] Add progress tracking for large downloads
- [ ] Implement websocket for real-time updates
- [ ] Add video metadata extraction
- [ ] Create admin dashboard for file management

---

## 🤝 Contributing

When contributing to the server:

1. Follow PEP 8 style guidelines
2. Add type hints to all functions
3. Write docstrings for new functions
4. Test with various Twitter URL formats
5. Handle edge cases gracefully

---

## 📞 Support

For issues or questions:
- Check FFmpeg installation: `ffmpeg -version`
- Check yt-dlp installation: `yt-dlp --version`
- Review server logs for detailed errors
- Ensure Twitter URLs are publicly accessible

---

**Happy Clipping! ✂️🎬**