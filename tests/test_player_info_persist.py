import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def test_player_info_preserved_after_prerate(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    client.post(
        "/users",
        json={
            "user_id": "leader",
            "name": "Leader",
            "password": "pw",
            "allow_create": True,
            "avatar": "url1",
            "gender": "M",
        },
    )
    client.post(
        "/users",
        json={"user_id": "rater", "name": "Rater", "password": "pw"},
    )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_rater = client.post("/login", json={"user_id": "rater", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "rater", "name": "RATER", "token": token_rater},
    )

    resp = client.post(
        "/clubs/c1/prerate",
        json={"rater_id": "rater", "target_id": "leader", "rating": 1100, "token": token_rater},
    )
    assert resp.status_code == 200

    resp = client.get("/clubs/c1/players/leader")
    assert resp.status_code == 200
    data = resp.json()
    assert data["avatar"] == "url1"
    assert data["gender"] == "M"
