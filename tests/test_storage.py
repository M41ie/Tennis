import datetime
import tennis.storage as storage
from tennis.models import Club, Player, players
from tennis.cli import submit_match
from tennis.storage import save_data, load_data


def test_pending_matches_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    players.clear()
    club = Club(club_id="c", name="Club")
    p1 = Player("p1", "P1", singles_rating=1000.0)
    p2 = Player("p2", "P2", singles_rating=1000.0)
    players[p1.user_id] = p1
    players[p2.user_id] = p2
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


def test_shared_player_across_clubs(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    players.clear()

    club1 = Club(club_id="c1", name="C1")
    club2 = Club(club_id="c2", name="C2")
    p = Player("u1", "U1", singles_rating=1000.0)
    players[p.user_id] = p
    club1.members[p.user_id] = p
    club2.members[p.user_id] = p

    clubs = {"c1": club1, "c2": club2}

    save_data(clubs)
    players.clear()
    loaded = load_data()
    p_loaded = players["u1"]
    assert loaded["c1"].members["u1"] is p_loaded
    assert loaded["c2"].members["u1"] is p_loaded


def test_load_after_member_removed(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    players.clear()

    club = Club(club_id="c", name="Club")
    p1 = Player("p1", "P1", singles_rating=1000.0)
    p2 = Player("p2", "P2", singles_rating=1000.0)
    players[p1.user_id] = p1
    players[p2.user_id] = p2
    club.members[p1.user_id] = p1
    club.members[p2.user_id] = p2
    clubs = {"c": club}

    m_date = datetime.date(2023, 1, 1)
    submit_match(clubs, "c", "p1", "p2", 6, 4, m_date, 1.0)
    club.matches.append(club.pending_matches.pop())

    club.members.pop("p1")

    save_data(clubs)
    players.clear()
    loaded = load_data()
    loaded_club = loaded["c"]
    assert loaded_club.matches[0].player_a.user_id == "p1"
