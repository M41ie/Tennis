import datetime
import pytest

from tennis.cli import record_match, record_doubles, submit_match
from tennis.models import Club, Player


def _setup_singles():
    club = Club(club_id="c", name="Club")
    p1 = Player("p1", "P1", singles_rating=1000.0)
    p2 = Player("p2", "P2", singles_rating=1000.0)
    club.members[p1.user_id] = p1
    club.members[p2.user_id] = p2
    clubs = {club.club_id: club}
    return clubs


def _setup_doubles():
    club = Club(club_id="c", name="Club")
    a1 = Player("a1", "A1", doubles_rating=1000.0)
    a2 = Player("a2", "A2", doubles_rating=1000.0)
    b1 = Player("b1", "B1", doubles_rating=1000.0)
    b2 = Player("b2", "B2", doubles_rating=1000.0)
    for p in (a1, a2, b1, b2):
        club.members[p.user_id] = p
    clubs = {club.club_id: club}
    return clubs


@pytest.mark.parametrize("score_a,score_b", [(-1, 0), (1, -2), (1.5, 2), (3, 2.2)])
def test_record_match_invalid(score_a, score_b):
    clubs = _setup_singles()
    with pytest.raises(ValueError):
        record_match(clubs, "c", "p1", "p2", score_a, score_b, datetime.date.today(), 1.0)


@pytest.mark.parametrize("score_a,score_b", [(-1, 0), (0, -1), (2.5, 1), (1, 2.7)])
def test_record_doubles_invalid(score_a, score_b):
    clubs = _setup_doubles()
    with pytest.raises(ValueError):
        record_doubles(
            clubs,
            "c",
            "a1",
            "a2",
            "b1",
            "b2",
            score_a,
            score_b,
            datetime.date.today(),
            1.0,
        )


@pytest.mark.parametrize("score_a,score_b", [(-1, 0), (0, -3), (2, 1.2), (3.1, 2)])
def test_submit_match_invalid(score_a, score_b):
    clubs = _setup_singles()
    with pytest.raises(ValueError):
        submit_match(
            clubs,
            "c",
            "p1",
            "p2",
            score_a,
            score_b,
            datetime.date.today(),
            1.0,
        )
