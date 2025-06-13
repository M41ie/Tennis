from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import secrets
from pydantic import BaseModel, StrictInt
import statistics
import datetime
import json
import os
import urllib.request
import urllib.parse
from pathlib import Path

import tennis.storage as storage
from .storage import load_data, save_data, load_users, save_users
from .cli import (
    register_user,
    login_user,
    request_join,
    approve_member,
    add_player as cli_add_player,
    remove_member as cli_remove_member,
    toggle_admin as cli_toggle_admin,
    transfer_leader as cli_transfer_leader,
    resign_admin as cli_resign_admin,
    quit_club as cli_quit_club,
    create_club as cli_create_club,
    hash_password,
    validate_scores,
    update_player as cli_update_player,
)
from .rating import (
    update_ratings,
    update_doubles_ratings,
    weighted_rating,
    weighted_doubles_rating,
    format_weight_from_name,
    weighted_singles_matches,
    weighted_doubles_matches,
)
from .models import Player, Club, Match, DoublesMatch, Appointment, User, players

app = FastAPI()


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": exc.errors()})

clubs = load_data()
users = load_users()

# token persistence file next to the database
TOKENS_FILE = Path(str(storage.DB_FILE)).with_name("tokens.json")

# tokens expire after 24 hours
TOKEN_TTL = datetime.timedelta(hours=24)

# simple in-memory token store mapping token -> (user_id, timestamp)
def _load_tokens() -> dict[str, tuple[str, datetime.datetime]]:
    try:
        text = TOKENS_FILE.read_text()
    except FileNotFoundError:
        return {}
    except OSError:
        # if the file is unreadable we simply skip loading tokens
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    now = datetime.datetime.utcnow()
    result: dict[str, tuple[str, datetime.datetime]] = {}
    for tok, (uid, ts) in data.items():
        ts_dt = datetime.datetime.fromisoformat(ts)
        if now - ts_dt < TOKEN_TTL:
            result[tok] = (uid, ts_dt)
    return result


def _save_tokens() -> None:
    try:
        TOKENS_FILE.write_text(
            json.dumps({t: (uid, ts.isoformat()) for t, (uid, ts) in tokens.items()})
        )
    except OSError:
        # Failing to persist tokens should not block authentication
        pass

# load tokens on startup
tokens: dict[str, tuple[str, datetime.datetime]] = _load_tokens()

# WeChat mini program credentials from environment (optional)
WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")


def _generate_club_id() -> str:
    """Return a unique club id based on existing clubs."""
    i = 1
    while f"c{i}" in clubs:
        i += 1
    return f"c{i}"


def _exchange_wechat_code(code: str) -> dict:
    """Call WeChat API to exchange login code for session info."""
    params = urllib.parse.urlencode(
        {
            "appid": WECHAT_APPID,
            "secret": WECHAT_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    url = "https://api.weixin.qq.com/sns/jscode2session?" + params
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


def require_auth(token: str) -> str:
    """Validate token and return the associated user id."""
    info = tokens.get(token)
    if not info:
        raise HTTPException(401, "Invalid token")
    user_id, ts = info
    if datetime.datetime.utcnow() - ts > TOKEN_TTL:
        tokens.pop(token, None)
        _save_tokens()
        raise HTTPException(401, "Token expired")
    return user_id


def _pending_status_for_user(
    user_id: str, match: Match | DoublesMatch, club: Club
) -> dict[str, object]:
    """Return status information for the given user viewing a pending match."""

    admins = {club.leader_id, *club.admin_ids}
    is_admin = user_id in admins

    if user_id == match.initiator:
        role = "submitter"
    else:
        if isinstance(match, DoublesMatch):
            team_a = {match.player_a1.user_id, match.player_a2.user_id}
            team_b = {match.player_b1.user_id, match.player_b2.user_id}

            if user_id in team_a:
                role = "teammate"
            elif user_id in team_b:
                role = "opponent"
            elif user_id in admins:
                role = "admin"
            else:
                role = "viewer"
        else:
            participants = {match.player_a.user_id, match.player_b.user_id}

            if user_id in participants:
                role = "opponent"
            elif user_id in admins:
                role = "admin"
            else:
                role = "viewer"

    confirmed_self = None
    confirmed_opp = None
    if isinstance(match, DoublesMatch):
        if user_id in {match.player_a1.user_id, match.player_a2.user_id}:
            confirmed_self = match.confirmed_a
            confirmed_opp = match.confirmed_b
        elif user_id in {match.player_b1.user_id, match.player_b2.user_id}:
            confirmed_self = match.confirmed_b
            confirmed_opp = match.confirmed_a
    else:
        if user_id == match.player_a.user_id:
            confirmed_self = match.confirmed_a
            confirmed_opp = match.confirmed_b
        elif user_id == match.player_b.user_id:
            confirmed_self = match.confirmed_b
            confirmed_opp = match.confirmed_a

    can_confirm = False
    can_decline = False
    status_text = ""

    if role == "submitter":
        if not (match.confirmed_a and match.confirmed_b):
            status_text = "您已提交，等待对手确认"
        else:
            status_text = "对手已确认，等待管理员审核"
    elif role == "teammate":
        if not match.confirmed_b:
            status_text = "您的队友已确认，等待对手确认"
        else:
            status_text = "对手和队友已确认，等待管理员审核"
    elif role == "opponent":
        if confirmed_self is False:
            can_confirm = True
            can_decline = True
            status_text = "对手提交了比赛战绩，请确认"
        else:
            status_text = "您已确认，等待管理员审核"
    elif role == "admin":
        status_text = "双方已确认，请审核"
    else:
        if match.confirmed_a and match.confirmed_b:
            status_text = "等待管理员审核"
        else:
            status_text = "待确认"

    if is_admin and match.confirmed_a and match.confirmed_b:
        role = "admin"
        status_text = "双方已确认，请审核"
        can_confirm = False
        can_decline = False

    return {
        "display_status_text": status_text,
        "can_confirm": can_confirm,
        "can_decline": can_decline,
        "current_user_role_in_match": role,
    }


def _club_stats(club: Club) -> dict[str, object]:
    """Aggregate statistics for a club."""
    singles = [p.singles_rating for p in club.members.values() if p.singles_rating is not None]
    doubles = [p.doubles_rating for p in club.members.values() if p.doubles_rating is not None]
    total_singles = sum(len(p.singles_matches) for p in club.members.values()) // 2
    total_doubles = sum(len(p.doubles_matches) for p in club.members.values()) // 4
    singles_avg = statistics.mean(singles) if singles else 0
    doubles_avg = statistics.mean(doubles) if doubles else 0
    return {
        "member_count": len(club.members),
        "singles_rating_range": [min(singles) if singles else 0, max(singles) if singles else 0],
        "doubles_rating_range": [min(doubles) if doubles else 0, max(doubles) if doubles else 0],
        "singles_avg_rating": singles_avg,
        "doubles_avg_rating": doubles_avg,
        "total_singles_matches": total_singles,
        "total_doubles_matches": total_doubles,
    }


class ClubCreate(BaseModel):
    club_id: str | None = None
    name: str
    user_id: str
    token: str
    logo: str | None = None
    region: str | None = None
    slogan: str | None = None


class ClubUpdate(BaseModel):
    user_id: str
    token: str
    name: str | None = None
    logo: str | None = None
    region: str | None = None
    slogan: str | None = None


class PlayerCreate(BaseModel):
    user_id: str
    name: str
    token: str
    age: int | None = None
    gender: str | None = None
    avatar: str | None = None
    birth: str | None = None
    handedness: str | None = None
    backhand: str | None = None
    region: str | None = None


class PlayerUpdate(BaseModel):
    user_id: str
    token: str
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    avatar: str | None = None
    birth: str | None = None
    handedness: str | None = None
    backhand: str | None = None
    region: str | None = None


class MatchCreate(BaseModel):
    user_id: str
    user_a: str
    user_b: str
    score_a: StrictInt
    score_b: StrictInt
    date: datetime.date | None = None
    format: str | None = None
    weight: float | None = None
    location: str | None = None
    token: str


class PendingMatchCreate(BaseModel):
    club_id: str | None = None  # optional alternate clubs
    initiator: str
    opponent: str
    score_initiator: StrictInt
    score_opponent: StrictInt
    date: datetime.date | None = None
    format: str | None = None
    weight: float | None = None
    location: str | None = None
    token: str


class PreRateRequest(BaseModel):
    rater_id: str
    target_id: str
    rating: float
    token: str


class PendingDoublesCreate(BaseModel):
    club_id: str | None = None
    initiator: str
    partner: str
    opponent1: str
    opponent2: str
    score_initiator: StrictInt
    score_opponent: StrictInt
    date: datetime.date | None = None
    format: str | None = None
    weight: float | None = None
    location: str | None = None
    token: str


class AppointmentCreate(BaseModel):
    user_id: str
    date: datetime.date
    token: str
    location: str | None = None
    info: str | None = None


class SignupRequest(BaseModel):
    user_id: str
    token: str


class UserCreate(BaseModel):
    user_id: str | None = None
    name: str
    password: str
    allow_create: bool = False
    avatar: str | None = None
    gender: str | None = None
    birth: str | None = None
    handedness: str | None = None
    backhand: str | None = None
    region: str | None = None


class LoginRequest(BaseModel):
    user_id: str
    password: str


class LogoutRequest(BaseModel):
    token: str


class WeChatLoginRequest(BaseModel):
    code: str


class JoinRequest(BaseModel):
    user_id: str
    token: str
    singles_rating: float | None = None
    doubles_rating: float | None = None
    reason: str | None = None


class ApproveRequest(BaseModel):
    approver_id: str
    user_id: str
    rating: float
    admin: bool = False
    token: str


class RemoveRequest(BaseModel):
    remover_id: str
    token: str
    ban: bool = False


class TokenOnly(BaseModel):
    token: str


class RoleRequest(BaseModel):
    user_id: str
    action: str
    token: str


@app.post("/users")
def register_user_api(data: UserCreate):
    if data.user_id and data.user_id in users:
        raise HTTPException(400, "User exists")
    uid = register_user(
        users,
        data.user_id,
        data.name,
        data.password,
        allow_create=data.allow_create,
        avatar=data.avatar,
        gender=data.gender,
        birth=data.birth,
        handedness=data.handedness,
        backhand=data.backhand,
        region=data.region,
    )
    save_users(users)
    save_data(clubs)
    return {"status": "ok", "user_id": uid}


@app.post("/login")
def login_api(data: LoginRequest):
    if login_user(users, data.user_id, data.password):
        token = secrets.token_hex(16)
        tokens[token] = (data.user_id, datetime.datetime.utcnow())
        _save_tokens()
        return {"success": True, "token": token}
    return {"success": False}


@app.post("/wechat_login")
def wechat_login_api(data: WeChatLoginRequest):
    """Login or register using a WeChat mini program code."""
    info = _exchange_wechat_code(data.code)
    openid = info.get("openid")
    if not openid:
        raise HTTPException(400, "Invalid code")

    user = None
    for u in users.values():
        if u.wechat_openid == openid:
            user = u
            break

    if not user:
        uid = openid
        user = User(
            user_id=uid,
            name=info.get("nickname", uid),
            password_hash="",
            wechat_openid=openid,
        )
        users[uid] = user
        if uid not in players:
            players[uid] = Player(user_id=uid, name=user.name)
        save_users(users)
        save_data(clubs)

    token = secrets.token_hex(16)
    tokens[token] = (user.user_id, datetime.datetime.utcnow())
    _save_tokens()
    return {"token": token, "user_id": user.user_id}


@app.post("/logout")
def logout_api(data: LogoutRequest):
    tokens.pop(data.token, None)
    _save_tokens()
    return {"status": "ok"}


@app.post("/check_token")
def check_token_api(data: TokenOnly):
    """Validate and refresh a token."""
    info = tokens.get(data.token)
    if not info:
        raise HTTPException(401, "Invalid token")
    uid, _ = info
    tokens[data.token] = (uid, datetime.datetime.utcnow())
    _save_tokens()
    return {"status": "ok", "user_id": uid}


@app.get("/users/{user_id}")
def get_user_info(user_id: str):
    """Return basic user info including joined clubs and permissions."""
    user = users.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    joined = [cid for cid, c in clubs.items() if user_id in c.members]
    return {
        "user_id": user.user_id,
        "name": user.name,
        "joined_clubs": joined,
        "can_create_club": user.can_create_club,
    }


@app.get("/users/{user_id}/messages")
def get_user_messages(user_id: str, token: str):
    uid = require_auth(token)
    if uid != user_id:
        raise HTTPException(401, "Token mismatch")
    user = users.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return [
        {"date": m.date.isoformat(), "text": m.text, "read": m.read}
        for m in user.messages
    ]


@app.get("/users/{user_id}/messages/unread_count")
def get_unread_count(user_id: str, token: str):
    """Return the number of unread messages for the user."""
    uid = require_auth(token)
    if uid != user_id:
        raise HTTPException(401, "Token mismatch")
    user = users.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return {"unread": sum(1 for m in user.messages if not m.read)}


@app.post("/users/{user_id}/messages/{index}/read")
def mark_message_read(user_id: str, index: int, data: TokenOnly):
    uid = require_auth(data.token)
    if uid != user_id:
        raise HTTPException(401, "Token mismatch")
    user = users.get(user_id)
    if not user or index >= len(user.messages):
        raise HTTPException(404, "Message not found")
    user.messages[index].read = True
    save_users(users)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/join")
def join_club(club_id: str, data: JoinRequest):
    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    try:
        request_join(
            clubs,
            users,
            club_id,
            data.user_id,
            singles_rating=data.singles_rating,
            doubles_rating=data.doubles_rating,
            reason=data.reason,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "ok"}


@app.patch("/clubs/{club_id}")
def update_club_info(club_id: str, data: ClubUpdate):
    """Update club basic information (leader or admin only)."""
    user = require_auth(data.token)
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    if user != club.leader_id and user not in club.admin_ids:
        raise HTTPException(403, "Forbidden")
    if data.name is not None:
        club.name = data.name
    if data.logo is not None:
        club.logo = data.logo
    if data.region is not None:
        club.region = data.region
    if data.slogan is not None:
        club.slogan = data.slogan
    save_data(clubs)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/approve")
def approve_club_member(club_id: str, data: ApproveRequest):
    user = require_auth(data.token)
    if user != data.approver_id:
        raise HTTPException(401, "Token mismatch")
    try:
        approve_member(
            clubs,
            users,
            club_id,
            data.approver_id,
            data.user_id,
            data.rating,
            make_admin=data.admin,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "ok"}


@app.get("/clubs")
def list_clubs():
    return [{"club_id": c.club_id, "name": c.name} for c in clubs.values()]


@app.post("/clubs")
def create_club(data: ClubCreate):
    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    club_id = data.club_id or _generate_club_id()
    try:
        cli_create_club(
            users,
            clubs,
            data.user_id,
            club_id,
            data.name,
            data.logo,
            data.region,
            data.slogan,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "ok", "club_id": club_id}


@app.get("/clubs/{club_id}")
def get_club_info(club_id: str):
    """Return basic club information including members and pending requests."""
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    return {
        "club_id": club.club_id,
        "name": club.name,
        "logo": club.logo,
        "region": club.region,
        "slogan": club.slogan,
        "leader_id": club.leader_id,
        "admin_ids": list(club.admin_ids),
        "pending_members": [
            {
                "user_id": uid,
                "reason": info.reason,
                "singles_rating": info.singles_rating,
                "doubles_rating": info.doubles_rating,
            }
            for uid, info in club.pending_members.items()
        ],
        "members": [
            {"user_id": p.user_id, "name": p.name} for p in club.members.values()
        ],
        "stats": _club_stats(club),
    }


@app.get("/clubs/{club_id}/players")
def list_players(
    club_id: str,
    doubles: bool = False,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    gender: str | None = None,
):
    """Return members of a club optionally filtered and sorted by rating."""

    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")

    today = datetime.date.today()
    get_rating = weighted_doubles_rating if doubles else weighted_rating

    players = []
    for p in club.members.values():
        rating = get_rating(p, today)
        singles_count = weighted_singles_matches(p)
        doubles_count = weighted_doubles_matches(p)
        if min_rating is not None and (rating is None or rating < min_rating):
            continue
        if max_rating is not None and (rating is None or rating > max_rating):
            continue
        if min_age is not None and (p.age is None or p.age < min_age):
            continue
        if max_age is not None and (p.age is None or p.age > max_age):
            continue
        if gender is not None and p.gender != gender:
            continue
        players.append(
            {
                "user_id": p.user_id,
                "name": p.name,
                "avatar": p.avatar,
                "gender": p.gender,
                "joined": p.joined.isoformat(),
                "rating": rating,
                "weighted_singles_matches": round(singles_count, 2),
                "weighted_doubles_matches": round(doubles_count, 2),
            }
        )

    players.sort(key=lambda x: x["rating"] if x["rating"] is not None else float('-inf'), reverse=True)
    return players


@app.get("/players/{user_id}")
def get_global_player(user_id: str, recent: int = 0):
    """Return player information without requiring a club."""
    player = players.get(user_id)
    if not player:
        raise HTTPException(404, "Player not found")

    today = datetime.date.today()
    singles = weighted_rating(player, today)
    doubles = weighted_doubles_rating(player, today)
    singles_count = weighted_singles_matches(player)
    doubles_count = weighted_doubles_matches(player)

    result = {
        "user_id": player.user_id,
        "id": player.user_id,
        "name": player.name,
        "avatar": player.avatar,
        "avatar_url": player.avatar,
        "birth": player.birth,
        "gender": player.gender,
        "handedness": player.handedness,
        "backhand": player.backhand,
        "joined": player.joined.isoformat(),
        "singles_rating": singles,
        "doubles_rating": doubles,
        "rating_singles": singles,
        "rating_doubles": doubles,
        "weighted_singles_matches": round(singles_count, 2),
        "weighted_doubles_matches": round(doubles_count, 2),
        "weighted_games_singles": round(singles_count, 2),
        "weighted_games_doubles": round(doubles_count, 2),
    }

    if recent > 0:
        from .cli import get_player_match_cards

        cards = []
        # iterate across all clubs to collect matches for this player
        for club_id, club in clubs.items():
            if user_id not in club.members:
                continue
            try:
                match_cards = get_player_match_cards(clubs, club_id, user_id)
            except ValueError:
                continue
            for c in match_cards:
                c["date"] = c["date"].isoformat()
                cards.append(c)
        # sort by date descending and return most recent
        cards.sort(key=lambda x: x["date"], reverse=True)
        result["recent_records"] = cards[:recent]

    return result


@app.get("/players")
def list_all_players(
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    gender: str | None = None,
    club: str | None = None,
    doubles: bool = False,
):
    """Return players from one or more clubs optionally filtered and sorted."""

    # When no club parameter is provided, return an empty list so the
    # leaderboard correctly shows no players selected.
    if not club:
        return []

    club_ids = club.split(",")
    clubs_to_iter = []
    for cid in club_ids:
        c = clubs.get(cid)
        if not c:
            raise HTTPException(404, "Club not found")
        clubs_to_iter.append(c)
    today = datetime.date.today()
    get_rating = weighted_doubles_rating if doubles else weighted_rating
    players = []
    for c in clubs_to_iter:
        for p in c.members.values():
            rating = get_rating(p, today)
            singles_count = weighted_singles_matches(p)
            doubles_count = weighted_doubles_matches(p)
            if min_rating is not None and (rating is None or rating < min_rating):
                continue
            if max_rating is not None and (rating is None or rating > max_rating):
                continue
            if min_age is not None and (p.age is None or p.age < min_age):
                continue
            if max_age is not None and (p.age is None or p.age > max_age):
                continue
            if gender is not None and p.gender != gender:
                continue
            players.append(
                {
                    "club_id": c.club_id,
                    "user_id": p.user_id,
                    "name": p.name,
                    "avatar": p.avatar,
                    "gender": p.gender,
                    "joined": p.joined.isoformat(),
                    "rating": rating,
                    "weighted_singles_matches": round(singles_count, 2),
                    "weighted_doubles_matches": round(doubles_count, 2),
                }
            )
    players.sort(key=lambda x: x["rating"] if x["rating"] is not None else float('-inf'), reverse=True)
    return players


@app.post("/clubs/{club_id}/players")
def add_player(club_id: str, data: PlayerCreate):
    require_auth(data.token)
    try:
        cli_add_player(
            clubs,
            club_id,
            data.user_id,
            data.name,
            age=data.age,
            gender=data.gender,
            avatar=data.avatar,
            birth=data.birth,
            handedness=data.handedness,
            backhand=data.backhand,
            region=data.region,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


@app.patch("/clubs/{club_id}/players/{user_id}")
def update_player_api(club_id: str, user_id: str, data: PlayerUpdate):
    """Update existing player information."""
    user = require_auth(data.token)
    if user != data.user_id or data.user_id != user_id:
        raise HTTPException(401, "Token mismatch")
    try:
        cli_update_player(
            clubs,
            club_id,
            user_id,
            name=data.name,
            age=data.age,
            gender=data.gender,
            avatar=data.avatar,
            birth=data.birth,
            handedness=data.handedness,
            backhand=data.backhand,
            region=data.region,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


@app.delete("/clubs/{club_id}/members/{user_id}")
def remove_member_api(club_id: str, user_id: str, data: RemoveRequest):
    """Remove a club member (leader or admin only)."""
    user = require_auth(data.token)
    if user != data.remover_id:
        raise HTTPException(401, "Token mismatch")
    try:
        cli_remove_member(
            clubs,
            users,
            club_id,
            data.remover_id,
            user_id,
            ban=data.ban,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/role")
def update_role_api(club_id: str, data: RoleRequest):
    """Update member roles within a club."""
    actor = require_auth(data.token)
    try:
        if data.action == "toggle_admin":
            cli_toggle_admin(clubs, club_id, actor, data.user_id)
        elif data.action == "transfer_leader":
            cli_transfer_leader(clubs, club_id, actor, data.user_id)
        elif data.action == "resign_admin":
            if actor != data.user_id:
                raise ValueError("Token mismatch")
            cli_resign_admin(clubs, club_id, actor)
        elif data.action == "quit":
            if actor != data.user_id:
                raise ValueError("Token mismatch")
            cli_quit_club(clubs, users, club_id, actor)
        else:
            raise ValueError("Invalid action")
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "ok"}


@app.get("/clubs/{club_id}/pending_doubles")
def list_pending_doubles(club_id: str, token: str):
    """Return pending doubles matches for a club visible to the caller."""
    uid = require_auth(token)
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    from .models import DoublesMatch
    from .cli import cleanup_pending_matches

    cleanup_pending_matches(club)

    admins = {club.leader_id, *club.admin_ids}
    result = []
    today = datetime.date.today()
    for idx, m in sorted(
        enumerate(club.pending_matches),
        key=lambda x: (x[1].date, x[1].created_ts),
        reverse=True,
    ):
        if not isinstance(m, DoublesMatch):
            continue
        team_a = {m.player_a1.user_id, m.player_a2.user_id}
        team_b = {m.player_b1.user_id, m.player_b2.user_id}
        participants = team_a | team_b
        if m.status == "rejected":
            if uid != m.initiator:
                continue
        elif m.status == "vetoed":
            if uid not in participants:
                continue
        elif uid not in participants:
            if uid in admins and m.confirmed_a and m.confirmed_b:
                pass
            else:
                continue

        entry = {
            "index": idx,
            "date": m.date.isoformat(),
            "a1": m.player_a1.user_id,
            "a2": m.player_a2.user_id,
            "b1": m.player_b1.user_id,
            "b2": m.player_b2.user_id,
            "score_a": m.score_a,
            "score_b": m.score_b,
            "confirmed_a": m.confirmed_a,
            "confirmed_b": m.confirmed_b,
            "location": m.location,
            "format_name": m.format_name,
        }

        is_admin = uid in admins

        if uid == m.initiator:
            role = "submitter"
        elif uid in team_a:
            role = "teammate"
        elif uid in team_b:
            role = "opponent"
        elif is_admin:
            role = "admin"
        else:
            role = "viewer"

        confirmed_self = None
        confirmed_opp = None
        if uid in team_a:
            confirmed_self = m.confirmed_a
            confirmed_opp = m.confirmed_b
        elif uid in team_b:
            confirmed_self = m.confirmed_b
            confirmed_opp = m.confirmed_a

        can_confirm = False
        can_decline = False
        status_text = ""

        if m.status == "rejected":
            days_left = 3 - (today - (m.status_date or today)).days
            status_text = f"对手已拒绝，该记录将在{days_left}日后自动删除"
        elif m.status == "vetoed":
            days_left = 3 - (today - (m.status_date or today)).days
            status_text = f"管理员审核未通过，该记录将在{days_left}日后自动删除"
        else:
            if role == "submitter":
                if not (m.confirmed_a and m.confirmed_b):
                    status_text = "您已提交，等待对手确认"
                    wait_days = (today - m.created).days
                    if wait_days >= 4:
                        left = 7 - wait_days
                        status_text = f"该记录长时间未得到对手确认，将在{left}日后自动删除"
                else:
                    status_text = "对手已确认，等待管理员审核"
                    wait_days = (today - (m.confirmed_on or m.created)).days
                    if wait_days >= 4:
                        left = 7 - wait_days
                        status_text = f"该记录长时间未得到管理员审核，将在{left}日后自动删除"
            elif role in {"teammate", "opponent"}:
                if role == "teammate":
                    if not m.confirmed_b:
                        status_text = "您的队友已确认，等待对手确认"
                        wait_days = (today - m.created).days
                        if wait_days >= 4:
                            left = 7 - wait_days
                            status_text = f"该记录长时间未得到对手确认，将在{left}日后自动删除"
                    else:
                        status_text = "对手和队友已确认，等待管理员审核"
                        wait_days = (today - (m.confirmed_on or m.created)).days
                        if wait_days >= 4:
                            left = 7 - wait_days
                            status_text = f"该记录长时间未得到管理员审核，将在{left}日后自动删除"
                else:  # opponent
                    if confirmed_self is False:
                        can_confirm = True
                        can_decline = True
                        status_text = "对手提交了比赛战绩，请确认"
                    else:
                        status_text = "您的队友已确认，等待管理员审核"
                        wait_days = (today - (m.confirmed_on or m.created)).days
                        if wait_days >= 4:
                            left = 7 - wait_days
                            status_text = f"该记录长时间未得到管理员审核，将在{left}日后自动删除"
            elif role == "admin":
                status_text = "双方已确认，请审核"
            else:
                if m.confirmed_a and m.confirmed_b:
                    status_text = "等待管理员审核"
                else:
                    status_text = "待确认"

        if is_admin and m.confirmed_a and m.confirmed_b:
            role = "admin"
            status_text = "双方已确认，请审核"
            can_confirm = False
            can_decline = False

        entry.update(
            {
                "display_status_text": status_text,
                "can_confirm": can_confirm,
                "can_decline": can_decline,
                "current_user_role_in_match": role,
                "submitted_by_player_id": m.initiator,
            }
        )

        a1 = club.members.get(m.player_a1.user_id)
        a2 = club.members.get(m.player_a2.user_id)
        b1 = club.members.get(m.player_b1.user_id)
        b2 = club.members.get(m.player_b2.user_id)
        entry["a1_name"] = a1.name if a1 else m.player_a1.user_id
        entry["a2_name"] = a2.name if a2 else m.player_a2.user_id
        entry["b1_name"] = b1.name if b1 else m.player_b1.user_id
        entry["b2_name"] = b2.name if b2 else m.player_b2.user_id
        entry["rating_a1_before"] = a1.doubles_rating if a1 else None
        entry["rating_a2_before"] = a2.doubles_rating if a2 else None
        entry["rating_b1_before"] = b1.doubles_rating if b1 else None
        entry["rating_b2_before"] = b2.doubles_rating if b2 else None
        if m.initiator and (submitter := club.members.get(m.initiator)):
            entry["submitted_by_player_name"] = submitter.name

        result.append(entry)

    return result


@app.post("/clubs/{club_id}/prerate")
def pre_rate_api(club_id: str, data: PreRateRequest):
    user = require_auth(data.token)
    if user != data.rater_id:
        raise HTTPException(401, "Token mismatch")
    from .cli import pre_rate

    try:
        pre_rate(clubs, club_id, data.rater_id, data.target_id, data.rating)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


@app.get("/clubs/{club_id}/players/{user_id}")
def get_player(club_id: str, user_id: str, recent: int = 0):
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    player = club.members.get(user_id)
    if not player:
        raise HTTPException(404, "Player not found")
    today = datetime.date.today()
    singles = weighted_rating(player, today)
    doubles = weighted_doubles_rating(player, today)
    singles_count = weighted_singles_matches(player)
    doubles_count = weighted_doubles_matches(player)

    result = {
        "user_id": player.user_id,
        "id": player.user_id,
        "name": player.name,
        "avatar": player.avatar,
        "avatar_url": player.avatar,
        "birth": player.birth,
        "gender": player.gender,
        "handedness": player.handedness,
        "backhand": player.backhand,
        "joined": player.joined.isoformat(),
        "singles_rating": singles,
        "doubles_rating": doubles,
        "rating_singles": singles,
        "rating_doubles": doubles,
        "weighted_singles_matches": round(singles_count, 2),
        "weighted_doubles_matches": round(doubles_count, 2),
        "weighted_games_singles": round(singles_count, 2),
        "weighted_games_doubles": round(doubles_count, 2),
    }
    if recent > 0:
        from .cli import get_player_match_cards

        try:
            cards = get_player_match_cards(clubs, club_id, user_id)
        except ValueError as e:
            raise HTTPException(404, str(e))
        for c in cards:
            c["date"] = c["date"].isoformat()
        result["recent_records"] = cards[:recent]

    return result


@app.get("/clubs/{club_id}/players/{user_id}/records")
def get_player_records(club_id: str, user_id: str):
    from .cli import get_player_match_cards

    try:
        cards = get_player_match_cards(clubs, club_id, user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    # convert dates to iso strings
    for c in cards:
        c["date"] = c["date"].isoformat()
    return cards


@app.get("/clubs/{club_id}/players/{user_id}/doubles_records")
def get_player_doubles_records(club_id: str, user_id: str):
    """Return doubles match history cards for a player."""
    from .cli import get_player_doubles_cards

    try:
        cards = get_player_doubles_cards(clubs, club_id, user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    for c in cards:
        c["date"] = c["date"].isoformat()
    return cards


@app.post("/clubs/{club_id}/matches")
def record_match_api(club_id: str, data: MatchCreate):
    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    try:
        validate_scores(data.score_a, data.score_b)
    except ValueError as e:
        raise HTTPException(400, str(e))

    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    pa = club.members.get(data.user_a)
    pb = club.members.get(data.user_b)
    if not pa or not pb:
        raise HTTPException(400, "Players not found")
    date = data.date or datetime.date.today()
    weight = data.weight
    if data.format:
        weight = format_weight_from_name(data.format)
    if weight is None:
        weight = format_weight_from_name("6_game")
    match = Match(
        date=date,
        player_a=pa,
        player_b=pb,
        score_a=data.score_a,
        score_b=data.score_b,
        format_weight=weight,
        location=data.location,
        format_name=data.format,
    )
    update_ratings(match)
    club.matches.append(match)
    pa.singles_rating = weighted_rating(pa, date)
    pb.singles_rating = weighted_rating(pb, date)
    save_data(clubs)
    return {"status": "ok"}


@app.get("/clubs/{club_id}/pending_matches")
def list_pending_matches(club_id: str, token: str):
    """Return pending singles matches for a club visible to the caller."""
    uid = require_auth(token)
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    from .cli import cleanup_pending_matches
    cleanup_pending_matches(club)
    result = []
    admins = {club.leader_id, *club.admin_ids}
    today = datetime.date.today()
    for idx, m in sorted(
        enumerate(club.pending_matches),
        key=lambda x: (x[1].date, x[1].created_ts),
        reverse=True,
    ):
        from .models import DoublesMatch

        if isinstance(m, DoublesMatch):
            continue
        participants = {m.player_a.user_id, m.player_b.user_id}
        if m.status == "rejected":
            if uid != m.initiator:
                continue
        elif m.status == "vetoed":
            if uid not in participants:
                continue
        elif uid not in participants:
            if uid in admins and m.confirmed_a and m.confirmed_b:
                pass
            else:
                continue

        entry = {
            "index": idx,
            "date": m.date.isoformat(),
            "player_a": m.player_a.user_id,
            "player_b": m.player_b.user_id,
            "score_a": m.score_a,
            "score_b": m.score_b,
            "confirmed_a": m.confirmed_a,
            "confirmed_b": m.confirmed_b,
            "location": m.location,
            "format_name": m.format_name,
        }

        is_admin = uid in admins

        if uid == m.initiator:
            role = "submitter"
        elif uid in participants:
            role = "opponent"
        elif is_admin:
            role = "admin"
        else:
            role = "viewer"

        confirmed_self = None
        confirmed_opp = None
        if uid == m.player_a.user_id:
            confirmed_self = m.confirmed_a
            confirmed_opp = m.confirmed_b
        elif uid == m.player_b.user_id:
            confirmed_self = m.confirmed_b
            confirmed_opp = m.confirmed_a

        can_confirm = False
        can_decline = False
        status_text = ""

        if m.status == "rejected":
            days_left = 3 - (today - (m.status_date or today)).days
            status_text = f"对手已拒绝，该记录将在{days_left}日后自动删除"
        elif m.status == "vetoed":
            days_left = 3 - (today - (m.status_date or today)).days
            status_text = f"管理员审核未通过，该记录将在{days_left}日后自动删除"
        else:
            if role == "submitter":
                if not (m.confirmed_a and m.confirmed_b):
                    status_text = "您已提交，等待对手确认"
                    wait_days = (today - m.created).days
                    if wait_days >= 4:
                        left = 7 - wait_days
                        status_text = f"该记录长时间未得到对手确认，将在{left}日后自动删除"
                else:
                    status_text = "对手已确认，等待管理员审核"
                    wait_days = (today - (m.confirmed_on or m.created)).days
                    if wait_days >= 4:
                        left = 7 - wait_days
                        status_text = f"该记录长时间未得到管理员审核，将在{left}日后自动删除"
            elif role == "opponent":
                if confirmed_self is False:
                    can_confirm = True
                    can_decline = True
                    status_text = "对手提交了比赛战绩，请确认"
                else:
                    status_text = "您已确认，等待管理员审核"
                    wait_days = (today - (m.confirmed_on or m.created)).days
                    if wait_days >= 4:
                        left = 7 - wait_days
                        status_text = f"该记录长时间未得到管理员审核，将在{left}日后自动删除"
            elif role == "admin":
                status_text = "双方已确认，请审核"
            else:  # viewer
                if m.confirmed_a and m.confirmed_b:
                    status_text = "等待管理员审核"
                else:
                    status_text = "待确认"

        if is_admin and m.confirmed_a and m.confirmed_b:
            role = "admin"
            status_text = "双方已确认，请审核"
            can_confirm = False
            can_decline = False

        entry.update(
            {
                "display_status_text": status_text,
                "can_confirm": can_confirm,
                "can_decline": can_decline,
                "current_user_role_in_match": role,
                "submitted_by_player_id": m.initiator,
            }
        )

        pa = club.members.get(m.player_a.user_id)
        pb = club.members.get(m.player_b.user_id)
        entry["player_a_name"] = pa.name if pa else m.player_a.user_id
        entry["player_b_name"] = pb.name if pb else m.player_b.user_id
        entry["rating_a_before"] = pa.singles_rating if pa else None
        entry["rating_b_before"] = pb.singles_rating if pb else None
        if m.initiator and (submitter := club.members.get(m.initiator)):
            entry["submitted_by_player_name"] = submitter.name

        result.append(entry)

    return result


@app.post("/clubs/{club_id}/pending_matches")
def submit_match_api(club_id: str, data: PendingMatchCreate):
    from .cli import submit_match

    user = require_auth(data.token)
    if user != data.initiator:
        raise HTTPException(401, "Token mismatch")

    cid = data.club_id or club_id
    try:
        validate_scores(data.score_initiator, data.score_opponent)
        submit_match(
            clubs,
            cid,
            data.initiator,
            data.opponent,
            data.score_initiator,
            data.score_opponent,
            data.date or datetime.date.today(),
            data.weight or (format_weight_from_name(data.format) if data.format else format_weight_from_name("6_game")),
            location=data.location,
            format_name=data.format,
            users=users,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "pending"}


class ConfirmRequest(BaseModel):
    user_id: str
    token: str


class ApproveMatchRequest(BaseModel):
    approver: str
    token: str


@app.post("/clubs/{club_id}/pending_matches/{index}/confirm")
def confirm_match_api(club_id: str, index: int, data: ConfirmRequest):
    from .cli import confirm_match

    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")

    try:
        confirm_match(clubs, club_id, index, data.user_id, users)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_matches/{index}/reject")
def reject_match_api(club_id: str, index: int, data: ConfirmRequest):
    """Participant rejects a pending singles match."""
    from .cli import reject_match

    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")

    try:
        reject_match(clubs, club_id, index, data.user_id, users)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "rejected"}


@app.post("/clubs/{club_id}/pending_matches/{index}/approve")
def approve_match_api(club_id: str, index: int, data: ApproveMatchRequest):
    from .cli import approve_match

    user = require_auth(data.token)
    if user != data.approver:
        raise HTTPException(401, "Token mismatch")

    try:
        approve_match(clubs, club_id, index, data.approver, users)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_matches/{index}/veto")
def veto_match_api(club_id: str, index: int, data: ApproveMatchRequest):
    """Admin vetoes a pending singles match."""
    from .cli import veto_match

    user = require_auth(data.token)
    if user != data.approver:
        raise HTTPException(401, "Token mismatch")

    try:
        veto_match(clubs, club_id, index, data.approver, users)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "vetoed"}


@app.post("/clubs/{club_id}/pending_doubles")
def submit_doubles_api(club_id: str, data: PendingDoublesCreate):
    from .cli import submit_doubles

    user = require_auth(data.token)
    if user != data.initiator:
        raise HTTPException(401, "Token mismatch")

    cid = data.club_id or club_id
    try:
        validate_scores(data.score_initiator, data.score_opponent)
        submit_doubles(
            clubs,
            cid,
            data.initiator,
            data.partner,
            data.opponent1,
            data.opponent2,
            data.score_initiator,
            data.score_opponent,
            data.date or datetime.date.today(),
            data.weight or (
                format_weight_from_name(data.format)
                if data.format
                else format_weight_from_name("6_game")
            ),
            location=data.location,
            format_name=data.format,
            users=users,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "pending"}


@app.post("/clubs/{club_id}/pending_doubles/{index}/confirm")
def confirm_doubles_api(club_id: str, index: int, data: ConfirmRequest):
    from .cli import confirm_doubles

    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")

    try:
        confirm_doubles(clubs, club_id, index, data.user_id, users)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_doubles/{index}/reject")
def reject_doubles_api(club_id: str, index: int, data: ConfirmRequest):
    """Participant rejects a pending doubles match."""
    from .cli import reject_doubles

    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")

    try:
        reject_doubles(clubs, club_id, index, data.user_id, users)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "rejected"}


@app.post("/clubs/{club_id}/pending_doubles/{index}/approve")
def approve_doubles_api(club_id: str, index: int, data: ApproveMatchRequest):
    from .cli import approve_doubles

    user = require_auth(data.token)
    if user != data.approver:
        raise HTTPException(401, "Token mismatch")

    try:
        approve_doubles(clubs, club_id, index, data.approver, users)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_doubles/{index}/veto")
def veto_doubles_api(club_id: str, index: int, data: ApproveMatchRequest):
    """Admin vetoes a pending doubles match."""
    from .cli import veto_doubles

    user = require_auth(data.token)
    if user != data.approver:
        raise HTTPException(401, "Token mismatch")

    try:
        veto_doubles(clubs, club_id, index, data.approver, users)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "vetoed"}


@app.post("/clubs/{club_id}/appointments")
def create_appointment(club_id: str, data: AppointmentCreate):
    """Create a new appointment in a club."""
    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    if data.user_id not in club.members and data.user_id != club.leader_id:
        raise HTTPException(400, "Not a member")
    appt = Appointment(
        date=data.date,
        creator=data.user_id,
        location=data.location,
        info=data.info,
    )
    club.appointments.append(appt)
    save_data(clubs)
    return {"status": "ok"}


@app.get("/clubs/{club_id}/appointments")
def list_appointments(club_id: str):
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    result = []
    for idx, a in enumerate(club.appointments):
        result.append(
            {
                "index": idx,
                "date": a.date.isoformat(),
                "creator": a.creator,
                "location": a.location,
                "info": a.info,
                "signups": list(a.signups),
            }
        )
    return result


@app.post("/clubs/{club_id}/appointments/{index}/signup")
def signup_appointment(club_id: str, index: int, data: SignupRequest):
    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    if index >= len(club.appointments):
        raise HTTPException(404, "Appointment not found")
    if data.user_id not in club.members:
        raise HTTPException(400, "Not a member")
    club.appointments[index].signups.add(data.user_id)
    save_data(clubs)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/appointments/{index}/cancel")
def cancel_signup(club_id: str, index: int, data: SignupRequest):
    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    if index >= len(club.appointments):
        raise HTTPException(404, "Appointment not found")
    club.appointments[index].signups.discard(data.user_id)
    save_data(clubs)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
