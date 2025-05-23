from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

# Limits on how many clubs a user may create or join
MAX_CREATED_CLUBS = 1
MAX_JOINED_CLUBS = 5


@dataclass
class User:
    """Account data for authentication and permissions."""

    user_id: str
    name: str
    password_hash: str
    can_create_club: bool = False
    # Number of clubs this user has created
    created_clubs: int = 0
    # Number of clubs the user has joined
    joined_clubs: int = 0
    messages: List['Message'] = field(default_factory=list)

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

    admin_ids: Set[str] = field(default_factory=set)
    pending_members: Set[str] = field(default_factory=set)
    banned_ids: Set[str] = field(default_factory=set)
    members: Dict[str, Player] = field(default_factory=dict)
    matches: List['Match | DoublesMatch'] = field(default_factory=list)
    pending_matches: List['Match | DoublesMatch'] = field(default_factory=list)
    # list of upcoming appointments/meetups
    appointments: List['Appointment'] = field(default_factory=list)

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


@dataclass
class Message:
    """A simple notification for a user."""

    date: datetime.date
    text: str
    read: bool = False


@dataclass
class Appointment:
    """A scheduled meetup that players can sign up for."""

    date: datetime.date
    creator: str
    location: Optional[str] = None
    info: Optional[str] = None
    signups: Set[str] = field(default_factory=set)
