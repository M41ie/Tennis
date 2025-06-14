from __future__ import annotations
import datetime
from fastapi import HTTPException
from . import state


def require_auth(token: str) -> str:
    """Validate token and return associated user id."""
    info = state.tokens.get(token)
    if not info:
        raise HTTPException(401, "Invalid token")
    user_id, ts = info
    if datetime.datetime.utcnow() - ts > state.TOKEN_TTL:
        state.tokens.pop(token, None)
        state._save_tokens()
        raise HTTPException(401, "Token expired")
    return user_id


def assert_token_matches(token_user: str, target_user: str) -> None:
    if token_user != target_user:
        raise HTTPException(401, "Token mismatch")
