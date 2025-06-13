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
    resp = client.get(f"/users/p1/messages?token={token_p1}")
    assert len(resp.json()) == 1
    resp = client.get(f"/users/p1/messages/unread_count?token={token_p1}")
    assert resp.json()["unread"] == 1
    resp = client.get(f"/users/p2/messages?token={token_p2}")
    assert len(resp.json()) == 1
    resp = client.get(f"/users/p2/messages/unread_count?token={token_p2}")
    assert resp.json()["unread"] == 1

    # verify persisted ratings
    loaded = storage.load_data()
    club = loaded["c1"]
    assert len(club.matches) == 1
    p1 = club.members["p1"]
    p2 = club.members["p2"]

    from tennis.models import Player, Match
    from tennis.rating import update_ratings, weighted_rating

    ref_p1 = Player("p1", "P1", singles_rating=1000.0)
    ref_p2 = Player("p2", "P2", singles_rating=1000.0)
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
            "partner": "p2",
            "opponent1": "p3",
            "opponent2": "p4",
            "score_initiator": 6,
            "score_opponent": 3,
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
            "partner": "p2",
            "opponent1": "p3",
            "opponent2": "p4",
            "score_initiator": 6,
            "score_opponent": 3,
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

    resp = client.get(f"/clubs/c1/pending_matches?token={tokens['p1']}")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 1
    rec = records[0]
    assert rec["index"] == 0
    assert rec["player_a"] == "p1"
    assert rec["player_b"] == "p2"
    assert rec["confirmed_a"] is True
    assert rec["confirmed_b"] is False


def test_pending_match_role_fields(tmp_path, monkeypatch):
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
            "token": tokens["p1"],
        },
    )

    rec = client.get(f"/clubs/c1/pending_matches?token={tokens['p1']}").json()[0]
    assert rec["display_status_text"] == "您已提交，等待对手确认"
    assert rec["can_confirm"] is False
    assert rec["can_decline"] is False
    assert rec["current_user_role_in_match"] == "submitter"

    rec = client.get(f"/clubs/c1/pending_matches?token={tokens['p2']}").json()[0]
    assert rec["display_status_text"] == "对手提交了比赛战绩，请确认"
    assert rec["can_confirm"] is True
    assert rec["can_decline"] is True
    assert rec["current_user_role_in_match"] == "opponent"

    client.post(
        "/clubs/c1/pending_matches/0/confirm",
        json={"user_id": "p2", "token": tokens["p2"]},
    )

    rec = client.get(f"/clubs/c1/pending_matches?token={tokens['leader']}").json()[0]
    assert rec["display_status_text"] == "双方已确认，请审核"
    assert rec["current_user_role_in_match"] == "admin"


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
            "partner": "p2",
            "opponent1": "p3",
            "opponent2": "p4",
            "score_initiator": 6,
            "score_opponent": 3,
            "date": "2023-01-02",
            "token": tokens["p1"],
        },
    )

    resp = client.get(f"/clubs/c1/pending_doubles?token={tokens['p1']}")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 1
    rec = records[0]
    assert rec["index"] == 0
    assert rec["a1"] == "p1"
    assert rec["a2"] == "p2"
    assert rec["b1"] == "p3"
    assert rec["b2"] == "p4"
    assert rec["confirmed_a"] is True
    assert rec["confirmed_b"] is False
    assert rec["display_status_text"] == "您已提交，等待对手确认"
    assert rec["can_confirm"] is False
    assert rec["can_decline"] is False

    resp = client.get(f"/clubs/c1/pending_doubles?token={tokens['p3']}")
    assert resp.status_code == 200
    rec = resp.json()[0]
    assert rec["display_status_text"] == "对手提交了比赛战绩，请确认"
    assert rec["can_confirm"] is True
    assert rec["can_decline"] is True


def test_doubles_opponent_confirmed_text(tmp_path, monkeypatch):
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
            "partner": "p2",
            "opponent1": "p3",
            "opponent2": "p4",
            "score_initiator": 6,
            "score_opponent": 3,
            "token": tokens["p1"],
        },
    )

    client.post(
        "/clubs/c1/pending_doubles/0/confirm",
        json={"user_id": "p3", "token": tokens["p3"]},
    )

    rec = client.get(f"/clubs/c1/pending_doubles?token={tokens['p3']}").json()[0]
    assert rec["display_status_text"] == "您的队友已确认，等待管理员审核"
    assert rec["can_confirm"] is False
    assert rec["can_decline"] is False

    rec = client.get(f"/clubs/c1/pending_doubles?token={tokens['p4']}").json()[0]
    assert rec["display_status_text"] == "您的队友已确认，等待管理员审核"

    rec = client.get(f"/clubs/c1/pending_doubles?token={tokens['p1']}").json()[0]
    assert rec["display_status_text"] == "对手已确认，等待管理员审核"


def test_admin_submitter_review_text(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid in ("leader", "p2"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    tokens = {u: client.post("/login", json={"user_id": u, "password": "pw"}).json()["token"] for u in ("leader", "p2")}

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": tokens["leader"]},
    )
    for pid in ("leader", "p2"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tokens[pid]},
        )

    client.post(
        "/clubs/c1/pending_matches",
        json={
            "initiator": "leader",
            "opponent": "p2",
            "score_initiator": 6,
            "score_opponent": 4,
            "token": tokens["leader"],
        },
    )

    rec = client.get(f"/clubs/c1/pending_matches?token={tokens['leader']}").json()[0]
    assert rec["display_status_text"] == "您已提交，等待对手确认"

    client.post(
        "/clubs/c1/pending_matches/0/confirm",
        json={"user_id": "p2", "token": tokens["p2"]},
    )

    rec = client.get(f"/clubs/c1/pending_matches?token={tokens['leader']}").json()[0]
    assert rec["display_status_text"] == "双方已确认，请审核"


def test_admin_opponent_review_text_doubles(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid in ("leader", "p1", "p2", "p3"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    tokens = {u: client.post("/login", json={"user_id": u, "password": "pw"}).json()["token"] for u in ("leader", "p1", "p2", "p3")}

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": tokens["leader"]},
    )
    for pid in ("leader", "p1", "p2", "p3"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tokens[pid]},
        )

    client.post(
        "/clubs/c1/pending_doubles",
        json={
            "initiator": "p1",
            "partner": "p2",
            "opponent1": "leader",
            "opponent2": "p3",
            "score_initiator": 6,
            "score_opponent": 4,
            "token": tokens["p1"],
        },
    )

    rec = client.get(f"/clubs/c1/pending_doubles?token={tokens['leader']}").json()[0]
    assert rec["display_status_text"] == "对手提交了比赛战绩，请确认"

    client.post(
        "/clubs/c1/pending_doubles/0/confirm",
        json={"user_id": "leader", "token": tokens["leader"]},
    )

    rec = client.get(f"/clubs/c1/pending_doubles?token={tokens['leader']}").json()[0]
    assert rec["display_status_text"] == "双方已确认，请审核"


def test_reject_pending_match(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid in ("leader", "p1", "p2"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    tokens = {pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"] for pid in ("leader", "p1", "p2")}

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
            "token": tokens["p1"],
        },
    )

    # status as seen by initiator
    resp = client.get(f"/clubs/c1/pending_matches?token={tokens['p1']}")
    assert resp.status_code == 200
    rec = resp.json()[0]
    assert rec["display_status_text"] == "您已提交，等待对手确认"
    assert rec["can_confirm"] is False
    assert rec["can_decline"] is False

    # status as seen by opponent
    resp = client.get(f"/clubs/c1/pending_matches?token={tokens['p2']}")
    assert resp.status_code == 200
    rec = resp.json()[0]
    assert rec["display_status_text"] == "对手提交了比赛战绩，请确认"
    assert rec["can_confirm"] is True
    assert rec["can_decline"] is True

    resp = client.post(
        "/clubs/c1/pending_matches/0/reject",
        json={"user_id": "p2", "token": tokens["p2"]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    resp = client.get(f"/clubs/c1/pending_matches?token={tokens['p1']}")
    assert resp.status_code == 200
    rec = resp.json()[0]
    assert "对手已拒绝" in rec["display_status_text"]


def test_reject_pending_doubles(tmp_path, monkeypatch):
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

    tokens = {pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"] for pid in ("leader", "p1", "p2", "p3", "p4")}

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
            "partner": "p2",
            "opponent1": "p3",
            "opponent2": "p4",
            "score_initiator": 6,
            "score_opponent": 3,
            "token": tokens["p1"],
        },
    )

    resp = client.post(
        "/clubs/c1/pending_doubles/0/reject",
        json={"user_id": "p3", "token": tokens["p3"]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    resp = client.get(f"/clubs/c1/pending_doubles?token={tokens['p1']}")
    assert resp.status_code == 200
    rec = resp.json()[0]
    assert "对手已拒绝" in rec["display_status_text"]


def test_veto_pending_match(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid in ("leader", "p1", "p2"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    tokens = {pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"] for pid in ("leader", "p1", "p2")}

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
        json={"initiator": "p1", "opponent": "p2", "score_initiator": 6, "score_opponent": 4, "token": tokens["p1"]},
    )

    resp = client.post(
        "/clubs/c1/pending_matches/0/veto",
        json={"approver": "leader", "token": tokens["leader"]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "vetoed"

    data = storage.load_data()
    assert data["c1"].pending_matches
    assert data["c1"].pending_matches[0].status == "vetoed"
    users = storage.load_users()
    assert any("vetoed" in m.text for m in users["p1"].messages)


def test_veto_pending_doubles(tmp_path, monkeypatch):
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

    tokens = {pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"] for pid in ("leader", "p1", "p2", "p3", "p4")}

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
            "partner": "p2",
            "opponent1": "p3",
            "opponent2": "p4",
            "score_initiator": 6,
            "score_opponent": 3,
            "token": tokens["p1"],
        },
    )

    resp = client.post(
        "/clubs/c1/pending_doubles/0/veto",
        json={"approver": "leader", "token": tokens["leader"]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "vetoed"

    data = storage.load_data()
    assert data["c1"].pending_matches
    assert data["c1"].pending_matches[0].status == "vetoed"
    users = storage.load_users()
    assert any("vetoed" in m.text for m in users["p1"].messages)


def test_pending_visibility_rules(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    # register users and login
    for uid in ("leader", "p1", "p2", "p3"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    tokens = {u: client.post("/login", json={"user_id": u, "password": "pw"}).json()["token"] for u in ("leader", "p1", "p2", "p3")}

    # create club and add players
    client.post("/clubs", json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": tokens["leader"]})
    for pid in ("p1", "p2", "p3"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tokens[pid]},
        )

    # submit pending match p1 vs p2
    client.post(
        "/clubs/c1/pending_matches",
        json={
            "initiator": "p1",
            "opponent": "p2",
            "score_initiator": 6,
            "score_opponent": 4,
            "token": tokens["p1"],
        },
    )

    # Only participants see the unconfirmed match
    assert len(client.get(f"/clubs/c1/pending_matches?token={tokens['p1']}").json()) == 1
    assert len(client.get(f"/clubs/c1/pending_matches?token={tokens['p2']}").json()) == 1
    assert client.get(f"/clubs/c1/pending_matches?token={tokens['p3']}").json() == []
    assert client.get(f"/clubs/c1/pending_matches?token={tokens['leader']}").json() == []

    # opponent confirms; now both participants confirmed
    client.post(
        "/clubs/c1/pending_matches/0/confirm",
        json={"user_id": "p2", "token": tokens["p2"]},
    )

    # admin can now see the record
    assert len(client.get(f"/clubs/c1/pending_matches?token={tokens['leader']}").json()) == 1
    # non-participant still cannot
    assert client.get(f"/clubs/c1/pending_matches?token={tokens['p3']}").json() == []


def test_pending_match_includes_ratings(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid in ("leader", "p1", "p2"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    tokens = {pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"] for pid in ("leader", "p1", "p2")}

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
        json={"initiator": "p1", "opponent": "p2", "score_initiator": 6, "score_opponent": 4, "token": tokens["p1"]},
    )

    resp = client.get(f"/clubs/c1/pending_matches?token={tokens['p1']}")
    rec = resp.json()[0]
    assert "rating_a_before" in rec and "rating_b_before" in rec
    assert rec["rating_a_before"] is None



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


def test_check_token_endpoint(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post("/users", json={"user_id": "u", "name": "U", "password": "pw", "allow_create": True})
    token = client.post("/login", json={"user_id": "u", "password": "pw"}).json()["token"]

    resp = client.post("/check_token", json={"token": token})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "u"

    resp = client.post("/check_token", json={"token": "bad"})
    assert resp.status_code == 401


def test_doubles_leaderboard_api(tmp_path, monkeypatch):
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

    # adjust doubles ratings for predictable ordering
    api.clubs["c1"].members["p1"].doubles_rating = 1200
    api.clubs["c1"].members["p2"].doubles_rating = 1100
    api.clubs["c1"].members["p3"].doubles_rating = 1300
    api.clubs["c1"].members["p4"].doubles_rating = 1000

    resp = client.get("/clubs/c1/players?doubles=true")
    assert resp.status_code == 200
    board = resp.json()
    for p in board:
        assert p["weighted_singles_matches"] == 0.0
        assert p["weighted_doubles_matches"] == 0.0
    ids = [p["user_id"] for p in board]
    assert ids == ["p3", "p1", "p2", "p4", "leader"]


def test_token_persistence(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post(
        "/users",
        json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True},
    )
    client.post("/users", json={"user_id": "p1", "name": "P1", "password": "pw"})

    token = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token},
    )

    # reload module to simulate restart
    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    resp = client.post(
        "/clubs/c1/players",
        json={"user_id": "p1", "name": "P1", "token": token},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_players_filters(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid in ("leader", "p1", "p2", "p3"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    tokens = {
        pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"]
        for pid in ("leader", "p1", "p2", "p3")
    }

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": tokens["leader"]},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p1", "name": "P1", "age": 20, "gender": "M", "token": tokens["p1"]},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p2", "name": "P2", "age": 25, "gender": "F", "token": tokens["p2"]},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p3", "name": "P3", "age": 22, "gender": "M", "token": tokens["p3"]},
    )

    api.clubs["c1"].members["p1"].singles_rating = 1200
    api.clubs["c1"].members["p2"].singles_rating = 1100
    api.clubs["c1"].members["p3"].singles_rating = 1300

    resp = client.get("/clubs/c1/players?min_rating=1100&max_age=25&gender=M")
    assert resp.status_code == 200
    data = resp.json()
    for p in data:
        assert p["weighted_singles_matches"] == 0.0
        assert p["weighted_doubles_matches"] == 0.0
    ids = [p["user_id"] for p in data]
    assert ids == ["p3", "p1"]


def test_list_all_players_multi_club(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid in ("leader1", "leader2", "p1", "p2", "p3", "p4"):
        allow = uid.startswith("leader")
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    tokens = {
        pid: client.post("/login", json={"user_id": pid, "password": "pw"}).json()["token"]
        for pid in ("leader1", "leader2", "p1", "p2", "p3", "p4")
    }

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader1", "token": tokens["leader1"]},
    )
    client.post(
        "/clubs",
        json={"club_id": "c2", "name": "C2", "user_id": "leader2", "token": tokens["leader2"]},
    )

    client.post(
        "/clubs/c1/players",
        json={"user_id": "p1", "name": "P1", "token": tokens["p1"]},
    )
    client.post(
        "/clubs/c2/players",
        json={"user_id": "p2", "name": "P2", "token": tokens["p2"]},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p3", "name": "P3", "token": tokens["p3"]},
    )
    client.post(
        "/clubs/c2/players",
        json={"user_id": "p4", "name": "P4", "token": tokens["p4"]},
    )

    api.clubs["c1"].members["p1"].singles_rating = 1200
    api.clubs["c2"].members["p2"].singles_rating = 1100
    api.clubs["c1"].members["p3"].singles_rating = 1300
    api.clubs["c2"].members["p4"].singles_rating = 1250

    resp = client.get("/players?club=c1,c2&min_rating=1200")
    assert resp.status_code == 200
    board = resp.json()
    for p in board:
        assert p["weighted_singles_matches"] == 0.0
        assert p["weighted_doubles_matches"] == 0.0
    ids = [p["user_id"] for p in board]
    assert ids == ["p3", "p4", "p1"]


def test_update_player_api(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    # register and login
    client.post(
        "/users",
        json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True},
    )
    client.post(
        "/users",
        json={"user_id": "p1", "name": "P1", "password": "pw"},
    )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_p1 = client.post("/login", json={"user_id": "p1", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p1", "name": "P1", "token": token_p1},
    )

    resp = client.patch(
        "/clubs/c1/players/p1",
        json={
            "user_id": "p1",
            "token": token_p1,
            "name": "New",
            "age": 30,
            "gender": "M",
            "avatar": "img.png",
            "birth": "1990-01-01",
            "handedness": "right",
            "backhand": "double",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    data = storage.load_data()
    p1 = data["c1"].members["p1"]
    assert p1.name == "New"
    assert p1.age == 30
    assert p1.gender == "M"
    assert p1.avatar == "img.png"
    assert p1.birth == "1990-01-01"
    assert p1.handedness == "right"
    assert p1.backhand == "double"


def test_update_global_player_api(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post(
        "/users",
        json={"user_id": "p1", "name": "P1", "password": "pw"},
    )

    token = client.post("/login", json={"user_id": "p1", "password": "pw"}).json()["token"]

    resp = client.patch(
        "/players/p1",
        json={
            "user_id": "p1",
            "token": token,
            "name": "New",
            "gender": "M",
            "region": "Beijing",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    storage.load_data()
    p1 = storage.players["p1"]
    assert p1.name == "New"
    assert p1.gender == "M"
    assert p1.region == "Beijing"


def test_login_by_name(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post(
        "/users",
        json={"user_id": "u1", "name": "Alice", "password": "pw"},
    )

    resp = client.post("/login", json={"user_id": "Alice", "password": "pw"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    token = data["token"]

    check = client.post("/check_token", json={"token": token})
    assert check.json()["user_id"] == "u1"


def test_remove_member_api(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    # register users
    client.post(
        "/users",
        json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True},
    )
    client.post(
        "/users",
        json={"user_id": "member", "name": "M", "password": "pw"},
    )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_member = client.post("/login", json={"user_id": "member", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )

    # join and approve member
    client.post(
        "/clubs/c1/join",
        json={
            "user_id": "member",
            "token": token_member,
            "singles_rating": 1000.0,
            "doubles_rating": 1000.0,
        },
    )
    client.post(
        "/clubs/c1/approve",
        json={
            "approver_id": "leader",
            "user_id": "member",
            "rating": 1200.0,
            "token": token_leader,
        },
    )

    data = storage.load_data()
    assert data["c1"].members.get("member")
    assert data["c1"].members["member"].singles_rating == 1200.0
    assert storage.load_users()["member"].joined_clubs == 1

    resp = client.request(
        "DELETE",
        "/clubs/c1/members/member",
        json={"remover_id": "leader", "token": token_leader, "ban": True},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    data = storage.load_data()
    users = storage.load_users()
    club = data["c1"]
    assert "member" not in club.members
    assert "member" in club.banned_ids
    assert users["member"].joined_clubs == 0


def test_appointment_flow(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid in ("leader", "p1"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_p1 = client.post("/login", json={"user_id": "p1", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p1", "name": "P1", "token": token_p1},
    )

    resp = client.post(
        "/clubs/c1/appointments",
        json={"user_id": "leader", "date": "2023-05-01", "location": "Court", "token": token_leader},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp = client.get("/clubs/c1/appointments")
    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) == 1
    assert apps[0]["location"] == "Court"

    resp = client.post(
        "/clubs/c1/appointments/0/signup",
        json={"user_id": "p1", "token": token_p1},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/clubs/c1/appointments/0/cancel",
        json={"user_id": "p1", "token": token_p1},
    )
    assert resp.status_code == 200

    data = storage.load_data()
    club = data["c1"]
    assert len(club.appointments) == 1
    assert not club.appointments[0].signups


def test_player_recent_api(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    for uid in ("leader", "p1", "p2"):
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_p1 = client.post("/login", json={"user_id": "p1", "password": "pw"}).json()["token"]
    token_p2 = client.post("/login", json={"user_id": "p2", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p1", "name": "P1", "token": token_p1},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p2", "name": "P2", "token": token_p2},
    )

    client.post(
        "/clubs/c1/matches",
        json={
            "user_id": "p1",
            "user_a": "p1",
            "user_b": "p2",
            "score_a": 6,
            "score_b": 4,
            "date": "2023-01-01",
            "token": token_p1,
        },
    )

    resp = client.get("/clubs/c1/players/p1?recent=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "recent_records" in data
    assert len(data["recent_records"]) == 1
    rec = data["recent_records"][0]
    assert rec["self_score"] == 6
    assert rec["opponent_score"] == 4


def test_get_user_info_api(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    # create user and club
    client.post("/users", json={"user_id": "u1", "name": "U1", "password": "pw"})
    client.post("/users", json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True})
    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_u1 = client.post("/login", json={"user_id": "u1", "password": "pw"}).json()["token"]
    client.post("/clubs", json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader})
    client.post(
        "/clubs/c1/join",
        json={
            "user_id": "u1",
            "token": token_u1,
            "singles_rating": 1000.0,
            "doubles_rating": 1000.0,
        },
    )
    client.post(
        "/clubs/c1/approve",
        json={
            "approver_id": "leader",
            "user_id": "u1",
            "rating": 1300.0,
            "token": token_leader,
        },
    )
    assert storage.load_data()["c1"].members["u1"].singles_rating == 1300.0

    resp = client.get("/users/u1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "u1"
    assert data["joined_clubs"] == ["c1"]
    # user u1 has no create permissions since the limit is 0
    assert data["can_create_club"] is False
    resp = client.get(f"/users/u1/messages?token={token_u1}")
    assert resp.status_code == 200
    msgs = resp.json()
    assert len(msgs) == 1
    resp = client.get(f"/users/u1/messages/unread_count?token={token_u1}")
    assert resp.json()["unread"] == 1


def test_join_rejection_flow(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post("/users", json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True})
    client.post("/users", json={"user_id": "m1", "name": "M", "password": "pw"})

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_m1 = client.post("/login", json={"user_id": "m1", "password": "pw"}).json()["token"]

    client.post("/clubs", json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader})

    client.post(
        "/clubs/c1/join",
        json={"user_id": "m1", "token": token_m1, "singles_rating": 1000.0, "doubles_rating": 1000.0},
    )

    client.post(
        "/clubs/c1/reject",
        json={"approver_id": "leader", "user_id": "m1", "reason": "no", "token": token_leader},
    )

    info = client.get("/clubs/c1").json()
    assert info["rejected_members"]["m1"] == "no"
    assert all(p["user_id"] != "m1" for p in info["pending_members"])

    resp = client.get(f"/users/m1/messages?token={token_m1}")
    assert any("rejected" in m["text"] for m in resp.json())

    client.post(
        "/clubs/c1/clear_rejection",
        json={"user_id": "m1", "token": token_m1},
    )
    info = client.get("/clubs/c1").json()
    assert "m1" not in info["rejected_members"]

    client.post(
        "/clubs/c1/join",
        json={"user_id": "m1", "token": token_m1, "singles_rating": 1000.0, "doubles_rating": 1000.0},
    )
    info = client.get("/clubs/c1").json()
    assert any(p["user_id"] == "m1" for p in info["pending_members"])


def test_dissolve_club(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post(
        "/users",
        json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True},
    )
    client.post(
        "/users",
        json={"user_id": "m1", "name": "M", "password": "pw"},
    )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_m1 = client.post("/login", json={"user_id": "m1", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    client.post(
        "/clubs/c1/join",
        json={"user_id": "m1", "token": token_m1},
    )
    client.post(
        "/clubs/c1/approve",
        json={"approver_id": "leader", "user_id": "m1", "rating": 1000.0, "token": token_leader},
    )

    resp = client.request(
        "DELETE",
        "/clubs/c1",
        json={"user_id": "leader", "token": token_leader},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    data = storage.load_data()
    users = storage.load_users()
    assert "c1" not in data
    assert users["leader"].created_clubs == 0
    assert users["leader"].joined_clubs == 0
    assert users["m1"].joined_clubs == 0
