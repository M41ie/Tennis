import argparse
import datetime
import random
import string
from passlib.context import CryptContext
from typing import Optional

from .models import (
    Player,
    Club,
    Match,
    DoublesMatch,
    User,
    Message,
    JoinApplication,
    MAX_CREATED_CLUBS,
    MAX_JOINED_CLUBS,
)
from .rating import (
    update_ratings,
    update_doubles_ratings,
    weighted_rating,
    weighted_doubles_rating,
    initial_rating_from_votes,
    format_weight_from_name,
    FORMAT_WEIGHTS,
    expected_score,
)
from .storage import load_data, save_data, load_users, save_users


players: dict[str, Player] = {}
from .services.stats import get_leaderboard


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def check_password(user: User, password: str) -> bool:
    try:
        return pwd_context.verify(password, user.password_hash)
    except Exception:
        return False


def normalize_gender(g: str | None) -> str | None:
    """Return canonical gender codes 'M'/'F' or None."""
    if not g:
        return None
    g = g.strip()
    if g in {"M", "Male", "男"}:
        return "M"
    if g in {"F", "Female", "女"}:
        return "F"
    return g


def validate_scores(score_a, score_b):
    """Ensure scores are non-negative integers."""
    if not (isinstance(score_a, int) and isinstance(score_b, int)):
        raise ValueError("Invalid score")
    if score_a < 0 or score_b < 0:
        raise ValueError("Invalid score")


def cleanup_pending_matches(club: Club) -> None:
    """Remove expired pending matches from a club."""
    today = datetime.date.today()
    remaining = []
    for m in club.pending_matches:
        if m.status in {"rejected", "vetoed"}:
            if m.status_date and (today - m.status_date).days >= 3:
                continue
        elif not (m.confirmed_a and m.confirmed_b):
            if (today - m.created).days >= 7:
                continue
        else:
            base = m.confirmed_on or m.created
            if (today - base).days >= 7:
                continue
        remaining.append(m)
    club.pending_matches = remaining


def _next_user_id(users, *, use_uuid: bool = False) -> str:
    """Return a new user id.

    When ``use_uuid`` is ``True`` a 7 character alphanumeric identifier is
    generated. Duplicate values are avoided by regenerating until an unused
    string is found.

    Otherwise the next available alphabetic ID (A, B, ..., Z, AA, ...) is
    chosen. Existing IDs that fit the pattern are skipped so gaps are filled
    and custom user IDs do not affect the sequence.
    """

    if use_uuid:
        alphabet = string.ascii_letters + string.digits
        while True:
            uid = "".join(random.choice(alphabet) for _ in range(7))
            if uid not in users:
                return uid

    def encode(n: int) -> str:
        s = ""
        while n > 0:
            n, rem = divmod(n - 1, 26)
            s = chr(ord("A") + rem) + s
        return s

    idx = 1
    while encode(idx) in users:
        idx += 1

    s = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        s = chr(ord("A") + rem) + s
    return s


def register_user(
    users,
    user_id: str | None,
    name: str,
    password: str,
    allow_create: bool = False,
    *,
    use_uuid: bool = False,
    avatar: str | None = None,
    gender: str | None = None,
    birth: str | None = None,
    handedness: str | None = None,
    backhand: str | None = None,
    region: str | None = None,
):
    """Add a new user account."""
    if not user_id:
        user_id = _next_user_id(users, use_uuid=use_uuid)
    if user_id in users:
        raise ValueError("User already exists")
    for u in users.values():
        if u.name == name:
            raise ValueError("用户名已存在")
    for p in players.values():
        if p.name == name:
            raise ValueError("用户名已存在")
    users[user_id] = User(
        user_id=user_id,
        name=name,
        password_hash=hash_password(password),
        can_create_club=True,
        is_sys_admin=(not users) and not use_uuid,
        max_creatable_clubs=1 if allow_create else MAX_CREATED_CLUBS,
    )
    gender = normalize_gender(gender)
    if user_id not in players:
        players[user_id] = Player(
            user_id=user_id,
            name=name,
            avatar=avatar,
            gender=gender,
            birth=birth,
            handedness=handedness,
            backhand=backhand,
            region=region,
        )
    return user_id


def resolve_user(users, identifier: str) -> User | None:
    """Return the User matching the given ID or name."""
    user = users.get(identifier)
    if not user:
        for u in users.values():
            if u.name == identifier:
                user = u
                break
    return user


def set_user_limits(users, user_id: str, max_joinable: int, max_creatable: int) -> None:
    """Update per-user club limits."""
    u = users.get(user_id)
    if not u:
        raise ValueError("User not found")
    u.max_joinable_clubs = max_joinable
    u.max_creatable_clubs = max_creatable


def login_user(users, identifier: str, password: str) -> bool:
    """Verify a user's password by ID or name."""
    user = resolve_user(users, identifier)
    if not user:
        return False
    return check_password(user, password)


def request_join(
    clubs,
    users,
    club_id: str,
    user_id: str,
    singles_rating: float | None = None,
    doubles_rating: float | None = None,
    reason: str | None = None,
):
    """User requests to join a club."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    # allow re-applying after a rejection
    club.rejected_members.pop(user_id, None)
    if user_id in club.banned_ids:
        raise ValueError("User banned")
    if user_id in club.members:
        raise ValueError("Already member")
    if user_id not in users:
        raise ValueError("User not registered")
    club.pending_members[user_id] = JoinApplication(
        reason=reason,
        singles_rating=singles_rating,
        doubles_rating=doubles_rating,
    )

    # notify leader and admins of pending request
    today = datetime.date.today()
    for uid in [club.leader_id, *club.admin_ids]:
        if not uid:
            continue
        u = users.get(uid)
        if u is not None:
            u.messages.append(
                Message(date=today, text=f"Join request from {user_id} for club {club.name}")
            )


def approve_member(
    clubs,
    users,
    club_id: str,
    approver_id: str,
    user_id: str,
    rating: float,
    make_admin: bool = False,
):
    """Approve a pending member request and assign an initial rating."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    if approver_id != club.leader_id and approver_id not in club.admin_ids:
        raise ValueError("Not authorized")
    if user_id not in club.pending_members:
        raise ValueError("No request")
    user = users.get(user_id)
    if not user:
        raise ValueError("User not registered")
    if user.joined_clubs >= user.max_joinable_clubs:
        raise ValueError("加入俱乐部的数量已达上限")
    club.pending_members.pop(user_id, None)
    player = players.get(user_id)
    if player is None:
        player = Player(user_id=user.user_id, name=user.name)
        players[user_id] = player
    if player.singles_rating is None:
        player.singles_rating = rating
    if player.doubles_rating is None:
        player.doubles_rating = rating
    club.members[user_id] = player
    user.joined_clubs += 1
    if make_admin:
        if len(club.admin_ids) >= 3:
            raise ValueError("Admin limit reached")
        club.admin_ids.add(user_id)
    user.messages.append(
        Message(
            date=datetime.date.today(),
            text=f"Approved to join club {club.name}",
        )
    )


def reject_application(
    clubs,
    users,
    club_id: str,
    approver_id: str,
    user_id: str,
    reason: str,
):
    """Reject a pending join request with a reason."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    if approver_id != club.leader_id and approver_id not in club.admin_ids:
        raise ValueError("Not authorized")
    if user_id not in club.pending_members:
        raise ValueError("No request")
    club.pending_members.pop(user_id, None)
    club.rejected_members[user_id] = reason
    user = users.get(user_id)
    if user is not None:
        user.messages.append(
            Message(
                date=datetime.date.today(),
                text=f"Join request for club {club.name} rejected: {reason}",
            )
        )


def clear_rejection(clubs, club_id: str, user_id: str):
    """Remove stored rejection reason so the user can reapply."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    club.rejected_members.pop(user_id, None)


def create_club(users, clubs, user_id: str, club_id: str, name: str, logo: Optional[str], region: Optional[str], slogan: Optional[str] = None):
    user = users.get(user_id)
    if not user:
        raise ValueError('User not found')
    if user.created_clubs >= user.max_creatable_clubs:
        raise ValueError('创建俱乐部的数量已达上限')
    if user.joined_clubs >= user.max_joinable_clubs:
        raise ValueError('加入俱乐部的数量已达上限')
    if club_id in clubs:
        raise ValueError('Club already exists')
    for c in clubs.values():
        if c.name == name:
            raise ValueError('俱乐部名已存在')
    clubs[club_id] = Club(
        club_id=club_id,
        name=name,
        logo=logo,
        region=region,
        slogan=slogan,
        leader_id=user_id,
    )
    club = clubs[club_id]
    player = players.get(user_id)
    if player is None:
        player = Player(user_id=user_id, name=user.name)
        players[user_id] = player
    club.members[user_id] = player
    user.created_clubs += 1
    user.joined_clubs += 1


def add_player(
    clubs,
    club_id: str,
    user_id: str,
    name: str,
    age: int | None = None,
    gender: str | None = None,
    avatar: str | None = None,
    birth: str | None = None,
    handedness: str | None = None,
    backhand: str | None = None,
    region: str | None = None,
):
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    if user_id in club.members:
        raise ValueError('Player already in club')
    player = players.get(user_id)
    if player is None:
        player = Player(
            user_id=user_id,
            name=name,
            age=age,
            gender=normalize_gender(gender),
            avatar=avatar,
            birth=birth,
            handedness=handedness,
            backhand=backhand,
            region=region,
        )
        players[user_id] = player
    else:
        if name is not None:
            player.name = name
        if age is not None:
            player.age = age
        if gender is not None:
            player.gender = normalize_gender(gender)
        if avatar is not None:
            player.avatar = avatar
        if birth is not None:
            player.birth = birth
        if handedness is not None:
            player.handedness = handedness
        if backhand is not None:
            player.backhand = backhand
        if region is not None:
            player.region = region
    club.members[user_id] = player


def update_player(
    clubs,
    club_id: str,
    user_id: str,
    name: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    avatar: str | None = None,
    birth: str | None = None,
    handedness: str | None = None,
    backhand: str | None = None,
    region: str | None = None,
):
    """Modify an existing player's profile."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    player = club.members.get(user_id)
    if not player:
        raise ValueError('Player not found')
    if name is not None:
        player.name = name
    if age is not None:
        player.age = age
    if gender is not None:
        player.gender = normalize_gender(gender)
    if avatar is not None:
        player.avatar = avatar
    if birth is not None:
        player.birth = birth
    if handedness is not None:
        player.handedness = handedness
    if backhand is not None:
        player.backhand = backhand
    if region is not None:
        player.region = region


def remove_member(
    clubs,
    users,
    club_id: str,
    remover_id: str,
    user_id: str,
    ban: bool = False,
):
    """Remove a member from a club and optionally ban them."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    if remover_id != club.leader_id and remover_id not in club.admin_ids:
        raise ValueError("Not authorized")
    if user_id not in club.members:
        raise ValueError("Player not found")

    club.members.pop(user_id)
    club.admin_ids.discard(user_id)
    if ban:
        club.banned_ids.add(user_id)

    user = users.get(user_id)
    if user and user.joined_clubs > 0:
        user.joined_clubs -= 1


def toggle_admin(clubs, club_id: str, actor_id: str, target_id: str):
    """Leader toggles admin role for a member."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    if actor_id != club.leader_id:
        raise ValueError("Not authorized")
    if target_id not in club.members or target_id == club.leader_id:
        raise ValueError("Player not found")

    if target_id in club.admin_ids:
        club.admin_ids.remove(target_id)
    else:
        if len(club.admin_ids) >= 3:
            raise ValueError("Admin limit reached")
        club.admin_ids.add(target_id)


def transfer_leader(clubs, club_id: str, actor_id: str, target_id: str):
    """Transfer club leadership to another member."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    if actor_id != club.leader_id:
        raise ValueError("Not authorized")
    if target_id not in club.members:
        raise ValueError("Player not found")
    if target_id == club.leader_id:
        return

    old_leader = club.leader_id
    club.leader_id = target_id
    club.admin_ids.discard(target_id)
    if old_leader and len(club.admin_ids) < 3:
        club.admin_ids.add(old_leader)


def sys_set_leader(clubs, club_id: str, target_id: str):
    """System admin directly sets club leader."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    if target_id not in club.members:
        raise ValueError("Player not found")
    old_leader = club.leader_id
    if target_id == old_leader:
        return
    club.leader_id = target_id
    club.admin_ids.discard(target_id)
    if old_leader and old_leader != target_id and len(club.admin_ids) < 3:
        club.admin_ids.add(old_leader)


def resign_admin(clubs, club_id: str, user_id: str):
    """Admin resigns their role."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    club.admin_ids.discard(user_id)


def quit_club(clubs, users, club_id: str, user_id: str):
    """Member quits a club."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    if user_id == club.leader_id:
        raise ValueError("Leader cannot quit")
    if user_id not in club.members:
        raise ValueError("Player not found")
    club.members.pop(user_id)
    club.admin_ids.discard(user_id)
    u = users.get(user_id)
    if u and u.joined_clubs > 0:
        u.joined_clubs -= 1


def dissolve_club(clubs, users, club_id: str, user_id: str):
    """Leader dissolves a club and removes all memberships."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    if user_id != club.leader_id:
        raise ValueError("Not authorized")
    for uid in list(club.members):
        u = users.get(uid)
        if u and u.joined_clubs > 0:
            u.joined_clubs -= 1
    leader = users.get(club.leader_id)
    if leader and leader.created_clubs > 0:
        leader.created_clubs -= 1
    clubs.pop(club_id, None)


def pre_rate(clubs, club_id: str, rater_id: str, target_id: str, rating: float):
    """Record a pre-rating for ``target_id`` from ``rater_id``."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    rater = club.members.get(rater_id)
    target = club.members.get(target_id)
    if not rater or not target:
        raise ValueError('Both rater and target must be in club')

    target.pre_ratings[rater_id] = rating
    new_rating = initial_rating_from_votes(target, club)
    target.singles_rating = new_rating
    target.doubles_rating = new_rating


def submit_match(
    clubs,
    club_id: str,
    initiator: str,
    opponent: str,
    score_initiator: int,
    score_opponent: int,
    date: datetime.date,
    weight: float,
    location: str | None = None,
    format_name: str | None = None,
    *,
    users: dict | None = None,
):
    """Start a match record pending confirmation and approval."""
    validate_scores(score_initiator, score_opponent)
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    cleanup_pending_matches(club)
    cleanup_pending_matches(club)
    p_init = club.members.get(initiator)
    p_opp = club.members.get(opponent)
    if not p_init or not p_opp:
        raise ValueError("Both players must be in club")
    match = Match(
        date=date,
        club_id=club_id,
        player_a=p_init,
        player_b=p_opp,
        score_a=score_initiator,
        score_b=score_opponent,
        format_weight=weight,
        location=location,
        format_name=format_name,
        initiator=initiator,
    )
    if initiator == p_init.user_id:
        match.confirmed_a = True
    else:
        match.confirmed_b = True
    club.pending_matches.append(match)

    # Do not notify admins until all participants have confirmed


def confirm_match(clubs, club_id: str, index: int, user_id: str, users=None):
    """Player confirms a pending match."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    cleanup_pending_matches(club)
    if index >= len(club.pending_matches):
        raise ValueError("Match not found")
    match = club.pending_matches[index]
    if match.player_a.user_id == user_id:
        match.confirmed_a = True
    elif match.player_b.user_id == user_id:
        match.confirmed_b = True
    else:
        raise ValueError("User not in match")

    if match.confirmed_a and match.confirmed_b and users is not None:
        today = datetime.date.today()
        if match.confirmed_on is None:
            match.confirmed_on = today
        for uid in [club.leader_id, *club.admin_ids]:
            if not uid:
                continue
            u = users.get(uid)
            if u:
                u.messages.append(
                    Message(date=today, text=f"Match pending approval in {club.name}")
                )


def reject_match(clubs, club_id: str, index: int, user_id: str, users=None):
    """Participant rejects a pending singles match."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    cleanup_pending_matches(club)
    if index >= len(club.pending_matches):
        raise ValueError("Match not found")
    match = club.pending_matches[index]
    participants = {match.player_a.user_id, match.player_b.user_id}
    if user_id not in participants:
        raise ValueError("User not in match")
    match.status = "rejected"
    match.status_date = datetime.date.today()
    if users is not None and match.initiator:
        initiator = users.get(match.initiator)
        if initiator:
            initiator.messages.append(
                Message(
                    date=datetime.date.today(),
                    text=f"Match on {match.date.isoformat()} rejected in {club.name}",
                )
            )


def veto_match(clubs, club_id: str, index: int, approver: str, users=None):
    """Admin vetoes a pending singles match without approval."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    cleanup_pending_matches(club)
    if index >= len(club.pending_matches):
        raise ValueError("Match not found")
    is_sys_admin = False
    if users is not None:
        u = users.get(approver)
        is_sys_admin = bool(u and getattr(u, "is_sys_admin", False))
    if approver != club.leader_id and approver not in club.admin_ids and not is_sys_admin:
        raise ValueError("Not authorized")
    match = club.pending_matches[index]
    from .models import DoublesMatch
    if isinstance(match, DoublesMatch):
        raise ValueError("Not a singles match")
    match.status = "vetoed"
    match.status_date = datetime.date.today()
    if users is not None and match.initiator:
        initiator = users.get(match.initiator)
        if initiator:
            initiator.messages.append(
                Message(
                    date=datetime.date.today(),
                    text=f"Match on {match.date.isoformat()} vetoed in {club.name}",
                )
            )


def veto_doubles(clubs, club_id: str, index: int, approver: str, users=None):
    """Admin vetoes a pending doubles match without approval."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    cleanup_pending_matches(club)
    if index >= len(club.pending_matches):
        raise ValueError("Match not found")
    is_sys_admin = False
    if users is not None:
        u = users.get(approver)
        is_sys_admin = bool(u and getattr(u, "is_sys_admin", False))
    if approver != club.leader_id and approver not in club.admin_ids and not is_sys_admin:
        raise ValueError("Not authorized")
    match = club.pending_matches[index]
    if not isinstance(match, DoublesMatch):
        raise ValueError("Not a doubles match")
    match.status = "vetoed"
    match.status_date = datetime.date.today()
    if users is not None and match.initiator:
        initiator = users.get(match.initiator)
        if initiator:
            initiator.messages.append(
                Message(
                    date=datetime.date.today(),
                    text=f"Match on {match.date.isoformat()} vetoed in {club.name}",
                )
            )


def submit_doubles(
    clubs,
    club_id: str,
    initiator: str,
    partner: str,
    opponent1: str,
    opponent2: str,
    score_initiator: int,
    score_opponent: int,
    date: datetime.date,
    weight: float,
    location: str | None = None,
    format_name: str | None = None,
    *,
    users: dict | None = None,
):
    """Start a doubles match pending confirmation and approval.

    The initiator is automatically placed on team A along with ``partner``. The
    opponents form team B. Only the initiator's team is pre-confirmed.
    """
    validate_scores(score_initiator, score_opponent)
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")

    pa1 = club.members.get(initiator)
    pa2 = club.members.get(partner)
    pb1 = club.members.get(opponent1)
    pb2 = club.members.get(opponent2)
    if not all([pa1, pa2, pb1, pb2]):
        raise ValueError("All players must be in club")

    match = DoublesMatch(
        date=date,
        club_id=club_id,
        player_a1=pa1,
        player_a2=pa2,
        player_b1=pb1,
        player_b2=pb2,
        score_a=score_initiator,
        score_b=score_opponent,
        format_weight=weight,
        location=location,
        format_name=format_name,
        initiator=initiator,
    )
    match.confirmed_a = True
    club.pending_matches.append(match)

    if users is not None:
        today = datetime.date.today()
        for uid in [club.leader_id, *club.admin_ids]:
            if not uid:
                continue
            u = users.get(uid)
            if u:
                u.messages.append(
                    Message(date=today, text=f"Doubles match pending approval in {club.name}")
                )


def confirm_doubles(clubs, club_id: str, index: int, user_id: str, users=None):
    """Confirm a pending doubles match."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    cleanup_pending_matches(club)
    if index >= len(club.pending_matches):
        raise ValueError("Match not found")
    match = club.pending_matches[index]
    if not isinstance(match, DoublesMatch):
        raise ValueError("Not a doubles match")
    if user_id in (match.player_a1.user_id, match.player_a2.user_id):
        match.confirmed_a = True
    elif user_id in (match.player_b1.user_id, match.player_b2.user_id):
        match.confirmed_b = True
    else:
        raise ValueError("User not in match")

    if match.confirmed_a and match.confirmed_b and users is not None:
        today = datetime.date.today()
        if match.confirmed_on is None:
            match.confirmed_on = today
        for uid in [club.leader_id, *club.admin_ids]:
            if not uid:
                continue
            u = users.get(uid)
            if u:
                u.messages.append(
                    Message(date=today, text=f"Doubles match pending approval in {club.name}")
                )


def reject_doubles(clubs, club_id: str, index: int, user_id: str, users=None):
    """Participant rejects a pending doubles match."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    cleanup_pending_matches(club)
    if index >= len(club.pending_matches):
        raise ValueError("Match not found")
    match = club.pending_matches[index]
    if not isinstance(match, DoublesMatch):
        raise ValueError("Not a doubles match")
    participants = {
        match.player_a1.user_id,
        match.player_a2.user_id,
        match.player_b1.user_id,
        match.player_b2.user_id,
    }
    if user_id not in participants:
        raise ValueError("User not in match")
    match.status = "rejected"
    match.status_date = datetime.date.today()
    if users is not None and match.initiator:
        initiator = users.get(match.initiator)
        if initiator:
            initiator.messages.append(
                Message(
                    date=datetime.date.today(),
                    text=f"Match on {match.date.isoformat()} rejected in {club.name}",
                )
            )


def approve_doubles(clubs, club_id: str, index: int, approver: str, users=None):
    """Approve a pending doubles match and apply ratings."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    if index >= len(club.pending_matches):
        raise ValueError("Match not found")
    match = club.pending_matches[index]
    if not isinstance(match, DoublesMatch):
        raise ValueError("Not a doubles match")
    approve_match(clubs, club_id, index, approver, users)


def approve_match(clubs, club_id: str, index: int, approver: str, users=None):
    """Leader or admin approves a confirmed match and apply ratings."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    cleanup_pending_matches(club)
    if index >= len(club.pending_matches):
        raise ValueError("Match not found")
    is_sys_admin = False
    if users is not None:
        u = users.get(approver)
        is_sys_admin = bool(u and getattr(u, "is_sys_admin", False))
    if approver != club.leader_id and approver not in club.admin_ids and not is_sys_admin:
        raise ValueError("Not authorized")
    match = club.pending_matches[index]
    if not (match.confirmed_a and match.confirmed_b):
        raise ValueError("Match not confirmed")
    match = club.pending_matches.pop(index)
    match.approved = True
    club.matches.append(match)
    if isinstance(match, DoublesMatch):
        update_doubles_ratings(match)
        players = [match.player_a1, match.player_a2, match.player_b1, match.player_b2]
        for p in players:
            p.doubles_rating = weighted_doubles_rating(p, match.date)
    else:
        update_ratings(match)
        pa = match.player_a
        pb = match.player_b
        pa.singles_rating = weighted_rating(pa, match.date)
        pb.singles_rating = weighted_rating(pb, match.date)
    if users:
        date_str = match.date.isoformat()
        if isinstance(match, DoublesMatch):
            participant_ids = [match.player_a1.user_id, match.player_a2.user_id, match.player_b1.user_id, match.player_b2.user_id]
        else:
            participant_ids = [match.player_a.user_id, match.player_b.user_id]
        for uid in participant_ids:
            u = users.get(uid)
            if u:
                u.messages.append(
                    Message(date=match.date, text=f"Match on {date_str} approved in {club.name}")
                )


def record_match(
    clubs,
    club_id: str,
    user_a: str,
    user_b: str,
    score_a: int,
    score_b: int,
    date: datetime.date,
    weight: float,
    location: str | None = None,
    format_name: str | None = None,
):
    validate_scores(score_a, score_b)
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    pa = club.members.get(user_a)
    pb = club.members.get(user_b)
    if not pa or not pb:
        raise ValueError('Both players must be in club')
    match = Match(
        date=date,
        club_id=club_id,
        player_a=pa,
        player_b=pb,
        score_a=score_a,
        score_b=score_b,
        format_weight=weight,
        location=location,
        format_name=format_name,
    )
    update_ratings(match)
    clubs[club_id].matches.append(match)

    rating_a = weighted_rating(pa, date)
    rating_b = weighted_rating(pb, date)
    pa.singles_rating = rating_a
    pb.singles_rating = rating_b
    print(f"New ratings: {pa.name} {rating_a:.1f}, {pb.name} {rating_b:.1f}")


def record_doubles(
    clubs,
    club_id: str,
    a1: str,
    a2: str,
    b1: str,
    b2: str,
    score_a: int,
    score_b: int,
    date: datetime.date,
    weight: float,
    location: str | None = None,
    format_name: str | None = None,
):
    validate_scores(score_a, score_b)
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    pa1 = club.members.get(a1)
    pa2 = club.members.get(a2)
    pb1 = club.members.get(b1)
    pb2 = club.members.get(b2)
    if not all([pa1, pa2, pb1, pb2]):
        raise ValueError('All players must be in club')
    match = DoublesMatch(
        date=date,
        club_id=club_id,
        player_a1=pa1,
        player_a2=pa2,
        player_b1=pb1,
        player_b2=pb2,
        score_a=score_a,
        score_b=score_b,
        format_weight=weight,
        location=location,
        format_name=format_name,
    )
    update_doubles_ratings(match)
    clubs[club_id].matches.append(match)
    rating_a1 = weighted_doubles_rating(pa1, date)
    rating_a2 = weighted_doubles_rating(pa2, date)
    rating_b1 = weighted_doubles_rating(pb1, date)
    rating_b2 = weighted_doubles_rating(pb2, date)
    pa1.doubles_rating = rating_a1
    pa2.doubles_rating = rating_a2
    pb1.doubles_rating = rating_b1
    pb2.doubles_rating = rating_b2
    print(
        f"New doubles ratings: {pa1.name} {rating_a1:.1f}, {pa2.name} {rating_a2:.1f}, "
        f"{pb1.name} {rating_b1:.1f}, {pb2.name} {rating_b2:.1f}"
    )



def leaderboard(
    clubs,
    club_id: str,
    doubles: bool,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    gender: str | None = None,
):
    data = get_leaderboard(
        clubs,
        club_id,
        doubles,
        min_rating=min_rating,
        max_rating=max_rating,
        min_age=min_age,
        max_age=max_age,
        gender=gender,
    )
    for p, rating in data:
        avatar = p.avatar or "-"
        print(f"{avatar} {p.name}: {rating:.1f}")


def get_player_match_cards(clubs, club_id: str, user_id: str):
    """Return a list of match card info dictionaries for a player."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    player = club.members.get(user_id)
    if not player:
        raise ValueError("Player not found")

    cards = []
    for m in club.matches:
        if isinstance(m, DoublesMatch):
            continue
        if m.player_a != player and m.player_b != player:
            continue
        if m.player_a == player:
            opp = m.player_b
            self_score = m.score_a
            opp_score = m.score_b
            self_after = m.rating_a_after
            self_before = m.rating_a_before
            opp_after = m.rating_b_after
            opp_before = m.rating_b_before
        else:
            opp = m.player_a
            self_score = m.score_b
            opp_score = m.score_a
            self_after = m.rating_b_after
            self_before = m.rating_b_before
            opp_after = m.rating_a_after
            opp_before = m.rating_a_before

        # calculate expected and actual scoring rates
        if self_before is not None and opp_before is not None:
            exp_rate = expected_score(self_before, opp_before)
        else:
            exp_rate = None
        total = self_score + opp_score
        actual_rate = self_score / total if total > 0 else None

        cards.append(
            {
                "date": m.date,
                "created_ts": m.created_ts,
                "location": m.location,
                "format": m.format_name,
                "self_score": self_score,
                "opponent_score": opp_score,
                "opponent": opp.name,
                "opponent_id": opp.user_id,
                "opponent_avatar": opp.avatar,
                "expected_score": exp_rate,
                "actual_rate": actual_rate,
                "self_rating_after": self_after,
                "self_delta": (
                    self_after - self_before
                    if self_after is not None and self_before is not None
                    else None
                ),
                "opponent_rating_after": opp_after,
                "opponent_delta": (
                    opp_after - opp_before
                    if opp_after is not None and opp_before is not None
                    else None
                ),
            }
        )

    cards.sort(key=lambda x: (x["date"], x["created_ts"]), reverse=True)
    for c in cards:
        del c["created_ts"]
    return cards


def _match_to_card(m: Match, player: Player) -> dict:
    """Return card info for a single match from the player's perspective."""
    if m.player_a == player:
        opp = m.player_b
        self_score = m.score_a
        opp_score = m.score_b
        self_after = m.rating_a_after
        self_before = m.rating_a_before
        opp_after = m.rating_b_after
        opp_before = m.rating_b_before
    else:
        opp = m.player_a
        self_score = m.score_b
        opp_score = m.score_a
        self_after = m.rating_b_after
        self_before = m.rating_b_before
        opp_after = m.rating_a_after
        opp_before = m.rating_a_before

    if self_before is not None and opp_before is not None:
        exp_rate = expected_score(self_before, opp_before)
    else:
        exp_rate = None
    total = self_score + opp_score
    actual_rate = self_score / total if total > 0 else None

    return {
        "date": m.date,
        "created_ts": m.created_ts,
        "location": m.location,
        "format": m.format_name,
        "self_score": self_score,
        "opponent_score": opp_score,
        "opponent": opp.name,
        "opponent_id": opp.user_id,
        "opponent_avatar": opp.avatar,
        "expected_score": exp_rate,
        "actual_rate": actual_rate,
        "self_rating_after": self_after,
        "self_delta": (
            self_after - self_before if self_after is not None and self_before is not None else None
        ),
        "opponent_rating_after": opp_after,
        "opponent_delta": (
            opp_after - opp_before if opp_after is not None and opp_before is not None else None
        ),
        "club_id": m.club_id,
    }


def get_player_global_match_cards(player: Player) -> list[dict]:
    """Return match cards for a player across all clubs."""
    cards = [_match_to_card(m, player) for m in player.singles_matches]
    cards.sort(key=lambda x: (x["date"], x["created_ts"]), reverse=True)
    for c in cards:
        del c["created_ts"]
    return cards


def get_player_doubles_cards(clubs, club_id: str, user_id: str):
    """Return a list of doubles match card info for a player."""
    club = clubs.get(club_id)
    if not club:
        raise ValueError("Club not found")
    player = club.members.get(user_id)
    if not player:
        raise ValueError("Player not found")

    cards = []
    for m in club.matches:
        if not isinstance(m, DoublesMatch):
            continue
        if player not in (m.player_a1, m.player_a2, m.player_b1, m.player_b2):
            continue
        if player in (m.player_a1, m.player_a2):
            partner = m.player_a2 if m.player_a1 == player else m.player_a1
            opp1, opp2 = m.player_b1, m.player_b2
            self_score = m.score_a
            opp_score = m.score_b
            if player == m.player_a1:
                self_after = m.rating_a1_after
                self_before = m.rating_a1_before
                partner_after = m.rating_a2_after
                partner_before = m.rating_a2_before
            else:
                self_after = m.rating_a2_after
                self_before = m.rating_a2_before
                partner_after = m.rating_a1_after
                partner_before = m.rating_a1_before
            opp1_after = m.rating_b1_after
            opp1_before = m.rating_b1_before
            opp2_after = m.rating_b2_after
            opp2_before = m.rating_b2_before
        else:
            partner = m.player_b2 if m.player_b1 == player else m.player_b1
            opp1, opp2 = m.player_a1, m.player_a2
            self_score = m.score_b
            opp_score = m.score_a
            if player == m.player_b1:
                self_after = m.rating_b1_after
                self_before = m.rating_b1_before
                partner_after = m.rating_b2_after
                partner_before = m.rating_b2_before
            else:
                self_after = m.rating_b2_after
                self_before = m.rating_b2_before
                partner_after = m.rating_b1_after
                partner_before = m.rating_b1_before
            opp1_after = m.rating_a1_after
            opp1_before = m.rating_a1_before
            opp2_after = m.rating_a2_after
            opp2_before = m.rating_a2_before

        # expected and actual scoring rates for the player's team
        if (
            m.rating_a1_before is not None
            and m.rating_a2_before is not None
            and m.rating_b1_before is not None
            and m.rating_b2_before is not None
        ):
            team_a_before = (m.rating_a1_before + m.rating_a2_before) / 2
            team_b_before = (m.rating_b1_before + m.rating_b2_before) / 2
            if player in (m.player_a1, m.player_a2):
                exp_rate = expected_score(team_a_before, team_b_before)
            else:
                exp_rate = expected_score(team_b_before, team_a_before)
        else:
            exp_rate = None

        total = self_score + opp_score
        actual_rate = self_score / total if total > 0 else None

        cards.append(
            {
                "date": m.date,
                "created_ts": m.created_ts,
                "location": m.location,
                "format": m.format_name,
                "self_score": self_score,
                "opponent_score": opp_score,
                "partner": partner.name,
                "partner_id": partner.user_id,
                "partner_avatar": partner.avatar,
                "partner_rating_after": partner_after,
                "partner_delta": (
                    partner_after - partner_before
                    if partner_after is not None and partner_before is not None
                    else None
                ),
                "opponent1": opp1.name,
                "opponent1_id": opp1.user_id,
                "opponent1_avatar": opp1.avatar,
                "opponent1_rating_after": opp1_after,
                "opponent1_delta": (
                    opp1_after - opp1_before
                    if opp1_after is not None and opp1_before is not None
                    else None
                ),
                "opponent2": opp2.name,
                "opponent2_id": opp2.user_id,
                "opponent2_avatar": opp2.avatar,
                "opponent2_rating_after": opp2_after,
                "opponent2_delta": (
                    opp2_after - opp2_before
                    if opp2_after is not None and opp2_before is not None
                    else None
                ),
                "opponents": f"{opp1.name}/{opp2.name}",
                "expected_score": exp_rate,
                "actual_rate": actual_rate,
                "self_rating_after": self_after,
                "self_delta": (
                    self_after - self_before
                    if self_after is not None and self_before is not None
                    else None
                ),
            }
        )

    cards.sort(key=lambda x: (x["date"], x["created_ts"]), reverse=True)
    for c in cards:
        del c["created_ts"]
    return cards


def _doubles_match_to_card(m: DoublesMatch, player: Player) -> dict:
    if player in (m.player_a1, m.player_a2):
        partner = m.player_a2 if m.player_a1 == player else m.player_a1
        opp1, opp2 = m.player_b1, m.player_b2
        self_score = m.score_a
        opp_score = m.score_b
        if player == m.player_a1:
            self_after = m.rating_a1_after
            self_before = m.rating_a1_before
            partner_after = m.rating_a2_after
            partner_before = m.rating_a2_before
        else:
            self_after = m.rating_a2_after
            self_before = m.rating_a2_before
            partner_after = m.rating_a1_after
            partner_before = m.rating_a1_before
        opp1_after = m.rating_b1_after
        opp1_before = m.rating_b1_before
        opp2_after = m.rating_b2_after
        opp2_before = m.rating_b2_before
    else:
        partner = m.player_b2 if m.player_b1 == player else m.player_b1
        opp1, opp2 = m.player_a1, m.player_a2
        self_score = m.score_b
        opp_score = m.score_a
        if player == m.player_b1:
            self_after = m.rating_b1_after
            self_before = m.rating_b1_before
            partner_after = m.rating_b2_after
            partner_before = m.rating_b2_before
        else:
            self_after = m.rating_b2_after
            self_before = m.rating_b2_before
            partner_after = m.rating_b1_after
            partner_before = m.rating_b1_before
        opp1_after = m.rating_a1_after
        opp1_before = m.rating_a1_before
        opp2_after = m.rating_a2_after
        opp2_before = m.rating_a2_before

    if (
        m.rating_a1_before is not None
        and m.rating_a2_before is not None
        and m.rating_b1_before is not None
        and m.rating_b2_before is not None
    ):
        team_a_before = (m.rating_a1_before + m.rating_a2_before) / 2
        team_b_before = (m.rating_b1_before + m.rating_b2_before) / 2
        if player in (m.player_a1, m.player_a2):
            exp_rate = expected_score(team_a_before, team_b_before)
        else:
            exp_rate = expected_score(team_b_before, team_a_before)
    else:
        exp_rate = None

    total = self_score + opp_score
    actual_rate = self_score / total if total > 0 else None

    return {
        "date": m.date,
        "created_ts": m.created_ts,
        "location": m.location,
        "format": m.format_name,
        "self_score": self_score,
        "opponent_score": opp_score,
        "partner": partner.name,
        "partner_id": partner.user_id,
        "partner_avatar": partner.avatar,
        "partner_rating_after": partner_after,
        "partner_delta": (
            partner_after - partner_before if partner_after is not None and partner_before is not None else None
        ),
        "opponent1": opp1.name,
        "opponent1_id": opp1.user_id,
        "opponent1_avatar": opp1.avatar,
        "opponent1_rating_after": opp1_after,
        "opponent1_delta": (
            opp1_after - opp1_before if opp1_after is not None and opp1_before is not None else None
        ),
        "opponent2": opp2.name,
        "opponent2_id": opp2.user_id,
        "opponent2_avatar": opp2.avatar,
        "opponent2_rating_after": opp2_after,
        "opponent2_delta": (
            opp2_after - opp2_before if opp2_after is not None and opp2_before is not None else None
        ),
        "opponents": f"{opp1.name}/{opp2.name}",
        "expected_score": exp_rate,
        "actual_rate": actual_rate,
        "self_rating_after": self_after,
        "self_delta": (
            self_after - self_before if self_after is not None and self_before is not None else None
        ),
        "club_id": m.club_id,
    }


def get_player_global_doubles_cards(player: Player) -> list[dict]:
    cards = [_doubles_match_to_card(m, player) for m in player.doubles_matches]
    cards.sort(key=lambda x: (x["date"], x["created_ts"]), reverse=True)
    for c in cards:
        del c["created_ts"]
    return cards


def player_history(clubs, club_id: str, user_id: str, doubles: bool):
    club = clubs.get(club_id)
    if not club:
        raise ValueError('Club not found')
    player = club.members.get(user_id)
    if not player:
        raise ValueError('Player not found')
    if doubles:
        matches = player.doubles_matches
        for m in matches:
            if m.player_a1 == player:
                rating = m.rating_a1_after
            elif m.player_a2 == player:
                rating = m.rating_a2_after
            elif m.player_b1 == player:
                rating = m.rating_b1_after
            else:
                rating = m.rating_b2_after
            opponents = (
                f"{m.player_b1.name}/{m.player_b2.name}"
                if m.player_a1 == player or m.player_a2 == player
                else f"{m.player_a1.name}/{m.player_a2.name}"
            )
            print(f"{m.date.isoformat()} vs {opponents}: {rating:.1f}")
    else:
        cards = get_player_match_cards(clubs, club_id, user_id)
        for c in cards:
            delta = c["self_delta"]
            delta_str = f" ({delta:+.1f})" if delta is not None else ""
            print(
                f"{c['date'].isoformat()} {c['location'] or '-'} "
                f"{c['format'] or '-'} {c['self_score']}-{c['opponent_score']} vs "
                f"{c['opponent']}: {c['self_rating_after']:.1f}{delta_str}"
            )


def main():
    parser = argparse.ArgumentParser(description='Tennis Rating CLI')
    sub = parser.add_subparsers(dest='cmd')

    cclub = sub.add_parser('create_club')
    cclub.add_argument('user_id')
    cclub.add_argument('club_id')
    cclub.add_argument('name')
    cclub.add_argument('--logo')
    cclub.add_argument('--region')
    cclub.add_argument('--slogan')

    reg = sub.add_parser('register_user')
    reg.add_argument('user_id', nargs='?')
    reg.add_argument('name')
    reg.add_argument('password')
    reg.add_argument('--allow-create', action='store_true')

    login = sub.add_parser('login')
    login.add_argument('user_id')
    login.add_argument('password')

    join = sub.add_parser('request_join')
    join.add_argument('club_id')
    join.add_argument('user_id')
    join.add_argument('--singles', type=float)
    join.add_argument('--doubles', type=float)
    join.add_argument('--reason')

    approve = sub.add_parser('approve_member')
    approve.add_argument('club_id')
    approve.add_argument('approver_id')
    approve.add_argument('user_id')
    approve.add_argument('rating', type=float)
    approve.add_argument('--admin', action='store_true')

    aplayer = sub.add_parser('add_player')
    aplayer.add_argument('club_id')
    aplayer.add_argument('user_id')
    aplayer.add_argument('name')
    aplayer.add_argument('--age', type=int)
    aplayer.add_argument('--gender')
    aplayer.add_argument('--avatar')
    aplayer.add_argument('--birth')
    aplayer.add_argument('--handedness')
    aplayer.add_argument('--backhand')
    aplayer.add_argument('--region')

    pre = sub.add_parser('pre_rate')
    pre.add_argument('club_id')
    pre.add_argument('rater_id')
    pre.add_argument('target_id')
    pre.add_argument('rating', type=float)

    rmatch = sub.add_parser('record_match')
    rmatch.add_argument('club_id')
    rmatch.add_argument('user_a')
    rmatch.add_argument('user_b')
    rmatch.add_argument('score_a', type=int)
    rmatch.add_argument('score_b', type=int)
    rmatch.add_argument('--date', type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(), default=datetime.date.today())
    rmatch.add_argument('--location')
    rmatch.add_argument('--format', choices=FORMAT_WEIGHTS.keys())
    rmatch.add_argument('--weight', type=float)

    smatch = sub.add_parser('submit_match')
    smatch.add_argument('club_id')
    smatch.add_argument('initiator')
    smatch.add_argument('opponent')
    smatch.add_argument('score_i', type=int)
    smatch.add_argument('score_o', type=int)
    smatch.add_argument('--date', type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(), default=datetime.date.today())
    smatch.add_argument('--location')
    smatch.add_argument('--format', choices=FORMAT_WEIGHTS.keys())
    smatch.add_argument('--weight', type=float)

    cconfirm = sub.add_parser('confirm_match')
    cconfirm.add_argument('club_id')
    cconfirm.add_argument('index', type=int)
    cconfirm.add_argument('user_id')

    capprove = sub.add_parser('approve_match')
    capprove.add_argument('club_id')
    capprove.add_argument('index', type=int)
    capprove.add_argument('approver')

    rdouble = sub.add_parser('record_doubles')
    rdouble.add_argument('club_id')
    rdouble.add_argument('a1')
    rdouble.add_argument('a2')
    rdouble.add_argument('b1')
    rdouble.add_argument('b2')
    rdouble.add_argument('score_a', type=int)
    rdouble.add_argument('score_b', type=int)
    rdouble.add_argument('--date', type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(), default=datetime.date.today())
    rdouble.add_argument('--location')
    rdouble.add_argument('--format', choices=FORMAT_WEIGHTS.keys())
    rdouble.add_argument('--weight', type=float)

    board = sub.add_parser('leaderboard')
    board.add_argument('club_id', nargs='?')
    board.add_argument('--doubles', action='store_true')
    board.add_argument('--min-rating', type=float)
    board.add_argument('--max-rating', type=float)
    board.add_argument('--min-age', type=int)
    board.add_argument('--max-age', type=int)
    board.add_argument('--gender')

    hist = sub.add_parser('player_history')
    hist.add_argument('club_id')
    hist.add_argument('user_id')
    hist.add_argument('--doubles', action='store_true')

    args = parser.parse_args()
    global players
    clubs, players = load_data()
    users = load_users()

    if args.cmd == 'create_club':
        create_club(users, clubs, args.user_id, args.club_id, args.name, args.logo, args.region, args.slogan)
    elif args.cmd == 'register_user':
        register_user(users, args.user_id, args.name, args.password, allow_create=args.allow_create)
    elif args.cmd == 'login':
        if login_user(users, args.user_id, args.password):
            print('Login successful')
        else:
            print('Login failed')
        return
    elif args.cmd == 'request_join':
        request_join(
            clubs,
            users,
            args.club_id,
            args.user_id,
            singles_rating=args.singles,
            doubles_rating=args.doubles,
            reason=args.reason,
        )
    elif args.cmd == 'approve_member':
        approve_member(
            clubs,
            users,
            args.club_id,
            args.approver_id,
            args.user_id,
            args.rating,
            make_admin=args.admin,
        )
    elif args.cmd == 'add_player':
        add_player(
            clubs,
            args.club_id,
            args.user_id,
            args.name,
            age=args.age,
            gender=args.gender,
            avatar=args.avatar,
            birth=args.birth,
            handedness=args.handedness,
            backhand=args.backhand,
            region=args.region,
        )
    elif args.cmd == 'pre_rate':
        pre_rate(clubs, args.club_id, args.rater_id, args.target_id, args.rating)
    elif args.cmd == 'record_match':
        weight = args.weight
        if args.format:
            weight = format_weight_from_name(args.format)
        if weight is None:
            weight = format_weight_from_name("6_game")
        record_match(
            clubs,
            args.club_id,
            args.user_a,
            args.user_b,
            args.score_a,
            args.score_b,
            args.date,
            weight,
            location=args.location,
            format_name=args.format,
        )
    elif args.cmd == 'submit_match':
        weight = args.weight
        if args.format:
            weight = format_weight_from_name(args.format)
        if weight is None:
            weight = format_weight_from_name("6_game")
        submit_match(
            clubs,
            args.club_id,
            args.initiator,
            args.opponent,
            args.score_i,
            args.score_o,
            args.date,
            weight,
            location=args.location,
            format_name=args.format,
            users=users,
        )
    elif args.cmd == 'confirm_match':
        confirm_match(clubs, args.club_id, args.index, args.user_id)
    elif args.cmd == 'approve_match':
        approve_match(clubs, args.club_id, args.index, args.approver, users)
    elif args.cmd == 'record_doubles':
        weight = args.weight
        if args.format:
            weight = format_weight_from_name(args.format)
        if weight is None:
            weight = format_weight_from_name("6_game")
        record_doubles(
            clubs,
            args.club_id,
            args.a1,
            args.a2,
            args.b1,
            args.b2,
            args.score_a,
            args.score_b,
            args.date,
            weight,
            location=args.location,
            format_name=args.format,
        )
    elif args.cmd == 'leaderboard':
        leaderboard(
            clubs,
            args.club_id,
            args.doubles,
            min_rating=args.min_rating,
            max_rating=args.max_rating,
            min_age=args.min_age,
            max_age=args.max_age,
            gender=args.gender,
        )
        return
    elif args.cmd == 'player_history':
        player_history(clubs, args.club_id, args.user_id, args.doubles)
        return
    else:
        parser.print_help()
        return

    save_data(clubs)
    save_users(users)


if __name__ == '__main__':
    main()
