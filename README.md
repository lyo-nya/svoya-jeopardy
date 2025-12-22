# 🎆 New Year Jeopardy Party Game

A Telegram Mini App for playing Jeopardy-style trivia at your New Year's Eve party.

## Features

- **5 players** submit question sets before the party
- **4 categories** with **5 questions** each per player
- Point values: 100, 200, 300, 400, 500
- Host controls the game board on a large screen (TV/projector)
- Festive New Year's Eve theme

## Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: Jinja2 templates + CSS
- **Hosting**: Fly.io

## Development Setup

```bash
# Install dependencies
uv sync

# Run development server
uv run flask --app app:create_app run --debug

# Or with gunicorn
uv run gunicorn 'app:create_app()'
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Flask secret key for sessions |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather |
| `DATABASE_URL` | SQLite database URL (optional) |
| `UPLOAD_FOLDER` | Path for uploaded images (optional) |

## Project Structure

```
jeopardy/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── models.py            # SQLAlchemy models
│   ├── routes/              # Route blueprints
│   ├── services/            # Business logic
│   ├── static/              # CSS, JS, images
│   └── templates/           # Jinja2 templates
├── uploads/                  # User uploaded images
├── instance/                 # SQLite database
└── pyproject.toml
```

## License

MIT
