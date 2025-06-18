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


def test_sys_set_leader(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)

    # create users
    client.post(
        "/users",
        json={"user_id": "M", "name": "Admin", "password": "pw", "allow_create": True},
    )
    client.post(
        "/users",
        json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True},
    )
    client.post("/users", json={"user_id": "u1", "name": "U1", "password": "pw"})

    token_admin = client.post("/login", json={"user_id": "M", "password": "pw"}).json()["token"]
    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "u1", "name": "U1", "token": token_leader},
    )

    resp = client.post(
        "/sys/clubs/c1/leader",
        json={"user_id": "u1", "token": token_admin},
    )
    assert resp.status_code == 200
    info = client.get("/clubs/c1").json()
    assert info["leader_id"] == "u1"
    with storage._connect() as conn:
        row = conn.execute(
            "SELECT leader_id FROM club_meta WHERE club_id = 'c1'"
        ).fetchone()
        assert row[0] == "u1"
