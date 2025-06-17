import importlib
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def setup_client(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    return TestClient(api.app)


def _register_users(client, users):
    for uid, allow in users:
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )


def _login_tokens(client, ids):
    return {uid: client.post("/login", json={"user_id": uid, "password": "pw"}).json()["token"] for uid in ids}


def test_concurrent_requests_isolate_players(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)
    _register_users(client, [("leader", True), ("p1", False), ("p2", False)])
    tokens = _login_tokens(client, ["leader", "p1", "p2"])

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": tokens["leader"]},
    )
    for pid in ("p1", "p2"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tokens[pid]},
        )

    def update(uid, new_name):
        client.patch(
            f"/players/{uid}",
            json={"user_id": uid, "token": tokens[uid], "name": new_name},
        )
        return client.get(f"/players/{uid}").json()["name"]

    with ThreadPoolExecutor() as exc:
        f1 = exc.submit(update, "p1", "ONE")
        f2 = exc.submit(update, "p2", "TWO")
        name1 = f1.result()
        name2 = f2.result()

    assert name1 == "ONE"
    assert name2 == "TWO"
