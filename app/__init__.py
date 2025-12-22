"""Flask application factory for the Jeopardy game."""

from __future__ import annotations

import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    from app.config import config
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config[config_name])

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(app.instance_path), "uploads"), exist_ok=True)

    db.init_app(app)

    from app import models  # noqa: F401

    from app.routes import game_bp, main_bp, setup_bp, webhook_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(setup_bp, url_prefix="/setup")
    app.register_blueprint(game_bp, url_prefix="/game")
    app.register_blueprint(webhook_bp, url_prefix="/webhook")

    _register_error_handlers(app)

    with app.app_context():
        db.create_all()

    return app


def _register_error_handlers(app: Flask) -> None:
    """Register custom error handlers."""

    @app.errorhandler(404)
    def not_found_error(error: Exception) -> tuple[str, int]:
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error: Exception) -> tuple[str, int]:
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden_error(error: Exception) -> tuple[str, int]:
        return render_template("errors/404.html"), 403
