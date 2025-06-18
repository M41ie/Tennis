import pytest
import tennis.storage as storage
from tennis.models import User


def test_cache_updated_on_commit(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    u1 = User("u1", "U1", password_hash="pw")
    u2 = User("u2", "U2", password_hash="pw")
    with storage.transaction() as conn:
        storage.create_user(u1, conn=conn)
        storage.create_user(u2, conn=conn)

    storage.load_users()
    orig_id = id(storage.get_user("u2"))

    u1.name = "NEW"
    with storage.transaction() as conn:
        storage.update_user_record(u1, conn=conn)

    assert storage.get_user("u1").name == "NEW"
    assert id(storage.get_user("u2")) == orig_id


def test_cache_unchanged_on_rollback(tmp_path, monkeypatch):
    db = tmp_path / "tennis.db"
    monkeypatch.setattr(storage, "DB_FILE", db)

    u1 = User("u1", "U1", password_hash="pw")
    with storage.transaction() as conn:
        storage.create_user(u1, conn=conn)

    storage.load_users()
    name_before = storage.get_user("u1").name

    with pytest.raises(RuntimeError):
        with storage.transaction() as conn:
            u1.name = "FAIL"
            storage.update_user_record(u1, conn=conn)
            raise RuntimeError("boom")

    assert storage.get_user("u1").name == name_before
