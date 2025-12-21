# New Year Jeopardy Party Game - Implementation Plan

## 🎆 Project Summary

A Telegram Mini App for playing Jeopardy-style trivia at your New Year's Eve party. Friends submit question sets in advance, and during the party, a host controls the digital game board while everyone plays in person.

## 📋 Documentation

| Document | Description |
|----------|-------------|
| [01-requirements.md](./01-requirements.md) | User stories, functional & non-functional requirements |
| [02-technical-design.md](./02-technical-design.md) | Architecture, data models, API routes, page designs |
| [03-implementation-tasks.md](./03-implementation-tasks.md) | Detailed task breakdown with estimates |
| [04-deployment-guide.md](./04-deployment-guide.md) | EC2 setup, CI/CD, Telegram configuration |

## 🎮 How It Works

### Before the Party
1. Add the Mini App to your Telegram group chat (you become the host)
2. Each of the 5 players submits 4 categories (5 questions each)
3. Questions support text and optional images
4. Question sets are hidden from other players

### At the Party
1. Host opens the app and starts the game
2. Host selects whose question set to play first
3. The question author sits out their round
4. Host controls the board: reveals questions, shows answers, awards points
5. Scoreboard shows current round + overall scores
6. Repeat for all 5 players' sets
7. Winner revealed with festive celebration!

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Jinja2 templates + CSS (SSR) |
| Backend | Python Flask |
| Database | SQLite |
| Hosting | AWS EC2 + Docker + Nginx |
| CI/CD | GitHub Actions |

## 📊 Key Specifications

- **Players**: 5
- **Categories per player**: 4
- **Questions per category**: 5
- **Point values**: 100, 200, 300, 400, 500
- **Total questions**: 100 (20 per player's set)
- **Rounds**: 5 (one per player)

## ⏰ Timeline

**Party Date**: December 31st, 2025

**Estimated Development Time**: 12-16 hours

| Phase | Time |
|-------|------|
| Project Setup | 1-2h |
| Telegram Integration | 1-2h |
| Templates & Styling | 2-3h |
| Question Submission | 2-3h |
| Lobby & Game Start | 1-2h |
| Gameplay | 3-4h |
| Scores & Results | 1h |
| Polish & Testing | 1-2h |
| Deployment | 1-2h |

## 🎨 Theme

New Year's Eve festive design:
- **Colors**: Midnight blue, gold, champagne, festive green
- **Accents**: Sparkles, subtle animations
- **Winner screen**: Celebratory confetti effect

## 🤖 Telegram Bot

- **Bot Username**: `@svoya_jeopardy_bot`
- **Mini App Access**: Via group chat menu button

## 📁 Project Structure

```
jeopardy/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── routes/
│   ├── services/
│   ├── static/
│   └── templates/
├── uploads/
├── instance/
├── .github/workflows/
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
└── requirements.txt
```

## ✅ Next Steps

1. Review these documents
2. Let me know if anything needs adjustment
3. Say "let's build it" when ready to start coding!
