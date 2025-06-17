import importlib
import pytest
import testing.postgresql
from tennis.models import players
import tennis.storage as storage

@pytest.fixture(autouse=True)
def clear_players():
    players.set({})
    yield
    players.set({})


@pytest.fixture(autouse=True)
def use_postgres(monkeypatch):
    with testing.postgresql.Postgresql() as pg:
        monkeypatch.setenv("DATABASE_URL", pg.url())
        importlib.reload(storage)
        yield
        storage.invalidate_cache()


def fetch(conn, query, *args):
    """Return the first row for ``query`` using the given SQLite connection."""
    cur = conn.cursor()
    row = cur.execute(query, args).fetchone()
    return row

