# Video Clipper Architecture Documentation

## Overview

This document describes the architecture and workflow of the Video Clipper project, a FastAPI-based backend service that downloads videos from Twitter/X posts and creates clipped segments based on user-specified timeframes.

## System Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        A[Next.js Frontend]
        B[API Consumer]
    end

    subgraph API["API Gateway Layer"]
        C[FastAPI Application]
        D[CORS Middleware]
        E[Rate Limiter - SlowAPI]
    end

    subgraph Core["Core Processing Layer"]
        F[Request Handler /clip]
        G[ID Generator]
        H[Timeframe Validator]
    end

    subgraph Services["External Services"]
        I[yt-dlp Service]
        J[FFmpeg/FFprobe]
        K[Redis Rate Limiter]
    end

    subgraph Storage["Storage Layer"]
        L[Downloads Directory]
        M[Static File Server]
    end

    A -->|POST /clip| C
    B -->|POST /clip| C
    C --> D
    C --> E
    E --> K
    C --> F
    F --> G
    F --> H
    F --> I
    F --> J
    I --> L
    J --> L
    L --> M
    M -->|GET /downloads/:file| A
```

## Component Architecture

```mermaid
classDiagram
    class FastAPI {
        +app: FastAPI
        +limiter: SlowAPILimiter
        +middleware: CORSMiddleware
    }

    class RequestHandler {
        +clip_video(request: Request)
        +cleanup_file(filepath, ttl)
    }

    class IDGenerator {
        -last_timestamp: int
        -counter: int
        -lock: Thread
        +generate_id() string
    }

    class TimeframeValidator {
        +validate_timeframe(start, end)
        +validate_timeframe_against_video(start, end, path)
        +get_video_duration(path)
    }

    class VideoDownloader {
        +download_tweet_video(url, output_path)
    }

    class VideoClipper {
        +clip_video_ffmpeg(input, output, start, end)
    }

    class RateLimiter {
        -redis_client: Redis
        +limit(rate: string)
    }

    FastAPI --> RequestHandler
    RequestHandler --> IDGenerator
    RequestHandler --> TimeframeValidator
    RequestHandler --> VideoDownloader
    RequestHandler --> VideoClipper
    FastAPI --> RateLimiter
```

## Sequential Workflow

### 1. Request Initiation

```mermaid
sequenceDiagram
    participant Client
    participant CORS
    participant RateLimiter
    participant Handler
    participant IDGen
    participant Validator
    participant Downloader
    participant Clipper
    participant Storage

    Client->>CORS: POST /clip<br/>{tweet_url, start, end}
    CORS->>RateLimiter: Check rate limit
    alt Rate limit exceeded
        RateLimiter-->>Client: 429 Too Many Requests
    else Within limit
        RateLimiter->>Handler: Process request
        Handler->>IDGen: Generate unique ID
        IDGen-->>Handler: request_id (timestamp+counter)

        Handler->>Validator: validate_timeframe(start, end)
        alt Invalid timeframe
            Validator-->>Handler: HTTPException(400)
            Handler-->>Client: 400 Bad Request
        else Valid timeframe
            Validator-->>Handler: (start_sec, end_sec)

            Handler->>Downloader: download_tweet_video(url, path)
            Downloader->>Downloader: Execute yt-dlp
            Downloader->>Storage: Save video.mp4
            Downloader-->>Handler: Success

            opt Clipping requested
                Handler->>Validator: validate_against_video(start, end, path)
                Validator->>Validator: ffprobe duration check
                alt Invalid timeframe
                    Validator-->>Handler: HTTPException(400)
                    Handler-->>Client: 400 Bad Request
                else Valid
                    Validator-->>Handler: OK
                    Handler->>Clipper: clip_video_ffmpeg(input, output, start, end)
                    Clipper->>Clipper: Execute ffmpeg -c copy
                    Clipper->>Storage: Save clipped_video.mp4
                    Clipper-->>Handler: Success
                end
            end

            Handler->>Handler: Generate download_link
            Handler-->>Client: 200 OK<br/>{download_link}

            Note over Handler,Storage: Schedule cleanup<br/>after TTL seconds
        end
    end
```

### 2. Detailed Step-by-Step Process

#### Step 1: Request Reception & Middleware Processing

**Components Involved:**
- FastAPI Application
- CORS Middleware
- SlowAPI Rate Limiter

**Process Flow:**
1. Client sends POST request to `/clip` endpoint with JSON body:
   ```json
   {
     "tweet_url": "https://x.com/user/status/123456",
     "start": 10.5,
     "end": 25.0
   }
   ```

2. **CORS Middleware** validates origin against `ALLOWED_ORIGINS` environment variable
   - Default: `http://localhost:3000`
   - Supports multiple origins via comma-separated list

3. **Rate Limiter** checks request count:
   - Primary: Redis backend (`REDIS_URL` env var)
   - Fallback: In-memory storage if Redis unavailable
   - Limit: 5 requests per minute per IP address
   - Returns `429 Too Many Requests` if exceeded

#### Step 2: Request Parsing & Validation

**Components Involved:**
- Request Handler (`clip_video`)
- Timeframe Validator (`valid_timeframe.py`)

**Process Flow:**
1. Extract and normalize request parameters:
   - Convert `x.com` URLs to `twitter.com` for yt-dlp compatibility
   - Parse `start` and `end` timestamps

2. **Timeframe Validation Rules:**
   - Both `start` and `end` must be provided together, or both omitted (full video)
   - Values must be finite numeric seconds
   - `start >= 0`, `end > start`
   - Clip duration `(end - start) <= MAX_CLIP_SECONDS` (default: 600s)
   - Absolute times `<= MAX_TIMECODE_SECONDS` (default: 86400s)

3. Environment variables control limits:
   - `MAX_CLIP_SECONDS`: Maximum clip duration
   - `MAX_TIMECODE_SECONDS`: Maximum absolute timestamp

#### Step 3: Unique ID Generation

**Components Involved:**
- ID Generator (`id_generator.py`)

**Algorithm:**
```python
ID Format: {timestamp}{counter:04d}
Example: 17040672000000

- Timestamp: Unix epoch seconds
- Counter: 4-digit zero-padded increment for same-second requests
- Thread-safe with locking mechanism
```

**Purpose:**
- Ensures unique filenames for concurrent requests
- Enables tracking and cleanup of temporary files

#### Step 4: Video Download

**Components Involved:**
- Video Downloader (`download_command.py`)
- yt-dlp external tool

**Process Flow:**
1. Construct yt-dlp command:
   ```bash
   yt-dlp -o {output_path} \
          -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4" \
          {tweet_url}
   ```

2. Execute asynchronously using `asyncio.create_subprocess_exec`
   - Non-blocking operation
   - Captures stdout/stderr for error reporting

3. Error Handling:
   - subprocess failures raise HTTPException(500)
   - Error messages propagated to client

4. Output: Video saved to `DOWNLOAD_DIR/{request_id}.mp4`

#### Step 5: Timeframe Validation Against Video Duration

**Components Involved:**
- Timeframe Validator (`valid_timeframe.py`)
- FFprobe external tool

**Process Flow:**
1. Query video duration using ffprobe:
   ```bash
   ffprobe -v error \
           -show_entries format=duration \
           -of default=noprint_wrappers=1:nokey=1 \
           {video_path}
   ```

2. Validate requested timeframe:
   - `end_sec <= duration + 1s` (1s buffer for floating-point precision)
   - `start_sec <= duration`

3. Only executed if clipping was requested (start/end provided)

#### Step 6: Video Clipping

**Components Involved:**
- Video Clipper (`clip_from_download.py`)
- FFmpeg external tool

**Process Flow:**
1. Construct ffmpeg command with stream copy (fast, no re-encoding):
   ```bash
   ffmpeg -i {input_path} \
          -ss {start_sec} \
          -to {end_sec} \
          -c copy \
          {output_path}
   ```

2. Execute asynchronously using `asyncio.create_subprocess_exec`
   - Keyframe-accurate clipping
   - Maintains original quality

3. Output: Clipped video saved to `DOWNLOAD_DIR/clipped_{request_id}.mp4`

4. If no clipping requested:
   - Original downloaded video becomes the target file

#### Step 7: Response Generation

**Components Involved:**
- Request Handler
- Static File Server

**Process Flow:**
1. Construct download URL:
   ```python
   base_url = os.getenv("BASE_URL", str(request.base_url).rstrip("/"))
   download_link = f"{base_url}/downloads/{target_filename}"
   ```

2. Return JSON response:
   ```json
   {
     "download_link": "http://server:port/downloads/clipped_17040672000000.mp4"
   }
   ```

3. Static files served via FastAPI's `StaticFiles` middleware
   - Mount point: `/downloads`
   - Directory: `DOWNLOAD_DIR`

#### Step 8: Asynchronous Cleanup

**Components Involved:**
- Cleanup Task (`cleanup_file`)
- asyncio Event Loop

**Process Flow:**
1. Schedule cleanup task in background:
   ```python
   asyncio.create_task(cleanup_file(filepath, DOWNLOAD_TTL_SECONDS))
   ```

2. Wait for TTL period (default: 3600 seconds / 1 hour)

3. Remove temporary files:
   - Original downloaded video
   - Clipped video (if created)

4. Error handling:
   - Failed cleanup logged but doesn't affect client request

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph Input["Input Parameters"]
        P1[tweet_url]
        P2[start_sec]
        P3[end_sec]
    end

    subgraph Processing["Processing Pipeline"]
        P4[URL Normalization]
        P5[Timeframe Validation]
        P6[ID Generation]
        P7[Video Download]
        P8[Duration Check]
        P9[Video Clipping]
    end

    subgraph Output["Output"]
        P10[Download Link]
    end

    subgraph External["External Tools"]
        T1[yt-dlp]
        T2[ffprobe]
        T3[ffmpeg]
    end

    subgraph Storage["File Storage"]
        F1[Original Video]
        F2[Clipped Video]
    end

    P1 --> P4
    P2 --> P5
    P3 --> P5
    P4 --> P6
    P5 --> P6
    P6 --> P7
    P7 --> T1
    T1 --> F1
    F1 --> P8
    P8 --> T2
    P8 --> P9
    P9 --> T3
    T3 --> F2
    F1 --> P10
    F2 --> P10
```

## Deployment Architecture

```mermaid
graph TB
    subgraph Docker["Docker Container"]
        subgraph App["Application Layer"]
            A1[FastAPI Server]
            A2[Uvicorn ASGI]
        end

        subgraph Deps["Dependencies"]
            D1[yt-dlp]
            D2[FFmpeg]
            D3[FFprobe]
        end

        subgraph Env["Environment"]
            E1[PORT]
            E2[DOWNLOAD_DIR]
            E3[DOWNLOAD_TTL_SECONDS]
            E4[ALLOWED_ORIGINS]
            E5[REDIS_URL]
        end

        subgraph Volumes["Persistent Storage"]
            V1[/app/downloads]
        end
    end

    subgraph External["External Services"]
        R1[Redis Server]
    end

    subgraph Network["Network"]
        N1[Port 8080/9000]
        N2[CORS Origins]
    end

    A2 --> A1
    A1 --> D1
    A1 --> D2
    A1 --> D3
    A1 --> E1
    A1 --> E2
    A1 --> E3
    A1 --> E4
    A1 --> E5
    E5 -.-> R1
    A1 --> V1
    A2 --> N1
    N1 --> N2
```

## Configuration Reference

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PORT` | 9000 | Server listening port |
| `DOWNLOAD_DIR` | /app/downloads | Directory for temporary video files |
| `DOWNLOAD_TTL_SECONDS` | 3600 | Time before file cleanup (1 hour) |
| `ALLOWED_ORIGINS` | http://localhost:3000 | Comma-separated CORS origins |
| `REDIS_URL` | redis://localhost:6379 | Redis connection string for rate limiting |
| `BASE_URL` | Auto-detected | Base URL for download links |
| `MAX_CLIP_SECONDS` | 600 | Maximum clip duration (10 minutes) |
| `MAX_TIMECODE_SECONDS` | 86400 | Maximum absolute timestamp (24 hours) |

## Error Handling Strategy

```mermaid
flowchart TD
    E1[Error Occurs] --> E2{Error Type}

    E2 -->|Validation Error| E3[HTTPException 400]
    E2 -->|Rate Limit Exceeded| E4[HTTPException 429]
    E2 -->|Download Failure| E5[HTTPException 500]
    E2 -->|Clip Failure| E6[HTTPException 500]
    E2 -->|Unknown Error| E7[HTTPException 500]

    E3 --> E8[Log Error Details]
    E4 --> E8
    E5 --> E8
    E6 --> E8
    E7 --> E8

    E8 --> E9[Trigger Cleanup]
    E9 --> E10[Return Error Response]
```

## Performance Considerations

1. **Async Operations**: All I/O operations (subprocess calls, file operations) use async/await patterns
2. **Stream Copy**: FFmpeg uses `-c copy` for fast clipping without re-encoding
3. **Rate Limiting**: Prevents resource exhaustion with configurable limits
4. **Cleanup Automation**: Automatic file deletion prevents disk space issues
5. **Thread Safety**: ID generator uses locks for concurrent request safety

## Security Features

1. **CORS Protection**: Restricts cross-origin requests to configured origins
2. **Rate Limiting**: Prevents abuse and DoS attacks
3. **Input Validation**: Comprehensive validation of all user inputs
4. **Path Isolation**: Downloads restricted to dedicated directory
5. **Temporary Files**: Automatic cleanup reduces attack surface

## Monitoring & Logging

- Structured logging with timestamps and log levels
- Request processing tracked at INFO level
- Errors logged at ERROR level with stack traces
- Rate limiter events logged for monitoring

---

*Document Version: 1.0*
*Last Updated: 2024*


+++ docs/architecture.md (修改后)
# ClipIt Architecture Documentation

## Overview

This document describes the architecture and workflow of ClipIt (formerly Video Clipper), a production-ready split-architecture application. The system consists of a **Next.js frontend hosted on Vercel** and a **FastAPI backend deployed on Oracle Cloud Infrastructure (OCI)**, with Caddy serving as a reverse proxy and TLS terminator.

The backend downloads videos from Twitter/X posts and creates clipped segments based on user-specified timeframes using yt-dlp and FFmpeg.

## Current Deployment Status

**Project Score: 8.5/10** - Production-ready with minor improvements needed

### Deployment Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                         INTERNET                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌─────────────────┐             ┌─────────────────────┐
    │     Vercel      │             │   Name.com DNS      │
    │   (Frontend)    │             │   (DNS Provider)    │
    │                 │             │                     │
    │ clipit.         │             │ clipit.             │
    │ drunktrader.dev │             │ drunktrader.dev     │
    │                 │             │       │             │
    └────────┬────────┘             │       ├─────────────┘
             │                      │       │
             │                      │       ▼
             │                      │ ┌─────────────────────┐
             │                      │ │ clipit-backend.     │
             │                      │ │ drunktrader.dev     │
             │                      │ │       │             │
             │                      │ │       ▼             │
             │                      │ │  140.238.227.201    │
             │                      │ │   (OCI Public IP)   │
             │                      │ └───────┬─────────────┘
             │                      │         │
             │ POST /clip           │         ▼
             │──────────────────────▶│ ┌─────────────────────┐
             │                      │ │       Caddy         │
             │                      │ │  (Reverse Proxy)    │
             │                      │ │  :443 → :8080       │
             │                      │ │  + TLS/HTTPS        │
             │                      │ └─────────┬───────────┘
             │                      │           │
             │                      │           ▼
             │ GET /downloads/      │ ┌─────────────────────┐
             │◀─────────────────────│ │      FastAPI        │
             │                      │ │    (Port 8080)      │
             │                      │ │                     │
             │                      │ │  ┌───────────────┐  │
             │                      │ │  │    Redis      │  │
             │                      │ │  │ (Rate Limit)  │  │
             │                      │ │  └───────────────┘  │
             │                      │ │                     │
             │                      │ │  ┌───────────────┐  │
             │                      │ │  │   yt-dlp      │  │
             │                      │ │  └───────────────┘  │
             │                      │ │                     │
             │                      │ │  ┌───────────────┐  │
             │                      │ │  │ FFmpeg/FFprobe│  │
             │                      │ │  └───────────────┘  │
             │                      │ │                     │
             │                      │ │  ┌───────────────┐  │
             │                      │ │  │ /app/downloads│  │
             │                      │ │  │ (Temp Store)  │  │
             │                      │ │  └───────────────┘  │
             │                      │ └─────────────────────┘
             │                      │         OCI VM
             ▼                      │
    ┌─────────────────┐             │
    │   Next.js App   │             │
    │   (Browser)     │             │
    └─────────────────┘             └─────────────────────────┘
```

## High-Level Architecture

ClipIt uses a **split frontend/backend architecture**:

- **Frontend**: Next.js application hosted on Vercel at `https://clipit.drunktrader.dev`
- **Backend**: FastAPI application on OCI VM at `https://clipit-backend.drunktrader.dev`
- **Supporting Services**: Redis and video processing tools run in Docker containers on the OCI VM

### Key Architectural Decisions

1. **Separation of Concerns**: Frontend handles UI/UX; backend handles video processing
2. **Edge Hosting**: Vercel provides global CDN for static assets
3. **Compute Proximity**: Backend runs close to video storage to minimize I/O latency
4. **TLS Termination**: Caddy handles HTTPS certificates automatically
5. **Stateless Design**: Videos stored temporarily on filesystem, not in Redis

## System Architecture Diagram

```mermaid
graph TB
    subgraph User["User Layer"]
        U[End User Browser]
    end

    subgraph Frontend["Frontend Layer - Vercel"]
        A[Next.js Application]
        V[Vercel CDN]
    end

    subgraph DNS["DNS Layer - Name.com"]
        D1[clipit.drunktrader.dev → Vercel]
        D2[clipit-backend.drunktrader.dev → OCI IP]
    end

    subgraph Gateway["Gateway Layer - OCI"]
        C[Caddy Reverse Proxy]
        T[TLS/HTTPS Manager]
    end

    subgraph Backend["Backend Layer - FastAPI"]
        F[FastAPI Application]
        CORS[CORS Middleware]
        RL[Rate Limiter - SlowAPI]
    end

    subgraph Core["Core Processing Layer"]
        RH[Request Handler /clip]
        IG[ID Generator]
        TV[Timeframe Validator]
    end

    subgraph Services["External Services"]
        YD[yt-dlp Service]
        FF[FFmpeg/FFprobe]
        RD[Redis Rate Limiter]
    end

    subgraph Storage["Storage Layer"]
        DL[Downloads Directory /app/downloads]
        SF[Static File Server]
        CL[Cleanup Scheduler]
    end

    U -->|HTTPS| V
    V --> A
    A -->|POST /clip| D2
    D2 --> C
    C -->|HTTP :8080| F
    F --> CORS
    F --> RL
    RL --> RD
    F --> RH
    RH --> IG
    RH --> TV
    RH --> YD
    RH --> FF
    YD --> DL
    FF --> DL
    DL --> SF
    SF -->|GET /downloads/:file| C
    C --> U
    CL -.->|TTL Expiry| DL
```

## Component Architecture

```mermaid
classDiagram
    class FastAPI {
        +app: FastAPI
        +limiter: SlowAPILimiter
        +middleware: CORSMiddleware
    }

    class RequestHandler {
        +clip_video(request: Request)
        +cleanup_file(filepath, ttl)
    }

    class IDGenerator {
        -last_timestamp: int
        -counter: int
        -lock: Thread
        +generate_id() string
    }

    class TimeframeValidator {
        +validate_timeframe(start, end)
        +validate_timeframe_against_video(start, end, path)
        +get_video_duration(path)
    }

    class VideoDownloader {
        +download_tweet_video(url, output_path)
    }

    class VideoClipper {
        +clip_video_ffmpeg(input, output, start, end)
    }

    class RateLimiter {
        -redis_client: Redis
        +limit(rate: string)
    }

    FastAPI --> RequestHandler
    RequestHandler --> IDGenerator
    RequestHandler --> TimeframeValidator
    RequestHandler --> VideoDownloader
    RequestHandler --> VideoClipper
    FastAPI --> RateLimiter
```

## Detailed Request Flow

### Complete Workflow: From User to Download

This section describes the complete journey of a video clip request through the ClipIt architecture.

```mermaid
sequenceDiagram
    participant U as User Browser
    participant V as Vercel (Next.js)
    participant D as DNS (Name.com)
    participant CA as Caddy
    participant F as FastAPI
    participant R as Redis
    participant Y as yt-dlp
    participant FP as FFprobe
    participant FM as FFmpeg
    participant FS as Filesystem

    U->>V: Enter X/Twitter URL
    V->>D: Resolve clipit-backend.drunktrader.dev
    D-->>V: Return 140.238.227.201
    V->>CA: POST /clip (HTTPS :443)
    CA->>F: Reverse Proxy (HTTP :8080)

    Note over F: 1. CORS Validation
    F->>F: Check ALLOWED_ORIGINS

    Note over F: 2. Rate Limiting
    F->>R: Check rate limit (5/min/IP)
    R-->>F: Within limit

    Note over F: 3. Request Validation
    F->>F: Validate start/end times
    F->>F: Generate unique ID

    Note over F,Y: 4. Video Download
    F->>Y: Execute yt-dlp
    Y->>Y: Download from X/Twitter
    Y->>FS: Save /app/downloads/{id}.mp4
    Y-->>F: Download complete

    Note over F,FP: 5. Duration Validation
    F->>FP: Probe video duration
    FP-->>F: Return duration
    F->>F: Validate timeframe vs duration

    Note over F,FM: 6. Video Clipping
    F->>FM: ffmpeg -ss X -to Y -c copy
    FM->>FS: Create clipped_{id}.mp4
    FM-->>F: Clip complete

    Note over F: 7. Response Generation
    F->>F: Generate download URL
    F-->>CA: Return {download_link}
    CA-->>V: HTTPS response
    V-->>U: Display download button

    Note over U,FS: 8. Video Download
    U->>CA: GET /downloads/clipped_{id}.mp4
    CA->>F: Serve static file
    F->>FS: Read file
    FS-->>U: Stream video

    Note over F,FS: 9. Cleanup (TTL: 1 hour)
    F->>F: Schedule cleanup task
    Note right of F: After 3600 seconds
    F->>FS: Delete temp files
```

## Infrastructure Components

### DNS Configuration (Name.com)

The DNS layer routes traffic to the appropriate services:

| Subdomain | Type | Target | Purpose |
|-----------|------|--------|---------|
| `clipit.drunktrader.dev` | CNAME | Vercel | Frontend application |
| `clipit-backend.drunktrader.dev` | A | 140.238.227.201 | Backend API on OCI VM |

### Caddy Reverse Proxy

Caddy serves as the entry point for all backend traffic:

**Configuration Highlights:**
- Listens on port 443 (HTTPS)
- Automatically manages TLS certificates via Let's Encrypt
- Reverse proxies to FastAPI on `127.0.0.1:8080`
- Handles domain-based routing for `clipit-backend.drunktrader.dev`

**Benefits:**
- Zero-config HTTPS
- Automatic certificate renewal
- Simple reverse proxy configuration
- HTTP/2 support out of the box

### Docker Containerization

The backend runs in Docker containers on the OCI VM:

```yaml
Services:
  - fastapi-app: Port 8080
    ├── Python runtime
    ├── FastAPI + Uvicorn
    ├── yt-dlp
    ├── FFmpeg/FFprobe
    └── Volume: /app/downloads

  - redis: Port 6379
    └── Rate limiting state storage
```

**Note:** The Next.js container has been removed from OCI since the frontend now runs on Vercel.

### Redis Role

Redis is used **exclusively for rate limiting state**, not for video storage:

- Stores IP-based request counts
- Maintains sliding window for rate limit calculations
- Default limit: 5 requests per minute per IP
- Falls back to in-memory storage if Redis is unavailable

### Filesystem Storage

Video files are stored temporarily on the OCI VM filesystem:

- Location: `/app/downloads` (inside container)
- Naming: `{timestamp}{counter}.mp4` and `clipped_{timestamp}{counter}.mp4`
- TTL: 3600 seconds (1 hour) before automatic cleanup
- No database tracking - files managed by application logic

## Step-by-Step Processing Pipeline

#### Step 1: Request Reception & Middleware Processing

**Components Involved:**
- FastAPI Application
- CORS Middleware
- SlowAPI Rate Limiter

**Process Flow:**
1. Client sends POST request to `/clip` endpoint with JSON body:
   ```json
   {
     "tweet_url": "https://x.com/user/status/123456",
     "start": 10.5,
     "end": 25.0
   }
   ```

2. **CORS Middleware** validates origin against `ALLOWED_ORIGINS` environment variable
   - Default: `http://localhost:3000`
   - Supports multiple origins via comma-separated list

3. **Rate Limiter** checks request count:
   - Primary: Redis backend (`REDIS_URL` env var)
   - Fallback: In-memory storage if Redis unavailable
   - Limit: 5 requests per minute per IP address
   - Returns `429 Too Many Requests` if exceeded

#### Step 2: Request Parsing & Validation

**Components Involved:**
- Request Handler (`clip_video`)
- Timeframe Validator (`valid_timeframe.py`)

**Process Flow:**
1. Extract and normalize request parameters:
   - Convert `x.com` URLs to `twitter.com` for yt-dlp compatibility
   - Parse `start` and `end` timestamps

2. **Timeframe Validation Rules:**
   - Both `start` and `end` must be provided together, or both omitted (full video)
   - Values must be finite numeric seconds
   - `start >= 0`, `end > start`
   - Clip duration `(end - start) <= MAX_CLIP_SECONDS` (default: 600s)
   - Absolute times `<= MAX_TIMECODE_SECONDS` (default: 86400s)

3. Environment variables control limits:
   - `MAX_CLIP_SECONDS`: Maximum clip duration
   - `MAX_TIMECODE_SECONDS`: Maximum absolute timestamp

#### Step 3: Unique ID Generation

**Components Involved:**
- ID Generator (`id_generator.py`)

**Algorithm:**
```python
ID Format: {timestamp}{counter:04d}
Example: 17040672000000

- Timestamp: Unix epoch seconds
- Counter: 4-digit zero-padded increment for same-second requests
- Thread-safe with locking mechanism
```

**Purpose:**
- Ensures unique filenames for concurrent requests
- Enables tracking and cleanup of temporary files

#### Step 4: Video Download

**Components Involved:**
- Video Downloader (`download_command.py`)
- yt-dlp external tool

**Process Flow:**
1. Construct yt-dlp command:
   ```bash
   yt-dlp -o {output_path} \
          -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4" \
          {tweet_url}
   ```

2. Execute asynchronously using `asyncio.create_subprocess_exec`
   - Non-blocking operation
   - Captures stdout/stderr for error reporting

3. Error Handling:
   - subprocess failures raise HTTPException(500)
   - Error messages propagated to client

4. Output: Video saved to `DOWNLOAD_DIR/{request_id}.mp4`

#### Step 5: Timeframe Validation Against Video Duration

**Components Involved:**
- Timeframe Validator (`valid_timeframe.py`)
- FFprobe external tool

**Process Flow:**
1. Query video duration using ffprobe:
   ```bash
   ffprobe -v error \
           -show_entries format=duration \
           -of default=noprint_wrappers=1:nokey=1 \
           {video_path}
   ```

2. Validate requested timeframe:
   - `end_sec <= duration + 1s` (1s buffer for floating-point precision)
   - `start_sec <= duration`

3. Only executed if clipping was requested (start/end provided)

#### Step 6: Video Clipping

**Components Involved:**
- Video Clipper (`clip_from_download.py`)
- FFmpeg external tool

**Process Flow:**
1. Construct ffmpeg command with stream copy (fast, no re-encoding):
   ```bash
   ffmpeg -i {input_path} \
          -ss {start_sec} \
          -to {end_sec} \
          -c copy \
          {output_path}
   ```

2. Execute asynchronously using `asyncio.create_subprocess_exec`
   - Keyframe-accurate clipping
   - Maintains original quality

3. Output: Clipped video saved to `DOWNLOAD_DIR/clipped_{request_id}.mp4`

4. If no clipping requested:
   - Original downloaded video becomes the target file

#### Step 7: Response Generation

**Components Involved:**
- Request Handler
- Static File Server

**Process Flow:**
1. Construct download URL:
   ```python
   base_url = os.getenv("BASE_URL", str(request.base_url).rstrip("/"))
   download_link = f"{base_url}/downloads/{target_filename}"
   ```

2. Return JSON response:
   ```json
   {
     "download_link": "http://server:port/downloads/clipped_17040672000000.mp4"
   }
   ```

3. Static files served via FastAPI's `StaticFiles` middleware
   - Mount point: `/downloads`
   - Directory: `DOWNLOAD_DIR`

#### Step 8: Asynchronous Cleanup

**Components Involved:**
- Cleanup Task (`cleanup_file`)
- asyncio Event Loop

**Process Flow:**
1. Schedule cleanup task in background:
   ```python
   asyncio.create_task(cleanup_file(filepath, DOWNLOAD_TTL_SECONDS))
   ```

2. Wait for TTL period (default: 3600 seconds / 1 hour)

3. Remove temporary files:
   - Original downloaded video
   - Clipped video (if created)

4. Error handling:
   - Failed cleanup logged but doesn't affect client request

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph Input["Input Parameters"]
        P1[tweet_url]
        P2[start_sec]
        P3[end_sec]
    end

    subgraph Processing["Processing Pipeline"]
        P4[URL Normalization]
        P5[Timeframe Validation]
        P6[ID Generation]
        P7[Video Download]
        P8[Duration Check]
        P9[Video Clipping]
    end

    subgraph Output["Output"]
        P10[Download Link]
    end

    subgraph External["External Tools"]
        T1[yt-dlp]
        T2[ffprobe]
        T3[ffmpeg]
    end

    subgraph Storage["File Storage"]
        F1[Original Video]
        F2[Clipped Video]
    end

    P1 --> P4
    P2 --> P5
    P3 --> P5
    P4 --> P6
    P5 --> P6
    P6 --> P7
    P7 --> T1
    T1 --> F1
    F1 --> P8
    P8 --> T2
    P8 --> P9
    P9 --> T3
    T3 --> F2
    F1 --> P10
    F2 --> P10
```

## Production Deployment Architecture

### Current OCI VM Setup

The backend runs on Oracle Cloud Infrastructure with the following topology:

```mermaid
graph TB
    subgraph Internet["Internet"]
        U[User Requests]
    end

    subgraph OCI["Oracle Cloud Infrastructure VM"]
        subgraph Caddy["Caddy Reverse Proxy"]
            C1[TLS Termination :443]
            C2[Reverse Proxy to :8080]
            C3[Auto HTTPS/Let's Encrypt]
        end

        subgraph Docker["Docker Containers"]
            subgraph FastAPI_Container["FastAPI Container"]
                F1[FastAPI Application]
                F2[Uvicorn ASGI Server]
                F3[yt-dlp]
                F4[FFmpeg/FFprobe]
                F5[Volume: /app/downloads]
            end

            subgraph Redis_Container["Redis Container"]
                R1[Redis Server :6379]
                R2[Rate Limit State]
            end
        end
    end

    subgraph Vercel["Vercel (Separate)"]
        V1[Next.js Frontend]
        V2[CDN Edge Network]
    end

    U -->|HTTPS clipit-backend.drunktrader.dev| C1
    C1 --> C2
    C2 -->|HTTP localhost:8080| F1
    F1 --> F2
    F1 --> F3
    F1 --> F4
    F1 --> F5
    F1 -->|Rate Limit Check| R1
    R1 --> R2

    V1 -.->|Frontend Only| U
```

**Important Notes:**
- The Next.js container has been **removed** from OCI since the frontend now runs on Vercel
- Only FastAPI and Redis containers run on the OCI VM
- Caddy runs as a native service on the host (not in Docker)
- All video processing happens inside the FastAPI container

### Environment Configuration

Production environment variables on OCI:

| Variable | Production Value | Purpose |
|----------|------------------|---------|
| `PORT` | 8080 | Internal FastAPI port |
| `ALLOWED_ORIGINS` | `https://clipit.drunktrader.dev` | CORS for Vercel frontend |
| `REDIS_URL` | `redis://redis:6379` | Docker network Redis URL |
| `BASE_URL` | `https://clipit-backend.drunktrader.dev` | Public backend URL |
| `DOWNLOAD_TTL_SECONDS` | 3600 | 1-hour file retention |

## Configuration Reference

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PORT` | 9000 | Server listening port |
| `DOWNLOAD_DIR` | /app/downloads | Directory for temporary video files |
| `DOWNLOAD_TTL_SECONDS` | 3600 | Time before file cleanup (1 hour) |
| `ALLOWED_ORIGINS` | http://localhost:3000 | Comma-separated CORS origins |
| `REDIS_URL` | redis://localhost:6379 | Redis connection string for rate limiting |
| `BASE_URL` | Auto-detected | Base URL for download links |
| `MAX_CLIP_SECONDS` | 600 | Maximum clip duration (10 minutes) |
| `MAX_TIMECODE_SECONDS` | 86400 | Maximum absolute timestamp (24 hours) |

## Error Handling Strategy

```mermaid
flowchart TD
    E1[Error Occurs] --> E2{Error Type}

    E2 -->|Validation Error| E3[HTTPException 400]
    E2 -->|Rate Limit Exceeded| E4[HTTPException 429]
    E2 -->|Download Failure| E5[HTTPException 500]
    E2 -->|Clip Failure| E6[HTTPException 500]
    E2 -->|Unknown Error| E7[HTTPException 500]

    E3 --> E8[Log Error Details]
    E4 --> E8
    E5 --> E8
    E6 --> E8
    E7 --> E8

    E8 --> E9[Trigger Cleanup]
    E9 --> E10[Return Error Response]
```

## Performance Considerations

1. **Async Operations**: All I/O operations (subprocess calls, file operations) use async/await patterns
2. **Stream Copy**: FFmpeg uses `-c copy` for fast clipping without re-encoding
3. **Rate Limiting**: Prevents resource exhaustion with configurable limits
4. **Cleanup Automation**: Automatic file deletion prevents disk space issues
5. **Thread Safety**: ID generator uses locks for concurrent request safety

## Security Features

1. **CORS Protection**: Restricts cross-origin requests to configured origins
2. **Rate Limiting**: Prevents abuse and DoS attacks
3. **Input Validation**: Comprehensive validation of all user inputs
4. **Path Isolation**: Downloads restricted to dedicated directory
5. **Temporary Files**: Automatic cleanup reduces attack surface

## Monitoring & Logging

- Structured logging with timestamps and log levels
- Request processing tracked at INFO level
- Errors logged at ERROR level with stack traces
- Rate limiter events logged for monitoring

## Architecture Summary

### In One Sentence

**Vercel serves the Next.js UI, the browser sends clipping requests to the OCI-hosted FastAPI backend through Caddy/HTTPS, FastAPI uses Redis for rate limiting and yt-dlp/FFmpeg for video processing, stores temporary results on disk, returns a download URL, and deletes files after the 1-hour TTL.**

### Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Frontend Host | Vercel | Global CDN edge network |
| Backend Host | OCI VM | 140.238.227.201 |
| Max Clip Duration | 600 seconds | 10 minutes |
| File TTL | 3600 seconds | 1 hour |
| Rate Limit | 5 requests/min/IP | Configurable via SlowAPI |
| HTTPS | Automatic | Caddy + Let's Encrypt |