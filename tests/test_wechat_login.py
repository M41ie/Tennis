import importlib
import sqlite3
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def test_wechat_login_creates_user(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))

    def fake_exchange(code):
        assert code == "code123"
        return {"openid": "wx123", "session_key": "sk"}

    monkeypatch.setattr(api, "_exchange_wechat_code", fake_exchange)

    client = TestClient(api.app)

    resp = client.post("/wechat_login", json={"code": "code123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"]
    uid = data["user_id"]
    assert data["just_created"] is True

    with sqlite3.connect(storage.DB_FILE) as conn:
        row = conn.execute(
            "SELECT wechat_openid FROM users WHERE user_id = ?",
            (uid,),
        ).fetchone()
        assert row is not None
        assert row[0] == "wx123"
