"""Game routes for gameplay control."""

from flask import render_template
from app.routes import game_bp


@game_bp.route("/")
def game_board():
    """Display the main game board."""
    # TODO: Implement game board
    return "Game board - coming soon"


@game_bp.route("/start", methods=["POST"])
def start_game():
    """Start the game."""
    # TODO: Implement game start
    return "Start game - coming soon"


@game_bp.route("/select-round", methods=["GET"])
def select_round():
    """Display round selection page."""
    # TODO: Implement round selection
    return "Select round - coming soon"


@game_bp.route("/select-round/<int:player_id>", methods=["POST"])
def set_round(player_id):
    """Set the current round to a player's question set."""
    # TODO: Implement round setting
    return f"Set round to player {player_id} - coming soon"


@game_bp.route("/question/<int:question_id>", methods=["GET"])
def show_question(question_id):
    """Display a question."""
    # TODO: Implement question display
    return f"Question {question_id} - coming soon"


@game_bp.route("/reveal/<int:question_id>", methods=["POST"])
def reveal_answer(question_id):
    """Reveal the answer to a question."""
    # TODO: Implement answer reveal
    return f"Reveal answer for {question_id} - coming soon"


@game_bp.route("/award/<int:question_id>/<int:player_id>", methods=["POST"])
def award_points(question_id, player_id):
    """Award points to a player."""
    # TODO: Implement point awarding
    return f"Award points for question {question_id} to player {player_id} - coming soon"


@game_bp.route("/next-round", methods=["POST"])
def next_round():
    """Proceed to the next round."""
    # TODO: Implement next round
    return "Next round - coming soon"
