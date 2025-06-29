from __future__ import annotations
import datetime
import json
from .exceptions import ServiceError
from ..cli import (
    create_club as cli_create_club,
    add_player as cli_add_player,
    request_join as cli_request_join,
    approve_member as cli_approve_member,
    dissolve_club as cli_dissolve_club,
    approve_match as cli_approve_match,
    reject_application as cli_reject_application,
    clear_rejection as cli_clear_rejection,
    update_player as cli_update_player,
    remove_member as cli_remove_member,
    toggle_admin as cli_toggle_admin,
    transfer_leader as cli_transfer_leader,
    resign_admin as cli_resign_admin,
    quit_club as cli_quit_club,
    submit_match as cli_submit_match,
    confirm_match as cli_confirm_match,
    reject_match as cli_reject_match,
    veto_match as cli_veto_match,
    submit_doubles as cli_submit_doubles,
    confirm_doubles as cli_confirm_doubles,
    reject_doubles as cli_reject_doubles,
    veto_doubles as cli_veto_doubles,
    pre_rate as cli_pre_rate,
    record_match as cli_record_match,
    sys_set_leader as cli_sys_set_leader,
    normalize_gender,
)
from ..storage import (
    load_users,
    load_data,
    get_club,
    get_user,
    get_player,
    set_player,
    create_club as create_club_record,
    create_player,
    update_user_record,
    update_player_record,
    save_club,
    save_user,
    delete_club,
    create_appointment_record,
    update_appointment_record,
    transaction,
)
from .. import storage
from .helpers import get_club_or_404



def _find_pending_match(club, match_id: int) -> int:
    for idx, m in enumerate(club.pending_matches):
        if getattr(m, "id", None) == match_id:
            return idx
    raise ServiceError("Match not found", 404)


def _prepare_players(
    club: "Club" | None = None, extra: list[str] | None = None
) -> None:
    """Ensure players referenced by a club or ``extra`` ids are cached."""
    _, players = load_data()
    if club:
        for p in club.members.values():
            if p.user_id not in players:
                set_player(p)
    if extra:
        for uid in extra:
            if uid not in players:
                p = get_player(uid)
                if p:
                    set_player(p)


import uuid


def generate_club_id() -> str:
    """Return a random UUID based identifier for new clubs."""
    return uuid.uuid4().hex


def get_clubs_batch(ids: list[str]) -> list[Club]:
    """Return multiple ``Club`` objects, raising if any is not found."""
    clubs = []
    for cid in ids:
        clubs.append(get_club_or_404(cid))
    return clubs


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
    club = get_club(club_id)
    clubs = {club_id: club} if club else {}
    _prepare_players(club, extra=[user_id])
    try:
        cli_create_club(users, clubs, user_id, club_id, name, logo, region, slogan)
    except ValueError as e:
        raise ServiceError(str(e), 400)

    club = clubs[club_id]
    with transaction() as conn:
        create_club_record(club, conn=conn)
        create_player(club_id, club.members[user_id], conn=conn)
        update_user_record(users[user_id], conn=conn)
    storage.bump_cache_version()
    return club_id


def add_player(club_id: str, user_id: str, name: str, **kwargs):
    """Add a player to a club and persist the change."""
    club = get_club_or_404(club_id)
    clubs = {club_id: club}
    _prepare_players(club, extra=[user_id])
    try:
        cli_add_player(clubs, club_id, user_id, name, **kwargs)
    except ValueError as e:
        raise ServiceError(str(e), 400)

    player = clubs[club_id].members[user_id]
    with transaction() as conn:
        create_player(club_id, player, conn=conn)
        update_player_record(player, conn=conn)
    storage.bump_cache_version()


def request_join_club(club_id: str, user_id: str, **kwargs) -> None:
    """Handle a join request and persist affected records."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club, extra=[user_id])
    try:
        cli_request_join(clubs, users, club_id, user_id, **kwargs)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        for uid in [club.leader_id, *club.admin_ids]:
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)
    storage.bump_cache_version()


def approve_member_request(club_id: str, approver_id: str, user_id: str, rating: float, make_admin: bool = False) -> None:
    """Approve membership and persist changes."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    try:
        cli_approve_member(clubs, users, club_id, approver_id, user_id, rating, make_admin=make_admin)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    player = club.members[user_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        save_user(users[user_id], conn=conn)
        update_player_record(player, conn=conn)
        approver = users.get(approver_id)
        if approver:
            save_user(approver, conn=conn)
    storage.bump_cache_version()


def dissolve_existing_club(club_id: str, user_id: str) -> None:
    """Dissolve a club and update affected users."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    members = list(club.members)
    try:
        cli_dissolve_club(clubs, users, club_id, user_id)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    with transaction() as conn:
        delete_club(club_id, conn=conn)
        for uid in set(members + [user_id]):
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)
    storage.bump_cache_version()


def approve_pending_match(club_id: str, match_id: int, approver: str) -> None:
    """Approve a pending singles match and persist the club and users."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    index = _find_pending_match(club, match_id)
    match = club.pending_matches[index]
    try:
        cli_approve_match(clubs, club_id, index, approver, users)
    except ValueError as e:
        raise ServiceError(str(e), 400)
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
    storage.bump_cache_version()


def reject_join_request(club_id: str, approver_id: str, user_id: str, reason: str) -> None:
    """Reject a join request and persist club and user records."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    try:
        cli_reject_application(clubs, users, club_id, approver_id, user_id, reason)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        u = users.get(user_id)
        if u:
            save_user(u, conn=conn)
    storage.bump_cache_version()


def clear_member_rejection(club_id: str, user_id: str) -> None:
    """Clear a stored rejection reason."""
    club = get_club_or_404(club_id)
    clubs = {club_id: club}
    _prepare_players(club)
    try:
        cli_clear_rejection(clubs, club_id, user_id)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)


def update_club_info(club_id: str, **fields) -> None:
    """Update basic club fields."""
    club = get_club_or_404(club_id)
    if "name" in fields and fields["name"] is not None:
        club.name = fields["name"]
    if "logo" in fields and fields["logo"] is not None:
        club.logo = fields["logo"]
    if "region" in fields and fields["region"] is not None:
        club.region = fields["region"]
    if "slogan" in fields and fields["slogan"] is not None:
        club.slogan = fields["slogan"]
    with transaction() as conn:
        save_club(club, conn=conn)
    storage.bump_cache_version()


def update_global_player(user_id: str, **fields) -> None:
    """Update player information without club context."""
    users = load_users()
    player = get_player(user_id)
    if not player:
        raise ServiceError("Player not found", 404)
    _prepare_players(None, extra=[user_id])
    if fields.get("name") is not None:
        new_name = fields["name"]
        for u in users.values():
            if u.user_id != user_id and u.name == new_name:
                raise ServiceError("用户名已存在", 400)
        _, players = load_data()
        for p in players.values():
            if p.user_id != user_id and p.name == new_name:
                raise ServiceError("用户名已存在", 400)
        player.name = new_name
        if user_id in users:
            users[user_id].name = new_name
    if fields.get("age") is not None:
        player.age = fields["age"]
    if fields.get("gender") is not None:
        player.gender = normalize_gender(fields["gender"])
    if fields.get("avatar") is not None:
        player.avatar = fields["avatar"]
    if fields.get("birth") is not None:
        player.birth = fields["birth"]
    if fields.get("handedness") is not None:
        player.handedness = fields["handedness"]
    if fields.get("backhand") is not None:
        player.backhand = fields["backhand"]
    if fields.get("region") is not None:
        player.region = fields["region"]
    with transaction() as conn:
        update_player_record(player, conn=conn)
        if user_id in users:
            save_user(users[user_id], conn=conn)
    storage.bump_cache_version()


def update_player_profile(club_id: str, user_id: str, **fields) -> None:
    """Update a club member's profile."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    if fields.get("name") is not None:
        new_name = fields["name"]
        for u in users.values():
            if u.user_id != user_id and u.name == new_name:
                raise ServiceError("用户名已存在", 400)
        for p in players.values():
            if p.user_id != user_id and p.name == new_name:
                raise ServiceError("用户名已存在", 400)
    try:
        cli_update_player(clubs, club_id, user_id, **fields)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    player = clubs[club_id].members[user_id]
    if fields.get("name") is not None and user_id in users:
        users[user_id].name = fields["name"]
    with transaction() as conn:
        update_player_record(player, conn=conn)
        if user_id in users:
            save_user(users[user_id], conn=conn)


def remove_club_member(club_id: str, remover_id: str, user_id: str, ban: bool = False) -> None:
    """Remove a member from a club and update records."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    try:
        cli_remove_member(clubs, users, club_id, remover_id, user_id, ban=ban)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        u = users.get(user_id)
        if u:
            save_user(u, conn=conn)


def update_member_role(club_id: str, action: str, actor_id: str, target_id: str) -> None:
    """Perform a role-related action and persist changes."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    try:
        if action == "toggle_admin":
            cli_toggle_admin(clubs, club_id, actor_id, target_id)
        elif action == "transfer_leader":
            cli_transfer_leader(clubs, club_id, actor_id, target_id)
        elif action == "resign_admin":
            cli_resign_admin(clubs, club_id, actor_id)
        elif action == "quit":
            cli_quit_club(clubs, users, club_id, actor_id)
        else:
            raise ValueError("Invalid action")
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        for uid in {actor_id, target_id}:
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)
    storage.bump_cache_version()


def submit_pending_match(
    club_id: str,
    initiator: str,
    opponent: str,
    score_initiator: int,
    score_opponent: int,
    date: datetime.date,
    weight: float,
    *,
    location: str | None = None,
    format_name: str | None = None,
) -> None:
    """Create a pending singles match."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club, extra=[initiator, opponent])
    try:
        cli_submit_match(
            clubs,
            club_id,
            initiator,
            opponent,
            score_initiator,
            score_opponent,
            date,
            weight,
            location=location,
            format_name=format_name,
            users=users,
        )
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        for uid in [club.leader_id, *club.admin_ids]:
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)
    storage.bump_cache_version()


def confirm_pending_match(club_id: str, match_id: int, user_id: str) -> None:
    """Confirm a pending singles match."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    index = _find_pending_match(club, match_id)
    try:
        cli_confirm_match(clubs, club_id, index, user_id, users)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        for uid in [club.leader_id, *club.admin_ids]:
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)


def reject_pending_match(club_id: str, match_id: int, user_id: str) -> None:
    """Reject a pending singles match."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    index = _find_pending_match(club, match_id)
    try:
        cli_reject_match(clubs, club_id, index, user_id, users)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    match = club.pending_matches[index]
    with transaction() as conn:
        save_club(club, conn=conn)
        if match.initiator:
            u = users.get(match.initiator)
            if u:
                save_user(u, conn=conn)
    storage.bump_cache_version()


def veto_pending_match(club_id: str, match_id: int, approver: str) -> None:
    """Veto a pending singles match."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    index = _find_pending_match(club, match_id)
    try:
        cli_veto_match(clubs, club_id, index, approver, users)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    match = club.pending_matches[index]
    with transaction() as conn:
        save_club(club, conn=conn)
        if match.initiator:
            u = users.get(match.initiator)
            if u:
                save_user(u, conn=conn)


def submit_pending_doubles(
    club_id: str,
    initiator: str,
    partner: str,
    opponent1: str,
    opponent2: str,
    score_initiator: int,
    score_opponent: int,
    date: datetime.date,
    weight: float,
    *,
    location: str | None = None,
    format_name: str | None = None,
) -> None:
    """Create a pending doubles match."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club, extra=[initiator, partner, opponent1, opponent2])
    try:
        cli_submit_doubles(
            clubs,
            club_id,
            initiator,
            partner,
            opponent1,
            opponent2,
            score_initiator,
            score_opponent,
            date,
            weight,
            location=location,
            format_name=format_name,
            users=users,
        )
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        for uid in [club.leader_id, *club.admin_ids]:
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)


def confirm_pending_doubles(club_id: str, match_id: int, user_id: str) -> None:
    """Confirm a pending doubles match."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    index = _find_pending_match(club, match_id)
    try:
        cli_confirm_doubles(clubs, club_id, index, user_id, users)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        for uid in [club.leader_id, *club.admin_ids]:
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)


def reject_pending_doubles(club_id: str, match_id: int, user_id: str) -> None:
    """Reject a pending doubles match."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    index = _find_pending_match(club, match_id)
    try:
        cli_reject_doubles(clubs, club_id, index, user_id, users)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    match = club.pending_matches[index]
    with transaction() as conn:
        save_club(club, conn=conn)
        if match.initiator:
            u = users.get(match.initiator)
            if u:
                save_user(u, conn=conn)


def veto_pending_doubles(club_id: str, match_id: int, approver: str) -> None:
    """Veto a pending doubles match."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    index = _find_pending_match(club, match_id)
    try:
        cli_veto_doubles(clubs, club_id, index, approver, users)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    match = club.pending_matches[index]
    with transaction() as conn:
        save_club(club, conn=conn)
        if match.initiator:
            u = users.get(match.initiator)
            if u:
                save_user(u, conn=conn)


def create_appointment_entry(club_id: str, appt: Appointment) -> None:
    """Create an appointment and persist it."""
    club = get_club_or_404(club_id)
    club.appointments.append(appt)
    with transaction() as conn:
        create_appointment_record(club_id, appt, conn=conn)
    storage.bump_cache_version()


def update_appointment_signups(club_id: str, index: int, *, add: str | None = None, remove: str | None = None) -> None:
    """Add or remove a signup for an appointment."""
    club = get_club_or_404(club_id)
    if index >= len(club.appointments):
        raise ServiceError("Appointment not found", 404)
    appt = club.appointments[index]
    with transaction() as conn:
        row = conn.execute(
            "SELECT id, signups FROM appointments WHERE club_id = ? ORDER BY id LIMIT 1 OFFSET ?",
            (club_id, index),
        ).fetchone()
        if not row:
            raise ServiceError("Appointment not found", 404)
        value = row["signups"]
        if isinstance(value, str):
            parsed = json.loads(value or "[]")
        else:
            parsed = value or []
        signups = set(parsed)
        if add:
            signups.add(add)
            appt.signups.add(add)
        if remove:
            signups.discard(remove)
            appt.signups.discard(remove)
        update_appointment_record(row["id"], conn=conn, signups=signups)
    storage.bump_cache_version()


def pre_rate_member(club_id: str, rater_id: str, target_id: str, rating: float) -> None:
    """Record a pre-rating and persist the player."""
    club = get_club_or_404(club_id)
    clubs = {club_id: club}
    _prepare_players(club)
    try:
        cli_pre_rate(clubs, club_id, rater_id, target_id, rating)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    player = clubs[club_id].members[target_id]
    with transaction() as conn:
        update_player_record(player, conn=conn)
    storage.bump_cache_version()


def record_match_result(
    club_id: str,
    user_a: str,
    user_b: str,
    score_a: int,
    score_b: int,
    date: datetime.date,
    weight: float,
    *,
    location: str | None = None,
    format_name: str | None = None,
) -> None:
    """Record a finished singles match and persist affected players."""
    club = get_club_or_404(club_id)
    clubs = {club_id: club}
    _prepare_players(club)
    try:
        cli_record_match(
            clubs,
            club_id,
            user_a,
            user_b,
            score_a,
            score_b,
            date,
            weight,
            location=location,
            format_name=format_name,
        )
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    pa = club.members[user_a]
    pb = club.members[user_b]
    with transaction() as conn:
        save_club(club, conn=conn)
        update_player_record(pa, conn=conn)
        update_player_record(pb, conn=conn)
    storage.bump_cache_version()


def sys_set_leader(club_id: str, user_id: str) -> None:
    """System admin sets club leader and persist changes."""
    club = get_club_or_404(club_id)
    users = load_users()
    clubs = {club_id: club}
    _prepare_players(club)
    try:
        cli_sys_set_leader(clubs, club_id, user_id)
    except ValueError as e:
        raise ServiceError(str(e), 400)
    club = clubs[club_id]
    with transaction() as conn:
        save_club(club, conn=conn)
        for uid in [user_id, club.leader_id]:
            u = users.get(uid)
            if u:
                save_user(u, conn=conn)
    storage.bump_cache_version()


