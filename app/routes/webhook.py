"""Webhook routes for Telegram bot updates."""

from flask import request, current_app
from app.routes import webhook_bp
from app import db
from app.models import Game


@webhook_bp.route("/", methods=["POST"])
def telegram_webhook():
    """
    Handle incoming Telegram bot updates.
    
    Primarily handles my_chat_member updates to detect when the bot
    is added to a group chat, capturing the adder as the host.
    """
    data = request.get_json()
    
    if not data:
        return "OK", 200
    
    # Handle my_chat_member update (bot added/removed from chat)
    if "my_chat_member" in data:
        handle_my_chat_member(data["my_chat_member"])
    
    return "OK", 200


def handle_my_chat_member(update: dict):
    """
    Handle my_chat_member update.
    
    This is triggered when the bot's status changes in a chat
    (e.g., added to group, removed from group, promoted, etc.)
    """
    chat = update.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type")
    
    # Only handle group/supergroup chats
    if chat_type not in ("group", "supergroup"):
        return
    
    if not chat_id:
        return
    
    # Get the user who triggered the change
    from_user = update.get("from", {})
    from_user_id = from_user.get("id")
    
    if not from_user_id:
        return
    
    # Check the new status of the bot
    new_member = update.get("new_chat_member", {})
    new_status = new_member.get("status")
    
    # Bot was added to the chat (status: member or administrator)
    if new_status in ("member", "administrator"):
        # Check if game already exists for this chat
        game = Game.query.filter_by(chat_id=chat_id).first()
        
        if not game:
            # Create new game with the adder as host
            game = Game(
                chat_id=chat_id,
                host_telegram_id=from_user_id,
            )
            db.session.add(game)
            db.session.commit()
            current_app.logger.info(
                f"Created game for chat {chat_id} with host {from_user_id}"
            )
