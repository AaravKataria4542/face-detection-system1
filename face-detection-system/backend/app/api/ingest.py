"""
Endpoint 1: Receive video feed.

Two ingest paths:
  • POST /api/v1/ingest/{session_id}/frame  – single JPEG frame upload
  • WS  /api/v1/ingest/{session_id}/ws      – WebSocket frame stream
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.face_detection import FaceDetector, process_frame
from app.services.frame_buffer import frame_buffer
from app.services.roi_repository import ROIRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])

# One shared detector instance (MediaPipe is not thread-safe; we rely on
# the single-threaded asyncio event loop + run_in_executor for CPU work).
_detector = FaceDetector(min_detection_confidence=0.5)


def _new_session_id() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# POST single frame
# ---------------------------------------------------------------------------

@router.post(
    "/{session_id}/frame",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a single JPEG frame",
)
async def ingest_frame(
    session_id: str,
    frame_index: int = 0,
    file: UploadFile = File(..., description="JPEG image frame"),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ("image/jpeg", "image/jpg", "image/png"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG/PNG frames are accepted.",
        )

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:  # 5 MB cap
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Frame too large.")

    annotated, det = process_frame(raw, _detector)
    frame_buffer.put(session_id, annotated)

    if det:
        repo = ROIRepository(db)
        await repo.save(session_id, frame_index, det)
        return {"session_id": session_id, "frame_index": frame_index, "face_detected": True, "confidence": det.confidence}

    return {"session_id": session_id, "frame_index": frame_index, "face_detected": False}


# ---------------------------------------------------------------------------
# WebSocket stream
# ---------------------------------------------------------------------------

@router.websocket("/{session_id}/ws")
async def ingest_ws(session_id: str, websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """
    Accepts a stream of raw JPEG bytes over WebSocket.
    Each message = one frame.  Sends back JSON ack with detection result.
    """
    await websocket.accept()
    logger.info("WS ingest connected: session=%s", session_id)
    frame_index = 0
    repo = ROIRepository(db)

    try:
        while True:
            raw = await websocket.receive_bytes()

            if len(raw) > 5 * 1024 * 1024:
                await websocket.send_json({"error": "frame_too_large"})
                continue

            annotated, det = process_frame(raw, _detector)
            frame_buffer.put(session_id, annotated)

            if det:
                await repo.save(session_id, frame_index, det)
                await websocket.send_json({
                    "frame_index": frame_index,
                    "face_detected": True,
                    "confidence": round(det.confidence, 4),
                    "bbox": {
                        "x": det.x_px, "y": det.y_px,
                        "w": det.width_px, "h": det.height_px,
                    },
                })
            else:
                await websocket.send_json({"frame_index": frame_index, "face_detected": False})

            frame_index += 1

    except WebSocketDisconnect:
        logger.info("WS ingest disconnected: session=%s frames=%d", session_id, frame_index)
    except Exception as exc:
        logger.exception("WS ingest error session=%s: %s", session_id, exc)
        await websocket.close(code=1011)
