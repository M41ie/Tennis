from __future__ import annotations
import secrets
import datetime
from fastapi import HTTPException
from .state import clubs, users, tokens, _save_tokens
from ..cli import register_user, resolve_user, check_password
from ..storage import save_users, save_data
from ..models import Player, players, User


def create_user(data) -> str:
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
    return uid


def login(user_id: str, password: str):
    user = resolve_user(users, user_id)
    if user and check_password(user, password):
        token = secrets.token_hex(16)
        tokens[token] = (user.user_id, datetime.datetime.utcnow())
        _save_tokens()
        return True, token, user.user_id
    return False, None, None


def logout(token: str):
    tokens.pop(token, None)
    _save_tokens()


def refresh_token(token: str):
    info = tokens.get(token)
    if not info:
        raise HTTPException(401, "Invalid token")
    uid, _ = info
    tokens[token] = (uid, datetime.datetime.utcnow())
    _save_tokens()
    return uid


def user_info(user_id: str):
    user = users.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    joined = [cid for cid, c in clubs.items() if user_id in c.members]
    created = getattr(user, "created_clubs", 0)
    max_created = getattr(user, "max_creatable_clubs", 0)
    return {
        "user_id": user.user_id,
        "name": user.name,
        "joined_clubs": joined,
        "can_create_club": created < max_created if max_created else user.can_create_club,
        "max_joinable_clubs": getattr(user, "max_joinable_clubs", 5),
        "max_creatable_clubs": max_created,
        "created_clubs": created,
        "sys_admin": getattr(user, "is_sys_admin", False),
    }


def list_messages(user: User):
    return [{"date": m.date.isoformat(), "text": m.text, "read": m.read} for m in user.messages]


def unread_count(user: User) -> int:
    return sum(1 for m in user.messages if not m.read)


def mark_read(user: User, index: int):
    if index >= len(user.messages):
        raise HTTPException(404, "Message not found")
    user.messages[index].read = True
    save_users(users)
