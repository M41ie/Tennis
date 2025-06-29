import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def test_upload_then_update_avatar(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post(
        "/users",
        json={"user_id": "u1", "name": "U1", "password": "pw"},
    )
    token = client.post("/login", json={"user_id": "u1", "password": "pw"}).json()["token"]

    img = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\xda\x63\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xa5\x00\x00\x00\x00IEND\xaeB\x60\x82"
    )
    resp = client.post("/upload", files={"file": ("a.png", img, "image/png")})
    assert resp.status_code == 200
    url = resp.json()["url"]

    resp = client.put(
        "/players/u1",
        json={"user_id": "u1", "token": token, "avatar": url},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    with storage._connect() as conn:
        row = conn.execute("SELECT avatar FROM players WHERE user_id = 'u1'").fetchone()
        assert row is not None
        assert row[0] == url
