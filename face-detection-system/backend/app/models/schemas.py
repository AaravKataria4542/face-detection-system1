from datetime import datetime
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x_norm: float = Field(..., ge=0.0, le=1.0, description="Normalised x (top-left)")
    y_norm: float = Field(..., ge=0.0, le=1.0, description="Normalised y (top-left)")
    width_norm: float = Field(..., ge=0.0, le=1.0, description="Normalised width")
    height_norm: float = Field(..., ge=0.0, le=1.0, description="Normalised height")
    x_px: int = Field(..., ge=0, description="Pixel x (top-left)")
    y_px: int = Field(..., ge=0, description="Pixel y (top-left)")
    width_px: int = Field(..., ge=0, description="Pixel width")
    height_px: int = Field(..., ge=0, description="Pixel height")


class ROIRecordOut(BaseModel):
    id: int
    session_id: str
    frame_index: int
    timestamp: datetime
    frame_width: int
    frame_height: int
    confidence: float
    bbox: BoundingBox

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_record(cls, record) -> "ROIRecordOut":
        return cls(
            id=record.id,
            session_id=record.session_id,
            frame_index=record.frame_index,
            timestamp=record.timestamp,
            frame_width=record.frame_width,
            frame_height=record.frame_height,
            confidence=record.confidence,
            bbox=BoundingBox(
                x_norm=record.x_norm,
                y_norm=record.y_norm,
                width_norm=record.width_norm,
                height_norm=record.height_norm,
                x_px=record.x_px,
                y_px=record.y_px,
                width_px=record.width_px,
                height_px=record.height_px,
            ),
        )


class ROIListResponse(BaseModel):
    session_id: str
    total: int
    records: list[ROIRecordOut]


class SessionInfo(BaseModel):
    session_id: str
    frame_count: int
    created_at: datetime | None = None
