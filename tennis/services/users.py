from __future__ import annotations
import secrets
import datetime
from .exceptions import ServiceError
from .. import cli
from ..cli import register_user, resolve_user, check_password, hash_password, set_user_limits
from ..storage import (
    load_users,
    load_data,
    get_player,
    get_club,
    list_clubs,
    insert_token,
    delete_token,
    get_token,
    insert_refresh_token,
    get_refresh_token,
    delete_refresh_token,
    create_user as create_user_record,
    create_player,
    set_player,
    get_user as get_user_record,
    list_user_messages,
    mark_user_message_read,
    transaction,
    save_user,
    update_player_record,
)
from .. import storage
from . import state
from ..models import User, Player


def create_user(data) -> str:
    users = load_users()
    _, players = load_data()
    import tennis.cli as cli_module
    cli_module.players = players
    if data.user_id:
        existing = get_player(data.user_id)
        if existing:
            set_player(existing)
    if data.user_id and data.user_id in users:
        raise ServiceError("User exists", 400)
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
    if uid not in players:
        new_player = Player(
            user_id=uid,
            name=data.name,
            avatar=data.avatar,
            gender=data.gender,
            birth=data.birth,
            handedness=data.handedness,
            backhand=data.backhand,
            region=data.region,
        )
        set_player(new_player)
    # persist new records individually
    with transaction() as conn:
        create_user_record(users[uid], conn=conn)
        create_player(
            "",
            get_player(uid),
            joined=get_player(uid).joined,
            conn=conn,
        )
    storage.bump_cache_version()
    return uid


def login(user_id: str, password: str):
    user = get_user_record(user_id)
    if not user:
        users = load_users()
        user = resolve_user(users, user_id)
    if not user:
        return False, None, None

    hashed = user.password_hash
    is_old = len(hashed) == 64 and all(c in "0123456789abcdef" for c in hashed)

    if is_old:
        import hashlib

        if hashlib.sha256(password.encode("utf-8")).hexdigest() != hashed:
            return False, None, None
        # upgrade hash
        user.password_hash = hash_password(password)
        with transaction() as conn:
            save_user(user, conn=conn)
        storage.bump_cache_version()
    else:
        if not check_password(user, password):
            return False, None, None

    access_token = secrets.token_hex(16)
    refresh_token = secrets.token_hex(16)
    insert_token(access_token, user.user_id)
    insert_refresh_token(user.user_id, refresh_token, datetime.datetime.utcnow() + state.REFRESH_TOKEN_TTL)
    return True, access_token, refresh_token, user.user_id


DEFAULT_NICK_LEN = 5
OPENID_NICK_OFFSET = 6


def _unique_nickname(openid: str, users: dict, players: dict) -> str:
    """Return a unique nickname generated from ``openid``.

    The nickname generation begins from the seventh character of ``openid`` to
    avoid common leading segments.  Progressively longer slices of this suffix
    are tested until a unique value is found.  If the suffix alone does not
    yield a unique nickname, the full ``openid`` is returned as a fallback.
    """

    suffix = openid[OPENID_NICK_OFFSET:]

    if not suffix:
        return openid

    def in_use(name: str) -> bool:
        return any(u.name == name for u in users.values()) or any(
            p.name == name for p in players.values()
        )

    length = min(DEFAULT_NICK_LEN, len(suffix))
    max_len = len(suffix)

    while length <= max_len:
        nick = suffix[:length]
        if not in_use(nick):
            return nick
        length += 1

    if not in_use(suffix):
        return suffix

    return openid


def wechat_login(code: str, exchange_func) -> tuple[str, str, str, bool]:
    """Login or register using a WeChat mini program code.

    Returns a tuple ``(token, user_id, just_created)`` where ``just_created``
    is ``True`` if this call resulted in creating a brand new user.
    """
    info = exchange_func(code)
    openid = info.get("openid")
    if not openid:
        raise ServiceError("Invalid code", 400)

    users = load_users()
    _, players = load_data()
    import tennis.cli as cli_module
    cli_module.players = players
    user = None
    created = False
    for u in users.values():
        if u.wechat_openid == openid:
            user = u
            break

    if not user:
        # allocate a sequential user ID using the normal registration flow
        provided_nick = info.get("nickname")
        if provided_nick:
            nickname = provided_nick
        else:
            nickname = _unique_nickname(openid, users, players)
        uid = register_user(users, None, nickname, "")
        user = users[uid]
        user.password_hash = ""
        user.wechat_openid = openid
        users[uid] = user
        new_player = Player(user_id=uid, name=nickname)
        set_player(new_player)
        with transaction() as conn:
            create_user_record(user, conn=conn)
            create_player(
                "",
                new_player,
                joined=new_player.joined,
                conn=conn,
            )
        storage.bump_cache_version()
        created = True

    access_token = secrets.token_hex(16)
    refresh_token = secrets.token_hex(16)
    insert_token(access_token, user.user_id)
    insert_refresh_token(user.user_id, refresh_token, datetime.datetime.utcnow() + state.REFRESH_TOKEN_TTL)
    return access_token, refresh_token, user.user_id, created


def logout(token: str):
    info = get_token(token)
    if info:
        uid, _ = info
        delete_refresh_token(uid)
    delete_token(token)


def refresh_token(token: str):
    info = get_token(token)
    if not info:
        raise ServiceError("Invalid token", 401)
    uid, _ = info
    insert_token(token, uid)
    return uid


def refresh_access_token(refresh_token: str) -> tuple[str, str]:
    info = get_refresh_token(refresh_token)
    if not info:
        raise ServiceError("Invalid token", 401)
    uid, expires = info
    if datetime.datetime.utcnow() > expires:
        delete_refresh_token(uid)
        raise ServiceError("Token expired", 401)
    access_token = secrets.token_hex(16)
    insert_token(access_token, uid)
    return access_token, uid


def user_info(user_id: str):
    user = get_user_record(user_id)
    if not user:
        raise ServiceError("User not found", 404)
    joined = [c.club_id for c in list_clubs() if user_id in c.members]
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
    except IndexError:
        raise ServiceError("Message not found", 404)


def update_user_limits(user_id: str, max_joinable: int, max_creatable: int) -> None:
    """Update club limits for a user."""
    users = load_users()
    try:
        set_user_limits(users, user_id, max_joinable=max_joinable, max_creatable=max_creatable)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    with transaction() as conn:
        save_user(users[user_id], conn=conn)
    storage.bump_cache_version()


def update_player_rating(user_id: str, singles: float | None, doubles: float | None) -> None:
    """Directly set a player's rating values."""
    player = storage.get_player(user_id)
    if not player:
        raise ServiceError("Player not found", 404)
    if singles is not None:
        player.singles_rating = singles
    if doubles is not None:
        player.doubles_rating = doubles
    with transaction() as conn:
        update_player_record(player, conn=conn)
    storage.bump_cache_version()

