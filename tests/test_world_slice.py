import json

import pytest


@pytest.fixture()
def seeded(store):
    store.add_canon("setting fact", "setting", immutable=True)
    store.add_canon("tone fact", "tone")
    store.add_canon("geo fact", "geography")
    pip = store.add_character("Pip", traits=["curious"])
    bramble = store.add_character("Bramble")
    store.write_events([
        {"order_index": 1, "summary": "e1", "characters_involved": [pip.id]},
        {"order_index": 2, "summary": "e2", "characters_involved": [pip.id, bramble.id]},
        {"order_index": 3, "summary": "e3", "characters_involved": [bramble.id]},
    ])
    return {"pip": pip.id, "bramble": bramble.id}


def test_slice_shape_and_full_defaults(store, seeded):
    sl = store.get_world_slice()
    assert set(sl) == {"canon", "characters", "events"}
    assert len(sl["canon"]) == 3
    assert len(sl["characters"]) == 2       # None -> all
    assert len(sl["events"]) == 3           # only 3 exist, default N=10


def test_slice_is_json_serializable(store, seeded):
    sl = store.get_world_slice()
    text = json.dumps(sl)  # must not raise
    assert json.loads(text)["characters"][0]["traits"] == ["curious"]


def test_slice_filters_characters(store, seeded):
    sl = store.get_world_slice(character_ids=[seeded["pip"]])
    assert [c["name"] for c in sl["characters"]] == ["Pip"]


def test_slice_recent_events_limit_and_order(store, seeded):
    sl = store.get_world_slice(recent_events=2)
    # 2 most recent by order_index, returned chronological (ascending)
    assert [e["summary"] for e in sl["events"]] == ["e2", "e3"]


def test_slice_recent_events_none_returns_all(store, seeded):
    sl = store.get_world_slice(recent_events=None)
    assert [e["summary"] for e in sl["events"]] == ["e1", "e2", "e3"]


def test_slice_filters_canon_categories(store, seeded):
    sl = store.get_world_slice(canon_categories=["tone", "setting"])
    cats = sorted(c["category"] for c in sl["canon"])
    assert cats == ["setting", "tone"]


def test_slice_empty_character_list(store, seeded):
    sl = store.get_world_slice(character_ids=[])
    assert sl["characters"] == []
