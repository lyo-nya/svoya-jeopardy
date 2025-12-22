"""Webhook routes for Telegram bot updates."""

from flask import request, current_app
from app.routes import webhook_bp
from app import db
from app.models import Game
from app.services.telegram import send_webapp_button


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
    
    current_app.logger.info(f"Received webhook update: {data.get('update_id')}")
    
    # Handle my_chat_member update (bot added/removed from chat)
    if "my_chat_member" in data:
        handle_my_chat_member(data["my_chat_member"])
    
    # Handle /start command in private chat
    if "message" in data:
        handle_message(data["message"])
    
    return "OK", 200


def handle_message(message: dict):
    """Handle incoming messages, particularly /start command."""
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type")
    chat_title = chat.get("title") or chat.get("first_name", "Private Chat")
    text = message.get("text", "")
    from_user = message.get("from", {})
    from_user_id = from_user.get("id")
    
    # Handle /start command in private chat
    if chat_type == "private" and text.startswith("/start"):
        bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
        app_url = current_app.config.get("APP_URL", "")
        
        if bot_token and app_url:
            # Check if there's a start parameter (e.g., /start chat_-123456)
            parts = text.split()
            start_param = parts[1] if len(parts) > 1 else None
            
            # Create or get game for private chat
            game = Game.query.filter_by(chat_id=chat_id).first()
            if not game:
                game = Game(
                    chat_id=chat_id, 
                    host_telegram_id=from_user_id,
                    chat_title=chat_title,
                    chat_type=chat_type,
                )
                db.session.add(game)
                db.session.commit()
            elif not game.chat_title:
                # Update chat title if not set
                game.chat_title = chat_title
                game.chat_type = chat_type
                db.session.commit()
            
            # Send welcome message with WebApp button
            send_webapp_button(chat_id, bot_token, app_url)
            current_app.logger.info(f"Sent WebApp button to private chat {chat_id}")


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
        
        # Send welcome message with WebApp button to the group
        bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
        app_url = current_app.config.get("APP_URL", "")
        
        if bot_token and app_url:
            success = send_webapp_button(chat_id, bot_token, app_url)
            if success:
                current_app.logger.info(f"Sent WebApp button to group {chat_id}")
            else:
                current_app.logger.error(f"Failed to send WebApp button to group {chat_id}")
