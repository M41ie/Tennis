import datetime
import pytest
from tennis.models import Club, Player, Match
from tennis.cli import submit_match, confirm_match, approve_match
from tennis.rating import weighted_rating, update_ratings


def test_match_approval_workflow():
    club = Club(club_id="c", name="Club", leader_id="leader")
    p1 = Player("p1", "P1")
    p2 = Player("p2", "P2")
    leader = Player("leader", "L")
    club.members[p1.user_id] = p1
    club.members[p2.user_id] = p2
    club.members[leader.user_id] = leader
    clubs = {club.club_id: club}

    date = datetime.date(2023, 1, 1)
    submit_match(clubs, "c", "p1", "p2", 6, 4, date, 1.0)
    assert len(club.pending_matches) == 1
    match = club.pending_matches[0]
    assert match.confirmed_a
    assert not match.confirmed_b

    confirm_match(clubs, "c", 0, "p2")
    assert match.confirmed_b

    approve_match(clubs, "c", 0, "leader")
    assert len(club.pending_matches) == 0
    assert len(club.matches) == 1

    # compute expected ratings using a fresh reference calculation
    ref_p1 = Player("p1", "P1")
    ref_p2 = Player("p2", "P2")
    ref_match = Match(
        date=date,
        player_a=ref_p1,
        player_b=ref_p2,
        score_a=6,
        score_b=4,
    )
    update_ratings(ref_match)
    expected_p1 = weighted_rating(ref_p1, date)
    expected_p2 = weighted_rating(ref_p2, date)

    assert pytest.approx(p1.singles_rating, rel=1e-6) == expected_p1
    assert pytest.approx(p2.singles_rating, rel=1e-6) == expected_p2
