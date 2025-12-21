# Requirements: New Year Jeopardy Party Game

## Overview

A Telegram Mini App for playing Jeopardy-style trivia at a New Year's Eve party. Players submit question sets in advance, and during the party, a host controls the game board while everyone plays in person.

## Glossary

| Term | Definition |
|------|------------|
| **Player** | A participant in the game who submits questions and competes for points |
| **Host** | A player who controls the game board during gameplay |
| **Question Set** | A collection of 4 categories created by one player |
| **Category** | A themed group of 5 questions with increasing difficulty |
| **Round** | Playing through one player's question set |
| **Game** | A complete session consisting of 5 rounds (one per player) |

## User Stories

### US-1: Game Setup

**As a host**, I want to add the mini app to my Telegram group chat, so that all chat members become game participants.

**Acceptance Criteria:**
- Mini app can be launched from a Telegram group chat
- All group chat members are automatically recognized as players
- Host role is assigned to the player who starts the game

---

### US-2: Question Submission

**As a player**, I want to create my question set before the party, so that others can play my trivia during the game.

**Acceptance Criteria:**
- Player can create exactly 4 categories
- Each category has a name and 5 questions
- Questions have increasing point values: 100, 200, 300, 400, 500
- Each question has a text prompt and a text answer
- Questions can optionally include an image
- Player can edit their questions until the game starts
- Other players cannot see my questions until my round is played

---

### US-3: Game Start

**As a host**, I want to start the game when everyone is ready, so that we can begin playing at the party.

**Acceptance Criteria:**
- Host sees a "Start Game" button when all players have submitted questions
- Starting the game locks all question submissions
- Host can see which players have/haven't submitted their question sets

---

### US-4: Round Selection

**As a host**, I want to choose whose question set to play next, so that we can go through each player's round.

**Acceptance Criteria:**
- Host sees a list of players whose rounds haven't been played yet
- Host can select which player's question set to play
- The selected player is marked as "sitting out" for this round

---

### US-5: Game Board Display

**As a host**, I want to see the Jeopardy game board, so that I can control the game.

**Acceptance Criteria:**
- Board displays 4 category columns
- Each column shows 5 question tiles with point values (100-500)
- Answered questions are visually marked as complete
- Scoreboard is visible showing current round scores and overall scores
- Player whose round it is shown as "sitting out"

---

### US-6: Question Reveal

**As a host**, I want to select and reveal questions, so that players can answer them.

**Acceptance Criteria:**
- Host taps a question tile to select it
- Question text (and image if present) is displayed prominently
- A "Reveal Answer" button is available
- Tapping "Reveal Answer" shows the correct answer

---

### US-7: Awarding Points

**As a host**, I want to award points to the player who answered correctly, so that scores are tracked.

**Acceptance Criteria:**
- After revealing answer, host sees a list of eligible players (excluding the question author)
- Host taps the player who answered correctly
- That player receives the question's point value
- If no one got it right, host can tap "No one" to skip
- Board updates to show question as answered

---

### US-8: Score Viewing

**As a player**, I want to see scores on my phone, so that I can follow the game progress.

**Acceptance Criteria:**
- Players can view current round scores on their device
- Players can view overall game scores on their device
- Scores update when refreshing the page

---

### US-9: Round Completion

**As a host**, I want to complete a round when all questions are answered, so that we can move to the next player's set.

**Acceptance Criteria:**
- When all 20 questions in a round are answered, round is marked complete
- Host can proceed to round selection for next player's set
- Current round scores are added to overall scores

---

### US-10: Game Completion

**As a host**, I want to see final results when all rounds are complete, so that we can celebrate the winner.

**Acceptance Criteria:**
- After all 5 rounds, game shows final standings
- Winner is highlighted with festive New Year styling
- Final scores for all players are displayed

---

## Functional Requirements

### FR-1: Telegram Integration
- FR-1.1: App authenticates users via Telegram WebApp API
- FR-1.2: App retrieves user info (name, ID, photo) from Telegram
- FR-1.3: App works within Telegram's Mini App container
- FR-1.4: App uses Telegram's theme colors for consistent look

### FR-2: Question Management
- FR-2.1: Store questions with: category, text, answer, point value, optional image
- FR-2.2: Images uploaded and stored on server
- FR-2.3: Maximum image size: 5MB
- FR-2.4: Supported formats: JPEG, PNG, GIF, WebP

### FR-3: Game State Management
- FR-3.1: Track game state: setup, in_progress, completed
- FR-3.2: Track round state: which questions have been answered
- FR-3.3: Track scores per player per round and overall
- FR-3.4: Persist all state in database

### FR-4: Access Control
- FR-4.1: Only host can control game flow
- FR-4.2: Players can only edit their own questions
- FR-4.3: Question content hidden until round is played
- FR-4.4: All chat members can view scores

---

## Non-Functional Requirements

### NFR-1: Performance
- Page load time < 2 seconds
- Image uploads complete within 10 seconds

### NFR-2: Usability
- Mobile-first responsive design
- Works on iOS and Android Telegram apps
- Clear visual feedback for all actions

### NFR-3: Theme
- New Year's Eve festive styling
- Colors: Gold, deep blue, white, with sparkle accents
- Celebratory animations for winner reveal

### NFR-4: Reliability
- Game state preserved if host closes/reopens app
- No data loss on network interruptions
