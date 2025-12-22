"""Setup routes for question submission."""

import os
from flask import render_template, request, redirect, url_for, flash, current_app, g, send_from_directory
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError
from PIL import Image
from app.routes import setup_bp
from app import db
from app.models import Category, Question
from app.services import telegram_required, get_chat_id, get_or_create_game, get_or_create_player

POINT_VALUES = [100, 200, 300, 400, 500]
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_image(file, player_id: int, question_index: int) -> str | None:
    """Save and resize uploaded image. Returns filename or None."""
    if not file or not file.filename:
        return None
    
    if not allowed_file(file.filename):
        return None
    
    # Create unique filename
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"p{player_id}_q{question_index}_{secure_filename(file.filename)}"
    
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    filepath = os.path.join(upload_folder, filename)
    
    # Save and resize image
    image = Image.open(file)
    
    # Convert to RGB if necessary (for PNG with transparency)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    
    # Resize if too large (max 1200px on longest side)
    max_size = 1200
    if image.width > max_size or image.height > max_size:
        ratio = min(max_size / image.width, max_size / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # Save as JPEG for consistency
    jpeg_filename = filename.rsplit(".", 1)[0] + ".jpg"
    jpeg_filepath = os.path.join(upload_folder, jpeg_filename)
    image.save(jpeg_filepath, "JPEG", quality=85)
    
    return jpeg_filename


@setup_bp.route("/uploads/<filename>")
def uploaded_file(filename: str):
    """Serve uploaded files."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@setup_bp.route("/")
@telegram_required
def setup_overview():
    """Display question submission overview page."""
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    # Get or create game and player
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Check if game already started
    if game.status != "setup":
        flash("Игра уже началась. Редактирование вопросов недоступно.", "error")
        return redirect(url_for("main.lobby"))
    
    # Get player's categories as dict by position
    categories = {}
    for cat in player.categories:
        categories[cat.position] = cat
    
    return render_template(
        "setup.html",
        player=player,
        categories=categories,
    )


@setup_bp.route("/category/<int:pos>", methods=["GET"])
@telegram_required
def edit_category(pos: int):
    """Redirect to wizard step 0 (category name)."""
    return redirect(url_for("setup.edit_category_step", pos=pos, step=0))


@setup_bp.route("/category/<int:pos>/step/<int:step>", methods=["GET"])
@telegram_required
def edit_category_step(pos: int, step: int):
    """Display category edit wizard step."""
    if pos < 0 or pos > 3:
        flash("Неверная позиция категории", "error")
        return redirect(url_for("setup.setup_overview"))
    
    if step < 0 or step > 5:
        flash("Неверный шаг", "error")
        return redirect(url_for("setup.edit_category_step", pos=pos, step=0))
    
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Check if game already started
    if game.status != "setup":
        flash("Игра уже началась. Редактирование вопросов недоступно.", "error")
        return redirect(url_for("main.lobby"))
    
    # Get existing category if any
    category = Category.query.filter_by(player_id=player.id, position=pos).first()
    questions = list(category.questions.order_by(Question.points).all()) if category else []
    questions_by_points = {q.points: q for q in questions}
    
    # Step 0 = category name, Steps 1-5 = questions
    current_question = None
    if step > 0:
        points = POINT_VALUES[step - 1]
        current_question = questions_by_points.get(points)
    
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
def save_category_step(pos: int, step: int):
    """Save category wizard step and advance to next step."""
    if pos < 0 or pos > 3:
        flash("Неверная позиция категории", "error")
        return redirect(url_for("setup.setup_overview"))
    
    if step < 0 or step > 5:
        flash("Неверный шаг", "error")
        return redirect(url_for("setup.edit_category_step", pos=pos, step=0))
    
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Check if game already started
    if game.status != "setup":
        flash("Игра уже началась. Редактирование вопросов недоступно.", "error")
        return redirect(url_for("main.lobby"))
    
    # Get action from form
    action = request.form.get("action", "next")
    
    try:
        # Get or create category
        category = Category.query.filter_by(player_id=player.id, position=pos).first()
        
        if not category:
            category = Category(player_id=player.id, position=pos, name="")
            db.session.add(category)
            db.session.flush()
        
        if step == 0:
            # Save category name
            category_name = request.form.get("category_name", "").strip()
            if category_name:
                if len(category_name) > 50:
                    flash("Название категории должно быть не более 50 символов", "error")
                    return redirect(url_for("setup.edit_category_step", pos=pos, step=0))
                category.name = category_name
            elif not category.name:
                category.name = f"Категория {pos + 1}"
            db.session.commit()
        else:
            # Save question (step 1-5)
            question_idx = step - 1
            points = POINT_VALUES[question_idx]
            question_text = request.form.get("question_text", "").strip()
            answer_text = request.form.get("answer_text", "").strip()
            remove_image = request.form.get("remove_image") == "1"
            
            # Only save if at least one field is filled
            if question_text or answer_text:
                # Apply placeholders for incomplete
                if question_text and not answer_text:
                    answer_text = "???"
                elif answer_text and not question_text:
                    question_text = "???"
                
                # Validate lengths
                if len(question_text) > 1000:
                    flash("Вопрос слишком длинный (макс. 1000 символов)", "error")
                    return redirect(url_for("setup.edit_category_step", pos=pos, step=step))
                
                if len(answer_text) > 500:
                    flash("Ответ слишком длинный (макс. 500 символов)", "error")
                    return redirect(url_for("setup.edit_category_step", pos=pos, step=step))
                
                # Get or create question
                question = Question.query.filter_by(category_id=category.id, points=points).first()
                if not question:
                    question = Question(category_id=category.id, points=points, text="", answer="")
                    db.session.add(question)
                
                question.text = question_text
                question.answer = answer_text
                
                # Handle image removal
                if remove_image and question.image_path:
                    # Delete old image file
                    old_path = os.path.join(current_app.config["UPLOAD_FOLDER"], question.image_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                    question.image_path = None
                
                # Handle image upload
                image_file = request.files.get("image_file")
                if image_file and image_file.filename:
                    image_file.seek(0, 2)
                    file_size = image_file.tell()
                    image_file.seek(0)
                    
                    if file_size > MAX_IMAGE_SIZE:
                        flash("Картинка слишком большая (макс. 5МБ)", "error")
                        return redirect(url_for("setup.edit_category_step", pos=pos, step=step))
                    
                    image_path = save_image(image_file, player.id, pos * 5 + question_idx)
                    if image_path:
                        question.image_path = image_path
                    else:
                        flash("Не удалось сохранить картинку. Неверный формат.", "error")
                
                db.session.commit()
        
        # Update questions_submitted flag
        total_questions = Question.query.join(Category).filter(
            Category.player_id == player.id
        ).count()
        player.questions_submitted = total_questions > 0
        db.session.commit()
        
        # Determine next step based on action
        if action == "finish":
            flash(f"Категория «{category.name}» сохранена!", "success")
            return redirect(url_for("setup.setup_overview"))
        elif action == "skip":
            # Skip to next step
            next_step = step + 1
            if next_step > 5:
                flash(f"Категория «{category.name}» сохранена!", "success")
                return redirect(url_for("setup.setup_overview"))
            return redirect(url_for("setup.edit_category_step", pos=pos, step=next_step))
        else:
            # Default: next step
            next_step = step + 1
            if next_step > 5:
                flash(f"Категория «{category.name}» сохранена!", "success")
                return redirect(url_for("setup.setup_overview"))
            return redirect(url_for("setup.edit_category_step", pos=pos, step=next_step))
            
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error saving category step: {e}")
        flash("Произошла ошибка. Попробуйте ещё раз.", "error")
    
    return redirect(url_for("setup.edit_category_step", pos=pos, step=step))


@setup_bp.route("/category/<int:pos>", methods=["POST"])
@telegram_required
def save_category(pos: int):
    """Save category and questions. Supports partial submissions."""
    if pos < 0 or pos > 3:
        flash("Неверная позиция категории", "error")
        return redirect(url_for("setup.setup_overview"))
    
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Check if game already started
    if game.status != "setup":
        flash("Игра уже началась. Редактирование вопросов недоступно.", "error")
        return redirect(url_for("main.lobby"))
    
    try:
        # Get or create category
        category = Category.query.filter_by(player_id=player.id, position=pos).first()
        
        if not category:
            category = Category(player_id=player.id, position=pos, name="")
            db.session.add(category)
            db.session.flush()  # Get the ID
        
        # Update category name (use default if empty)
        category_name = request.form.get("category_name", "").strip()
        if category_name:
            # Validate category name length
            if len(category_name) > 50:
                flash("Название категории должно быть не более 50 символов", "error")
                return redirect(url_for("setup.edit_category", pos=pos))
            category.name = category_name
        elif not category.name:
            # Set default name if none provided and none exists
            category.name = f"Категория {pos + 1}"
        
        db.session.commit()
        
        # Get existing questions as dict by points
        existing_questions = {q.points: q for q in category.questions}
        
        saved_count = 0
        # Process each question - allow partial submissions
        for i in range(5):
            points = POINT_VALUES[i]
            question_text = request.form.get(f"question_{i}", "").strip()
            answer_text = request.form.get(f"answer_{i}", "").strip()
            
            # Skip if both are empty (allow partial submission)
            if not question_text and not answer_text:
                continue
            
            # If one is filled but not the other, still save but note it's incomplete
            if question_text and not answer_text:
                answer_text = "???"  # Placeholder for incomplete answer
            elif answer_text and not question_text:
                question_text = "???"  # Placeholder for incomplete question
            
            # Validate lengths
            if len(question_text) > 1000:
                flash(f"Вопрос {i + 1} слишком длинный (макс. 1000 символов)", "error")
                return redirect(url_for("setup.edit_category", pos=pos))
            
            if len(answer_text) > 500:
                flash(f"Ответ {i + 1} слишком длинный (макс. 500 символов)", "error")
                return redirect(url_for("setup.edit_category", pos=pos))
            
            # Get or create question
            question = existing_questions.get(points)
            
            if not question:
                question = Question(category_id=category.id, points=points, text="", answer="")
                db.session.add(question)
            
            question.text = question_text
            question.answer = answer_text
            saved_count += 1
            
            # Handle image removal
            remove_image = request.form.get(f"remove_image_{i}") == "1"
            if remove_image and question.image_path:
                old_path = os.path.join(current_app.config["UPLOAD_FOLDER"], question.image_path)
                if os.path.exists(old_path):
                    os.remove(old_path)
                question.image_path = None
            
            # Handle image upload
            image_file = request.files.get(f"image_{i}")
            if image_file and image_file.filename:
                # Check file size
                image_file.seek(0, 2)  # Seek to end
                file_size = image_file.tell()
                image_file.seek(0)  # Reset position
                
                if file_size > MAX_IMAGE_SIZE:
                    flash(f"Картинка для вопроса {i + 1} слишком большая (макс. 5МБ)", "error")
                    return redirect(url_for("setup.edit_category", pos=pos))
                
                image_path = save_image(image_file, player.id, pos * 5 + i)
                if image_path:
                    question.image_path = image_path
                else:
                    flash(f"Не удалось сохранить картинку для вопроса {i + 1}. Неверный формат.", "error")
        
        db.session.commit()
        
        # Update questions_submitted flag based on having at least 1 question
        total_questions = Question.query.join(Category).filter(
            Category.player_id == player.id
        ).count()
        player.questions_submitted = total_questions > 0
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
