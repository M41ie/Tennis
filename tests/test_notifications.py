import datetime
import datetime
from tennis.cli import (
    register_user,
    create_club,
    request_join,
    submit_match,
    submit_doubles,
    confirm_match,
    confirm_doubles,
)
from tennis.models import Player


def test_request_join_notifies_staff():
    users = {}
    clubs = {}
    register_user(users, "leader", "Leader", "pw", allow_create=True)
    register_user(users, "admin", "Admin", "pw")
    register_user(users, "joiner", "Joiner", "pw")
    create_club(users, clubs, "leader", "c1", "C1", None, None)
    club = clubs["c1"]
    club.admin_ids.add("admin")

    request_join(clubs, users, "c1", "joiner")

    assert len(users["leader"].messages) == 1
    assert "joiner" in users["leader"].messages[0].text
    assert len(users["admin"].messages) == 1
    assert "joiner" in users["admin"].messages[0].text


def test_submit_match_and_doubles_notify_staff():
    users = {}
    clubs = {}
    register_user(users, "leader", "Leader", "pw", allow_create=True)
    register_user(users, "admin", "Admin", "pw")
    register_user(users, "p1", "P1", "pw")
    register_user(users, "p2", "P2", "pw")
    register_user(users, "p3", "P3", "pw")
    register_user(users, "p4", "P4", "pw")
    create_club(users, clubs, "leader", "c1", "C1", None, None)
    club = clubs["c1"]
    club.admin_ids.add("admin")
    for pid in ("p1", "p2", "p3", "p4"):
        club.members[pid] = Player(pid, pid.upper())

    today = datetime.date.today()
    submit_match(
        clubs,
        "c1",
        "p1",
        "p2",
        6,
        4,
        today,
        1.0,
        users=users,
    )
    # no notifications until opponent confirms
    assert not users["leader"].messages
    assert not users["admin"].messages
    confirm_match(clubs, "c1", 0, "p2", users)
    assert any("Match pending approval" in m.text for m in users["leader"].messages)
    assert any("Match pending approval" in m.text for m in users["admin"].messages)

    submit_doubles(
        clubs,
        "c1",
        "p1",
        "p2",
        "p3",
        "p4",
        6,
        3,
        today,
        1.0,
        users=users,
    )
    # still only previous notifications
    leader_msgs_before = len(users["leader"].messages)
    admin_msgs_before = len(users["admin"].messages)
    assert leader_msgs_before == 2  # from singles confirmation (leader/admin)
    assert admin_msgs_before == 2
    confirm_doubles(clubs, "c1", 1, "p3", users)
    assert any("Doubles match pending approval" in m.text for m in users["leader"].messages[leader_msgs_before:])
    assert any("Doubles match pending approval" in m.text for m in users["admin"].messages[admin_msgs_before:])

