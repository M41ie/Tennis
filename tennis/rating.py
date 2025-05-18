from __future__ import annotations

import datetime
from typing import List, Tuple

from .models import Player, Match, DoublesMatch, Club

K_FACTOR = 32
TIME_DECAY = 0.99
MAX_HISTORY = 20

# Small rate that controls how much experience is gained per game played
BASE_EXPERIENCE_RATE = 0.05
# Bonus applied to weighted ratings based on accumulated experience
EXPERIENCE_BONUS = 0.1


def _experience_gain(rating: float, games: int, weight: float) -> float:
    """Return the experience gained from ``games`` played at ``weight``.

    ``rating`` is scaled so that higher rated players gain less experience.
    The factor ``7 / (7 - rating_level)`` approximates the difficulty curve
    described in the specification.
    """
    rating_level = rating / 1000.0
    difficulty = 7 / (7 - rating_level) if rating_level < 7 else 7.0
    return games * weight * BASE_EXPERIENCE_RATE / difficulty


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

    match.player_a.experience += _experience_gain(a_rating, games_played, match.format_weight)
    match.player_b.experience += _experience_gain(b_rating, games_played, match.format_weight)

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
        base = player.singles_rating
    else:
        total_weight = sum(weights)
        base = sum(r * w for r, w in zip(ratings, weights)) / total_weight

    return base + player.experience * EXPERIENCE_BONUS


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

    match.player_a1.experience += _experience_gain(match.player_a1.doubles_rating, games_played, match.format_weight)
    match.player_a2.experience += _experience_gain(match.player_a2.doubles_rating, games_played, match.format_weight)
    match.player_b1.experience += _experience_gain(match.player_b1.doubles_rating, games_played, match.format_weight)
    match.player_b2.experience += _experience_gain(match.player_b2.doubles_rating, games_played, match.format_weight)

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
        base = player.doubles_rating
    else:
        total_weight = sum(weights)
        base = sum(r * w for r, w in zip(ratings, weights)) / total_weight

    return base + player.experience * EXPERIENCE_BONUS


def initial_rating_from_votes(player: Player, club: Club, default: float = 1000.0) -> float:
    """Calculate a player's starting rating from pre-ratings.

    Each rater's vote is weighted by the number of singles matches they have
    played in the club. Players with no recorded matches contribute weight 1.
    If the player has no pre-ratings, ``default`` is returned.
    """

    if not player.pre_ratings:
        return default

    total = 0.0
    weight_sum = 0.0
    for rater_id, rating in player.pre_ratings.items():
        rater = club.members.get(rater_id)
        if not rater:
            continue
        weight = max(1, len(rater.singles_matches))
        total += rating * weight
        weight_sum += weight

    if weight_sum == 0:
        return default

    return total / weight_sum
