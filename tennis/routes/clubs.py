from fastapi import APIRouter, HTTPException, Header
from ..services.exceptions import ServiceError
from pydantic import BaseModel
from ..services.auth import require_auth, assert_token_matches
from ..services.clubs import (
    create_club as svc_create_club,
    add_player as svc_add_player,
    get_clubs_batch as svc_get_clubs_batch,
)
from ..storage import get_club, get_player, get_user, list_clubs
from ..rating import (
    weighted_rating,
    weighted_doubles_rating,
    weighted_singles_matches,
    weighted_doubles_matches,
)
from ..services.stats import _club_stats
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
    # refresh caches for the newly created objects
    club = get_club(cid)
    if club:
        api.clubs[cid] = club
    player = get_player(data.user_id)
    if player:
        api.players[player.user_id] = player
    user = get_user(data.user_id)
    if user:
        api.users[user.user_id] = user
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
    except ServiceError as e:
        if e.status_code != 400 or str(e.detail) != "Player already in club":
            raise
    # refresh caches for the updated club and new player
    club = get_club(club_id)
    if club:
        api.clubs[club_id] = club
    player = get_player(data.user_id)
    if player:
        api.players[player.user_id] = player
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


@router.get("/clubs/batch")
def get_clubs_batch(club_ids: str):
    """Return basic club information for multiple clubs."""
    ids = [c for c in club_ids.split(",") if c]
    clubs = svc_get_clubs_batch(ids)
    today = datetime.date.today()
    result = []
    for club in clubs:
        pending = []
        for uid, info in club.pending_members.items():
            entry = {
                "user_id": uid,
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
                        "weighted_games_singles": round(weighted_singles_matches(player), 2),
                        "weighted_games_doubles": round(
                            weighted_doubles_matches(player), 2
                        ),
                        "singles_rating": singles if singles is not None else info.singles_rating,
                        "doubles_rating": doubles if doubles is not None else info.doubles_rating,
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
            pending.append(entry)

        members = [
            {
                "user_id": p.user_id,
                "name": p.name,
                "avatar": p.avatar,
                "gender": p.gender,
            }
            for p in club.members.values()
        ]

        result.append(
            {
                "club_id": club.club_id,
                "name": club.name,
                "logo": club.logo,
                "region": club.region,
                "slogan": club.slogan,
                "leader_id": club.leader_id,
                "admin_ids": list(club.admin_ids),
                "pending_members": pending,
                "members": members,
                "rejected_members": club.rejected_members,
                "stats": _club_stats(club),
            }
        )

    return result


@router.get("/clubs/search")
def search_clubs(query: str | None = None, limit: int | None = None, offset: int = 0):
    """Return detailed club information filtered by an optional query."""
    q = query.lower() if query else None
    clubs = list_clubs()
    today = datetime.date.today()
    result = []
    for club in clubs:
        if q and q not in club.club_id.lower() and q not in club.name.lower():
            continue
        entry = {
            "club_id": club.club_id,
            "name": club.name,
            "logo": club.logo,
            "region": club.region,
            "slogan": club.slogan,
            "pending_members": len(club.pending_members),
            "pending_matches": len(club.pending_matches),
            "total_matches": len(club.matches),
            "stats": _club_stats(club),
        }
        result.append(entry)

    result.sort(key=lambda x: x["club_id"])
    if offset:
        result = result[offset:]
    if limit is not None:
        result = result[:limit]
    return result
