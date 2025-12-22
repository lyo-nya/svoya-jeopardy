"""Setup routes for question submission."""

from flask import render_template
from app.routes import setup_bp


@setup_bp.route("/")
def setup_overview():
    """Display question submission overview page."""
    # TODO: Implement setup page
    return "Setup page - coming soon"


@setup_bp.route("/category/<int:pos>", methods=["GET"])
def edit_category(pos):
    """Display category edit form."""
    # TODO: Implement category edit page
    return f"Edit category {pos} - coming soon"


@setup_bp.route("/category/<int:pos>", methods=["POST"])
def save_category(pos):
    """Save category and questions."""
    # TODO: Implement category save
    return f"Save category {pos} - coming soon"


@setup_bp.route("/upload-image", methods=["POST"])
def upload_image():
    """Handle image upload."""
    # TODO: Implement image upload
    return "Image upload - coming soon"
