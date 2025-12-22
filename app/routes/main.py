"""Main routes for the Jeopardy game."""

from __future__ import annotations

from flask import current_app, g, jsonify, redirect, render_template, request, url_for

from app.models import Round
from app.routes import main_bp
from app.services import game_context_required, telegram_required


@main_bp.route("/")
def entry():
    """Entry point that initializes Telegram WebApp SDK and redirects to /app."""
    init_data = request.args.get("init_data")
    if init_data:
        return redirect(url_for("main.index", init_data=init_data))
    return render_template("entry.html")


@main_bp.route("/app")
@telegram_required
@game_context_required
def index():
    """Redirect to appropriate page based on game state."""
    game = g.game

    if game.status == "completed":
        return redirect(url_for("main.results"))
    if game.status == "in_progress":
        return redirect(url_for("game.game_board"))
    return redirect(url_for("setup.setup_overview"))


@main_bp.route("/lobby")
@telegram_required
@game_context_required
def lobby():
    """Display lobby page with player list and game status."""
    game, player = g.game, g.player
    players = list(game.players.order_by("id").all())
    ready_count = sum(1 for p in players if p.questions_submitted)

    return render_template(
        "lobby.html",
        game=game,
        player=player,
        players=players,
        ready_count=ready_count,
        total_count=len(players),
        can_start=ready_count >= 1 and game.status == "setup",
        is_host=player.is_host,
    )


@main_bp.route("/scores")
@telegram_required
@game_context_required
def scores():
    """Display current scores."""
    game, player = g.game, g.player
    players = sorted(game.players.all(), key=lambda p: p.total_score, reverse=True)

    current_round = None
    round_scores: dict[int, int] = {}
    sitting_out_player = None

    if game.status == "in_progress" and game.current_round_id:
        current_round = Round.query.get(game.current_round_id)
        if current_round:
            sitting_out_player = current_round.player
            round_scores = {rs.player_id: rs.score for rs in current_round.round_scores}

    completed_rounds = Round.query.filter_by(
        game_id=game.id, status="completed"
    ).order_by(Round.round_number).all()

    return render_template(
        "scores.html",
        game=game,
        player=player,
        players=players,
        current_round=current_round,
        round_scores=round_scores,
        sitting_out_player=sitting_out_player,
        completed_rounds=completed_rounds,
    )


@main_bp.route("/results")
@telegram_required
@game_context_required
def results():
    """Display final game results."""
    game, player = g.game, g.player

    if game.status != "completed":
        return redirect(url_for("main.lobby"))

    players = sorted(game.players.all(), key=lambda p: p.total_score, reverse=True)
    rounds = Round.query.filter_by(game_id=game.id).order_by(Round.round_number).all()

    for r in rounds:
        r.scores_list = list(r.round_scores.all())

    return render_template(
        "results.html",
        game=game,
        player=player,
        players=players,
        rounds=rounds,
    )


@main_bp.route("/health")
def health_check():
    """Health check endpoint for monitoring."""
    bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    app_url = current_app.config.get("APP_URL", "")

    return jsonify({
        "status": "ok",
        "config": {
            "bot_token_configured": bool(bot_token),
            "bot_token_length": len(bot_token) if bot_token else 0,
            "app_url_configured": bool(app_url),
            "app_url": app_url or "NOT SET",
        },
    })


@main_bp.route("/debug/init")
def debug_init():
    """Debug endpoint to inspect init_data parsing."""
    from urllib.parse import unquote

    init_data = request.args.get("init_data", "")
    if not init_data:
        return jsonify({"error": "No init_data provided"})

    pairs = {}
    for part in init_data.split("&"):
        if "=" in part:
            key, value = part.split("=", 1)
            decoded = unquote(value)
            pairs[key] = decoded[:50] + "..." if len(decoded) > 50 else decoded

    return jsonify({
        "parsed_keys": list(pairs.keys()),
        "has_hash": "hash" in pairs,
        "has_user": "user" in pairs,
        "has_chat": "chat" in pairs,
        "has_chat_instance": "chat_instance" in pairs,
        "sample_values": {k: v for k, v in pairs.items() if k != "hash"},
    })
