from .exceptions import ServiceError
from .. import storage
from ..models import Player, DoublesMatch, Match


def get_player_friends(user_id: str) -> list[dict[str, object]]:
    """Return aggregated interaction stats for a player."""

    player = storage.get_player(user_id)
    if not player:
        raise ServiceError("Player not found", 404)

    friends: dict[str, dict[str, object]] = {}

    def update(
        p: Player,
        win: bool,
        weight: float,
        *,
        singles: bool = False,
        doubles: bool = False,
        partner: bool = False,
        score_diff: float = 0.0,
    ) -> None:
        if p.user_id == user_id:
            return
        entry = friends.setdefault(
            p.user_id,
            {
                "user_id": p.user_id,
                "name": p.name,
                "avatar": p.avatar,
                "weight": 0.0,
                "wins": 0.0,
                "singles_weight": 0.0,
                "singles_wins": 0.0,
                "doubles_weight": 0.0,
                "doubles_wins": 0.0,
                "partner_games": 0.0,
                "partner_wins": 0.0,
                "singles_score_diff": 0.0,
                "doubles_score_diff": 0.0,
                "partner_score_diff": 0.0,
            },
        )
        entry["weight"] += weight
        if win:
            entry["wins"] += weight
        if singles:
            entry["singles_weight"] += weight
            if win:
                entry["singles_wins"] += weight
            entry["singles_score_diff"] += score_diff
        if doubles:
            entry["doubles_weight"] += weight
            if win:
                entry["doubles_wins"] += weight
            entry["doubles_score_diff"] += score_diff
        if partner:
            entry["partner_games"] += weight
            if win:
                entry["partner_wins"] += weight
            entry["partner_score_diff"] += score_diff

    for m in player.singles_matches:
        if m.player_a == player:
            opp = m.player_b
            win = m.score_a > m.score_b
            if m.rating_a_after is not None and m.rating_a_before is not None:
                diff = m.rating_a_after - m.rating_a_before
            else:
                diff = 0.0
        else:
            opp = m.player_a
            win = m.score_b > m.score_a
            if m.rating_b_after is not None and m.rating_b_before is not None:
                diff = m.rating_b_after - m.rating_b_before
            else:
                diff = 0.0
        update(opp, win, m.format_weight, singles=True, score_diff=diff)

    for m in player.doubles_matches:
        if player in (m.player_a1, m.player_a2):
            partner = m.player_a2 if m.player_a1 == player else m.player_a1
            opponents = (m.player_b1, m.player_b2)
            win = m.score_a > m.score_b
            if player == m.player_a1:
                after = m.rating_a1_after
                before = m.rating_a1_before
            else:
                after = m.rating_a2_after
                before = m.rating_a2_before
        else:
            partner = m.player_b2 if m.player_b1 == player else m.player_b1
            opponents = (m.player_a1, m.player_a2)
            win = m.score_b > m.score_a
            if player == m.player_b1:
                after = m.rating_b1_after
                before = m.rating_b1_before
            else:
                after = m.rating_b2_after
                before = m.rating_b2_before
        if after is not None and before is not None:
            diff = after - before
        else:
            diff = 0.0
        # partner interactions should not count towards doubles opponent stats
        update(partner, win, m.format_weight, partner=True, score_diff=diff)
        for opp in opponents:
            update(opp, win, m.format_weight, doubles=True, score_diff=diff)

    result = list(friends.values())
    result.sort(key=lambda x: x["weight"], reverse=True)
    for r in result:
        r["weight"] = round(r["weight"], 2)
        r["wins"] = round(r["wins"], 2)
        r["singles_weight"] = round(r["singles_weight"], 2)
        r["singles_wins"] = round(r["singles_wins"], 2)
        r["doubles_weight"] = round(r["doubles_weight"], 2)
        r["doubles_wins"] = round(r["doubles_wins"], 2)
        r["partner_games"] = round(r["partner_games"], 2)
        r["partner_wins"] = round(r["partner_wins"], 2)
        r["singles_score_diff"] = round(r["singles_score_diff"], 3)
        r["doubles_score_diff"] = round(r["doubles_score_diff"], 3)
        r["partner_score_diff"] = round(r["partner_score_diff"], 3)
    return result

__all__ = ["get_player_friends"]
