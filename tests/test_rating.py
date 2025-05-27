import datetime

import pytest

from tennis.models import Player, Match, DoublesMatch, Club
from tennis.rating import (
    update_ratings,
    update_doubles_ratings,
    weighted_rating,
    weighted_doubles_rating,
    expected_score,
    EXPERIENCE_BONUS,
    EXPERIENCE_RATE,
    initial_rating_from_votes,
    format_weight_from_name,
    FORMAT_6_GAME,
    FORMAT_4_GAME,
    FORMAT_TB11,
    FORMAT_TB10,
)


def expected_experience(rating: float, games: int, weight: float) -> float:
    if rating <= 0:
        return 0.0
    denom = (125 / (7 / rating - 1)) * ((6 + 12) / 2)
    if weight not in (FORMAT_6_GAME, FORMAT_4_GAME):
        denom *= ((4 + 7) / 2)
    if denom == 0:
        return 0.0
    return 0.5 / denom * games


def test_update_ratings_basic():
    a = Player("a", "A", singles_rating=3.0)
    b = Player("b", "B", singles_rating=3.0)
    match = Match(
        date=datetime.date(2023, 1, 1),
        player_a=a,
        player_b=b,
        score_a=6,
        score_b=4,
    )

    # calculate expected values before update
    games = match.score_a + match.score_b
    exp_a = expected_score(a.singles_rating, b.singles_rating)
    actual_a = match.score_a / games
    comp = match.format_weight * 0.25 * (actual_a - exp_a)
    gain = expected_experience(a.singles_rating, games, match.format_weight)
    expected_a = a.singles_rating + comp + gain
    expected_b = b.singles_rating - comp + gain

    new_a, new_b = update_ratings(match)

    assert pytest.approx(new_a, rel=1e-6) == expected_a
    assert pytest.approx(new_b, rel=1e-6) == expected_b
    exp_gain = expected_experience(3.0, games, 1.0)
    assert pytest.approx(a.experience, rel=1e-6) == exp_gain
    assert pytest.approx(b.experience, rel=1e-6) == exp_gain
    assert pytest.approx(a.singles_rating, rel=1e-6) == expected_a
    assert pytest.approx(b.singles_rating, rel=1e-6) == expected_b


def test_update_ratings_weight_and_margin():
    a = Player("a", "A", singles_rating=3.5)
    b = Player("b", "B", singles_rating=3.0)
    match = Match(
        date=datetime.date(2023, 1, 1),
        player_a=a,
        player_b=b,
        score_a=4,
        score_b=0,
        format_weight=0.7,
    )

    games = match.score_a + match.score_b
    exp_a = expected_score(a.singles_rating, b.singles_rating)
    actual_a = match.score_a / games
    comp = match.format_weight * 0.25 * (actual_a - exp_a)
    gain_a = expected_experience(a.singles_rating, games, match.format_weight)
    gain_b = expected_experience(b.singles_rating, games, match.format_weight)
    expected_a = a.singles_rating + comp + gain_a
    expected_b = b.singles_rating - comp + gain_b

    new_a, new_b = update_ratings(match)

    assert pytest.approx(new_a, rel=1e-6) == expected_a
    assert pytest.approx(new_b, rel=1e-6) == expected_b
    exp_gain_a = expected_experience(3.5, games, 0.7)
    exp_gain_b = expected_experience(3.0, games, 0.7)
    assert pytest.approx(a.experience, rel=1e-6) == exp_gain_a
    assert pytest.approx(b.experience, rel=1e-6) == exp_gain_b

def test_update_doubles_ratings_basic():
    a1 = Player("a1", "A1", doubles_rating=3.0)
    a2 = Player("a2", "A2", doubles_rating=3.0)
    b1 = Player("b1", "B1", doubles_rating=3.0)
    b2 = Player("b2", "B2", doubles_rating=3.0)
    match = DoublesMatch(
        date=datetime.date(2023, 1, 1),
        player_a1=a1,
        player_a2=a2,
        player_b1=b1,
        player_b2=b2,
        score_a=6,
        score_b=3,
    )

    games = match.score_a + match.score_b
    team_a_rating = (a1.doubles_rating + a2.doubles_rating) / 2
    team_b_rating = (b1.doubles_rating + b2.doubles_rating) / 2
    exp_a = expected_score(team_a_rating, team_b_rating)
    actual_a = match.score_a / games
    comp = match.format_weight * 0.25 * (actual_a - exp_a)

    delta_a1 = comp * (a1.doubles_rating / (a1.doubles_rating + a2.doubles_rating))
    delta_a2 = comp * (a2.doubles_rating / (a1.doubles_rating + a2.doubles_rating))
    delta_b1 = -comp * (b1.doubles_rating / (b1.doubles_rating + b2.doubles_rating))
    delta_b2 = -comp * (b2.doubles_rating / (b1.doubles_rating + b2.doubles_rating))

    gain_a1 = expected_experience(a1.doubles_rating, games, match.format_weight)
    gain_a2 = expected_experience(a2.doubles_rating, games, match.format_weight)
    gain_b1 = expected_experience(b1.doubles_rating, games, match.format_weight)
    gain_b2 = expected_experience(b2.doubles_rating, games, match.format_weight)

    expected = (
        a1.doubles_rating + delta_a1 + gain_a1,
        a2.doubles_rating + delta_a2 + gain_a2,
        b1.doubles_rating + delta_b1 + gain_b1,
        b2.doubles_rating + delta_b2 + gain_b2,
    )

    result = update_doubles_ratings(match)
    assert tuple(pytest.approx(x, rel=1e-6) for x in result) == tuple(pytest.approx(x, rel=1e-6) for x in expected)
    assert pytest.approx(a1.experience, rel=1e-6) == gain_a1
    assert pytest.approx(a2.experience, rel=1e-6) == gain_a2
    assert pytest.approx(b1.experience, rel=1e-6) == gain_b1
    assert pytest.approx(b2.experience, rel=1e-6) == gain_b2


def test_update_doubles_ratings_zero_total():
    a1 = Player("a1", "A1", doubles_rating=0.0)
    a2 = Player("a2", "A2", doubles_rating=0.0)
    b1 = Player("b1", "B1", doubles_rating=0.0)
    b2 = Player("b2", "B2", doubles_rating=0.0)
    match = DoublesMatch(
        date=datetime.date(2023, 1, 1),
        player_a1=a1,
        player_a2=a2,
        player_b1=b1,
        player_b2=b2,
        score_a=6,
        score_b=4,
    )

    games = match.score_a + match.score_b
    exp_a = expected_score(0.0, 0.0)
    actual_a = match.score_a / games
    comp = match.format_weight * 0.25 * (actual_a - exp_a)
    delta_each = comp / 2
    gain = expected_experience(0.0, games, match.format_weight)

    result = update_doubles_ratings(match)

    expected = (
        delta_each + gain,
        delta_each + gain,
        -delta_each + gain,
        -delta_each + gain,
    )

    assert tuple(pytest.approx(x, rel=1e-6) for x in result) == tuple(pytest.approx(x, rel=1e-6) for x in expected)
    assert pytest.approx(a1.experience, rel=1e-6) == gain
    assert pytest.approx(a2.experience, rel=1e-6) == gain
    assert pytest.approx(b1.experience, rel=1e-6) == gain
    assert pytest.approx(b2.experience, rel=1e-6) == gain


def test_weighted_rating_zero_score():
    player = Player("p", "P", singles_rating=0.0)

    assert pytest.approx(weighted_rating(player, datetime.date(2023, 1, 1)), rel=1e-6) == 0.0

def test_weighted_rating_time_decay():
    a = Player("a", "A")
    b = Player("b", "B")
    c = Player("c", "C")

    m1 = Match(
        date=datetime.date(2023, 1, 1),
        player_a=a,
        player_b=b,
        score_a=6,
        score_b=4,
    )
    update_ratings(m1)

    m2 = Match(
        date=datetime.date(2023, 1, 2),
        player_a=a,
        player_b=c,
        score_a=3,
        score_b=6,
    )
    update_ratings(m2)

    as_of = datetime.date(2023, 1, 3)
    expected = a.singles_rating + a.experience * EXPERIENCE_BONUS

    assert pytest.approx(weighted_rating(a, as_of), rel=1e-6) == expected


def test_weighted_doubles_rating_time_decay():
    a1 = Player("a1", "A1", doubles_rating=3.0)
    a2 = Player("a2", "A2", doubles_rating=3.0)
    b1 = Player("b1", "B1", doubles_rating=3.0)
    b2 = Player("b2", "B2", doubles_rating=3.0)

    m1 = DoublesMatch(
        date=datetime.date(2023, 1, 1),
        player_a1=a1,
        player_a2=a2,
        player_b1=b1,
        player_b2=b2,
        score_a=6,
        score_b=3,
    )
    update_doubles_ratings(m1)

    m2 = DoublesMatch(
        date=datetime.date(2023, 1, 2),
        player_a1=a1,
        player_a2=a2,
        player_b1=b1,
        player_b2=b2,
        score_a=3,
        score_b=6,
    )
    update_doubles_ratings(m2)

    as_of = datetime.date(2023, 1, 3)
    expected = a1.doubles_rating + a1.experience * EXPERIENCE_BONUS

    assert pytest.approx(weighted_doubles_rating(a1, as_of), rel=1e-6) == expected


def test_initial_rating_from_votes_weighting():
    club = Club(club_id="c", name="Club")

    r1 = Player("r1", "R1", singles_rating=1200.0)
    r2 = Player("r2", "R2", singles_rating=800.0)
    new = Player("n", "New")

    club.members[r1.user_id] = r1
    club.members[r2.user_id] = r2
    club.members[new.user_id] = new

    # give r1 two matches and r2 one match to weight r1 higher
    m_dummy = Match(
        date=datetime.date(2023, 1, 1),
        player_a=r1,
        player_b=r2,
        score_a=6,
        score_b=0,
    )
    r1.singles_matches.append(m_dummy)
    r1.singles_matches.append(m_dummy)
    r2.singles_matches.append(m_dummy)

    new.pre_ratings[r1.user_id] = 1100.0
    new.pre_ratings[r2.user_id] = 900.0

    rating = initial_rating_from_votes(new, club)

    expected = ((1100.0 * 2) + (900.0 * 1)) / 3
    assert pytest.approx(rating, rel=1e-6) == expected


def test_experience_bonus_accumulates():
    a = Player("a", "A")
    b = Player("b", "B")

    m1 = Match(
        date=datetime.date(2023, 1, 1),
        player_a=a,
        player_b=b,
        score_a=6,
        score_b=4,
    )
    update_ratings(m1)
    expected_first = a.singles_rating + a.experience * EXPERIENCE_BONUS
    assert pytest.approx(weighted_rating(a, m1.date), rel=1e-6) == expected_first

    m2 = Match(
        date=datetime.date(2023, 1, 2),
        player_a=a,
        player_b=b,
        score_a=6,
        score_b=4,
    )
    update_ratings(m2)

    as_of = m2.date
    expected_second = a.singles_rating + a.experience * EXPERIENCE_BONUS

    assert pytest.approx(weighted_rating(a, as_of), rel=1e-6) == expected_second
    assert expected_second > expected_first


def test_format_name_lookup():
    assert format_weight_from_name("6_game") == FORMAT_6_GAME
    assert format_weight_from_name("4_game") == FORMAT_4_GAME
    assert format_weight_from_name("tb11") == FORMAT_TB11
    assert format_weight_from_name("tb10") == FORMAT_TB10
    with pytest.raises(ValueError):
        format_weight_from_name("bogus")
