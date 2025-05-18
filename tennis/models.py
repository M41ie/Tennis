from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Player:
    user_id: str
    name: str
    singles_rating: float = 1000.0
    doubles_rating: float = 1000.0
    matches: List['Match'] = field(default_factory=list)

@dataclass
class Club:
    club_id: str
    name: str
    logo: str | None = None
    region: str | None = None
    members: Dict[str, Player] = field(default_factory=dict)

@dataclass
class Match:
    date: datetime.date
    player_a: Player
    player_b: Player
    score_a: int
    score_b: int
    format_weight: float = 1.0
