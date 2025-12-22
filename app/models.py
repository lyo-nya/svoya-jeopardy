"""SQLAlchemy models for the Jeopardy game."""

from __future__ import annotations

from datetime import datetime

from app import db


class Game(db.Model):
    """A Jeopardy game session for a Telegram chat."""

    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.BigInteger, nullable=False, unique=True)
    host_telegram_id = db.Column(db.BigInteger, nullable=False)
    status = db.Column(db.String(20), default="setup")
    current_round_id = db.Column(db.Integer, db.ForeignKey("rounds.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    players = db.relationship("Player", back_populates="game", lazy="dynamic")
    rounds = db.relationship(
        "Round",
        back_populates="game",
        lazy="dynamic",
        foreign_keys="Round.game_id",
    )

    def __repr__(self) -> str:
        return f"<Game {self.id} chat={self.chat_id} status={self.status}>"


class Player(db.Model):
    """A player in the game."""

    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    telegram_id = db.Column(db.BigInteger, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_host = db.Column(db.Boolean, default=False)
    total_score = db.Column(db.Integer, default=0)
    questions_submitted = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint("game_id", "telegram_id"),)

    game = db.relationship("Game", back_populates="players")
    categories = db.relationship("Category", back_populates="player", lazy="dynamic")
    rounds = db.relationship("Round", back_populates="player", lazy="dynamic")
    round_scores = db.relationship("RoundScore", back_populates="player", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Player {self.id} name={self.name}>"


class Category(db.Model):
    """A category of questions created by a player."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.Integer, nullable=False)

    player = db.relationship("Player", back_populates="categories")
    questions = db.relationship(
        "Question",
        back_populates="category",
        lazy="dynamic",
        order_by="Question.points",
    )

    def __repr__(self) -> str:
        return f"<Category {self.id} name={self.name}>"


class Question(db.Model):
    """A single question in a category."""

    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    is_answered = db.Column(db.Boolean, default=False)
    answered_by_player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=True)

    category = db.relationship("Category", back_populates="questions")
    answered_by = db.relationship("Player", foreign_keys=[answered_by_player_id])

    def __repr__(self) -> str:
        return f"<Question {self.id} points={self.points}>"


class Round(db.Model):
    """A round of the game (one player's question set)."""

    __tablename__ = "rounds"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")
    round_number = db.Column(db.Integer, nullable=False)

    game = db.relationship("Game", back_populates="rounds", foreign_keys=[game_id])
    player = db.relationship("Player", back_populates="rounds")
    round_scores = db.relationship("RoundScore", back_populates="round", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Round {self.id} player={self.player_id} status={self.status}>"


class RoundScore(db.Model):
    """Tracks a player's score for a specific round."""

    __tablename__ = "round_scores"

    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("rounds.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    score = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint("round_id", "player_id"),)

    round = db.relationship("Round", back_populates="round_scores")
    player = db.relationship("Player", back_populates="round_scores")

    def __repr__(self) -> str:
        return f"<RoundScore round={self.round_id} player={self.player_id} score={self.score}>"
