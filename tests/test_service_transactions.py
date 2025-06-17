import datetime
import sqlite3
import pytest
import tennis.storage as storage
from tennis.models import Club, Player
from tennis.services.clubs import record_match_result


def test_record_match_transaction_rollback(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    club = Club(club_id="c1", name="Club", leader_id="leader")
    p1 = Player("p1", "P1", singles_rating=1000.0)
    p2 = Player("p2", "P2", singles_rating=1000.0)
    leader = Player("leader", "Leader", singles_rating=1000.0)

    with storage.transaction() as conn:
        storage.create_club(club, conn=conn)
        for p in (p1, p2, leader):
            storage.create_player("c1", p, conn=conn)

    orig_save_club = storage.save_club

    def failing_save_club(club, conn=None):
        orig_save_club(club, conn=conn)
        raise RuntimeError("boom")

    monkeypatch.setattr(
        __import__("tennis.services.clubs", fromlist=["save_club"]),
        "save_club",
        failing_save_club,
    )

    with pytest.raises(RuntimeError):
        record_match_result(
            "c1",
            "p1",
            "p2",
            6,
            0,
            datetime.date(2023, 1, 1),
            1.0,
        )

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 0
        rating_p1 = conn.execute(
            "SELECT singles_rating FROM players WHERE user_id = 'p1'"
        ).fetchone()[0]
        rating_p2 = conn.execute(
            "SELECT singles_rating FROM players WHERE user_id = 'p2'"
        ).fetchone()[0]
        assert rating_p1 == 1000.0
        assert rating_p2 == 1000.0
