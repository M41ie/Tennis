from .exceptions import ServiceError
from .. import storage
from ..models import Player, DoublesMatch, Match


def get_player_friends(user_id: str) -> list[dict[str, object]]:
    """Return aggregated interaction stats for a player."""

    player = storage.get_player(user_id)
    if not player:
        raise ServiceError("Player not found", 404)

    friends: dict[str, dict[str, object]] = {}

    def update(p: Player, win: bool, weight: float, partner: bool = False) -> None:
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
                "partner_games": 0.0,
                "partner_wins": 0.0,
            },
        )
        entry["weight"] += weight
        if win:
            entry["wins"] += weight
        if partner:
            entry["partner_games"] += weight
            if win:
                entry["partner_wins"] += weight

    for m in player.singles_matches:
        if m.player_a == player:
            opp = m.player_b
            win = m.score_a > m.score_b
        else:
            opp = m.player_a
            win = m.score_b > m.score_a
        update(opp, win, m.format_weight)

    for m in player.doubles_matches:
        if player in (m.player_a1, m.player_a2):
            partner = m.player_a2 if m.player_a1 == player else m.player_a1
            opponents = (m.player_b1, m.player_b2)
            win = m.score_a > m.score_b
        else:
            partner = m.player_b2 if m.player_b1 == player else m.player_b1
            opponents = (m.player_a1, m.player_a2)
            win = m.score_b > m.score_a
        update(partner, win, m.format_weight, partner=True)
        for opp in opponents:
            update(opp, win, m.format_weight)

    result = list(friends.values())
    result.sort(key=lambda x: x["weight"], reverse=True)
    for r in result:
        r["weight"] = round(r["weight"], 2)
        r["wins"] = round(r["wins"], 2)
        r["partner_games"] = round(r["partner_games"], 2)
        r["partner_wins"] = round(r["partner_wins"], 2)
    return result

__all__ = ["get_player_friends"]
