import datetime
import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state
import tennis.models


def setup(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    return TestClient(api.app), api


def test_trend_endpoints(tmp_path, monkeypatch):
    client, api = setup(tmp_path, monkeypatch)

    client.post(
        "/users",
        json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True},
    )
    client.post("/users", json={"user_id": "u1", "name": "U1", "password": "pw"})
    client.post("/users", json={"user_id": "u2", "name": "U2", "password": "pw"})

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "u1", "name": "U1", "token": token_leader},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "u2", "name": "U2", "token": token_leader},
    )

    today = datetime.date.today()
    clubs, players = storage.load_data()
    tennis.models.players.clear()
    tennis.models.players.update(players)
    clubs["c1"].members["u1"].joined = today - datetime.timedelta(days=5)
    clubs["c1"].members["u2"].joined = today - datetime.timedelta(days=2)
    storage.save_data(clubs)

    client.post(
        "/clubs/c1/matches",
        json={
            "user_id": "leader",
            "user_a": "u1",
            "user_b": "u2",
            "score_a": 6,
            "score_b": 2,
            "date": str(today - datetime.timedelta(days=1)),
            "token": token_leader,
        },
    )

    user_trend = client.get("/sys/user_trend?days=7").json()
    assert user_trend[-1]["count"] == 3

    match_activity = client.get("/sys/match_activity?days=7").json()
    assert match_activity[-2]["count"] == 1

