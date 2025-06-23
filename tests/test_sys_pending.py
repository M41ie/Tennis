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


def _register_users(client, ids):
    for uid in ids:
        allow = uid == "leader"
        client.post(
            "/users",
            json={"user_id": uid, "name": uid.upper(), "password": "pw", "allow_create": allow},
        )


def _login_tokens(client, ids):
    return {uid: client.post("/login", json={"user_id": uid, "password": "pw"}).json()["token"] for uid in ids}


def test_sys_pending_singles_filtered(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)
    _register_users(client, ["A", "leader", "p1", "p2"])
    tokens = _login_tokens(client, ["A", "leader", "p1", "p2"])

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": tokens["leader"]},
    )
    for pid in ("p1", "p2"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tokens["leader"]},
        )

    client.post(
        "/clubs/c1/pending_matches",
        json={"initiator": "p1", "opponent": "p2", "score_initiator": 6, "score_opponent": 4, "token": tokens["p1"]},
    )
    client.post(
        "/clubs/c1/pending_matches/0/reject",
        json={"user_id": "p2", "token": tokens["p2"]},
    )

    resp = client.get(f"/sys/pending_matches?token={tokens['A']}")
    assert resp.status_code == 200
    assert resp.json() == []

    client.post(
        "/clubs/c1/pending_matches",
        json={"initiator": "p1", "opponent": "p2", "score_initiator": 6, "score_opponent": 3, "token": tokens["p1"]},
    )
    client.post(
        "/clubs/c1/pending_matches/1/confirm",
        json={"user_id": "p2", "token": tokens["p2"]},
    )
    client.post(
        "/clubs/c1/pending_matches/1/veto",
        json={"approver": "leader", "token": tokens["leader"]},
    )

    resp = client.get(f"/sys/pending_matches?token={tokens['A']}")
    assert resp.status_code == 200
    assert resp.json() == []


def test_sys_pending_doubles_filtered(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)
    _register_users(client, ["A", "leader", "p1", "p2", "p3", "p4"])
    tokens = _login_tokens(client, ["A", "leader", "p1", "p2", "p3", "p4"])

    client.post(
        "/clubs",
        json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": tokens["leader"]},
    )
    for pid in ("p1", "p2", "p3", "p4"):
        client.post(
            "/clubs/c1/players",
            json={"user_id": pid, "name": pid.upper(), "token": tokens["leader"]},
        )

    client.post(
        "/clubs/c1/pending_doubles",
        json={
            "initiator": "p1",
            "partner": "p2",
            "opponent1": "p3",
            "opponent2": "p4",
            "score_initiator": 6,
            "score_opponent": 3,
            "token": tokens["p1"],
        },
    )
    client.post(
        "/clubs/c1/pending_doubles/0/reject",
        json={"user_id": "p3", "token": tokens["p3"]},
    )

    resp = client.get(f"/sys/pending_doubles?token={tokens['A']}")
    assert resp.status_code == 200
    assert resp.json() == []

    client.post(
        "/clubs/c1/pending_doubles",
        json={
            "initiator": "p1",
            "partner": "p2",
            "opponent1": "p3",
            "opponent2": "p4",
            "score_initiator": 6,
            "score_opponent": 2,
            "token": tokens["p1"],
        },
    )
    client.post(
        "/clubs/c1/pending_doubles/1/confirm",
        json={"user_id": "p3", "token": tokens["p3"]},
    )
    client.post(
        "/clubs/c1/pending_doubles/1/veto",
        json={"approver": "leader", "token": tokens["leader"]},
    )

    resp = client.get(f"/sys/pending_doubles?token={tokens['A']}")
    assert resp.status_code == 200
    assert resp.json() == []
