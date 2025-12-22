"""Main routes for New Year Jeopardy Party Game."""

from flask import redirect, url_for, render_template, g, current_app, jsonify, request
from app.routes import main_bp
from app.services import (
    telegram_required,
    get_chat_id,
    get_or_create_game,
    get_or_create_player,
    get_current_player,
)


@main_bp.route("/")
def entry():
    """
    Unauthenticated entry point for Telegram Mini App.
    
    This page loads without authentication so the Telegram SDK JavaScript
    can initialize and provide the initData. The JavaScript then redirects
    to the authenticated /app route with the initData as a query parameter.
    """
    # Check if init_data is already provided (e.g., from a redirect)
    init_data = request.args.get("init_data")
    if init_data:
        # If we already have init_data, redirect to the authenticated route
        return redirect(url_for("main.index", init_data=init_data))
    
    # Otherwise, render the entry page that will get init_data from Telegram SDK
    return render_template("entry.html")


@main_bp.route("/app")
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


@main_bp.route("/health")
def health_check():
    """Health check endpoint for monitoring and debugging."""
    bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    app_url = current_app.config.get("APP_URL", "")
    
    return jsonify({
        "status": "ok",
        "config": {
            "bot_token_configured": bool(bot_token),
            "bot_token_length": len(bot_token) if bot_token else 0,
            "app_url_configured": bool(app_url),
            "app_url": app_url if app_url else "NOT SET",
        }
    })


@main_bp.route("/debug/init")
def debug_init():
    """Debug endpoint to check init_data parsing."""
    init_data = request.args.get("init_data", "")
    
    if not init_data:
        return jsonify({
            "error": "No init_data provided",
            "hint": "This endpoint is for debugging Telegram WebApp authentication"
        })
    
    # Try to parse without validation
    from urllib.parse import unquote
    pairs = {}
    for part in init_data.split("&"):
        if "=" in part:
            key, value = part.split("=", 1)
            pairs[key] = unquote(value)[:50] + "..." if len(unquote(value)) > 50 else unquote(value)
    
    return jsonify({
        "parsed_keys": list(pairs.keys()),
        "has_hash": "hash" in pairs,
        "has_user": "user" in pairs,
        "has_chat": "chat" in pairs,
        "has_chat_instance": "chat_instance" in pairs,
        "sample_values": {k: v for k, v in pairs.items() if k not in ["hash"]}
    })
