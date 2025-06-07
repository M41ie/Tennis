from __future__ import annotations

import datetime
from typing import List, Tuple

from .models import Player, Match, DoublesMatch, Club

K_FACTOR = 32
TIME_DECAY = 0.99
MAX_HISTORY = 5
EXPERIENCE_BONUS = 0.1
# Base rate for experience gain. Kept intentionally small so that
# accumulated experience only nudges the final rating.
EXPERIENCE_RATE = 0.05

# Match format weights
FORMAT_6_GAME = 1.0
FORMAT_4_GAME = 0.7
FORMAT_TB10 = 0.25
FORMAT_TB7 = 0.15

FORMAT_WEIGHTS = {
    "6_game": FORMAT_6_GAME,
    "4_game": FORMAT_4_GAME,
    "tb10": FORMAT_TB10,
    "tb7": FORMAT_TB7,
}


def format_weight_from_name(name: str) -> float:
    """Return the weight constant for the given format name."""
    key = name.lower()
    if key not in FORMAT_WEIGHTS:
        raise ValueError(f"Unknown format '{name}'")
    return FORMAT_WEIGHTS[key]


def expected_score(rating_a: float, rating_b: float) -> float:
    """Return the expected win ratio for ``rating_a`` against ``rating_b``.

    This mirrors the spreadsheet logic which uses a logistic function with base
    :math:`e` and a fixed slope of ``4``.
    """

    import math

    return 1 / (1 + math.exp(-4 * (rating_a - rating_b)))


def update_ratings(match: Match) -> Tuple[float, float]:
    """Update player ratings based on a match result.

    Returns the new ratings for player_a and player_b.
    """
    a_rating = match.player_a.singles_rating
    b_rating = match.player_b.singles_rating
    pre_a = a_rating
    pre_b = b_rating

    match.rating_a_before = a_rating
    match.rating_b_before = b_rating

    games_played = match.score_a + match.score_b
    if games_played == 0:
        return a_rating, b_rating

    exp_a = expected_score(a_rating, b_rating)
    actual_a = match.score_a / games_played

    # competitive skill adjustment
    delta_a = match.format_weight * 0.25 * (actual_a - exp_a)
    delta_b = -delta_a

    def _exp_gain(rating: float) -> float:
        if rating <= 0:
            return 0.0
        denom = (125 / (7 / rating - 1)) * ((6 + 12) / 2)
        if match.format_weight not in (FORMAT_6_GAME, FORMAT_4_GAME):
            denom *= ((4 + 7) / 2)
        if denom == 0:
            return 0.0
        return 0.5 / denom * games_played

    gain_a = _exp_gain(a_rating)
    gain_b = _exp_gain(b_rating)

    a_rating += delta_a + gain_a
    b_rating += delta_b + gain_b

    match.player_a.singles_rating = a_rating
    match.player_b.singles_rating = b_rating

    match.rating_a_after = a_rating
    match.rating_b_after = b_rating

    match.player_a.singles_matches.append(match)
    match.player_b.singles_matches.append(match)

    # record experience gained separately. ``weighted_rating`` simply returns
    # the stored rating without any additional bonus.
    match.player_a.experience += gain_a
    match.player_b.experience += gain_b

    return a_rating, b_rating


def weighted_rating(player: Player, as_of: datetime.date) -> float:
    """Return the player's current singles rating without extra bonus."""

    return player.singles_rating


def update_doubles_ratings(match: DoublesMatch) -> Tuple[float, float, float, float]:
    """Update doubles ratings for all players based on a doubles match.

    The logic mirrors :func:`update_ratings` but operates on the team averages
    and then distributes the adjustment to each partner proportionally by their
    pre-match rating. Experience gain also uses the same formula as singles.
    """

    team_a_rating = (match.player_a1.doubles_rating + match.player_a2.doubles_rating) / 2
    team_b_rating = (match.player_b1.doubles_rating + match.player_b2.doubles_rating) / 2

    match.rating_a1_before = match.player_a1.doubles_rating
    match.rating_a2_before = match.player_a2.doubles_rating
    match.rating_b1_before = match.player_b1.doubles_rating
    match.rating_b2_before = match.player_b2.doubles_rating
    pre_a1 = match.player_a1.doubles_rating
    pre_a2 = match.player_a2.doubles_rating
    pre_b1 = match.player_b1.doubles_rating
    pre_b2 = match.player_b2.doubles_rating

    exp_a = expected_score(team_a_rating, team_b_rating)

    games_played = match.score_a + match.score_b
    if games_played == 0:
        return team_a_rating, team_a_rating, team_b_rating, team_b_rating

    actual_a = match.score_a / games_played

    # competitive skill adjustment computed on the team averages
    delta_team = match.format_weight * 0.25 * (actual_a - exp_a)

    total_a = match.player_a1.doubles_rating + match.player_a2.doubles_rating
    total_b = match.player_b1.doubles_rating + match.player_b2.doubles_rating

    if total_a == 0:
        delta_a1 = delta_team / 2
        delta_a2 = delta_team / 2
    else:
        delta_a1 = delta_team * (match.player_a1.doubles_rating / total_a)
        delta_a2 = delta_team * (match.player_a2.doubles_rating / total_a)

    if total_b == 0:
        delta_b1 = -delta_team / 2
        delta_b2 = -delta_team / 2
    else:
        delta_b1 = -delta_team * (match.player_b1.doubles_rating / total_b)
        delta_b2 = -delta_team * (match.player_b2.doubles_rating / total_b)

    def _exp_gain(rating: float) -> float:
        if rating <= 0:
            return 0.0
        denom = (125 / (7 / rating - 1)) * ((6 + 12) / 2)
        if match.format_weight not in (FORMAT_6_GAME, FORMAT_4_GAME):
            denom *= ((4 + 7) / 2)
        return 0.5 / denom * games_played

    gain_a1 = _exp_gain(pre_a1)
    gain_a2 = _exp_gain(pre_a2)
    gain_b1 = _exp_gain(pre_b1)
    gain_b2 = _exp_gain(pre_b2)

    match.player_a1.doubles_rating += delta_a1 + gain_a1
    match.player_a2.doubles_rating += delta_a2 + gain_a2
    match.player_b1.doubles_rating += delta_b1 + gain_b1
    match.player_b2.doubles_rating += delta_b2 + gain_b2

    match.rating_a1_after = match.player_a1.doubles_rating
    match.rating_a2_after = match.player_a2.doubles_rating
    match.rating_b1_after = match.player_b1.doubles_rating
    match.rating_b2_after = match.player_b2.doubles_rating

    match.player_a1.doubles_matches.append(match)
    match.player_a2.doubles_matches.append(match)
    match.player_b1.doubles_matches.append(match)
    match.player_b2.doubles_matches.append(match)

    match.player_a1.experience += gain_a1
    match.player_a2.experience += gain_a2
    match.player_b1.experience += gain_b1
    match.player_b2.experience += gain_b2

    return (
        match.rating_a1_after,
        match.rating_a2_after,
        match.rating_b1_after,
        match.rating_b2_after,
    )


def weighted_doubles_rating(player: Player, as_of: datetime.date) -> float:
    """Return the player's current doubles rating without extra bonus."""

    return player.doubles_rating


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


def weighted_matches(player: Player) -> float:
    """Return the sum of match weights for a player."""

    total = sum(m.format_weight for m in player.singles_matches)
    total += sum(m.format_weight for m in player.doubles_matches)
    return total
