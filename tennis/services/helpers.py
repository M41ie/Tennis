from .exceptions import ServiceError
from ..storage import get_user, get_club
from ..models import User, Club


def get_user_or_404(user_id: str) -> User:
    user = get_user(user_id)
    if not user:
        raise ServiceError("User not found", 404)
    return user


def get_club_or_404(club_id: str) -> Club:
    club = get_club(club_id)
    if not club:
        raise ServiceError("Club not found", 404)
    return club
