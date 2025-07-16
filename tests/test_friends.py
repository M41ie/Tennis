import datetime
import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def setup_env(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    cli = importlib.import_module("tennis.cli")
    users = {}
    clubs = {}
    cli.register_user(users, "leader", "L", "pw", allow_create=True)
    for uid in ("p1", "p2", "p3", "p4"):
        cli.register_user(users, uid, uid.upper(), "pw")
    cli.create_club(users, clubs, "leader", "c1", "C1", None, None)
    for uid in ("p1", "p2", "p3", "p4"):
        cli.add_player(clubs, "c1", uid, uid.upper())
    # singles matches
    cli.record_match(clubs, "c1", "p1", "p2", 6, 4, datetime.date(2023,1,1), 1.0)
    cli.record_match(clubs, "c1", "p3", "p1", 6, 2, datetime.date(2023,1,2), 1.0)
    # doubles matches
    cli.record_doubles(clubs, "c1", "p1", "p2", "p3", "p4", 6, 3, datetime.date(2023,1,3), 1.0)
    cli.record_doubles(clubs, "c1", "p1", "p3", "p2", "p4", 4, 6, datetime.date(2023,1,4), 1.0)
    storage.save_users(users)
    storage.save_data(clubs)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)
    return client


def test_player_friends_api(tmp_path, monkeypatch):
    client = setup_env(tmp_path, monkeypatch)
    data = client.get("/players/p1/friends").json()
    assert len(data) == 3
    by_id = {d["user_id"]: d for d in data}
    assert by_id["p2"]["weight"] == 3.0
    assert by_id["p2"]["wins"] == 2.0
    assert by_id["p3"]["weight"] == 3.0
    assert by_id["p3"]["wins"] == 1.0
    assert by_id["p4"]["weight"] == 2.0
    assert by_id["p4"]["wins"] == 1.0
