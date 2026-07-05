import pytest

from worldstate import NotFoundError
from conftest import apply_new


def seed_pip(store, world_id):
    def build(cs):
        store.stage_entity(cs, kind="character", slug="pip", name="Pip", summary="A kit.")
        store.stage_entity(cs, kind="location", slug="hollow", name="The Hollow")
        store.stage_fact(cs, entity_slug="pip", key="mood", value="curious")
    return apply_new(store, world_id, build)


def test_entity_update_changes_fields_and_provenance(store, world):
    first = seed_pip(store, world.id)

    def build(cs):
        store.stage_entity_update(cs, slug="pip", summary="A braver kit.", status="active")
    second = apply_new(store, world.id, build)

    pip = store.get_entity(world.id, "pip")
    assert pip.summary == "A braver kit."
    assert pip.created_by_changeset_id == first.id      # unchanged
    assert pip.updated_by_changeset_id == second.id     # advanced


def test_fact_update(store, world):
    seed_pip(store, world.id)

    def build(cs):
        store.stage_fact_update(cs, entity_slug="pip", key="mood", value="brave")
    apply_new(store, world.id, build)

    pip = store.get_entity(world.id, "pip")
    facts = {f.key: f.value for f in store.get_facts(pip.id)}
    assert facts["mood"] == "brave"


def test_fact_update_missing_key_raises_and_rolls_back(store, world):
    seed_pip(store, world.id)
    cs = store.propose_changeset(world.id)
    store.stage_fact(cs.id, entity_slug="pip", key="color", value="red")   # would succeed
    store.stage_fact_update(cs.id, entity_slug="pip", key="ghost", value="x")  # fails
    store.approve_changeset(cs.id)
    with pytest.raises(NotFoundError):
        store.apply_changeset(cs.id)

    # Atomic: neither change applied, and the fact "color" must NOT exist.
    pip = store.get_entity(world.id, "pip")
    keys = {f.key for f in store.get_facts(pip.id)}
    assert keys == {"mood"}
    assert store.get_changeset(cs.id).status == "approved"  # not marked applied


def test_relationship_delete(store, world):
    seed_pip(store, world.id)

    def build(cs):
        store.stage_relationship(cs, src_slug="pip", dst_slug="hollow", kind="lives_in")
    apply_new(store, world.id, build)
    assert len(store.retrieve_world_state(world.id).relationships) == 1

    cs = store.propose_changeset(world.id)
    store.stage_relationship_delete(cs.id, src_slug="pip", dst_slug="hollow",
                                    kind="lives_in")
    store.approve_changeset(cs.id)
    store.apply_changeset(cs.id)
    assert store.retrieve_world_state(world.id).relationships == []


def test_entity_delete_cascades_facts(store, world):
    seed_pip(store, world.id)
    pip = store.get_entity(world.id, "pip")
    assert store.get_facts(pip.id)  # has a fact

    cs = store.propose_changeset(world.id)
    store.stage_entity_delete(cs.id, slug="pip")
    store.approve_changeset(cs.id)
    store.apply_changeset(cs.id)

    with pytest.raises(NotFoundError):
        store.get_entity(world.id, "pip")
    # facts cascaded away
    assert store.conn.execute(
        "SELECT COUNT(*) FROM facts WHERE entity_id = ?", (pip.id,)
    ).fetchone()[0] == 0


def test_fact_referencing_unknown_entity_rolls_back(store, world):
    seed_pip(store, world.id)
    cs = store.propose_changeset(world.id)
    store.stage_fact(cs.id, entity_slug="pip", key="new", value="ok")
    store.stage_fact(cs.id, entity_slug="nobody", key="k", value="v")  # unknown -> error
    store.approve_changeset(cs.id)
    with pytest.raises(NotFoundError):
        store.apply_changeset(cs.id)

    pip = store.get_entity(world.id, "pip")
    assert {f.key for f in store.get_facts(pip.id)} == {"mood"}  # "new" rolled back


def test_duplicate_entity_slug_rolls_back(store, world):
    seed_pip(store, world.id)
    cs = store.propose_changeset(world.id)
    store.stage_entity(cs.id, kind="character", slug="pip", name="Duplicate Pip")
    store.approve_changeset(cs.id)
    with pytest.raises(Exception):
        store.apply_changeset(cs.id)
    # still exactly one entity named "Pip"
    assert store.get_entity(world.id, "pip").name == "Pip"


def test_isolation_between_worlds(store):
    a = store.create_world("emberfall", "Emberfall")
    b = store.create_world("tidepool", "Tidepool")
    apply_new(store, a.id, lambda cs: store.stage_entity(
        cs, kind="character", slug="pip", name="Pip"))
    # Same slug is fine in a different world.
    apply_new(store, b.id, lambda cs: store.stage_entity(
        cs, kind="character", slug="pip", name="Other Pip"))

    assert store.get_entity(a.id, "pip").name == "Pip"
    assert store.get_entity(b.id, "pip").name == "Other Pip"
    assert len(store.retrieve_world_state(a.id).entities) == 1
