"""
Thread-safe in-memory store for the latest processed frame per session.
Used to serve the MJPEG stream to multiple consumers without reprocessing.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Optional


class FrameBuffer:
    def __init__(self) -> None:
        self._frames: dict[str, bytes] = {}
        self._events: dict[str, asyncio.Event] = defaultdict(asyncio.Event)

    def put(self, session_id: str, jpeg: bytes) -> None:
        self._frames[session_id] = jpeg
        event = self._events[session_id]
        event.set()
        event.clear()  # reset so next consumer waits for the next frame

    def latest(self, session_id: str) -> Optional[bytes]:
        return self._frames.get(session_id)

    async def wait_for_frame(self, session_id: str, timeout: float = 5.0) -> Optional[bytes]:
        """Block until a new frame is available or timeout."""
        event = self._events[session_id]
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return self._frames.get(session_id)

    def clear_session(self, session_id: str) -> None:
        self._frames.pop(session_id, None)
        self._events.pop(session_id, None)


# Singleton
frame_buffer = FrameBuffer()
