import datetime

import pytest

from tennis.models import Player, Match, DoublesMatch
from tennis.rating import (
    update_ratings,
    update_doubles_ratings,
    weighted_rating,
    weighted_doubles_rating,
    expected_score,
    TIME_DECAY,
)


def test_update_ratings_basic():
    a = Player("a", "A", singles_rating=1000.0)
    b = Player("b", "B", singles_rating=1000.0)
    match = Match(
        date=datetime.date(2023, 1, 1),
        player_a=a,
        player_b=b,
        score_a=6,
        score_b=4,
    )

    # calculate expected values before update
    exp_a = expected_score(a.singles_rating, b.singles_rating)
    games = match.score_a + match.score_b
    margin = abs(match.score_a - match.score_b) / games
    expected_delta = 32 * (1 - exp_a) * (1 + margin) * match.format_weight
    expected_a = a.singles_rating + expected_delta
    expected_b = b.singles_rating - expected_delta

    new_a, new_b = update_ratings(match)

    assert pytest.approx(new_a, rel=1e-6) == expected_a
    assert pytest.approx(new_b, rel=1e-6) == expected_b
    assert pytest.approx(a.singles_rating, rel=1e-6) == expected_a
    assert pytest.approx(b.singles_rating, rel=1e-6) == expected_b


def test_update_ratings_weight_and_margin():
    a = Player("a", "A", singles_rating=1100.0)
    b = Player("b", "B", singles_rating=1000.0)
    match = Match(
        date=datetime.date(2023, 1, 1),
        player_a=a,
        player_b=b,
        score_a=4,
        score_b=0,
        format_weight=0.7,
    )

    exp_a = expected_score(a.singles_rating, b.singles_rating)
    games = match.score_a + match.score_b
    margin = abs(match.score_a - match.score_b) / games
    expected_delta = 32 * (1 - exp_a) * (1 + margin) * match.format_weight
    expected_a = a.singles_rating + expected_delta
    expected_b = b.singles_rating - expected_delta

    new_a, new_b = update_ratings(match)

    assert pytest.approx(new_a, rel=1e-6) == expected_a
    assert pytest.approx(new_b, rel=1e-6) == expected_b


def test_update_doubles_ratings_basic():
    a1 = Player("a1", "A1")
    a2 = Player("a2", "A2")
    b1 = Player("b1", "B1")
    b2 = Player("b2", "B2")
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
    margin = abs(match.score_a - match.score_b) / games
    team_a_rating = (a1.doubles_rating + a2.doubles_rating) / 2
    team_b_rating = (b1.doubles_rating + b2.doubles_rating) / 2
    exp_a = expected_score(team_a_rating, team_b_rating)
    expected_delta = 32 * (1 - exp_a) * (1 + margin) * match.format_weight

    delta_a1 = expected_delta * (a1.doubles_rating / (a1.doubles_rating + a2.doubles_rating))
    delta_a2 = expected_delta * (a2.doubles_rating / (a1.doubles_rating + a2.doubles_rating))
    delta_b1 = -expected_delta * (b1.doubles_rating / (b1.doubles_rating + b2.doubles_rating))
    delta_b2 = -expected_delta * (b2.doubles_rating / (b1.doubles_rating + b2.doubles_rating))

    expected = (
        a1.doubles_rating + delta_a1,
        a2.doubles_rating + delta_a2,
        b1.doubles_rating + delta_b1,
        b2.doubles_rating + delta_b2,
    )

    result = update_doubles_ratings(match)
    assert tuple(pytest.approx(x, rel=1e-6) for x in result) == tuple(pytest.approx(x, rel=1e-6) for x in expected)


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
    weights = []
    ratings = []
    for m in reversed(a.singles_matches[-20:]):
        days = (as_of - m.date).days
        weight = TIME_DECAY ** days
        weights.append(weight)
        if m.player_a == a:
            ratings.append(m.rating_a_after)
        else:
            ratings.append(m.rating_b_after)
    total_weight = sum(weights)
    expected = sum(r * w for r, w in zip(ratings, weights)) / total_weight

    assert pytest.approx(weighted_rating(a, as_of), rel=1e-6) == expected


def test_weighted_doubles_rating_time_decay():
    a1 = Player("a1", "A1")
    a2 = Player("a2", "A2")
    b1 = Player("b1", "B1")
    b2 = Player("b2", "B2")

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
    weights = []
    ratings = []
    for m in reversed(a1.doubles_matches[-20:]):
        days = (as_of - m.date).days
        weight = TIME_DECAY ** days
        weights.append(weight)
        if m.player_a1 == a1:
            ratings.append(m.rating_a1_after)
        elif m.player_a2 == a1:
            ratings.append(m.rating_a2_after)
        elif m.player_b1 == a1:
            ratings.append(m.rating_b1_after)
        else:
            ratings.append(m.rating_b2_after)
    total_weight = sum(weights)
    expected = sum(r * w for r, w in zip(ratings, weights)) / total_weight

    assert pytest.approx(weighted_doubles_rating(a1, as_of), rel=1e-6) == expected
