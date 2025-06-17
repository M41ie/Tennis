from __future__ import annotations
from fastapi import HTTPException
from ..cli import (
    create_club as cli_create_club,
    add_player as cli_add_player,
    request_join as cli_request_join,
    approve_member as cli_approve_member,
    dissolve_club as cli_dissolve_club,
    approve_match as cli_approve_match,
)
from ..storage import (
    load_data,
    load_users,
    create_club as create_club_record,
    create_player,
    update_user_record,
    update_player_record,
    save_club,
    save_user,
    delete_club,
    transaction,
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

    with transaction() as conn:
        create_club_record(clubs[club_id], conn=conn)
        create_player(club_id, clubs[club_id].members[user_id], conn=conn)
        update_user_record(users[user_id], conn=conn)
    return club_id


def add_player(club_id: str, user_id: str, name: str, **kwargs):
    """Add a player to a club and persist the change."""
    clubs = load_data()
    try:
        cli_add_player(clubs, club_id, user_id, name, **kwargs)
    except ValueError as e:
        raise HTTPException(400, str(e))

    player = clubs[club_id].members[user_id]
    with transaction() as conn:
        create_player(club_id, player, conn=conn)
        update_player_record(player, conn=conn)


def request_join_club(club_id: str, user_id: str, **kwargs) -> None:
    """Handle a join request and persist affected records."""
    clubs = load_data()
    users = load_users()
    try:
        cli_request_join(clubs, users, club_id, user_id, **kwargs)
    except ValueError as e:
        raise HTTPException(400, str(e))
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        for uid in [club.leader_id, *club.admin_ids]:
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)


def approve_member_request(club_id: str, approver_id: str, user_id: str, rating: float, make_admin: bool = False) -> None:
    """Approve membership and persist changes."""
    clubs = load_data()
    users = load_users()
    try:
        cli_approve_member(clubs, users, club_id, approver_id, user_id, rating, make_admin=make_admin)
    except ValueError as e:
        raise HTTPException(400, str(e))
    club = clubs[club_id]
    player = club.members[user_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        save_user(users[user_id], conn=conn)
        update_player_record(player, conn=conn)
        approver = users.get(approver_id)
        if approver:
            save_user(approver, conn=conn)


def dissolve_existing_club(club_id: str, user_id: str) -> None:
    """Dissolve a club and update affected users."""
    clubs = load_data()
    users = load_users()
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    members = list(club.members)
    try:
        cli_dissolve_club(clubs, users, club_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    with transaction() as conn:
        delete_club(club_id, conn=conn)
        for uid in set(members + [user_id]):
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)


def approve_pending_match(club_id: str, index: int, approver: str) -> None:
    """Approve a pending singles match and persist the club and users."""
    clubs = load_data()
    users = load_users()
    club = clubs.get(club_id)
    if not club:
        raise HTTPException(404, "Club not found")
    if index >= len(club.pending_matches):
        raise HTTPException(404, "Match not found")
    match = club.pending_matches[index]
    try:
        cli_approve_match(clubs, club_id, index, approver, users)
    except ValueError as e:
        raise HTTPException(400, str(e))
    participants = (
        [match.player_a.user_id, match.player_b.user_id]
        if not hasattr(match, "player_a1")
        else [
            match.player_a1.user_id,
            match.player_a2.user_id,
            match.player_b1.user_id,
            match.player_b2.user_id,
        ]
    )
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        for uid in set(participants + [approver]):
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)


