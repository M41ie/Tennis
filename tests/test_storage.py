import datetime
import json
import tennis.storage as storage
from tennis.models import Club, Player, Match


def test_pending_matches_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    club = Club(club_id="c", name="Club")
    p1 = Player("p1", "P1", singles_rating=1000.0)
    p2 = Player("p2", "P2", singles_rating=1000.0)
    club.members[p1.user_id] = p1
    club.members[p2.user_id] = p2

    match = Match(date=datetime.date(2023, 1, 1), player_a=p1, player_b=p2, score_a=6, score_b=4, format_weight=1.0)
    match.confirmed_a = True
    club.pending_matches.append(match)
    storage.save_club(club)

    with storage._connect() as conn:
        row = conn.execute("SELECT data FROM pending_matches").fetchone()
        assert row is not None
        data = json.loads(row[0])
        assert data["score_a"] == 6
        assert data["score_b"] == 4
        assert data["confirmed_a"] is True
        assert data["confirmed_b"] is False


def test_shared_player_across_clubs(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    club1 = Club(club_id="c1", name="C1")
    club2 = Club(club_id="c2", name="C2")
    p = Player("u1", "U1", singles_rating=1000.0)
    club1.members[p.user_id] = p
    club2.members[p.user_id] = p

    storage.save_club(club1)
    storage.save_club(club2)

    with storage._connect() as conn:
        rows = conn.execute(
            "SELECT club_id FROM club_members WHERE user_id = 'u1' ORDER BY club_id"
        ).fetchall()
        assert [r[0] for r in rows] == ["c1", "c2"]
        count = conn.execute(
            "SELECT COUNT(*) FROM players WHERE user_id = 'u1'"
        ).fetchone()[0]
        assert count == 1


def test_load_after_member_removed(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    club = Club(club_id="c", name="Club")
    p1 = Player("p1", "P1", singles_rating=1000.0)
    p2 = Player("p2", "P2", singles_rating=1000.0)
    club.members[p1.user_id] = p1
    club.members[p2.user_id] = p2

    match = Match(date=datetime.date(2023, 1, 1), player_a=p1, player_b=p2, score_a=6, score_b=4, format_weight=1.0)
    club.matches.append(match)

    storage.save_club(club)

    club.members.pop("p1")

    storage.save_club(club)

    with storage._connect() as conn:
        row = conn.execute(
            "SELECT data FROM matches WHERE club_id = 'c'"
        ).fetchone()
        assert row is not None
        data = json.loads(row[0])
        assert data["player_a"] == "p1"
        members = conn.execute(
            "SELECT user_id FROM club_members WHERE club_id = 'c'"
        ).fetchall()
        assert [m[0] for m in members] == ["p2"]
