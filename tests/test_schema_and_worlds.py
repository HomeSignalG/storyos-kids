import sqlite3

import pytest

from worldstate import NotFoundError, WorldStateStore, db


def test_schema_version_recorded():
    conn = db.connect(":memory:")
    assert db.schema_version(conn) == db.SCHEMA_VERSION
    conn.close()


def test_foreign_keys_enabled(store):
    (fk,) = store.conn.execute("PRAGMA foreign_keys").fetchone()
    assert fk == 1


def test_persists_to_file(tmp_path):
    path = tmp_path / "world.db"
    s1 = WorldStateStore.open(path)
    w = s1.create_world("emberfall", "Emberfall")
    s1.close()

    s2 = WorldStateStore.open(path)  # reopen; schema already present
    assert s2.get_world_by_slug("emberfall").id == w.id
    s2.close()


def test_create_and_fetch_world(store):
    w = store.create_world("emberfall", "Emberfall", "desc")
    assert w.slug == "emberfall"
    assert store.get_world(w.id).name == "Emberfall"
    assert store.get_world_by_slug("emberfall").id == w.id
    assert [x.id for x in store.list_worlds()] == [w.id]


def test_duplicate_world_slug_rejected(store):
    store.create_world("emberfall", "Emberfall")
    with pytest.raises(sqlite3.IntegrityError):
        store.create_world("emberfall", "Another")


def test_missing_world_raises(store):
    with pytest.raises(NotFoundError):
        store.get_world(999)
    with pytest.raises(NotFoundError):
        store.get_world_by_slug("nope")
