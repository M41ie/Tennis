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
    for pid, token in (("p1", token_p1), ("p2", token_p2)):
        resp = client.post(
            f"/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": token},
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


def test_prerate_api(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid, allow in [("leader", True), ("r1", False), ("r2", False)]:
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_r1 = client.post("/login", json={"user_id": "r1", "password": "pw"}).json()["token"]
    token_r2 = client.post("/login", json={"user_id": "r2", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    for pid, tok in (("r1", token_r1), ("r2", token_r2)):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tok},
        )

    resp = client.post(
        "/clubs/c1/prerate",
        json={"rater_id": "r1", "target_id": "r2", "rating": 1200, "token": token_r1},
    )
    assert resp.status_code == 200

    data = storage.load_data()
    assert data["c1"].members["r2"].pre_ratings["r1"] == 1200

    resp = client.post(
        "/clubs/c1/prerate",
        json={"rater_id": "r1", "target_id": "x", "rating": 1000, "token": token_r1},
    )
    assert resp.status_code == 400


def test_doubles_match_flow(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    # register users
    for uid in ("leader", "p1", "p2", "p3", "p4"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    tokens = {
        pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"]
        for pid in ("p1", "p2", "p3", "p4")
    }

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    for pid in ("p1", "p2", "p3", "p4"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tokens[pid]},
        )

    resp = client.post(
        "/clubs/c1/pending_doubles",
        json={
            "initiator": "p1",
            "a1": "p1",
            "a2": "p2",
            "b1": "p3",
            "b2": "p4",
            "score_a": 6,
            "score_b": 3,
            "date": "2023-01-02",
            "token": tokens["p1"],
        },
    )
    assert resp.status_code == 200

    resp = client.post(
        "/clubs/c1/pending_doubles/0/confirm",
        json={"user_id": "p3", "token": tokens["p3"]},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/clubs/c1/pending_doubles/0/approve",
        json={"approver": "leader", "token": token_leader},
    )
    assert resp.status_code == 200

    data = storage.load_data()
    club = data["c1"]
    assert len(club.matches) == 1


def test_doubles_records_api(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    # register users
    for uid in ("leader", "p1", "p2", "p3", "p4"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    tokens = {
        pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"]
        for pid in ("p1", "p2", "p3", "p4")
    }

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    for pid in ("p1", "p2", "p3", "p4"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tokens[pid]},
        )

    client.post(
        "/clubs/c1/pending_doubles",
        json={
            "initiator": "p1",
            "a1": "p1",
            "a2": "p2",
            "b1": "p3",
            "b2": "p4",
            "score_a": 6,
            "score_b": 3,
            "date": "2023-01-02",
            "token": tokens["p1"],
        },
    )

    client.post(
        "/clubs/c1/pending_doubles/0/confirm",
        json={"user_id": "p3", "token": tokens["p3"]},
    )

    client.post(
        "/clubs/c1/pending_doubles/0/approve",
        json={"approver": "leader", "token": token_leader},
    )

    resp = client.get("/clubs/c1/players/p1/doubles_records")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 1
    rec = records[0]
    assert rec["self_score"] == 6
    assert rec["opponent_score"] == 3
    assert rec["partner"] == "P2"
    assert rec["opponents"] == "P3/P4"


def test_pending_match_query(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid, allow in [("leader", True), ("p1", False), ("p2", False)]:
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    tokens = {
        pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"]
        for pid in ("leader", "p1", "p2")
    }

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": tokens["leader"]},
    )
    for pid in ("p1", "p2"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tokens[pid]},
        )

    client.post(
        "/clubs/c1/pending_matches",
        json={
            "initiator": "p1",
            "opponent": "p2",
            "score_initiator": 6,
            "score_opponent": 4,
            "date": "2023-01-01",
            "token": tokens["p1"],
        },
    )

    resp = client.get("/clubs/c1/pending_matches")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 1
    rec = records[0]
    assert rec["index"] == 0
    assert rec["player_a"] == "p1"
    assert rec["player_b"] == "p2"


def test_pending_doubles_query(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid in ("leader", "p1", "p2", "p3", "p4"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    tokens = {
        pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"]
        for pid in ("leader", "p1", "p2", "p3", "p4")
    }

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": tokens["leader"]},
    )
    for pid in ("p1", "p2", "p3", "p4"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tokens[pid]},
        )

    client.post(
        "/clubs/c1/pending_doubles",
        json={
            "initiator": "p1",
            "a1": "p1",
            "a2": "p2",
            "b1": "p3",
            "b2": "p4",
            "score_a": 6,
            "score_b": 3,
            "date": "2023-01-02",
            "token": tokens["p1"],
        },
    )

    resp = client.get("/clubs/c1/pending_doubles")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 1
    rec = records[0]
    assert rec["index"] == 0
    assert rec["a1"] == "p1"
    assert rec["a2"] == "p2"
    assert rec["b1"] == "p3"
    assert rec["b2"] == "p4"


def test_token_logout_and_expiry(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post("/users", json={"user_id": "u", "name": "U", "password": "pw", "allow_create": True})
    token = client.post("/login", json={"user_id": "u", "password": "pw"}).json()["token"]

    client.post("/logout", json={"token": token})
    resp = client.post("/clubs", json={"club_id": "c", "name": "C", "user_id": "u", "token": token})
    assert resp.status_code == 401

    token2 = client.post("/login", json={"user_id": "u", "password": "pw"}).json()["token"]
    api.tokens[token2] = (api.tokens[token2][0], datetime.datetime.utcnow() - datetime.timedelta(days=2))
    resp = client.post("/clubs", json={"club_id": "c", "name": "C", "user_id": "u", "token": token2})
    assert resp.status_code == 401
