import datetime

from tennis.cli import get_leaderboard
from tennis.models import Club, Player


def test_get_leaderboard_filters():
    club = Club(club_id="c1", name="Club")
    p1 = Player("p1", "P1", singles_rating=1200.0, age=25, gender="M")
    p2 = Player("p2", "P2", singles_rating=900.0, age=30, gender="F")
    p3 = Player("p3", "P3", singles_rating=1100.0, age=20, gender="M")

    club.members[p1.user_id] = p1
    club.members[p2.user_id] = p2
    club.members[p3.user_id] = p3

    clubs = {club.club_id: club}

    result = get_leaderboard(clubs, "c1", False, min_rating=1000, gender="M")
    ids = [p.user_id for p, _ in result]
    assert ids == ["p1", "p3"]


def test_get_leaderboard_doubles():
    club = Club(club_id="c1", name="Club")
    p1 = Player("p1", "P1", singles_rating=800.0, doubles_rating=1200.0)
    p2 = Player("p2", "P2", singles_rating=1500.0, doubles_rating=1100.0)
    p3 = Player("p3", "P3", singles_rating=1000.0, doubles_rating=1300.0)

    club.members[p1.user_id] = p1
    club.members[p2.user_id] = p2
    club.members[p3.user_id] = p3

    clubs = {club.club_id: club}

    result = get_leaderboard(clubs, "c1", True)
    ids = [p.user_id for p, _ in result]
    assert ids == ["p3", "p1", "p2"]

