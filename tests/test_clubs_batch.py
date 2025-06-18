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


def test_get_clubs_batch(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)

    for uid in ("leader1", "leader2"):
        client.post(
            "/users",
            json={"user_id": uid, "name": uid, "password": "pw", "allow_create": True},
        )

    token1 = client.post("/login", json={"user_id": "leader1", "password": "pw"}).json()["token"]
    token2 = client.post("/login", json={"user_id": "leader2", "password": "pw"}).json()["token"]

    client.post("/clubs", json={"club_id": "c1", "name": "C1", "user_id": "leader1", "token": token1})
    client.post("/clubs", json={"club_id": "c2", "name": "C2", "user_id": "leader2", "token": token2})

    resp = client.get("/clubs/batch", params={"club_ids": "c1,c2"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = {c["club_id"] for c in data}
    assert ids == {"c1", "c2"}
