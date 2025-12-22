"""Flask configuration for New Year Jeopardy Party Game."""

import os
from pathlib import Path

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Railway volume mount path (if using persistent storage)
RAILWAY_VOLUME_PATH = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "")


def get_data_path(subdir: str) -> str:
    """Get path for data storage, preferring Railway volume if available."""
    if RAILWAY_VOLUME_PATH:
        path = Path(RAILWAY_VOLUME_PATH) / subdir
    else:
        path = BASE_DIR / subdir
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def get_database_uri() -> str:
    """Get database URI, preferring Railway volume if available."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    db_path = get_data_path("data") + "/jeopardy.db"
    return f"sqlite:///{db_path}"


def get_upload_folder() -> str:
    """Get upload folder path."""
    return os.environ.get("UPLOAD_FOLDER", get_data_path("uploads"))


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = get_upload_folder()
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max upload
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
