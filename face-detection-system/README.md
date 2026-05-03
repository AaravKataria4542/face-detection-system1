# FaceTrack — Real-Time Face Detection Streaming System

A fully containerised full-stack application that:
- Accepts a webcam video feed over **WebSocket**
- Detects faces using **MediaPipe** (no OpenCV)
- Draws an axis-aligned bounding-box ROI using **Pillow**
- Persists ROI data to **PostgreSQL**
- Streams annotated frames back as **MJPEG**
- Displays everything in a **React** frontend

---

## Quick Start (< 5 minutes)

### Prerequisites
- Docker ≥ 24 and Docker Compose v2
- A browser with webcam access (Chrome recommended)

```bash
# 1. Clone / enter the project
cd face-detection-system

# 2. Build and start all containers
docker compose up --build

# 3. Open the app
open http://localhost          # or navigate in browser
```

Click **▶ START STREAM**, allow camera access, and watch live face detection with bounding boxes drawn server-side.

API docs: http://localhost:8000/docs

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Network                         │
│                                                          │
│  ┌─────────────┐   WebSocket    ┌──────────────────────┐ │
│  │             │ ─────────────► │  POST /ingest/{id}/ws│ │
│  │   React     │                │                      │ │
│  │  Frontend   │   MJPEG stream │  GET /stream/{id}    │ │
│  │  (nginx:80) │ ◄───────────── │  /mjpeg              │ │
│  │             │                │                      │ │
│  │             │   REST         │  GET /roi/{id}       │ │
│  │             │ ◄───────────── │                      │ │
│  └─────────────┘                │  FastAPI             │ │
│                                 │  (uvicorn:8000)      │ │
│                                 │                      │ │
│                                 │  MediaPipe Detector  │ │
│                                 │  Pillow ROI Drawer   │ │
│                                 └──────────┬───────────┘ │
│                                            │             │
│                                 ┌──────────▼───────────┐ │
│                                 │  PostgreSQL :5432     │ │
│                                 │  roi_records table   │ │
│                                 └──────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Services

| Service   | Image              | Port  | Role                          |
|-----------|--------------------|-------|-------------------------------|
| db        | postgres:16-alpine | 5432  | ROI data persistence          |
| backend   | python:3.11-slim   | 8000  | FastAPI + MediaPipe + Pillow  |
| frontend  | node:20 → nginx    | 80    | React UI                      |

---

## API Reference

### Endpoint 1 — Ingest (receive feed)

| Method      | Path                              | Description                     |
|-------------|-----------------------------------|---------------------------------|
| `POST`      | `/api/v1/ingest/{session_id}/frame` | Upload a single JPEG frame     |
| `WebSocket` | `/api/v1/ingest/{session_id}/ws`    | Stream frames; receive JSON acks |

**WebSocket ack (per frame):**
```json
{
  "frame_index": 42,
  "face_detected": true,
  "confidence": 0.9731,
  "bbox": { "x": 120, "y": 80, "w": 200, "h": 260 }
}
```

### Endpoint 2 — Stream (serve annotated feed)

| Method      | Path                               | Description                    |
|-------------|------------------------------------|--------------------------------|
| `GET`       | `/api/v1/stream/{session_id}/mjpeg` | MJPEG multipart stream        |
| `WebSocket` | `/api/v1/stream/{session_id}/ws`    | Push JPEG frames over WS      |

### Endpoint 3 — ROI Data

| Method | Path                           | Description                         |
|--------|--------------------------------|-------------------------------------|
| `GET`  | `/api/v1/roi/sessions`        | List all sessions                   |
| `GET`  | `/api/v1/roi/{session_id}`    | Paginated ROI records for a session |
| `GET`  | `/api/v1/roi/{session_id}/latest` | Most recent ROI record          |

**ROI record shape:**
```json
{
  "id": 1,
  "session_id": "abc123",
  "frame_index": 42,
  "timestamp": "2024-01-15T10:30:00Z",
  "frame_width": 640,
  "frame_height": 480,
  "confidence": 0.97,
  "bbox": {
    "x_norm": 0.1875, "y_norm": 0.1667,
    "width_norm": 0.3125, "height_norm": 0.5417,
    "x_px": 120, "y_px": 80,
    "width_px": 200, "height_px": 260
  }
}
```

---

## Database Schema

```sql
CREATE TABLE roi_records (
    id           SERIAL PRIMARY KEY,
    session_id   VARCHAR(64)   NOT NULL,
    frame_index  INTEGER       NOT NULL,
    timestamp    TIMESTAMPTZ   NOT NULL,
    -- Normalised coordinates [0..1]
    x_norm       FLOAT         NOT NULL,
    y_norm       FLOAT         NOT NULL,
    width_norm   FLOAT         NOT NULL,
    height_norm  FLOAT         NOT NULL,
    -- Pixel coordinates
    x_px         INTEGER       NOT NULL,
    y_px         INTEGER       NOT NULL,
    width_px     INTEGER       NOT NULL,
    height_px    INTEGER       NOT NULL,
    -- Frame info
    frame_width  INTEGER       NOT NULL,
    frame_height INTEGER       NOT NULL,
    confidence   FLOAT         NOT NULL
);

CREATE INDEX ix_roi_session_frame ON roi_records (session_id, frame_index);
CREATE INDEX ix_roi_timestamp     ON roi_records (timestamp);
```

---

## Face Detection — No OpenCV

| Component          | Library Used   | Purpose                         |
|--------------------|----------------|---------------------------------|
| Face detection     | MediaPipe      | FaceDetection model (short range) |
| Image decode/encode| Pillow (PIL)   | Open JPEG, convert RGB          |
| ROI bounding box   | Pillow ImageDraw | Draw rectangle, label        |
| Tensor operations  | NumPy          | PIL → ndarray for MediaPipe     |

OpenCV is **not installed** and not present in `requirements.txt`.

---

## Running Tests

```bash
# Inside the backend container
docker compose exec backend pytest -v

# Or locally with a venv
cd backend
pip install -r requirements.txt aiosqlite
pytest -v
```

---

## Project Structure

```
face-detection-system/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── app/
│       ├── main.py            # FastAPI app + lifespan
│       ├── core/config.py     # Settings (pydantic-settings)
│       ├── db/session.py      # Async SQLAlchemy engine
│       ├── models/
│       │   ├── roi.py         # ROIRecord ORM model
│       │   └── schemas.py     # Pydantic response schemas
│       ├── services/
│       │   ├── face_detection.py   # MediaPipe + Pillow ROI drawing
│       │   ├── roi_repository.py   # DB access layer
│       │   └── frame_buffer.py     # In-memory latest-frame store
│       ├── api/
│       │   ├── ingest.py      # Endpoint 1: receive feed
│       │   ├── stream.py      # Endpoint 2: serve feed
│       │   └── roi.py         # Endpoint 3: ROI data
│       └── tests/
│           ├── test_face_detection.py
│           └── test_api.py
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── App.js / App.module.css
        ├── index.js / index.css
        ├── hooks/
        │   ├── useWebcamStream.js
        │   └── useROIData.js
        └── components/
            ├── VideoPanel.js/.module.css
            ├── ROITable.js/.module.css
            └── StatusBar.js/.module.css
```

---

## AI Collaboration

This project was built with Claude (Anthropic) as an AI pair-programmer. The AI contributed:
- Initial architecture decisions (MediaPipe vs dlib, asyncpg vs sync driver)
- All code generation with subsequent manual review
- Schema design recommendations (normalised + pixel coords for flexibility)

All generated code was reviewed for correctness, security (non-root Docker user, content-type validation, frame size caps, CORS), and alignment with the spec (no OpenCV, Pillow-only drawing).
