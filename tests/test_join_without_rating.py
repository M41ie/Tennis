import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def setup_client(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    return api, TestClient(api.app)


def test_join_without_rating(tmp_path, monkeypatch):
    api, client = setup_client(tmp_path, monkeypatch)

    # register users
    client.post("/users", json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True})
    client.post("/users", json={"user_id": "rated", "name": "R", "password": "pw"})
    client.post("/users", json={"user_id": "newbie", "name": "N", "password": "pw"})

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_rated = client.post("/login", json={"user_id": "rated", "password": "pw"}).json()["token"]
    token_newbie = client.post("/login", json={"user_id": "newbie", "password": "pw"}).json()["token"]

    client.post("/clubs", json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader})

    # give the rated user an initial rating
    player = storage.get_player("rated")
    player.singles_rating = 1000.0
    player.doubles_rating = 1000.0
    storage.update_player_record(player)

    resp = client.post("/clubs/c1/join", json={"user_id": "rated", "token": token_rated})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp = client.post("/clubs/c1/join", json={"user_id": "newbie", "token": token_newbie})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
