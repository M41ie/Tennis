import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def test_upload_avatar_too_large(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api = importlib.reload(importlib.import_module("tennis.api"))
    client = TestClient(api.app)

    data = b"x" * (2 * 1024 * 1024 + 1)
    resp = client.post("/upload", files={"file": ("big.png", data, "image/png")})
    assert resp.status_code == 413
