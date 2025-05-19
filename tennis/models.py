from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Player:
    user_id: str
    name: str
    singles_rating: float = 1000.0
    doubles_rating: float = 1000.0
    experience: float = 0.0
    singles_matches: List['Match'] = field(default_factory=list)
    doubles_matches: List['DoublesMatch'] = field(default_factory=list)
    # ratings suggested by other players before any official matches
    pre_ratings: Dict[str, float] = field(default_factory=dict)
    # optional demographic fields for leaderboard filtering
    age: Optional[int] = None
    gender: Optional[str] = None
    avatar: Optional[str] = None

@dataclass
class Club:
    club_id: str
    name: str
    logo: str | None = None
    region: str | None = None
    leader_id: str | None = None
    admins: List[str] = field(default_factory=list)
    members: Dict[str, Player] = field(default_factory=dict)
    matches: List['Match | DoublesMatch'] = field(default_factory=list)
    pending_matches: List['Match | DoublesMatch'] = field(default_factory=list)

@dataclass
class Match:
    date: datetime.date
    player_a: Player
    player_b: Player
    score_a: int
    score_b: int
    format_weight: float = 1.0
    location: Optional[str] = None
    format_name: Optional[str] = None
    rating_a_before: Optional[float] = None
    rating_b_before: Optional[float] = None
    rating_a_after: Optional[float] = None
    rating_b_after: Optional[float] = None
    initiator: str | None = None
    confirmed_a: bool = False
    confirmed_b: bool = False
    approved: bool = False


@dataclass
class DoublesMatch:
    date: datetime.date
    player_a1: Player
    player_a2: Player
    player_b1: Player
    player_b2: Player
    score_a: int
    score_b: int
    format_weight: float = 1.0
    location: Optional[str] = None
    format_name: Optional[str] = None
    rating_a1_before: Optional[float] = None
    rating_a2_before: Optional[float] = None
    rating_b1_before: Optional[float] = None
    rating_b2_before: Optional[float] = None
    rating_a1_after: Optional[float] = None
    rating_a2_after: Optional[float] = None
    rating_b1_after: Optional[float] = None
    rating_b2_after: Optional[float] = None
    initiator: str | None = None
    confirmed_a: bool = False
    confirmed_b: bool = False
    approved: bool = False
