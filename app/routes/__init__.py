"""Route blueprints for the Jeopardy game."""

from flask import Blueprint

main_bp = Blueprint("main", __name__)
setup_bp = Blueprint("setup", __name__)
game_bp = Blueprint("game", __name__)
webhook_bp = Blueprint("webhook", __name__)

from app.routes import game, main, setup, webhook  # noqa: E402, F401
