import importlib
import datetime
from fastapi.testclient import TestClient

import tennis.storage as storage
import tennis.services.state as state


def _setup_env(tmp_path, monkeypatch, doubles=False):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)

    cli = importlib.import_module("tennis.cli")
    users = {}
    clubs = {}
    cli.register_user(users, "leader", "Leader", "pw", allow_create=True)
    players = ["p1", "p2"]
    if doubles:
        players += ["p3", "p4"]
    for uid in players:
        cli.register_user(users, uid, uid.upper(), "pw")
    cli.create_club(users, clubs, "leader", "c1", "C1", None, None)
    for uid in players:
        cli.add_player(clubs, "c1", uid, uid.upper())

    storage.save_users(users)
    storage.save_data(clubs)
    return cli, users, clubs


def test_singles_record_sorting(tmp_path, monkeypatch):
    cli, users, clubs = _setup_env(tmp_path, monkeypatch)

    cli.submit_match(clubs, "c1", "p1", "p2", 6, 4, datetime.date(2023, 1, 1), 1.0)
    cli.confirm_match(clubs, "c1", 0, "p2")

    ts1 = datetime.datetime(2023, 1, 1, 10, 0, 0)

    class DT1(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return ts1

    monkeypatch.setattr(cli.datetime, "datetime", DT1)
    cli.approve_match(clubs, "c1", 0, "leader", users)

    cli.submit_match(clubs, "c1", "p1", "p2", 6, 3, datetime.date(2023, 1, 2), 1.0)
    cli.confirm_match(clubs, "c1", 0, "p2")

    ts2 = datetime.datetime(2023, 1, 1, 12, 0, 0)

    class DT2(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return ts2

    monkeypatch.setattr(cli.datetime, "datetime", DT2)
    cli.approve_match(clubs, "c1", 0, "leader", users)

    storage.save_users(users)
    storage.save_data(clubs)

    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    records = client.get("/players/p1/records").json()
    assert len(records) == 2
    assert records[0]["self_score"] == 6 and records[0]["opponent_score"] == 3
    assert records[1]["self_score"] == 6 and records[1]["opponent_score"] == 4


def test_doubles_record_sorting(tmp_path, monkeypatch):
    cli, users, clubs = _setup_env(tmp_path, monkeypatch, doubles=True)

    cli.submit_doubles(
        clubs,
        "c1",
        "p1",
        "p2",
        "p3",
        "p4",
        6,
        4,
        datetime.date(2023, 1, 1),
        1.0,
    )
    cli.confirm_doubles(clubs, "c1", 0, "p3")
    cli.confirm_doubles(clubs, "c1", 0, "p4")

    ts1 = datetime.datetime(2023, 1, 1, 10, 0, 0)

    class DT1(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return ts1

    monkeypatch.setattr(cli.datetime, "datetime", DT1)
    cli.approve_match(clubs, "c1", 0, "leader", users)

    cli.submit_doubles(
        clubs,
        "c1",
        "p1",
        "p2",
        "p3",
        "p4",
        6,
        3,
        datetime.date(2023, 1, 2),
        1.0,
    )
    cli.confirm_doubles(clubs, "c1", 0, "p3")
    cli.confirm_doubles(clubs, "c1", 0, "p4")

    ts2 = datetime.datetime(2023, 1, 1, 12, 0, 0)

    class DT2(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return ts2

    monkeypatch.setattr(cli.datetime, "datetime", DT2)
    cli.approve_match(clubs, "c1", 0, "leader", users)

    storage.save_users(users)
    storage.save_data(clubs)

    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    records = client.get("/players/p1/doubles_records").json()
    assert len(records) == 2
    assert records[0]["self_score"] == 6 and records[0]["opponent_score"] == 3
    assert records[1]["self_score"] == 6 and records[1]["opponent_score"] == 4
