import importlib
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

    with storage._connect() as conn:
        row = conn.execute(
            "SELECT wechat_openid FROM users WHERE user_id = ?",
            (uid,),
        ).fetchone()
        assert row is not None
        assert row[0] == "wx123"


def test_wechat_login_unique_nickname(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))

    def fake_exchange(code):
        if code == "c1":
            return {"openid": "xxxxxxABCDE1", "session_key": "sk1"}
        elif code == "c2":
            return {"openid": "xxxxxxABCDE2", "session_key": "sk2"}
        raise AssertionError("unexpected code")

    monkeypatch.setattr(api, "_exchange_wechat_code", fake_exchange)

    client = TestClient(api.app)

    r1 = client.post("/wechat_login", json={"code": "c1"})
    assert r1.status_code == 200
    uid1 = r1.json()["user_id"]

    r2 = client.post("/wechat_login", json={"code": "c2"})
    assert r2.status_code == 200
    uid2 = r2.json()["user_id"]

    with storage._connect() as conn:
        n1 = conn.execute("SELECT name FROM users WHERE user_id = ?", (uid1,)).fetchone()[0]
        n2 = conn.execute("SELECT name FROM users WHERE user_id = ?", (uid2,)).fetchone()[0]

    assert n1 == "ABCDE"
    assert n2 == "ABCDE2"
