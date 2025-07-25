import importlib
import tennis.storage as storage
from fastapi.testclient import TestClient
import tennis.services.state as state
import tennis.models


def setup_db(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    return api, TestClient(api.app)


def test_leaderboard_full(tmp_path, monkeypatch):
    api, client = setup_db(tmp_path, monkeypatch)

    # register users
    for uid, allow in (("leader", True), ("p1", False)):
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_p1 = client.post("/login", json={"user_id": "p1", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p1", "name": "P1", "token": token_p1},
    )

    club = storage.get_club("c1")
    club.members["p1"].singles_rating = 1200
    storage.save_club(club)

    resp = client.get("/leaderboard_full?club=c1&user_id=p1")
    assert resp.status_code == 200
    data = resp.json()
    assert any(c["club_id"] == "c1" for c in data.get("clubs", []))
    assert data.get("joined_clubs") == ["c1"]
    assert data.get("players")[0]["user_id"] == "p1"


def test_global_leaderboard_includes_orphan(tmp_path, monkeypatch):
    api, client = setup_db(tmp_path, monkeypatch)

    # register a user without joining any club
    client.post(
        "/users",
        json={"user_id": "solo", "name": "Solo", "password": "pw"},
    )

    # give the user a rating so they show up
    player = storage.get_player("solo")
    player.singles_rating = 1000.0
    storage.update_player_record(player)

    resp = client.get("/leaderboard_full")
    assert resp.status_code == 200
    ids = [p["user_id"] for p in resp.json()["players"]]
    assert "solo" in ids


def test_leaderboard_full_sort_matches(tmp_path, monkeypatch):
    api, client = setup_db(tmp_path, monkeypatch)

    for uid, allow in (("leader", True), ("p1", False), ("p2", False)):
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_p1 = client.post("/login", json={"user_id": "p1", "password": "pw"}).json()["token"]
    token_p2 = client.post("/login", json={"user_id": "p2", "password": "pw"}).json()["token"]

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p1", "name": "P1", "token": token_p1},
    )
    client.post(
        "/clubs/c1/players",
        json={"user_id": "p2", "name": "P2", "token": token_p2},
    )

    club = storage.get_club("c1")
    import datetime
    from tennis.models import Match
    p1 = club.members["p1"]
    p2 = club.members["p2"]
    today = datetime.date.today()
    match = Match(date=today, player_a=p1, player_b=p2, score_a=6, score_b=4, club_id="c1")
    p1.singles_matches.append(match)
    p2.singles_matches.append(match)
    p2.singles_matches.append(match)
    for m in club.members.values():
        m.singles_rating = 1000
    storage.save_club(club)

    resp = client.get("/leaderboard_full?club=c1&sort=matches")
    assert resp.status_code == 200
    data = resp.json()
    ids = [p["user_id"] for p in data["players"]]
    assert ids[0] == "p2"
