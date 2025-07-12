from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

# Limits on how many clubs a user may create or join
# By default users cannot create any clubs until a limit is set
MAX_CREATED_CLUBS = 0
MAX_JOINED_CLUBS = 5


@dataclass
class User:
    """Account data for authentication and permissions."""

    user_id: str
    name: str
    password_hash: str
    # optional openid from WeChat mini program
    wechat_openid: Optional[str] = None
    # all users may create clubs; limit controls whether they actually can
    can_create_club: bool = True
    is_sys_admin: bool = False
    # Number of clubs this user has created
    created_clubs: int = 0
    # Number of clubs the user has joined
    joined_clubs: int = 0
    # Per-user limits
    max_creatable_clubs: int = MAX_CREATED_CLUBS
    max_joinable_clubs: int = MAX_JOINED_CLUBS
    messages: List['Message'] = field(default_factory=list)

@dataclass
class Player:
    user_id: str
    name: str
    singles_rating: Optional[float] = None
    doubles_rating: Optional[float] = None
    experience: float = 0.0
    singles_matches: List['Match'] = field(default_factory=list)
    doubles_matches: List['DoublesMatch'] = field(default_factory=list)
    # ratings suggested by other players before any official matches
    pre_ratings: Dict[str, float] = field(default_factory=dict)
    # optional demographic fields for leaderboard filtering
    age: Optional[int] = None
    gender: Optional[str] = None
    avatar: Optional[str] = None
    birth: Optional[str] = None
    handedness: Optional[str] = None
    backhand: Optional[str] = None
    region: Optional[str] = None
    # date the player joined the club
    joined: datetime.date = field(default_factory=datetime.date.today)


# Player objects are loaded via :mod:`tennis.storage`.
# No runtime state is kept in this module.

@dataclass
class JoinApplication:
    """Data for a pending join request."""

    reason: str | None = None
    singles_rating: float | None = None
    doubles_rating: float | None = None


@dataclass
class Club:
    club_id: str
    name: str
    logo: str | None = None
    region: str | None = None
    slogan: str | None = None
    leader_id: str | None = None

    admin_ids: Set[str] = field(default_factory=set)
    pending_members: Dict[str, JoinApplication] = field(default_factory=dict)
    # store rejection reasons for previously denied join requests
    rejected_members: Dict[str, str] = field(default_factory=dict)
    banned_ids: Set[str] = field(default_factory=set)
    members: Dict[str, Player] = field(default_factory=dict)
    # track per-member join date
    member_joined: Dict[str, datetime.date] = field(default_factory=dict)
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
    club_id: str | None = None
    id: int | None = None
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
    approved_ts: datetime.datetime | None = None
    created: datetime.date = field(default_factory=datetime.date.today)
    created_ts: datetime.datetime = field(default_factory=datetime.datetime.now)
    confirmed_on: datetime.date | None = None
    status: str | None = None
    status_date: datetime.date | None = None


@dataclass
class DoublesMatch:
    date: datetime.date
    player_a1: Player
    player_a2: Player
    player_b1: Player
    player_b2: Player
    score_a: int
    score_b: int
    club_id: str | None = None
    id: int | None = None
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
    approved_ts: datetime.datetime | None = None
    created: datetime.date = field(default_factory=datetime.date.today)
    created_ts: datetime.datetime = field(default_factory=datetime.datetime.now)
    confirmed_on: datetime.date | None = None
    status: str | None = None
    status_date: datetime.date | None = None


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

@dataclass
class UserSubscribe:
    user_id: str
    scene: str
    quota: int = 0


@dataclass
class SubscribeLog:
    user_id: str
    scene: str
    errcode: int
    errmsg: str | None = None
    retries: int = 0
