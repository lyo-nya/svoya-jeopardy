"""Main routes for New Year Jeopardy Party Game."""

from flask import redirect, url_for
from app.routes import main_bp


@main_bp.route("/")
def index():
    """Entry point - redirect based on game state."""
    # TODO: Implement proper routing based on game state
    return redirect(url_for("setup.setup_overview"))


@main_bp.route("/scores")
def scores():
    """Display current scores."""
    # TODO: Implement scores page
    return "Scores page - coming soon"


@main_bp.route("/results")
def results():
    """Display final results."""
    # TODO: Implement results page
    return "Results page - coming soon"


@main_bp.route("/lobby")
def lobby():
    """Display lobby page."""
    # TODO: Implement lobby page
    return "Lobby page - coming soon"
