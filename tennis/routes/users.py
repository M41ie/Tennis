from fastapi import APIRouter, Header
from pydantic import BaseModel
from ..services import users as user_service
from ..services.auth import require_auth, assert_token_matches
from ..services.helpers import get_user_or_404

from ..storage import get_user, get_player
from .. import api

router = APIRouter()


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


class TokenOnly(BaseModel):
    token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class WeChatLoginRequest(BaseModel):
    code: str


@router.post("/users")
def register_user_api(data: UserCreate):
    uid = user_service.create_user(data)
    return {"status": "ok", "user_id": uid}


@router.post("/login")
def login_api(data: LoginRequest):
    success, access, refresh, user_id = user_service.login(data.user_id, data.password)
    if success:
        return {
            "success": True,
            "access_token": access,
            "refresh_token": refresh,
            "token": access,
            "user_id": user_id,
        }
    return {"success": False}


@router.post("/wechat_login")
def wechat_login_api(data: WeChatLoginRequest):
    from .. import api  # local import to avoid circular dependency
    access, refresh, uid, created = user_service.wechat_login(
        data.code, api._exchange_wechat_code
    )
    # refresh caches for the logged in user
    user = get_user(uid)
    if user:
        api.users[user.user_id] = user
    player = get_player(uid)
    if player:
        api.players[player.user_id] = player
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token": access,
        "user_id": uid,
        "just_created": created,
    }


@router.post("/logout")
def logout_api(data: LogoutRequest):
    user_service.logout(data.token)
    return {"status": "ok"}


@router.post("/check_token")
def check_token_api(data: TokenOnly):
    uid = user_service.refresh_token(data.token)
    return {"status": "ok", "user_id": uid}


@router.post("/refresh_token")
def refresh_access_token_api(data: RefreshRequest):
    token, uid = user_service.refresh_access_token(data.refresh_token)
    return {"access_token": token, "token": token, "user_id": uid}


@router.get("/users/{user_id}")
def get_user_info(user_id: str):
    return user_service.user_info(user_id)


@router.get("/users/{user_id}/messages")
def get_user_messages(user_id: str, authorization: str | None = Header(None)):
    uid = require_auth(authorization)
    assert_token_matches(uid, user_id)
    user = get_user_or_404(user_id)
    return user_service.list_messages(user)


@router.get("/users/{user_id}/messages/unread_count")
def get_unread_count(user_id: str, authorization: str | None = Header(None)):
    uid = require_auth(authorization)
    assert_token_matches(uid, user_id)
    user = get_user_or_404(user_id)
    return {"unread": user_service.unread_count(user)}


@router.post("/users/{user_id}/messages/{index}/read")
def mark_message_read(user_id: str, index: int, authorization: str | None = Header(None)):
    uid = require_auth(authorization)
    assert_token_matches(uid, user_id)
    user = get_user_or_404(user_id)
    user_service.mark_read(user, index)
    return {"status": "ok"}
