import pytest

from worldstate import InvalidStateError
from conftest import apply_new


def test_full_happy_path(store, world):
    def build(cs):
        store.stage_entity(cs, kind="character", slug="pip", name="Pip the Fox",
                           summary="A curious kit.")
        store.stage_entity(cs, kind="location", slug="hollow", name="The Hollow")
        store.stage_fact(cs, entity_slug="pip", key="species", value="fox")
        store.stage_fact(cs, entity_slug="pip", key="age", value="young")
        store.stage_relationship(cs, src_slug="pip", dst_slug="hollow",
                                 kind="lives_in", detail="under the old oak")
        store.stage_event(cs, seq=1, title="Pip finds the Hollow",
                          participants=[{"entity_slug": "pip", "role": "protagonist"}])

    cs = apply_new(store, world.id, build)
    assert cs.status == "applied"
    assert cs.applied_at is not None

    state = store.retrieve_world_state(world.id)
    assert {e.slug for e in state.entities} == {"pip", "hollow"}
    pip = state.entity_by_slug("pip")
    assert {f.key: f.value for f in state.facts_for(pip.id)} == {
        "species": "fox", "age": "young"
    }
    assert len(state.relationships) == 1
    assert state.relationships[0].kind == "lives_in"
    assert len(state.events) == 1
    assert len(state.event_participants) == 1
    assert state.event_participants[0].role == "protagonist"


def test_provenance_stamped(store, world):
    cs = store.propose_changeset(world.id, author="ada")
    store.stage_entity(cs.id, kind="character", slug="pip", name="Pip")
    store.approve_changeset(cs.id)
    store.apply_changeset(cs.id)

    pip = store.get_entity(world.id, "pip")
    assert pip.created_by_changeset_id == cs.id
    assert pip.updated_by_changeset_id == cs.id


def test_changes_get_target_ids(store, world):
    def build(cs):
        store.stage_entity(cs, kind="item", slug="lantern", name="Ever-Lantern")
    cs = apply_new(store, world.id, build)
    changes = store.get_changes(cs.id)
    assert len(changes) == 1
    assert changes[0].target_id is not None
    assert store.get_entity(world.id, "lantern").id == changes[0].target_id


def test_cannot_approve_twice(store, world):
    cs = store.propose_changeset(world.id)
    store.approve_changeset(cs.id)
    with pytest.raises(InvalidStateError):
        store.approve_changeset(cs.id)


def test_cannot_apply_unapproved(store, world):
    cs = store.propose_changeset(world.id)
    with pytest.raises(InvalidStateError):
        store.apply_changeset(cs.id)


def test_cannot_apply_twice(store, world):
    cs = store.propose_changeset(world.id)
    store.stage_entity(cs.id, kind="character", slug="pip", name="Pip")
    store.approve_changeset(cs.id)
    store.apply_changeset(cs.id)
    with pytest.raises(InvalidStateError):
        store.apply_changeset(cs.id)


def test_cannot_stage_after_approval(store, world):
    cs = store.propose_changeset(world.id)
    store.approve_changeset(cs.id)
    with pytest.raises(InvalidStateError):
        store.stage_entity(cs.id, kind="character", slug="pip", name="Pip")


def test_reject_blocks_apply(store, world):
    cs = store.propose_changeset(world.id)
    store.stage_entity(cs.id, kind="character", slug="pip", name="Pip")
    store.reject_changeset(cs.id)
    assert store.get_changeset(cs.id).status == "rejected"
    with pytest.raises(InvalidStateError):
        store.apply_changeset(cs.id)


def test_list_changesets(store, world):
    a = store.propose_changeset(world.id, note="first")
    b = store.propose_changeset(world.id, note="second")
    assert [c.id for c in store.list_changesets(world.id)] == [a.id, b.id]
