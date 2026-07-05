import pytest

from worldstate import (
    Canon,
    Character,
    Event,
    NotFoundError,
    SqliteWorldStore,
    WorldStore,
)


# -- interface -------------------------------------------------------------

def test_sqlite_store_implements_interface(store):
    assert isinstance(store, WorldStore)


def test_persists_to_file(tmp_path):
    path = tmp_path / "w.db"
    s1 = SqliteWorldStore.open(path)
    cid = s1.add_canon("A fact.", "lore").id
    s1.close()

    s2 = SqliteWorldStore.open(path)  # reopen; schema already present
    assert s2.get_canon(cid).statement == "A fact."
    s2.close()


# -- canon -----------------------------------------------------------------

def test_add_and_get_canon_immutable_roundtrips(store):
    c = store.add_canon("Lanterns never gutter.", "setting", immutable=True)
    assert isinstance(c, Canon)
    got = store.get_canon(c.id)
    assert got.statement == "Lanterns never gutter."
    assert got.category == "setting"
    assert got.immutable is True  # stored 0/1, exposed as bool


def test_add_canon_defaults_mutable(store):
    c = store.add_canon("A soft rule.", "tone")
    assert store.get_canon(c.id).immutable is False


def test_get_canon_missing_raises(store):
    with pytest.raises(NotFoundError):
        store.get_canon(999)


def test_list_canon_filter_by_category(store):
    store.add_canon("s1", "setting")
    store.add_canon("t1", "tone")
    store.add_canon("s2", "setting")
    assert len(store.list_canon()) == 3
    settings = store.list_canon(["setting"])
    assert [c.statement for c in settings] == ["s1", "s2"]
    assert len(store.list_canon(["tone", "setting"])) == 3
    assert store.list_canon(["nonexistent"]) == []


# -- characters ------------------------------------------------------------

def test_add_and_get_character_json_roundtrips(store):
    ch = store.add_character(
        "Pip",
        traits=["curious", "kind"],
        relationships={"hollow": "home"},
        speech_style="warm",
        history=["found the lantern"],
    )
    assert isinstance(ch, Character)
    got = store.get_character(ch.id)
    assert got.name == "Pip"
    assert got.traits == ["curious", "kind"]
    assert got.relationships == {"hollow": "home"}
    assert got.speech_style == "warm"
    assert got.history == ["found the lantern"]


def test_add_character_defaults(store):
    ch = store.get_character(store.add_character("Bramble").id)
    assert ch.traits == []
    assert ch.relationships == {}
    assert ch.speech_style == ""
    assert ch.history == []


def test_get_character_missing_raises(store):
    with pytest.raises(NotFoundError):
        store.get_character(123)


def test_list_characters(store):
    a = store.add_character("A")
    b = store.add_character("B")
    assert [c.id for c in store.list_characters()] == [a.id, b.id]
    assert [c.name for c in store.list_characters([b.id])] == ["B"]
    assert store.list_characters([]) == []


# -- events ----------------------------------------------------------------

def test_write_events_and_defaults(store):
    store.write_events([
        {"order_index": 1, "summary": "first", "characters_involved": [1],
         "world_refs": ["r"]},
        {"order_index": 2, "summary": "second"},  # json fields default, created_at auto
    ])
    events = store._recent_events(None)
    assert [e.summary for e in events] == ["first", "second"]
    assert events[0].characters_involved == [1]
    assert events[1].characters_involved == []
    assert events[1].world_refs == []
    assert all(e.created_at for e in events)  # auto-stamped


def test_write_events_accepts_event_dataclass(store):
    store.write_events([
        Event(id=0, order_index=5, summary="from dataclass",
              characters_involved=[9], world_refs=[], created_at=""),
    ])
    events = store._recent_events(None)
    assert events[0].summary == "from dataclass"
    assert events[0].created_at  # defaulted since empty


def test_write_events_atomic(store):
    # A bad event (missing required 'summary') aborts the whole batch.
    with pytest.raises(KeyError):
        store.write_events([
            {"order_index": 1, "summary": "ok"},
            {"order_index": 2},  # missing summary
        ])
    assert store._recent_events(None) == []
