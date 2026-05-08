from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Game:
    id: int
    code: str
    title: str
    created_at: str
    status: str


@dataclass
class Round:
    id: int
    game_id: int
    image_path: Optional[str]
    prompt: Optional[str]
    status: str
    round_number: int
    created_at: str


@dataclass
class Player:
    id: int
    game_id: int
    display_name: str
    joined_at: str


@dataclass
class Vote:
    id: int
    round_id: int
    player_id: int
    vote_value: str
    updated_at: str


@dataclass
class VoteCounts:
    fire: int = 0
    cheeks: int = 0

    @property
    def total(self):
        return self.fire + self.cheeks

    @property
    def fire_pct(self):
        if self.total == 0:
            return 0
        return round(self.fire / self.total * 100)

    @property
    def cheeks_pct(self):
        if self.total == 0:
            return 0
        return round(self.cheeks / self.total * 100)

    @property
    def verdict(self):
        if self.total == 0:
            return "NO VOTES"
        diff = abs(self.fire_pct - self.cheeks_pct)
        if diff <= 10:
            return "CHAOS SPLIT"
        if self.fire > self.cheeks:
            return "CERTIFIED FIRE 🔥"
        return "ABSOLUTE CHEEKS 🍑"
