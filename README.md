# ClipIt

A full-stack application for downloading and clipping Twitter/X videos. Simply paste a tweet URL, download the video, and optionally create custom clips with precise timestamps.

## Features

- 📥 Download videos from Twitter/X posts
- ✂️ Clip downloaded videos with custom start/end times
- 🚀 Fast processing with async operations
- 🎨 Modern, responsive UI
- 📁 Organized file management

## Tech Stack

### Frontend (Client)
- **Next.js 14** - React framework with App Router for server-side rendering and optimized performance
- **React 18** - Component-based UI library for building interactive interfaces
- **TypeScript** - Type safety and better developer experience
- **Tailwind CSS** - Utility-first CSS framework for rapid UI development
- **Axios** - HTTP client for API communication with the backend

### Backend (Server)
- **FastAPI** - Modern Python web framework for building APIs with automatic OpenAPI documentation
- **Uvicorn** - Lightning-fast ASGI server for running async Python applications
- **yt-dlp** - Robust video downloading tool supporting Twitter/X and other platforms
- **FFmpeg** - Industry-standard tool for video processing and clipping
- **Python Virtual Environment** - Isolated Python environment for dependency management

## Project Structure

```
clip-it/
├── client/          # Next.js frontend application
│   ├── app/         # Next.js App Router pages
│   ├── components/  # React components (VideoClipperForm)
│   └── .next/       # Build artifacts (auto-generated)
├── server/          # FastAPI backend application
│   ├── main.py      # FastAPI server entry point
│   ├── downloads/   # Storage for downloaded videos
│   ├── venv/        # Python virtual environment (auto-generated)
│   └── __pycache__/ # Python bytecode cache
└── README.md        # This file
```

## Getting Started

### Prerequisites

- **Node.js** 18+ and npm/yarn
- **Python** 3.8+
- **FFmpeg** installed on your system
- **pip** (Python package manager)

### 1) Setup Server

1. Navigate to server directory:
   ```bash
   cd server
   ```

2. Create Python virtual environment:
   ```bash
   python3 -m venv venv
   ```

3. Activate virtual environment:
   ```bash
   # On Linux/macOS
   source venv/bin/activate
   
   # On Windows
   # venv\Scripts\activate
   ```

4. Install Python dependencies:
   ```bash
   pip install -r requirement.txt
   ```

5. Configure environment variables:
   ```bash
   cp .env.example .env
   ```

6. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

7. To deactivate virtual environment when done:
   ```bash
   deactivate
   ```

Server runs at `http://localhost:8000`  
API docs at `http://localhost:8000/docs`

See detailed instructions in [server/server_readme.md](server/server_readme.md)

### 2) Setup Client

1. Navigate to client directory:
   ```bash
   cd client
   ```

2. Install Node dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```

3. Configure environment variables:
   ```bash
   cp .env.local.example .env.local
   ```

4. Start the development server:
   ```bash
   npm run dev
   # or
   yarn dev
   ```

Client runs at `http://localhost:3000`

See detailed instructions in [client/README.md](client/README.md)

## How It Works

1. **User Input**: Paste a Twitter/X video URL in the web interface
2. **Download**: Server uses yt-dlp to fetch the video
3. **Storage**: Video is saved to `server/downloads/` with a unique ID
4. **Clipping** (Optional): Use FFmpeg to extract specific timeframes
5. **Delivery**: Processed videos are served back to the client

## Environment Variables

### Client
See [client/.env.local.example](client/.env.local.example) for required variables:
- `NEXT_PUBLIC_API_URL` - Backend API endpoint

### Server
See [server/.env.example](server/.env.example) for required variables:
- `DOWNLOADS_DIR` - Directory for storing videos
- Additional configuration options

## API Endpoints

- `POST /download` - Download video from URL
- `POST /clip` - Create clip from downloaded video
- `GET /videos/{id}` - Retrieve processed video

Full API documentation available at `/docs` when server is running.

## Development Notes

- Build artifacts in `client/.next/` are auto-generated - do not edit manually
- Downloaded videos are stored in `server/downloads/` - ensure sufficient disk space
- Python bytecode cache in `server/__pycache__/` can be safely deleted
- Virtual environment `server/venv/` should be added to `.gitignore`
- Always activate the virtual environment before running server commands