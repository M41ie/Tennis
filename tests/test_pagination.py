import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def setup(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    return api, TestClient(api.app)


def test_sys_users_pagination(tmp_path, monkeypatch):
    api, client = setup(tmp_path, monkeypatch)
    for i in range(3):
        client.post("/users", json={"user_id": f"u{i}", "name": f"U{i}", "password": "pw"})
    resp = client.get("/sys/users?limit=1&offset=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == "u1"


def test_sys_clubs_pagination(tmp_path, monkeypatch):
    api, client = setup(tmp_path, monkeypatch)
    tokens = {}
    for i in range(3):
        uid = f"leader{i}"
        client.post("/users", json={"user_id": uid, "name": uid, "password": "pw", "allow_create": True})
        tokens[uid] = client.post("/login", json={"user_id": uid, "password": "pw"}).json()["token"]
        client.post("/clubs", json={"club_id": f"c{i}", "name": f"C{i}", "user_id": uid, "token": tokens[uid]})
    resp = client.get("/sys/clubs?limit=2&offset=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["club_id"] == "c1"


def test_leaderboard_pagination(tmp_path, monkeypatch):
    api, client = setup(tmp_path, monkeypatch)
    client.post("/users", json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True})
    token = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    client.post("/clubs", json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token})
    ratings = [1100, 1000, 900]
    for i, r in enumerate(ratings):
        uid = f"p{i}"
        client.post("/users", json={"user_id": uid, "name": uid.upper(), "password": "pw"})
        t = client.post("/login", json={"user_id": uid, "password": "pw"}).json()["token"]
        client.post(f"/clubs/c1/players", json={"user_id": uid, "name": uid.upper(), "token": t})
        clubs = storage.load_data()
        clubs["c1"].members[uid].singles_rating = r
        storage.save_data(clubs)
    resp = client.get("/leaderboard_full?club=c1&limit=1&offset=1")
    assert resp.status_code == 200
    players = resp.json()["players"]
    assert len(players) == 1
    assert players[0]["user_id"] == "p1"

