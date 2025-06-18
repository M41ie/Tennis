from __future__ import annotations
import datetime
from fastapi import Request
from .exceptions import ServiceError
from . import state
from .. import storage


def require_auth(authorization: str | None = None, request: Request | None = None) -> str:
    """Validate token from the ``Authorization`` header and return the user id."""

    header = authorization
    if request is not None and not header:
        header = request.headers.get("Authorization")

    if not header or not header.startswith("Bearer "):
        raise ServiceError("Invalid token", 401)

    token = header[7:]

    info = storage.get_token(token)
    if not info:
        raise ServiceError("Invalid token", 401)
    user_id, ts = info
    if datetime.datetime.utcnow() - ts > state.TOKEN_TTL:
        storage.delete_token(token)
        raise ServiceError("Token expired", 401)
    return user_id


def assert_token_matches(token_user: str, target_user: str) -> None:
    if token_user != target_user:
        raise ServiceError("Token mismatch", 401)
