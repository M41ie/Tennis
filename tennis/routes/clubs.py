from fastapi import APIRouter
from pydantic import BaseModel
from ..services import clubs as clubs_service
from ..services.auth import require_auth

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
    require_auth(data.token)
    cid = data.club_id or clubs_service.generate_club_id()
    clubs_service.create_club(
        data.user_id,
        data.name,
        club_id=cid,
        logo=data.logo,
        region=data.region,
        slogan=data.slogan,
    )
    return {"status": "ok", "club_id": cid}


@router.post("/clubs/{club_id}/players")
def add_player(club_id: str, data: PlayerCreate):
    require_auth(data.token)
    clubs_service.add_player(
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
    return {"status": "ok"}
