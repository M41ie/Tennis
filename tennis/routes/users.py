from fastapi import APIRouter
from pydantic import BaseModel
from ..services import users as user_service
from ..services.auth import require_auth, assert_token_matches
from ..services.helpers import get_user_or_404

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


class WeChatLoginRequest(BaseModel):
    code: str


@router.post("/users")
def register_user_api(data: UserCreate):
    uid = user_service.create_user(data)
    return {"status": "ok", "user_id": uid}


@router.post("/login")
def login_api(data: LoginRequest):
    success, token, user_id = user_service.login(data.user_id, data.password)
    if success:
        return {"success": True, "token": token, "user_id": user_id}
    return {"success": False}


@router.post("/wechat_login")
def wechat_login_api(data: WeChatLoginRequest):
    from .. import api  # local import to avoid circular dependency
    token, uid, created = user_service.wechat_login(
        data.code, api._exchange_wechat_code
    )
    return {"token": token, "user_id": uid, "just_created": created}


@router.post("/logout")
def logout_api(data: LogoutRequest):
    user_service.logout(data.token)
    return {"status": "ok"}


@router.post("/check_token")
def check_token_api(data: TokenOnly):
    uid = user_service.refresh_token(data.token)
    return {"status": "ok", "user_id": uid}


@router.get("/users/{user_id}")
def get_user_info(user_id: str):
    return user_service.user_info(user_id)


@router.get("/users/{user_id}/messages")
def get_user_messages(user_id: str, token: str):
    uid = require_auth(token)
    assert_token_matches(uid, user_id)
    user = get_user_or_404(user_id)
    return user_service.list_messages(user)


@router.get("/users/{user_id}/messages/unread_count")
def get_unread_count(user_id: str, token: str):
    uid = require_auth(token)
    assert_token_matches(uid, user_id)
    user = get_user_or_404(user_id)
    return {"unread": user_service.unread_count(user)}


@router.post("/users/{user_id}/messages/{index}/read")
def mark_message_read(user_id: str, index: int, data: TokenOnly):
    uid = require_auth(data.token)
    assert_token_matches(uid, user_id)
    user = get_user_or_404(user_id)
    user_service.mark_read(user, index)
    return {"status": "ok"}
