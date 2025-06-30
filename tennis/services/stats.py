import datetime
import statistics
from ..rating import (
    weighted_rating,
    weighted_doubles_rating,
)
from ..models import Club, Player, Match, DoublesMatch
from ..storage import load_data


def _pending_status_for_user(user_id: str, match: Match | DoublesMatch, club: Club) -> dict[str, object]:
    """Return status information for the given user viewing a pending match."""

    admins = {club.leader_id, *club.admin_ids}
    is_admin = user_id in admins

    if user_id == match.initiator:
        role = "submitter"
    else:
        if isinstance(match, DoublesMatch):
            team_a = {match.player_a1.user_id, match.player_a2.user_id}
            team_b = {match.player_b1.user_id, match.player_b2.user_id}

            if user_id in team_a:
                role = "teammate"
            elif user_id in team_b:
                role = "opponent"
            elif user_id in admins:
                role = "admin"
            else:
                role = "viewer"
        else:
            participants = {match.player_a.user_id, match.player_b.user_id}

            if user_id in participants:
                role = "opponent"
            elif user_id in admins:
                role = "admin"
            else:
                role = "viewer"

    confirmed_self = None
    confirmed_opp = None
    if isinstance(match, DoublesMatch):
        if user_id in {match.player_a1.user_id, match.player_a2.user_id}:
            confirmed_self = match.confirmed_a
            confirmed_opp = match.confirmed_b
        elif user_id in {match.player_b1.user_id, match.player_b2.user_id}:
            confirmed_self = match.confirmed_b
            confirmed_opp = match.confirmed_a
    else:
        if user_id == match.player_a.user_id:
            confirmed_self = match.confirmed_a
            confirmed_opp = match.confirmed_b
        elif user_id == match.player_b.user_id:
            confirmed_self = match.confirmed_b
            confirmed_opp = match.confirmed_a

    can_confirm = False
    can_decline = False
    status_text = ""

    if role == "submitter":
        if not (match.confirmed_a and match.confirmed_b):
            status_text = "您已提交，等待对手确认"
        else:
            status_text = "对手已确认，等待管理员审核"
    elif role == "teammate":
        if not match.confirmed_b:
            status_text = "您的队友已确认，等待对手确认"
        else:
            status_text = "对手和队友已确认，等待管理员审核"
    elif role == "opponent":
        if confirmed_self is False:
            can_confirm = True
            can_decline = True
            status_text = "对手提交了比赛战绩，请确认"
        else:
            status_text = "您已确认，等待管理员审核"
    elif role == "admin":
        status_text = "双方已确认，请审核"
    else:
        if match.confirmed_a and match.confirmed_b:
            status_text = "等待管理员审核"
        else:
            status_text = "待确认"

    if is_admin and match.confirmed_a and match.confirmed_b:
        role = "admin"
        status_text = "双方已确认，请审核"
        can_confirm = False
        can_decline = False

    return {
        "display_status_text": status_text,
        "can_confirm": can_confirm,
        "can_decline": can_decline,
        "current_user_role_in_match": role,
    }


def _club_stats(club: Club) -> dict[str, object]:
    """Aggregate statistics for a club."""
    singles = [p.singles_rating for p in club.members.values() if p.singles_rating is not None]
    doubles = [p.doubles_rating for p in club.members.values() if p.doubles_rating is not None]
    total_singles = sum(len(p.singles_matches) for p in club.members.values()) / 2
    total_doubles = sum(len(p.doubles_matches) for p in club.members.values()) / 4
    singles_avg = statistics.mean(singles) if singles else 0
    doubles_avg = statistics.mean(doubles) if doubles else 0
    return {
        "member_count": len(club.members),
        "singles_rating_range": [min(singles) if singles else 0, max(singles) if singles else 0],
        "doubles_rating_range": [min(doubles) if doubles else 0, max(doubles) if doubles else 0],
        "singles_avg_rating": singles_avg,
        "doubles_avg_rating": doubles_avg,
        "total_singles_matches": total_singles,
        "total_doubles_matches": total_doubles,
    }


def get_leaderboard(
    clubs: dict[str, Club],
    club_id: str | None,
    doubles: bool,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    gender: str | None = None,
) -> list[tuple[Player, float]]:
    """Collect leaderboard data with optional filters."""

    today = datetime.date.today()
    if club_id is not None:
        club = clubs.get(club_id)
        if not club:
            raise ValueError("Club not found")
        clubs_to_iter = [club]
    else:
        clubs_to_iter = list(clubs.values())
        # fetch all players so we can include those without club membership
        _, all_players = load_data()
        extra_players = [
            p
            for p in all_players.values()
            if all(p.user_id not in c.members for c in clubs_to_iter)
        ]

    players: list[tuple[Player, float]] = []
    for club in clubs_to_iter:
        for p in club.members.values():
            rating = weighted_doubles_rating(p, today) if doubles else weighted_rating(p, today)
            if rating is None:
                continue
            if min_rating is not None and rating < min_rating:
                continue
            if max_rating is not None and rating > max_rating:
                continue
            if min_age is not None and (p.age is None or p.age < min_age):
                continue
            if max_age is not None and (p.age is None or p.age > max_age):
                continue
            if gender is not None and p.gender != gender:
                continue
            players.append((p, rating))

    if club_id is None:
        for p in extra_players:
            rating = weighted_doubles_rating(p, today) if doubles else weighted_rating(p, today)
            if rating is None:
                continue
            if min_rating is not None and rating < min_rating:
                continue
            if max_rating is not None and rating > max_rating:
                continue
            if min_age is not None and (p.age is None or p.age < min_age):
                continue
            if max_age is not None and (p.age is None or p.age > max_age):
                continue
            if gender is not None and p.gender != gender:
                continue
            players.append((p, rating))

    players.sort(key=lambda x: x[1], reverse=True)
    return players
