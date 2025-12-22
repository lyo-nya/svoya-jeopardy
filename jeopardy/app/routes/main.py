"""Main routes for New Year Jeopardy Party Game."""

from flask import redirect, url_for, render_template, g
from app.routes import main_bp
from app.services import (
    telegram_required,
    get_chat_id,
    get_or_create_game,
    get_or_create_player,
    get_current_player,
)


@main_bp.route("/")
@telegram_required
def index():
    """Entry point - redirect based on game state."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Redirect based on game status
    if game.status == "completed":
        return redirect(url_for("main.results"))
    elif game.status == "in_progress":
        return redirect(url_for("game.game_board"))
    else:
        # Setup phase - go to question submission
        return redirect(url_for("setup.setup_overview"))


@main_bp.route("/lobby")
@telegram_required
def lobby():
    """Display lobby page."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Get all players in this game
    players = list(game.players.order_by("id").all())
    
    # Count ready players
    ready_count = sum(1 for p in players if p.questions_submitted)
    total_count = len(players)
    
    # Can start if we have 5 players and all have submitted
    can_start = total_count >= 5 and ready_count >= 5 and game.status == "setup"
    
    return render_template(
        "lobby.html",
        game=game,
        player=player,
        players=players,
        ready_count=ready_count,
        total_count=total_count,
        can_start=can_start,
        is_host=player.is_host,
    )


@main_bp.route("/scores")
@telegram_required
def scores():
    """Display current scores."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Get all players with their scores
    players = list(game.players.order_by("total_score").all())
    players.reverse()  # Highest first
    
    return render_template(
        "scores.html",
        game=game,
        player=player,
        players=players,
    )


@main_bp.route("/results")
@telegram_required
def results():
    """Display final results."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    if game.status != "completed":
        return redirect(url_for("main.lobby"))
    
    # Get all players sorted by score
    players = list(game.players.order_by("total_score").all())
    players.reverse()  # Highest first
    
    # Get all rounds for breakdown
    rounds = list(game.rounds.order_by("round_number").all())
    
    return render_template(
        "results.html",
        game=game,
        player=player,
        players=players,
        rounds=rounds,
    )
