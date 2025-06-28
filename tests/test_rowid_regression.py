import datetime
import tennis.storage as storage
from tennis.models import Player, Match, Appointment


class DummyCursor:
    def __init__(self):
        self.lastrowid = 1
    def execute(self, *a, **kw):
        return None
    def executemany(self, *a, **kw):
        return None
    def fetchone(self):
        return {"id": 1}
    def fetchall(self):
        return []
    def __iter__(self):
        return iter([])


class DummyConn:
    def __init__(self):
        self.cursor_obj = DummyCursor()
    def cursor(self, *a, **kw):
        return self.cursor_obj
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass


def test_returning_id_with_pg(monkeypatch):
    monkeypatch.setattr(storage, "IS_PG", True)
    monkeypatch.setattr(storage, "_refresh_after_write", lambda: None)
    conn = DummyConn()

    p = Player("p", "P", singles_rating=1000.0)
    match = Match(date=datetime.date.today(), player_a=p, player_b=p, score_a=6, score_b=0)
    assert storage.create_match("c", match, conn=conn) == 1

    appt = Appointment(date=datetime.date.today(), creator="p")
    assert storage.create_appointment_record("c", appt, conn=conn) == 1

    monkeypatch.setattr(storage, "_connect", lambda: conn)
    assert storage.create_message_record("p", "hi") == 1
