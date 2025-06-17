import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def test_refresh_access_token_flow(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)

    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post("/users", json={"user_id": "u", "name": "U", "password": "pw", "allow_create": True})
    data = client.post("/login", json={"user_id": "u", "password": "pw"}).json()
    access = data["access_token"]
    refresh = data["refresh_token"]

    resp = client.post("/refresh_token", json={"refresh_token": refresh})
    assert resp.status_code == 200
    new_token = resp.json()["access_token"]
    assert new_token != access
    check = client.post("/check_token", json={"token": new_token})
    assert check.status_code == 200
    assert check.json()["user_id"] == "u"

    client.post("/logout", json={"token": new_token})
    resp2 = client.post("/refresh_token", json={"refresh_token": refresh})
    assert resp2.status_code == 401
