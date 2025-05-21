import importlib
from fastapi.testclient import TestClient
import pytest
import tennis.storage as storage


def setup_api(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)
    return client


def prepare_basic_club(client):
    # register users
    client.post("/users", json={"user_id": "leader", "name": "L", "password": "pw", "allow_create": True})
    client.post("/users", json={"user_id": "p1", "name": "P1", "password": "pw"})
    client.post("/users", json={"user_id": "p2", "name": "P2", "password": "pw"})

    token_leader = client.post("/login", json={"user_id": "leader", "password": "pw"}).json()["token"]
    token_p1 = client.post("/login", json={"user_id": "p1", "password": "pw"}).json()["token"]

    client.post("/clubs", json={"club_id": "c1", "name": "C1", "user_id": "leader", "token": token_leader})
    client.post("/clubs/c1/players", json={"user_id": "p1", "name": "P1", "token": token_p1})
    token_p2 = client.post("/login", json={"user_id": "p2", "password": "pw"}).json()["token"]
    client.post("/clubs/c1/players", json={"user_id": "p2", "name": "P2", "token": token_p2})
    return token_p1


@pytest.mark.parametrize("score_a,score_b", [(-1, 0), (1, -1), (1.2, 3)])
def test_record_match_api_invalid(tmp_path, monkeypatch, score_a, score_b):
    client = setup_api(tmp_path, monkeypatch)
    token_p1 = prepare_basic_club(client)
    resp = client.post(
        "/clubs/c1/matches",
        json={
            "user_id": "p1",
            "user_a": "p1",
            "user_b": "p2",
            "score_a": score_a,
            "score_b": score_b,
            "token": token_p1,
        },
    )
    assert resp.status_code == 400


@pytest.mark.parametrize("score_a,score_b", [(-2, 1), (0, -1), (2.5, 1)])
def test_submit_match_api_invalid(tmp_path, monkeypatch, score_a, score_b):
    client = setup_api(tmp_path, monkeypatch)
    token_p1 = prepare_basic_club(client)
    resp = client.post(
        "/clubs/c1/pending_matches",
        json={
            "initiator": "p1",
            "opponent": "p2",
            "score_initiator": score_a,
            "score_opponent": score_b,
            "token": token_p1,
        },
    )
    assert resp.status_code == 400
