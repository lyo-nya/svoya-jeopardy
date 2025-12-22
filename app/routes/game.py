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
        flash("Только хост может начать игру", "error")
        return redirect(url_for("main.lobby"))
    
    # Check if already started
    if game.status != "setup":
        flash("Игра уже началась", "error")
        return redirect(url_for("main.lobby"))
    
    # Check if we have at least 1 player with questions
    players = list(game.players.all())
    players_with_questions = [p for p in players if p.questions_submitted]
    
    if len(players_with_questions) < 1:
        flash("Нужен хотя бы один игрок с вопросами для начала игры", "error")
        return redirect(url_for("main.lobby"))
    
    try:
        # Create Round records only for players who have submitted questions
        for i, p in enumerate(players_with_questions):
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
        
        flash("🎮 Игра началась! Выберите чьи вопросы играть первыми.", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error starting game: {e}")
        flash("Произошла ошибка. Попробуйте ещё раз.", "error")
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
        flash("Только хост может выбирать раунды", "error")
        return redirect(url_for("game.select_round"))
    
    # Find the round for this player
    round_record = Round.query.filter_by(game_id=game.id, player_id=player_id, status="pending").first()
    
    if not round_record:
        flash("Неверный выбор раунда", "error")
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
    
    flash(f"Играем вопросы {round_record.player.name}!", "success")
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
        flash("Неверный вопрос для текущего раунда", "error")
        return redirect(url_for("game.game_board"))
    
    # Check if already answered
    if question.is_answered:
        flash("Этот вопрос уже отвечен", "error")
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
        flash("Только хост может начислять очки", "error")
        return redirect(url_for("game.game_board"))
    
    question = Question.query.get_or_404(question_id)
    
    # Check if already answered
    if question.is_answered:
        flash("Этот вопрос уже отвечен", "error")
        return redirect(url_for("game.game_board"))
    
    # Verify the player exists and is in this game
    target_player = Player.query.filter_by(id=player_id, game_id=game.id).first()
    if not target_player:
        flash("Неверный игрок", "error")
        return redirect(url_for("game.game_board"))
    
    # Verify player is not sitting out
    current_round = Round.query.get(game.current_round_id) if game.current_round_id else None
    if not current_round:
        flash("Нет активного раунда", "error")
        return redirect(url_for("game.select_round"))
    
    if target_player.id == current_round.player_id:
        flash("Нельзя начислить очки игроку, который пропускает раунд", "error")
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
        flash(f"+{question.points} очков игроку {target_player.name}!", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error awarding points: {e}")
        flash("Произошла ошибка. Попробуйте ещё раз.", "error")
    
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
        flash("Только хост может пропускать вопросы", "error")
        return redirect(url_for("game.game_board"))
    
    question = Question.query.get_or_404(question_id)
    
    # Check if already answered
    if question.is_answered:
        flash("Этот вопрос уже отвечен", "error")
        return redirect(url_for("game.game_board"))
    
    try:
        question.is_answered = True
        question.answered_by_player_id = None
        db.session.commit()
        flash("Вопрос пропущен — никто не получил очки", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error skipping question: {e}")
        flash("Произошла ошибка. Попробуйте ещё раз.", "error")
    
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
        flash("Только хост может переходить к следующему раунду", "error")
        return redirect(url_for("game.game_board"))
    
    current_round = Round.query.get(game.current_round_id) if game.current_round_id else None
    
    if not current_round:
        flash("Нет активного раунда для завершения", "error")
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
            flash("🎉 Все раунды сыграны! Игра окончена!", "success")
            return redirect(url_for("main.results"))
        
        flash(f"Раунд {current_round.round_number} завершён!", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error completing round: {e}")
        flash("Произошла ошибка. Попробуйте ещё раз.", "error")
    
    return redirect(url_for("game.select_round"))


@game_bp.route("/reset", methods=["POST"])
@telegram_required
def reset_game():
    """Reset the game to allow starting fresh."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Only host can reset
    if not player.is_host:
        flash("Только хост может перезапустить игру", "error")
        return redirect(url_for("main.results"))
    
    try:
        # Delete all round scores
        RoundScore.query.filter(
            RoundScore.round_id.in_(
                db.session.query(Round.id).filter_by(game_id=game.id)
            )
        ).delete(synchronize_session=False)
        
        # Delete all rounds
        Round.query.filter_by(game_id=game.id).delete(synchronize_session=False)
        
        # Reset all questions to unanswered
        Question.query.filter(
            Question.category_id.in_(
                db.session.query(Category.id).filter(
                    Category.player_id.in_(
                        db.session.query(Player.id).filter_by(game_id=game.id)
                    )
                )
            )
        ).update(
            {Question.is_answered: False, Question.answered_by_player_id: None},
            synchronize_session=False
        )
        
        # Reset player scores
        Player.query.filter_by(game_id=game.id).update(
            {Player.total_score: 0},
            synchronize_session=False
        )
        
        # Reset game status
        game.status = "setup"
        game.current_round_id = None
        
        db.session.commit()
        flash("🔄 Игра перезапущена! Можете начать заново.", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error resetting game: {e}")
        flash("Произошла ошибка. Попробуйте ещё раз.", "error")
        return redirect(url_for("main.results"))
    
    return redirect(url_for("main.lobby"))
