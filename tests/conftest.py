import pytest

from worldstate import WorldStateStore


@pytest.fixture()
def store():
    s = WorldStateStore.open(":memory:")
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def world(store):
    return store.create_world("emberfall", "Emberfall", "A signature bedtime world.")


def apply_new(store, world_id, build, *, author="tester", note=""):
    """Helper: propose -> build -> approve -> apply, return applied changeset."""
    cs = store.propose_changeset(world_id, author=author, note=note)
    build(cs.id)
    store.approve_changeset(cs.id)
    return store.apply_changeset(cs.id)
