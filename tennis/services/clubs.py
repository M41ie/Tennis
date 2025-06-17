from __future__ import annotations
from fastapi import HTTPException
from ..cli import create_club as cli_create_club, add_player as cli_add_player
from ..storage import (
    load_data,
    load_users,
    create_club as create_club_record,
    create_player,
    update_user_record,
    update_player_record,
)


def generate_club_id() -> str:
    clubs = load_data()
    i = 1
    while f"c{i}" in clubs:
        i += 1
    return f"c{i}"


def create_club(
    user_id: str,
    name: str,
    club_id: str,
    logo=None,
    region=None,
    slogan=None,
):
    """Create a new club and persist it to the database."""
    users = load_users()
    clubs = load_data()
    try:
        cli_create_club(users, clubs, user_id, club_id, name, logo, region, slogan)
    except ValueError as e:
        raise HTTPException(400, str(e))

    create_club_record(clubs[club_id])
    create_player(club_id, clubs[club_id].members[user_id])
    update_user_record(users[user_id])
    return club_id


def add_player(club_id: str, user_id: str, name: str, **kwargs):
    """Add a player to a club and persist the change."""
    clubs = load_data()
    try:
        cli_add_player(clubs, club_id, user_id, name, **kwargs)
    except ValueError as e:
        raise HTTPException(400, str(e))

    player = clubs[club_id].members[user_id]
    create_player(club_id, player)
    update_player_record(player)


