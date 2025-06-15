from __future__ import annotations
import secrets
from fastapi import HTTPException
from ..cli import register_user, resolve_user, check_password
from ..storage import (
    load_users,
    load_data,
    insert_token,
    delete_token,
    get_token,
    create_user as create_user_record,
    create_player,
    get_user as get_user_record,
    list_user_messages,
    mark_user_message_read,
)
from ..models import players, User


def create_user(data) -> str:
    users = load_users()
    clubs = load_data()
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
    # persist new records individually
    create_user_record(users[uid])
    create_player("", players[uid])
    try:
        import tennis.api as api
        api.users.clear()
        api.users.update(load_users())
    except Exception:
        pass
    return uid


def login(user_id: str, password: str):
    user = get_user_record(user_id)
    if not user:
        users = load_users()
        user = resolve_user(users, user_id)
    if user and check_password(user, password):
        token = secrets.token_hex(16)
        insert_token(token, user.user_id)
        return True, token, user.user_id
    return False, None, None


def wechat_login(code: str, exchange_func) -> tuple[str, str, bool]:
    """Login or register using a WeChat mini program code.

    Returns a tuple ``(token, user_id, just_created)`` where ``just_created``
    is ``True`` if this call resulted in creating a brand new user.
    """
    info = exchange_func(code)
    openid = info.get("openid")
    if not openid:
        raise HTTPException(400, "Invalid code")

    users = load_users()
    user = None
    created = False
    for u in users.values():
        if u.wechat_openid == openid:
            user = u
            break

    if not user:
        # allocate a sequential user ID using the normal registration flow
        nickname = info.get("nickname") or openid
        uid = register_user(users, None, nickname, "")
        user = users[uid]
        user.password_hash = ""
        user.wechat_openid = openid
        users[uid] = user
        create_user_record(user)
        create_player("", players[uid])
        try:
            import tennis.api as api
            api.users = load_users()
        except Exception:
            pass
        created = True

    token = secrets.token_hex(16)
    insert_token(token, user.user_id)
    return token, user.user_id, created


def logout(token: str):
    delete_token(token)


def refresh_token(token: str):
    info = get_token(token)
    if not info:
        raise HTTPException(401, "Invalid token")
    uid, _ = info
    insert_token(token, uid)
    return uid


def user_info(user_id: str):
    user = get_user_record(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    clubs = load_data()
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
    msgs = list_user_messages(user.user_id)
    return [{"date": m.date.isoformat(), "text": m.text, "read": m.read} for _, m in msgs]


def unread_count(user: User) -> int:
    msgs = list_user_messages(user.user_id)
    return sum(1 for _, m in msgs if not m.read)


def mark_read(user: User, index: int):
    try:
        mark_user_message_read(user.user_id, index)
        import tennis.api as api
        api.users.clear()
        api.users.update(load_users())
    except IndexError:
        raise HTTPException(404, "Message not found")
