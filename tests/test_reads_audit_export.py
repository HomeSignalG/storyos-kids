import pytest

from conftest import apply_new


def seed_world(store, world_id):
    def build(cs):
        store.stage_entity(cs, kind="character", slug="pip", name="Pip")
        store.stage_entity(cs, kind="location", slug="hollow", name="Hollow")
        store.stage_entity(cs, kind="item", slug="lantern", name="Ever-Lantern")
        store.stage_fact(cs, entity_slug="pip", key="species", value="fox")
        store.stage_relationship(cs, src_slug="pip", dst_slug="hollow", kind="lives_in")
        store.stage_relationship(cs, src_slug="pip", dst_slug="lantern", kind="keeper_of")
        store.stage_event(cs, seq=1, title="First light",
                          participants=[{"entity_slug": "pip", "role": "lead"}])
    return apply_new(store, world_id, build)


def test_get_relationships_directions(store, world):
    seed_world(store, world.id)
    pip = store.get_entity(world.id, "pip")
    hollow = store.get_entity(world.id, "hollow")
    assert len(store.get_relationships(pip.id, "out")) == 2
    assert len(store.get_relationships(pip.id, "in")) == 0
    assert len(store.get_relationships(hollow.id, "in")) == 1
    assert len(store.get_relationships(hollow.id, "both")) == 1
    with pytest.raises(ValueError):
        store.get_relationships(pip.id, "sideways")


def test_get_events_and_participants(store, world):
    seed_world(store, world.id)
    events = store.get_events(world.id)
    assert [e.seq for e in events] == [1]
    parts = store.get_event_participants(events[0].id)
    assert len(parts) == 1 and parts[0].role == "lead"


def test_provenance(store, world):
    first = seed_world(store, world.id)

    def build(cs):
        store.stage_entity_update(cs, slug="pip", summary="braver")
    second = apply_new(store, world.id, build)

    pip = store.get_entity(world.id, "pip")
    prov = store.provenance("entities", pip.id)
    assert prov["created_by"].id == first.id
    assert prov["updated_by"].id == second.id

    ev = store.get_events(world.id)[0]
    ev_prov = store.provenance("events", ev.id)
    assert ev_prov["created_by"].id == first.id
    assert ev_prov["updated_by"] is None

    with pytest.raises(ValueError):
        store.provenance("worlds", world.id)


def test_audit_log(store, world):
    seed_world(store, world.id)
    log = store.audit_log(world.id)
    # 3 entities + 1 fact + 2 relationships + 1 event = 7 applied changes
    assert len(log) == 7
    assert all(r["applied_at"] is not None for r in log)
    assert log[0]["target_table"] == "entities"
    assert log[0]["target_id"] is not None
    # ordered by (changeset, seq)
    assert [r["seq"] for r in log] == sorted(r["seq"] for r in log)


def test_audit_log_excludes_unapplied(store, world):
    seed_world(store, world.id)
    # A proposed-but-not-applied changeset must not appear.
    cs = store.propose_changeset(world.id)
    store.stage_entity(cs.id, kind="concept", slug="courage", name="Courage")
    assert len(store.audit_log(world.id)) == 7  # unchanged


def test_export_world_is_json_serializable(store, world):
    seed_world(store, world.id)
    import json
    snap = store.export_world(world.id)
    text = json.dumps(snap)  # must not raise
    reloaded = json.loads(text)
    assert reloaded["world"]["slug"] == "emberfall"
    assert len(reloaded["entities"]) == 3
    assert len(reloaded["relationships"]) == 2
    assert reloaded["events"][0]["title"] == "First light"
    assert reloaded["event_participants"][0]["role"] == "lead"
