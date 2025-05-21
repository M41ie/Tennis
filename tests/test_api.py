import importlib
import datetime
from fastapi.testclient import TestClient
import pytest
import tennis.storage as storage


def test_api_match_flow(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    # register leader user and players
    resp = client.post(
        "/users",
        json={"user_id": "leader", "name": "Leader", "password": "pw", "allow_create": True},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    for pid in ("p1", "p2"):
        resp = client.post(
            "/users",
            json={"user_id": pid, "name": pid.upper(), "password": "pw"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    # login users
    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_p1 = client.post("/login", json={"user_id": "p1", "password": "pw"}).json()["token"]
    token_p2 = client.post("/login", json={"user_id": "p2", "password": "pw"}).json()["token"]

    # create club
    resp = client.post(
        "/clubs",
        json={"club_id": "c1", "name": "Club1", "user_id": "leader", "token": token_leader},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # add players
    for pid in ("p1", "p2"):
        resp = client.post(
            f"/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper()},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    # submit pending match
    resp = client.post(
        "/clubs/c1/pending_matches",
        json={
            "initiator": "p1",
            "opponent": "p2",
            "score_initiator": 6,
            "score_opponent": 4,
            "date": "2023-01-01",
            "token": token_p1,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

    # confirm by opponent
    resp = client.post(
        "/clubs/c1/pending_matches/0/confirm",
        json={"user_id": "p2", "token": token_p2},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # approve by leader
    resp = client.post(
        "/clubs/c1/pending_matches/0/approve",
        json={"approver": "leader", "token": token_leader},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # verify persisted ratings
    loaded = storage.load_data()
    club = loaded["c1"]
    assert len(club.matches) == 1
    p1 = club.members["p1"]
    p2 = club.members["p2"]

    from tennis.models import Player, Match
    from tennis.rating import update_ratings, weighted_rating

    ref_p1 = Player("p1", "P1")
    ref_p2 = Player("p2", "P2")
    match = Match(
        date=datetime.date(2023, 1, 1),
        player_a=ref_p1,
        player_b=ref_p2,
        score_a=6,
        score_b=4,
    )
    update_ratings(match)
    expected_p1 = weighted_rating(ref_p1, match.date)
    expected_p2 = weighted_rating(ref_p2, match.date)

    assert p1.singles_rating == pytest.approx(expected_p1)
    assert p2.singles_rating == pytest.approx(expected_p2)


def test_invalid_token(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post("/users", json={"user_id": "u1", "name": "U1", "password": "pw", "allow_create": True})
    token = client.post("/login", json={"user_id": "u1", "password": "pw"}).json()["token"]

    # wrong token should fail
    resp = client.post(
        "/clubs",
        json={"club_id": "c1", "name": "Club", "user_id": "u1", "token": "bad"},
    )
    assert resp.status_code == 401

    # correct token succeeds
    resp = client.post(
        "/clubs",
        json={"club_id": "c1", "name": "Club", "user_id": "u1", "token": token},
    )
    assert resp.status_code == 200
