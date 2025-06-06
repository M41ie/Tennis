import pytest

from tennis.cli import (
    register_user,
    create_club,
    request_join,
    approve_member,
)
from tennis.models import MAX_CREATED_CLUBS, MAX_JOINED_CLUBS


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
    approve_member(clubs, users, "c1", "leader", "member", 1100.0)
    assert "member" in clubs["c1"].members
    assert len(users["member"].messages) == 1
    assert clubs["c1"].members["member"].singles_rating == 1100.0


def test_create_club_limit():
    users = {}
    clubs = {}
    register_user(users, "leader", "Leader", "pw", allow_create=True)
    create_club(users, clubs, "leader", "c1", "Club1", None, None)
    with pytest.raises(ValueError):
        create_club(users, clubs, "leader", "c2", "Club2", None, None)


def test_creator_is_member():
    users = {}
    clubs = {}
    register_user(users, "leader", "Leader", "pw", allow_create=True)
    create_club(users, clubs, "leader", "c1", "Club1", None, None)
    assert "leader" in clubs["c1"].members
    assert users["leader"].joined_clubs == 1


def test_join_club_limit():
    users = {}
    clubs = {}
    # register joiner
    register_user(users, "joiner", "Joiner", "pw")
    # create multiple clubs with different leaders
    for i in range(MAX_JOINED_CLUBS):
        lid = f"leader{i}"
        cid = f"c{i}"
        register_user(users, lid, f"L{i}", "pw", allow_create=True)
        create_club(users, clubs, lid, cid, f"Club{i}", None, None)
        request_join(clubs, users, cid, "joiner")
        approve_member(clubs, users, cid, lid, "joiner", 1000.0)

    # attempt to join one more club
    register_user(users, "extra_leader", "EL", "pw", allow_create=True)
    create_club(users, clubs, "extra_leader", "cx", "ClubX", None, None)
    request_join(clubs, users, "cx", "joiner")
    with pytest.raises(ValueError):
        approve_member(clubs, users, "cx", "extra_leader", "joiner", 1000.0)


def test_admin_limit():
    users = {}
    clubs = {}
    register_user(users, "leader", "Leader", "pw", allow_create=True)
    create_club(users, clubs, "leader", "c1", "Club1", None, None)

    # add three admins
    for i in range(3):
        uid = f"admin{i}"
        register_user(users, uid, f"A{i}", "pw")
        request_join(clubs, users, "c1", uid)
        approve_member(clubs, users, "c1", "leader", uid, 1000.0, make_admin=True)
        assert uid in clubs["c1"].admin_ids

    # fourth admin should fail
    register_user(users, "extra", "Extra", "pw")
    request_join(clubs, users, "c1", "extra")
    with pytest.raises(ValueError):
        approve_member(clubs, users, "c1", "leader", "extra", 1000.0, make_admin=True)
