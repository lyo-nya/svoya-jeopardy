"""Flask configuration for New Year Jeopardy Party Game."""

import os
from pathlib import Path

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Fly.io volume mount path (if using persistent storage)
# Fly.io mounts volumes to a specified path in fly.toml (default: /data)
FLY_VOLUME_PATH = os.environ.get("FLY_VOLUME_PATH", "/data")


def get_data_path(subdir: str) -> str:
    """Get path for data storage, preferring Fly.io volume if available."""
    # Check if running on Fly.io (FLY_APP_NAME is set automatically)
    if os.environ.get("FLY_APP_NAME"):
        path = Path(FLY_VOLUME_PATH) / subdir
    else:
        path = BASE_DIR / subdir
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def get_database_uri() -> str:
    """Get database URI, preferring Fly.io volume if available."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    db_path = get_data_path("data") + "/jeopardy.db"
    return f"sqlite:///{db_path}"


def get_upload_folder() -> str:
    """Get upload folder path."""
    return os.environ.get("UPLOAD_FOLDER", get_data_path("uploads"))


def get_app_url() -> str:
    """Get the application URL, deriving from Fly.io app name if not explicitly set."""
    # First check for explicit APP_URL
    app_url = os.environ.get("APP_URL", "")
    if app_url:
        return app_url.rstrip("/")
    
    # Try to derive from Fly.io app name
    fly_app_name = os.environ.get("FLY_APP_NAME", "")
    if fly_app_name:
        return f"https://{fly_app_name}.fly.dev"
    
    return ""


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    APP_URL = get_app_url()  # Base URL for the web app (auto-derived on Fly.io)

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
