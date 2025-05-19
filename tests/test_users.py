import pytest

from tennis.cli import (
    register_user,
    create_club,
    request_join,
    approve_member,
)


def test_create_club_permission():
    users = {}
    clubs = {}
    register_user(users, "u1", "User1", "pw")
    with pytest.raises(ValueError):
        create_club(users, clubs, "u1", "c1", "Club1", None, None)


def test_join_and_approve():
    users = {}
    clubs = {}
    register_user(users, "leader", "Leader", "pw", allow_create=True)
    register_user(users, "member", "Member", "pw")
    create_club(users, clubs, "leader", "c1", "Club1", None, None)
    request_join(clubs, users, "c1", "member")
    assert "member" in clubs["c1"].pending_members
    approve_member(clubs, users, "c1", "leader", "member")
    assert "member" in clubs["c1"].members
