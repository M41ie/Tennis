from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services.auth import require_auth, assert_token_matches
from ..services.clubs import create_club as svc_create_club, add_player as svc_add_player
from ..storage import load_data, load_users
from .. import api

router = APIRouter()


class ClubCreate(BaseModel):
    club_id: str | None = None
    name: str
    user_id: str
    token: str
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


@router.post("/clubs")
def create_club(data: ClubCreate):
    uid = require_auth(data.token)
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
    api.clubs = load_data()
    api.users = load_users()
    return {"status": "ok", "club_id": cid}


@router.post("/clubs/{club_id}/players")
def add_player(club_id: str, data: PlayerCreate):
    require_auth(data.token)
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
    api.clubs = load_data()
    return {"status": "ok"}
