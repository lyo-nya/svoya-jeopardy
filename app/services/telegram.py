"""Telegram WebApp integration service."""

import hmac
import hashlib
import json
import requests
from urllib.parse import parse_qs, unquote
from functools import wraps
from flask import request, current_app, g
from app import db
from app.models import Game, Player


def send_webapp_button(chat_id: int, bot_token: str, app_url: str) -> bool:
    """
    Send a message to a chat with a button to open the WebApp.
    
    Args:
        chat_id: The Telegram chat ID
        bot_token: The bot's API token
        app_url: The base URL of the web app (e.g., https://svoya-jeopardy.fly.dev)
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    if not bot_token or not app_url:
        current_app.logger.error(
            f"send_webapp_button: Missing bot_token={bool(bot_token)}, app_url={bool(app_url)}"
        )
        return False
    
    # Clean up the app_url (remove trailing slash if present)
    app_url = app_url.rstrip("/")
    
    # The WebApp URL - Telegram will include chat info in initData automatically
    # when the button is pressed in a group chat
    webapp_url = app_url
    
    current_app.logger.info(f"Sending WebApp button to chat {chat_id} with URL: {webapp_url}")
    
    # Create inline keyboard with WebApp button
    keyboard = {
        "inline_keyboard": [[
            {
                "text": "🎮 Play New Year Jeopardy!",
                "web_app": {"url": webapp_url}
            }
        ]]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": "🎆 *New Year Jeopardy Party Game* 🎆\n\n"
                "Welcome! I'm here to host a fun Jeopardy-style party game.\n\n"
                "📋 *How to play:*\n"
                "1. Each player creates their own questions\n"
                "2. Take turns answering each other's questions\n"
                "3. Earn points for correct answers\n"
                "4. Most points wins! 🏆\n\n"
                "Click the button below to join the game!",
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard)
    }
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
            timeout=10
        )
        result = response.json()
        if response.status_code == 200 and result.get("ok"):
            current_app.logger.info(f"Successfully sent WebApp button to chat {chat_id}")
            return True
        else:
            current_app.logger.error(
                f"Failed to send message to chat {chat_id}: "
                f"status={response.status_code}, response={result}"
            )
            return False
    except Exception as e:
        current_app.logger.error(f"Error sending message to chat {chat_id}: {e}")
        return False


def validate_telegram_data(init_data: str, bot_token: str) -> dict | None:
    """
    Validate Telegram WebApp initData and return parsed data.
    
    Returns None if validation fails, otherwise returns dict with:
    - user: dict with id, first_name, last_name, username
    - chat_instance: str
    - chat_type: str
    - start_param: str (optional, contains chat_id for group chats)
    """
    if not init_data or not bot_token:
        current_app.logger.warning(
            f"Validation failed: init_data={'empty' if not init_data else 'present'}, "
            f"bot_token={'empty' if not bot_token else 'present'}"
        )
        return None
    
    # Parse the init_data string manually to preserve the exact values
    # init_data format: key1=value1&key2=value2&...
    pairs = {}
    received_hash = None
    
    for part in init_data.split("&"):
        if "=" in part:
            key, value = part.split("=", 1)
            # URL decode the value
            decoded_value = unquote(value)
            if key == "hash":
                received_hash = decoded_value
            else:
                pairs[key] = decoded_value
    
    if not received_hash:
        current_app.logger.warning("Validation failed: no hash in init_data")
        return None
    
    # Build data check string (sorted key=value pairs, excluding hash)
    data_pairs = [f"{k}={v}" for k, v in pairs.items()]
    data_pairs.sort()
    data_check_string = "\n".join(data_pairs)
    
    # Calculate expected hash
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()
    
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    
    # Verify hash
    if not hmac.compare_digest(received_hash, expected_hash):
        current_app.logger.warning(
            f"Validation failed: hash mismatch. "
            f"Data check string (first 100 chars): {data_check_string[:100]}..."
        )
        return None
    
    current_app.logger.info("Telegram data validated successfully")
    
    # Parse and return data
    result = {}
    
    # Parse user data
    if "user" in pairs:
        try:
            result["user"] = json.loads(pairs["user"])
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Failed to parse user JSON: {e}")
            return None
    
    # Parse chat data (for group chats)
    if "chat" in pairs:
        try:
            result["chat"] = json.loads(pairs["chat"])
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Failed to parse chat JSON: {e}")
            return None
    
    # Other fields
    if "chat_instance" in pairs:
        result["chat_instance"] = pairs["chat_instance"]
    if "chat_type" in pairs:
        result["chat_type"] = pairs["chat_type"]
    if "start_param" in pairs:
        result["start_param"] = pairs["start_param"]
    
    return result


def get_telegram_data() -> dict | None:
    """Get and validate Telegram data from the current request."""
    # Check form data first, then query params
    init_data = request.form.get("init_data") or request.args.get("init_data")
    
    if not init_data:
        current_app.logger.warning(
            f"No init_data found in request. "
            f"Form keys: {list(request.form.keys())}, "
            f"Args keys: {list(request.args.keys())}"
        )
        return None
    
    bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        current_app.logger.error("TELEGRAM_BOT_TOKEN not configured!")
        return None
        
    return validate_telegram_data(init_data, bot_token)


def get_chat_id() -> int | None:
    """
    Extract chat_id from Telegram data.
    
    For group chats, chat_id comes from the chat object or start_param.
    For private chats, we use the user's telegram_id as chat_id.
    """
    telegram_data = g.get("telegram_data")
    if not telegram_data:
        return None
    
    # Group chat: chat object contains the id
    if "chat" in telegram_data:
        return telegram_data["chat"].get("id")
    
    # Group chat via start_param (when opened via bot link with parameter)
    if "start_param" in telegram_data:
        param = telegram_data["start_param"]
        # start_param format: "chat_<chat_id>"
        if param.startswith("chat_"):
            chat_id_str = param[5:]
            if chat_id_str.lstrip("-").isdigit():
                return int(chat_id_str)
    
    # Private chat: use user's telegram_id
    if "user" in telegram_data:
        return telegram_data["user"].get("id")
    
    return None


def get_current_game() -> Game | None:
    """Get the current game based on chat_id."""
    chat_id = get_chat_id()
    if not chat_id:
        return None
    
    return Game.query.filter_by(chat_id=chat_id).first()


def get_or_create_game(chat_id: int, host_telegram_id: int) -> Game:
    """Get existing game or create a new one."""
    game = Game.query.filter_by(chat_id=chat_id).first()
    
    if not game:
        game = Game(chat_id=chat_id, host_telegram_id=host_telegram_id)
        db.session.add(game)
        db.session.commit()
    
    return game


def get_current_player() -> Player | None:
    """Get the current player based on Telegram data and game."""
    telegram_data = g.get("telegram_data")
    if not telegram_data or "user" not in telegram_data:
        return None
    
    game = get_current_game()
    if not game:
        return None
    
    telegram_id = telegram_data["user"]["id"]
    return Player.query.filter_by(
        game_id=game.id,
        telegram_id=telegram_id,
    ).first()


def get_or_create_player(game: Game, telegram_data: dict) -> Player:
    """Get existing player or create a new one."""
    user = telegram_data["user"]
    telegram_id = user["id"]
    
    player = Player.query.filter_by(
        game_id=game.id,
        telegram_id=telegram_id,
    ).first()
    
    if not player:
        # Build display name
        first_name = user.get("first_name", "")
        last_name = user.get("last_name", "")
        name = f"{first_name} {last_name}".strip() or user.get("username", f"Player {telegram_id}")
        
        # Check if this player is the host
        is_host = telegram_id == game.host_telegram_id
        
        player = Player(
            game_id=game.id,
            telegram_id=telegram_id,
            name=name,
            is_host=is_host,
        )
        db.session.add(player)
        db.session.commit()
    
    return player


def is_host() -> bool:
    """Check if the current player is the host."""
    player = get_current_player()
    return player is not None and player.is_host


def telegram_required(f):
    """Decorator to require valid Telegram authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        telegram_data = get_telegram_data()
        
        if not telegram_data:
            current_app.logger.error(
                f"Authorization failed for {request.path}. "
                f"Method: {request.method}, "
                f"Has init_data in form: {'init_data' in request.form}, "
                f"Has init_data in args: {'init_data' in request.args}"
            )
            return (
                "Authorization Error: Unable to verify Telegram authentication. "
                "Please try closing and reopening the app from Telegram.",
                401
            )
        
        # Store in Flask g object for access in route handlers
        g.telegram_data = telegram_data
        
        return f(*args, **kwargs)
    
    return decorated_function


def host_required(f):
    """Decorator to require host privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_host():
            return "Forbidden: Host access required", 403
        return f(*args, **kwargs)
    
    return decorated_function
