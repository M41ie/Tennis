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
