from datetime import datetime, timezone
from sqlalchemy import Integer, Float, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class ROIRecord(Base):
    """
    Stores axis-aligned bounding box (ROI) data for each detected face frame.

    Coordinates are normalised to [0.0, 1.0] relative to frame dimensions,
    making them resolution-independent.  Pixel values are also stored for
    convenience when the frame dimensions are known.
    """

    __tablename__ = "roi_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Normalised coordinates [0..1]
    x_norm: Mapped[float] = mapped_column(Float, nullable=False)
    y_norm: Mapped[float] = mapped_column(Float, nullable=False)
    width_norm: Mapped[float] = mapped_column(Float, nullable=False)
    height_norm: Mapped[float] = mapped_column(Float, nullable=False)

    # Pixel coordinates (frame resolution at capture time)
    x_px: Mapped[int] = mapped_column(Integer, nullable=False)
    y_px: Mapped[int] = mapped_column(Integer, nullable=False)
    width_px: Mapped[int] = mapped_column(Integer, nullable=False)
    height_px: Mapped[int] = mapped_column(Integer, nullable=False)

    # Frame dimensions
    frame_width: Mapped[int] = mapped_column(Integer, nullable=False)
    frame_height: Mapped[int] = mapped_column(Integer, nullable=False)

    # Detection confidence [0..1]
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    __table_args__ = (
        Index("ix_roi_session_frame", "session_id", "frame_index"),
        Index("ix_roi_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ROIRecord id={self.id} session={self.session_id!r} "
            f"frame={self.frame_index} box=({self.x_px},{self.y_px},"
            f"{self.width_px},{self.height_px})>"
        )
