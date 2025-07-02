import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def setup(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    return TestClient(api.app)


def test_sys_stats_and_clubs(tmp_path, monkeypatch):
    client = setup(tmp_path, monkeypatch)

    # create users
    client.post(
        "/users",
        json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True},
    )
    client.post("/users", json={"user_id": "u1", "name": "U1", "password": "pw"})

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_u1 = client.post("/login", json={"user_id": "u1", "password": "pw"}).json()["token"]

    # create club and pending member
    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    client.post(
        "/clubs/c1/join",
        json={
            "user_id": "u1",
            "token": token_u1,
            "singles_rating": 3.0,
            "doubles_rating": 3.0,
        },
    )

    stats = client.get("/sys/stats").json()
    assert stats["total_users"] == 2
    assert stats["total_clubs"] == 1
    assert stats["pending_items"] == 1

    clubs = client.get("/sys/clubs").json()
    assert isinstance(clubs, list) and clubs
    assert clubs[0]["club_id"] == "c1"
    assert clubs[0]["pending_members"] == 1


def test_sys_stats_include_dissolved(tmp_path, monkeypatch):
    client = setup(tmp_path, monkeypatch)

    for uid, allow in [("leader", True), ("p1", False), ("p2", False)]:
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
    for pid, token in [("p1", token_p1), ("p2", token_p2)]:
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": token_leader},
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

    client.request(
        "DELETE",
        "/clubs/c1",
        json={"user_id": "leader", "token": token_leader},
    )

    stats = client.get("/sys/stats").json()
    assert stats["total_matches"] == 1
