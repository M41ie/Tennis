import datetime
import tennis.storage as storage
from tennis.models import Club, Player
from tennis.cli import submit_match
from tennis.storage import save_data, load_data


def test_pending_matches_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    club = Club(club_id="c", name="Club")
    p1 = Player("p1", "P1")
    p2 = Player("p2", "P2")
    club.members[p1.user_id] = p1
    club.members[p2.user_id] = p2
    clubs = {club.club_id: club}

    date = datetime.date(2023, 1, 1)
    submit_match(clubs, "c", "p1", "p2", 6, 4, date, 1.0)
    assert len(club.pending_matches) == 1

    save_data(clubs)
    loaded = load_data()
    loaded_club = loaded["c"]
    assert len(loaded_club.pending_matches) == 1
    match = loaded_club.pending_matches[0]
    assert match.score_a == 6
    assert match.score_b == 4
    assert match.confirmed_a
    assert not match.confirmed_b
