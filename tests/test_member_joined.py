import datetime
import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def setup_client(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    return TestClient(api.app)


def test_member_join_dates_per_club(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)

    # register users and create two clubs
    client.post("/users", json={"user_id": "leader1", "name": "L1", "password": "pw", "allow_create": True})
    client.post("/users", json={"user_id": "leader2", "name": "L2", "password": "pw", "allow_create": True})
    client.post("/users", json={"user_id": "player", "name": "P", "password": "pw"})

    token1 = client.post("/login", json={"user_id": "leader1", "password": "pw"}).json()["token"]
    token2 = client.post("/login", json={"user_id": "leader2", "password": "pw"}).json()["token"]
    token_p = client.post("/login", json={"user_id": "player", "password": "pw"}).json()["token"]

    client.post("/clubs", json={"club_id": "c1", "name": "C1", "user_id": "leader1", "token": token1})
    client.post("/clubs", json={"club_id": "c2", "name": "C2", "user_id": "leader2", "token": token2})

    client.post("/clubs/c1/players", json={"user_id": "player", "name": "P", "token": token_p})
    client.post("/clubs/c2/players", json={"user_id": "player", "name": "P", "token": token_p})

    # adjust join dates
    today = datetime.date.today()
    club1 = storage.get_club("c1")
    club2 = storage.get_club("c2")
    club1.member_joined["player"] = today - datetime.timedelta(days=5)
    club2.member_joined["player"] = today - datetime.timedelta(days=2)
    storage.save_club(club1)
    storage.save_club(club2)

    resp1 = client.get("/clubs/c1/players").json()[0]
    resp2 = client.get("/clubs/c2/players").json()[0]

    assert resp1["joined"] == (today - datetime.timedelta(days=5)).isoformat()
    assert resp2["joined"] == (today - datetime.timedelta(days=2)).isoformat()

