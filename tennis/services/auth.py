from __future__ import annotations
import datetime
from fastapi import HTTPException, Request
from . import state
from .. import storage


def require_auth(authorization: str | None = None, request: Request | None = None) -> str:
    """Validate token from the ``Authorization`` header and return the user id."""

    header = authorization
    if request is not None and not header:
        header = request.headers.get("Authorization")

    if not header or not header.startswith("Bearer "):
        raise HTTPException(401, "Invalid token")

    token = header[7:]

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
