"""
API-level tests using httpx AsyncClient with an in-memory SQLite DB.
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from PIL import Image
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.db.session import Base, get_db
from app.main import app
from app.services.face_detection import DetectionResult


# ---------------------------------------------------------------------------
# Test DB setup (SQLite in-memory)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def test_db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        from app.models import roi  # noqa – register models
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture()
async def client(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _make_jpeg_bytes(w=160, h=120) -> bytes:
    img = Image.new("RGB", (w, h), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Ingest endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.api.ingest.process_frame")
async def test_ingest_frame_no_face(mock_pf, client):
    mock_pf.return_value = (_make_jpeg_bytes(), None)
    jpeg = _make_jpeg_bytes()
    resp = await client.post(
        "/api/v1/ingest/test-session/frame?frame_index=0",
        files={"file": ("frame.jpg", jpeg, "image/jpeg")},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["face_detected"] is False


@pytest.mark.asyncio
@patch("app.api.ingest.process_frame")
async def test_ingest_frame_with_face(mock_pf, client):
    det = DetectionResult(
        found=True, x_norm=0.1, y_norm=0.1, width_norm=0.3, height_norm=0.3,
        x_px=16, y_px=12, width_px=48, height_px=36,
        confidence=0.9, frame_width=160, frame_height=120,
    )
    mock_pf.return_value = (_make_jpeg_bytes(), det)
    jpeg = _make_jpeg_bytes()
    resp = await client.post(
        "/api/v1/ingest/test-session-face/frame?frame_index=0",
        files={"file": ("frame.jpg", jpeg, "image/jpeg")},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["face_detected"] is True
    assert data["confidence"] == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_ingest_wrong_content_type(client):
    resp = await client.post(
        "/api/v1/ingest/sess/frame",
        files={"file": ("frame.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415


# ---------------------------------------------------------------------------
# ROI endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_roi_not_found(client):
    resp = await client.get("/api/v1/roi/nonexistent-session")
    assert resp.status_code == 404


@pytest.mark.asyncio
@patch("app.api.ingest.process_frame")
async def test_roi_after_ingest(mock_pf, client):
    det = DetectionResult(
        found=True, x_norm=0.2, y_norm=0.2, width_norm=0.3, height_norm=0.3,
        x_px=32, y_px=24, width_px=48, height_px=36,
        confidence=0.85, frame_width=160, frame_height=120,
    )
    mock_pf.return_value = (_make_jpeg_bytes(), det)
    jpeg = _make_jpeg_bytes()

    # Ingest a frame
    await client.post(
        "/api/v1/ingest/roi-test/frame?frame_index=0",
        files={"file": ("f.jpg", jpeg, "image/jpeg")},
    )

    # Fetch ROI
    resp = await client.get("/api/v1/roi/roi-test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    record = body["records"][0]
    assert record["bbox"]["x_px"] == 32


@pytest.mark.asyncio
async def test_sessions_list_empty(client):
    resp = await client.get("/api/v1/roi/sessions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
