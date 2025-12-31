"""Game routes for gameplay control."""

from __future__ import annotations

from flask import current_app, flash, g, redirect, render_template, url_for
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.constants import POINT_VALUES
from app.models import Category, Player, Question, Round, RoundScore
from app.routes import game_bp
from app.services import game_context_required, telegram_required


def _require_host(player: Player) -> str | None:
    """Return error message if player is not the host, None otherwise."""
    return "Только хост может выполнить это действие" if not player.is_host else None


def _require_game_status(game, required_status: str, redirect_url: str):
    """Redirect if game is not in required status."""
    if game.status != required_status:
        return redirect(url_for(redirect_url))
    return None


@game_bp.route("/")
@telegram_required
@game_context_required
def game_board():
    """Display the main game board."""
    game, player = g.game, g.player

    if game.status != "in_progress":
        return redirect(url_for("main.lobby"))

    if not game.current_round_id:
        return redirect(url_for("game.select_round"))

    current_round = Round.query.get(game.current_round_id)
    if not current_round:
        return redirect(url_for("game.select_round"))

    sitting_out_player = current_round.player
    categories = list(
        Category.query.filter_by(player_id=sitting_out_player.id)
        .order_by(Category.position)
        .all()
    )
    playing_players = [p for p in game.players if p.id != sitting_out_player.id]
    round_scores = {rs.player_id: rs.score for rs in current_round.round_scores}

    # Only check questions with valid point values and actual content (displayed on the board)
    all_answered = all(
        q.is_answered
        for cat in categories
        for q in cat.questions
        if q.points in POINT_VALUES and q.text and q.text != "???"
    )

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
@game_context_required
def start_game():
    """Start the game."""
    game, player = g.game, g.player

    if not player.is_host:
        flash("Только хост может начать игру", "error")
        return redirect(url_for("main.lobby"))

    if game.status != "setup":
        flash("Игра уже началась", "error")
        return redirect(url_for("main.lobby"))

    players_with_questions = [p for p in game.players.all() if p.questions_submitted]
    if not players_with_questions:
        flash("Нужен хотя бы один игрок с вопросами для начала игры", "error")
        return redirect(url_for("main.lobby"))

    try:
        for i, p in enumerate(players_with_questions):
            db.session.add(Round(
                game_id=game.id,
                player_id=p.id,
                round_number=i + 1,
                status="pending",
            ))

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
@game_context_required
def select_round():
    """Display round selection page."""
    game, player = g.game, g.player

    if game.status != "in_progress":
        return redirect(url_for("main.lobby"))

    pending_rounds = Round.query.filter_by(game_id=game.id, status="pending").all()
    available_players = [r.player for r in pending_rounds]

    if not available_players:
        game.status = "completed"
        db.session.commit()
        return redirect(url_for("main.results"))

    completed_rounds = Round.query.filter_by(
        game_id=game.id, status="completed"
    ).order_by(Round.round_number).all()

    players_by_score = list(game.players.order_by(Player.total_score.desc()).all())

    # Get current in-progress round if any
    current_round = Round.query.get(game.current_round_id) if game.current_round_id else None

    return render_template(
        "select_round.html",
        game=game,
        player=player,
        available_players=available_players,
        completed_rounds=completed_rounds,
        players_by_score=players_by_score,
        is_host=player.is_host,
        current_round=current_round,
    )


@game_bp.route("/select-round/<int:player_id>", methods=["POST"])
@telegram_required
@game_context_required
def set_round(player_id: int):
    """Set the current round to a player's question set."""
    game, player = g.game, g.player

    if not player.is_host:
        flash("Только хост может выбирать раунды", "error")
        return redirect(url_for("game.select_round"))

    round_record = Round.query.filter_by(
        game_id=game.id, player_id=player_id, status="pending"
    ).first()

    if not round_record:
        flash("Неверный выбор раунда", "error")
        return redirect(url_for("game.select_round"))

    round_record.status = "in_progress"
    game.current_round_id = round_record.id

    for p in game.players:
        if p.id != player_id:
            db.session.add(RoundScore(round_id=round_record.id, player_id=p.id, score=0))

    db.session.commit()
    flash(f"Играем вопросы {round_record.player.name}!", "success")
    return redirect(url_for("game.game_board"))


@game_bp.route("/question/<int:question_id>", methods=["GET"])
@telegram_required
@game_context_required
def show_question(question_id: int):
    """Display a question."""
    game, player = g.game, g.player

    question = Question.query.get_or_404(question_id)
    category = question.category

    current_round = Round.query.get(game.current_round_id) if game.current_round_id else None
    if not current_round or category.player_id != current_round.player_id:
        flash("Неверный вопрос для текущего раунда", "error")
        return redirect(url_for("game.game_board"))

    if question.is_answered:
        flash("Этот вопрос уже отвечен", "error")
        return redirect(url_for("game.game_board"))

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
    return redirect(url_for("game.show_question", question_id=question_id, revealed="1"))


@game_bp.route("/award/<int:question_id>/<int:player_id>", methods=["POST"])
@telegram_required
@game_context_required
def award_points(question_id: int, player_id: int):
    """Award points to a player for answering correctly."""
    game, player = g.game, g.player

    if not player.is_host:
        flash("Только хост может начислять очки", "error")
        return redirect(url_for("game.game_board"))

    question = Question.query.get_or_404(question_id)

    if question.is_answered:
        flash("Этот вопрос уже отвечен", "error")
        return redirect(url_for("game.game_board"))

    target_player = Player.query.filter_by(id=player_id, game_id=game.id).first()
    if not target_player:
        flash("Неверный игрок", "error")
        return redirect(url_for("game.game_board"))

    current_round = Round.query.get(game.current_round_id) if game.current_round_id else None
    if not current_round:
        flash("Нет активного раунда", "error")
        return redirect(url_for("game.select_round"))

    if target_player.id == current_round.player_id:
        flash("Нельзя начислить очки игроку, который пропускает раунд", "error")
        return redirect(url_for("game.show_question", question_id=question_id, revealed="1"))

    try:
        question.is_answered = True
        question.answered_by_player_id = player_id

        round_score = RoundScore.query.filter_by(
            round_id=current_round.id, player_id=player_id
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
@game_context_required
def skip_question(question_id: int):
    """Skip a question without awarding points."""
    player = g.player

    if not player.is_host:
        flash("Только хост может пропускать вопросы", "error")
        return redirect(url_for("game.game_board"))

    question = Question.query.get_or_404(question_id)

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
@game_context_required
def next_round():
    """Complete current round and proceed to next."""
    game, player = g.game, g.player

    if not player.is_host:
        flash("Только хост может переходить к следующему раунду", "error")
        return redirect(url_for("game.game_board"))

    current_round = Round.query.get(game.current_round_id) if game.current_round_id else None
    if not current_round:
        flash("Нет активного раунда для завершения", "error")
        return redirect(url_for("game.select_round"))

    try:
        for rs in current_round.round_scores:
            rs.player.total_score += rs.score

        current_round.status = "completed"
        game.current_round_id = None
        db.session.commit()

        pending_count = Round.query.filter_by(game_id=game.id, status="pending").count()
        if pending_count == 0:
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
@game_context_required
def reset_game():
    """Reset the game to allow starting fresh."""
    game, player = g.game, g.player

    if not player.is_host:
        flash("Только хост может перезапустить игру", "error")
        return redirect(url_for("main.results"))

    try:
        round_ids = db.session.query(Round.id).filter_by(game_id=game.id)
        RoundScore.query.filter(RoundScore.round_id.in_(round_ids)).delete(synchronize_session=False)
        Round.query.filter_by(game_id=game.id).delete(synchronize_session=False)

        player_ids = db.session.query(Player.id).filter_by(game_id=game.id)
        category_ids = db.session.query(Category.id).filter(Category.player_id.in_(player_ids))
        Question.query.filter(Question.category_id.in_(category_ids)).update(
            {Question.is_answered: False, Question.answered_by_player_id: None},
            synchronize_session=False,
        )

        Player.query.filter_by(game_id=game.id).update(
            {Player.total_score: 0}, synchronize_session=False
        )

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
