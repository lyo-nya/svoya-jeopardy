"""Flask application factory for New Year Jeopardy Party Game."""

import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Load configuration
    from app.config import config
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config[config_name])

    # Ensure instance folder exists
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    # Ensure uploads folder exists
    uploads_path = os.path.join(os.path.dirname(app.instance_path), "uploads")
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path)

    # Initialize extensions
    db.init_app(app)

    # Import models so they are registered with SQLAlchemy
    from app import models  # noqa: F401

    # Register blueprints
    from app.routes import main_bp, setup_bp, game_bp, webhook_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(setup_bp, url_prefix="/setup")
    app.register_blueprint(game_bp, url_prefix="/game")
    app.register_blueprint(webhook_bp, url_prefix="/webhook")

    # Register error handlers
    register_error_handlers(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


def register_error_handlers(app):
    """Register custom error handlers."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Roll back any failed database transactions
        return render_template("errors/500.html"), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/404.html"), 403  # Reuse 404 template for simplicity
