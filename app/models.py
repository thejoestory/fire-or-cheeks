from dataclasses import dataclass, field
from typing import Optional, List
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


@dataclass
class RoundSummary:
    round_number: int
    image_path: Optional[str]
    prompt: Optional[str]
    fire: int
    cheeks: int
    total: int
    fire_pct: int
    cheeks_pct: int
    verdict: str


@dataclass
class GameSummary:
    game: "Game"
    rounds: List[RoundSummary]

    @property
    def fire_wins(self):
        return sum(1 for r in self.rounds if "FIRE" in r.verdict)

    @property
    def cheeks_wins(self):
        return sum(1 for r in self.rounds if "CHEEKS" in r.verdict)

    @property
    def chaos_splits(self):
        return sum(1 for r in self.rounds if "CHAOS" in r.verdict)

    @property
    def overall_verdict(self):
        if self.fire_wins > self.cheeks_wins:
            return "OVERALL FIRE 🔥"
        if self.cheeks_wins > self.fire_wins:
            return "OVERALL CHEEKS 🍑"
        return "IT'S A TIE 🤝"
