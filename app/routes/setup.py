"""Setup routes for question submission."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from flask import current_app, flash, g, redirect, render_template, request, send_from_directory, url_for
from PIL import Image
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from app import db
from app.constants import (
    CATEGORIES_PER_PLAYER,
    MAX_ANSWER_TEXT_LENGTH,
    MAX_CATEGORY_NAME_LENGTH,
    MAX_IMAGE_SIZE_BYTES,
    MAX_QUESTION_TEXT_LENGTH,
    POINT_VALUES,
    QUESTIONS_PER_CATEGORY,
)
from app.models import Category, Question
from app.routes import setup_bp
from app.services import game_context_required, telegram_required

if TYPE_CHECKING:
    from werkzeug.datastructures import FileStorage


def _allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def _save_image(file: FileStorage, player_id: int, question_index: int) -> str | None:
    """Save and resize uploaded image. Returns filename or None."""
    if not file or not file.filename or not _allowed_file(file.filename):
        return None

    filename = f"p{player_id}_q{question_index}_{secure_filename(file.filename)}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]

    image = Image.open(file)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    max_size = 1200
    if image.width > max_size or image.height > max_size:
        ratio = min(max_size / image.width, max_size / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    jpeg_filename = filename.rsplit(".", 1)[0] + ".jpg"
    image.save(os.path.join(upload_folder, jpeg_filename), "JPEG", quality=85)
    return jpeg_filename


def _delete_image(image_path: str) -> None:
    """Delete an image file from uploads."""
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], image_path)
    if os.path.exists(full_path):
        os.remove(full_path)


def _get_or_create_category(player_id: int, position: int) -> Category:
    """Get existing category or create a new one."""
    category = Category.query.filter_by(player_id=player_id, position=position).first()
    if not category:
        category = Category(player_id=player_id, position=position, name="")
        db.session.add(category)
        db.session.flush()
    return category


def _update_questions_submitted(player_id: int) -> None:
    """Update the questions_submitted flag based on question count."""
    from app.models import Player
    total = Question.query.join(Category).filter(Category.player_id == player_id).count()
    Player.query.filter_by(id=player_id).update({Player.questions_submitted: total > 0})


def _validate_text_lengths(question_text: str, answer_text: str) -> str | None:
    """Validate question/answer lengths. Returns error message or None."""
    if len(question_text) > MAX_QUESTION_TEXT_LENGTH:
        return f"Вопрос слишком длинный (макс. {MAX_QUESTION_TEXT_LENGTH} символов)"
    if len(answer_text) > MAX_ANSWER_TEXT_LENGTH:
        return f"Ответ слишком длинный (макс. {MAX_ANSWER_TEXT_LENGTH} символов)"
    return None


def _check_file_size(file: FileStorage) -> bool:
    """Check if file size is within limits."""
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    return size <= MAX_IMAGE_SIZE_BYTES


def _save_question(
    category: Category,
    points: int,
    question_text: str,
    answer_text: str,
    player_id: int,
    question_index: int,
    image_file: FileStorage | None = None,
    remove_image: bool = False,
) -> str | None:
    """
    Save or update a question. Returns error message or None on success.
    """
    if not question_text and not answer_text:
        return None

    if question_text and not answer_text:
        answer_text = "???"
    elif answer_text and not question_text:
        question_text = "???"

    error = _validate_text_lengths(question_text, answer_text)
    if error:
        return error

    question = Question.query.filter_by(category_id=category.id, points=points).first()
    if not question:
        question = Question(category_id=category.id, points=points, text="", answer="")
        db.session.add(question)

    question.text = question_text
    question.answer = answer_text

    if remove_image and question.image_path:
        _delete_image(question.image_path)
        question.image_path = None

    if image_file and image_file.filename:
        if not _check_file_size(image_file):
            return "Картинка слишком большая (макс. 5МБ)"
        image_path = _save_image(image_file, player_id, question_index)
        if image_path:
            question.image_path = image_path
        else:
            return "Не удалось сохранить картинку. Неверный формат."

    return None


@setup_bp.route("/uploads/<filename>")
def uploaded_file(filename: str):
    """Serve uploaded files."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@setup_bp.route("/")
@telegram_required
@game_context_required
def setup_overview():
    """Display question submission overview page."""
    game, player = g.game, g.player

    if game.status != "setup":
        flash("Игра уже началась. Редактирование вопросов недоступно.", "error")
        return redirect(url_for("main.lobby"))

    categories = {cat.position: cat for cat in player.categories}

    return render_template("setup.html", player=player, categories=categories)


@setup_bp.route("/category/<int:position>", methods=["GET"])
@telegram_required
def edit_category(position: int):
    """Redirect to wizard step 0 (category name)."""
    return redirect(url_for("setup.edit_category_step", pos=position, step=0))


@setup_bp.route("/category/<int:pos>/step/<int:step>", methods=["GET"])
@telegram_required
@game_context_required
def edit_category_step(pos: int, step: int):
    """Display category edit wizard step."""
    if not (0 <= pos < CATEGORIES_PER_PLAYER):
        flash("Неверная позиция категории", "error")
        return redirect(url_for("setup.setup_overview"))

    if not (0 <= step <= QUESTIONS_PER_CATEGORY):
        flash("Неверный шаг", "error")
        return redirect(url_for("setup.edit_category_step", pos=pos, step=0))

    game, player = g.game, g.player

    if game.status != "setup":
        flash("Игра уже началась. Редактирование вопросов недоступно.", "error")
        return redirect(url_for("main.lobby"))

    category = Category.query.filter_by(player_id=player.id, position=pos).first()
    questions = list(category.questions.order_by(Question.points).all()) if category else []
    questions_by_points = {q.points: q for q in questions}

    current_question = None
    if step > 0:
        current_question = questions_by_points.get(POINT_VALUES[step - 1])

    return render_template(
        "category_wizard.html",
        pos=pos,
        step=step,
        category=category,
        current_question=current_question,
        point_values=POINT_VALUES,
        questions_by_points=questions_by_points,
    )


@setup_bp.route("/category/<int:pos>/step/<int:step>", methods=["POST"])
@telegram_required
@game_context_required
def save_category_step(pos: int, step: int):
    """Save category wizard step and advance to next step."""
    if not (0 <= pos < CATEGORIES_PER_PLAYER):
        flash("Неверная позиция категории", "error")
        return redirect(url_for("setup.setup_overview"))

    if not (0 <= step <= QUESTIONS_PER_CATEGORY):
        flash("Неверный шаг", "error")
        return redirect(url_for("setup.edit_category_step", pos=pos, step=0))

    game, player = g.game, g.player

    if game.status != "setup":
        flash("Игра уже началась. Редактирование вопросов недоступно.", "error")
        return redirect(url_for("main.lobby"))

    action = request.form.get("action", "next")

    try:
        category = _get_or_create_category(player.id, pos)

        if step == 0:
            category_name = request.form.get("category_name", "").strip()
            if category_name:
                if len(category_name) > MAX_CATEGORY_NAME_LENGTH:
                    flash(f"Название категории должно быть не более {MAX_CATEGORY_NAME_LENGTH} символов", "error")
                    return redirect(url_for("setup.edit_category_step", pos=pos, step=0))
                category.name = category_name
            elif not category.name:
                category.name = f"Категория {pos + 1}"
            db.session.commit()
        else:
            question_idx = step - 1
            points = POINT_VALUES[question_idx]
            error = _save_question(
                category=category,
                points=points,
                question_text=request.form.get("question_text", "").strip(),
                answer_text=request.form.get("answer_text", "").strip(),
                player_id=player.id,
                question_index=pos * QUESTIONS_PER_CATEGORY + question_idx,
                image_file=request.files.get("image_file"),
                remove_image=request.form.get("remove_image") == "1",
            )
            if error:
                flash(error, "error")
                return redirect(url_for("setup.edit_category_step", pos=pos, step=step))
            db.session.commit()

        _update_questions_submitted(player.id)
        db.session.commit()

        if action == "finish" or (action != "skip" and step >= QUESTIONS_PER_CATEGORY):
            flash(f"Категория «{category.name}» сохранена!", "success")
            return redirect(url_for("setup.setup_overview"))

        return redirect(url_for("setup.edit_category_step", pos=pos, step=step + 1))

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error saving category step: {e}")
        flash("Произошла ошибка. Попробуйте ещё раз.", "error")
        return redirect(url_for("setup.edit_category_step", pos=pos, step=step))


@setup_bp.route("/category/<int:pos>", methods=["POST"])
@telegram_required
@game_context_required
def save_category(pos: int):
    """Save category and all questions at once (legacy endpoint)."""
    if not (0 <= pos < CATEGORIES_PER_PLAYER):
        flash("Неверная позиция категории", "error")
        return redirect(url_for("setup.setup_overview"))

    game, player = g.game, g.player

    if game.status != "setup":
        flash("Игра уже началась. Редактирование вопросов недоступно.", "error")
        return redirect(url_for("main.lobby"))

    try:
        category = _get_or_create_category(player.id, pos)

        category_name = request.form.get("category_name", "").strip()
        if category_name:
            if len(category_name) > MAX_CATEGORY_NAME_LENGTH:
                flash(f"Название категории должно быть не более {MAX_CATEGORY_NAME_LENGTH} символов", "error")
                return redirect(url_for("setup.edit_category", pos=pos))
            category.name = category_name
        elif not category.name:
            category.name = f"Категория {pos + 1}"

        db.session.commit()

        saved_count = 0
        for i, points in enumerate(POINT_VALUES):
            error = _save_question(
                category=category,
                points=points,
                question_text=request.form.get(f"question_{i}", "").strip(),
                answer_text=request.form.get(f"answer_{i}", "").strip(),
                player_id=player.id,
                question_index=pos * QUESTIONS_PER_CATEGORY + i,
                image_file=request.files.get(f"image_{i}"),
                remove_image=request.form.get(f"remove_image_{i}") == "1",
            )
            if error:
                flash(f"Вопрос {i + 1}: {error}", "error")
                return redirect(url_for("setup.edit_category", pos=pos))

            if request.form.get(f"question_{i}", "").strip() or request.form.get(f"answer_{i}", "").strip():
                saved_count += 1

        db.session.commit()

        _update_questions_submitted(player.id)
        db.session.commit()

        if saved_count > 0:
            flash(f"Категория «{category.name}» сохранена! ({saved_count} вопр.)", "success")
        else:
            flash("Заполните хотя бы один вопрос для сохранения", "error")
            return redirect(url_for("setup.edit_category", pos=pos))

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error saving category: {e}")
        flash("Произошла ошибка. Попробуйте ещё раз.", "error")

    return redirect(url_for("setup.setup_overview"))


@setup_bp.route("/category/<int:pos>/delete", methods=["POST"])
@telegram_required
@game_context_required
def delete_category(pos: int):
    """Delete a category and all its questions."""
    if not (0 <= pos < CATEGORIES_PER_PLAYER):
        flash("Неверная позиция категории", "error")
        return redirect(url_for("setup.setup_overview"))

    game, player = g.game, g.player

    if game.status != "setup":
        flash("Игра уже началась. Редактирование вопросов недоступно.", "error")
        return redirect(url_for("main.lobby"))

    try:
        category = Category.query.filter_by(player_id=player.id, position=pos).first()
        if category:
            category_name = category.name
            # Delete all question images first
            for question in category.questions:
                if question.image_path:
                    _delete_image(question.image_path)
            # Delete all questions
            Question.query.filter_by(category_id=category.id).delete()
            # Delete the category
            db.session.delete(category)
            db.session.commit()

            _update_questions_submitted(player.id)
            db.session.commit()

            flash(f"Категория «{category_name}» удалена", "success")
        else:
            flash("Категория не найдена", "error")

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error deleting category: {e}")
        flash("Произошла ошибка при удалении. Попробуйте ещё раз.", "error")

    return redirect(url_for("setup.setup_overview"))


@setup_bp.route("/category/<int:pos>/question/<int:step>/delete", methods=["POST"])
@telegram_required
@game_context_required
def delete_question(pos: int, step: int):
    """Delete a single question from a category."""
    if not (0 <= pos < CATEGORIES_PER_PLAYER):
        flash("Неверная позиция категории", "error")
        return redirect(url_for("setup.setup_overview"))

    if not (1 <= step <= QUESTIONS_PER_CATEGORY):
        flash("Неверный номер вопроса", "error")
        return redirect(url_for("setup.edit_category_step", pos=pos, step=0))

    game, player = g.game, g.player

    if game.status != "setup":
        flash("Игра уже началась. Редактирование вопросов недоступно.", "error")
        return redirect(url_for("main.lobby"))

    try:
        category = Category.query.filter_by(player_id=player.id, position=pos).first()
        if not category:
            flash("Категория не найдена", "error")
            return redirect(url_for("setup.setup_overview"))

        points = POINT_VALUES[step - 1]
        question = Question.query.filter_by(category_id=category.id, points=points).first()

        if question:
            # Delete image if exists
            if question.image_path:
                _delete_image(question.image_path)
            db.session.delete(question)
            db.session.commit()

            _update_questions_submitted(player.id)
            db.session.commit()

            flash(f"Вопрос за {points} очков удалён", "success")
        else:
            flash("Вопрос не найден", "error")

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error deleting question: {e}")
        flash("Произошла ошибка при удалении. Попробуйте ещё раз.", "error")

    return redirect(url_for("setup.edit_category_step", pos=pos, step=step))
