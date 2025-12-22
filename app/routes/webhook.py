"""Webhook routes for Telegram bot updates."""

from __future__ import annotations

from typing import Any

from flask import current_app, request

from app import db
from app.models import Game
from app.routes import webhook_bp
from app.services.telegram import send_webapp_button


@webhook_bp.route("/", methods=["POST"])
def telegram_webhook():
    """Handle incoming Telegram bot updates."""
    data = request.get_json()
    if not data:
        return "OK", 200

    if "my_chat_member" in data:
        _handle_chat_member_update(data["my_chat_member"])

    if "message" in data:
        _handle_message(data["message"])

    return "OK", 200


def _handle_message(message: dict[str, Any]) -> None:
    """Handle incoming messages, particularly /start command."""
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type")
    text = message.get("text", "")
    from_user_id = message.get("from", {}).get("id")

    if chat_type != "private" or not text.startswith("/start"):
        return

    bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    app_url = current_app.config.get("APP_URL", "")

    if not (bot_token and app_url):
        return

    game = Game.query.filter_by(chat_id=chat_id).first()
    if not game:
        game = Game(chat_id=chat_id, host_telegram_id=from_user_id)
        db.session.add(game)
        db.session.commit()

    send_webapp_button(chat_id, bot_token, app_url, is_group=False)


def _handle_chat_member_update(update: dict[str, Any]) -> None:
    """Handle bot added/removed from chat."""
    chat = update.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type")

    if chat_type not in ("group", "supergroup") or not chat_id:
        return

    from_user_id = update.get("from", {}).get("id")
    if not from_user_id:
        return

    new_status = update.get("new_chat_member", {}).get("status")
    if new_status not in ("member", "administrator"):
        return

    game = Game.query.filter_by(chat_id=chat_id).first()
    if not game:
        game = Game(chat_id=chat_id, host_telegram_id=from_user_id)
        db.session.add(game)
        db.session.commit()

    bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    app_url = current_app.config.get("APP_URL", "")

    if bot_token and app_url:
        send_webapp_button(chat_id, bot_token, app_url, is_group=True)
