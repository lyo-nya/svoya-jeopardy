# Technical Design: New Year Jeopardy Party Game

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram Client                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Telegram Mini App (WebView)             │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │         SSR HTML + CSS + Minimal JS          │    │   │
│  │  │         (Jinja2 Templates)                   │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      AWS EC2 Instance                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Caddy (Reverse Proxy + Auto-SSL)        │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                              │
│                              ▼                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Python Flask Application                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │   Routes    │  │  Services   │  │   Models   │  │   │
│  │  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                              │
│                              ▼                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 SQLite Database                      │   │
│  │                 + Image Storage (filesystem)         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | Jinja2 + HTML + CSS | Simple, readable, SSR |
| Interactivity | Vanilla JS (minimal) | Only for Telegram WebApp API integration |
| Backend | Flask (Python) | Simple, readable, great for SSR |
| Database | SQLite | Simple, no separate server needed |
| File Storage | Local filesystem | Simple, adequate for 5 users |
| Web Server | Caddy | Auto-SSL, reverse proxy |
| Process Manager | Gunicorn | Production-ready WSGI server |
| Containerization | Docker + Docker Compose | Easy deployment |
| CI/CD | GitHub Actions | Auto-deploy on push to main |

## Data Models

### Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    Game      │       │    Player    │       │   Category   │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │       │ id (PK)      │
│ chat_id      │◄──────│ game_id (FK) │◄──────│ player_id(FK)│
│ host_id      │       │ telegram_id  │       │ name         │
│ status       │       │ name         │       │ position     │
│ current_round│       │ photo_url    │       └──────┬───────┘
│ created_at   │       │ is_host      │              │
└──────────────┘       │ total_score  │              │
                       └──────────────┘              │
                                                     │
┌──────────────┐       ┌──────────────┐              │
│    Round     │       │   Question   │◄─────────────┘
├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │
│ game_id (FK) │       │ category_id  │
│ player_id(FK)│       │ text         │
│ status       │       │ answer       │
│ round_number │       │ points       │
└──────┬───────┘       │ image_path   │
       │               │ is_answered  │
       │               │ answered_by  │
       ▼               └──────────────┘
┌──────────────┐
│  RoundScore  │
├──────────────┤
│ id (PK)      │
│ round_id(FK) │
│ player_id(FK)│
│ score        │
└──────────────┘
```

### Database Schema

```sql
-- Games table
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL UNIQUE,
    host_telegram_id INTEGER NOT NULL, -- whoever added the bot to the chat
    status TEXT DEFAULT 'setup', -- setup, in_progress, completed
    current_round_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Players table
CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    telegram_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    photo_url TEXT,
    is_host BOOLEAN DEFAULT FALSE,
    total_score INTEGER DEFAULT 0,
    questions_submitted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (game_id) REFERENCES games(id),
    UNIQUE(game_id, telegram_id)
);

-- Categories table
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    position INTEGER NOT NULL, -- 0-3
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- Questions table
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    answer TEXT NOT NULL,
    points INTEGER NOT NULL, -- 100, 200, 300, 400, 500
    image_path TEXT,
    is_answered BOOLEAN DEFAULT FALSE,
    answered_by_player_id INTEGER,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (answered_by_player_id) REFERENCES players(id)
);

-- Rounds table
CREATE TABLE rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL, -- whose questions are being played
    status TEXT DEFAULT 'pending', -- pending, in_progress, completed
    round_number INTEGER NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games(id),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- Round scores table
CREATE TABLE round_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    score INTEGER DEFAULT 0,
    FOREIGN KEY (round_id) REFERENCES rounds(id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    UNIQUE(round_id, player_id)
);
```

## Application Routes

### Page Routes (SSR HTML)

| Route | Method | Description | Access |
|-------|--------|-------------|--------|
| `/` | GET | Entry point, redirects based on game state | All |
| `/setup` | GET | Question submission page | Player |
| `/setup/category/<pos>` | GET | Edit single category | Player |
| `/lobby` | GET | Pre-game lobby, see who's ready | All |
| `/game` | GET | Main game board (host view) | Host |
| `/game/question/<id>` | GET | Display single question | Host |
| `/scores` | GET | Scoreboard view | All |
| `/results` | GET | Final results page | All |

### Webhook Routes

| Route | Method | Description | Access |
|-------|--------|-------------|--------|
| `/webhook` | POST | Telegram bot webhook (receives updates) | Telegram |

### Action Routes (Form POST / Redirects)

| Route | Method | Description | Access |
|-------|--------|-------------|--------|
| `/setup/category/<pos>` | POST | Save category + questions | Player |
| `/setup/upload-image` | POST | Upload question image | Player |
| `/game/start` | POST | Start the game | Host |
| `/game/select-round/<player_id>` | POST | Select whose round to play | Host |
| `/game/reveal/<question_id>` | POST | Mark question as revealed | Host |
| `/game/award/<question_id>/<player_id>` | POST | Award points to player | Host |
| `/game/next-round` | POST | Proceed to next round | Host |

## Page Designs

### 1. Setup Page (`/setup`)

```
┌─────────────────────────────────────┐
│  🎄 New Year Jeopardy 🎄           │
│  Submit Your Questions              │
├─────────────────────────────────────┤
│                                     │
│  Category 1: [Movies    ] ✓ Ready   │
│  ├─ Q1 (100): What film...          │
│  ├─ Q2 (200): Who directed...       │
│  ├─ Q3 (300): In which year...      │
│  ├─ Q4 (400): Name the actor...     │
│  └─ Q5 (500): What was the...       │
│  [Edit Category]                    │
│                                     │
│  Category 2: [Music     ] ✓ Ready   │
│  ...                                │
│                                     │
│  Category 3: [          ] ○ Empty   │
│  [Add Category]                     │
│                                     │
│  Category 4: [          ] ○ Empty   │
│  [Add Category]                     │
│                                     │
├─────────────────────────────────────┤
│  Progress: 2/4 categories done      │
│  [Go to Lobby]                      │
└─────────────────────────────────────┘
```

### 2. Category Edit Page (`/setup/category/<pos>`)

```
┌─────────────────────────────────────┐
│  ← Back                             │
│  Category 1                         │
├─────────────────────────────────────┤
│  Category Name:                     │
│  [90s Movies                    ]   │
│                                     │
│  ─────────────────────────────────  │
│  Question 1 (100 points)            │
│  [What 1994 film features a box  ]  │
│  [of chocolates?                 ]  │
│  Answer:                            │
│  [Forrest Gump                   ]  │
│  [+ Add Image]                      │
│                                     │
│  ─────────────────────────────────  │
│  Question 2 (200 points)            │
│  [...                            ]  │
│  ...                                │
│                                     │
├─────────────────────────────────────┤
│  [Save Category]                    │
└─────────────────────────────────────┘
```

### 3. Lobby Page (`/lobby`)

```
┌─────────────────────────────────────┐
│  🎆 New Year Jeopardy 🎆           │
│  Waiting for players...             │
├─────────────────────────────────────┤
│                                     │
│  Players Ready:                     │
│                                     │
│  👤 Alice      ✓ Questions Ready    │
│  👤 Bob        ✓ Questions Ready    │
│  👤 Charlie    ○ Still working...   │
│  👤 Diana      ✓ Questions Ready    │
│  👤 Eve        ○ Still working...   │
│                                     │
│  3/5 players ready                  │
│                                     │
├─────────────────────────────────────┤
│  [Edit My Questions]                │
│                                     │
│  (Host only:)                       │
│  [Start Game] (disabled)            │
└─────────────────────────────────────┘
```

### 4. Game Board Page (`/game`)

```
┌─────────────────────────────────────┐
│  🎄 Round 1: Alice's Questions 🎄  │
├─────────────────────────────────────┤
│ Movies  │ Music   │ Sports  │ Food  │
├─────────┼─────────┼─────────┼───────┤
│  100    │  100    │  [done] │  100  │
├─────────┼─────────┼─────────┼───────┤
│  200    │  [done] │  200    │  200  │
├─────────┼─────────┼─────────┼───────┤
│  300    │  300    │  300    │  300  │
├─────────┼─────────┼─────────┼───────┤
│  400    │  400    │  400    │  400  │
├─────────┼─────────┼─────────┼───────┤
│  500    │  500    │  500    │  500  │
├─────────────────────────────────────┤
│  Round Scores:        Overall:      │
│  Bob: 300             Bob: 300      │
│  Charlie: 200         Charlie: 200  │
│  Diana: 100           Diana: 100    │
│  Eve: 0               Eve: 0        │
│  (Alice sitting out)                │
└─────────────────────────────────────┘
```

### 5. Question Display Page (`/game/question/<id>`)

```
┌─────────────────────────────────────┐
│  Movies - 300 points                │
├─────────────────────────────────────┤
│                                     │
│                                     │
│     Which 1999 movie features       │
│     the quote "I see dead          │
│     people"?                        │
│                                     │
│         [Optional Image]            │
│                                     │
│                                     │
├─────────────────────────────────────┤
│  [Reveal Answer]                    │
└─────────────────────────────────────┘

(After reveal:)
┌─────────────────────────────────────┐
│  Movies - 300 points                │
├─────────────────────────────────────┤
│     Which 1999 movie features       │
│     the quote "I see dead          │
│     people"?                        │
│                                     │
│     ✨ The Sixth Sense ✨           │
│                                     │
├─────────────────────────────────────┤
│  Who got it right?                  │
│  [Bob] [Charlie] [Diana] [Eve]      │
└─────────────────────────────────────┘
```

### 6. Final Results Page (`/results`)

```
┌─────────────────────────────────────┐
│  🎆🎉 GAME OVER! 🎉🎆              │
│  Happy New Year!                    │
├─────────────────────────────────────┤
│                                     │
│         🏆 WINNER 🏆               │
│         ✨ Bob ✨                   │
│         2,450 points                │
│                                     │
│  ─────────────────────────────────  │
│                                     │
│  Final Standings:                   │
│                                     │
│  🥇 Bob        2,450 pts            │
│  🥈 Diana      2,100 pts            │
│  🥉 Charlie    1,800 pts            │
│  4. Eve        1,200 pts            │
│  5. Alice        950 pts            │
│                                     │
│  ─────────────────────────────────  │
│                                     │
│  Per-Round Breakdown:               │
│                                     │
│        │Alice│Bob │Charl│Diana│Eve │
│  ──────┼─────┼────┼─────┼─────┼────│
│  R1(A) │ --  │ 600│ 400 │ 300 │200 │
│  R2(B) │ 350 │ -- │ 450 │ 500 │200 │
│  R3(C) │ 200 │ 550│ --  │ 400 │350 │
│  R4(D) │ 200 │ 700│ 450 │ --  │150 │
│  R5(E) │ 200 │ 600│ 500 │ 900 │ -- │
│  ──────┼─────┼────┼─────┼─────┼────│
│  Total │ 950 │2450│1800 │2100 │900 │
│                                     │
│  ─────────────────────────────────  │
│  🎆 Celebrate! 🎆                  │
└─────────────────────────────────────┘
```

## Directory Structure

```
jeopardy/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── models.py            # SQLAlchemy models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py          # Main routes (/, /scores, /results)
│   │   ├── setup.py         # Question submission routes
│   │   └── game.py          # Game control routes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── telegram.py      # Telegram WebApp validation
│   │   └── game.py          # Game logic
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # New Year themed styles
│   │   ├── js/
│   │   │   └── telegram.js  # Telegram WebApp integration
│   │   └── images/          # Static assets
│   └── templates/
│       ├── base.html        # Base template with theme
│       ├── setup.html
│       ├── category_edit.html
│       ├── lobby.html
│       ├── game.html
│       ├── question.html
│       ├── scores.html
│       └── results.html
├── uploads/                  # User uploaded images
├── instance/
│   └── jeopardy.db          # SQLite database
├── tests/
│   └── ...
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── Caddyfile
└── README.md
```

## Telegram WebApp Integration

### Authentication Flow

1. User opens Mini App from Telegram
2. Telegram passes `initData` to the WebApp
3. Flask validates `initData` signature using bot token
4. Extract user info (id, name, photo) from validated data
5. Create/update player in database
6. Store user session

### Host Detection

When the bot is added to a group chat, Telegram sends a `my_chat_member` update to the bot. We capture this to determine the host:

1. Bot receives `my_chat_member` update when added to a group
2. Store the `from.id` (who added the bot) as the host for that `chat.id`
3. When players open the Mini App, check if they match the stored host ID
4. If no host is stored yet (e.g., bot was added before this feature), first person to open becomes host

### initData Validation (Python)

```python
import hmac
import hashlib
from urllib.parse import parse_qs

def validate_telegram_data(init_data: str, bot_token: str) -> dict | None:
    """Validate Telegram WebApp initData and return user data."""
    parsed = parse_qs(init_data)
    
    # Extract hash
    received_hash = parsed.get('hash', [None])[0]
    if not received_hash:
        return None
    
    # Build data check string
    data_pairs = []
    for key, value in parsed.items():
        if key != 'hash':
            data_pairs.append(f"{key}={value[0]}")
    data_pairs.sort()
    data_check_string = '\n'.join(data_pairs)
    
    # Calculate expected hash
    secret_key = hmac.new(
        b'WebAppData', 
        bot_token.encode(), 
        hashlib.sha256
    ).digest()
    
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(received_hash, expected_hash):
        return None
    
    # Parse user data
    import json
    user_data = json.loads(parsed.get('user', ['{}'])[0])
    return user_data
```

### Frontend JavaScript

```javascript
// telegram.js
const tg = window.Telegram.WebApp;

// Initialize
tg.ready();
tg.expand();

// Get init data for backend validation
const initData = tg.initData;

// Apply Telegram theme
document.documentElement.style.setProperty(
    '--tg-theme-bg-color', 
    tg.themeParams.bg_color || '#1a1a2e'
);

// Send init data with every form submission
document.querySelectorAll('form').forEach(form => {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'init_data';
    input.value = initData;
    form.appendChild(input);
});
```

## Security Considerations

1. **Telegram Validation**: All requests must include valid `initData`
2. **CSRF Protection**: Flask-WTF for form submissions
3. **Access Control**: Verify player belongs to game's chat
4. **Host Verification**: Check `is_host` flag for game control actions
5. **Question Privacy**: Only return question content during active round
6. **Image Upload**: Validate file type, limit size to 5MB
7. **SQL Injection**: Use SQLAlchemy ORM (parameterized queries)
