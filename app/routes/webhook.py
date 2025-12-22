"""Webhook routes for Telegram bot updates."""

from flask import request, current_app
from app.routes import webhook_bp
from app import db
from app.models import Game
from app.services.telegram import send_webapp_button


@webhook_bp.route("/", methods=["GET"])
def webhook_test():
    """Test endpoint to verify webhook URL is reachable."""
    return "Webhook endpoint is working!", 200


@webhook_bp.route("/", methods=["POST"])
def telegram_webhook():
    """
    Handle incoming Telegram bot updates.
    
    Primarily handles my_chat_member updates to detect when the bot
    is added to a group chat, capturing the adder as the host.
    """
    data = request.get_json()
    
    if not data:
        current_app.logger.warning("Webhook received empty data")
        return "OK", 200
    
    # Log the full update for debugging
    import json
    current_app.logger.info(f"Received webhook update: {json.dumps(data, indent=2)}")
    
    # Handle my_chat_member update (bot added/removed from chat)
    if "my_chat_member" in data:
        handle_my_chat_member(data["my_chat_member"])
    
    # Handle /start command in private chat
    if "message" in data:
        handle_message(data["message"])
    
    return "OK", 200


def handle_message(message: dict):
    """Handle incoming messages, particularly /start and /play commands."""
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type")
    text = message.get("text", "")
    from_user = message.get("from", {})
    from_user_id = from_user.get("id")
    
    bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    app_url = current_app.config.get("APP_URL", "")
    
    current_app.logger.info(
        f"handle_message: chat_id={chat_id}, chat_type={chat_type}, "
        f"text={text[:50] if text else ''}, from_user_id={from_user_id}"
    )
    
    # Handle /play command in any chat - sends the WebApp button
    if text.startswith("/play"):
        current_app.logger.info(f"/play command received in chat {chat_id}")
        
        if bot_token and app_url:
            # Create or get game for this chat
            game = Game.query.filter_by(chat_id=chat_id).first()
            if not game:
                game = Game(chat_id=chat_id, host_telegram_id=from_user_id)
                db.session.add(game)
                db.session.commit()
                current_app.logger.info(f"Created game for chat {chat_id}")
            
            # Send WebApp button (is_group based on chat_type)
            is_group = chat_type in ("group", "supergroup")
            success = send_webapp_button(chat_id, bot_token, app_url, is_group=is_group)
            current_app.logger.info(f"send_webapp_button result: {success}")
        else:
            current_app.logger.error(
                f"/play: Missing config - bot_token={bool(bot_token)}, app_url={bool(app_url)}"
            )
        return
    
    # Handle /start command in private chat
    if chat_type == "private" and text.startswith("/start"):
        current_app.logger.info(f"/start command received in private chat {chat_id}")
        
        if bot_token and app_url:
            # Check if there's a start parameter (e.g., /start chat_-123456)
            parts = text.split()
            start_param = parts[1] if len(parts) > 1 else None
            
            # Create or get game for private chat
            game = Game.query.filter_by(chat_id=chat_id).first()
            if not game:
                game = Game(chat_id=chat_id, host_telegram_id=from_user_id)
                db.session.add(game)
                db.session.commit()
            
            # Send welcome message with WebApp button (private chat)
            send_webapp_button(chat_id, bot_token, app_url, is_group=False)
            current_app.logger.info(f"Sent WebApp button to private chat {chat_id}")
        else:
            current_app.logger.error(
                f"/start: Missing config - bot_token={bool(bot_token)}, app_url={bool(app_url)}"
            )


def handle_my_chat_member(update: dict):
    """
    Handle my_chat_member update.
    
    This is triggered when the bot's status changes in a chat
    (e.g., added to group, removed from group, promoted, etc.)
    """
    chat = update.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type")
    chat_title = chat.get("title", "Unknown")
    
    current_app.logger.info(
        f"handle_my_chat_member: chat_id={chat_id}, chat_type={chat_type}, "
        f"chat_title={chat_title}"
    )
    
    # Only handle group/supergroup chats
    if chat_type not in ("group", "supergroup"):
        current_app.logger.info(f"Skipping non-group chat type: {chat_type}")
        return
    
    if not chat_id:
        current_app.logger.warning("No chat_id in my_chat_member update")
        return
    
    # Get the user who triggered the change
    from_user = update.get("from", {})
    from_user_id = from_user.get("id")
    
    if not from_user_id:
        current_app.logger.warning("No from_user_id in my_chat_member update")
        return
    
    # Check the new status of the bot
    new_member = update.get("new_chat_member", {})
    new_status = new_member.get("status")
    old_member = update.get("old_chat_member", {})
    old_status = old_member.get("status")
    
    current_app.logger.info(
        f"Bot status change: {old_status} -> {new_status} in chat {chat_id}"
    )
    
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
        else:
            current_app.logger.info(f"Game already exists for chat {chat_id}")
        
        # Send welcome message with WebApp button to the group
        bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
        app_url = current_app.config.get("APP_URL", "")
        
        current_app.logger.info(
            f"Config check: bot_token={bool(bot_token)}, app_url={app_url}"
        )
        
        if bot_token and app_url:
            success = send_webapp_button(chat_id, bot_token, app_url, is_group=True)
            if success:
                current_app.logger.info(f"Sent WebApp button to group {chat_id}")
            else:
                current_app.logger.error(f"Failed to send WebApp button to group {chat_id}")
        else:
            current_app.logger.error(
                f"Missing config: bot_token={bool(bot_token)}, app_url={bool(app_url)}"
            )
