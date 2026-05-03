"""
Face Detection Streaming API
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.session import init_db
from app.api import ingest, stream, roi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up – initialising database …")
    await init_db()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Real-time face detection API. "
        "Accepts a video feed, detects faces, draws ROI bounding boxes "
        "(Pillow only – no OpenCV), persists ROI data to PostgreSQL, "
        "and streams annotated frames back to clients."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(stream.router, prefix="/api/v1")
app.include_router(roi.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return JSONResponse({"status": "ok", "version": settings.APP_VERSION})


@app.get("/", tags=["root"])
async def root():
    return JSONResponse({"message": "Face Detection API", "docs": "/docs"})
