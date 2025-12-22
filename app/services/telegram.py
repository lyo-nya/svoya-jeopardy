"""Telegram WebApp authentication and integration."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar
from urllib.parse import unquote

import requests
from flask import current_app, g, redirect, request, session, url_for

from app import db
from app.models import Game, Player

if TYPE_CHECKING:
    from flask import Response

F = TypeVar("F", bound=Callable[..., Any])

SESSION_TIMEOUT_SECONDS = 3600
TELEGRAM_API_TIMEOUT = 10


def validate_init_data(init_data: str, bot_token: str) -> dict[str, Any] | None:
    """
    Validate Telegram WebApp initData using HMAC-SHA256.
    
    Returns parsed data dict if valid, None otherwise.
    """
    if not init_data or not bot_token:
        return None

    pairs: dict[str, str] = {}
    received_hash: str | None = None

    for part in init_data.split("&"):
        if "=" in part:
            key, value = part.split("=", 1)
            decoded_value = unquote(value)
            if key == "hash":
                received_hash = decoded_value
            else:
                pairs[key] = decoded_value

    if not received_hash:
        return None

    data_check_string = "\n".join(sorted(f"{k}={v}" for k, v in pairs.items()))
    
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(received_hash, expected_hash):
        return None

    result: dict[str, Any] = {}
    
    for key in ("user", "chat"):
        if key in pairs:
            try:
                result[key] = json.loads(pairs[key])
            except json.JSONDecodeError:
                return None

    for key in ("chat_instance", "chat_type", "start_param"):
        if key in pairs:
            result[key] = pairs[key]

    return result


def get_telegram_data() -> dict[str, Any] | None:
    """
    Get validated Telegram data from request or session.
    
    Checks request params first, falls back to session-cached data.
    """
    init_data = request.form.get("init_data") or request.args.get("init_data")
    bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    
    if not bot_token:
        current_app.logger.error("TELEGRAM_BOT_TOKEN not configured")
        return None

    if init_data:
        telegram_data = validate_init_data(init_data, bot_token)
        if telegram_data:
            session["telegram_data"] = telegram_data
            session["telegram_auth_time"] = time.time()
            return telegram_data
        return None

    if "telegram_data" in session:
        auth_time = session.get("telegram_auth_time", 0)
        if time.time() - auth_time < SESSION_TIMEOUT_SECONDS:
            return session["telegram_data"]
        session.pop("telegram_data", None)
        session.pop("telegram_auth_time", None)

    return None


def extract_chat_id(telegram_data: dict[str, Any]) -> int | None:
    """
    Extract chat_id from Telegram data.
    
    Priority: start_param > group chat > user's private chat
    """
    if "start_param" in telegram_data:
        param = telegram_data["start_param"]
        if param.startswith("chat_"):
            chat_id_str = param[5:]
            if chat_id_str.lstrip("-").isdigit():
                return int(chat_id_str)

    if "chat" in telegram_data:
        chat = telegram_data["chat"]
        if chat.get("type") in ("group", "supergroup"):
            return chat.get("id")

    if "user" in telegram_data:
        return telegram_data["user"].get("id")

    return None


def get_chat_id() -> int | None:
    """Get chat_id from current request's Telegram data."""
    telegram_data = g.get("telegram_data")
    return extract_chat_id(telegram_data) if telegram_data else None


def get_or_create_game(chat_id: int, host_telegram_id: int) -> Game:
    """Get existing game or create a new one for the chat."""
    game = Game.query.filter_by(chat_id=chat_id).first()
    if not game:
        game = Game(chat_id=chat_id, host_telegram_id=host_telegram_id)
        db.session.add(game)
        db.session.commit()
    return game


def get_or_create_player(game: Game, telegram_data: dict[str, Any]) -> Player:
    """Get existing player or create a new one for the game."""
    user = telegram_data["user"]
    telegram_id = user["id"]

    player = Player.query.filter_by(game_id=game.id, telegram_id=telegram_id).first()
    if player:
        return player

    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")
    name = f"{first_name} {last_name}".strip() or user.get("username") or f"Player {telegram_id}"

    player = Player(
        game_id=game.id,
        telegram_id=telegram_id,
        name=name,
        is_host=(telegram_id == game.host_telegram_id),
    )
    db.session.add(player)
    db.session.commit()
    return player


def get_current_game() -> Game | None:
    """Get the current game based on chat_id in request context."""
    chat_id = get_chat_id()
    return Game.query.filter_by(chat_id=chat_id).first() if chat_id else None


def get_current_player() -> Player | None:
    """Get the current player based on Telegram data and game."""
    telegram_data = g.get("telegram_data")
    if not telegram_data or "user" not in telegram_data:
        return None

    game = get_current_game()
    if not game:
        return None

    return Player.query.filter_by(
        game_id=game.id,
        telegram_id=telegram_data["user"]["id"],
    ).first()


def is_host() -> bool:
    """Check if the current player is the host."""
    player = get_current_player()
    return player is not None and player.is_host


def telegram_required(f: F) -> F:
    """Decorator requiring valid Telegram authentication."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Response | Any:
        telegram_data = get_telegram_data()
        if not telegram_data:
            return redirect(url_for("main.entry"))
        g.telegram_data = telegram_data
        return f(*args, **kwargs)
    return decorated  # type: ignore[return-value]


def host_required(f: F) -> F:
    """Decorator requiring host privileges (must be used after telegram_required)."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Response | tuple[str, int] | Any:
        if not is_host():
            return "Forbidden: Host access required", 403
        return f(*args, **kwargs)
    return decorated  # type: ignore[return-value]


def game_context_required(f: F) -> F:
    """
    Decorator that loads game and player into g object.
    
    Must be used after @telegram_required.
    Sets g.game and g.player for use in route handlers.
    """
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Response | tuple[str, int] | Any:
        chat_id = get_chat_id()
        if not chat_id:
            return "Could not determine chat", 400

        telegram_data = g.telegram_data
        g.game = get_or_create_game(chat_id, telegram_data["user"]["id"])
        g.player = get_or_create_player(g.game, telegram_data)
        return f(*args, **kwargs)
    return decorated  # type: ignore[return-value]


def _get_bot_username(bot_token: str) -> str | None:
    """Fetch bot username from Telegram API."""
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=TELEGRAM_API_TIMEOUT,
        )
        result = response.json()
        if result.get("ok"):
            return result["result"].get("username")
    except requests.RequestException as e:
        current_app.logger.error(f"Error getting bot info: {e}")
    return None


def send_webapp_button(chat_id: int, bot_token: str, app_url: str, *, is_group: bool = True) -> bool:
    """Send a message with WebApp button to a Telegram chat."""
    if not bot_token or not app_url:
        return False

    app_url = app_url.rstrip("/")

    if is_group:
        bot_username = _get_bot_username(bot_token)
        if not bot_username:
            return False
        start_link = f"https://t.me/{bot_username}?startapp=chat_{chat_id}"
        keyboard = {"inline_keyboard": [[{"text": "🎮 Play New Year Jeopardy!", "url": start_link}]]}
    else:
        keyboard = {"inline_keyboard": [[{"text": "🎮 Play New Year Jeopardy!", "web_app": {"url": app_url}}]]}

    message_text = (
        "🎆 *New Year Jeopardy Party Game* 🎆\n\n"
        "Welcome! I'm here to host a fun Jeopardy-style party game.\n\n"
        "📋 *How to play:*\n"
        "1. Each player creates their own questions\n"
        "2. Take turns answering each other's questions\n"
        "3. Earn points for correct answers\n"
        "4. Most points wins! 🏆\n\n"
        f"Click the button below to {'join this game!' if is_group else 'open the game!'}"
    )

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message_text,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(keyboard),
            },
            timeout=TELEGRAM_API_TIMEOUT,
        )
        return response.status_code == 200 and response.json().get("ok", False)
    except requests.RequestException as e:
        current_app.logger.error(f"Error sending message to chat {chat_id}: {e}")
        return False
