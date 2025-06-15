import pytest
from tennis.models import players

@pytest.fixture(autouse=True)
def clear_players():
    players.clear()
    yield
    players.clear()


def fetch(conn, query, *args):
    """Return the first row for ``query`` using the given SQLite connection."""
    cur = conn.cursor()
    row = cur.execute(query, args).fetchone()
    return row

