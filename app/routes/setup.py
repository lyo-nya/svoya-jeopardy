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
        flash("Game has already started. You cannot edit questions.", "error")
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
    """Display category edit form."""
    if pos < 0 or pos > 3:
        flash("Invalid category position", "error")
        return redirect(url_for("setup.setup_overview"))
    
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Check if game already started
    if game.status != "setup":
        flash("Game has already started. You cannot edit questions.", "error")
        return redirect(url_for("main.lobby"))
    
    # Get existing category if any
    category = Category.query.filter_by(player_id=player.id, position=pos).first()
    questions = list(category.questions.order_by(Question.points).all()) if category else []
    
    return render_template(
        "category_edit.html",
        pos=pos,
        category=category,
        questions=questions,
    )


@setup_bp.route("/category/<int:pos>", methods=["POST"])
@telegram_required
def save_category(pos: int):
    """Save category and questions."""
    if pos < 0 or pos > 3:
        flash("Invalid category position", "error")
        return redirect(url_for("setup.setup_overview"))
    
    chat_id = get_chat_id()
    if not chat_id:
        return "Could not determine chat", 400
    
    telegram_data = g.telegram_data
    game = get_or_create_game(chat_id, telegram_data["user"]["id"])
    player = get_or_create_player(game, telegram_data)
    
    # Check if game already started
    if game.status != "setup":
        flash("Game has already started. You cannot edit questions.", "error")
        return redirect(url_for("main.lobby"))
    
    try:
        # Get or create category
        category = Category.query.filter_by(player_id=player.id, position=pos).first()
        
        if not category:
            category = Category(player_id=player.id, position=pos, name="")
            db.session.add(category)
        
        # Update category name
        category_name = request.form.get("category_name", "").strip()
        
        if not category_name:
            flash("Category name is required", "error")
            return redirect(url_for("setup.edit_category", pos=pos))
        
        # Validate category name length
        if len(category_name) > 50:
            flash("Category name must be 50 characters or less", "error")
            return redirect(url_for("setup.edit_category", pos=pos))
        
        category.name = category_name
        db.session.commit()
        
        # Get existing questions as dict by points
        existing_questions = {q.points: q for q in category.questions}
        
        # Process each question
        for i in range(5):
            points = POINT_VALUES[i]
            question_text = request.form.get(f"question_{i}", "").strip()
            answer_text = request.form.get(f"answer_{i}", "").strip()
            
            if not question_text or not answer_text:
                flash(f"Question {i + 1} is incomplete", "error")
                return redirect(url_for("setup.edit_category", pos=pos))
            
            # Validate lengths
            if len(question_text) > 1000:
                flash(f"Question {i + 1} is too long (max 1000 characters)", "error")
                return redirect(url_for("setup.edit_category", pos=pos))
            
            if len(answer_text) > 500:
                flash(f"Answer {i + 1} is too long (max 500 characters)", "error")
                return redirect(url_for("setup.edit_category", pos=pos))
            
            # Get or create question
            question = existing_questions.get(points)
            
            if not question:
                question = Question(category_id=category.id, points=points, text="", answer="")
                db.session.add(question)
            
            question.text = question_text
            question.answer = answer_text
            
            # Handle image upload
            image_file = request.files.get(f"image_{i}")
            if image_file and image_file.filename:
                # Check file size
                image_file.seek(0, 2)  # Seek to end
                file_size = image_file.tell()
                image_file.seek(0)  # Reset position
                
                if file_size > MAX_IMAGE_SIZE:
                    flash(f"Image for question {i + 1} is too large (max 5MB)", "error")
                    return redirect(url_for("setup.edit_category", pos=pos))
                
                image_path = save_image(image_file, player.id, pos * 5 + i)
                if image_path:
                    question.image_path = image_path
                else:
                    flash(f"Failed to save image for question {i + 1}. Invalid file type.", "error")
        
        db.session.commit()
        
        # Check if all 4 categories are complete
        category_count = Category.query.filter_by(player_id=player.id).count()
        if category_count >= 4:
            player.questions_submitted = True
            db.session.commit()
        
        flash(f"Category '{category.name}' saved!", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error saving category: {e}")
        flash("An error occurred. Please try again.", "error")
    
    return redirect(url_for("setup.setup_overview"))
