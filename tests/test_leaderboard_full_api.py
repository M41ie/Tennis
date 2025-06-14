import importlib
import tennis.storage as storage
from fastapi.testclient import TestClient
import tennis.services.state as state


def setup_db(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    return api, TestClient(api.app)


def test_leaderboard_full(tmp_path, monkeypatch):
    api, client = setup_db(tmp_path, monkeypatch)

    # register users
    for uid, allow in (("leader", True), ("p1", False)):
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

    api.clubs["c1"].members["p1"].singles_rating = 1200

    resp = client.get("/leaderboard_full?club=c1&user_id=p1")
    assert resp.status_code == 200
    data = resp.json()
    assert any(c["club_id"] == "c1" for c in data.get("clubs", []))
    assert data.get("joined_clubs") == ["c1"]
    assert data.get("players")[0]["user_id"] == "p1"
