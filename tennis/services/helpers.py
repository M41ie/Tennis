from fastapi import HTTPException
from ..storage import load_users, load_data
from ..models import User, Club


def get_user_or_404(user_id: str) -> User:
    user = load_users().get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


def get_club_or_404(club_id: str) -> Club:
    club = load_data().get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    return club
