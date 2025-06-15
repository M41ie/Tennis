from fastapi import APIRouter
from pydantic import BaseModel
from ..services.auth import require_auth, assert_token_matches
from ..cli import create_club as cli_create_club, add_player as cli_add_player
from ..storage import save_data, save_users
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
    cli_create_club(
        api.users,
        api.clubs,
        data.user_id,
        cid,
        data.name,
        data.logo,
        data.region,
        data.slogan,
    )
    save_data(api.clubs)
    save_users(api.users)
    return {"status": "ok", "club_id": cid}


@router.post("/clubs/{club_id}/players")
def add_player(club_id: str, data: PlayerCreate):
    require_auth(data.token)
    try:
        cli_add_player(
            api.clubs,
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
        if str(e) != "Player already in club":
            raise
    save_data(api.clubs)
    return {"status": "ok"}
