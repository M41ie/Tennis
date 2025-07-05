import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def test_subscribe_quota_and_log(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    wechat = importlib.reload(importlib.import_module("tennis.wechat"))

    client = TestClient(api.app)

    client.post("/users", json={"user_id": "u1", "name": "U1", "password": "pw", "allow_create": True})
    token = client.post("/login", json={"user_id": "u1", "password": "pw"}).json()["token"]

    resp = client.post("/subscribe", json={"user_id": "u1", "scene": "audit", "token": token})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    with storage._connect() as conn:
        row = conn.execute(
            "SELECT quota FROM user_subscribe WHERE user_id = ? AND scene = ?",
            ("u1", "audit"),
        ).fetchone()
        assert row is not None and row[0] == 1

    async def fake_send(openid, audit_type, audit_status, page):
        return {"errcode": 43101, "errmsg": "fail"}

    monkeypatch.setattr(wechat, "_send", fake_send)

    wechat.send_audit_message("u1", "wx", "audit", "type", "status", "p")

    with storage._connect() as conn:
        row = conn.execute(
            "SELECT errcode FROM subscribe_log WHERE user_id = ? AND scene = ?",
            ("u1", "audit"),
        ).fetchone()
        assert row is not None and row[0] == 43101
