"""Route blueprints for New Year Jeopardy Party Game."""

from flask import Blueprint

# Create blueprints
main_bp = Blueprint("main", __name__)
setup_bp = Blueprint("setup", __name__)
game_bp = Blueprint("game", __name__)

# Import routes to register them with blueprints
from app.routes import main, setup, game
