from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from ..services.auth import require_auth, assert_token_matches
from ..services.clubs import create_club as svc_create_club, add_player as svc_add_player
from ..storage import load_data, load_users, get_club, get_player, get_user
from ..rating import (
    weighted_rating,
    weighted_doubles_rating,
    weighted_singles_matches,
    weighted_doubles_matches,
)
from .. import api
import datetime

router = APIRouter()


class ClubCreate(BaseModel):
    club_id: str | None = None
    name: str
    user_id: str
    logo: str | None = None
    region: str | None = None
    slogan: str | None = None


class PlayerCreate(BaseModel):
    user_id: str
    name: str
    age: int | None = None
    gender: str | None = None
    avatar: str | None = None
    birth: str | None = None
    handedness: str | None = None
    backhand: str | None = None
    region: str | None = None


@router.post("/clubs")
def create_club(data: ClubCreate, authorization: str | None = Header(None)):
    uid = require_auth(authorization)
    assert_token_matches(uid, data.user_id)
    cid = data.club_id or api._generate_club_id()
    svc_create_club(
        data.user_id,
        data.name,
        cid,
        logo=data.logo,
        region=data.region,
        slogan=data.slogan,
    )
    # refresh API state after DB write
    clubs, players = load_data()
    api.clubs.clear()
    api.clubs.update(clubs)
    api.players.clear()
    api.players.update(players)
    api.users.clear()
    api.users.update(load_users())
    return {"status": "ok", "club_id": cid}


@router.post("/clubs/{club_id}/players")
def add_player(club_id: str, data: PlayerCreate, authorization: str | None = Header(None)):
    require_auth(authorization)
    try:
        svc_add_player(
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
    except HTTPException as e:
        if e.status_code != 400 or str(e.detail) != "Player already in club":
            raise
    clubs, players = load_data()
    api.clubs.clear()
    api.clubs.update(clubs)
    api.players.clear()
    api.players.update(players)
    return {"status": "ok"}


@router.get("/clubs/{club_id}/pending_members")
def list_pending_members(club_id: str):
    """Return pending member applications with player details."""
    club = get_club(club_id)
    if not club:
        raise HTTPException(404, "Club not found")

    today = datetime.date.today()
    result = []
    for uid, info in club.pending_members.items():
        entry = {
            "user_id": uid,
            "id": uid,
            "reason": info.reason,
            "singles_rating": info.singles_rating,
            "doubles_rating": info.doubles_rating,
        }

        player = get_player(uid)
        if player:
            singles = weighted_rating(player, today)
            doubles = weighted_doubles_rating(player, today)
            entry.update(
                {
                    "name": player.name,
                    "avatar": player.avatar,
                    "avatar_url": player.avatar,
                    "gender": player.gender,
                    "weighted_games_singles": round(
                        weighted_singles_matches(player), 2
                    ),
                    "weighted_games_doubles": round(
                        weighted_doubles_matches(player), 2
                    ),
                    "singles_rating": singles
                    if singles is not None
                    else info.singles_rating,
                    "doubles_rating": doubles
                    if doubles is not None
                    else info.doubles_rating,
                }
            )
        else:
            user = get_user(uid)
            entry.update(
                {
                    "name": user.name if user else uid,
                    "avatar": getattr(user, "avatar", "") if user else "",
                    "avatar_url": getattr(user, "avatar", "") if user else "",
                    "gender": getattr(user, "gender", "") if user else "",
                    "weighted_games_singles": None,
                    "weighted_games_doubles": None,
                }
            )
        result.append(entry)

    return result
