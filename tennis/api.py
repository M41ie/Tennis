from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime

from .storage import load_data, save_data, load_users, save_users
from .cli import (
    register_user,
    login_user,
    request_join,
    approve_member,
    hash_password,
)
from .rating import (
    update_ratings,
    update_doubles_ratings,
    weighted_rating,
    weighted_doubles_rating,
    format_weight_from_name,
)
from .models import Player, Club, Match

app = FastAPI()

clubs = load_data()
users = load_users()


class ClubCreate(BaseModel):
    club_id: str
    name: str
    logo: str | None = None
    region: str | None = None


class PlayerCreate(BaseModel):
    user_id: str
    name: str
    age: int | None = None
    gender: str | None = None
    avatar: str | None = None


class MatchCreate(BaseModel):
    user_a: str
    user_b: str
    score_a: int
    score_b: int
    date: datetime.date | None = None
    format: str | None = None
    weight: float | None = None
    location: str | None = None


class PendingMatchCreate(BaseModel):
    club_id: str | None = None  # optional alternate clubs
    initiator: str
    opponent: str
    score_initiator: int
    score_opponent: int
    date: datetime.date | None = None
    format: str | None = None
    weight: float | None = None
    location: str | None = None


class UserCreate(BaseModel):
    user_id: str
    name: str
    password: str
    allow_create: bool = False


class LoginRequest(BaseModel):
    user_id: str
    password: str


class JoinRequest(BaseModel):
    user_id: str


class ApproveRequest(BaseModel):
    approver_id: str
    user_id: str
    admin: bool = False


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
        return {"success": True}
    return {"success": False}


@app.post("/clubs/{club_id}/join")
def join_club(club_id: str, data: JoinRequest):
    try:
        request_join(clubs, users, club_id, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/approve")
def approve_club_member(club_id: str, data: ApproveRequest):
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
    return {"status": "ok"}


@app.get("/clubs")
def list_clubs():
    return [{"club_id": c.club_id, "name": c.name} for c in clubs.values()]


@app.post("/clubs")
def create_club(data: ClubCreate):
    if data.club_id in clubs:
        raise HTTPException(400, "Club exists")
    clubs[data.club_id] = Club(
        club_id=data.club_id,
        name=data.name,
        logo=data.logo,
        region=data.region,
    )
    save_data(clubs)
    return {"status": "ok"}


@app.get("/clubs/{club_id}/players")
def list_players(club_id: str):
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    today = datetime.date.today()
    return [
        {
            "user_id": p.user_id,
            "name": p.name,
            "rating": weighted_rating(p, today),
        }
        for p in club.members.values()
    ]


@app.get("/players")
def list_all_players(
    min_rating: float | None = None,
    max_rating: float | None = None,
    gender: str | None = None,
    club: str | None = None,
):
    if club:
        c = clubs.get(club)
        if not c:
            raise HTTPException(404, "Club not found")
        clubs_to_iter = [c]
    else:
        clubs_to_iter = clubs.values()
    today = datetime.date.today()
    players = []
    for c in clubs_to_iter:
        for p in c.members.values():
            rating = weighted_rating(p, today)
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


@app.post("/clubs/{club_id}/matches")
def record_match_api(club_id: str, data: MatchCreate):
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


@app.post("/clubs/{club_id}/pending_matches")
def submit_match_api(club_id: str, data: PendingMatchCreate):
    from .cli import submit_match

    cid = data.club_id or club_id
    try:
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


class ApproveMatchRequest(BaseModel):
    approver: str


@app.post("/clubs/{club_id}/pending_matches/{index}/confirm")
def confirm_match_api(club_id: str, index: int, data: ConfirmRequest):
    from .cli import confirm_match

    try:
        confirm_match(clubs, club_id, index, data.user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


@app.post("/clubs/{club_id}/pending_matches/{index}/approve")
def approve_match_api(club_id: str, index: int, data: ApproveMatchRequest):
    from .cli import approve_match

    try:
        approve_match(clubs, club_id, index, data.approver)
    except ValueError as e:
        raise HTTPException(400, str(e))
    save_data(clubs)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
