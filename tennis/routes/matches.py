from fastapi import APIRouter, Header
from ..services.matches import (
    list_global_pending_doubles_service,
    list_global_pending_matches_service,
    list_pending_doubles_service,
    list_pending_matches_service,
)

router = APIRouter()


@router.get("/players/{user_id}/pending_doubles")
def list_global_pending_doubles(user_id: str, token: str, authorization: str | None = Header(None)):
    return list_global_pending_doubles_service(user_id, token, authorization)


@router.get("/players/{user_id}/pending_matches")
def list_global_pending_matches(user_id: str, token: str, authorization: str | None = Header(None)):
    return list_global_pending_matches_service(user_id, token, authorization)


@router.get("/clubs/{club_id}/pending_doubles")
def list_pending_doubles(club_id: str, token: str, authorization: str | None = Header(None)):
    return list_pending_doubles_service(club_id, token, authorization)


@router.get("/clubs/{club_id}/pending_matches")
def list_pending_matches(club_id: str, token: str, authorization: str | None = Header(None)):
    return list_pending_matches_service(club_id, token, authorization)
