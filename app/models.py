"""SQLAlchemy models for New Year Jeopardy Party Game."""

from datetime import datetime
from app import db


class Game(db.Model):
    """Represents a Jeopardy game session for a Telegram chat."""

    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.BigInteger, nullable=False, unique=True)
    chat_title = db.Column(db.String(255), nullable=True)  # Chat/group name for display
    chat_type = db.Column(db.String(20), nullable=True)  # private, group, supergroup
    host_telegram_id = db.Column(db.BigInteger, nullable=False)
    status = db.Column(db.String(20), default="setup")  # setup, in_progress, completed
    current_round_id = db.Column(db.Integer, db.ForeignKey("rounds.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    players = db.relationship("Player", back_populates="game", lazy="dynamic")
    rounds = db.relationship(
        "Round",
        back_populates="game",
        lazy="dynamic",
        foreign_keys="Round.game_id",
    )

    def __repr__(self):
        return f"<Game {self.id} chat={self.chat_id} status={self.status}>"


class Player(db.Model):
    """Represents a player in the game."""

    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    telegram_id = db.Column(db.BigInteger, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_host = db.Column(db.Boolean, default=False)
    total_score = db.Column(db.Integer, default=0)
    questions_submitted = db.Column(db.Boolean, default=False)

    # Unique constraint: one player per telegram_id per game
    __table_args__ = (db.UniqueConstraint("game_id", "telegram_id"),)

    # Relationships
    game = db.relationship("Game", back_populates="players")
    categories = db.relationship("Category", back_populates="player", lazy="dynamic")
    rounds = db.relationship("Round", back_populates="player", lazy="dynamic")
    round_scores = db.relationship("RoundScore", back_populates="player", lazy="dynamic")

    def __repr__(self):
        return f"<Player {self.id} name={self.name} telegram_id={self.telegram_id}>"


class Category(db.Model):
    """Represents a category of questions created by a player."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.Integer, nullable=False)  # 0-3

    # Relationships
    player = db.relationship("Player", back_populates="categories")
    questions = db.relationship(
        "Question",
        back_populates="category",
        lazy="dynamic",
        order_by="Question.points",
    )

    def __repr__(self):
        return f"<Category {self.id} name={self.name} position={self.position}>"


class Question(db.Model):
    """Represents a single question in a category."""

    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, nullable=False)  # 100, 200, 300, 400, 500
    image_path = db.Column(db.String(255), nullable=True)
    is_answered = db.Column(db.Boolean, default=False)
    answered_by_player_id = db.Column(
        db.Integer, db.ForeignKey("players.id"), nullable=True
    )

    # Relationships
    category = db.relationship("Category", back_populates="questions")
    answered_by = db.relationship("Player", foreign_keys=[answered_by_player_id])

    def __repr__(self):
        return f"<Question {self.id} points={self.points} answered={self.is_answered}>"


class Round(db.Model):
    """Represents a round of the game (one player's question set)."""

    __tablename__ = "rounds"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, in_progress, completed
    round_number = db.Column(db.Integer, nullable=False)

    # Relationships
    game = db.relationship("Game", back_populates="rounds", foreign_keys=[game_id])
    player = db.relationship("Player", back_populates="rounds")
    round_scores = db.relationship("RoundScore", back_populates="round", lazy="dynamic")

    def __repr__(self):
        return f"<Round {self.id} player={self.player_id} status={self.status}>"


class RoundScore(db.Model):
    """Tracks a player's score for a specific round."""

    __tablename__ = "round_scores"

    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("rounds.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    score = db.Column(db.Integer, default=0)

    # Unique constraint: one score per player per round
    __table_args__ = (db.UniqueConstraint("round_id", "player_id"),)

    # Relationships
    round = db.relationship("Round", back_populates="round_scores")
    player = db.relationship("Player", back_populates="round_scores")

    def __repr__(self):
        return f"<RoundScore round={self.round_id} player={self.player_id} score={self.score}>"
