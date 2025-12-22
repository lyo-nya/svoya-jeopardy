"""Telegram WebApp integration service."""

import hmac
import hashlib
import json
from urllib.parse import parse_qs
from functools import wraps
from flask import request, current_app, g
from app import db
from app.models import Game, Player


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
        return None
    
    parsed = parse_qs(init_data)
    
    # Extract hash
    received_hash = parsed.get("hash", [None])[0]
    if not received_hash:
        return None
    
    # Build data check string (sorted key=value pairs, excluding hash)
    data_pairs = []
    for key, value in parsed.items():
        if key != "hash":
            data_pairs.append(f"{key}={value[0]}")
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
        return None
    
    # Parse and return data
    result = {}
    
    # Parse user data
    user_json = parsed.get("user", [None])[0]
    if user_json:
        result["user"] = json.loads(user_json)
    
    # Parse chat data (for group chats)
    chat_json = parsed.get("chat", [None])[0]
    if chat_json:
        result["chat"] = json.loads(chat_json)
    
    # Other fields
    if "chat_instance" in parsed:
        result["chat_instance"] = parsed["chat_instance"][0]
    if "chat_type" in parsed:
        result["chat_type"] = parsed["chat_type"][0]
    if "start_param" in parsed:
        result["start_param"] = parsed["start_param"][0]
    
    return result


def get_telegram_data() -> dict | None:
    """Get and validate Telegram data from the current request."""
    # Check form data first, then query params
    init_data = request.form.get("init_data") or request.args.get("init_data")
    
    if not init_data:
        return None
    
    bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
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
            return "Unauthorized: Invalid Telegram data", 401
        
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
