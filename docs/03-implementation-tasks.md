# Implementation Tasks: New Year Jeopardy Party Game

## Overview

This document breaks down the implementation into concrete tasks. Estimated total time: **12-16 hours** of focused development.

---

## Phase 1: Project Setup (1-2 hours)

### Task 1.1: Initialize Project Structure
- [ ] Create directory structure as per technical design
- [ ] Create `requirements.txt` with dependencies:
  ```
  flask==3.0.0
  flask-sqlalchemy==3.1.1
  gunicorn==21.2.0
  python-dotenv==1.0.0
  pillow==10.1.0
  ```
- [ ] Create `.env.example` with required environment variables
- [ ] Create `config.py` with Flask configuration
- [ ] Create Flask app factory in `__init__.py`

### Task 1.2: Database Setup
- [ ] Define SQLAlchemy models in `models.py`
- [ ] Create database initialization script
- [ ] Test database creation and basic operations

### Task 1.3: Docker Setup
- [ ] Create `Dockerfile` for Flask app
- [ ] Create `docker-compose.yml` with app + nginx services
- [ ] Create `nginx.conf` for reverse proxy
- [ ] Create `gunicorn.conf.py` configuration
- [ ] Test local Docker build and run

---

## Phase 2: Telegram Integration (1-2 hours)

### Task 2.1: Telegram WebApp Validation
- [ ] Implement `validate_telegram_data()` function
- [ ] Create middleware/decorator to validate all requests
- [ ] Extract and store user info (id, name, photo)
- [ ] Handle validation failures gracefully

### Task 2.2: Bot Webhook for Host Detection
- [ ] Create `/webhook` endpoint for Telegram bot updates
- [ ] Handle `my_chat_member` update type
- [ ] When bot is added to group, store adder as host in games table
- [ ] Register webhook URL with Telegram API

### Task 2.3: Session Management
- [ ] Store current user in Flask session/context
- [ ] Create `get_current_player()` helper
- [ ] Create `get_current_game()` helper (from chat_id)
- [ ] Implement host detection

### Task 2.4: Frontend Telegram Integration
- [ ] Create `telegram.js` for WebApp API
- [ ] Initialize WebApp and expand
- [ ] Apply Telegram theme colors
- [ ] Include init_data in all form submissions

---

## Phase 3: Base Templates & Styling (2-3 hours)

### Task 3.1: Base Template
- [ ] Create `base.html` with:
  - HTML5 structure
  - Meta tags for mobile
  - Telegram WebApp script include
  - CSS include
  - Common header/navigation
  - Flash message display
  - Footer with New Year theme

### Task 3.2: New Year Theme CSS
- [ ] Define CSS variables for color scheme:
  - Primary: Deep midnight blue (#1a1a2e)
  - Secondary: Gold (#ffd700)
  - Accent: Champagne (#f7e7ce)
  - Success: Festive green (#2d5a27)
- [ ] Style base elements (buttons, inputs, cards)
- [ ] Create game board grid styles
- [ ] Add subtle sparkle/snow animations (CSS only)
- [ ] Ensure mobile-first responsive design
- [ ] Style scoreboard component

### Task 3.3: Component Styles
- [ ] Category card styles
- [ ] Question tile styles (default, answered, selected)
- [ ] Player avatar/name styles
- [ ] Score display styles
- [ ] Winner celebration styles

---

## Phase 4: Question Submission (2-3 hours)

### Task 4.1: Setup Page Routes
- [ ] Create `/setup` route - main submission page
- [ ] Create `/setup/category/<pos>` GET route - edit category
- [ ] Create `/setup/category/<pos>` POST route - save category
- [ ] Create `/setup/upload-image` POST route - image upload

### Task 4.2: Setup Templates
- [ ] Create `setup.html` - overview of 4 categories
- [ ] Create `category_edit.html` - form for category + 5 questions
- [ ] Add image upload UI with preview
- [ ] Add form validation (client-side)

### Task 4.3: Question Storage Logic
- [ ] Implement category creation/update
- [ ] Implement question creation/update
- [ ] Handle image upload (validate, resize, store)
- [ ] Mark player as "questions_submitted" when all 4 complete
- [ ] Prevent edits after game starts

---

## Phase 5: Lobby & Game Start (1-2 hours)

### Task 5.1: Lobby Page
- [ ] Create `/lobby` route
- [ ] Show all players with submission status
- [ ] Show "Start Game" button for host (disabled until all ready)
- [ ] Create `lobby.html` template

### Task 5.2: Game Initialization
- [ ] Create `/game/start` POST route
- [ ] Initialize Round records for each player
- [ ] Set game status to "in_progress"
- [ ] Lock question submissions
- [ ] Redirect to round selection

---

## Phase 6: Game Board & Gameplay (3-4 hours)

### Task 6.1: Round Selection
- [ ] Create `/game/select-round` GET route - choose whose set
- [ ] Create `/game/select-round/<player_id>` POST route
- [ ] Set current round, mark as in_progress
- [ ] Initialize round scores for eligible players

### Task 6.2: Game Board
- [ ] Create `/game` route - main board view
- [ ] Query current round's categories and questions
- [ ] Calculate scores for display
- [ ] Identify sitting-out player
- [ ] Create `game.html` template with grid

### Task 6.3: Question Display
- [ ] Create `/game/question/<id>` GET route
- [ ] Show question text and image
- [ ] Create `question.html` template
- [ ] Add "Reveal Answer" button

### Task 6.4: Answer Reveal
- [ ] Create `/game/reveal/<question_id>` POST route
- [ ] Update question display to show answer
- [ ] Show player selection buttons

### Task 6.5: Point Awarding
- [ ] Create `/game/award/<question_id>/<player_id>` POST route
- [ ] Update question as answered
- [ ] Add points to player's round score
- [ ] Redirect back to game board

### Task 6.6: Round Completion
- [ ] Detect when all 20 questions answered
- [ ] Create `/game/next-round` POST route
- [ ] Add round scores to total scores
- [ ] Mark round as completed
- [ ] Show round selection for next player's set

---

## Phase 7: Scores & Results (1 hour)

### Task 7.1: Scores Page
- [ ] Create `/scores` route
- [ ] Query current round scores and total scores
- [ ] Create `scores.html` template
- [ ] Make accessible to all players

### Task 7.2: Final Results
- [ ] Detect when all rounds completed
- [ ] Create `/results` route
- [ ] Calculate final standings
- [ ] Create `results.html` with celebration styling
- [ ] Highlight winner

---

## Phase 8: Polish & Testing (1-2 hours)

### Task 8.1: Error Handling
- [ ] Create error templates (404, 500)
- [ ] Add try/catch around database operations
- [ ] Graceful handling of invalid game states
- [ ] User-friendly error messages

### Task 8.2: Edge Cases
- [ ] Handle player refreshing mid-game
- [ ] Handle host closing/reopening app
- [ ] Handle network interruptions
- [ ] Validate point values and scores

### Task 8.3: Visual Polish
- [ ] Test on iOS Telegram
- [ ] Test on Android Telegram
- [ ] Adjust sizing/spacing for mobile
- [ ] Add loading states
- [ ] Smooth transitions

### Task 8.4: Testing
- [ ] Test complete flow: setup → game → results
- [ ] Test with multiple browser windows (simulate players)
- [ ] Test image upload with various sizes
- [ ] Verify score calculations

---

## Phase 9: Deployment (1-2 hours)

### Task 9.1: GitHub Actions CI/CD
- [ ] Create `.github/workflows/deploy.yml`
- [ ] Setup SSH key secrets
- [ ] Build Docker image on push to main
- [ ] Deploy to EC2

### Task 9.2: EC2 Server Setup
- [ ] Install Docker and Docker Compose
- [ ] Configure domain/subdomain
- [ ] Setup Let's Encrypt SSL
- [ ] Configure nginx
- [ ] Open required ports (80, 443)

### Task 9.3: Telegram Bot Configuration
- [ ] Set Mini App URL in BotFather
- [ ] Configure menu button
- [ ] Test opening from Telegram

### Task 9.4: Final Verification
- [ ] Complete end-to-end test on production
- [ ] Verify SSL certificate
- [ ] Check error logging
- [ ] Backup plan for database

---

## Task Checklist Summary

| Phase | Tasks | Est. Time |
|-------|-------|-----------|
| 1. Project Setup | 3 | 1-2h |
| 2. Telegram Integration | 4 | 1-2h |
| 3. Templates & Styling | 3 | 2-3h |
| 4. Question Submission | 3 | 2-3h |
| 5. Lobby & Game Start | 2 | 1-2h |
| 6. Game Board & Gameplay | 6 | 3-4h |
| 7. Scores & Results | 2 | 1h |
| 8. Polish & Testing | 4 | 1-2h |
| 9. Deployment | 4 | 1-2h |
| **Total** | **31 tasks** | **12-16h** |

---

## Dependencies Between Phases

```
Phase 1 (Setup)
    │
    ├──▶ Phase 2 (Telegram) ──▶ Phase 3 (Templates)
    │                                │
    │                                ▼
    │                          Phase 4 (Questions)
    │                                │
    │                                ▼
    │                          Phase 5 (Lobby)
    │                                │
    │                                ▼
    │                          Phase 6 (Gameplay)
    │                                │
    │                                ▼
    │                          Phase 7 (Results)
    │                                │
    └────────────────────────────────┼───────────▶ Phase 9 (Deploy)
                                     │
                                     ▼
                               Phase 8 (Polish)
```

Phases 1-2 can be done in parallel by different developers. Phases 3-7 are sequential. Phase 8-9 can be worked on once the core is complete.
