import datetime
import pytest

from tennis.models import Player, Club, Match
from tennis.rating import update_ratings
from tennis.cli import get_player_match_cards


def test_get_player_match_cards_basic():
    club = Club(club_id="c", name="Club")
    p1 = Player("p1", "P1")
    p2 = Player("p2", "P2")
    club.members[p1.user_id] = p1
    club.members[p2.user_id] = p2
    clubs = {club.club_id: club}

    m1 = Match(
        date=datetime.date(2023, 1, 1),
        player_a=p1,
        player_b=p2,
        score_a=6,
        score_b=4,
        location="Court",
        format_name="6_game",
    )
    update_ratings(m1)
    club.matches.append(m1)

    cards = get_player_match_cards(clubs, "c", "p1")
    assert len(cards) == 1
    card = cards[0]
    assert card["self_score"] == 6
    assert card["opponent_score"] == 4
    assert card["opponent"] == "P2"
    delta = m1.rating_a_after - m1.rating_a_before
    assert card["self_delta"] == pytest.approx(delta)
