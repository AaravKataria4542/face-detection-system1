from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Face Detection API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://facedet:facedet@db:5432/facedetdb"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://facedet:facedet@db:5432/facedetdb"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:80", "http://frontend:80"]

    # Streaming
    JPEG_QUALITY: int = 80
    MAX_FRAME_WIDTH: int = 1280
    MAX_FRAME_HEIGHT: int = 720

    # ROI drawing
    ROI_COLOR: tuple[int, int, int] = (0, 255, 0)   # Green in RGB
    ROI_THICKNESS: int = 3
    ROI_LABEL_FONT_SIZE: int = 14

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
