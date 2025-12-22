"""Flask configuration."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FLY_VOLUME_PATH = os.environ.get("FLY_VOLUME_PATH", "/data")


def _get_data_path(subdir: str) -> Path:
    """Get path for data storage, preferring Fly.io volume if available."""
    if os.environ.get("FLY_APP_NAME"):
        path = Path(FLY_VOLUME_PATH) / subdir
    else:
        path = BASE_DIR / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_database_uri() -> str:
    """Get database URI, preferring Fly.io volume if available."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    db_path = _get_data_path("data") / "jeopardy.db"
    return f"sqlite:///{db_path}"


def _get_app_url() -> str:
    """Get the application URL, deriving from Fly.io app name if not set."""
    if app_url := os.environ.get("APP_URL", ""):
        return app_url.rstrip("/")
    if fly_app_name := os.environ.get("FLY_APP_NAME", ""):
        return f"https://{fly_app_name}.fly.dev"
    return ""


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    APP_URL = _get_app_url()

    SQLALCHEMY_DATABASE_URI = _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = str(os.environ.get("UPLOAD_FOLDER") or _get_data_path("uploads"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
