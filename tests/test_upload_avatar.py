import importlib
from fastapi.testclient import TestClient
import tennis.storage as storage
import tennis.services.state as state


def test_upload_avatar_too_large(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)
    importlib.reload(state)
    api_module = importlib.reload(importlib.import_module("tennis.api"))
    monkeypatch.setattr(api_module, "AVATARS_ROOT", tmp_path / "avatars")
    api_module.AVATARS_ROOT.mkdir(parents=True, exist_ok=True)
    client = TestClient(api_module.app)

    data = b"x" * (2 * 1024 * 1024 + 1)
    resp = client.post("/upload/image", files={"file": ("big.png", data, "image/png")})
    assert resp.status_code == 413
