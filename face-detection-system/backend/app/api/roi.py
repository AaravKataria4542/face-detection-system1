"""
Endpoint 3: Serve stored ROI data.

  • GET /api/v1/roi/{session_id}          – paginated ROI records for a session
  • GET /api/v1/roi/{session_id}/latest   – most recent ROI record
  • GET /api/v1/roi/sessions              – list all known sessions
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import ROIListResponse, ROIRecordOut, SessionInfo
from app.services.roi_repository import ROIRepository

router = APIRouter(prefix="/roi", tags=["roi"])


@router.get(
    "/sessions",
    response_model=list[SessionInfo],
    summary="List all recording sessions",
)
async def list_sessions(db: AsyncSession = Depends(get_db)):
    repo = ROIRepository(db)
    rows = await repo.list_sessions()
    return [SessionInfo(**r) for r in rows]


@router.get(
    "/{session_id}",
    response_model=ROIListResponse,
    summary="Get paginated ROI records for a session",
)
async def get_roi(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = ROIRepository(db)
    total = await repo.count_by_session(session_id)
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ROI data for session '{session_id}'.",
        )
    records = await repo.get_by_session(session_id, limit=limit, offset=offset)
    return ROIListResponse(
        session_id=session_id,
        total=total,
        records=[ROIRecordOut.from_orm_record(r) for r in records],
    )


@router.get(
    "/{session_id}/latest",
    response_model=ROIRecordOut,
    summary="Get the most recent ROI record for a session",
)
async def get_latest_roi(session_id: str, db: AsyncSession = Depends(get_db)):
    repo = ROIRepository(db)
    records = await repo.get_by_session(session_id, limit=1, offset=0)
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ROI data for session '{session_id}'.",
        )
    # return the last inserted by re-fetching with reverse order
    all_records = await repo.get_by_session(session_id, limit=1000, offset=0)
    latest = all_records[-1]
    return ROIRecordOut.from_orm_record(latest)
