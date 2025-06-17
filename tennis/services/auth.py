from __future__ import annotations
import datetime
from fastapi import HTTPException, Request
from . import state
from .. import storage


def require_auth(token: str, authorization: str | None = None, request: Request | None = None) -> str:
    """Validate token and return associated user id.

    The function first attempts to read a ``Bearer`` token from the
    ``Authorization`` header. If not provided, it falls back to the passed
    ``token`` argument for backwards compatibility.
    """
    header = authorization
    if request is not None and not header:
        header = request.headers.get("Authorization")

    if header and header.startswith("Bearer "):
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
