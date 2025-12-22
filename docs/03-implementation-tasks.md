# Implementation Tasks: New Year Jeopardy Party Game

## Overview

This document breaks down the implementation into concrete tasks. Estimated total time: **12-16 hours** of focused development.

---

## Phase 1: Project Setup (1-2 hours) ✅ COMPLETE

### Task 1.1: Initialize Project Structure ✅
- [x] Create directory structure as per technical design
- [x] Initialize project with `uv init`
- [x] Add dependencies: `uv add flask flask-sqlalchemy gunicorn pillow`
- [x] Create `config.py` with Flask configuration
- [x] Create Flask app factory in `__init__.py`

### Task 1.2: Database Setup ✅
- [x] Define SQLAlchemy models in `models.py`
- [x] Create database initialization script
- [x] Test database creation and basic operations

### Task 1.3: Railway Setup ✅
- [x] Add start script to `pyproject.toml` for Railpack
- [x] Configure for persistent volume (SQLite + uploads)
- [x] Add Procfile for deployment

---

## Phase 2: Telegram Integration (1-2 hours) ✅ COMPLETE

### Task 2.1: Telegram WebApp Validation ✅
- [x] Implement `validate_telegram_data()` function
- [x] Create middleware/decorator to validate all requests
- [x] Extract and store user info (id, name)
- [x] Handle validation failures gracefully

### Task 2.2: Bot Webhook for Host Detection ✅
- [x] Create `/webhook` endpoint for Telegram bot updates
- [x] Handle `my_chat_member` update type
- [x] When bot is added to group, store adder as host in games table
- [ ] Register webhook URL with Telegram API (requires deployment)

### Task 2.3: Session Management ✅
- [x] Store current user in Flask session/context
- [x] Create `get_current_player()` helper
- [x] Create `get_current_game()` helper (from chat_id)
- [x] Implement host detection

### Task 2.4: Frontend Telegram Integration ✅
- [x] Create `telegram.js` for WebApp API
- [x] Initialize WebApp and expand
- [ ] Apply Telegram theme colors (skipped for MVP)
- [x] Include init_data in all form submissions

---

## Phase 3: Base Templates & Styling (2-3 hours) ⚠️ PARTIAL

### Task 3.1: Base Template ✅
- [x] Create `base.html` with:
  - [x] HTML5 structure
  - [x] Meta tags for mobile
  - [x] Telegram WebApp script include
  - [x] CSS include
  - [ ] Common header/navigation (minimal)
  - [x] Flash message display
  - [ ] Footer with New Year theme (skipped for MVP)

### Task 3.2: New Year Theme CSS ⚠️ MINIMAL
- [ ] Define CSS variables for color scheme (basic colors only)
- [x] Style base elements (buttons, inputs, cards)
- [x] Create game board grid styles
- [ ] Add subtle sparkle/snow animations (skipped for MVP)
- [x] Ensure mobile-first responsive design
- [x] Style scoreboard component

### Task 3.3: Component Styles ⚠️ MINIMAL
- [x] Category card styles
- [x] Question tile styles (default, answered, selected)
- [x] Player avatar/name styles
- [x] Score display styles
- [ ] Winner celebration styles (skipped for MVP)

---

## Phase 4: Question Submission (2-3 hours) ✅ COMPLETE

### Task 4.1: Setup Page Routes ✅
- [x] Create `/setup` route - main submission page
- [x] Create `/setup/category/<pos>` GET route - edit category
- [x] Create `/setup/category/<pos>` POST route - save category
- [x] Create `/setup/upload-image` POST route - image upload

### Task 4.2: Setup Templates ✅
- [x] Create `setup.html` - overview of 4 categories
- [x] Create `category_edit.html` - form for category + 5 questions
- [x] Add image upload UI with preview
- [ ] Add form validation (client-side) (server-side only for MVP)

### Task 4.3: Question Storage Logic ✅
- [x] Implement category creation/update
- [x] Implement question creation/update
- [x] Handle image upload (validate, resize, store)
- [x] Mark player as "questions_submitted" when all 4 complete
- [x] Prevent edits after game starts

---

## Phase 5: Lobby & Game Start (1-2 hours) ✅ COMPLETE

### Task 5.1: Lobby Page ✅
- [x] Create `/lobby` route
- [x] Show all players with submission status
- [x] Show "Start Game" button for host (disabled until all ready)
- [x] Create `lobby.html` template

### Task 5.2: Game Initialization ✅
- [x] Create `/game/start` POST route
- [x] Initialize Round records for each player
- [x] Set game status to "in_progress"
- [x] Lock question submissions
- [x] Redirect to round selection

---

## Phase 6: Game Board & Gameplay (3-4 hours) ✅ COMPLETE

### Task 6.1: Round Selection ✅
- [x] Create `/game/select-round` GET route - choose whose set
- [x] Create `/game/select-round/<player_id>` POST route
- [x] Set current round, mark as in_progress
- [x] Initialize round scores for eligible players

### Task 6.2: Game Board ✅
- [x] Create `/game` route - main board view
- [x] Query current round's categories and questions
- [x] Calculate scores for display
- [x] Identify sitting-out player
- [x] Create `game.html` template with grid

### Task 6.3: Question Display ✅
- [x] Create `/game/question/<id>` GET route
- [x] Show question text and image
- [x] Create `question.html` template
- [x] Add "Reveal Answer" button

### Task 6.4: Answer Reveal ✅
- [x] Create `/game/reveal/<question_id>` POST route
- [x] Update question display to show answer
- [x] Show player selection buttons

### Task 6.5: Point Awarding ✅
- [x] Create `/game/award/<question_id>/<player_id>` POST route
- [x] Update question as answered
- [x] Add points to player's round score
- [x] Redirect back to game board

### Task 6.6: Round Completion ✅
- [x] Detect when all 20 questions answered
- [x] Create `/game/next-round` POST route
- [x] Add round scores to total scores
- [x] Mark round as completed
- [x] Show round selection for next player's set

---

## Phase 7: Scores & Results (1 hour) ⚠️ MINIMAL

### Task 7.1: Scores Page ⚠️ MINIMAL
- [x] Create `/scores` route
- [x] Query current round scores and total scores
- [x] Create `scores.html` template (minimal)
- [x] Make accessible to all players

### Task 7.2: Final Results ⚠️ MINIMAL
- [x] Detect when all rounds completed
- [x] Create `/results` route
- [x] Calculate final standings (overall totals)
- [ ] Query per-round scores for breakdown table (skipped for MVP)
- [x] Create `results.html` with celebration styling (minimal)
- [x] Display overall standings
- [x] Highlight winner

---

## Phase 8: Polish & Testing (1-2 hours) ❌ NOT STARTED

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

## Phase 9: Deployment (30 min) ⚠️ READY TO DEPLOY

### Task 9.1: Deploy to Railway
- [x] Prepare Procfile and config for Railway
- [ ] Create Railway account and project
- [ ] Connect GitHub repository
- [ ] Add environment variables (bot token, secret key)
- [ ] Attach persistent volume for data
- [ ] Deploy and get public URL

### Task 9.2: Telegram Bot Configuration
- [ ] Set Mini App URL in BotFather (use Railway URL)
- [ ] Register webhook URL
- [ ] Configure menu button
- [ ] Test opening from Telegram

### Task 9.3: Final Verification
- [ ] Complete end-to-end test on production
- [ ] Verify all players can access
- [ ] Test image upload

---

## Task Checklist Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| 1. Project Setup | 3 | ✅ Complete |
| 2. Telegram Integration | 4 | ✅ Complete |
| 3. Templates & Styling | 3 | ⚠️ Minimal |
| 4. Question Submission | 3 | ✅ Complete |
| 5. Lobby & Game Start | 2 | ✅ Complete |
| 6. Game Board & Gameplay | 6 | ✅ Complete |
| 7. Scores & Results | 2 | ⚠️ Minimal |
| 8. Polish & Testing | 4 | ❌ Not Started |
| 9. Deployment | 3 | ⚠️ Ready |

**Legend:**
- ✅ Complete
- ⚠️ Partial / Minimal MVP
- ❌ Not Started

---

## Dependencies Between Phases

```
Phase 1 (Setup) ✅
    │
    ├──▶ Phase 2 (Telegram) ✅ ──▶ Phase 3 (Templates) ⚠️
    │                                │
    │                                ▼
    │                          Phase 4 (Questions) ✅
    │                                │
    │                                ▼
    │                          Phase 5 (Lobby) ✅
    │                                │
    │                                ▼
    │                          Phase 6 (Gameplay) ✅
    │                                │
    │                                ▼
    │                          Phase 7 (Results) ⚠️
    │                                │
    └────────────────────────────────┼───────────▶ Phase 9 (Deploy) ⚠️
                                     │
                                     ▼
                               Phase 8 (Polish) ❌
```

**Current Status:** Core functionality complete. Ready for deployment and testing.
