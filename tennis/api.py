from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import secrets
from pydantic import BaseModel, StrictInt
import datetime
import json
from pathlib import Path

import tennis.storage as storage
from .storage import load_data, save_data, load_users, save_users
from .cli import (
    register_user,
    login_user,
    request_join,
    approve_member,
    remove_member as cli_remove_member,
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
)
from .models import Player, Club, Match, Appointment

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
        data = json.loads(TOKENS_FILE.read_text())
    except FileNotFoundError:
        return {}
    now = datetime.datetime.utcnow()
    result: dict[str, tuple[str, datetime.datetime]] = {}
    for tok, (uid, ts) in data.items():
        ts_dt = datetime.datetime.fromisoformat(ts)
        if now - ts_dt < TOKEN_TTL:
            result[tok] = (uid, ts_dt)
    return result


def _save_tokens() -> None:
    TOKENS_FILE.write_text(
        json.dumps({t: (uid, ts.isoformat()) for t, (uid, ts) in tokens.items()})
    )

# load tokens on startup
tokens: dict[str, tuple[str, datetime.datetime]] = _load_tokens()


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


class ClubCreate(BaseModel):
    club_id: str
    name: str
    user_id: str
    token: str
    logo: str | None = None
    region: str | None = None


class PlayerCreate(BaseModel):
    user_id: str
    name: str
    token: str
    age: int | None = None
    gender: str | None = None
    avatar: str | None = None


class PlayerUpdate(BaseModel):
    user_id: str
    token: str
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    avatar: str | None = None


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
    a1: str
    a2: str
    b1: str
    b2: str
    score_a: StrictInt
    score_b: StrictInt
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
    user_id: str
    name: str
    password: str
    allow_create: bool = False


class LoginRequest(BaseModel):
    user_id: str
    password: str


class LogoutRequest(BaseModel):
    token: str


class JoinRequest(BaseModel):
    user_id: str
    token: str


class ApproveRequest(BaseModel):
    approver_id: str
    user_id: str
    admin: bool = False
    token: str


class RemoveRequest(BaseModel):
    remover_id: str
    token: str
    ban: bool = False


@app.post("/users")
def register_user_api(data: UserCreate):
    if data.user_id in users:
        raise HTTPException(400, "User exists")
    register_user(
        users,
        data.user_id,
        data.name,
        data.password,
        allow_create=data.allow_create,
    )
    save_users(users)
    return {"status": "ok"}


@app.post("/login")
def login_api(data: LoginRequest):
    if login_user(users, data.user_id, data.password):
        token = secrets.token_hex(16)
        tokens[token] = (data.user_id, datetime.datetime.utcnow())
        _save_tokens()
        return {"success": True, "token": token}
    return {"success": False}


@app.post("/logout")
def logout_api(data: LogoutRequest):
    tokens.pop(data.token, None)
    _save_tokens()
    return {"status": "ok"}


@app.post("/clubs/{club_id}/join")
def join_club(club_id: str, data: JoinRequest):
    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")
    try:
        request_join(clubs, users, club_id, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
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
    try:
        cli_create_club(
            users,
            clubs,
            data.user_id,
            data.club_id,
            data.name,
            data.logo,
            data.region,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    save_users(users)
    return {"status": "ok"}


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
        if min_rating is not None and rating < min_rating:
            continue
        if max_rating is not None and rating > max_rating:
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
                "rating": rating,
            }
        )

    players.sort(key=lambda x: x["rating"], reverse=True)
    return players


@app.get("/players")
def list_all_players(
    min_rating: float | None = None,
    max_rating: float | None = None,
    gender: str | None = None,
    club: str | None = None,
    doubles: bool = False,
):
    if club:
        c = clubs.get(club)
        if not c:
            raise HTTPException(404, "Club not found")
        clubs_to_iter = [c]
    else:
        clubs_to_iter = clubs.values()
    today = datetime.date.today()
    get_rating = weighted_doubles_rating if doubles else weighted_rating
    players = []
    for c in clubs_to_iter:
        for p in c.members.values():
            rating = get_rating(p, today)
            if min_rating is not None and rating < min_rating:
                continue
            if max_rating is not None and rating > max_rating:
                continue
            if gender is not None and p.gender != gender:
                continue
            players.append(
                {
                    "club_id": c.club_id,
                    "user_id": p.user_id,
                    "name": p.name,
                    "avatar": p.avatar,
                    "rating": rating,
                }
            )
    players.sort(key=lambda x: x["rating"], reverse=True)
    return players


@app.post("/clubs/{club_id}/players")
def add_player(club_id: str, data: PlayerCreate):
    require_auth(data.token)
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    if data.user_id in club.members:
        raise HTTPException(400, "Player exists")
    club.members[data.user_id] = Player(
        user_id=data.user_id,
        name=data.name,
        age=data.age,
        gender=data.gender,
        avatar=data.avatar,
    )
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


@app.get("/clubs/{club_id}/pending_doubles")
def list_pending_doubles(club_id: str):
    """Return pending doubles matches for a club."""
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    from .models import DoublesMatch

    result = []
    for idx, m in enumerate(club.pending_matches):
        if not isinstance(m, DoublesMatch):
            continue
        result.append(
            {
                "index": idx,
                "date": m.date.isoformat(),
                "a1": m.player_a1.user_id,
                "a2": m.player_a2.user_id,
                "b1": m.player_b1.user_id,
                "b2": m.player_b2.user_id,
                "score_a": m.score_a,
                "score_b": m.score_b,
            }
        )
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
def get_player(club_id: str, user_id: str):
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    player = club.members.get(user_id)
    if not player:
        raise HTTPException(404, "Player not found")
    today = datetime.date.today()
    return {
        "user_id": player.user_id,
        "name": player.name,
        "avatar": player.avatar,
        "singles_rating": weighted_rating(player, today),
        "doubles_rating": weighted_doubles_rating(player, today),
    }


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
def list_pending_matches(club_id: str):
    """Return pending singles matches for a club."""
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    result = []
    for idx, m in enumerate(club.pending_matches):
        from .models import DoublesMatch

        if isinstance(m, DoublesMatch):
            continue
        result.append(
            {
                "index": idx,
                "date": m.date.isoformat(),
                "player_a": m.player_a.user_id,
                "player_b": m.player_b.user_id,
                "score_a": m.score_a,
                "score_b": m.score_b,
            }
        )
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
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
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
        confirm_match(clubs, club_id, index, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_matches/{index}/approve")
def approve_match_api(club_id: str, index: int, data: ApproveMatchRequest):
    from .cli import approve_match

    user = require_auth(data.token)
    if user != data.approver:
        raise HTTPException(401, "Token mismatch")

    try:
        approve_match(clubs, club_id, index, data.approver)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_doubles")
def submit_doubles_api(club_id: str, data: PendingDoublesCreate):
    from .cli import submit_doubles

    user = require_auth(data.token)
    if user != data.initiator:
        raise HTTPException(401, "Token mismatch")

    cid = data.club_id or club_id
    try:
        validate_scores(data.score_a, data.score_b)
        submit_doubles(
            clubs,
            cid,
            data.a1,
            data.a2,
            data.b1,
            data.b2,
            data.score_a,
            data.score_b,
            data.date or datetime.date.today(),
            data.weight or (
                format_weight_from_name(data.format)
                if data.format
                else format_weight_from_name("6_game")
            ),
            initiator=data.initiator,
            location=data.location,
            format_name=data.format,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "pending"}


@app.post("/clubs/{club_id}/pending_doubles/{index}/confirm")
def confirm_doubles_api(club_id: str, index: int, data: ConfirmRequest):
    from .cli import confirm_doubles

    user = require_auth(data.token)
    if user != data.user_id:
        raise HTTPException(401, "Token mismatch")

    try:
        confirm_doubles(clubs, club_id, index, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_doubles/{index}/approve")
def approve_doubles_api(club_id: str, index: int, data: ApproveMatchRequest):
    from .cli import approve_doubles

    user = require_auth(data.token)
    if user != data.approver:
        raise HTTPException(401, "Token mismatch")

    try:
        approve_doubles(clubs, club_id, index, data.approver)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


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
