import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage


def setup_client(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    api = importlib.reload(importlib.import_module("tennis.api"))
    return TestClient(api.app)


def create_basic_club(client):
    users = [("leader", True), ("u1", False), ("u2", False)]
    tokens = {}
    for uid, allow in users:
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )
        tokens[uid] = client.post("/login", json={"user_id": uid, "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": tokens["leader"]},
    )
    for uid in ("u1", "u2"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": uid, "name": uid.upper(), "token": tokens[uid]},
        )
    return tokens


def test_role_management(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)
    tokens = create_basic_club(client)

    # leader cannot quit directly
    resp = client.post(
        "/clubs/c1/role",
        json={"user_id": "leader", "action": "quit", "token": tokens["leader"]},
    )
    assert resp.status_code == 400

    # promote u1 to admin
    client.post(
        "/clubs/c1/role",
        json={"user_id": "u1", "action": "toggle_admin", "token": tokens["leader"]},
    )
    info = client.get("/clubs/c1").json()
    assert "u1" in info["admin_ids"]

    # transfer leadership to u1 while they are admin
    client.post(
        "/clubs/c1/role",
        json={"user_id": "u1", "action": "transfer_leader", "token": tokens["leader"]},
    )
    info = client.get("/clubs/c1").json()
    assert info["leader_id"] == "u1"
    assert "leader" in info["admin_ids"]
    assert "u1" not in info["admin_ids"]

    # new leader toggles admin for u2
    client.post(
        "/clubs/c1/role",
        json={"user_id": "u2", "action": "toggle_admin", "token": tokens["u1"]},
    )
    info = client.get("/clubs/c1").json()
    assert "u2" in info["admin_ids"]

    # u2 quits and should lose admin role
    client.post(
        "/clubs/c1/role",
        json={"user_id": "u2", "action": "quit", "token": tokens["u2"]},
    )
    info = client.get("/clubs/c1").json()
    assert "u2" not in info["admin_ids"]
    assert all(m["user_id"] != "u2" for m in info["members"])

    # former leader resigns admin
    client.post(
        "/clubs/c1/role",
        json={"user_id": "leader", "action": "resign_admin", "token": tokens["leader"]},
    )
    info = client.get("/clubs/c1").json()
    assert "leader" not in info["admin_ids"]

