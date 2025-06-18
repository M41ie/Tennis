import importlib
import pytest
import testing.postgresql
import fakeredis
from tennis.models import players
import tennis.storage as storage

@pytest.fixture(autouse=True)
def clear_players():
    players.clear()
    yield
    players.clear()


@pytest.fixture(autouse=True)
def use_postgres(monkeypatch):
    with testing.postgresql.Postgresql() as pg:
        monkeypatch.setenv("DATABASE_URL", pg.url())
        monkeypatch.setenv("REDIS_URL", "redis://localhost")
        monkeypatch.setattr(storage, "redis", fakeredis, raising=False)
        importlib.reload(storage)
        yield
        storage.invalidate_cache()


def fetch(conn, query, *args):
    """Return the first row for ``query`` using the given SQLite connection."""
    cur = conn.cursor()
    row = cur.execute(query, args).fetchone()
    return row


@pytest.fixture(autouse=True)
def inject_auth_header(monkeypatch):
    from fastapi.testclient import TestClient

    orig_request = TestClient.request

    def wrapped(self, method, url, *args, **kwargs):
        headers = kwargs.setdefault("headers", {})

        if "json" in kwargs and isinstance(kwargs["json"], dict):
            token = kwargs["json"].pop("token", None)
            if token:
                headers["Authorization"] = f"Bearer {token}"

        if "params" in kwargs and isinstance(kwargs["params"], dict):
            token = kwargs["params"].pop("token", None)
            if token:
                headers["Authorization"] = f"Bearer {token}"

        if "token=" in url:
            from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit

            parts = urlsplit(url)
            query = dict(parse_qsl(parts.query))
            token = query.pop("token", None)
            if token:
                headers["Authorization"] = f"Bearer {token}"
                url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

        return orig_request(self, method, url, *args, **kwargs)

    monkeypatch.setattr(TestClient, "request", wrapped)
    yield
    monkeypatch.setattr(TestClient, "request", orig_request)

