"""Game routes for gameplay control."""

from flask import render_template, redirect, url_for, flash, g, current_app
from sqlalchemy.exc import SQLAlchemyError
from app.routes import game_bp
from app import db
from app.models import Game, Player, Round, RoundScore, Category, Question
from app.services import (
    telegram_required,
    host_required,
    get_chat_id,
    get_or_create_game,
    get_or_create_player,
)


@game_bp.route("/")
@telegram_required
def game_board():
    """Display the main game board."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    if game.status != "in_progress":
        return redirect(url_for("main.lobby"))
    
    # Get current round
    current_round = Round.query.get(game.current_round_id) if game.current_round_id else None
    
    if not current_round:
        return redirect(url_for("game.select_round"))
    
    # Get the player whose questions are being played (sitting out)
    sitting_out_player = current_round.player
    
    # Get categories and questions for this round
    categories = list(Category.query.filter_by(player_id=sitting_out_player.id).order_by(Category.position).all())
    
    # Get all players except the one sitting out, for scoring
    playing_players = [p for p in game.players if p.id != sitting_out_player.id]
    
    # Get round scores
    round_scores = {rs.player_id: rs.score for rs in current_round.round_scores}
    
    # Check if all questions answered
    all_answered = True
    for cat in categories:
        for q in cat.questions:
            if not q.is_answered:
                all_answered = False
                break
    
    return render_template(
        "game.html",
        game=game,
        player=player,
        current_round=current_round,
        sitting_out_player=sitting_out_player,
        categories=categories,
        playing_players=playing_players,
        round_scores=round_scores,
        all_answered=all_answered,
        is_host=player.is_host,
    )


@game_bp.route("/start", methods=["POST"])
@telegram_required
def start_game():
    """Start the game."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Only host can start
    if not player.is_host:
        flash("Only the host can start the game", "error")
        return redirect(url_for("main.lobby"))
    
    # Check if already started
    if game.status != "setup":
        flash("Game has already started", "error")
        return redirect(url_for("main.lobby"))
    
    # Check if we have enough players
    players = list(game.players.all())
    if len(players) < 5:
        flash(f"Need 5 players to start. Currently have {len(players)}.", "error")
        return redirect(url_for("main.lobby"))
    
    # Check if all players submitted questions
    not_ready = [p for p in players if not p.questions_submitted]
    if not_ready:
        names = ", ".join(p.name for p in not_ready)
        flash(f"These players haven't submitted questions: {names}", "error")
        return redirect(url_for("main.lobby"))
    
    try:
        # Create Round records for each player
        for i, p in enumerate(players):
            round_record = Round(
                game_id=game.id,
                player_id=p.id,
                round_number=i + 1,
                status="pending",
            )
            db.session.add(round_record)
        
        # Update game status
        game.status = "in_progress"
        db.session.commit()
        
        flash("🎮 Game started! Select whose questions to play first.", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error starting game: {e}")
        flash("An error occurred starting the game. Please try again.", "error")
        return redirect(url_for("main.lobby"))
    
    return redirect(url_for("game.select_round"))


@game_bp.route("/select-round", methods=["GET"])
@telegram_required
def select_round():
    """Display round selection page."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    if game.status != "in_progress":
        return redirect(url_for("main.lobby"))
    
    # Get rounds that haven't been played yet
    pending_rounds = Round.query.filter_by(game_id=game.id, status="pending").all()
    available_players = [r.player for r in pending_rounds]
    
    # Get completed rounds
    completed_rounds = Round.query.filter_by(game_id=game.id, status="completed").order_by(Round.round_number).all()
    
    # Get players sorted by score
    players_by_score = list(game.players.order_by(Player.total_score.desc()).all())
    
    # If no more rounds, game is complete
    if not available_players:
        game.status = "completed"
        db.session.commit()
        return redirect(url_for("main.results"))
    
    return render_template(
        "select_round.html",
        game=game,
        player=player,
        available_players=available_players,
        completed_rounds=completed_rounds,
        players_by_score=players_by_score,
        is_host=player.is_host,
    )


@game_bp.route("/select-round/<int:player_id>", methods=["POST"])
@telegram_required
def set_round(player_id: int):
    """Set the current round to a player's question set."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Only host can select round
    if not player.is_host:
        flash("Only the host can select rounds", "error")
        return redirect(url_for("game.select_round"))
    
    # Find the round for this player
    round_record = Round.query.filter_by(game_id=game.id, player_id=player_id, status="pending").first()
    
    if not round_record:
        flash("Invalid round selection", "error")
        return redirect(url_for("game.select_round"))
    
    # Set as current round
    round_record.status = "in_progress"
    game.current_round_id = round_record.id
    
    # Create RoundScore records for all players except the one sitting out
    for p in game.players:
        if p.id != player_id:
            round_score = RoundScore(
                round_id=round_record.id,
                player_id=p.id,
                score=0,
            )
            db.session.add(round_score)
    
    db.session.commit()
    
    flash(f"Playing {round_record.player.name}'s questions!", "success")
    return redirect(url_for("game.game_board"))


@game_bp.route("/question/<int:question_id>", methods=["GET"])
@telegram_required
def show_question(question_id: int):
    """Display a question."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    question = Question.query.get_or_404(question_id)
    category = question.category
    
    # Verify question belongs to current round
    current_round = Round.query.get(game.current_round_id) if game.current_round_id else None
    if not current_round or category.player_id != current_round.player_id:
        flash("Invalid question for current round", "error")
        return redirect(url_for("game.game_board"))
    
    # Check if already answered
    if question.is_answered:
        flash("This question has already been answered", "error")
        return redirect(url_for("game.game_board"))
    
    # Get players who can receive points (not the question author)
    sitting_out_player = category.player
    eligible_players = [p for p in game.players if p.id != sitting_out_player.id]
    
    return render_template(
        "question.html",
        game=game,
        player=player,
        question=question,
        category=category,
        eligible_players=eligible_players,
        is_host=player.is_host,
    )


@game_bp.route("/reveal/<int:question_id>", methods=["POST"])
@telegram_required
def reveal_answer(question_id: int):
    """Reveal the answer to a question."""
    # Just redirect back to question page with reveal flag
    return redirect(url_for("game.show_question", question_id=question_id, revealed="1"))


@game_bp.route("/award/<int:question_id>/<int:player_id>", methods=["POST"])
@telegram_required
def award_points(question_id: int, player_id: int):
    """Award points to a player."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Only host can award points
    if not player.is_host:
        flash("Only the host can award points", "error")
        return redirect(url_for("game.game_board"))
    
    question = Question.query.get_or_404(question_id)
    
    # Check if already answered
    if question.is_answered:
        flash("This question has already been answered", "error")
        return redirect(url_for("game.game_board"))
    
    # Verify the player exists and is in this game
    target_player = Player.query.filter_by(id=player_id, game_id=game.id).first()
    if not target_player:
        flash("Invalid player", "error")
        return redirect(url_for("game.game_board"))
    
    # Verify player is not sitting out
    current_round = Round.query.get(game.current_round_id) if game.current_round_id else None
    if not current_round:
        flash("No active round", "error")
        return redirect(url_for("game.select_round"))
    
    if target_player.id == current_round.player_id:
        flash("Cannot award points to the player sitting out", "error")
        return redirect(url_for("game.show_question", question_id=question_id, revealed="1"))
    
    try:
        # Mark question as answered
        question.is_answered = True
        question.answered_by_player_id = player_id
        
        # Update round score
        round_score = RoundScore.query.filter_by(
            round_id=current_round.id,
            player_id=player_id,
        ).first()
        if round_score:
            round_score.score += question.points
        
        db.session.commit()
        flash(f"Awarded {question.points} points to {target_player.name}!", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error awarding points: {e}")
        flash("An error occurred. Please try again.", "error")
    
    return redirect(url_for("game.game_board"))


@game_bp.route("/skip/<int:question_id>", methods=["POST"])
@telegram_required
def skip_question(question_id: int):
    """Skip a question without awarding points."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Only host can skip
    if not player.is_host:
        flash("Only the host can skip questions", "error")
        return redirect(url_for("game.game_board"))
    
    question = Question.query.get_or_404(question_id)
    
    # Check if already answered
    if question.is_answered:
        flash("This question has already been answered", "error")
        return redirect(url_for("game.game_board"))
    
    try:
        question.is_answered = True
        question.answered_by_player_id = None
        db.session.commit()
        flash("Question skipped - no points awarded", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error skipping question: {e}")
        flash("An error occurred. Please try again.", "error")
    
    return redirect(url_for("game.game_board"))


@game_bp.route("/next-round", methods=["POST"])
@telegram_required
def next_round():
    """Proceed to the next round."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Only host can advance
    if not player.is_host:
        flash("Only the host can advance rounds", "error")
        return redirect(url_for("game.game_board"))
    
    current_round = Round.query.get(game.current_round_id) if game.current_round_id else None
    
    if not current_round:
        flash("No active round to complete", "error")
        return redirect(url_for("game.select_round"))
    
    try:
        # Add round scores to total scores
        for rs in current_round.round_scores:
            rs.player.total_score += rs.score
        
        # Mark round as completed
        current_round.status = "completed"
        game.current_round_id = None
        db.session.commit()
        
        # Check if there are more rounds
        pending_rounds = Round.query.filter_by(game_id=game.id, status="pending").count()
        if pending_rounds == 0:
            game.status = "completed"
            db.session.commit()
            flash("🎉 All rounds complete! Game over!", "success")
            return redirect(url_for("main.results"))
        
        flash(f"Round {current_round.round_number} complete!", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error completing round: {e}")
        flash("An error occurred. Please try again.", "error")
    
    return redirect(url_for("game.select_round"))
