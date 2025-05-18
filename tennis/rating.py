from __future__ import annotations

import datetime
from typing import List, Tuple

from .models import Player, Match, DoublesMatch

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

    match.rating_a_after = a_rating
    match.rating_b_after = b_rating

    match.player_a.singles_matches.append(match)
    match.player_b.singles_matches.append(match)

    return a_rating, b_rating


def weighted_rating(player: Player, as_of: datetime.date) -> float:
    """Calculate the time-decayed weighted average rating of a player's singles matches."""
    weights: List[float] = []
    ratings: List[float] = []

    for m in reversed(player.singles_matches[-MAX_HISTORY:]):
        days = (as_of - m.date).days
        weight = TIME_DECAY ** days
        weights.append(weight)
        if m.player_a == player:
            ratings.append(m.rating_a_after or player.singles_rating)
        else:
            ratings.append(m.rating_b_after or player.singles_rating)

    if not ratings:
        return player.singles_rating

    total_weight = sum(weights)
    return sum(r * w for r, w in zip(ratings, weights)) / total_weight


def update_doubles_ratings(match: DoublesMatch) -> Tuple[float, float, float, float]:
    """Update doubles ratings for all players based on a doubles match."""
    team_a_rating = (match.player_a1.doubles_rating + match.player_a2.doubles_rating) / 2
    team_b_rating = (match.player_b1.doubles_rating + match.player_b2.doubles_rating) / 2

    exp_a = expected_score(team_a_rating, team_b_rating)
    exp_b = 1 - exp_a

    games_played = match.score_a + match.score_b
    if games_played == 0:
        return team_a_rating, team_a_rating, team_b_rating, team_b_rating
    margin = abs(match.score_a - match.score_b) / games_played

    actual_a = 1 if match.score_a > match.score_b else 0
    actual_b = 1 - actual_a

    delta_team_a = K_FACTOR * (actual_a - exp_a) * (1 + margin) * match.format_weight
    delta_team_b = K_FACTOR * (actual_b - exp_b) * (1 + margin) * match.format_weight

    total_a = match.player_a1.doubles_rating + match.player_a2.doubles_rating
    total_b = match.player_b1.doubles_rating + match.player_b2.doubles_rating

    delta_a1 = delta_team_a * (match.player_a1.doubles_rating / total_a)
    delta_a2 = delta_team_a * (match.player_a2.doubles_rating / total_a)
    delta_b1 = delta_team_b * (match.player_b1.doubles_rating / total_b)
    delta_b2 = delta_team_b * (match.player_b2.doubles_rating / total_b)

    match.player_a1.doubles_rating += delta_a1
    match.player_a2.doubles_rating += delta_a2
    match.player_b1.doubles_rating += delta_b1
    match.player_b2.doubles_rating += delta_b2

    match.rating_a1_after = match.player_a1.doubles_rating
    match.rating_a2_after = match.player_a2.doubles_rating
    match.rating_b1_after = match.player_b1.doubles_rating
    match.rating_b2_after = match.player_b2.doubles_rating

    match.player_a1.doubles_matches.append(match)
    match.player_a2.doubles_matches.append(match)
    match.player_b1.doubles_matches.append(match)
    match.player_b2.doubles_matches.append(match)

    return (
        match.rating_a1_after,
        match.rating_a2_after,
        match.rating_b1_after,
        match.rating_b2_after,
    )


def weighted_doubles_rating(player: Player, as_of: datetime.date) -> float:
    """Calculate time-decayed weighted average doubles rating of a player."""
    weights: List[float] = []
    ratings: List[float] = []

    for m in reversed(player.doubles_matches[-MAX_HISTORY:]):
        days = (as_of - m.date).days
        weight = TIME_DECAY ** days
        weights.append(weight)
        if m.player_a1 == player:
            ratings.append(m.rating_a1_after or player.doubles_rating)
        elif m.player_a2 == player:
            ratings.append(m.rating_a2_after or player.doubles_rating)
        elif m.player_b1 == player:
            ratings.append(m.rating_b1_after or player.doubles_rating)
        else:
            ratings.append(m.rating_b2_after or player.doubles_rating)

    if not ratings:
        return player.doubles_rating

    total_weight = sum(weights)
    return sum(r * w for r, w in zip(ratings, weights)) / total_weight
