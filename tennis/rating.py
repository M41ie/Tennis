from __future__ import annotations

import datetime
from typing import List, Tuple

from .models import Player, Match

K_FACTOR = 32
TIME_DECAY = 0.99
MAX_HISTORY = 20


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_ratings(match: Match) -> Tuple[float, float]:
    """Update player ratings based on a match result.

    Returns the new ratings for player_a and player_b.
    """
    a_rating = match.player_a.singles_rating
    b_rating = match.player_b.singles_rating
    exp_a = expected_score(a_rating, b_rating)
    exp_b = 1 - exp_a

    games_played = match.score_a + match.score_b
    if games_played == 0:
        return a_rating, b_rating
    margin = abs(match.score_a - match.score_b) / games_played

    actual_a = 1 if match.score_a > match.score_b else 0
    actual_b = 1 - actual_a

    delta_a = K_FACTOR * (actual_a - exp_a) * (1 + margin) * match.format_weight
    delta_b = K_FACTOR * (actual_b - exp_b) * (1 + margin) * match.format_weight

    a_rating += delta_a
    b_rating += delta_b

    match.player_a.singles_rating = a_rating
    match.player_b.singles_rating = b_rating

    match.player_a.matches.append(match)
    match.player_b.matches.append(match)

    return a_rating, b_rating


def weighted_rating(player: Player, as_of: datetime.date) -> float:
    """Calculate the time-decayed weighted average rating of a player."""
    weights = []
    ratings = []

    for m in reversed(player.matches[-MAX_HISTORY:]):
        days = (as_of - m.date).days
        weight = TIME_DECAY ** days
        weights.append(weight)
        if m.player_a == player:
            ratings.append(m.player_a.singles_rating)
        else:
            ratings.append(m.player_b.singles_rating)

    if not ratings:
        return player.singles_rating

    total_weight = sum(weights)
    return sum(r * w for r, w in zip(ratings, weights)) / total_weight
