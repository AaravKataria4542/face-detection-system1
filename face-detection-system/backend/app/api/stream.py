"""
Endpoint 2: Serve the annotated video feed.

  • GET /api/v1/stream/{session_id}/mjpeg  – MJPEG multipart stream
  • WS  /api/v1/stream/{session_id}/ws     – WebSocket JPEG stream
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import StreamingResponse

from app.services.frame_buffer import frame_buffer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stream", tags=["stream"])

BOUNDARY = b"--frameboundary"


async def _mjpeg_generator(session_id: str):
    """Async generator producing MJPEG multipart chunks."""
    consecutive_empty = 0
    while True:
        jpeg = await frame_buffer.wait_for_frame(session_id, timeout=3.0)
        if jpeg is None:
            consecutive_empty += 1
            if consecutive_empty > 10:
                # No frames for 30 s – stop the stream
                break
            continue

        consecutive_empty = 0
        yield (
            BOUNDARY + b"\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n"
            b"\r\n" + jpeg + b"\r\n"
        )


@router.get(
    "/{session_id}/mjpeg",
    summary="Serve annotated video as MJPEG stream",
    responses={200: {"content": {"multipart/x-mixed-replace": {}}}},
)
async def serve_mjpeg(session_id: str):
    if frame_buffer.latest(session_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active stream for session '{session_id}'.",
        )
    return StreamingResponse(
        _mjpeg_generator(session_id),
        media_type="multipart/x-mixed-replace; boundary=frameboundary",
        headers={"Cache-Control": "no-cache, no-store"},
    )


@router.websocket("/{session_id}/ws")
async def serve_ws(session_id: str, websocket: WebSocket):
    """Push annotated JPEG frames over WebSocket to the frontend."""
    await websocket.accept()
    logger.info("WS stream connected: session=%s", session_id)

    try:
        while True:
            jpeg = await frame_buffer.wait_for_frame(session_id, timeout=5.0)
            if jpeg is None:
                # Send a keep-alive ping
                await websocket.send_json({"type": "ping"})
                continue

            await websocket.send_bytes(jpeg)
    except WebSocketDisconnect:
        logger.info("WS stream disconnected: session=%s", session_id)
    except Exception as exc:
        logger.exception("WS stream error session=%s: %s", session_id, exc)
        await websocket.close(code=1011)
