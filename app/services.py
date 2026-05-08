import random
import string
import os
from typing import Optional, List
from .database import get_db
from .models import Game, Round, Player, Vote, VoteCounts


def generate_code(length=6):
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
    return "".join(random.choices(chars, k=length))


def create_game(title: str) -> Game:
    with get_db() as conn:
        for _ in range(10):
            code = generate_code()
            existing = conn.execute("SELECT id FROM games WHERE code = ?", (code,)).fetchone()
            if not existing:
                break
        cur = conn.execute(
            "INSERT INTO games (code, title) VALUES (?, ?)",
            (code, title)
        )
        game = conn.execute("SELECT * FROM games WHERE id = ?", (cur.lastrowid,)).fetchone()
        return Game(**dict(game))


def get_game_by_code(code: str) -> Optional[Game]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM games WHERE code = ?", (code.upper(),)).fetchone()
        return Game(**dict(row)) if row else None


def get_game_by_id(game_id: int) -> Optional[Game]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        return Game(**dict(row)) if row else None


def create_or_get_player(game_id: int, display_name: str) -> Player:
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM players WHERE game_id = ? AND display_name = ?",
            (game_id, display_name)
        ).fetchone()
        if existing:
            return Player(**dict(existing))
        cur = conn.execute(
            "INSERT INTO players (game_id, display_name) VALUES (?, ?)",
            (game_id, display_name)
        )
        row = conn.execute("SELECT * FROM players WHERE id = ?", (cur.lastrowid,)).fetchone()
        return Player(**dict(row))


def get_player(player_id: int) -> Optional[Player]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        return Player(**dict(row)) if row else None


def get_player_count(game_id: int) -> int:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM players WHERE game_id = ?", (game_id,)).fetchone()
        return row["cnt"]


def create_round(game_id: int, prompt: Optional[str], image_path: Optional[str]) -> Round:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM rounds WHERE game_id = ?", (game_id,)
        ).fetchone()
        round_number = row["cnt"] + 1
        cur = conn.execute(
            "INSERT INTO rounds (game_id, image_path, prompt, status, round_number) VALUES (?, ?, ?, 'pending', ?)",
            (game_id, image_path, prompt, round_number)
        )
        row = conn.execute("SELECT * FROM rounds WHERE id = ?", (cur.lastrowid,)).fetchone()
        return Round(**dict(row))


def get_current_round(game_id: int) -> Optional[Round]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM rounds WHERE game_id = ? ORDER BY id DESC LIMIT 1",
            (game_id,)
        ).fetchone()
        return Round(**dict(row)) if row else None


def get_round(round_id: int) -> Optional[Round]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM rounds WHERE id = ?", (round_id,)).fetchone()
        return Round(**dict(row)) if row else None


def update_round_status(round_id: int, status: str) -> Optional[Round]:
    with get_db() as conn:
        conn.execute("UPDATE rounds SET status = ? WHERE id = ?", (status, round_id))
        row = conn.execute("SELECT * FROM rounds WHERE id = ?", (round_id,)).fetchone()
        return Round(**dict(row)) if row else None


def cast_vote(round_id: int, player_id: int, vote_value: str) -> Vote:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO votes (round_id, player_id, vote_value, updated_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(round_id, player_id) DO UPDATE SET
               vote_value = excluded.vote_value,
               updated_at = CURRENT_TIMESTAMP""",
            (round_id, player_id, vote_value)
        )
        row = conn.execute(
            "SELECT * FROM votes WHERE round_id = ? AND player_id = ?",
            (round_id, player_id)
        ).fetchone()
        return Vote(**dict(row))


def get_vote_counts(round_id: int) -> VoteCounts:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT vote_value, COUNT(*) as cnt FROM votes WHERE round_id = ? GROUP BY vote_value",
            (round_id,)
        ).fetchall()
        counts = VoteCounts()
        for row in rows:
            if row["vote_value"] == "fire":
                counts.fire = row["cnt"]
            elif row["vote_value"] == "cheeks":
                counts.cheeks = row["cnt"]
        return counts


def get_player_vote(round_id: int, player_id: int) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT vote_value FROM votes WHERE round_id = ? AND player_id = ?",
            (round_id, player_id)
        ).fetchone()
        return row["vote_value"] if row else None


def get_all_rounds(game_id: int) -> List[Round]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM rounds WHERE game_id = ? ORDER BY round_number ASC",
            (game_id,)
        ).fetchall()
        return [Round(**dict(r)) for r in rows]
