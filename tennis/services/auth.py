from __future__ import annotations
import datetime
from fastapi import HTTPException
from . import state
from .. import storage


def require_auth(token: str) -> str:
    """Validate token and return associated user id."""
    info = storage.get_token(token)
    if not info:
        raise HTTPException(401, "Invalid token")
    user_id, ts = info
    if datetime.datetime.utcnow() - ts > state.TOKEN_TTL:
        storage.delete_token(token)
        raise HTTPException(401, "Token expired")
    return user_id


def assert_token_matches(token_user: str, target_user: str) -> None:
    if token_user != target_user:
        raise HTTPException(401, "Token mismatch")
