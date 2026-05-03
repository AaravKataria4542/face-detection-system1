from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.roi import ROIRecord
from app.services.face_detection import DetectionResult


class ROIRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, session_id: str, frame_index: int, det: DetectionResult) -> ROIRecord:
        record = ROIRecord(
            session_id=session_id,
            frame_index=frame_index,
            timestamp=datetime.now(timezone.utc),
            x_norm=det.x_norm,
            y_norm=det.y_norm,
            width_norm=det.width_norm,
            height_norm=det.height_norm,
            x_px=det.x_px,
            y_px=det.y_px,
            width_px=det.width_px,
            height_px=det.height_px,
            frame_width=det.frame_width,
            frame_height=det.frame_height,
            confidence=det.confidence,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 500,
        offset: int = 0,
    ) -> Sequence[ROIRecord]:
        stmt = (
            select(ROIRecord)
            .where(ROIRecord.session_id == session_id)
            .order_by(ROIRecord.frame_index)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_session(self, session_id: str) -> int:
        stmt = select(func.count()).where(ROIRecord.session_id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_sessions(self) -> list[dict]:
        stmt = (
            select(
                ROIRecord.session_id,
                func.count(ROIRecord.id).label("frame_count"),
                func.min(ROIRecord.timestamp).label("created_at"),
            )
            .group_by(ROIRecord.session_id)
            .order_by(func.min(ROIRecord.timestamp).desc())
        )
        result = await self._session.execute(stmt)
        return [
            {"session_id": r.session_id, "frame_count": r.frame_count, "created_at": r.created_at}
            for r in result.all()
        ]
