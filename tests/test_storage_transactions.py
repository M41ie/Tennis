import datetime
import tennis.storage as storage
from tennis.models import Club, Player, Match


def test_transactional_create(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    club = Club(club_id="c1", name="Club")
    storage.create_club(club)

    player = Player("p1", "P1", singles_rating=1000.0)
    storage.create_player("c1", player)

    match = Match(
        date=datetime.date(2023, 1, 1),
        player_a=player,
        player_b=player,
        score_a=6,
        score_b=0,
    )
    storage.create_match("c1", match, pending=False)

    loaded = storage.load_data()
    assert "c1" in loaded
    assert "p1" in loaded["c1"].members
    assert len(loaded["c1"].matches) == 1
