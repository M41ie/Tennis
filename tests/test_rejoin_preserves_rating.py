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


def test_rejoin_preserves_rating(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)

    for uid, allow in [("leader1", True), ("leader2", True), ("p1", False)]:
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    token_l1 = client.post("/login", json={"user_id": "leader1", "password": "pw"}).json()["token"]
    token_l2 = client.post("/login", json={"user_id": "leader2", "password": "pw"}).json()["token"]
    token_p1 = client.post("/login", json={"user_id": "p1", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader1", "token": token_l1},
    )
    client.post(
        "/clubs",
        json={"club_id": "c2", "name": "C2", "user_id": "leader2", "token": token_l2},
    )

    client.post("/clubs/c1/join", json={"user_id": "p1", "token": token_p1})
    client.post(
        "/clubs/c1/approve",
        json={"approver_id": "leader1", "user_id": "p1", "rating": 1000.0, "token": token_l1},
    )

    client.request("DELETE", "/clubs/c1", json={"user_id": "leader1", "token": token_l1})

    client.post("/clubs/c2/join", json={"user_id": "p1", "token": token_p1})
    client.post(
        "/clubs/c2/approve",
        json={"approver_id": "leader2", "user_id": "p1", "rating": 1200.0, "token": token_l2},
    )

    with storage._connect() as conn:
        rating = conn.execute(
            "SELECT singles_rating, doubles_rating FROM players WHERE user_id = 'p1'"
        ).fetchone()
        assert rating == (1000.0, 1000.0)
